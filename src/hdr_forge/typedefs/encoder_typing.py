from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfileEncodingMode
from hdr_forge.typedefs.video_typing import HdrMetadata


class RESOLUTION_PRESETS(Enum):
    """Vordefinierte Auflösungen für die Skalierung."""
    K8 = "8K"
    UHD = "UHD"
    QHD = "QHD"
    FHD = "FHD"
    HD = "HD"
    SD = "SD"


RESOLUTION_PRESETS_VALUES: dict[RESOLUTION_PRESETS, tuple[int, int]] = {
    RESOLUTION_PRESETS.K8: (7680, 4320),
    RESOLUTION_PRESETS.UHD: (3840, 2160),
    RESOLUTION_PRESETS.QHD: (2560, 1440),
    RESOLUTION_PRESETS.FHD: (1920, 1080),
    RESOLUTION_PRESETS.HD: (1280, 720),
    RESOLUTION_PRESETS.SD: (854, 480),
}


@dataclass
class CropHandler:
    """Datenklasse für die Ergebnisse der Crop-Analyse."""
    finish_progress: bool = False
    completed_samples: int = 0
    total_samples: int = 0


class HdrSdrFormat(Enum):
    """Target color format for video encoding."""
    AUTO = "auto"
    SDR = "sdr"
    HDR10 = "hdr10"
    DOLBY_VISION = "dolby_vision"


class VideoCodec(Enum):
    """Video encoder mode."""
    X265 = "x265"
    X264 = "x264"
    COPY = "copy"


class VideoEncoderLibrary(Enum):
    """Video encoder library for FFmpeg."""
    LIBX265 = "libx265"
    LIBX264 = "libx264"
    COPY = "copy"

class ScaleMode(Enum):
    """Scaling mode for video resizing after cropping."""
    ADAPTIVE = "adaptive"
    HEIGHT = "height"


class CropMode(Enum):
    """Crop mode for black bar detection."""
    AUTO = "auto"
    OFF = "off"
    MANUAL = "manual"
    RATIO = "ratio"

@dataclass
class CropSettings:
    """Settings for cropping black bars from video."""
    mode: CropMode = CropMode.AUTO
    manual_crop: Optional[tuple[int, int, int, int]] = None  # x, y, width, height
    ratio: Optional[tuple[float, float]] = None # Aspect ratio for RATIO mode
    check_samples: int = 10  # Number of samples to analyze for auto crop detection


@dataclass
class SampleSettings:
    """Settings for processing a video sample."""
    enabled: bool = False
    start_time: Optional[float] = None  # in seconds
    end_time: Optional[float] = None    # in seconds

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

class X265Tune(Enum):
    ANIMATION = "animation"
    GRAIN = "grain"

@dataclass
class X265Params:
    preset: Optional[x265_x264_Preset] = None
    crf: Optional[int] = None
    tune: Optional[X265Tune] = None

class X264Tune(Enum):
    FILM = "film"
    ANIMATION = "animation"
    GRAIN = "grain"

@dataclass
class X264Params:
    preset: Optional[x265_x264_Preset] = None
    crf: Optional[int] = None
    tune: Optional[X264Tune] = None

class HdrForgeEncodingPresets(Enum):
    AUTO = "auto"
    FILM = "film"
    ACTION = "action"
    ANIMATION = "animation"

class HdrForgeEncodingHardwarePresets(Enum):
    CPU_BALANCED = "cpu:balanced"
    CPU_OPTIMIZED = "cpu:opt"
    CPU_QUALITY = "cpu:quality"
    CPU_BEST = "cpu:best"

@dataclass
class HdrForgeEncodingPresetSettings:
    preset: HdrForgeEncodingPresets = HdrForgeEncodingPresets.AUTO
    hardware_preset: HdrForgeEncodingHardwarePresets = HdrForgeEncodingHardwarePresets.CPU_BALANCED

@dataclass
class EncoderSettings:
    """Container for all video encoding settings.

    This dataclass encapsulates all parameters needed for video encoding,
    making it easier to pass configuration to the convert_video function.

    Attributes:
        video_encoder: VideoEncoder enum specifying the encoder to use
        target_format: Target color format (AUTO, SDR, HDR10, DOLBY_VISION)
        target_dv_profile: Dolby Vision profile for encoding (AUTO or 8)
        scale_height: Target height for video scaling (downscaling only)
        crop: CropSettings object defining cropping behavior
    """
    video_codec: VideoCodec = VideoCodec.X265
    hdr_forge_encoding_preset: HdrForgeEncodingPresetSettings = field(
        default_factory=lambda: HdrForgeEncodingPresetSettings()
    )
    hdr_sdr_format: HdrSdrFormat = HdrSdrFormat.AUTO
    hdr_metadata: HdrMetadata = field(default_factory=HdrMetadata)
    target_dv_profile: DolbyVisionProfileEncodingMode = DolbyVisionProfileEncodingMode.AUTO

    x265_prams: X265Params = field(default_factory=X265Params)
    x264_prams: X264Params = field(default_factory=X264Params)
    crop: CropSettings = field(default_factory=lambda: CropSettings(mode=CropMode.AUTO))

    scale_height: Optional[int] = None
    scale_mode: ScaleMode = ScaleMode.HEIGHT
    sample: SampleSettings = field(default_factory=lambda: SampleSettings(enabled=False))
