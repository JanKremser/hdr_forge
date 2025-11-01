from typing import Optional, Tuple
from hdr_forge.cli.cli_output import print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_HEVC_H264_NVENC_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HEVC_NVENC_Preset, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.video import Video

class H264NvencCodec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    PIXEL_FORMAT_8BIT = 'yuv420p'

    SDR_PROFILE = 'high'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.H264_NVENC,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_HEVC_H264_NVENC_Preset = self.calc_hw_preset_settings(Hdr_Forge_HEVC_H264_NVENC_Preset)
        self._cq: int = self._get_auto_cq(hw_preset)
        self._preset: HEVC_NVENC_Preset = self._get_auto_preset(hw_preset)

    def get_ffmpeg_params(self) -> dict:
        output_options: dict = super().get_ffmpeg_params()
        output_options.update({
            "rc": "vbr_hq", # variable bitrate with high quality (NVENC-specific)
            "profile:v": self.get_pix_format_for_encoding(),
            "pix_fmt": self.PIXEL_FORMAT_8BIT,
            "preset": self._preset.value,
            "cq": str(self._cq)
        })

        if self._video.is_hdr_video():
            print_warn("H264_NVENC-SDR encoding does not support HDR metadata removal;")

        return output_options

    def get_pix_format_for_encoding(self) -> str:
        return self.PIXEL_FORMAT_8BIT

    def get_bit_depth_for_encoding(self) -> int:
        return 8

    def get_custom_lib_parameters(self) -> dict:
        return {
            "cq": self._cq,
            "preset": self._preset.value,
        }

    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        return None

    def _get_auto_preset(self, hw_preset: Hdr_Forge_HEVC_H264_NVENC_Preset) -> HEVC_NVENC_Preset:
        """Select optimal encoding preset based on resolution and parameter priority.

        Priority:
            1. nvenc_params.preset (from --encoder-params)
            2. hw_preset.preset (from --hw-preset)

        Returns:
            HEVC_NVENC_Preset enum value
        """
        # Priority 1: nvenc_params from --encoder-params
        nvenc_params = self._encoder_settings.nvenc_params
        if nvenc_params.preset is not None:
            return nvenc_params.preset

        # Priority 2: Auto-detection from hw_preset
        preset = hw_preset.preset
        return HEVC_NVENC_Preset(preset)

    def _get_auto_cq(self, hw_preset: Hdr_Forge_HEVC_H264_NVENC_Preset) -> int:
        """Calculate optimal CQ value based on parameter priority.

        Priority:
            1. nvenc_params.cq (from --encoder-params)
            2. universal_params.quality (from --quality)
            3. hw_preset.cq (auto-detection)

        Returns:
            CQ value (lower = higher quality)
        """
        # Priority 1: nvenc_params from --encoder-params
        nvenc_params = self._encoder_settings.nvenc_params
        if nvenc_params.cq is not None:
            return nvenc_params.cq

        # Priority 2: universal_params from --quality
        universal_params = self._encoder_settings.universal_params
        if universal_params.quality is not None:
            return universal_params.quality

        # Priority 3: Auto-detection from hw_preset
        cq: float = hw_preset.cq
        if self.is_hdr_encoding():
            cq += 1.0  # 10-Bit HDR allows slightly higher CRF without quality loss

        hdr_forge_preset: HdrForgeEncodingPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion
        action_w = self._calculate_crf_adjustment_weight(
            current_crf=cq,
            crf_delta=action_crf,
        )
        cq -= action_crf * action_w

        grain_crf: float = self._grain.get_crf_x265_x264_adjustment()
        grain_w = self._calculate_crf_adjustment_weight(
            current_crf=cq,
            crf_delta=grain_crf,
        )
        cq -= grain_crf * grain_w

        return round(cq)
