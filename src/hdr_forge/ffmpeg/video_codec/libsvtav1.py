from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_AV1_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingTuningPresets, HdrSdrFormat
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from hdr_forge.typedefs.codec_typing import PIXEL_FORMAT_YUV420_10_BIT, PIXEL_FORMAT_YUV420_8_BIT, VideoEncoderLibrary
from hdr_forge.video import Video

class LibSvtAV1Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.HDR,
        HdrSdrFormat.HDR10,
        HdrSdrFormat.SDR,
    ]

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.LIBSVTAV1,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_AV1_Preset = self.calc_hw_preset_settings(Hdr_Forge_AV1_Preset)
        self._crf: int = self._get_auto_crf(hw_preset)
        self._preset: int = self._get_auto_preset(hw_preset)

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "preset": str(self._preset), # smaller equals slower (0-13)
            "crf": str(self._crf), # can be 7 higher than x265
        })

        pix_fmt: str | None = self.get_pix_format_for_encoding()
        if pix_fmt is not None:
            output_options["pix_fmt"] = pix_fmt

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10]:
            output_options['color_primaries'] = 'bt2020'
            output_options['color_trc'] = 'smpte2084'
            output_options['colorspace'] = 'bt2020nc'
            output_options['svtav1-params'] = 'enable-hdr=1'

            # No OBU-based HDR10 metadata support in SVT-AV1, so we have to pass it via FFmpeg's metadata:s:v:0 options if available for HDR10 output
            # SVT-AV1 set a Site Data flag in the bitstream for HDR10 content. This is a Site Date form a input Video.
            if encoding_hdr_sdr_format == HdrSdrFormat.HDR10:
                metadata_sv0: list[str] = []
                master_display: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
                if master_display:
                    metadata_sv0.append(f'mastering_display_metadata={build_master_display_string(master_display)}')
                max_cll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()
                if max_cll:
                    metadata_sv0.append(f'content_light_level={build_max_cll_string(max_cll)}')
                if metadata_sv0:
                    output_options['metadata:s:v:0'] = metadata_sv0
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR and self._video.is_hdr_video():
            # Explicitly set BT.709 flags for HDR→SDR tonemapped output
            # (base class handles filter chain and metadata:s:v, but not codec-level color signaling)
            output_options['color_primaries'] = 'bt709'
            output_options['color_trc'] = 'bt709'
            output_options['colorspace'] = 'bt709'

        return output_options

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
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "crf": self._crf,
            "preset": self._preset,
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

    def _get_auto_preset(self, hw_preset: Hdr_Forge_AV1_Preset) -> int:
        """Select optimal encoding preset based on parameter priority.

        Returns:
            SVT-AV1 preset as int (0=slowest, 13=fastest)
        """
        # Priority 1: universal_params from --speed
        universal_params = self._encoder_settings.universal_params
        if universal_params.speed is not None:
            # Map HdrForgeSpeedPreset string to AV1 integer (0=slowest, 13=fastest)
            speed_to_av1 = {
                "ultrafast": 12,
                "superfast": 10,
                "veryfast": 9,
                "faster": 8,
                "fast": 7,
                "medium": 6,
                "slow": 5,
                "slower": 4,
                "veryslow": 3,
            }
            return speed_to_av1.get(universal_params.speed.value, 6)

        # Priority 2: hw_preset integer (from presets.py)
        return hw_preset.preset

    def _get_auto_crf(self, hw_preset: Hdr_Forge_AV1_Preset) -> int:
        """Calculate optimal CRF value based on parameter priority.

        Returns:
            CRF value (lower = higher quality)
        """
        # Priority 1: universal_params from --quality
        universal_params = self._encoder_settings.universal_params
        if universal_params.quality is not None:
            return universal_params.quality

        # Priority 2: Auto-detection from hw_preset
        crf: float = hw_preset.crf
        if self.is_hdr_encoding():
            crf += 1.0  # 10-Bit HDR allows slightly higher CRF without quality loss

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingTuningPresets.ACTION else 0.0  # Action preset lowers CRF for better handling of fast motion
        if action_crf > 0:
            action_w = self._calculate_crf_adjustment_weight(
                current_crf=crf,
                crf_delta=action_crf,
            )
            crf -= action_crf * action_w

        return round(crf)
