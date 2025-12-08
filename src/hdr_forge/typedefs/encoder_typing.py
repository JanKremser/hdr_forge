from dataclasses import dataclass, field
from enum import Enum
from pickle import TRUE
from typing import Optional




from hdr_forge.typedefs.codec_typing import HEVC_NVENC_Preset, HdrForgeSpeedPreset, x265_x264_Preset
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfileEncodingMode
from hdr_forge.typedefs.video_typing import HdrMetadata


class RESOLUTION_PRESETS(Enum):
    """Vordefinierte Auflösungen für die Skalierung."""
    FUHD = "FUHD"
    UHD = "UHD"
    QHD_PLUS = "QHD+"
    WQHD = "WQHD"
    FHD = "FHD"
    HD = "HD"
    QHD = "QHD"
    SD = "SD"


RESOLUTION_PRESETS_VALUES: dict[RESOLUTION_PRESETS, tuple[int, int]] = {
    RESOLUTION_PRESETS.FUHD: (7680, 4320),
    RESOLUTION_PRESETS.UHD: (3840, 2160),
    RESOLUTION_PRESETS.QHD_PLUS: (3200, 1800),
    RESOLUTION_PRESETS.WQHD: (2560, 1440),
    RESOLUTION_PRESETS.FHD: (1920, 1080),
    RESOLUTION_PRESETS.HD: (1280, 720),
    RESOLUTION_PRESETS.QHD: (960, 540),
    RESOLUTION_PRESETS.SD: (854, 480),
}


class HdrSdrFormat(Enum):
    """Target color format for video encoding."""
    AUTO = "auto"
    SDR = "sdr"
    HDR = "hdr"
    HDR10 = "hdr10"
    HDR10_PLUS = "hdr10_plus"
    DOLBY_VISION = "dolby_vision"


class VideoCodec(Enum):
    """Video encoder mode."""
    H265 = "h265"
    H264 = "h264"
    COPY = "copy"

class AudioCodec(Enum):
    """Audio codec options for encoding."""
    COPY = "copy"
    AAC = "aac"
    AC3 = "ac3"
    EAC3 = "eac3"
    OPUS = "opus"
    VORBIS = "vorbis"
    FLAC = "flac"
    MP3 = "mp3"

@dataclass
class AudioCodecItem():
    """Audio codec configuration for encoding."""
    from_codec: Optional[str | AudioCodec] = None
    to_codec: AudioCodec = AudioCodec.COPY

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


class GrainMode(Enum):
    """Grain analysis and application modes."""
    OFF = "off"
    AUTO = "auto"
    CAT1 = "cat1"
    CAT2 = "cat2"
    CAT3 = "cat3"

@dataclass
class SampleSettings:
    """Settings for processing a video sample."""
    enabled: bool = False
    start_time: Optional[float] = None  # in seconds
    end_time: Optional[float] = None    # in seconds

class X265Tune(Enum):
    ANIMATION = "animation"
    GRAIN = "grain"

@dataclass
class Libx265Params:
    preset: Optional[x265_x264_Preset] = None
    crf: Optional[int] = None
    tune: Optional[X265Tune] = None

class X264Tune(Enum):
    FILM = "film"
    ANIMATION = "animation"
    GRAIN = "grain"

@dataclass
class Libx264Params:
    preset: Optional[x265_x264_Preset] = None
    crf: Optional[int] = None
    tune: Optional[X264Tune] = None

class NvencRcMode(Enum):
    """NVENC rate control modes."""
    VBR = "vbr"
    VBR_HQ = "vbr_hq"
    CBR = "cbr"
    CQP = "cqp"

@dataclass
class NvencParams:
    """NVENC encoder parameters."""
    preset: Optional[HEVC_NVENC_Preset] = None
    cq: Optional[int] = None
    rc: Optional[NvencRcMode] = None

@dataclass
class UniversalEncoderParams:
    """Universal encoder parameters that work across all encoders."""
    quality: Optional[int] = None  # Maps to CRF/CQ depending on encoder
    speed: Optional[HdrForgeSpeedPreset] = None  # Only for libx265/libx264, not NVENC

