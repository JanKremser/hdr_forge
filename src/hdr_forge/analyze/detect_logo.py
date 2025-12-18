import os
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import List, Optional, Tuple
import numpy as np
from collections import Counter


from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.ffmpeg import ffmpeg_wrapper
from hdr_forge.typedefs.encoder_typing import LogoRemovalAutoDetectMode, LogoRemovalMode, LogoRemovelSettings

os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "quiet"
import cv2

from hdr_forge.cli.cli_output import create_ffmpeg_progress_handler, print_info, print_warn, print_err, ProgressBarSpinner
from hdr_forge.video import Video

@dataclass
class MaskResult:
    mask: np.ndarray
    x: int
    y: int
    width: int
    height: int
    region: str | None = None


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

@dataclass
class ClusterInfo:
    boxes: List[Tuple[int, int, int, int, str]]
    centroid_x: float
    centroid_y: float
    merged_count: int = 0

    @property
    def size(self) -> int:
        return len(self.boxes)


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

    def _filter_logo_results(
        self,
        results: list[LogoDetectResult],
        video_width: int,
        video_height: int,
        max_size_ratio: float = 0.10,
        min_size_ratio: float = 0.005,
        min_confidence: float = 0.0,
        min_detection_count: int = 1
    ) -> List[LogoDetectResult]:
        """
        Filter LogoDetectResult list based on video resolution and thresholds.

        Args:
            results: List of LogoDetectResult to filter
            video_width: Video width in pixels
            video_height: Video height in pixels
            max_size_ratio: Maximum logo size as ratio of video dimension (default 10%)
            min_size_ratio: Minimum logo size as ratio of video dimension (default 0.5%)
            min_confidence: Minimum confidence threshold (default 0.0)
            min_detection_count: Minimum number of detections (default 1)

        Returns:
            Filtered list of LogoDetectResult
        """
        if not results:
            return []

        max_width = video_width * max_size_ratio
        max_height = video_height * max_size_ratio
        min_width = video_width * min_size_ratio
        min_height = video_height * min_size_ratio

        filtered: List[LogoDetectResult] = []

        for result in results:
            # Größen-Filter (zu groß)
            if result.width > max_width or result.height > max_height:
                continue

            # Größen-Filter (zu klein)
            if result.width < min_width or result.height < min_height:
                continue

            # Confidence-Filter
            if result.confidence < min_confidence:
                continue

            # Detection-Count-Filter
            if result.detection_count < min_detection_count:
                continue

            filtered.append(result)

        return filtered

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

    def _sample_frames(self, cap: cv2.VideoCapture) -> List[Tuple[int, int, int, int, str]]:
        """
        Sample frames across the video and collect logo candidates.
        """
        fps = self._video.get_fps()
        total_frames = self._video.get_total_frames()
        duration_seconds = self._video.get_duration_seconds()

        interval = max(duration_seconds / (self._scan_frames + 1), 1.0)
        positions_seconds = [int(interval * (i + 1)) for i in range(self._scan_frames)]

        detected_boxes: List[Tuple[int, int, int, int, str]] = []

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

            self._progressbar.update(percent=((idx + 1) / len(positions_seconds)) * 100)

        return detected_boxes

    def _calculate_cluster_centroid(
        self,
        cluster: List[Tuple[int, int, int, int, str]]
    ) -> Tuple[float, float]:
        """Calculate the centroid of a cluster."""
        centers_x = [b[0] + b[2] / 2 for b in cluster]
        centers_y = [b[1] + b[3] / 2 for b in cluster]
        return (
            sum(centers_x) / len(centers_x),
            sum(centers_y) / len(centers_y)
        )

    def _merge_cluster_into_base(
        self,
        base_cluster_idx: int,
        all_clusters: List[List[Tuple[int, int, int, int, str]]],
        merge_threshold: float
    ) -> Tuple[List[Tuple[int, int, int, int, str]], int, List[int]]:
        """
        Merge nearby clusters into a base cluster.

        Args:
            base_cluster_idx: Index of the base cluster in all_clusters
            all_clusters: List of all clusters
            merge_threshold: Maximum distance for merging

        Returns:
            Tuple of (merged_boxes, merge_count, merged_indices)
        """
        base_cluster = all_clusters[base_cluster_idx]
        base_centroid_x, base_centroid_y = self._calculate_cluster_centroid(base_cluster)
        merged_boxes = list(base_cluster)
        merged_count = 0
        merged_indices: List[int] = []

        for idx, cluster in enumerate(all_clusters):
            if idx == base_cluster_idx:
                continue

            centroid_x, centroid_y = self._calculate_cluster_centroid(cluster)
            distance = np.sqrt(
                (base_centroid_x - centroid_x)**2 +
                (base_centroid_y - centroid_y)**2
            )

            if distance <= merge_threshold:
                merged_boxes.extend(cluster)
                merged_count += 1
                merged_indices.append(idx)

        return merged_boxes, merged_count, merged_indices

    def _get_largest_box_area(
        self,
        cluster: List[Tuple[int, int, int, int, str]],
        max_logo_size: int = 600
    ) -> int:
        """Get the area of the largest reasonable box in a cluster."""
        reasonable = [
            b[2] * b[3] for b in cluster
            if b[2] <= max_logo_size and b[3] <= max_logo_size
        ]
        if not reasonable:
            reasonable = [b[2] * b[3] for b in cluster]
        return max(reasonable) if reasonable else 0

    def _build_all_merged_clusters(
        self,
        clusters: List[List[Tuple[int, int, int, int, str]]]
    ) -> List[ClusterInfo]:
        """
        Build merged clusters matching original algorithm:

        1. Sort clusters by size (largest first)
        2. For each cluster, merge nearby clusters into it
        3. Track which clusters have been used
        4. Return all merged clusters (sorted by size)
        """
        max_dimension = max(self._video.width, self._video.height)
        merge_threshold = max_dimension * 0.08

        # Erstelle Index-Liste sortiert nach Cluster-Größe (größte zuerst)
        sorted_indices = sorted(range(len(clusters)), key=lambda i: len(clusters[i]), reverse=True)

        merged_results: List[ClusterInfo] = []
        used_clusters: set = set()

        for orig_idx in sorted_indices:
            if orig_idx in used_clusters:
                continue

            merged_boxes, merged_count, merged_indices = self._merge_cluster_into_base(
                orig_idx, clusters, merge_threshold
            )

            # Markiere verwendete Cluster
            used_clusters.add(orig_idx)
            for idx in merged_indices:
                used_clusters.add(idx)

            centroid_x, centroid_y = self._calculate_cluster_centroid(merged_boxes)
            merged_results.append(ClusterInfo(
                boxes=merged_boxes,
                centroid_x=centroid_x,
                centroid_y=centroid_y,
                merged_count=merged_count
            ))

        # Ergebnisse sind bereits nach ursprünglicher Cluster-Größe geordnet
        # (größter initialer Cluster zuerst)
        return merged_results

    def _find_largest_reasonable_box(
        self,
        cluster: List[Tuple[int, int, int, int, str]],
        max_logo_size: int = 600
    ) -> Tuple[int, int, int, int]:
        """
        Find the largest reasonable detection box from a cluster.
        """
        boxes_with_area = [(b[0], b[1], b[2], b[3], b[2] * b[3]) for b in cluster]

        reasonable_boxes = [
            b for b in boxes_with_area
            if b[2] <= max_logo_size and b[3] <= max_logo_size
        ]

        if not reasonable_boxes:
            reasonable_boxes = boxes_with_area

        reasonable_boxes.sort(key=lambda x: x[4], reverse=True)
        largest = reasonable_boxes[0]

        return largest[0], largest[1], largest[2], largest[3]

    def _apply_padding_and_bounds(
        self,
        x: int, y: int, w: int, h: int,
        padding: float
    ) -> Tuple[int, int, int, int]:
        """
        Apply padding to box coordinates and ensure bounds are valid.
        """
        padding_w = int(w * padding)
        padding_h = int(h * padding)

        padded_x = max(1, x - padding_w)
        padded_y = max(1, y - padding_h)
        padded_w = min(self._video.width - padded_x, w + 2 * padding_w)
        padded_h = min(self._video.height - padded_y, h + 2 * padding_h)

        # Safety bounds check
        if padded_x + padded_w > self._video.width:
            padded_w = self._video.width - padded_x
        if padded_y + padded_h > self._video.height:
            padded_h = self._video.height - padded_y

        # Ensure even dimensions
        padded_w = padded_w if padded_w % 2 == 0 else padded_w + 1
        padded_h = padded_h if padded_h % 2 == 0 else padded_h + 1

        return padded_x, padded_y, padded_w, padded_h

    def _create_logo_result(
        self,
        cluster_info: ClusterInfo,
        total_detections: int,
        padding: float
    ) -> LogoDetectResult:
        """
        Create a LogoDetectResult from a ClusterInfo.
        """
        x, y, w, h = self._find_largest_reasonable_box(cluster_info.boxes)
        x, y, w, h = self._apply_padding_and_bounds(x, y, w, h, padding)

        region_counter = Counter([b[4] for b in cluster_info.boxes])
        most_common_region = region_counter.most_common(1)[0][0]

        confidence = cluster_info.size / total_detections if total_detections else 0.0

        return LogoDetectResult(
            x=x,
            y=y,
            width=w,
            height=h,
            confidence=confidence,
            is_valid=True,
            region=most_common_region,
            detection_count=cluster_info.size
        )

    def _detect_logo_in_video(
        self,
        show_debug: bool = False,
        padding: float = 0.1
    ) -> Optional[List[LogoDetectResult]]:
        """
        Automatically detect logo positions by analyzing multiple frames.

        Args:
            show_debug: Show debug window with detected regions
            padding: Padding ratio to add around detected logos

        Returns:
            List of LogoDetectResult sorted by cluster size (largest first),
            or None if no logos detected
        """
        cap = cv2.VideoCapture(str(self._video._filepath))
        if not cap.isOpened():
            print_err("Video could not be opened for logo detection.")
            return None

        self._progressbar = ProgressBarSpinner(description="Detecting logo")
        self._progressbar.start()

        # Step 1: Sample frames and collect detections
        detected_boxes = self._sample_frames(cap)
        cap.release()

        if show_debug:
            cv2.destroyAllWindows()

        if not detected_boxes:
            self._progressbar.stop("No logo detected.")
            print_warn("No bright logo found in corner regions.")
            return None

        # Step 2: Initial clustering
        clusters = self._cluster_detections(
            detected_boxes,
            self._video.width,
            self._video.height
        )

        if not clusters:
            self._progressbar.stop("No logo detected.")
            print_warn("Clustering failed. No valid clusters found.")
            return None

        # Step 3: Build all merged clusters (sorted by size, largest first)
        merged_clusters: List[ClusterInfo] = self._build_all_merged_clusters(clusters)

        # Step 4: Create LogoDetectResult for each merged cluster
        results: List[LogoDetectResult] = [
            self._create_logo_result(cluster_info, len(detected_boxes), padding)
            for cluster_info in merged_clusters
        ]

        # Log info for the largest/best cluster
        #largest = results[0]
        #largest_cluster_info = merged_clusters[0]

        self._progressbar.stop(
            text=f"Logos detected",
            long_info_text=f"""
Clusters found:  {len(clusters)}
Total candidates: {len(results)}"""
        )

        return results

    def _create_crop_video_by_mask_size(self, mask_result: MaskResult) -> Path | None:
        temp_dir: Path = get_global_temp_directory(sub_folder="remove_logo")
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None

        process_start_time: float = time.time()

        if duration > 0:
            progress_callback = create_ffmpeg_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
                video_fps=self._video.get_fps(),
                process_name="Creating crop video:",
            )

        output_options: dict = {
            'map': '0:v:0',
            'crf': '0',
            'preset': 'ultrafast',
            'vf': f"crop=x={mask_result.x}:y={mask_result.y}:w={mask_result.width}:h={mask_result.height}"
        }
        output_path: Path = temp_dir / "crop_video.mp4"
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
        temp_dir: Path = get_global_temp_directory(sub_folder="remove_logo")
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None

        process_start_time: float = time.time()

        if duration > 0:
            progress_callback = create_ffmpeg_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
                video_fps=self._video.get_fps(),
                process_name="Creating crop+delogo video:",
            )

        mask_info: dict | None = self._get_mask_info(mask_result.mask)
        if mask_info is None:
            print_err("Could not get mask info for delogo filter.")
            return None

        delogo_str: str = f"delogo=x={mask_info['x']}:y={mask_info['y']}:w={mask_info['width']}:h={mask_info['height']}"

        output_options: dict[str, str] = {
            'map': '0:v:0',
            'crf': '0',
            'preset': 'ultrafast',
            'vf': f"crop=x={mask_result.x}:y={mask_result.y}:w={mask_result.width}:h={mask_result.height},{delogo_str}"
        }
        output_path: Path = temp_dir / "crop_delogo_video.mp4"
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
        temp_dir: Path = get_global_temp_directory(sub_folder="remove_logo")
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None

        process_start_time: float = time.time()

        if duration > 0:
            progress_callback = create_ffmpeg_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
                video_fps=self._video.get_fps(),
                process_name="Creating crop video with mask delogo:",
            )

        output_options: dict = {
            'i': [
                str(delogo_path),
                str(mask_path),
            ],
            'crf': '0',
            'preset': 'ultrafast',
            "filter_complex": "[2:v]format=gray,gblur=sigma=2.5,format=yuva420p[mask_alpha];[1:v][mask_alpha]alphamerge[replacement_masked];[0:v][replacement_masked]overlay"
        }
        output_path: Path = temp_dir / "final_crop_video_delogo_mask.mp4"
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
        Analysiert maximal 2 Minuten des Videos (oder die gesamte Länge, falls kürzer).

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

        # Berechne maximale Anzahl zu analysierender Frames (maximal 2 Minuten)
        fps = self._video.get_fps()
        duration_seconds = self._video.get_duration_seconds()
        max_duration_seconds = min(120, duration_seconds)  # Maximal 2 Minuten (120 Sekunden)
        max_frames = int(max_duration_seconds * fps)
        total_frames = self._video.get_total_frames()
        frames_to_process = min(max_frames, total_frames)

        progressbar = ProgressBarSpinner(description="Creating logo mask")
        progressbar.start()

        valid_masks: list = []
        frame_count = 0

        while frame_count < frames_to_process:
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

            frame_count += 1
            progressbar.update(percent=(frame_count / frames_to_process) * 100)

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
        return MaskResult(mask=centered_mask, x=new_x, y=new_y, width=new_w, height=new_h, region=None)

    def _create_mask_delogo(self, mask_result: MaskResult) -> None | Path:
        temp_dir: Path = get_global_temp_directory(sub_folder="remove_logo")

        mask_path: Path = temp_dir / "logo_mask.png"
        self.save_mask_image(output_path=mask_path, mask_result=mask_result, user_info=False)

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

    def save_mask_image(self, output_path: Path, mask_result: MaskResult | None = None, user_info: bool = True) -> bool:
        """
        Save the generated mask image to a file.

        Args:
            output_path (Path): Path to save the mask image.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        mask: MaskResult | None = mask_result if mask_result is not None else self._result
        if mask is None:
            print_err("No mask available to save.")
            return False

        if output_path.is_dir():
            output_path = output_path / f"mask_x{mask.x}y{mask.y}.png"

        try:
            cv2.imwrite(str(output_path), mask.mask)
            if user_info:
                print_info(f"Mask image saved to: {output_path}")
            return True
        except Exception as e:
            print_err(f"Error saving mask image: {e}")
            return False

    def _find_valid_mask(self, detect_logos: list[LogoDetectResult], index: int = 0) -> MaskResult | None:
        try:
            detect_logo: LogoDetectResult = detect_logos[index]
            mask_crop: MaskResult = self._create_mask_from_video(
                video_path=str(self._video._filepath),
                crop_rect=(detect_logo.x, detect_logo.y, detect_logo.width, detect_logo.height),
                threshold=40,
                padding=10,
                blur_radius=0
            )
            default_padding = 20
            if self._logo_removal_settings.mode == LogoRemovalMode.DELOGO:
                default_padding = 5

            mask_center: MaskResult = self._center_mask_in_canvas(
                mask=mask_crop.mask,
                crop_rect=(mask_crop.x, mask_crop.y, mask_crop.width, mask_crop.height),
                padding=default_padding
            )
            mask_center.region = detect_logo.region
            return mask_center
        except Exception as e:
            if index + 1 < len(detect_logos):
                print_info(f"Trying next detected logo candidate (index {index + 1})...")
                return self._find_valid_mask(detect_logos=detect_logos, index=index + 1)
            print_err(f"Could not create valid mask: {e}")
            return None

    def create_mask(self) -> MaskResult | None:
        detect_logos: List[LogoDetectResult] | None = self._detect_logo_in_video()
        if detect_logos is None:
            return None
        detect_logos = self._filter_logo_results(
            results=detect_logos,
            max_size_ratio=0.30,
            min_size_ratio=0.01,
            video_height=self._video.height,
            video_width=self._video.width,
        )
        if len(detect_logos) == 0:
            return None

        mask_center: MaskResult | None = self._find_valid_mask(detect_logos=detect_logos, index=0)

        self._result = mask_center
        return mask_center

    def detect_logo(self) -> None:
        if self._logo_removal_settings.mode == LogoRemovalMode.OFF:
            return

        mask: MaskResult | None = self.create_mask()
        if mask is None:
            print_err(msg="No valid logo mask could be created.")
            sys.exit(status=1)
            return None

        if self._logo_removal_settings.mode == LogoRemovalMode.MASK:
            final_mask_delogo_video: None | Path = self._create_mask_delogo(mask_result=mask)
            if final_mask_delogo_video is None:
                sys.exit(1)
                return
            self._crop_mask_delogo_video = final_mask_delogo_video

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

        if self._logo_removal_settings.mode not in [LogoRemovalMode.MASK]:
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

        if self._logo_removal_settings.mode not in [LogoRemovalMode.MASK]:
            return None

        return f"[0:v][1:v]overlay=x={self._result.x}:y={self._result.y}"
