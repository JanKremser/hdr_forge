from abc import ABC, abstractmethod
import sys
from typing import Tuple

from ehdr.cli.cli_output import print_err, print_warn
from ehdr.typedefs.encoder_typing import EncoderSettings, HdrSdrFormat
from ehdr.video import Video

class CodecBase(ABC):

    def __init__(
        self,
        name: str,
        encoder_settings: EncoderSettings,
        video: Video,
        scale: Tuple[int, int],
        supported_hdr_sdr_formats: list[HdrSdrFormat] = [],
    ):
        self.name = name
        self._video = video
        self._scale = scale
        self._supported_hdr_sdr_formats: list[HdrSdrFormat] = supported_hdr_sdr_formats

        self._hdr_sdr_format_for_encoding = self._get_hdr_sdr_format_for_encoding(
            hdr_sdr_format=encoder_settings.hdr_sdr_format
        )
        if self._hdr_sdr_format_for_encoding not in supported_hdr_sdr_formats:
            print_err(f"{self.name} does not support the selected {encoder_settings.hdr_sdr_format}-format for encoding.")
            sys.exit(1)


    @abstractmethod
    def get_ffmpeg_params(self) -> dict:
        """Get FFmpeg parameters for this codec."""
        pass

    @abstractmethod
    def get_custom_lib_parameters(self) -> dict:
        """Get custom parameters specific to the codec library."""
        pass

    def get_name(self) -> str:
        return self.name

    def get_encoding_hdr_sdr_format(self) -> HdrSdrFormat:
        """Get the effective color format used for encoding.

        Returns:
            HdrSdrFormat used for encoding
        """
        return self._hdr_sdr_format_for_encoding

    def __str__(self):
        return f"{self.__class__.__name__}({self.name})"

    def _get_pixel_count(self) -> int:
        """Get total pixel count considering scale and crop.

        Returns:
            Total number of pixels for encoding
        """
        return self._scale[0] * self._scale[1]

    def _get_hdr_sdr_format_for_encoding(self, hdr_sdr_format: HdrSdrFormat) -> HdrSdrFormat:
        """Determine the effective color format based on target and source.

        Only downgrades are allowed (DV→HDR10→SDR). Upgrades are not possible.

        Returns:
            Effective ColorFormat to use for encoding
        """
        # Determine source format
        if self._video.is_dolby_vision_video():
            source_format = HdrSdrFormat.DOLBY_VISION
        elif self._video.is_hdr_video():
            source_format = HdrSdrFormat.HDR10
        else:
            source_format = HdrSdrFormat.SDR

        if hdr_sdr_format == HdrSdrFormat.AUTO:
            # Auto mode: keep source format
            return source_format

        # Check if conversion is valid (only downgrades allowed)
        format_hierarchy = {
            HdrSdrFormat.SDR: 0,
            HdrSdrFormat.HDR10: 1,
            HdrSdrFormat.DOLBY_VISION: 2
        }

        source_level = format_hierarchy[source_format]
        target_level = format_hierarchy[hdr_sdr_format]

        if target_level > source_level:
            print_warn(f"Warning: Cannot upgrade from {source_format.value} to {hdr_sdr_format.value}. Keeping source format.")
            return source_format

        # Valid downgrade
        return hdr_sdr_format