class EncoderOverride(Enum):
    """Encoder override for manual encoder selection."""
    AUTO = "auto"
    LIBX265 = "x265"
    LIBX264 = "x264"
    LIBSVTAV1 = "libsvtav1"
    HEVC_NVENC = "hevc_nvenc"
    H264_NVENC = "h264_nvenc"

class HdrForgeEncodingTuningPresets(Enum):
    VIDEO = "video"
    FILM = "film"
    BANDING = "banding"
    ACTION = "action"
    ANIMATION = "animation"
    GRAIN = "grain"
    GRAIN_FFMPEG = "grain:ffmpeg"
    FILM4K = "film4k"
    FILM4K_FAST = "film4k:fast"

class HdrForgeEncodingHardwarePresets(Enum):
    # Prefixed presets (explicit hardware specification)
    CPU_BALANCED = "cpu:balanced"
    CPU_QUALITY = "cpu:quality"
    GPU_BALANCED = "gpu:balanced"
    GPU_QUALITY = "gpu:quality"
    # Prefix-free presets (hardware derived from encoder)
    BALANCED = "balanced"
    QUALITY = "quality"

class LogoRemovalAutoDetectMode(Enum):
    AUTO = "auto"
    AUTO_TOP_LEFT = "auto-top-left"
    AUTO_TOP_RIGHT = "auto-top-right"
    AUTO_BOT_LEFT = "auto-bot-left"
    AUTO_BOT_RIGHT = "auto-bot-right"

class LogoRemovalMode(Enum):
    OFF = "off"
    DELOGO = "delogo"
    MASK = "mask"

@dataclass
class LogoRemovelSettings:
    """Settings for logo removal from video."""
    mode: LogoRemovalMode = LogoRemovalMode.OFF
    position: LogoRemovalAutoDetectMode = LogoRemovalAutoDetectMode.AUTO
    #mask_file: Optional[Path] = None  # Path to custom mask file for logo removal

@dataclass
class HdrForgeEncodingPresetSettings:
    preset: HdrForgeEncodingTuningPresets = HdrForgeEncodingTuningPresets.FILM
    hardware_preset: HdrForgeEncodingHardwarePresets = HdrForgeEncodingHardwarePresets.CPU_BALANCED

@dataclass
class EncoderSettings:
    """Container for all video encoding settings.

    This dataclass encapsulates all parameters needed for video encoding,
    making it easier to pass configuration to the convert_video function.
    """
    video_codec: VideoCodec = VideoCodec.H265
    audio_codecs: dict[str, AudioCodecItem] = field(default_factory=lambda: {}) # { lang or track id: AudioCodecItem }

    # Video filter settings
    vfilter: Optional[str] = None
    dar_ratio: Optional[tuple[int, int]] = None  # Display Aspect Ratio (width, height)

    # General encoding settings
    hdr_forge_encoding_preset: HdrForgeEncodingPresetSettings = field(
        default_factory=lambda: HdrForgeEncodingPresetSettings()
    )
    enable_gpu_acceleration: bool = False
    hdr_sdr_format: HdrSdrFormat = HdrSdrFormat.AUTO
    hdr_metadata: HdrMetadata = field(default_factory=HdrMetadata)
    target_dv_profile: DolbyVisionProfileEncodingMode = DolbyVisionProfileEncodingMode.AUTO

    # Encoder-specific parameters
    libx265_params: Libx265Params = field(default_factory=Libx265Params)
    libx264_params: Libx264Params = field(default_factory=Libx264Params)
    nvenc_params: NvencParams = field(default_factory=NvencParams)

    # Universal parameters and encoder override
    universal_params: UniversalEncoderParams = field(default_factory=UniversalEncoderParams)
    encoder_override: EncoderOverride = EncoderOverride.AUTO

    crop: CropSettings = field(default_factory=lambda: CropSettings(mode=CropMode.AUTO))
    grain: GrainMode = GrainMode.OFF
    logo_removal: LogoRemovelSettings = field(default_factory=lambda: LogoRemovelSettings())

    scale_height: Optional[int] = None
    scale_mode: ScaleMode = ScaleMode.HEIGHT
    sample: SampleSettings = field(default_factory=lambda: SampleSettings(enabled=False))

    threads: Optional[int] = None  # Number of threads to use for encoding (None for auto)
