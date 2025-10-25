from dataclasses import dataclass
from enum import Enum

from hdr_forge.typedefs.encoder_typing import HdrForgeEncodingHardwarePresets, VideoEncoderLibrary


@dataclass
class Hdr_Forge_X265_X264_Preset:
    crf: float
    preset: str

X265_X264_PRESET_SCALE: list[str] = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]


class RESOLUTION_PRESETS(Enum):
    """Vordefinierte Auflösungen für die Skalierung."""
    _8K = 7680 * 4320
    UHD = 3840 * 2160
    QHD = 2560 * 1440
    FHD = 1920 * 1080
    HD = 1280 * 720
    SD = 854 * 480
    NONE = 0

"""
CRF x265 to x264: 2-5 points lower than libx265 for similar quality.

bei x265 ist CRF 13 fast schon „visually lossless“.
"""
HW_PRESET: dict = {
    HdrForgeEncodingHardwarePresets.CPU_BALANCED: [
        {
            "from_pixel": RESOLUTION_PRESETS.NONE.value,
            "to_pixel": RESOLUTION_PRESETS.HD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 22, "to_CRF": 20, "from_preset": "fast", "to_preset": "medium"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 20, "to_CRF": 18, "from_preset": "fast", "to_preset": "medium"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.HD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 20, "to_CRF": 19, "from_preset": "medium", "to_preset": "medium"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 18, "to_CRF": 17, "from_preset": "medium", "to_preset": "medium"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.FHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.UHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 19, "to_CRF": 15, "from_preset": "medium", "to_preset": "fast"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 17, "to_CRF": 14, "from_preset": "medium", "to_preset": "fast"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.UHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS._8K.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 15, "to_CRF": 13, "from_preset": "faster", "to_preset": "ultrafast"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 14, "to_CRF": 12, "from_preset": "faster", "to_preset": "ultrafast"}
        },
    ],
    HdrForgeEncodingHardwarePresets.CPU_QUALITY: [
        {
            "from_pixel": RESOLUTION_PRESETS.NONE.value,
            "to_pixel": RESOLUTION_PRESETS.HD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 20, "to_CRF": 19, "from_preset": "faster", "to_preset": "fast"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 18, "to_CRF": 17, "from_preset": "faster", "to_preset": "fast"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.HD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 19, "to_CRF": 17.5, "from_preset": "medium", "to_preset": "medium"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 17, "to_CRF": 16, "from_preset": "medium", "to_preset": "medium"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.FHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.UHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 17.5, "to_CRF": 15, "from_preset": "medium", "to_preset": "slow"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 16, "to_CRF": 14, "from_preset": "medium", "to_preset": "slow"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.UHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS._8K.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 14, "to_CRF": 11, "from_preset": "slower", "to_preset": "veryslow"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 13, "to_CRF": 11, "from_preset": "slower", "to_preset": "veryslow"}
        },
    ]
}

def interpolate(value, x1, x2, y1, y2):
    """Lineare Interpolation"""
    if x1 == x2:
        return y1
    return y1 + (value - x1) * (y2 - y1) / (x2 - x1)


def interpolate_preset(value, x1, x2, from_preset, to_preset):
    """Interpoliert das Preset basierend auf PRESET_SCALE."""
    if from_preset == to_preset:
        return from_preset
    i1 = X265_X264_PRESET_SCALE.index(from_preset)
    i2 = X265_X264_PRESET_SCALE.index(to_preset)
    val = interpolate(value, x1, x2, i1, i2)
    return X265_X264_PRESET_SCALE[round(val)]


def calc_hw_prest_params(
    pixels,
    hw_preset: HdrForgeEncodingHardwarePresets = HdrForgeEncodingHardwarePresets.CPU_BALANCED,
    lib: VideoEncoderLibrary = VideoEncoderLibrary.LIBX265,
) -> dict:
    ranges = HW_PRESET.get(hw_preset, [])
    for r in ranges:
        if r["from_pixel"] <= pixels <= r["to_pixel"]:
            # x265
            from_crf = r[lib]["from_CRF"]
            to_crf = r[lib]["to_CRF"]
            crf = round(interpolate(pixels, r["from_pixel"], r["to_pixel"], from_crf, to_crf), 2)
            preset = interpolate_preset(
                pixels, r["from_pixel"], r["to_pixel"],
                r[lib]["from_preset"], r[lib]["to_preset"]
            )

            return {"crf": crf, "preset": preset}

    # Fallback
    return {}
