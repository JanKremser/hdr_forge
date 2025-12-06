from dataclasses import dataclass
from enum import Enum
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

D65_WHITEPOINT: tuple[float, float] = (0.3127, 0.3290)

DISPLAY_P3_MASTER_DISPLAY: MasterDisplayMetadata = MasterDisplayMetadata(
    r_x=0.680,
    r_y=0.320,
    g_x=0.265,
    g_y=0.690,
    b_x=0.150,
    b_y=0.060,
    wp_x=D65_WHITEPOINT[0],
    wp_y=D65_WHITEPOINT[1],
    min_lum=0.0,
    max_lum=0.0,
)

BT_2020_MASTER_DISPLAY: MasterDisplayMetadata = MasterDisplayMetadata(
    r_x=0.708,
    r_y=0.292,
    g_x=0.170,
    g_y=0.797,
    b_x=0.131,
    b_y=0.046,
    wp_x=D65_WHITEPOINT[0],
    wp_y=D65_WHITEPOINT[1],
    min_lum=0.0,
    max_lum=0.0,
)

BT_709_MASTER_DISPLAY: MasterDisplayMetadata = MasterDisplayMetadata(
    r_x=0.640,
    r_y=0.330,
    g_x=0.300,
    g_y=0.600,
    b_x=0.150,
    b_y=0.060,
    wp_x=D65_WHITEPOINT[0],
    wp_y=D65_WHITEPOINT[1],
    min_lum=0.0,
    max_lum=0.0,
)

class MasterDisplayColorPrimaries(Enum):
    BT709 = "BT.709"
    BT2020 = "BT.2020"
    DISPLAY_P3 = "DisplayP3"

MASTER_DISPLAY_PRESETS: dict[MasterDisplayColorPrimaries, MasterDisplayMetadata] = {
    MasterDisplayColorPrimaries.BT709: BT_709_MASTER_DISPLAY,
    MasterDisplayColorPrimaries.DISPLAY_P3: DISPLAY_P3_MASTER_DISPLAY,
    MasterDisplayColorPrimaries.BT2020: BT_2020_MASTER_DISPLAY,
}

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
