from typing import Optional, Tuple
from ehdr.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from ehdr.typedefs.encoder_typing import EncoderSettings, HdrSdrFormat, X265Params, X265Tune, x265_x264_Preset
from ehdr.typedefs.video_typing import ContentLightLevelMetadata, MasterDisplayMetadata, build_master_display_string, build_max_cll_string
from ehdr.video import Video

class Libx265Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.HDR10,
        HdrSdrFormat.SDR,
        HdrSdrFormat.DOLBY_VISION,
    ]

    # HDR x265 parameters for HDR10 encoding
    HDR_X265_PARAMS: list[str] = [
        'hdr-opt=1',
        'repeat-headers=1',
        'colorprim=bt2020',
        'transfer=smpte2084',
        'colormatrix=bt2020nc',
    ]

    # SDR x265 parameters
    SDR_X265_PARAMS: list[str] = [
        'colorprim=bt709',
        'transfer=bt709',
        'colormatrix=bt709',
        'no-hdr10-opt=1',
    ]

    HDR_PIXEL_FORMAT = 'yuv420p10le'
    SDR_PIXEL_FORMAT = 'yuv420p'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            name="libx265",
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        self._crf: int = self._get_auto_crf()
        self._preset: x265_x264_Preset = self._get_auto_preset()
        self._tune: X265Tune | None = encoder_settings.x265_prams.tune

    def get_ffmpeg_params(self) -> dict:
        output_options: dict = super().get_ffmpeg_params()
        output_options.update({
            "preset": self._preset.value,
            "crf": str(self._crf)
        })

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            x265_params: list[str] = self._build_hdr_x265_params()
            output_options['pix_fmt'] = self.HDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            x265_params: list[str] = self._build_sdr_x265_params()
            output_options['pix_fmt'] = self.SDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)

        return output_options

    def get_custom_lib_parameters(self) -> dict:
        masterdisplay: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()

        return {
            "crf": self._crf,
            "preset": self._preset.value,
            "tune": self._tune.value if self._tune else None,
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

    def _build_hdr_x265_params(self) -> list[str]:
        """Build x265 parameters for HDR10 video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.HDR_X265_PARAMS.copy()

        master_display: MasterDisplayMetadata | None = self._get_master_display_for_encoding()
        if master_display:
            params.append(f'master-display={build_master_display_string(master_display)}')

            max_cll_max_fll: ContentLightLevelMetadata | None = self._get_max_cll_for_encoding()
            if max_cll_max_fll:
                params.append(f'max-cll={build_max_cll_string(max_cll_max_fll)}')

        return params

    def _build_sdr_x265_params(self) -> list[str]:
        """Build x265 parameters for SDR video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.SDR_X265_PARAMS.copy()
        if self._video.is_hdr_video():
            # remove HDR metadata if present
            params.append('master-display=G(0,0)B(0,0)R(0,0)WP(0,0)L(0,0)')
            params.append('max-cll=0,0')
        return params

    def _get_auto_preset(self) -> x265_x264_Preset:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)
        """
        x265_params: X265Params = self._encoder_settings.x265_prams
        if x265_params.preset is not None:
            return x265_params.preset

        pixels = self._get_pixel_count()

        # 4K+ (4096x2160 = 8,847,360 pixels)
        if pixels >= 8_847_361:
            return x265_x264_Preset.SUPERFAST # faster -> veryslow besser

        # 2K to 4K range
        if pixels >= 2_073_601:
            return x265_x264_Preset.FASTER # fast -> slow besser

        # Full HD
        if pixels >= 2_073_600:
            return x265_x264_Preset.FAST # medium

        # Lower resolutions
        return x265_x264_Preset.MEDIUM # fast -> medium ist aber auch ok, abhänig von CPU-Leistung

    def _get_auto_crf(self) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)

        libx265 generally uses higher CRF values than libx264 for similar quality. 2-5 points higher.

        TODO:
        Bei 10-Bit-Encoding kannst du den CRF-Wert um etwa +1 (manchmal sogar +2) erhöhen, ohne sichtbaren Qualitätsverlust.
        """
        x265_params: X265Params = self._encoder_settings.x265_prams
        if x265_params.crf is not None:
            return x265_params.crf

        pixels: int = self._get_pixel_count()

        # UHD 4K (3840x2160 = 8,294,400 pixels)
        if pixels >= 6_144_000:
            return 13 # 15 bei slow-preset, 14 bei medium, 13 bei fast o. faster

        # 2K to 4K range - scale linearly
        if pixels >= 2_211_841:
            # Linear interpolation between 14 (at 6.14M) and 18 (at 2.21M)
            ratio = (pixels - 2_211_841) / (6_144_000 - 2_211_841)
            return int(18 - (4 * ratio)) # 14-18

        # Full HD (1920x1080 = 2,073,600 pixels)
        if pixels >= 2_073_600:
            return 18 # 18-20

        # Lower resolutions
        if pixels >= 1_000_000:
            return 19

        return 20 # 20-22
