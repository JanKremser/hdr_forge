import os
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable
import numpy as np
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "quiet"
import cv2
from ultralytics.models import YOLO

from hdr_forge.cli.cli_output import print_warn, print_err, ProgressBarSpinner
from hdr_forge.video import Video


@dataclass
class LogoResult:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    is_valid: bool = False


class LogoDetector:
    def __init__(
        self,
        video: Video,
        scan_frames: int = 200,
        model_path: str = "yolov8n.pt",
        max_logo_area_ratio: float = 0.1
    ):
        """
        Initialize logo detector.

        Args:
            video: Video object to analyze
            scan_frames: Number of frames to scan for logo detection
            model_path: Path to YOLO model file
            max_logo_area_ratio: Maximum area ratio for logo detection (default 0.1 = 10%)
        """
        self._video: Video = video
        self._scan_frames: int = scan_frames
        self._model_path: str = model_path
        self._max_logo_area_ratio: float = max_logo_area_ratio

        self._result: LogoResult = LogoResult()
        self._model: Optional[YOLO] = None

    def _load_model(self) -> None:
        """Load YOLO model if not already loaded."""
        if self._model is None:
            try:
                self._model = YOLO(self._model_path)
            except Exception as e:
                print_err(f"Failed to load YOLO model: {e}")
                raise

    def _detect_logo_in_frame(
        self,
        frame: np.ndarray,
        frame_area: int
    ) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect potential logos in a single frame.

        Args:
            frame: Frame to analyze
            frame_area: Total frame area for ratio calculation

        Returns:
            List of detected boxes: [(x1, y1, x2, y2, confidence), ...]
        """
        if self._model is None:
            return []

        detected_boxes: List[Tuple[int, int, int, int, float]] = []

        try:
            results = self._model(frame, verbose=False)

            for r in results:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    # Filter logos based on area (small objects at frame edges)
                    area = (x2 - x1) * (y2 - y1)

                    if area < frame_area * self._max_logo_area_ratio:
                        detected_boxes.append((x1, y1, x2, y2, conf))
        except Exception:
            pass

        return detected_boxes

    def _cluster_detections(
        self,
        detected_boxes: List[Tuple[int, int, int, int, float]],
        frame_width: int,
        frame_height: int,
        tolerance_ratio: float = 0.05
    ) -> List[List[Tuple[int, int, int, int, float]]]:
        """
        Cluster detections based on spatial proximity.

        Args:
            detected_boxes: List of detected boxes [(x1, y1, x2, y2, confidence), ...]
            frame_width: Frame width for calculating tolerance
            frame_height: Frame height for calculating tolerance
            tolerance_ratio: Maximum distance ratio for clustering (default 1.5%)

        Returns:
            List of clusters, each cluster is a list of boxes
        """
        if not detected_boxes:
            return []

        # Calculate distance threshold based on frame dimensions
        max_dimension = max(frame_width, frame_height)
        distance_threshold = max_dimension * tolerance_ratio

        clusters: List[List[Tuple[int, int, int, int, float]]] = []

        for box in detected_boxes:
            x1, y1, x2, y2, conf = box
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # Find nearest cluster
            best_cluster_idx = -1
            min_distance = float('inf')

            for idx, cluster in enumerate(clusters):
                # Calculate cluster centroid
                cluster_centers_x = [(b[0] + b[2]) / 2 for b in cluster]
                cluster_centers_y = [(b[1] + b[3]) / 2 for b in cluster]
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

    def detect_auto(
        self,
        callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """
        Automatically detect logo position by analyzing multiple frames.

        Args:
            callback: Optional callback function(completed_frames, total_frames)
        """
        self._load_model()

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

        detected_boxes: List[Tuple[int, int, int, int, float]] = []

        spinner = ProgressBarSpinner("Detecting logo...")
        spinner.start()

        for idx, pos_seconds in enumerate(positions_seconds):
            frame_pos = int(pos_seconds * fps)
            if frame_pos >= total_frames:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()

            if not ret:
                continue

            frame_area = frame.shape[0] * frame.shape[1]
            boxes = self._detect_logo_in_frame(frame, frame_area)
            detected_boxes.extend(boxes)

            if callback:
                callback(idx + 1, len(positions_seconds))

            spinner.update()

        cap.release()

        if not detected_boxes:
            spinner.stop("No logo detected.")
            print_warn("No logo found. Model might need extension or adjustment.")
            return

        # Cluster detections by spatial proximity
        clusters = self._cluster_detections(
            detected_boxes,
            self._video.width,
            self._video.height
        )

        if not clusters:
            spinner.stop("No logo detected.")
            print_warn("Clustering failed. No valid clusters found.")
            return

        # Find largest cluster (most frequent position)
        largest_cluster = max(clusters, key=len)
        cluster_count = len(clusters)
        largest_cluster_size = len(largest_cluster)

        # Calculate average only from largest cluster
        boxes_np = np.array(largest_cluster)
        avg_x1 = int(np.mean(boxes_np[:, 0]))
        avg_y1 = int(np.mean(boxes_np[:, 1]))
        avg_x2 = int(np.mean(boxes_np[:, 2]))
        avg_y2 = int(np.mean(boxes_np[:, 3]))
        avg_confidence = float(np.mean(boxes_np[:, 4]))

        width = avg_x2 - avg_x1
        height = avg_y2 - avg_y1

        self._result = LogoResult(
            x=avg_x1,
            y=avg_y1,
            width=width,
            height=height,
            confidence=avg_confidence,
            is_valid=True
        )

        spinner.stop(
            f"Logo detected at x={avg_x1}, y={avg_y1}, w={width}, h={height} "
            f"({largest_cluster_size} hits in {cluster_count} clusters)"
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
