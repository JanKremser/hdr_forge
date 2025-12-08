from dataclasses import dataclass
from enum import Enum

PIXEL_FORMAT_YUV420_10_BIT = 'yuv420p10le'
PIXEL_FORMAT_YUV420_8_BIT = 'yuv420p'

class HdrForgeSpeedPreset(Enum):
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    MEDIUM_PLUS = "medium:plus"
    SLOW = "slow"
    SLOW_PLUS = "slow:plus"
    SLOWER = "slower"
    VERYSLOW = "veryslow"

BT_709_FLAGS: list[str] = [
    'colorprim=bt709',
    'transfer=bt709',
    'colormatrix=bt709',
]

BT_2020_FLAGS: list[str] = [
    'colorprim=bt2020',
    'transfer=smpte2084',
    'colormatrix=bt2020nc',
]

class VideoEncoderLibrary(Enum):
    """Video encoder library for FFmpeg."""
    LIBX265 = "libx265"
    LIBX264 = "libx264"
    LIBSVTAV1 = "libsvtav1"
    HEVC_NVENC = "hevc_nvenc"
    H264_NVENC = "h264_nvenc"
    COPY = "copy"

class HEVC_NVENC_Preset(Enum):
    DEFAULT = "default"
    SLOW = "slow"
    HQ = "hq"
    LLHQ = "llhq"
    LLHP = "llhp"
    P1 = "p1" # fastest
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"
    P5 = "p5"
    P6 = "p6"
    P7 = "p7" # slowest

class x265_x264_Preset(Enum):
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"

@dataclass
class CodecPreset():
    codec_libs: list[VideoEncoderLibrary]
    codec_preset: str
    ffmpeg_params: dict[str, str | None | dict]

HDR_FORGE_SPEED_PRESET: dict[HdrForgeSpeedPreset, list[CodecPreset]] = {
    HdrForgeSpeedPreset.ULTRAFAST: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.ULTRAFAST.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P1.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.SUPERFAST: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.SUPERFAST.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P2.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.VERYFAST: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.VERYFAST.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P3.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.FASTER: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.FASTER.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P4.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.FAST:  [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.FAST.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P5.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.MEDIUM:  [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.MEDIUM.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P6.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.MEDIUM_PLUS:  [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264],
            codec_preset=x265_x264_Preset.MEDIUM.value,
            ffmpeg_params={
                'x264-params': {
                    'aq-mode': '2',
                    'ref': '4',
                    'bframes': '8',
                    'b-adapt': '2',
                    'trellis': '1',  # Kompromiss zwischen Geschwindigkeit und Qualität
                }
            },
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.MEDIUM.value,
            ffmpeg_params={
                'x265-params': {
                    'aq-mode': '2',
                    'ref': '4',
                    'bframes': '8',
                    'b-adapt': '2',
                    'rdoq-level': '1',# 8 frames slower as default 0
                    'lookahead-slices': '4',
                }
            },
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P6.value,
            ffmpeg_params={'multipass': 'fullres'},
        ),
    ],
    HdrForgeSpeedPreset.SLOW:  [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.SLOW.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P7.value,
            ffmpeg_params={},
        ),
    ],
    HdrForgeSpeedPreset.SLOW_PLUS: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264],
            codec_preset=x265_x264_Preset.SLOW.value,
            ffmpeg_params={
                'x264-params': {
                    'aq-mode': '2',
                    'ref': '4',
                    'bframes': '8',
                    'b-adapt': '2',
                    'trellis': '2',
                    'subme': '8',  # default bei slow ist 7
                    'me': 'umh',
                    'merange': '24',
                }
            },
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.SLOW.value,
            ffmpeg_params={
                'x265-params': {
                    # 'ref': '4',
                    # 'bframes': '8',
                    # 'rdoq-level': '2',

                    'aq-mode': '2',
                    'ref': '3',
                    'bframes': '4',
                    'b-adapt': '2',
                    'rdoq-level': '1', # 2-3 frame schneller bei 1, default 2
                    'subme': '2',
                    'me': 'hex',
                    'lookahead-slices': '4',
                }
            },
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P7.value,
            ffmpeg_params={
                'root': {
                    'multipass': 'fullres',
                    'aq-strength': '15',
                    'refs': '16',
                    'bf': '4',
                    'tune': 'hq',
                }
            },
        ),
    ],
    HdrForgeSpeedPreset.SLOWER: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.SLOWER.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P7.value,
            ffmpeg_params={
                'root': {
                    'multipass': 'fullres'
                }
            },
        ),
    ],
    HdrForgeSpeedPreset.VERYSLOW: [
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.LIBX264, VideoEncoderLibrary.LIBX265],
            codec_preset=x265_x264_Preset.VERYSLOW.value,
            ffmpeg_params={},
        ),
        CodecPreset(
            codec_libs=[VideoEncoderLibrary.H264_NVENC, VideoEncoderLibrary.HEVC_NVENC],
            codec_preset=HEVC_NVENC_Preset.P7.value,
            ffmpeg_params={
                'root': {
                    'multipass': 'fullres'
                }
            },
        ),
    ],
}
