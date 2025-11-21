from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary, Libx265Params, X265Tune, x265_x264_Preset
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.video import Video

class Libx265Codec(VideoCodecBase):

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
        # //
        # "level-idc=5.1",
        # "high-tier=1",
            # Main Tier → for Streaming, Blu-ray, Web
            # High Tier → only for very high bitrate encodings, not needed for typical HDR10 use cases
        # //
        # 'vbv-bufsize=20000',
        # 'vbv-maxrate=20000',
# | --------------------- | ------------------------ | ----------------------
# | **480p (SD)**         | 2 000                    | 4 000
# | **720p (HD)**         | 5 000                    | 10 000
# | **720p60 (HD)**       | 7 000                    | 14 000
# | **1080p (Full HD)**   | 10 000                   | 20 000
# | **1080p60 (Full HD)** | 15 000                   | 30 000
# | **1440p (2K)**        | 24 000                   | 48 000
# | **1440p60 (2K)**      | 30 000                   | 60 000
# | **2160p (4K UHD)**    | 35 000–45 000            | 70 000–90 000
# | **2160p60 (4K UHD)**  | 45 000–60 000            | 90 000–120 000
# | **4320p (8K)**        | 100 000–160 000          | 200 000–300 000
        # //
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

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "preset": self._preset.value,
            "crf": str(self._crf),
            "pix_fmt": self.get_pix_format_for_encoding(),
        })

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            x265_params: list[str] = self._build_hdr_x265_params()
            output_options['x265-params'] = ':'.join(x265_params)
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            x265_params: list[str] = self._build_sdr_x265_params()
            output_options['x265-params'] = ':'.join(x265_params)

        return output_options

    def get_pix_format_for_encoding(self) -> str:
        bit_depth = self.get_bit_depth_for_encoding()
        if bit_depth == 10:
            return self.PIXEL_FORMAT_10BIT
        elif bit_depth == 8:
            return self.PIXEL_FORMAT_8BIT
        return self._video.get_pix_fmt()  # fallback

    def get_bit_depth_for_encoding(self) -> int:
        return super().get_bit_depth_for_encoding()

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

    def _get_auto_tune(self) -> Optional[X265Tune]:
        """Select optimal encoding tune based on parameter priority.

        Priority:
            1. libx265_params.tune (from --encoder-params)
            2. Auto-detection (preset or grain analysis)

        Returns:
            X265Tune enum or None if no tune is set
        """
        # Priority 1: libx265_params from --encoder-params
        libx265_params: Libx265Params = self._encoder_settings.libx265_params
        if libx265_params.tune is not None:
            return libx265_params.tune

        # Priority 2: Auto-detection
        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingPresets.ANIMATION:
            return X265Tune.ANIMATION

        if self._grain.get_category() >= 2:
            return X265Tune.GRAIN

        return None

    def _get_auto_preset(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> x265_x264_Preset:
        """Select optimal encoding preset based on parameter priority.

        Priority:
            1. libx265_params.preset (from --encoder-params)
            2. universal_params.speed (from --speed)
            3. hw_preset.preset (auto-detection)

        Returns:
            x265_x264_Preset enum value
        """
        # Priority 1: libx265_params from --encoder-params
        libx265_params: Libx265Params = self._encoder_settings.libx265_params
        if libx265_params.preset is not None:
            return libx265_params.preset

        # Priority 2: universal_params from --speed
        universal_params = self._encoder_settings.universal_params
        if universal_params.speed is not None:
            return universal_params.speed

        # Priority 3: Auto-detection from hw_preset
        preset = hw_preset.preset
        return x265_x264_Preset(preset)

    def _get_auto_crf(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> int:
        """Calculate optimal CRF value based on parameter priority.

        Priority:
            1. libx265_params.crf (from --encoder-params)
            2. universal_params.quality (from --quality)
            3. hw_preset.crf (auto-detection)

        Returns:
            CRF value (lower = higher quality)

        libx265 generally uses higher CRF values than libx264 for similar quality. 2-5 points higher.
        """
        # Priority 1: libx265_params from --encoder-params
        libx265_params: Libx265Params = self._encoder_settings.libx265_params
        if libx265_params.crf is not None:
            return libx265_params.crf

        # Priority 2: universal_params from --quality
        universal_params = self._encoder_settings.universal_params
        if universal_params.quality is not None:
            return universal_params.quality

        # Priority 3: Auto-detection from hw_preset
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
