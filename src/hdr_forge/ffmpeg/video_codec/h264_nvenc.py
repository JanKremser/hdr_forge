from typing import Optional, Tuple
from hdr_forge.cli.cli_output import print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_HEVC_H264_NVENC_Preset
from hdr_forge.ffmpeg.video_codec.nvenc_base import NvencCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrSdrFormat, NvencRcMode
from hdr_forge.typedefs.codec_typing import PIXEL_FORMAT_YUV420_8_BIT, CodecPreset, VideoEncoderLibrary
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.video import Video

class H264NvencCodec(NvencCodecBase):

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
            "profile:v": self.SDR_PROFILE,
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
