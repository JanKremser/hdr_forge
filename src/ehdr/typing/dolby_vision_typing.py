from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class DolbyVisionSiteDataInfo:
    """Structure for Dolby Vision metadata information."""
    dv_profile: Optional[int] = None
    dv_level: Optional[int] = None
    rpu_present_flag: int = 0


@dataclass
class DolbyVisionRpuInfo:
    """Structure for Dolby Vision RPU information from dovi_tool info."""
    frames: int
    profile: int
    profile_el: Optional[str]  # e.g., "FEL", "MEL", None for non-EL profiles
    dm_version: int
    cm_version: str  # e.g., "CM v2.9"
    scene_shot_count: int
    rpu_min_nits: float
    rpu_max_nits: float
    l1_max_cll: float
    l1_max_fall: float
    l6_min_nits: Optional[float] = None
    l6_max_nits: Optional[float] = None
    l6_max_cll: Optional[int] = None
    l6_max_fall: Optional[int] = None
    l5_offset_top: Optional[int] = None
    l5_offset_bottom: Optional[int] = None
    l5_offset_left: Optional[int] = None
    l5_offset_right: Optional[int] = None


class DolbyVisionProfileEncodingMode(Enum):
    """Dolby Vision profile for encoding."""
    AUTO = "auto"
    _8 = "8"

@dataclass
class DolbyVisionInfo:
    """Structure for Dolby Vision RPU information from dovi_tool info."""
    dv_profile: int
    dv_profile_el: Optional[str]
    dv_level: Optional[int]
    dm_version: int
    cm_version: str
    dv_format: str
