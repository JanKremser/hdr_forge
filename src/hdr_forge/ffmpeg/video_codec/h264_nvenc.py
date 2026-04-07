from typing import Optional, Tuple
from hdr_forge.cli.cli_output import print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_HEVC_H264_NVENC_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingTuningPresets, HdrForgeSpeedPreset, HdrSdrFormat, NvencParams, NvencRcMode
from hdr_forge.typedefs.codec_typing import PIXEL_FORMAT_YUV420_8_BIT, CodecPreset, VideoEncoderLibrary
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.video import Video

class H264NvencCodec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    SDR_PROFILE = 'high'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.H264_NVENC,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
            gpu_encoding=True,
        )
        hw_preset: Hdr_Forge_HEVC_H264_NVENC_Preset = self.calc_hw_preset_settings(Hdr_Forge_HEVC_H264_NVENC_Preset)
        self._cq: int = self._get_auto_cq(hw_preset)
        self._preset: CodecPreset = self._get_auto_preset(calc_preset=hw_preset.preset)
        self._nvenc_rc: NvencRcMode = self._get_nvenc_rc()

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "rc": self._nvenc_rc.value,
            "profile:v": self.get_pix_format_for_encoding(),
            "preset": self._preset.codec_preset,
            "cq": str(self._cq)
        })

        pix_fmt: str | None = self.get_pix_format_for_encoding()
        if pix_fmt is not None:
            output_options["pix_fmt"] = pix_fmt

        if self._video.is_hdr_video():
            print_warn("H264_NVENC-SDR encoding does not support HDR metadata removal;")

        ffmpeg_root_params = self._preset.ffmpeg_params.get('root', {})
        if ffmpeg_root_params and isinstance(ffmpeg_root_params, dict):
            output_options.update(ffmpeg_root_params)

        return output_options

    def get_pix_format_for_encoding(self) -> str:
        return PIXEL_FORMAT_YUV420_8_BIT

    def get_bit_depth_for_encoding(self) -> int:
        return 8

    def get_custom_lib_parameters(self) -> dict:
        return {
            "cq": self._cq,
            "preset": self._preset.codec_preset,
        }

    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        return None

    def _get_nvenc_rc(self) -> NvencRcMode:
        """Get the rate control mode for NVENC encoding.

        Returns:
            Rate control mode as string
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

        Returns:
            HEVC_NVENC_Preset enum value
        """
        # Priority 1: nvenc_params from --encoder-params
        nvenc_params = self._encoder_settings.nvenc_params
        if nvenc_params.preset is not None:
            return CodecPreset(
                codec_libs=[self.lib],
                value=nvenc_params.preset.value,
                ffmpeg_params={},
            )

        # Priority 2: Auto-detection from hw_preset
        return super()._get_auto_preset(calc_preset=calc_preset)

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

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingTuningPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion
        action_w = self._calculate_crf_adjustment_weight(
            current_crf=cq,
            crf_delta=action_crf,
        )
        cq -= action_crf * action_w

        return round(cq)
