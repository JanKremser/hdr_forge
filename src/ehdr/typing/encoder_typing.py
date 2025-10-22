from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ehdr.typing.dolby_vision_typing import DolbyVisionProfileEncodingMode


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
    COPY = "copy"


class VideoEncoderLibrary(Enum):
    """Video encoder library for FFmpeg."""
    LIBX265 = "libx265"
    COPY = "copy"


@dataclass
class EncoderSettings:
    """Container for all video encoding settings.

    This dataclass encapsulates all parameters needed for video encoding,
    making it easier to pass configuration to the convert_video function.

    Attributes:
        video_encoder: VideoEncoder enum specifying the encoder to use
        target_format: Target color format (AUTO, SDR, HDR10, DOLBY_VISION)
        target_dv_profile: Dolby Vision profile for encoding (AUTO or 8)
        crf: Constant Rate Factor for quality control (lower = better quality)
        preset: x265 encoding preset (slower = better compression)
        scale_height: Target height for video scaling (downscaling only)
        enable_crop: Enable automatic black bar detection and cropping
    """
    video_codec: VideoCodec = VideoCodec.X265
    hdr_sdr_format: HdrSdrFormat = HdrSdrFormat.AUTO
    target_dv_profile: DolbyVisionProfileEncodingMode = DolbyVisionProfileEncodingMode.AUTO
    crf: Optional[int] = None
    preset: Optional[str] = None
    scale_height: Optional[int] = None
    enable_crop: bool = False
