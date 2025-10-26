import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from hdr_forge.cli.cli_output import ProgressBarSpinner
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
        duration_sec: int | None = 5,
        sample_rate: float | None = 1,
        resize_width: int | None = 640
    ):
        self._video: Video = video
        self._duration_sec: int = duration_sec or 5
        self._sample_rate: float = sample_rate or 1
        self._resize_width: int = resize_width or 640
        self._result: GrainResult = GrainResult()

    def _analyze_frame(self, frame: np.ndarray) -> float:
        h, w = frame.shape[:2]
        scale = self._resize_width / w
        frame_small = cv2.resize(frame, (self._resize_width, int(h*scale)))

        gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        highpass = gray.astype(np.float32) - blur.astype(np.float32)

        return float(np.std(highpass) / 255.0)

    def _calculate_category(self, avg_score: float) -> int:
        if avg_score < 0.01:
            return 0
        elif avg_score < 0.02:
            return 1
        elif avg_score < 0.03:
            return 2
        return 3

    def analyze(self) -> None:
        cap = cv2.VideoCapture(str(self._video._filepath))
        if not cap.isOpened():
            raise RuntimeError("Video cannot be opened")

        fps = self._video.get_fps()
        total_frames = int(min(self._duration_sec * fps, self._video.get_total_frames()))
        sample_interval = max(int(fps * self._sample_rate), 1)

        scores: List[float] = []
        spinner = ProgressBarSpinner("Analyzing grain...")
        spinner.start()

        for i in range(0, total_frames, sample_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                break

            score = self._analyze_frame(frame)
            scores.append(score)
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
            spinner.stop(f"Detected grain category: {category}")
        else:
            spinner.stop()

    def get_result(self) -> GrainResult:
        return self._result

    def get_category_and_score(self) -> Tuple[int, float]:
        return self._result.category, self._result.score
