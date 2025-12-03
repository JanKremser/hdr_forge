from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_AV1_Preset, Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary, Libx265Params, X265Tune, x265_x264_Preset
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.video import Video

class LibSvtAV1Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.HDR,
        HdrSdrFormat.HDR10,
        HdrSdrFormat.SDR,
        HdrSdrFormat.DOLBY_VISION,
    ]

    # HDR x265 parameters for HDR10 encoding
    HDR10_X265_PARAMS: list[str] = [
        'profile=main10',
        'hdr-opt=1',
        'hdr10=1',
        'repeat-headers=1',
        'colorprim=bt2020',
        'transfer=smpte2084',
        'colormatrix=bt2020nc',
    ]

    HDR_X265_PARAMS: list[str] = [
        'profile=main10',
        'hdr-opt=0',
        'hdr10=0',
        'no-hdr10-opt=1',
        'colorprim=bt2020',
        'transfer=smpte2084',
        'colormatrix=bt2020nc',
    ]

    # SDR x265 parameters
    SDR_X265_PARAMS: list[str] = [
        'profile=main',
        'hdr-opt=0',
        'hdr10=0',
        'no-hdr10-opt=1',
        # //
        'colorprim=bt709',
        'transfer=bt709',
        'colormatrix=bt709',
    ]

    PIXEL_FORMAT_10BIT = 'yuv420p10le'
    PIXEL_FORMAT_8BIT = 'yuv420p'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.LIBSVTAV1,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_AV1_Preset = self.calc_hw_preset_settings(Hdr_Forge_AV1_Preset)
        self._crf: int = self._get_auto_crf(hw_preset)
        self._preset: int = self._get_auto_preset(hw_preset)

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "preset": str(self._preset), # kleiner gleich langsamer (0-13)
            "crf": str(self._crf), # kann um 7 größer sein las x265
            "pix_fmt": self.get_pix_format_for_encoding(),
        })

        # encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        # if encoding_hdr_sdr_format in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
        #     x265_params: list[str] = self._build_hdr_x265_params()
        #     output_options['x265-params'] = ':'.join(x265_params)
        # elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
        #     x265_params: list[str] = self._build_sdr_x265_params()
        #     output_options['x265-params'] = ':'.join(x265_params)

        metadata: list[str] = [
            'hdr_forge_encoder_preset=' + str(self._preset),
            'hdr_forge_encoder_crf=' + str(self._crf),
        ]
        if 'metadata' in output_options:
            output_options['metadata'].extend(metadata)
        else:
            output_options['metadata'] = metadata

        return output_options

    def get_pix_format_for_encoding(self) -> str:
        bit_depth = self.get_bit_depth_for_encoding()
        if bit_depth == 10:
            return self.PIXEL_FORMAT_10BIT
        elif bit_depth == 8:
            return self.PIXEL_FORMAT_8BIT
        return super().get_pix_format_for_encoding()

    def get_bit_depth_for_encoding(self) -> int:
        return super().get_bit_depth_for_encoding()

    def get_custom_lib_parameters(self) -> dict:
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "crf": self._crf,
            "preset": self._preset,
            "master-display": build_master_display_string(masterdisplay) if masterdisplay else None,
            "max-cll": build_max_cll_string(max_cll_max_fll) if max_cll_max_fll else None,
        }

    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        master_display: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        if master_display is None and max_cll is None:
            return None

        return HdrMetadata(
            mastering_display_metadata=master_display,
            content_light_level_metadata=max_cll,
        )

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

        params: list[str] = []

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()
        if encoding_hdr_sdr_format == HdrSdrFormat.HDR:
            params = self.HDR_X265_PARAMS.copy()
            # remove HDR10 metadata if present
            params.append('master-display=G(0,0)B(0,0)R(0,0)WP(0,0)L(0,0)')
            params.append('max-cll=0,0')
            return params

        params: list[str] = self.HDR10_X265_PARAMS.copy()

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

    def _get_auto_preset(self, hw_preset: Hdr_Forge_AV1_Preset) -> int:
        """Select optimal encoding preset based on parameter priority.

        Returns:
            int
        """
        # # Priority 1: libx265_params from --encoder-params
        # libx265_params: Libx265Params = self._encoder_settings.libx265_params
        # if libx265_params.preset is not None:
        #     return libx265_params.preset

        # # Priority 2: universal_params from --speed
        # universal_params = self._encoder_settings.universal_params
        # if universal_params.speed is not None:
        #     return universal_params.speed

        # Priority 3: Auto-detection from hw_preset
        preset = hw_preset.preset
        return preset

    def _get_auto_crf(self, hw_preset: Hdr_Forge_AV1_Preset) -> int:
        """Calculate optimal CRF value based on parameter priority.

        Returns:
            CRF value (lower = higher quality)
        """
        # # Priority 1: libx265_params from --encoder-params
        # libx265_params: Libx265Params = self._encoder_settings.libx265_params
        # if libx265_params.crf is not None:
        #     return libx265_params.crf

        # # Priority 2: universal_params from --quality
        # universal_params = self._encoder_settings.universal_params
        # if universal_params.quality is not None:
        #     return universal_params.quality

        # Priority 3: Auto-detection from hw_preset
        crf: float = hw_preset.crf
        # if self.is_hdr_encoding():
        #     crf += 1.0  # 10-Bit HDR allows slightly higher CRF without quality loss

        # hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        # action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion
        # action_w = self._calculate_crf_adjustment_weight(
        #     current_crf=crf,
        #     crf_delta=action_crf,
        # )
        # crf -= action_crf * action_w

        # grain_crf: float = self._grain.get_crf_x265_x264_adjustment()
        # grain_w = self._calculate_crf_adjustment_weight(
        #     current_crf=crf,
        #     crf_delta=grain_crf,
        # )
        # crf -= grain_crf * grain_w

        return round(crf)
