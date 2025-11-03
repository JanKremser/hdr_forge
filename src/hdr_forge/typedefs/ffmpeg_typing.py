
from dataclasses import dataclass
from typing import Optional



@dataclass
class FfmpegProgressInfo:
    """Progress information from FFmpeg encoding.

    Attributes:
        frame: Current frame number
        fps: Frames per second
        speed: Encoding speed multiplier (e.g., 1.23x)
        time: Current time in seconds
        bitrate: Current bitrate in kb/s
        size: Current output file size in bytes
    """
    frame: int = 0
    fps: float = 0.0
    speed: Optional[float] = None
    time: Optional[float] = None
    bitrate: Optional[float] = None
    size: Optional[int] = None


@dataclass
class FfmpegMiniProgressInfo:
    """Progress information for dovi_tool operations using FFmpeg pipeline.

    Attributes:
        frame: Current frame number
        fps: Frames per second
        total_frames: Total number of frames to process
    """
    frame: int = 0
    fps: float = 0.0
    total_frames: int = 0
