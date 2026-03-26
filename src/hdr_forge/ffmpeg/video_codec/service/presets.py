from dataclasses import dataclass
from enum import Enum

from hdr_forge.typedefs.encoder_typing import HdrForgeEncodingHardwarePresets, HdrForgeSpeedPreset
from hdr_forge.typedefs.codec_typing import VideoEncoderLibrary


@dataclass
class Hdr_Forge_X265_X264_Preset:
    crf: float
    preset: HdrForgeSpeedPreset

@dataclass
class Hdr_Forge_HEVC_H264_NVENC_Preset:
    cq: float
    preset: HdrForgeSpeedPreset

@dataclass
class Hdr_Forge_AV1_Preset:
    crf: float
    preset: int

SPEED_PRESET_SCALE: list[str] = [
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "medium:plus",
    "slow:plus",
    "slow",
    "slower",
    "veryslow",
]

class RESOLUTION_PRESETS(Enum):
    """Predefined resolutions for scaling."""
    FUHD = 7680 * 4320
    UHD = 3840 * 2160
    QHD_PLUS = 3200 * 1800
    WQHD = 2560 * 1440
    FHD = 1920 * 1080
    HD = 1280 * 720
    QHD = 960 * 540
    SD = 854 * 480
    NONE = 0

"""
CRF x265 to x264: 2-5 points lower than libx265 for similar quality.

For x265, CRF 13 is almost "visually lossless".
"""
HW_PRESET: dict = {
    HdrForgeEncodingHardwarePresets.CPU_BALANCED: [
        {
            "from_pixel": RESOLUTION_PRESETS.NONE.value,
            "to_pixel": RESOLUTION_PRESETS.HD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 22, "to_CRF": 19, "from_preset": "slow", "to_preset": "medium:plus"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 20, "to_CRF": 17, "from_preset": "slow", "to_preset": "medium:plus"},
            VideoEncoderLibrary.LIBSVTAV1: {"from_CRF": 25, "to_CRF": 23, "from_preset": 5, "to_preset": 5},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.HD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 19, "to_CRF": 18, "from_preset": "medium:plus", "to_preset": "medium"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 17, "to_CRF": 16, "from_preset": "medium:plus", "to_preset": "medium"},
            VideoEncoderLibrary.LIBSVTAV1: {"from_CRF": 23, "to_CRF": 22, "from_preset": 4, "to_preset": 4},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.FHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.WQHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 18, "to_CRF": 17, "from_preset": "medium", "to_preset": "medium"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 16, "to_CRF": 16, "from_preset": "medium", "to_preset": "medium"},
            VideoEncoderLibrary.LIBSVTAV1: {"from_CRF": 23, "to_CRF": 23, "from_preset": 6, "to_preset": 6},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.WQHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.UHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 17, "to_CRF": 13, "from_preset": "fast", "to_preset": "fast"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 16, "to_CRF": 12, "from_preset": "fast", "to_preset": "fast"},
            VideoEncoderLibrary.LIBSVTAV1: {"from_CRF": 21, "to_CRF": 18, "from_preset": 6, "to_preset": 6},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.UHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FUHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 13, "to_CRF": 13, "from_preset": "faster", "to_preset": "ultrafast"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 12, "to_CRF": 12, "from_preset": "faster", "to_preset": "ultrafast"},
            VideoEncoderLibrary.LIBSVTAV1: {"from_CRF": 18, "to_CRF": 16, "from_preset": 6, "to_preset": 6},
        },
    ],
    HdrForgeEncodingHardwarePresets.CPU_QUALITY: [
        {
            "from_pixel": RESOLUTION_PRESETS.NONE.value,
            "to_pixel": RESOLUTION_PRESETS.HD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 20, "to_CRF": 19, "from_preset": "slower", "to_preset": "slow"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 18, "to_CRF": 17, "from_preset": "slower", "to_preset": "slow"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.HD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 19, "to_CRF": 16, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 17, "to_CRF": 15, "from_preset": "slow", "to_preset": "slow"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.FHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.UHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 16, "to_CRF": 14, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 15, "to_CRF": 14, "from_preset": "slow", "to_preset": "slow"}
        },
        {
            "from_pixel": RESOLUTION_PRESETS.UHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FUHD.value,
            VideoEncoderLibrary.LIBX265: {"from_CRF": 13, "to_CRF": 13, "from_preset": "slower", "to_preset": "veryslow"},
            VideoEncoderLibrary.LIBX264: {"from_CRF": 13, "to_CRF": 12, "from_preset": "slower", "to_preset": "veryslow"}
        },
    ],
    HdrForgeEncodingHardwarePresets.GPU_BALANCED: [
        {
            "from_pixel": RESOLUTION_PRESETS.NONE.value,
            "to_pixel": RESOLUTION_PRESETS.HD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 22, "to_CQ": 20, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 20, "to_CQ": 18, "from_preset": "slow", "to_preset": "slow"},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.HD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FHD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 20, "to_CQ": 19, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 18, "to_CQ": 17, "from_preset": "slow", "to_preset": "slow"},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.FHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.UHD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 19, "to_CQ": 15, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 17, "to_CQ": 14, "from_preset": "slow", "to_preset": "slow"},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.UHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FUHD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 15, "to_CQ": 13, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 14, "to_CQ": 12, "from_preset": "slow", "to_preset": "slow"},
        },
    ],
    HdrForgeEncodingHardwarePresets.GPU_QUALITY: [
        {
            "from_pixel": RESOLUTION_PRESETS.NONE.value,
            "to_pixel": RESOLUTION_PRESETS.HD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 22, "to_CQ": 20, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 20, "to_CQ": 18, "from_preset": "slow", "to_preset": "slow"},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.HD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FHD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 20, "to_CQ": 19, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 18, "to_CQ": 17, "from_preset": "slow", "to_preset": "slow"},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.FHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.UHD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 19, "to_CQ": 15, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 17, "to_CQ": 14, "from_preset": "slow", "to_preset": "slow"},
        },
        {
            "from_pixel": RESOLUTION_PRESETS.UHD.value + 1,
            "to_pixel": RESOLUTION_PRESETS.FUHD.value,
            VideoEncoderLibrary.HEVC_NVENC: {"from_CQ": 15, "to_CQ": 13, "from_preset": "slow", "to_preset": "slow"},
            VideoEncoderLibrary.H264_NVENC: {"from_CQ": 14, "to_CQ": 12, "from_preset": "slow", "to_preset": "slow"},
        },
    ],
}

