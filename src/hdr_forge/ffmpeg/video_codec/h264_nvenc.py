from typing import Tuple
from hdr_forge.cli.cli_output import print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_HEVC_H264_NVENC_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HEVC_NVENC_Preset, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary
from hdr_forge.video import Video

class H264NvencCodec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    SDR_PIXEL_FORMAT = 'yuv420p'

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
            "rc": "vbr_hq", # variable Bitrate mit hoher Qualität (NVENC-spezifisch)
            "preset": self._preset.value,
            "cq": str(self._cq)
        })

        output_options['pix_fmt'] = self.SDR_PIXEL_FORMAT
        if self._video.is_hdr_video():
            print_warn("H264_NVENC-SDR encoding does not support HDR metadata removal;")

        return output_options

    def get_custom_lib_parameters(self) -> dict:
        return {
            "cq": self._cq,
            "preset": self._preset.value,
        }

    def _get_auto_preset(self, hw_preset: Hdr_Forge_HEVC_H264_NVENC_Preset) -> HEVC_NVENC_Preset:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)
        """
        # x265_params: X265Params = self._encoder_settings.x265_prams
        # if x265_params.preset is not None:
        #     return x265_params.preset

        preset = hw_preset.preset
        return HEVC_NVENC_Preset(preset)

    def _get_auto_cq(self, hw_preset: Hdr_Forge_HEVC_H264_NVENC_Preset) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)

        libx265 generally uses higher CRF values than libx264 for similar quality. 2-5 points higher.
        """
        # x265_params: X265Params = self._encoder_settings.x265_prams
        # if x265_params.crf is not None:
        #     return x265_params.crf

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
