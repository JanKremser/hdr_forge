
from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class DolbyVisionInfo:
    """Structure for Dolby Vision metadata information."""
    dv_profile: Optional[int] = None
    dv_level: Optional[int] = None
    rpu_present_flag: int = 0

@dataclass
class MasterDisplayMetadata:
    r_x: float
    r_y: float
    g_x: float
    g_y: float
    b_x: float
    b_y: float
    wp_x: float
    wp_y: float
    min_lum: float
    max_lum: float

@dataclass
class ContentLightLevelMetadata:
    """Structure for Content Light Level metadata information."""
    maxcll: Optional[int] = None
    maxfall: Optional[int] = None

@dataclass
class HdrMetadata:
    mastering_display_metadata: Optional[MasterDisplayMetadata] = None
    content_light_level_metadata: Optional[ContentLightLevelMetadata] = None

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

class DolbyVisionProfile(Enum):
    """Dolby Vision profile for encoding."""
    AUTO = "auto"
    _8 = "8"
