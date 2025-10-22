from dataclasses import dataclass
from typing import Optional


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
