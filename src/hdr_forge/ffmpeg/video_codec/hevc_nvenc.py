from typing import Optional, Tuple
from hdr_forge.cli.cli_output import print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_HEVC_H264_NVENC_Preset
from hdr_forge.ffmpeg.video_codec.nvenc_base import NvencCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeSpeedPreset, HdrSdrFormat, NvencRcMode
from hdr_forge.typedefs.codec_typing import PIXEL_FORMAT_YUV420_8_BIT, CodecPreset, VideoEncoderLibrary
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.video import Video

class HevcNvencCodec(NvencCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.HDR10,
        HdrSdrFormat.HDR,
        HdrSdrFormat.SDR,
        HdrSdrFormat.DOLBY_VISION,
    ]

    PIXEL_FORMAT_10BIT = 'p010le' # 'yuv420p10le'

    HDR_PROFILE = 'main10'
    SDR_PROFILE = 'main'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.HEVC_NVENC,
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
            "preset": self._preset.codec_preset,
            "cq": str(self._cq),
        })

        pix_fmt: str | None = self.get_pix_format_for_encoding()
        if pix_fmt is not None:
            output_options["pix_fmt"] = pix_fmt

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            output_options['profile:v'] = self.HDR_PROFILE
            print_warn("HEVC_NVENC HDR Metadata for HDR/HDR10/Dolby Vision encoding is not yet supported;")
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            output_options['profile:v'] = self.SDR_PROFILE
            if self._video.is_hdr_video():
                print_warn(msg="HEVC_NVENC-SDR encoding does not support HDR metadata removal;")

        ffmpeg_root_params = self._preset.ffmpeg_params.get('root', {})
        if ffmpeg_root_params and isinstance(ffmpeg_root_params, dict):
            output_options.update(ffmpeg_root_params)

        return output_options

    def get_pix_format_for_encoding(self) -> str | None:
        bit_depth = self.get_bit_depth_for_encoding()
        if bit_depth == 10:
            return self.PIXEL_FORMAT_10BIT
        elif bit_depth == 8:
            return PIXEL_FORMAT_YUV420_8_BIT
        return super().get_pix_format_for_encoding()

    def get_bit_depth_for_encoding(self) -> int:
        return super().get_bit_depth_for_encoding()

    def get_custom_lib_parameters(self) -> dict:
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "cq": self._cq,
            "preset": self._preset.codec_preset,
            "rc": self._nvenc_rc.value,
            "master-display": build_master_display_string(masterdisplay) if masterdisplay else None,
            "max-cll": build_max_cll_string(max_cll_max_fll) if max_cll_max_fll else None,
        }

    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        master_display: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        if master_display is None and max_cll_max_fll is None:
            return None

        return HdrMetadata(
            mastering_display_metadata=master_display,
            content_light_level_metadata=max_cll_max_fll,
        )
