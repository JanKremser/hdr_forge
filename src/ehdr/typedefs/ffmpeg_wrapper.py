
from dataclasses import dataclass
from typing import Optional



@dataclass
class ProgressInfo:
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
