import os
from dataclasses import dataclass
from pathlib import Path
import time
from typing import List, Optional, Tuple
import numpy as np

from hdr_forge.ffmpeg import ffmpeg_wrapper
from hdr_forge.typedefs.encoder_typing import LogoRemovalMode

os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "quiet"
import cv2

from hdr_forge.cli.cli_output import create_ffmpeg_progress_handler, print_warn, print_err, ProgressBarSpinner
from hdr_forge.video import Video

@dataclass
class MaskResult:
    mask: np.ndarray
    x: int
    y: int
    width: int
    height: int


@dataclass
class LogoResult:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    is_valid: bool = False
    region: str = ""
    detection_count: int = 0


class LogoDetector:
    def __init__(
        self,
        video: Video,
        logo_removal: LogoRemovalMode = LogoRemovalMode.OFF,
        scan_frames: int = 250,
        brightness_threshold: int = 200,
        min_area: int = 500,
        max_area: int = 15000,
        corner_ratio: float = 0.3
    ):
        """
        Initialize color-based logo detector for bright logos in corners.

        Args:
            video: Video object to analyze
            scan_frames: Number of frames to scan for logo detection
            brightness_threshold: Grayscale threshold for bright regions (default 200)
            min_area: Minimum logo area in pixels (default 500)
            max_area: Maximum logo area in pixels (default 20000)
            corner_ratio: Ratio defining corner regions (0.3 = 30% from edges)
        """
        self._video: Video = video
        self._scan_frames: int = scan_frames
        self._brightness_threshold: int = brightness_threshold
        self._min_area: int = min_area
        self._max_area: int = max_area
        self._corner_ratio: float = corner_ratio
        self._logo_removal: LogoRemovalMode = logo_removal

        self._result: LogoResult = LogoResult()

    def _find_logo_in_frame(
        self,
        frame: np.ndarray
    ) -> List[Tuple[int, int, int, int, str]]:
        """
        Find bright, contour-based regions in corners of a frame.
        Uses multiple detection methods for better transparent/semi-transparent logo detection.

        Args:
            frame: Frame to analyze

        Returns:
            List of detected logo candidates: [(x, y, w, h, region), ...]
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_height, frame_width = frame.shape[:2]

        candidates: List[Tuple[int, int, int, int, str]] = []

        # Method 1: Strong brightness threshold (opaque white logos)
        _, thresh_high = cv2.threshold(gray, self._brightness_threshold, 255, cv2.THRESH_BINARY)

        # Method 2: Adaptive threshold (semi-transparent logos with local contrast)
        thresh_adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, -2
        )

        # Method 3: Lower threshold for semi-transparent logos
        _, thresh_low = cv2.threshold(gray, max(self._brightness_threshold - 50, 150), 255, cv2.THRESH_BINARY)

        # Combine all three methods
        combined = cv2.bitwise_or(thresh_high, cv2.bitwise_or(thresh_adaptive, thresh_low))

        # Remove small noise
        kernel = np.ones((2, 2), np.uint8)
        clean = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)

        # Close small gaps (helps with transparent logos)
        kernel_close = np.ones((5, 5), np.uint8)
        clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel_close, iterations=1)

        # Extract contours
        contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self._min_area or area > self._max_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)

            # Additional filter: Check if region has sufficient brightness
            # (helps filter out false positives from adaptive threshold)
            roi: np.ndarray = gray[y:y+h, x:x+w]
            mean_brightness = np.mean(roi.astype(np.float32))

            # Require at least moderate brightness (handles semi-transparent)
            if mean_brightness < 100:
                continue

            # Determine which corner region this is in
            region = self._determine_corner_region(x, y, w, h, frame_width, frame_height)

            if self._logo_removal == LogoRemovalMode.AUTO_TOP_LEFT and region != 'top-left':
                continue
            if self._logo_removal == LogoRemovalMode.AUTO_TOP_RIGHT and region != 'top-right':
                continue
            if self._logo_removal == LogoRemovalMode.AUTO_BOT_LEFT and region != 'bottom-left':
                continue
            if self._logo_removal == LogoRemovalMode.AUTO_BOT_RIGHT and region != 'bottom-right':
                continue

            # if region not in ['top-left']:
            #     continue

            if region:
                candidates.append((x, y, w, h, region))

        return candidates

    def _determine_corner_region(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        frame_width: int,
        frame_height: int
    ) -> Optional[str]:
        """
        Determine if a bounding box is in a corner region.

        Args:
            x, y, w, h: Bounding box coordinates
            frame_width, frame_height: Frame dimensions

        Returns:
            Region name or None if not in a corner
        """
        # Calculate center of bounding box
        center_x = x + w / 2
        center_y = y + h / 2

        # Define corner boundaries
        left_bound = frame_width * self._corner_ratio
        right_bound = frame_width * (1 - self._corner_ratio)
        top_bound = frame_height * self._corner_ratio
        bottom_bound = frame_height * (1 - self._corner_ratio)

        # Check which corner
        if center_x < left_bound and center_y < top_bound:
            return "top-left"
        elif center_x > right_bound and center_y < top_bound:
            return "top-right"
        elif center_x < left_bound and center_y > bottom_bound:
            return "bottom-left"
        elif center_x > right_bound and center_y > bottom_bound:
            return "bottom-right"

        return None

    def _cluster_detections(
        self,
        detected_boxes: List[Tuple[int, int, int, int, str]],
        frame_width: int,
        frame_height: int,
        tolerance_ratio: float = 0.05
    ) -> List[List[Tuple[int, int, int, int, str]]]:
        """
        Cluster detections based on spatial proximity.

        Args:
            detected_boxes: List of detected boxes [(x, y, w, h, region), ...]
            frame_width: Frame width for calculating tolerance
            frame_height: Frame height for calculating tolerance
            tolerance_ratio: Maximum distance ratio for clustering (default 5%)

        Returns:
            List of clusters, each cluster is a list of boxes
        """
        if not detected_boxes:
            return []

        # Calculate distance threshold based on frame dimensions
        max_dimension = max(frame_width, frame_height)
        distance_threshold = max_dimension * tolerance_ratio

        clusters: List[List[Tuple[int, int, int, int, str]]] = []

        for box in detected_boxes:
            x, y, w, h, region = box
            center_x = x + w / 2
            center_y = y + h / 2

            # Find nearest cluster
            best_cluster_idx = -1
            min_distance = float('inf')

            for idx, cluster in enumerate(clusters):
                # Calculate cluster centroid
                cluster_centers_x = [b[0] + b[2] / 2 for b in cluster]
                cluster_centers_y = [b[1] + b[3] / 2 for b in cluster]
                centroid_x = sum(cluster_centers_x) / len(cluster_centers_x)
                centroid_y = sum(cluster_centers_y) / len(cluster_centers_y)

                # Calculate distance to centroid
                distance = np.sqrt((center_x - centroid_x)**2 + (center_y - centroid_y)**2)

                if distance < min_distance:
                    min_distance = distance
                    best_cluster_idx = idx

            # Add to nearest cluster or create new one
            if min_distance <= distance_threshold:
                clusters[best_cluster_idx].append(box)
            else:
                clusters.append([box])

        return clusters

    def _merge_nearby_clusters(
        self,
        clusters: List[List[Tuple[int, int, int, int, str]]],
        frame_width: int,
        frame_height: int,
        merge_distance_ratio: float = 0.15
    ) -> List[List[Tuple[int, int, int, int, str]]]:
        """
        Merge clusters that are spatially close to each other (likely parts of same logo).

        Args:
            clusters: List of clusters
            frame_width: Frame width for calculating distance
            frame_height: Frame height for calculating distance
            merge_distance_ratio: Maximum distance ratio for merging (default 15%)

        Returns:
            List of merged clusters
        """
        if len(clusters) <= 1:
            return clusters

        max_dimension = max(frame_width, frame_height)
        merge_threshold = max_dimension * merge_distance_ratio

        def get_cluster_centroid(cluster):
            """Calculate centroid of a cluster."""
            centers_x = [b[0] + b[2] / 2 for b in cluster]
            centers_y = [b[1] + b[3] / 2 for b in cluster]
            return (sum(centers_x) / len(centers_x), sum(centers_y) / len(centers_y))

        # Build distance matrix between clusters
        merged = [False] * len(clusters)
        result_clusters = []

        for i, cluster_i in enumerate(clusters):
            if merged[i]:
                continue

            # Start new merged cluster
            merged_cluster = list(cluster_i)
            merged[i] = True
            centroid_i = get_cluster_centroid(cluster_i)

            # Find nearby clusters to merge
            for j, cluster_j in enumerate(clusters):
                if i >= j or merged[j]:
                    continue

                centroid_j = get_cluster_centroid(cluster_j)
                distance = np.sqrt(
                    (centroid_i[0] - centroid_j[0])**2 +
                    (centroid_i[1] - centroid_j[1])**2
                )

                if distance <= merge_threshold:
                    merged_cluster.extend(cluster_j)
                    merged[j] = True

            result_clusters.append(merged_cluster)

        return result_clusters

    def detect_logo(
        self,
        show_debug: bool = False,
        padding: float = 0.05
    ) -> None:
        """
        Automatically detect logo position by analyzing multiple frames.

        Args:
            callback: Optional callback function(completed_frames, total_frames)
            show_debug: Show debug window with detected regions (default False)
        """
        if self._logo_removal == LogoRemovalMode.OFF:
            return

        cap = cv2.VideoCapture(str(self._video._filepath))
        if not cap.isOpened():
            print_err("Video could not be opened for logo detection.")
            return

        fps = self._video.get_fps()
        total_frames = self._video.get_total_frames()
        duration_seconds = self._video.get_duration_seconds()

        # Calculate frame positions to sample across the video
        interval = max(duration_seconds / (self._scan_frames + 1), 1.0)
        positions_seconds = [int(interval * (i + 1)) for i in range(self._scan_frames)]

        detected_boxes: List[Tuple[int, int, int, int, str]] = []

        progressbar = ProgressBarSpinner(description="Detecting logo")
        progressbar.start()

        for idx, pos_seconds in enumerate(positions_seconds):
            frame_pos = int(pos_seconds * fps)
            if frame_pos >= total_frames:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()

            if not ret:
                continue

            candidates = self._find_logo_in_frame(frame)
            detected_boxes.extend(candidates)

            if show_debug and candidates:
                debug_frame = frame.copy()
                for x, y, w, h, region in candidates:
                    cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(debug_frame, region, (x, y - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imshow("Logo Detection", debug_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            progressbar.update(percent=((idx + 1) / len(positions_seconds)) * 100)

        cap.release()
        if show_debug:
            cv2.destroyAllWindows()

        if not detected_boxes:
            progressbar.stop("No logo detected.")
            print_warn("No bright logo found in corner regions.")
            return

        # Cluster detections by spatial proximity
        clusters = self._cluster_detections(
            detected_boxes,
            self._video.width,
            self._video.height
        )

        if not clusters:
            progressbar.stop("No logo detected.")
            print_warn("Clustering failed. No valid clusters found.")
            return

        # First: Find largest cluster (most frequent position)
        largest_cluster = max(clusters, key=len)
        original_cluster_count = len(clusters)

        # Calculate centroid of largest cluster
        largest_centers_x = [b[0] + b[2] / 2 for b in largest_cluster]
        largest_centers_y = [b[1] + b[3] / 2 for b in largest_cluster]
        main_centroid_x = sum(largest_centers_x) / len(largest_centers_x)
        main_centroid_y = sum(largest_centers_y) / len(largest_centers_y)

        # Then: Merge nearby clusters that are close to the main cluster
        max_dimension = max(self._video.width, self._video.height)
        merge_threshold = max_dimension * 0.08  # 8% distance (stricter merging)

        merged_cluster = list(largest_cluster)
        merged_count = 0

        for cluster in clusters:
            if cluster is largest_cluster:
                continue

            # Calculate centroid of this cluster
            centers_x = [b[0] + b[2] / 2 for b in cluster]
            centers_y = [b[1] + b[3] / 2 for b in cluster]
            centroid_x = sum(centers_x) / len(centers_x)
            centroid_y = sum(centers_y) / len(centers_y)

            # Check distance to main cluster
            distance = np.sqrt(
                (main_centroid_x - centroid_x)**2 +
                (main_centroid_y - centroid_y)**2
            )

            if distance <= merge_threshold:
                merged_cluster.extend(cluster)
                merged_count += 1

        largest_cluster_size = len(merged_cluster)
        cluster_count = original_cluster_count

        # Strategy: Use the largest REASONABLE detection (not oversized false positives)
        # Sort by area but filter out unreasonably large boxes
        boxes_with_area = [(b[0], b[1], b[2], b[3], b[2] * b[3]) for b in merged_cluster]

        # Filter: Logo should not be larger than 600x600 pixels (adjust if needed)
        max_logo_size = 600
        reasonable_boxes = [b for b in boxes_with_area if b[2] <= max_logo_size and b[3] <= max_logo_size]

        # If no reasonable boxes, fall back to all boxes
        if not reasonable_boxes:
            reasonable_boxes = boxes_with_area

        reasonable_boxes.sort(key=lambda x: x[4], reverse=True)

        # Take only the largest reasonable detection
        largest_box = reasonable_boxes[0]
        avg_x = largest_box[0]
        avg_y = largest_box[1]
        # avg_hw = int(max(largest_box[2], largest_box[3]))
        # avg_w = avg_hw
        # avg_h = avg_hw
        avg_w = largest_box[2]
        avg_h = largest_box[3]

        # Add small 5% padding
        padding_w = int(avg_w * padding)
        padding_h = int(avg_h * padding)

        # Apply padding
        padded_x = avg_x - padding_w
        padded_y = avg_y - padding_h
        padded_w = avg_w + 2 * padding_w
        padded_h = avg_h + 2 * padding_h

        # Ensure we stay within video bounds
        avg_x = max(1, padded_x)
        avg_y = max(1, padded_y)
        avg_w = min(self._video.width - avg_x, padded_w)
        avg_h = min(self._video.height - avg_y, padded_h)

        # Double-check bounds (safety check)
        if avg_x + avg_w > self._video.width:
            avg_w = self._video.width - avg_x
        if avg_y + avg_h > self._video.height:
            avg_h = self._video.height - avg_y

        # Determine most common region in merged cluster
        from collections import Counter
        region_counter = Counter([b[4] for b in merged_cluster])
        most_common_region = region_counter.most_common(1)[0][0]

        # Calculate confidence based on detection consistency
        confidence = largest_cluster_size / len(detected_boxes) if detected_boxes else 0.0

        avg_w = avg_w if avg_w % 2 == 0 else avg_w + 1
        avg_h = avg_h if avg_h % 2 == 0 else avg_h + 1

        self._result = LogoResult(
            x=avg_x,
            y=avg_y,
            width=avg_w,
            height=avg_h,
            confidence=confidence,
            is_valid=True,
            region=most_common_region,
            detection_count=largest_cluster_size
        )

        progressbar.stop(
            text=f"Logo detected in '{most_common_region}'",
            long_info_text=f"""
