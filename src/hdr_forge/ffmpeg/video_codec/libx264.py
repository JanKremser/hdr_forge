from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingTuningPresets, HdrForgeSpeedPreset, HdrSdrFormat, Libx264Params, X264Tune
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.typedefs.codec_typing import BT_709_FLAGS, COLOR_PRIMARIES_FLAG_MAP, PIXEL_FORMAT_YUV420_10_BIT, PIXEL_FORMAT_YUV420_8_BIT, CodecPreset, ColorPrimaries, VideoEncoderLibrary
from hdr_forge.video import Video

class Libx264Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    SDR_PROFILE = 'high'

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
        self._preset: CodecPreset = self._get_auto_preset(calc_preset=hw_preset.preset)
        self._tune: X264Tune | None = self._get_auto_tune()

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "profile:v": self.SDR_PROFILE,
            "preset": self._preset.codec_preset,
            "crf": str(self._crf),
        })

        pix_fmt: str | None = self.get_pix_format_for_encoding()
        if pix_fmt is not None:
            output_options["pix_fmt"] = pix_fmt

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        output_options['x264-params'] = self._build_x264_params()

        return output_options

    def _build_default_x264_params(self) -> list[str]:
        """Build default x264 parameters.
        Returns:
            list of x264 parameter strings
        """
        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.VIDEO:
            return []  # use x264 defaults for video preset

        # default params
        params: dict[str, str | None] = {
            'aq-mode': None,
            # default is 1
            # x264: 1 = variance AQ (standard), 2 = auto-variance AQ (recommended for most cases)
            'aq-strength': None,
            # - Default is 1.0
            # - 0.8–1.2 → very stable for most films, good compromise
            #   1.0 → universal
            #   1.5+ → very aggressive, sometimes for HDR or heavily textured content
            'psy-rd': None,
            # Psychovisual Rate-Distortion Optimization
            # - Default is 1.0:0.0 (psy-rd:psy-trellis)
            # - Format: psy-rd=X.X:Y.Y
            # - Values between 0.8:0.0 and 1.2:0.15 are common
            'ref': None,
            # Number of reference frames
            # - default is 1 for veryfast, 3 for medium, 5 for slow
            # - 4-5 = optimal all-round value
            # - 6-8 = slight optimization, but slower
            # - >8 = hardly any added value except for anime or very clean 4K masters (max 16)
            'bframes': '4',
            # Number of B-frames
            # - default is 3 for medium/slow
            # - 4-8 = optimal range
            'b-adapt': '2',
            # B-frame adaptation mode
            # - default is 1
            # - 0 = disabled
            # - 1 = fast (fast algorithm)
            # - 2 = optimal (optimal algorithm), slower but better decisions
            'trellis': None,
            # Trellis quantization (similar to rdoq-level in x265)
            # - 0 = disabled (default for fast/faster)
            # - 1 = only at end of encoding
            # - 2 = always active (default for slow/slower), better for dark scenes
            'qcomp': '0.65',
            # Balances contrast and motion scenes well
            # - 0.5-1.0 is the typical range
            # - Default is 0.6
            'rc-lookahead': '50',
            # Better lookahead for complex scenes
            # - default is 10 for veryfast, 40 for medium, 50 for slow
            # - 40-50 = optimal all-round value
            # - RAM-intensive for very high-resolution videos (4K+)
            'me': None,
            # Motion Estimation method
            # - dia (diamond) = fastest
            # - hex (hexagon) = good compromise (default for fast/faster)
            # - umh (uneven multi-hexagon) = default for slow/slower
            # - esa (exhaustive) = very slow, hardly any added value
            'subme': None,
            # Subpixel Motion Estimation quality
            # - 1-11 (1 = fast, 11 = best quality)
            # - default is 6 for medium, 7 for slow, 9 for slower
            # - 7-9 = good range for quality
            'merange': None,
            # Motion Estimation search range
            # - default is 16 for medium/slow
            # - 16-24 = good range
        }

        new_params= self._preset.ffmpeg_params.get('x264-params', {}) or {}
        if type(new_params) is dict:
            params.update(new_params)

        if hdr_forge_preset == HdrForgeEncodingTuningPresets.ANIMATION:
            params.update({
                'aq-mode': '2',
                'aq-strength': '1.1',
                'psy-rd': '0.9:0.0',  # x264 format: psy-rd:psy-trellis
                'ref': '8',  # Anime benefits from more reference frames
                'bframes': '10',  # for animation, more B-frames can help
                'b-adapt': '2',
                'trellis': '2',
                'deblock': None,  # default for animation tune is 1:1
            })
        elif (
            hdr_forge_preset in [
                HdrForgeEncodingTuningPresets.FILM,
                HdrForgeEncodingTuningPresets.ACTION,
            ]
        ):
            # optimize psy settings for more optical quality
            params.update({
                'aq-mode': '2',
                'psy-rd': '1.0:0.15',  # slight psy-trellis increase for better texture preservation
            })
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.BANDING:
            # reduce banding artifacts
            params.update({
                'aq-mode': '3',  # auto-variance AQ with bias to dark scenes
                'aq-strength': '1.2',
                'psy-rd': '1.2:0.20',
                'deblock': '-1:-1',
                'trellis': '2',
                'qcomp': '0.65',
            })

        return list(f"{key}={value}" for key, value in params.items() if value is not None)

    def _build_x264_params(self) -> str:
        """Build x264 parameters for SDR video encoding.

        Returns:
            list of x264 parameter strings
        """
        params: list[str] = self._build_default_x264_params()

        color_primaries_flag: Optional[ColorPrimaries] = self._encoder_settings.override_color_primaries_flag
        if color_primaries_flag is None:
            try:
                color_primaries_flag = ColorPrimaries(self._video.get_color_primaries())
            except ValueError:
                color_primaries_flag = None
                # unknown color primaries

        if color_primaries_flag is not None:
            flags: list[str] = COLOR_PRIMARIES_FLAG_MAP[color_primaries_flag].copy()
            params.extend(flags)

        x264_params_str: str = ':'.join(params)
        return x264_params_str

    def get_pix_format_for_encoding(self) -> str | None:
        bit_depth = self.get_bit_depth_for_encoding()
        if bit_depth == 10:
            return PIXEL_FORMAT_YUV420_10_BIT
        elif bit_depth == 8:
            return PIXEL_FORMAT_YUV420_8_BIT
        return super().get_pix_format_for_encoding()

    def get_bit_depth_for_encoding(self) -> int:
        return super().get_bit_depth_for_encoding()

    def get_custom_lib_parameters(self) -> dict:
        return {
            "crf": self._crf,
            "preset": self._preset.codec_preset,
            "tune": self._tune.value if self._tune else None,
        }

    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        return None

    def _get_auto_tune(self) -> Optional[X264Tune]:
        """Select optimal encoding tune based on parameter priority.

        Priority:
            1. libx264_params.tune (from --encoder-params)
            2. Auto-detection (preset or grain analysis)

        Returns:
            X264Tune enum or None if no tune is set
        """
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.tune is not None:
            return libx264_params.tune

        # Priority 2: Auto-detection
        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.ANIMATION:
            return X264Tune.ANIMATION
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.FILM:
            return X264Tune.FILM

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
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.preset is not None:
            return CodecPreset(
                codec_libs=[self.lib],
                codec_preset=str(libx264_params.preset),
                ffmpeg_params={},
            )

        return super()._get_auto_preset(calc_preset=calc_preset)

    def _get_auto_crf(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> int:
        """Calculate optimal CRF value based on parameter priority.

        Priority:
            1. libx264_params.crf (from --encoder-params)
            2. universal_params.quality (from --quality)
            3. hw_preset.crf (auto-detection)

        Returns:
            CRF value (lower = higher quality)
        """
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.crf is not None:
            return libx264_params.crf

        # Priority 2: universal_params from --quality
        universal_params = self._encoder_settings.universal_params
        if universal_params.quality is not None:
            return universal_params.quality

        # Priority 3: Auto-detection from hw_preset
        crf: float = hw_preset.crf

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingTuningPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion

        action_w: float = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=action_crf,
        )
        crf -= action_crf * action_w

        return round(crf)
