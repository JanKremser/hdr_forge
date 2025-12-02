from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary, Libx264Params, X264Tune, x265_x264_Preset
from hdr_forge.typedefs.video_typing import HdrMetadata
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

    PIXEL_FORMAT_10BIT = 'yuv420p10le'
    PIXEL_FORMAT_8BIT = 'yuv420p'

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
        self._preset: x265_x264_Preset = self._get_auto_preset(hw_preset)
        self._tune: X264Tune | None = self._get_auto_tune()

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "profile:v": self.SDR_PROFILE,
            "pix_fmt": self.get_pix_format_for_encoding(),
            "preset": self._preset.value,
            "crf": str(self._crf),
        })

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        x264_params: list[str] = self.SDR_X264_PARAMS
        output_options['x264-params'] = ':'.join(x264_params)

        metadata: list[str] = [
            'hdr_forge_encoder_preset=' + self._preset.value,
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
        return self._video.get_pix_fmt()  # fallback

    def get_bit_depth_for_encoding(self) -> int:
        return super().get_bit_depth_for_encoding()

    def get_custom_lib_parameters(self) -> dict:
        return {
            "crf": self._crf,
            "preset": self._preset.value,
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
        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingPresets.ANIMATION:
            return X264Tune.ANIMATION
        elif hdr_forge_preset == HdrForgeEncodingPresets.FILM:
            return X264Tune.FILM

        if self._grain.get_category() >= 2:
            return X264Tune.GRAIN

        return None

    def _get_auto_preset(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> x265_x264_Preset:
        """Select optimal encoding preset based on parameter priority.

        Priority:
            1. libx264_params.preset (from --encoder-params)
            2. universal_params.speed (from --speed)
            3. hw_preset.preset (auto-detection)

        Returns:
            x265_x264_Preset enum value

        TODO:
        slow bringt spürbare Vorteile, slower oder veryslow nur noch marginal — dafür viel mehr Zeit.
        """
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.preset is not None:
            return libx264_params.preset

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
