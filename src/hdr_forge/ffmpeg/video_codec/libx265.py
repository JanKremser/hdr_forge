from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingTuningPresets, HdrForgeSpeedPreset, HdrSdrFormat, Libx265Params, X265Tune
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.typedefs.codec_typing import BT_2020_FLAGS, BT_709_FLAGS, PIXEL_FORMAT_YUV420_10_BIT, PIXEL_FORMAT_YUV420_8_BIT, CodecPreset, VideoEncoderLibrary
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
    ]

    HDR_X265_PARAMS: list[str] = [
        'profile=main10',
    ]

    # SDR x265 parameters
    SDR_X265_PARAMS: list[str] = [
        'profile=main',
    ]

    REMOVE_HDR_FLAGS: list[str] = [
        'hdr-opt=0',
        'hdr10=0',
        'no-hdr10-opt=1',
    ]

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.LIBX265,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_X265_X264_Preset = self.calc_hw_preset_settings(Hdr_Forge_X265_X264_Preset)
        self._crf: int = self._get_auto_crf(calc_crf=hw_preset.crf)
        self._preset: CodecPreset = self._get_auto_preset(calc_preset=hw_preset.preset)
        self._tune: X265Tune | None = self._get_auto_tune()

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)

        output_options.update({
            "preset": self._preset.codec_preset,
            "crf": str(self._crf),
        })

        pix_fmt: str | None = self.get_pix_format_for_encoding()
        if pix_fmt is not None:
            output_options["pix_fmt"] = pix_fmt

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        output_options['x265-params'] = self._build_x265_params()

        return output_options

    def get_pix_format_for_encoding(self) -> str | None:
        bit_depth = self.get_bit_depth_for_encoding()

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.BANDING:
            return PIXEL_FORMAT_YUV420_10_BIT  # always use 10bit for banding reduction

        if bit_depth == 10:
            return PIXEL_FORMAT_YUV420_10_BIT
        elif bit_depth == 8:
            return PIXEL_FORMAT_YUV420_8_BIT
        return super().get_pix_format_for_encoding()

    def get_bit_depth_for_encoding(self) -> int:
        bit: int =  super().get_bit_depth_for_encoding()

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.BANDING:
            return 10

        return bit

    def get_custom_lib_parameters(self) -> dict:
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "crf": self._crf,
            "preset": self._preset.codec_preset,
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

    def _build_x265_params(self) -> str:
        """Build x265 parameters based on encoding settings.

        Returns:
            list of x265 parameter strings
        """
        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        x265_params: list[str] = self._build_default_x265_params()
        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            x265_params.extend(self._build_hdr_x265_params())
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            x265_params.extend(self._build_sdr_x265_params())

        x265_params_str: str = ':'.join(x265_params)

        return x265_params_str

    def _build_default_x265_params(self) -> list[str]:
        """Build default x265 parameters.

        Returns:
            list of x265 parameter strings
        """
        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.VIDEO:
            return []  # use x265 defaults for video preset

        # default params
        params: dict[str, str | None] = {
            'aq-mode': None,
            # default is 2
            # x265 can distribute bits more “intelligently,” especially in complex scenes and dark areas.
            # for almost all film types. This is one of the best AQ profiles for balanced quality.
            'aq-strength': None,
            # AQ only works within the selected "aq-mode"
            # - Default is 1.0
            # - 8–1.2 → very stable for most films, good compromise
            #   1.0 → universal
            #   1.5+ → very aggressive, sometimes for HDR or heavily textured content
            #   >2.0 → hardly necessary, can create artifacts or significantly increase bitrate
            'psy-rd': None, #psy-rd=1.5
            # Sharper, but potentially slightly more artifacts (not noticeable at normal bitrates)
            # - Default is 1.0
            # - Values between 1.0 and 2.0 are common in quality profiles.
            'psy-rdoq': None, #psy-rdoq=1.5
            # psy-rdoq: More realistic textures, but slightly higher bitrate requirements
            # - Default is 1.0
            # - 0.8–1.2 for a good compromise.
            'ref': None,
            # Number of reference frames
            # - default is 3 for medium preset, 4 for slow presets
            # - 4 = optimal all-round value
            #   5–6 = slight optimization, but slower
            #   >6 = hardly any added value except for anime or very clean 4K masters
            'bframes': '4',
            # Number of B-frames
            # - default is 4-8, depending on preset
            # - 8 = optimal all-round value
            'b-adapt': '2',
            # B-frame adaptation mode
            # - default is 2
            # - 0 = disabled default by medium and lower presets
            # - 1 = simple and fast
            # - 2 = optimal all-round value, default by slow and higher presets
            'rdoq-level': None,
            # Makes fine dark details visibly better
            # - 0 = disabled, default by medium, fast presets
            # - 1 = -
            # - 2 = better for films with a lot of dark scenes/details
            #       2 is slower but gives better results in dark scenes
            # - 3 = hardly any added value, not recommended
            #       3 is very slow
            'qcomp': '0.65',
            # Balances contrast and motion scenes well
            # - 0.5-1.0 is a rage
            # - Prevents bitrate spikes
            # - Default is 0.6
            'rc-lookahead': '25',
            # Better for most films with complex scenes
            # - default is 15 for fast, 20 for medium, 25 for slow, 40 for veryslow
            # - 40 = optimal all-round value
            # - This is RAM intensive for very high-resolution videos (4K+)
            'lookahead-slices': None,
            # default is 4 for slow and 8 for medium
        }

        new_params= self._preset.ffmpeg_params.get('x265-params', {}) or {}
        if type(new_params) is dict:
            params.update(new_params)

        if hdr_forge_preset == HdrForgeEncodingTuningPresets.ANIMATION:
            params.update({
                'aq-mode': '2',
                'aq-strength': '1.1', # default by animation tune is 0.4
                'psy-rd': '0.9', # default by animation tune is 0.4
                'psy-rdoq': '0.9',
                'ref': '6',
                'bframes': '10',# for animation, more b-frames can help compression -> 8-16
                'b-adapt': '2',
                'rdoq-level': '2', # 1-2 is ok
                'deblock': None, # default by animation tune is 1:1
            })
        elif (
            hdr_forge_preset in [
                HdrForgeEncodingTuningPresets.FILM,
                HdrForgeEncodingTuningPresets.ACTION,
            ]
        ):
            # default in x265 is psy-rd=1.0,psy-rdoq=1.0
            # optimize psy settings for more optical quality
            params.update({
                'aq-mode': '2',
                'psy-rd': '1.2',
                'psy-rdoq': '1.0',
            })
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.FILM4K:
            params.update({
                'aq-mode': '3',
                'aq-strength': '1.0',
                'qcomp': '0.66',
                'psy-rd': '2.0',
                'psy-rdoq': '1.5',
                'cutree': '1',
                'sao': '0',
                'deblock': '-1,-1',
                'tu-intra-depth': '3',
                'tu-inter-depth': '3',
                'subme': '5',
                'strong-intra-smoothing': '0',
            })
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.FILM4K_FAST:
            params.update({
                'aq-mode': '2',
                'aq-strength': '0.9',
                'qcomp': '0.65',
                'psy-rd': '1.2',
                'psy-rdoq': '1.0',
                'cutree': '1',
                'sao': '0',
                'deblock': '0,-1',
                'tu-intra-depth': '2',
                'tu-inter-depth': '2',
                'subme': '4',
                'strong-intra-smoothing': '0',
            })
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.BANDING:
            # reduce banding artifacts by enabling stronger deblocking and using 10bit encoding for SDR
            params.update({
                'aq-mode': '3',
                'aq-strength': '1.2',
                'psy-rd': '2.0',
                'psy-rdoq': '1.2',
                'deblock': '-1,-1',
                'rdoq-level': '2',
                'qcomp': '0.65',
            })
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.GRAIN:
            params.update({
                'aq-mode': '3',# besser um grain zu erhalten
                'aq-strength': '0.7', # 0.8 ist super, 0.7 ist besser für kompression
                'psy-rd': '1.8',
                'psy-rdoq': '1.0',
                'cutree': '1',# 0 ist besser. 1 ist ein guter kompromiss
                'qcomp': '0.80',# 0.80 ist super
                #'qg-size': '16',# 16 beeinflusst das Kompressionsverhalten negativ
                'sao': '0',
                'rc-grain': '1',
            })

        return list(f"{key}={value}" for key, value in params.items() if value is not None)

    def _build_hdr_x265_params(self) -> list[str]:
        """Build x265 parameters for HDR10 video encoding.

        Returns:
            list of x265 parameter strings
        """

        params: list[str] = BT_2020_FLAGS.copy()

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()
        if encoding_hdr_sdr_format == HdrSdrFormat.HDR:
            params.extend(self.HDR_X265_PARAMS.copy())

            # remove HDR10 metadata if present
            params.extend(self.REMOVE_HDR_FLAGS.copy())
            params.append('master-display=G(0,0)B(0,0)R(0,0)WP(0,0)L(0,0)')
            params.append('max-cll=0,0')
            return params
        else:
            params.extend(self.HDR10_X265_PARAMS.copy())

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
        params: list[str] = []

        params.extend(self.SDR_X265_PARAMS.copy())

        if self._video.is_hdr_video():
            # remove HDR metadata if present
            params.extend(self.REMOVE_HDR_FLAGS.copy())
            params.append('master-display=G(0,0)B(0,0)R(0,0)WP(0,0)L(0,0)')
            params.append('max-cll=0,0')

        if self._video.get_color_primaries() == 'bt2020':
            params.extend(BT_2020_FLAGS.copy())
        elif self._video.get_color_primaries() == 'bt709':
            params.extend(BT_709_FLAGS.copy())
        else:
            # unknown color primaries, do not set any
            pass
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
        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.ANIMATION:
            return X265Tune.ANIMATION

        if hdr_forge_preset == HdrForgeEncodingTuningPresets.GRAIN_FFMPEG:
            return X265Tune.GRAIN

        if self._grain.get_category() >= 2:
            return X265Tune.GRAIN

        return None

    def _get_auto_preset(self, calc_preset: HdrForgeSpeedPreset) -> CodecPreset:
        """Select optimal encoding preset based on parameter priority.

        Priority:
            1. libx265_params.preset (from --encoder-params)
            2. universal_params.speed (from --speed)
            3. calc_preset (auto-detection)

        Returns:
            CodecPreset value
        """
        # Priority 1: libx265_params from --encoder-params
        libx265_params: Libx265Params = self._encoder_settings.libx265_params
        if libx265_params.preset is not None:
            return CodecPreset(
                codec_libs=[self.lib],
                codec_preset=str(libx265_params.preset),
                ffmpeg_params={},
            )

        return super()._get_auto_preset(calc_preset=calc_preset)

    def _get_auto_crf(self, calc_crf: float) -> int:
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
        crf: float = calc_crf
        if self.is_hdr_encoding():
            crf += 1.0  # 10-Bit HDR allows slightly higher CRF without quality loss

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingTuningPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion
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
