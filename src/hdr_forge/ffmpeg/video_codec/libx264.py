from typing import Tuple
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrSdrFormat, X264Params, X264Tune, x265_x264_Preset
from hdr_forge.video import Video

class Libx264Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    # SDR x265 parameters
    SDR_X264_PARAMS: list[str] = [
        'colorprim=bt709',
        'transfer=bt709',
        'colormatrix=bt709',
    ]

    SDR_PIXEL_FORMAT = 'yuv420p'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            name="libx264",
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        self._crf: int = self._get_auto_crf()
        self._preset: x265_x264_Preset = self._get_auto_preset()
        self._tune: X264Tune | None = encoder_settings.x264_prams.tune

    def get_ffmpeg_params(self) -> dict:
        output_options: dict = super().get_ffmpeg_params()
        output_options.update({
            "preset": self._preset.value,
            "crf": str(self._crf),
            "pix_fmt": self.SDR_PIXEL_FORMAT,
        })

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        x264_params: list[str] = self.SDR_X264_PARAMS
        output_options['x264-params'] = ':'.join(x264_params)

        return output_options

    def get_custom_lib_parameters(self) -> dict:
        return {
            "crf": self._crf,
            "preset": self._preset.value,
            "tune": self._tune.value if self._tune else None,
        }

    def _get_auto_preset(self) -> x265_x264_Preset:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)

        TODO:
        slow bringt spürbare Vorteile, slower oder veryslow nur noch marginal — dafür viel mehr Zeit.
        """
        x264_params: X264Params = self._encoder_settings.x264_prams
        if x264_params.preset is not None:
            return x264_params.preset

        pixels = self._get_pixel_count()

        # 4K+ (4096x2160 = 8,847,360 pixels)
        if pixels >= 8_847_361:
            return x265_x264_Preset.SUPERFAST

        # 2K to 4K range
        if pixels >= 2_073_601:
            return x265_x264_Preset.FASTER

        # Full HD
        if pixels >= 2_073_600:
            return x265_x264_Preset.FAST

        # Lower resolutions
        return x265_x264_Preset.MEDIUM

    def _get_auto_crf(self) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)

        2-5 points lower than libx265 for similar quality.
        """
        x264_params: X264Params = self._encoder_settings.x264_prams
        if x264_params.crf is not None:
            return x264_params.crf

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
