"""Command-line argument parsing for EHDR."""

import argparse

from ehdr import __version__
from ehdr.typing.encoder_typing import ColorFormat
from ehdr.typing.dolby_vision_typing import DolbyVisionProfileEncodingMode


# Resolution constants
RESOLUTIONS = {
    'UHD': 2160,
    'QHD': 1440,
    'FHD': 1080,
    'HD': 720,
    'SD': 480
}


def parse_args():
    """Parse command-line arguments with subcommands.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='EHDR - Easy HDR Video Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'EHDR {__version__}'
    )

    # Create subcommands
    subparsers = parser.add_subparsers(dest='command', help='Subcommand')
    subparsers.required = True

    # "info" subcommand
    info_parser = subparsers.add_parser('info',
        description='Shows information about a video file',
        help='Display video information'
    )

    info_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for information display'
    )

    # "maccll" subcommand
    maxcll_parser = subparsers.add_parser('calc_maxcll',
        description='BETA function. Calculate MaxCLL and MaxFALL values for HDR videos',
        help='Calculate MaxCLL and MaxFALL'
    )

    maxcll_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for MaxCLL and MaxFALL calculation'
    )

    # "convert" subcommand
    convert_parser = subparsers.add_parser('convert',
        description='Convert videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Convert videos',
        epilog="""
Examples:
  ehdr convert -i input.mkv -o output.mkv
  ehdr convert -i input.mkv -o output.mkv --crf 16 --preset slow
  ehdr convert -i input.mkv -o output.mkv --dv --ncrop
  ehdr convert -i ./input_folder -o ./output_folder
        """
    )

    convert_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input video file or folder'
    )

    convert_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output video file or folder'
    )

    convert_parser.add_argument(
        '--crf',
        type=int,
        help='Constant Rate Factor for quality (lower = higher quality). Auto-calculated if not specified.'
    )

    convert_parser.add_argument(
        '-p', '--preset',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster',
                 'fast', 'medium', 'slow', 'slower', 'veryslow'],
        help='Encoding preset (speed vs compression). Auto-calculated if not specified.'
    )

    convert_parser.add_argument(
        '--ncrop',
        action='store_true',
        help='Disable automatic black bar cropping'
    )

    convert_parser.add_argument(
        '--scale',
        help='Scale video to specified resolution (4K, 2K, UHD, FHD, HD, SD or width in pixels)'
    )

    convert_parser.add_argument(
        '--color-format',
        choices=['auto', 'hdr10', 'sdr'],
        default='auto',
        help='Target color format for output video (auto = keep source format, hdr10 = convert to HDR10, sdr = convert to SDR)'
    )

    convert_parser.add_argument(
        '--dv-profile',
        choices=['auto', '8'],
        default='auto',
        help='Dolby Vision profile for encoding (auto = automatic detection, 8 = force profile 8.1)'
    )

    return parser.parse_args()


def get_scale_height(scale: str | None) -> int | None:
    """Get target height from scale argument.
    Args:
        scale: Scale argument string
    Returns:
        Target height in pixels or None
    """

    target_height = None
    if scale:
        if scale.upper() in RESOLUTIONS:
            target_height = RESOLUTIONS[scale.upper()]
        else:
            try:
                # Try to parse as integer height
                target_height = int(scale)
            except ValueError:
                print(f"Warning: Invalid scale value '{scale}', using original size")

    return target_height


def get_color_format_from_string(format_str: str | None) -> ColorFormat:
    """Convert string to ColorFormat enum.

    Args:
        format_str: Color format string

    Returns:
        Corresponding ColorFormat enum value
    """
    if format_str is None:
        return ColorFormat.AUTO

    format_str = format_str.lower()
    if format_str == 'sdr':
        return ColorFormat.SDR
    elif format_str == 'hdr10':
        return ColorFormat.HDR10
    elif format_str == 'dolby_vision':
        return ColorFormat.DOLBY_VISION
    else:
        return ColorFormat.AUTO

def get_dolby_vision_profile_from_string(profile_str: str | None) -> DolbyVisionProfileEncodingMode:
    """Convert string to DolbyVision enum.

    Args:
        profile_str: Dolby Vision profile string

    Returns:
        Corresponding DolbyVision enum value
    """
    if profile_str is None:
        return DolbyVisionProfileEncodingMode.AUTO

    profile_str = profile_str.lower()
    if profile_str == '8':
        return DolbyVisionProfileEncodingMode._8

    return DolbyVisionProfileEncodingMode.AUTO