def interpolate(value, x1, x2, y1, y2):
    """Linear interpolation"""
    if x1 == x2:
        return y1
    return y1 + (value - x1) * (y2 - y1) / (x2 - x1)


def interpolate_preset(value, x1, x2, from_preset, to_preset):
    """Interpolates the preset based on PRESET_SCALE."""
    if from_preset == to_preset:
        return from_preset
    i1 = SPEED_PRESET_SCALE.index(from_preset)
    i2 = SPEED_PRESET_SCALE.index(to_preset)
    val = interpolate(value, x1, x2, i1, i2)
    return SPEED_PRESET_SCALE[round(val)]

def calc_hw_prest_params(
    pixels,
    hw_preset: HdrForgeEncodingHardwarePresets = HdrForgeEncodingHardwarePresets.CPU_BALANCED,
    lib: VideoEncoderLibrary = VideoEncoderLibrary.LIBX265,
) -> dict:
    ranges = HW_PRESET.get(hw_preset, [])
    for r in ranges:
        if r["from_pixel"] <= pixels <= r["to_pixel"]:
            params: dict = {}

            if lib in [VideoEncoderLibrary.LIBX265, VideoEncoderLibrary.LIBX264]:
                from_crf = r[lib]["from_CRF"]
                to_crf = r[lib]["to_CRF"]
                crf = round(interpolate(
                    pixels,
                    r["from_pixel"],
                    r["to_pixel"],
                    from_crf,
                    to_crf
                ), 2)
                params["crf"] = crf
                preset = interpolate_preset(
                    pixels, r["from_pixel"], r["to_pixel"],
                    r[lib]["from_preset"], r[lib]["to_preset"]
                )
                params["preset"] = HdrForgeSpeedPreset(preset)

            if lib == VideoEncoderLibrary.LIBSVTAV1:
                from_crf = r[lib]["from_CRF"]
                to_crf = r[lib]["to_CRF"]
                crf = round(interpolate(
                    pixels,
                    r["from_pixel"],
                    r["to_pixel"],
                    from_crf,
                    to_crf
                ), 2)
                params["crf"] = crf
                preset = round(interpolate(
                    pixels,
                    r["from_pixel"],
                    r["to_pixel"],
                    r[lib]["from_preset"],
                    r[lib]["to_preset"]
                ))
                params["preset"] = preset

            if lib in [VideoEncoderLibrary.HEVC_NVENC, VideoEncoderLibrary.H264_NVENC]:
                from_cq = r[lib]["from_CQ"]
                to_cq = r[lib]["to_CQ"]
                cq = round(interpolate(
                    pixels,
                    r["from_pixel"],
                    r["to_pixel"],
                    from_cq,
                    to_cq
                ), 2)
                params["cq"] = cq
                preset = interpolate_preset(
                    pixels, r["from_pixel"], r["to_pixel"],
                    r[lib]["from_preset"], r[lib]["to_preset"]
                )
                params["preset"] = HdrForgeSpeedPreset(preset)


            return params

    # Fallback
    return {}
