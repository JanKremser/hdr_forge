from dataclasses import dataclass
from enum import Enum


@dataclass
class CropHandler:
    """Datenklasse für die Ergebnisse der Crop-Analyse."""
    finish_progress: bool = False
    completed_samples: int = 0
    total_samples: int = 0


class ColorFormat(Enum):
    """Target color format for video encoding."""
    AUTO = "auto"
    SDR = "sdr"
    HDR10 = "hdr10"
    DOLBY_VISION = "dolby_vision"
