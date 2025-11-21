from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
import os
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import List, Optional, Tuple
import numpy as np
from pyinpaint import Inpaint

from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import tempfile

from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.ffmpeg import ffmpeg_wrapper
from hdr_forge.typedefs.encoder_typing import LogoRemovalAutoDetectMode, LogoRemovalMode, LogoRemovelSettings

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
class LogoDetectResult:
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
        logo_removal: LogoRemovelSettings = LogoRemovelSettings(),
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
        self._logo_removal_settings: LogoRemovelSettings = logo_removal

        self._result: MaskResult | None = None
        self._crop_mask_delogo_video: Path | None = None

        self.temp_dir: Path = get_global_temp_directory(sub_folder="remove_logo")

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

            if self._logo_removal_settings.position == LogoRemovalAutoDetectMode.AUTO_TOP_LEFT and region != 'top-left':
                continue
            if self._logo_removal_settings.position == LogoRemovalAutoDetectMode.AUTO_TOP_RIGHT and region != 'top-right':
                continue
            if self._logo_removal_settings.position == LogoRemovalAutoDetectMode.AUTO_BOT_LEFT and region != 'bottom-left':
                continue
            if self._logo_removal_settings.position == LogoRemovalAutoDetectMode.AUTO_BOT_RIGHT and region != 'bottom-right':
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

    def _detect_logo_in_video(
        self,
        show_debug: bool = False,
        padding: float = 0.05
    ) -> None | LogoDetectResult:
        """
        Automatically detect logo position by analyzing multiple frames.

        Args:
            callback: Optional callback function(completed_frames, total_frames)
            show_debug: Show debug window with detected regions (default False)
        """
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

        progressbar.stop(
            text=f"Logo detected in '{most_common_region}'",
            long_info_text=f"""
Coordinates:     x={avg_x}, y={avg_y}
Size:            {avg_w}x{avg_h}
Detections:      {largest_cluster_size} out of {len(detected_boxes)} total detections
Clusters found:  {cluster_count}
Clusters merged: {merged_count}"""
        )

        return LogoDetectResult(
            x=avg_x,
            y=avg_y,
            width=avg_w,
            height=avg_h,
            confidence=confidence,
            is_valid=True,
            region=most_common_region,
            detection_count=largest_cluster_size
        )

    def _create_crop_video_by_mask_size(self, mask_result: MaskResult) -> Path | None:
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

        output_options: dict = {
            'vf': f"crop=x={mask_result.x}:y={mask_result.y}:w={mask_result.width}:h={mask_result.height}"
        }
        output_path: Path = self.temp_dir / "crop_video.mp4"
        success: bool = ffmpeg_wrapper.run_ffmpeg(
            input_file=self._video._filepath,
            output_file=output_path,
            output_options=output_options,
            progress_callback=progress_callback
        )
        if not success:
            return None

        return output_path

    def _create_crop_delogo_video_by_mask(self, mask_result: MaskResult) -> Path | None:
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
            return None

        delogo_str: str = f"delogo=x={mask_info['x']}:y={mask_info['y']}:w={mask_info['width']}:h={mask_info['height']}"

        output_options = {
            'vf': f"crop=x={mask_result.x}:y={mask_result.y}:w={mask_result.width}:h={mask_result.height},{delogo_str}"
        }
        output_path: Path = self.temp_dir / "crop_delogo_video.mp4"
        success: bool = ffmpeg_wrapper.run_ffmpeg(
            input_file=self._video._filepath,
            output_file=output_path,
            output_options=output_options,
            progress_callback=progress_callback
        )

        if not success:
            return None

        return output_path

    def _create_crop_video_with_mask_delogo(self, crop_video_path: Path,  delogo_path: Path, mask_path: Path) -> Path | None:
        #ffmpeg -i crop_video.mp4 -i delogo.mp4 -i mask.png -filter_complex "[2:v]format=yuva420p,scale=iw:ih[mask_alpha];[1:v][mask_alpha]alphamerge[replacement_masked];[0:v][replacement_masked]overlay" -c:a copy output.mp4
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

        output_options: dict = {
            'i': [
                str(delogo_path),
                str(mask_path),
            ],
            "filter_complex": "[2:v]format=yuva420p,scale=iw:ih[mask_alpha];[1:v][mask_alpha]alphamerge[replacement_masked];[0:v][replacement_masked]overlay"
        }
        output_path: Path = self.temp_dir / "final_crop_video_delogo_mask.mp4"
        success: bool = ffmpeg_wrapper.run_ffmpeg(
            input_file=crop_video_path,
            output_file=output_path,
            output_options=output_options,
            progress_callback=progress_callback
        )

        if not success:
            return None

        return output_path

    def _create_mask_from_video(self, video_path: str, crop_rect: Tuple[int, int, int, int], threshold: int = 200, padding: int = 0, blur_radius: int = 0, invated: bool = False) -> MaskResult:
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
        x, y, w, h = crop_rect

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

    def process_video_part(self, frames, mask_bin, ps, tmp_video_path, diff_threshold):
        """
        Bearbeitet einen Teil des Videos mit Masken-Reuse (für Multiprocessing)
        """
        height, width = frames[0].shape[:2]
        fps = 30  # nur für VideoWriter
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(tmp_video_path), fourcc, fps, (width, height))

        prev_frame = None
        prev_inpainted = None

        tmp_mask = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        mask_uint8 = (mask_bin * 255).astype(np.uint8)  # True->255, False->0
        Image.fromarray(mask_uint8).save(tmp_mask.name)

        for frame in frames:
            use_previous = False
            if prev_frame is not None:
                diff = cv2.absdiff(frame, prev_frame)
                diff_ratio = np.mean(diff > 10)
                if diff_ratio < diff_threshold and prev_inpainted is not None:
                    use_previous = True

            if use_previous and prev_inpainted is not None:
                result_bgr = frame.copy()
                # Convert to LAB für Helligkeitskorrektur
                frame_lab = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2LAB)
                prev_lab = cv2.cvtColor(prev_inpainted, cv2.COLOR_BGR2LAB)

                mask_inpainted = ~mask_bin

                # nur L-Kanal angleichen
                frame_lab[...,0][mask_inpainted] = prev_lab[...,0][mask_inpainted]

                # zurück zu BGR
                result_bgr = cv2.cvtColor(frame_lab, cv2.COLOR_LAB2BGR)
            else:
                # Inpainting ausführen
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with tempfile.NamedTemporaryFile(suffix=".png") as tmp_frame:
                    Image.fromarray(frame_rgb).save(tmp_frame.name)
                    inpainter = Inpaint(tmp_frame.name, tmp_mask.name, ps)
                    result_bgr = inpainter()

                    result_uint8 = (result_bgr * 255).clip(0,255).astype(np.uint8)
                    # RGB -> BGR für OpenCV
                    result_bgr = cv2.cvtColor(result_uint8, cv2.COLOR_RGB2BGR)
                    #result_bgr = np.clip(result_bgr, 0, 255).astype(np.uint8)
            prev_inpainted = result_bgr.copy()

            writer.write(result_bgr)
            prev_frame = frame.copy()

        writer.release()
        tmp_mask.close()
        return tmp_video_path

    def inpaint_video_multiprocess(self, input_path: Path, mask: np.ndarray, output_path: Path,
                                ps: int = 7, processes: int = 14, diff_threshold: float = 0.05):
        """
        Multiprozess-Inpainting: Video wird in Partitions geteilt, jeder Prozess bearbeitet einen Part.
        """
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Kann Video nicht öffnen: {input_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Maske prüfen / konvertieren
        if mask.shape[:2] != (height, width):
            raise ValueError(f"Maskengröße stimmt nicht: {mask.shape[:2]} != {(height, width)}")
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        mask_bin = (mask > 127) # 0/255 to bool

        # Alle Frames laden
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()

        # Video in Parts aufteilen
        part_size = (len(frames) + processes - 1) // processes
        frame_parts = [frames[i*part_size:(i+1)*part_size] for i in range(processes)]

        tmp_video_files = [tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) for _ in range(processes)]
        tmp_paths = [f.name for f in tmp_video_files]

        # --- Multiprocessing ---
        with ProcessPoolExecutor(max_workers=processes) as executor:
            futures = []
            for i in range(processes):
                if len(frame_parts[i]) > 0:
                    futures.append(executor.submit(self.process_video_part,
                                                frame_parts[i],
                                                mask_bin,
                                                ps,
                                                tmp_paths[i],
                                                diff_threshold))
            # Ergebnisse abwarten
            for f in futures:
                f.result()  # jeder Prozess erstellt sein temporäres Video

        # --- Temporäre Videos zusammenführen ---
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        for tmp_path in tmp_paths:
            cap = cv2.VideoCapture(tmp_path)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                writer.write(frame)
            cap.release()
            os.remove(tmp_path)

        writer.release()
        print(f"Fertig! Video gespeichert unter: {output_path}")

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

        # Seitenverhältnis auf gerade Zahl bringen
        if new_w % 2 != 0:
            new_w += 1
        if new_h % 2 != 0:
            new_h += 1

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

    def _create_mask_delogo(self, mask_result: MaskResult) -> None | Path:
        mask_path: Path = self.temp_dir / "logo_mask.png"

        cv2.imwrite(str(mask_path), mask_result.mask)
        crop_video_path: Path | None = self._create_crop_video_by_mask_size(mask_result=mask_result)
        if crop_video_path is None:
            print_err("Could not create crop video.")
            return None
        crop_delogo_video_path: Path | None= self._create_crop_delogo_video_by_mask(mask_result=mask_result)
        if crop_delogo_video_path is None:
            print_err("Could not create crop delogo video.")
            return None

        final_crop_video_path: Path | None = self._create_crop_video_with_mask_delogo(
            crop_video_path=crop_video_path,
            delogo_path=crop_delogo_video_path,
            mask_path=mask_path,
        )
        if final_crop_video_path is None:
            print_err("Could not create final crop video with mask delogo.")
            return None
        return final_crop_video_path

    def _create_inpainted_mask_video(self, mask_result: MaskResult) -> None | Path:
        crop_video_path: Path | None = self._create_crop_video_by_mask_size(mask_result=mask_result)
        if crop_video_path is None:
            print_err("Could not create crop video.")
            return None

        output_path: Path = self.temp_dir / "inpainted_logo_video.mp4"

        invate_mask = cv2.bitwise_not(mask_result.mask)
        mask_path: Path = self.temp_dir / "invate_mask.png"
        cv2.imwrite(str(mask_path), invate_mask)

        try:
            self.inpaint_video_multiprocess(
                input_path=crop_video_path,
                mask=invate_mask,
                output_path=output_path,
            )
        except Exception as e:
            print_err(f"Error during inpainting: {e}")
            return None

        return output_path


    def create_mask(self) -> MaskResult | None:
        detect_logo: None | LogoDetectResult = self._detect_logo_in_video()
        if detect_logo is None:
            return None

        mask_crop: MaskResult = self._create_mask_from_video(
            video_path=str(self._video._filepath),
            crop_rect=(detect_logo.x, detect_logo.y, detect_logo.width, detect_logo.height),
            threshold=40,
            padding=10,
            blur_radius=5
        )
        default_padding = 60
        if self._logo_removal_settings.mode == LogoRemovalMode.DELOGO:
            default_padding = 5
        mask_center: MaskResult = self._center_mask_in_canvas(
            mask=mask_crop.mask,
            crop_rect=(mask_crop.x, mask_crop.y, mask_crop.width, mask_crop.height),
            padding=default_padding
        )

        self._result = mask_center
        return mask_center

    def detect_logo(self) -> None:
        if self._logo_removal_settings.mode == LogoRemovalMode.OFF:
            return

        mask: MaskResult | None = self.create_mask()
        if mask is None:
            return None

        if self._logo_removal_settings.mode == LogoRemovalMode.MASK:
            final_mask_delogo_video: None | Path = self._create_mask_delogo(mask_result=mask)
            if final_mask_delogo_video is None:
                sys.exit(1)
                return
            self._crop_mask_delogo_video = final_mask_delogo_video
        elif self._logo_removal_settings.mode == LogoRemovalMode.INPAINT:
            inpainted_video_path: None | Path = self._create_inpainted_mask_video(mask_result=mask)
            if inpainted_video_path is None:
                sys.exit(1)
                return
            self._crop_mask_delogo_video = inpainted_video_path

    def get_result(self) -> MaskResult | None:
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
        return self._result is not None

    def get_ffmpeg_delogo_filter(self) -> Optional[str]:
        """
        Generate FFmpeg delogo filter string.

        Returns:
            FFmpeg delogo filter string or None if no logo detected
        """
        if not self._result:
            return None

        if self._logo_removal_settings.mode != LogoRemovalMode.DELOGO:
            return None

        return f"delogo=x={self._result.x}:y={self._result.y}:w={self._result.width}:h={self._result.height}"

    def get_ffmpeg_overlay_video_input(self) -> Optional[Path]:
        """
        Get path to temporary overlay video input for logo masking.

        Returns:
            Path to overlay video or None if no logo detected
        """
        if not self._result:
            return None

        if self._logo_removal_settings.mode not in [LogoRemovalMode.MASK, LogoRemovalMode.INPAINT]:
            return None

        # Here we would normally return the path to the generated overlay video
        # For this example, we return a placeholder path
        return self._crop_mask_delogo_video

    def get_ffmpeg_filter_filter_complex(self) -> Optional[str]:
        """
        Generate FFmpeg overlay filter string for logo masking.

        Args:
            mask_path: Path to the mask image file
        Returns:
            FFmpeg overlay filter string or None if no logo detected
        """
        if not self._result:
            return None

        if self._logo_removal_settings.mode not in [LogoRemovalMode.MASK, LogoRemovalMode.INPAINT]:
            return None

        return f"[0:v][1:v]overlay=x={self._result.x}:y={self._result.y}[v]"
