"""Command-line argument parsing for HDR Forge."""

import argparse

from hdr_forge import __version__
from hdr_forge.cli.cli_output import rainbow_text


def _add_version_arg(parser: argparse.ArgumentParser) -> None:
    """Add version argument to the parser.

    Args:
        parser: Argument parser to add the version argument to
    """
    logo = """
░ ▒█▒    ▒█▒ ░ ▒███████▒ ░  ▒███████▒ ░       ░ ▒████████▒ ░ ▒██████▒ ░  ▒███████▒ ░ ░ ▒██████▒ ░  ▒████████▒ ░
░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░      ░ ▒█▒ ░     ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒ ░
░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░      ░ ▒█▒ ░     ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒ ░      ░ ▒█▒ ░
░ ▒████████▒ ░ ▒█▒    ▒█▒ ░ ▒███████▒ ░       ░ ▒██████▒    ▒█▒    ▒█▒ ░ ▒███████▒    ▒█▒  ▒███▒ ░ ▒██████▒ ░
░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░      ░ ▒█▒ ░     ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒ ░
░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░      ░ ▒█▒ ░     ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒    ▒█▒ ░ ▒█▒ ░
░ ▒█▒    ▒█▒ ░ ▒███████▒ ░  ▒█▒    ▒█▒ ░      ░ ▒█▒ ░      ░ ▒██████▒ ░  ▒█▒    ▒█▒    ▒██████▒ ░  ▒████████▒ ░"""
    parser.add_argument(
        '--version',
        action='version',
        version=f"""{rainbow_text(logo)}
                                              HDR forge {__version__} - © JanKremser
"""
    )


def _add_info_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'info' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    # "info" subcommand
    info_parser: argparse.ArgumentParser = parser.add_parser('info',
        description='Shows information about a video file',
        help='Display video information'
    )

    info_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for information display'
    )


def _add_maxcll_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'calc_maxcll' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    # "maccll" subcommand
    maxcll_parser: argparse.ArgumentParser = parser.add_parser('calc_maxcll',
        description='BETA function. Calculate MaxCLL and MaxFALL values for HDR videos',
        help='Calculate MaxCLL and MaxFALL'
    )

    maxcll_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for MaxCLL and MaxFALL calculation'
    )


