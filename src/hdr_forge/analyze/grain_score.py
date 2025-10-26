import os
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "quiet"
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from hdr_forge.cli.cli_output import ProgressBarSpinner, print_err
from hdr_forge.video import Video

@dataclass
class GrainResult:
    category: int = 0
    score: float = 0.0
    scores: List[float] | None = None

    def __post_init__(self):
        if self.scores is None:
            self.scores = []

class GrainAnalyzer:
    def __init__(
        self,
        video: Video,
        duration_sec: int | None = 20,
        sample_rate: float | None = 2,
        resize_width: int | None = 640,
        start_sec: float | None = None
    ):
        self._video: Video = video
        self._duration_sec: int = duration_sec or 5
        self._sample_rate: float = sample_rate or 1
        self._resize_width: int = resize_width or 640
        self._start_sec: float = start_sec or (video.get_duration_seconds() / 2 if start_sec == "middle" else 0)

        self._result: GrainResult = GrainResult()

    def _analyze_frame_legacy(self, frame: np.ndarray) -> float:
        h, w = frame.shape[:2]
        scale = self._resize_width / w
        frame_small = cv2.resize(frame, (self._resize_width, int(h*scale)))

        gray: np.ndarray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
        mean_val: float = float(np.mean(gray))
        contrast = np.std(gray)
        # Early exit for nearly black/white
        if mean_val < 5 or mean_val > 250:
            return 0.0
        if mean_val < 16:
            return 0.0005 * mean_val
        if contrast < 5:
            return 0.0

        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        highpass = gray.astype(np.float32) - blur.astype(np.float32)

        highpass_std = float(np.std(highpass) / 255.0) # the old score
        return float(highpass_std)


    def _analyze_frame(self, frame: np.ndarray) -> float:
        """
        Analyzes a frame for film grain.
        Text/credits edges are devalued.
        Returns: Score between 0.0 and 3.0
        """
        # Resize for performance
        h, w = frame.shape[:2]
        scale = self._resize_width / float(w)
        frame_small = cv2.resize(frame, (self._resize_width, int(h*scale)))

        # Grayscale
        gray: np.ndarray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
        mean_val = float(np.mean(gray))
        if mean_val < 5.0 or mean_val > 250.0:
            return 0.0
        if mean_val < 10.0:
            return 0.00001 * mean_val
        if mean_val < 16.0:
            return 0.0005 * mean_val

        # Block size
        block_size = 32
        h_blocks = gray.shape[0] // block_size
        w_blocks = gray.shape[1] // block_size

        scores = []

        for by in range(h_blocks):
            for bx in range(w_blocks):
                y0 = by * block_size
                x0 = bx * block_size
                block = gray[y0:y0+block_size, x0:x0+block_size]

                # Mask very bright or dark pixels (text/credits)
                mask = (block > 10) & (block < 245)
                if np.count_nonzero(mask) < (block_size*block_size*0.2):
                    continue  # too few valid pixels in block

                valid_pixels = block[mask]

                # High-Pass Filter
                blur = cv2.GaussianBlur(valid_pixels.astype(np.float32), (3, 3), 0)
                highpass = valid_pixels.astype(np.float32) - blur.astype(np.float32)

                # Standard deviation
                std_score = float(np.std(highpass) / 255.0)

                # More robust Laplacian metric: Median instead of variance
                laplacian = cv2.Laplacian(valid_pixels, cv2.CV_64F)
                laplacian_score = float(np.median(np.abs(laplacian)) / 255.0)

                # Combine scores
                block_score = 0.5 * std_score + 0.5 * laplacian_score
                scores.append(block_score)

        if not scores:
            return 0.0

        avg_score = float(np.mean(scores))
        return avg_score

    def _calculate_category(self, avg_score: float) -> int:
        if avg_score < 0.035:
            return 0
        elif avg_score < 0.05:
            return 1
        elif avg_score < 0.1:
            return 2
        return 3

    def analyze(self) -> None:
        cap = cv2.VideoCapture(str(self._video._filepath))
        if not cap.isOpened():
            raise RuntimeError("Video cannot be opened")

        fps = self._video.get_fps()
        start_frame = int(self._start_sec * fps)
        end_frame = min(
            start_frame + int(self._duration_sec * fps),
            self._video.get_total_frames()
        )
        sample_interval = max(int(fps * self._sample_rate), 1)


        scores: List[float] = []
        spinner = ProgressBarSpinner("Analyzing grain...")
        spinner.start()

        for i in range(start_frame, end_frame, sample_interval):
            safe_pos = max(i - int(fps * 1), 0)
            cap.set(cv2.CAP_PROP_POS_FRAMES, safe_pos)
            ret, frame = cap.read()

            # Lies ein paar Frames, um Decoder zu stabilisieren
            for _ in range(3):
                spinner.update()
                ret, frame = cap.read()
                if not ret:
                    break

            if not ret:
                continue

            try:
                score = self._analyze_frame(frame)
                scores.append(score)
            except Exception:
                print_err("Error analyzing frame for grain score")
                pass

            spinner.update()

        cap.release()

        if scores:
            avg_score = float(np.mean(scores))
            category = self._calculate_category(avg_score)
            self._result = GrainResult(
                category=category,
                score=avg_score,
                scores=scores
            )
            spinner.stop(f"Detected grain category: {category}, score: {avg_score:.4f}")
        else:
            spinner.stop()

    def get_result(self) -> GrainResult:
        return self._result

    def get_category_and_score(self) -> Tuple[int, float]:
        return self._result.category, self._result.score

    def get_category(self) -> int:
        return self._result.category

    def get_crf_x265_x264_adjustment(self) -> float:
        cat, score = self.get_category_and_score()
        if cat == 0:
            return 0.0
        multi: float = min(1.0, score * 10.0)
        return 3.0 * multi
