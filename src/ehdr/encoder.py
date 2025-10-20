"""Video encoder configuration and parameter building."""

from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from ehdr.video import Video


class ColorFormat(Enum):
    """Target color format for video encoding."""
    AUTO = "auto"
    SDR = "sdr"
    HDR10 = "hdr10"
    DOLBY_VISION = "dolby_vision"


class Encoder:
    """Handles video encoding configuration for different color formats."""

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
    ]

    HDR_PIXEL_FORMAT = 'yuv420p10le'
    SDR_PIXEL_FORMAT = 'yuv420p'

    def __init__(
        self,
        video: Video,
        target_format: ColorFormat = ColorFormat.AUTO,
        crf: Optional[int] = None,
        preset: Optional[str] = None,
    ):
        """Initialize encoder with video and target color format.

        Args:
            video: Video object with metadata
            target_format: Target color format (AUTO, SDR, HDR10, DOLBY_VISION)
            crf: Optional CRF override (overrides video's CRF)
            preset: Optional preset override (overrides video's preset)
        """
        self.video = video
        self.target_format = target_format
        self.crf = crf if crf is not None else video.get_crf()
        self.preset = preset if preset is not None else video.get_preset()

        # Determine effective color format
        self.effective_format = self._determine_effective_format()

    def _determine_effective_format(self) -> ColorFormat:
        """Determine the effective color format based on target and source.

        Only downgrades are allowed (DV→HDR10→SDR). Upgrades are not possible.

        Returns:
            Effective ColorFormat to use for encoding
        """
        # Determine source format
        if self.video.is_dolby_vision_video():
            source_format = ColorFormat.DOLBY_VISION
        elif self.video.is_hdr_video():
            source_format = ColorFormat.HDR10
        else:
            source_format = ColorFormat.SDR

        if self.target_format == ColorFormat.AUTO:
            # Auto mode: keep source format
            return source_format

        # Check if conversion is valid (only downgrades allowed)
        format_hierarchy = {
            ColorFormat.SDR: 0,
            ColorFormat.HDR10: 1,
            ColorFormat.DOLBY_VISION: 2
        }

        source_level = format_hierarchy[source_format]
        target_level = format_hierarchy[self.target_format]

        if target_level > source_level:
            # Attempting upgrade - not allowed, keep source
            print(f"Warning: Cannot upgrade from {source_format.value} to {self.target_format.value}. Keeping source format.")
            return source_format

        # Valid downgrade
        return self.target_format

    def is_dolby_vision(self) -> bool:
        """Check if encoding to Dolby Vision format."""
        return self.effective_format == ColorFormat.DOLBY_VISION

    def is_hdr10(self) -> bool:
        """Check if encoding to HDR10 format."""
        return self.effective_format == ColorFormat.HDR10

    def is_sdr(self) -> bool:
        """Check if encoding to SDR format."""
        return self.effective_format == ColorFormat.SDR

    def build_ffmpeg_output_options(self) -> Dict[str, str]:
        """Build FFmpeg output options dictionary for encoding.

        Returns:
            Dictionary of FFmpeg output options
        """
        output_options: dict = {
            'c:v': 'libx265',
            'preset': self.preset,
            'crf': str(self.crf),
            'c:a': 'copy',
            'c:s': 'copy'
        }

        # Add format-specific parameters
        if self.is_hdr10():
            x265_params: list[str] = self._build_hdr_x265_params()
            output_options['pix_fmt'] = self.HDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)
        elif self.is_sdr():
            x265_params: list[str] = self._build_sdr_x265_params()
            output_options['pix_fmt'] = self.SDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)

        # Add video filters (crop and scale)
        crop_filter: str | None = self.video.get_crop_filter()
        if crop_filter:
            output_options['vf'] = crop_filter

        scale_filter: str | None = self.video.get_scale_filter()
        if scale_filter:
            if 'vf' in output_options:
                output_options['vf'] += f',{scale_filter}'
            else:
                output_options['vf'] = scale_filter

        return output_options

    def _build_hdr_x265_params(self) -> list[str]:
        """Build x265 parameters for HDR10 video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.HDR_X265_PARAMS.copy()

        master_display = self.video.get_master_display()
        if master_display:
            params.append(f'master-display={master_display}')

            max_cll_max_fall: Tuple[int, int] | None = self.video.get_max_cll_max_fall()
            if max_cll_max_fall:
                max_cll, max_fall = max_cll_max_fall
                params.append(f'max-cll={max_cll},{max_fall}')

        return params

    def _build_sdr_x265_params(self) -> list[str]:
        """Build x265 parameters for SDR video encoding.

        Returns:
            list of x265 parameter strings
        """
        return self.SDR_X265_PARAMS.copy()

    def build_x265_command(self, output_file: Path, rpu_file: Optional[str] = None) -> list[str]:
        """Build x265 command for Dolby Vision encoding.

        Args:
            output_file: Output file path
            rpu_file: Path to RPU file for Dolby Vision (required if is_dolby_vision)

        Returns:
            list of x265 command arguments
        """
        crf = self.crf
        preset = self.preset

        x265_cmd: list[str] = [
            'x265',
            '-',
            '--input-depth', '10',
            '--output-depth', '10',
            '--y4m',
            '--preset', preset,
            '--crf', str(crf),
        ]

        if self.is_dolby_vision():
            # Dolby Vision specific parameters
            master_display = self.video.get_master_display()
            if master_display:
                x265_cmd.extend(['--master-display', master_display])

            max_cll_max_fall: Tuple[int, int] | None = self.video.get_max_cll_max_fall(return_fallback=True)
            if max_cll_max_fall:
                max_cll, max_fall = max_cll_max_fall
                x265_cmd.extend(['--max-cll', f'{max_cll},{max_fall}'])

            x265_cmd.extend([
                '--colormatrix', self.video.get_color_space(),
                '--colorprim', self.video.get_color_primaries(),
                '--transfer', self.video.get_color_transfer(),
            ])

            if rpu_file:
                x265_cmd.extend([
                    '--dolby-vision-rpu', rpu_file,
                    '--dolby-vision-profile', '8.1',
                ])

            x265_cmd.extend([
                '--vbv-bufsize', '20000',
                '--vbv-maxrate', '20000',
                f'{str(output_file)}.hevc'
            ])
        elif self.is_hdr10():
            # HDR10 parameters for x265
            master_display = self.video.get_master_display()
            if master_display:
                x265_cmd.extend(['--master-display', master_display])

            max_cll_max_fall: Tuple[int, int] | None = self.video.get_max_cll_max_fall(return_fallback=True)
            if max_cll_max_fall:
                max_cll, max_fall = max_cll_max_fall
                x265_cmd.extend(['--max-cll', f'{max_cll},{max_fall}'])

            x265_cmd.extend([
                '--colormatrix', 'bt2020nc',
                '--colorprim', 'bt2020',
                '--transfer', 'smpte2084',
                f'{str(output_file)}.hevc'
            ])
        else:
            # SDR parameters for x265
            x265_cmd.extend([
                '--colormatrix', 'bt709',
                '--colorprim', 'bt709',
                '--transfer', 'bt709',
                f'{str(output_file)}.hevc'
            ])

        return x265_cmd

    def get_format_name(self) -> str:
        """Get human-readable format name.

        Returns:
            Format name string
        """
        if self.is_dolby_vision():
            return "Dolby Vision"
        elif self.is_hdr10():
            return "HDR10"
        else:
            return "SDR"