Coordinates:     x={avg_x}, y={avg_y}
Size:            {avg_w}x{avg_h}
Detections:      {largest_cluster_size} out of {len(detected_boxes)} total detections
Clusters found:  {cluster_count}
Clusters merged: {merged_count}"""
        )

    def get_result(self) -> LogoResult:
        """
        Get the logo detection result.

        Returns:
            LogoResult with detected logo position and dimensions
        """
        return self._result

    def is_logo_detected(self) -> bool:
        """
        Check if a valid logo was detected.

        Returns:
            True if logo was detected, False otherwise
        """
        return self._result.is_valid

    def get_ffmpeg_delogo_filter(self) -> Optional[str]:
        """
        Generate FFmpeg delogo filter string.

        Returns:
            FFmpeg delogo filter string or None if no logo detected
        """
        if not self._result.is_valid:
            return None

        return f"delogo=x={self._result.x}:y={self._result.y}:w={self._result.width}:h={self._result.height}"

    # def _create_final_mask(self, mask_folder: str, output_path: str, padding: int, blur_radius: int = 0):
    #     """
    #     Erzeugt eine finale Maske, bei der nur die Pixel weiß bleiben,
    #     die auf allen gültigen Masken weiß sind.
    #     Frames, die komplett schwarz sind, werden ignoriert.

    #     Optional kann die Maske weichgezeichnet werden.

    #     Args:
    #         mask_folder (str): Pfad zu den Masken (z.B. "./test/all_frames/")
    #         output_path (str): Pfad zur finalen Maske (z.B. "./test/final_mask.png")
    #         blur_radius (int, optional): Radius für GaussianBlur. 0 = keine Weichzeichnung.
    #     """
    #     # Alle Masken laden
    #     mask_files = sorted(glob.glob(os.path.join(mask_folder, "*.png")))
    #     if not mask_files:
    #         raise FileNotFoundError(f"Keine PNG-Dateien im Ordner {mask_folder} gefunden!")

    #     valid_masks = []
    #     for f in mask_files:
    #         mask = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    #         if mask is None:
    #             continue
    #         # Nur Masken verwenden, die mindestens ein weißes Pixel haben
    #         if np.any(mask > 0):
    #             valid_masks.append(mask)

    #     if not valid_masks:
    #         raise ValueError("Keine gültigen Masken mit weißen Pixeln gefunden!")

    #     # Alle Masken zu einem Stack zusammenfassen
    #     stack = np.stack(valid_masks, axis=0)

    #     # Pixelweise Minimum über alle Frames (nur weiß, wenn alle Frames an dieser Stelle weiß sind)
    #     final_mask = np.min(stack, axis=0)
    #     final_mask[final_mask > 0] = 255  # Binärmaske sicherstellen

    #     # Kernel für Dilate erstellen
    #     kernel = np.ones((padding, padding), np.uint8)
    #     # Dilate anwenden → weiße Bereiche wachsen nach außen
    #     final_mask = cv2.dilate(final_mask, kernel, iterations=1)

    #     # Optional weichzeichnen
    #     if blur_radius > 0:
    #         blurred = cv2.GaussianBlur(final_mask, (blur_radius, blur_radius), 0)
    #         # Optional: wieder hartes Binärbild
    #         _, padded_mask_soft = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
    #         final_mask = padded_mask_soft

    #     # Speichern
    #     cv2.imwrite(output_path, final_mask)
    #     print(f"Finale Schnittmengen-Maske erstellt: {output_path}")

    # def generate_mask_images(self, video_path: str, output_folder: str, threshold: int = 120):
    #     """
    #     Erstellt aus einem Video binäre Maskenbilder für jeden Frame (oder jede Sekunde).

    #     Args:
    #         video_path (str): Pfad zum Video.
    #         output_folder (str): Ordner, in dem die Masken gespeichert werden.
    #         crop_rect (tuple): (x, y, w, h) Rechteck für Crop.
    #         threshold (int): Schwellwert für binär (0 oder 255).
    #     """
    #     x, y, w, h = self._result.x, self._result.y, self._result.width, self._result.height

    #     if not os.path.exists(output_folder):
    #         os.makedirs(output_folder)

    #     cap = cv2.VideoCapture(video_path)
    #     if not cap.isOpened():
    #         raise FileNotFoundError(f"Video {video_path} konnte nicht geöffnet werden!")

    #     frame_idx = 0
    #     while True:
    #         ret, frame = cap.read()
    #         if not ret:
    #             break

    #         # Crop
    #         cropped = frame[y:y+h, x:x+w]

    #         # Graustufen
    #         gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    #         # Threshold → Binärmaske
    #         _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    #         # Speichern
    #         filename = os.path.join(output_folder, f"mask_{frame_idx:04d}.png")
    #         cv2.imwrite(filename, mask)

    #         frame_idx += 1

    #     cap.release()
    #     print(f"{frame_idx} Maskenbilder erzeugt in {output_folder}")

    def _create_crop_video_by_mask(self, mask_result: MaskResult) -> bool:
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None

        process_start_time: float = time.time()

        if duration > 0:
            progress_callback = create_ffmpeg_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
            )

        output_options = {
            'vf': f"crop=x={mask_result.x}:y={mask_result.y}:w={mask_result.width}:h={mask_result.height}"
        }
        success: bool = ffmpeg_wrapper.run_ffmpeg(
            input_file=self._video._filepath,
            output_file=Path("/home/jan/Dokumente/GitHub/ehdr/samples/test/crop_video_center.mp4"),
            output_options=output_options,
            progress_callback=progress_callback
        )

        return success

    def _create_crop_video_delogo_by_mask(self, mask_result: MaskResult) -> bool:
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None

        process_start_time: float = time.time()

        if duration > 0:
            progress_callback = create_ffmpeg_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
            )

        mask_info: dict | None = self._get_mask_info(mask_result.mask)
        if mask_info is None:
            print_err("Could not get mask info for delogo filter.")
            return False

        delogo_str: str = f"delogo=x={mask_info['x']}:y={mask_info['y']}:w={mask_info['width']}:h={mask_info['height']}"

        output_options = {
            'vf': f"crop=x={mask_result.x}:y={mask_result.y}:w={mask_result.width}:h={mask_result.height},{delogo_str}"
        }
        success: bool = ffmpeg_wrapper.run_ffmpeg(
            input_file=self._video._filepath,
            output_file=Path("/home/jan/Dokumente/GitHub/ehdr/samples/test/crop_video_center_delogo.mp4"),
            output_options=output_options,
            progress_callback=progress_callback
        )

        return success

    def _create_mask_from_video(self, video_path: str, threshold: int = 200, padding: int = 0, blur_radius: int = 0, invated: bool = False) -> MaskResult:
        """
        Erzeugt direkt aus einem Video eine finale Schnittmengen-Maske im Speicher.
        Nur Pixel, die in allen gültigen Frames weiß sind, bleiben weiß.

        Args:
            video_path (str): Pfad zum Video.
            crop_rect (tuple): (x, y, w, h) für Crop.
            threshold (int): Schwellwert für binär (0 oder 255).
            blur_radius (int, optional): Radius für Weichzeichnen (0 = keine Weichzeichnung).

        Returns:
            np.ndarray: finale Maske als NumPy-Array (0 oder 255)
        """
        x, y, w, h = self._result.x, self._result.y, self._result.width, self._result.height

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Video {video_path} konnte nicht geöffnet werden!")

        progressbar = ProgressBarSpinner(description="Creating logo mask")
        progressbar.start()

        valid_masks = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Crop
            cropped = frame[y:y+h, x:x+w]

            # Graustufen
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

            # Threshold → Binärmaske
            _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

            if np.any(mask > 0):
                valid_masks.append(mask)

            progressbar.update(percent=(cap.get(cv2.CAP_PROP_POS_FRAMES) / cap.get(cv2.CAP_PROP_FRAME_COUNT)) * 100)

        progressbar.stop("Mask creation completed.")

        cap.release()
        if not valid_masks:
            raise ValueError("Keine gültigen Masken mit weißen Pixeln gefunden!")

        # Stack zu einem 3D-Array
        stack = np.stack(valid_masks, axis=0)

        # Schnittmenge: Pixel nur weiß, wenn in allen Frames weiß
        final_mask = np.min(stack, axis=0)
        final_mask[final_mask > 0] = 255

        # add padding
        kernel = np.ones((padding, padding), np.uint8)
        final_mask = cv2.dilate(final_mask, kernel, iterations=1)

        # Optional Padding / Weichzeichnen
        if blur_radius > 0:
            final_mask = cv2.GaussianBlur(final_mask, (blur_radius, blur_radius), 0)

        if invated:
            inverted_mask = cv2.bitwise_not(final_mask)
            final_mask = inverted_mask

        return MaskResult(
            mask=final_mask,
            x=x,
            y=y,
            width=w,
            height=h
        )

    def _get_mask_info(self, mask):
        """Findet Position und Größe der Maske."""
        # Konturen finden
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Größte Kontur oder alle kombinieren
        all_points = np.vstack(contours)
        x, y, w, h = cv2.boundingRect(all_points)

        # Zusätzliche Infos
        white_pixels = np.count_nonzero(mask)
        total_pixels = mask.shape[0] * mask.shape[1]

        return {
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'area_pixels': white_pixels,
            'coverage': white_pixels / total_pixels
        }

    def _center_mask_in_canvas(self, mask: np.ndarray, crop_rect: Tuple[int, int, int, int], padding: int = 10) -> MaskResult:
        """
        Verschiebt die Maskierung in der Maske in die Mitte einer neuen Maske mit Padding.
        Berechnet die neue Position und Größe im Originalvideo.

        Args:
            mask (np.ndarray): Binärmaske (0/255).
            crop_rect (tuple): (x, y, w, h) Bereich im Originalvideo, aus dem die Maske stammt.
            padding (int): Abstand um die Maskierung herum.

        Returns:
            centered_mask (np.ndarray): Neue Maske mit zentrierter Maskierung.
            new_video_pos (tuple): (x, y, w, h) im Originalvideo.
        """
        info = self._get_mask_info(mask)
        if info is None:
            raise ValueError("Keine Kontur in der Maske gefunden!")

        # Alte Position und Größe in der Maske
        mask_x, mask_y, mask_w, mask_h = info['x'], info['y'], info['width'], info['height']

        # Neue Größe inkl. Padding
        new_w = mask_w + 2 * padding
        new_h = mask_h + 2 * padding

        # Erstelle neue leere Maske
        centered_mask = np.zeros((new_h, new_w), dtype=np.uint8)

        # Kopiere die Maskierung in die Mitte
        centered_mask[padding:padding+mask_h, padding:padding+mask_w] = mask[mask_y:mask_y+mask_h, mask_x:mask_x+mask_w]

        # Berechne neue Position im Originalvideo
        crop_x, crop_y, crop_w, crop_h = crop_rect
        new_x = crop_x + mask_x - padding
        new_y = crop_y + mask_y - padding

        # Stelle sicher, dass die neue Position nicht negativ ist
        new_x = max(0, new_x)
        new_y = max(0, new_y)

        # Optional: Begrenzung auf Videogröße kann hier ergänzt werden
        return MaskResult(mask=centered_mask, x=new_x, y=new_y, width=new_w, height=new_h)

    def build_logo_mask(self):
        mask_crop: MaskResult = self._create_mask_from_video(
            video_path=str(self._video._filepath),
            threshold=40,
            padding=10,
            blur_radius=5
        )
        info: dict | None = self._get_mask_info(mask_crop.mask)
        if info is None:
            print("Keine Konturen in der Maske gefunden.")
        else:
            print(f"Position: ({info['x']}, {info['y']})")
            print(f"Größe: {info['width']}x{info['height']} px")
            print(f"Weiße Pixel: {info['area_pixels']}")

        musk_center: MaskResult = self._center_mask_in_canvas(
            mask=mask_crop.mask,
            crop_rect=(mask_crop.x, mask_crop.y, mask_crop.width, mask_crop.height),
            padding=50
        )

        cv2.imwrite("/home/jan/Dokumente/GitHub/ehdr/samples/test/mask_mini_test_center.png", musk_center.mask)

        self._create_crop_video_by_mask(musk_center)
        self._create_crop_video_delogo_by_mask(musk_center)
