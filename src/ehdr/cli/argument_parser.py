"""Command-line argument parsing for EHDR."""

import argparse

from ehdr import __version__
from ehdr.typedefs.encoder_typing import HdrSdrFormat, EncoderSettings, ScaleMode, VideoCodec
from ehdr.typedefs.dolby_vision_typing import DolbyVisionProfileEncodingMode


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
        formatter_class=argparse.RawTextHelpFormatter,
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
        '-v', '--video-codec',
        choices=['x265', 'copy'],
        help="""Video codec to use for encoding.
[x265] : auto = re-encode if needed x265
[copy] : Copy stream without re-encoding\n
"""
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
        help='Scale video to specified resolution (4K, 2K, UHD, FHD, HD, SD or height in pixels)'
    )

    convert_parser.add_argument(
        '--scale-mode',
        choices=['height', 'adaptive'],
        default="height",
        help="""Specifies how the video should be scaled after cropping.
[height]   : Uses the target height as a fixed reference. The width is calculated
             from the aspect ratio. Ideal for standardized output formats like 1080p or 4K.
[adaptive] : Scales the video dynamically to fit optimally within the target resolution,
             without exceeding the specified width or height. Maintains the aspect ratio
             and avoids unnecessary upscaling.\n
"""
    )

    convert_parser.add_argument(
        '--hdr-sdr-format',
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


def get_hdr_sdr_format_from_string(format_str: str | None) -> HdrSdrFormat:
    """Convert string to ColorFormat enum.

    Args:
        format_str: Color format string

    Returns:
        Corresponding ColorFormat enum value
    """
    if format_str is None:
        return HdrSdrFormat.AUTO

    format_str = format_str.lower()
    if format_str == 'sdr':
        return HdrSdrFormat.SDR
    elif format_str == 'hdr10':
        return HdrSdrFormat.HDR10
    elif format_str == 'dolby_vision':
        return HdrSdrFormat.DOLBY_VISION
    else:
        return HdrSdrFormat.AUTO

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


def get_video_codec_from_string(codec_str: str | None) -> VideoCodec:
    """Convert string to VideoEncoder enum.

    Args:
        codec_str: Video codec string

    Returns:
        Corresponding VideoEncoder enum value
    """
    if codec_str is None:
        return VideoCodec.X265

    codec_str = codec_str.lower()
    if codec_str == 'copy':
        return VideoCodec.COPY

    return VideoCodec.X265


def create_encoder_settings_from_args(args) -> EncoderSettings:
    """Create EncoderSettings object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()

    Returns:
        EncoderSettings object with all encoding parameters
    """
    return EncoderSettings(
        video_codec=get_video_codec_from_string(args.video_codec),
        hdr_sdr_format=get_hdr_sdr_format_from_string(args.hdr_sdr_format),
        target_dv_profile=get_dolby_vision_profile_from_string(args.dv_profile),
        crf=args.crf,
        preset=args.preset,
        scale_height=get_scale_height(args.scale),
        scale_mode=ScaleMode(args.scale_mode),
        enable_crop=not args.ncrop,
    )
