from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary, X264Params, X264Tune, x265_x264_Preset
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
            lib=VideoEncoderLibrary.LIBX264,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_X265_X264_Preset = self.calc_hw_preset_settings(Hdr_Forge_X265_X264_Preset)
        self._crf: int = self._get_auto_crf(hw_preset)
        self._preset: x265_x264_Preset = self._get_auto_preset(hw_preset)
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

    def _get_auto_tune(self) -> Optional[X264Tune]:
        """Select optimal encoding tune based on content.

        Returns:
            X265Tune enum or None if no tune is set
        """
        x265_params: X264Params = self._encoder_settings.x264_prams
        if x265_params.tune is not None:
            return x265_params.tune

        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingPresets.ANIMATION:
            return X264Tune.ANIMATION
        elif hdr_forge_preset == HdrForgeEncodingPresets.FILM:
            return X264Tune.FILM

        if self._grain.get_category() >= 2:
            return X264Tune.GRAIN

        return None

    def _get_auto_preset(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> x265_x264_Preset:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)

        TODO:
        slow bringt spürbare Vorteile, slower oder veryslow nur noch marginal — dafür viel mehr Zeit.
        """
        x264_params: X264Params = self._encoder_settings.x264_prams
        if x264_params.preset is not None:
            return x264_params.preset

        preset = hw_preset.preset
        return x265_x264_Preset(preset)

    def _get_auto_crf(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)
        """
        x264_params: X264Params = self._encoder_settings.x264_prams
        if x264_params.crf is not None:
            return x264_params.crf

        crf: float = hw_preset.crf

        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion

        action_w: float = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=action_crf,
        )
        crf -= action_crf * action_w

        grain_crf: float = self._grain.get_crf_x265_x264_adjustment()
        grain_w: float = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=grain_crf,
        )
        crf -= grain_crf * grain_w

        return round(crf)
