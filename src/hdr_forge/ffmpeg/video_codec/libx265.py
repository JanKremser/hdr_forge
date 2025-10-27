from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary, X265Params, X265Tune, x265_x264_Preset
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.video import Video

class Libx265Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.HDR10,
        HdrSdrFormat.SDR,
        HdrSdrFormat.DOLBY_VISION,
    ]

    # HDR x265 parameters for HDR10 encoding
    HDR_X265_PARAMS: list[str] = [
        'profile=main10',
        'hdr-opt=1',
        'repeat-headers=1',
        'colorprim=bt2020',
        'transfer=smpte2084',
        'colormatrix=bt2020nc',
    ]

    # SDR x265 parameters
    SDR_X265_PARAMS: list[str] = [
        'profile=main',
        'colorprim=bt709',
        'transfer=bt709',
        'colormatrix=bt709',
        'no-hdr10-opt=1',
    ]

    HDR_PIXEL_FORMAT = 'yuv420p10le'
    SDR_PIXEL_FORMAT = 'yuv420p'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.LIBX265,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_X265_X264_Preset = self.calc_hw_preset_settings(Hdr_Forge_X265_X264_Preset)
        self._crf: int = self._get_auto_crf(hw_preset)
        self._preset: x265_x264_Preset = self._get_auto_preset(hw_preset)
        self._tune: X265Tune | None = self._get_auto_tune()

    def get_ffmpeg_params(self) -> dict:
        output_options: dict = super().get_ffmpeg_params()
        output_options.update({
            "preset": self._preset.value,
            "crf": str(self._crf)
        })

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            x265_params: list[str] = self._build_hdr_x265_params()
            output_options['pix_fmt'] = self.HDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            x265_params: list[str] = self._build_sdr_x265_params()
            output_options['pix_fmt'] = self.SDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)

        return output_options

    def get_custom_lib_parameters(self) -> dict:
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "crf": self._crf,
            "preset": self._preset.value,
            "tune": self._tune.value if self._tune else None,
            "master-display": build_master_display_string(masterdisplay) if masterdisplay else None,
            "max-cll": build_max_cll_string(max_cll_max_fll) if max_cll_max_fll else None,
        }

    def _get_master_display_for_encoding(self) -> Optional[MasterDisplayMetadata]:
        master_display: MasterDisplayMetadata | None = self._encoder_settings.hdr_metadata.mastering_display_metadata
        if master_display is None:
            master_display: MasterDisplayMetadata | None = self._video.get_master_display()

        return master_display

    def _get_max_cll_for_encoding(self) -> Optional[ContentLightLevelMetadata]:
        encoder_max_cll: ContentLightLevelMetadata | None = self._encoder_settings.hdr_metadata.content_light_level_metadata
        if encoder_max_cll is None:
            encoder_max_cll = self._video.get_content_light_level_metadata()

        return encoder_max_cll

    def _build_hdr_x265_params(self) -> list[str]:
        """Build x265 parameters for HDR10 video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.HDR_X265_PARAMS.copy()

        master_display: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        if master_display:
            params.append(f'master-display={build_master_display_string(master_display)}')

            max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()
            if max_cll_max_fll:
                params.append(f'max-cll={build_max_cll_string(max_cll_max_fll)}')

        return params

    def _build_sdr_x265_params(self) -> list[str]:
        """Build x265 parameters for SDR video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.SDR_X265_PARAMS.copy()
        if self._video.is_hdr_video():
            # remove HDR metadata if present
            params.append('master-display=G(0,0)B(0,0)R(0,0)WP(0,0)L(0,0)')
            params.append('max-cll=0,0')
        return params

    def _get_auto_tune(self) -> Optional[X265Tune]:
        """Select optimal encoding tune based on content.

        Returns:
            X265Tune enum or None if no tune is set
        """
        x265_params: X265Params = self._encoder_settings.x265_prams
        if x265_params.tune is not None:
            return x265_params.tune

        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingPresets.ANIMATION:
            return X265Tune.ANIMATION

        if self._grain.get_category() >= 2:
            return X265Tune.GRAIN

        return None

    def _get_auto_preset(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> x265_x264_Preset:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)
        """
        x265_params: X265Params = self._encoder_settings.x265_prams
        if x265_params.preset is not None:
            return x265_params.preset

        preset = hw_preset.preset
        return x265_x264_Preset(preset)

    def _get_auto_crf(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)

        libx265 generally uses higher CRF values than libx264 for similar quality. 2-5 points higher.
        """
        x265_params: X265Params = self._encoder_settings.x265_prams
        if x265_params.crf is not None:
            return x265_params.crf

        crf: float = hw_preset.crf
        if self.is_hdr_encoding():
            crf += 1.0  # 10-Bit HDR allows slightly higher CRF without quality loss

        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion
        action_w = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=action_crf,
        )
        crf -= action_crf * action_w

        grain_crf: float = self._grain.get_crf_x265_x264_adjustment()
        grain_w = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=grain_crf,
        )
        crf -= grain_crf * grain_w

        return round(crf)
