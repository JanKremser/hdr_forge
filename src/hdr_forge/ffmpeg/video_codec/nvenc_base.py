"""Base class for NVIDIA NVENC codec implementations (HEVC and H.264)."""

from typing import Tuple

from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingTuningPresets, HdrForgeSpeedPreset, NvencParams, NvencRcMode
from hdr_forge.typedefs.codec_typing import CodecPreset, VideoEncoderLibrary
from hdr_forge.video import Video


class NvencCodecBase(VideoCodecBase):
    """Base class for NVIDIA NVENC video codecs (H.264 and HEVC).

    Provides shared functionality for NVENC rate control, preset selection, and quality configuration.
    """

    def _get_nvenc_rc(self) -> NvencRcMode:
        """Get the rate control mode for NVENC encoding.

        Returns:
            Rate control mode as NvencRcMode
        """
        nvenc_params: NvencParams = self._encoder_settings.nvenc_params
        if nvenc_params.rc is not None:
            return nvenc_params.rc

        return NvencRcMode.VBR_HQ  # default to variable bitrate with high quality

    def _get_auto_preset(self, calc_preset: HdrForgeSpeedPreset) -> CodecPreset:
        """Select optimal encoding preset based on resolution and parameter priority.

        Priority:
            1. nvenc_params.preset (from --encoder-params)
            2. hw_preset.preset (from --hw-preset)

        Args:
            calc_preset: Hardware preset from calculation

        Returns:
            CodecPreset with preset value
        """
        # Priority 1: nvenc_params from --encoder-params
        nvenc_params = self._encoder_settings.nvenc_params
        if nvenc_params.preset is not None:
            return CodecPreset(
                codec_libs=[self.lib],
                codec_preset=nvenc_params.preset.value,
                ffmpeg_params={},
            )

        # Priority 2: Auto-detection from hw_preset
        return super()._get_auto_preset(calc_preset=calc_preset)

    def _get_auto_cq(self, hw_preset) -> int:
        """Calculate optimal CQ value based on parameter priority.

        Priority:
            1. nvenc_params.cq (from --encoder-params)
            2. universal_params.quality (from --quality)
            3. hw_preset.cq (auto-detection with HDR/action adjustments)

        Args:
            hw_preset: Hardware preset configuration

        Returns:
            CQ value (lower = higher quality, 0-51)
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

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingTuningPresets.ACTION else 0.0  # Action preset lowers CRF for better handling of fast motion
        action_w = self._calculate_crf_adjustment_weight(
            current_crf=cq,
            crf_delta=action_crf,
        )
        cq -= action_crf * action_w

        return round(cq)