def _add_convert_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'convert' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    # "convert" subcommand
    convert_parser: argparse.ArgumentParser = parser.add_parser('convert',
        description='Convert videos',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Convert videos',
        epilog="""
Examples:
  hdr_forge convert -i input.mkv -o output.mkv
  hdr_forge convert -i ./input_folder -o ./output_folder
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
        choices=['x265', 'x264', 'copy'],
        default='x265',
        help="""Video codec to use for encoding.
[x265]  : x265 encoding for HDR/DolbyVision and SDR outputs.
[x264]  : x264 encoding for SDR outputs. Not recommended for HDR content.
[copy]  : Copy stream without re-encoding\n
"""
    )

    convert_parser.add_argument(
        '-p', '--preset',
        choices=["auto", "film", "action", "animation"],
        default="auto",
        help="""HDR Forge encoding preset for simplified settings. Default is the automation mode. Not x265/x264 presets.
You can combine Presets with HW-Presets.
Examples:
    hdr_forge convert -i input.mkv -o output.mkv --preset auto
    hdr_forge convert -i input.mkv -o output.mkv --preset film
Presets:
    [auto]        : Automatic preset selection based on input video characteristics. This is the default.

    [film]        : Optimized for film content with moderate motion
    [action]      : Optimized for action-packed content with fast motion
    [animation]   : Optimized for animated content with vibrant colors\n
"""
    )

    convert_parser.add_argument(
        '--hw-preset',
        choices=["cpu:balanced", "cpu:quality", "gpu:balanced", "gpu:quality", "balanced", "quality"],
        default="cpu:balanced",
        help="""HDR Forge hardware preset for encoding optimization. Not x265/x264 presets.
You can specify presets with or without hardware prefix (cpu:/gpu:).
When using prefix-free presets (balanced, quality), the hardware is automatically derived from --encoder.

Examples:
    hdr_forge convert -i input.mkv -o output.mkv --hw-preset quality
    hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc --hw-preset balanced
    hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

Prefix-free presets (hardware derived from encoder):
    [balanced] : Balanced speed and quality (default)
    [quality]  : Focus on quality. You need a high-performance system for this preset.

Explicit hardware presets (validated against encoder):
  CPU based encoding:
    [cpu:balanced] : Balanced speed and quality for CPU encoding
    [cpu:quality]  : Quality-focused for CPU encoding

  GPU based encoding:
    [gpu:balanced] : Balanced quality and size for GPU encoding
    [gpu:quality]  : Quality-focused for GPU encoding\n
"""
    # [cpu:opt]      : Optimized settings for your system with balanced speed and quality
    )

    convert_parser.add_argument(
        '--quality',
        type=int,
        help="""Universal quality parameter (0-51, lower = better quality).
Works with all encoders and automatically maps to CRF (x265/x264) or CQ (NVENC).
This is overridden by encoder-specific parameters (--encoder-params).\n
"""
    )

    convert_parser.add_argument(
        '--speed',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
        help="""Universal speed preset. ONLY works with x265/x264 encoders.
[ultrafast] : Fastest encoding, lowest compression
[superfast] : Very fast encoding, very low compression
[veryfast]  : Fast encoding, low compression
[faster]    : Below average compression and speed
[fast]      : Slightly below average compression and speed
[medium]    : Balanced compression and speed
[slow]      : Above average compression, slower encoding
[slower]    : High compression, slow encoding
[veryslow]  : Maximum compression, very slow encoding

Note: This parameter is NOT compatible with NVENC encoders. Use --encoder-params instead.\n
"""
    )

    convert_parser.add_argument(
        '--crop',
        help="""Crop black bars from video. Not supported for Dolby Vision encoding.
[off]              : Default: No cropping
[auto]             : Automatically detect and crop black bars
[width:height:x:y] : Manually specify crop dimensions. The basis for the calculation is the original video, not the target resolution.
[16:9] or [1.77:1] : 16:9, 21:9 etc. to crop to specific aspect ratio
[cinema]           : CinemaScope Classic 2.35:1 ratio
[cinema-modern]    : CinemaScope Modern 2.39:1 ratio\n
"""
    )

    convert_parser.add_argument(
        '--grain',
        help="""Analyze grain in the input video and optimize encoding settings accordingly.
[off]              : Default: Do not analyze grain
[auto]             : Automatically detect grain and adjust encoding settings
"""
    )

    convert_parser.add_argument(
        '--scale',
        help="""Scale video to specified resolution (8K, UHD, FHD, HD, SD or height in pixels)
[8K]       : 4320p
[UHD]      : 2160p
[QHD]      : 1440p
[FHD]      : 1080p
[HD]       : 720p
[SD]       : 480p
[<height>] : Specify target height in pixels (e.g., 1440 for 2560x1440). Width is calculated based on aspect ratio.
             If not specified, original resolution is maintained.\n
"""
    )

    convert_parser.add_argument(
        '--scale-mode',
        choices=['height', 'adaptive'],
        default="height",
        help="""Specifies how the video should be scaled after cropping. Not supported for Dolby Vision encoding.
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
        help="""User-specified target color format for the output video.
[auto]   : Automatically determine target color format based on input video
[hdr10]  : Convert to HDR10 format
[sdr]    : Convert to SDR format\n
"""
    )

    convert_parser.add_argument(
        '--dv-profile',
        choices=['auto', '8'],
        default='auto',
        help='Dolby Vision profile for encoding (auto = automatic detection, 8 = force profile 8.1)'
    )

    convert_parser.add_argument(
        '--sample',
        help="""Process only a short sample of the video for testing purposes. Not supported for Dolby Vision encoding
[auto]      : Process a 30 seconds sample starting at 1 minute into the video
[start:end] : Specify start and end time in seconds (e.g., 60:90 for a sample from 1:00 to 1:30)\n
"""
    )

    convert_parser.add_argument(
        '--master-display',
        help="""Expert function:
Set custom Master Display metadata for HDR10 videos. Format:
G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)

Example:
    --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"

Input Video Master Display metadata will be used if not specified.
"""
    )

    convert_parser.add_argument(
        '--max-cll',
        help="""Expert function:
Set custom MaxCLL and MaxFALL values for HDR10 videos. Format:

Example:
    --max-cll "1000,400"

Input Video MaxCLL and MaxFALL values will be used if not specified.
"""
    )

    convert_parser.add_argument(
        '--encoder',
        choices=['auto', 'libx265', 'libx264', 'hevc_nvenc', 'h264_nvenc'],
        default='auto',
        help="""Expert function:
Encoder selection override. By default, encoder is automatically selected based on --hw-preset.
[auto]         : Automatic encoder selection (default)
[libx265]      : Force libx265 encoder
[libx264]      : Force libx264 encoder
[hevc_nvenc]   : Force NVIDIA NVENC HEVC encoder
[h264_nvenc]   : Force NVIDIA NVENC H.264 encoder\n
"""
    )

    convert_parser.add_argument(
        '--encoder-params',
        help="""Expert function:
Encoder-specific parameters. Requires --encoder to be set (not 'auto').
Format depends on selected encoder:

libx265/libx264:
    preset=<value>:crf=<value>:tune=<value>
    Example: preset=slow:crf=16:tune=grain

hevc_nvenc/h264_nvenc:
    preset=<value>:cq=<value>:rc=<value>
    Example: preset=hq:cq=18:rc=vbr_hq

    NVENC Presets: default, slow, hq, llhq, llhp
    RC Modes: vbr, vbr_hq, cbr, cqp\n
"""
    )

    convert_parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug output'
    )

def parse_args():
    """Parse command-line arguments with subcommands.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='HDR Forge - HDR Video Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    _add_version_arg(parser=parser)

    # Create subcommands
    subparsers: argparse._SubParsersAction = parser.add_subparsers(dest='command', help='Subcommand')
    subparsers.required = True

    _add_info_subcommand(parser=subparsers)

    _add_maxcll_subcommand(parser=subparsers)

    _add_convert_subcommand(parser=subparsers)

    return parser.parse_args()
