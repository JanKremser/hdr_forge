from typing import Optional, Tuple
from hdr_forge.cli.cli_output import print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_HEVC_H264_NVENC_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HEVC_NVENC_Preset, HdrForgeEncodingPresets, HdrSdrFormat, VideoEncoderLibrary
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.video import Video

class HevcNvencCodec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.HDR10,
        HdrSdrFormat.SDR,
        HdrSdrFormat.DOLBY_VISION,
    ]

    HDR_PIXEL_FORMAT = 'p010le' # 'yuv420p10le'
    SDR_PIXEL_FORMAT = 'yuv420p'

    HDR_PROFILE = 'main10'
    SDR_PROFILE = 'main'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.HEVC_NVENC,
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

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            output_options['pix_fmt'] = self.HDR_PIXEL_FORMAT
            output_options['profile:v'] = self.HDR_PROFILE

            master_display: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
            if master_display:
                metadata: list = output_options.get('metadata:s:v', []) or []
                metadata.append(f'master-display={build_master_display_string(master_display)}')
                max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()
                if max_cll_max_fll:
                    metadata.append(f'max-cll={build_max_cll_string(max_cll_max_fll)}')
                output_options['metadata:s:v'] = metadata

            if encoding_hdr_sdr_format in [HdrSdrFormat.DOLBY_VISION]:
                print_warn("HEVC_NVENC HDR Metadata for Dolby Vision encoding is not yet supported;")
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            output_options['pix_fmt'] = self.SDR_PIXEL_FORMAT
            output_options['profile:v'] = self.SDR_PROFILE
            if self._video.is_hdr_video():
                print_warn("HEVC_NVENC-SDR encoding does not support HDR metadata removal;")

        return output_options

    def get_custom_lib_parameters(self) -> dict:
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "cq": self._cq,
            "preset": self._preset.value,
            "master-display": build_master_display_string(masterdisplay) if masterdisplay else None,
            "max-cll": build_max_cll_string(max_cll_max_fll) if max_cll_max_fll else None,
        }

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
