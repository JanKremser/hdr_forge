from typing import Tuple
from ehdr.cli.cli_output import print_err
from ehdr.ffmpeg.base import CodecBase
from ehdr.typedefs.encoder_typing import EncoderSettings, HdrSdrFormat
from ehdr.video import Video

class Libx264Codec(CodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            name="libx264",
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        self._crf: int = encoder_settings.crf if encoder_settings.crf is not None else self._get_auto_crf()
        self._preset: str = encoder_settings.preset if encoder_settings.preset is not None else self._get_auto_preset()

    def get_ffmpeg_params(self) -> dict:
        return {
            "c:v": self.name,
            "preset": self._preset,
            "crf": str(self._crf)
        }

    def get_custom_lib_parameters(self) -> dict:
        return {
            "crf": self._crf,
            "preset": self._preset,
        }

    def _get_auto_preset(self) -> str:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)
        """
        pixels = self._get_pixel_count()

        # 4K+ (4096x2160 = 8,847,360 pixels)
        if pixels >= 8_847_361:
            return 'superfast'

        # 2K to 4K range
        if pixels >= 2_073_601:
            return 'faster'

        # Full HD
        if pixels >= 2_073_600:
            return 'fast'

        # Lower resolutions
        return 'medium'

    def _get_auto_crf(self) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)

        5 points lower than libx265 for similar quality.
        """
        pixels = self._get_pixel_count()

        # UHD 4K (3840x2160 = 8,294,400 pixels)
        if pixels >= 6_144_000:
            return 8

        # 2K to 4K range - scale linearly
        if pixels >= 2_211_841:
            # Linear interpolation between 9 (at 6.14M) and 13 (at 2.21M)
            ratio = (pixels - 2_211_841) / (6_144_000 - 2_211_841)
            return int(13 - (4 * ratio))

        # Full HD (1920x1080 = 2,073,600 pixels)
        if pixels >= 2_073_600:
            return 13

        # Lower resolutions
        if pixels >= 1_000_000:
            return 14

        return 15
