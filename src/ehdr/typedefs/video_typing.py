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

def build_master_display_string(md: MasterDisplayMetadata) -> str:
    return (f"G({int(md.g_x*50000)},{int(md.g_y*50000)})"
            f"B({int(md.b_x*50000)},{int(md.b_y*50000)})"
            f"R({int(md.r_x*50000)},{int(md.r_y*50000)})"
            f"WP({int(md.wp_x*50000)},{int(md.wp_y*50000)})"
            f"L({int(md.max_lum*10000)},{int(md.min_lum*10000)})")

def build_max_cll_string(cll: ContentLightLevelMetadata) -> str:
    return f"{cll.maxcll or 0},{cll.maxfall or 0}"
