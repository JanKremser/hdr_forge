"""Command-line argument parsing for HDR Forge."""

import argparse

from hdr_forge import __version__
from hdr_forge.cli.cli_output import ANSI_BLUE, ANSI_GREEN, ANSI_ORANGE, ANSI_RED, color_str, rainbow_text


HDR_FORGE_LOGO = rainbow_text("""
▒█▒   ▒█▒ ▒██████▒  ▒██████▒      ▒██████▒  ▒█████▒   ▒██████▒    ▒█████▒  ▒██████▒
▒█▒   ▒█▒ ▒█▒   ▒█▒ ▒█▒   ▒█▒     ▒█▒      ▒█▒   ▒█▒  ▒█▒   ▒█▒  ▒█▒       ▒█▒
▒███████▒ ▒█▒   ▒█▒ ▒██████▒      ▒█████▒  ▒█▒   ▒█▒  ▒██████▒   ▒█▒ ▒██▒  ▒████▒
▒█▒   ▒█▒ ▒█▒   ▒█▒ ▒█▒   ▒█▒     ▒█▒      ▒█▒   ▒█▒  ▒█▒   ▒█▒  ▒█▒   ▒█▒ ▒█▒
▒█▒   ▒█▒ ▒██████▒  ▒█▒   ▒█▒     ▒█▒       ▒█████▒   ▒█▒   ▒█▒   ▒█████▒  ▒██████▒

▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒""")

def _add_version_arg(parser: argparse.ArgumentParser) -> None:
    """Add version argument to the parser.

    Args:
        parser: Argument parser to add the version argument to
    """
    parser.add_argument(
        '--version',
        action='version',
        version=f"""          HDR forge {__version__} - © JanKremser"""
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

    info_parser.add_argument(
        '-d', '--debug',
        action='store_true',
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

    maxcll_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )

def _add_detect_logo_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'detect_logo' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    # "detect_logo" subcommand
    detect_logo_parser: argparse.ArgumentParser = parser.add_parser('detect-logo',
        description='Detect logos in a video file',
        help='Detect logos'
    )

    detect_logo_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for logo detection'
    )

    detect_logo_parser.add_argument(
        '-e', '--export',
        help='Export detected logo mask to specified file path as PNG image'
    )

    detect_logo_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )


def _add_convert_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'convert' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    expert_dot = color_str("■", ANSI_RED)
    sdr_dot = color_str("■", ANSI_ORANGE)
    hdr_dot = color_str("■", ANSI_GREEN)
    dolby_vision_dot = color_str("■", ANSI_BLUE)

    # "convert" subcommand
    convert_parser: argparse.ArgumentParser = parser.add_parser('convert',
        description='Convert videos',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Convert videos',
        epilog=f"""
{expert_dot} EXPERT
{sdr_dot} Available for SDR
{hdr_dot} Available for HDR10/HDR
{dolby_vision_dot} Available for Dolby Vision

Examples:
  hdr_forge convert -i input.mkv -o output.mkv
  hdr_forge convert -i ./input_folder -o ./output_folder
        """
    )

    convert_parser.add_argument(
        '-i', '--input',
        required=True,
        help=f'{sdr_dot} {hdr_dot} {dolby_vision_dot} Input video file or folder'
    )

    convert_parser.add_argument(
        '-o', '--output',
        required=True,
        help=f'{sdr_dot} {hdr_dot} {dolby_vision_dot} Output video file or folder'
    )

    convert_parser.add_argument(
        '-v', '--video-codec',
        choices=['h265', 'h264', 'copy'],
        default='h265',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Video codec to use for encoding.
[h265]  : h265 encoding for HDR/DolbyVision and SDR outputs.
[h264]  : h264 encoding for SDR outputs. Not recommended for HDR content.
[copy]  : Copy stream without re-encoding\n
"""
    )

    convert_parser.add_argument(
        '-p', '--preset',
        choices=["auto", "film", "banding", "video", "action", "animation"],
        default="auto",
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
HDR Forge encoding preset for simplified settings. Default is the automation mode. Not libx265/libx264 presets.
You can combine Presets with HW-Presets.
Examples:
    hdr_forge convert -i input.mkv -o output.mkv --preset auto
    hdr_forge convert -i input.mkv -o output.mkv --preset film
Presets:
    [auto]        : Use a film preset as default.

    [film]        : Optimized for film content with moderate motion.
    [banding]     : Similar to 'film' but with additional banding reduction techniques.
                    This settings switch 8bit encoding for SDR to 10bit, reducing banding artifacts in challenging scenes.
    [video]       : Optimized for general video content. This is a neutral preset for varied content.
                    You use the default ffmpeg presets, without optimizations for specific content types.
    [action]      : Optimized for action-packed content with fast motion
    [animation]   : Optimized for animated content with vibrant colors\n
"""
    )

    convert_parser.add_argument(
        '--hw-preset',
        choices=["cpu:balanced", "cpu:quality", "gpu:balanced", "gpu:quality", "balanced", "quality"],
        default="cpu:balanced",
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
HDR Forge hardware preset for encoding optimization. Not libx265/libx264 presets.
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
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Universal quality parameter (0-51, lower = better quality).
Works with all encoders and automatically maps to CRF (libx265/libx264) or CQ (NVENC).
This is overridden by encoder-specific parameters (--encoder-params).\n
"""
    )

    convert_parser.add_argument(
        '--speed',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'medium:plus', 'slow', 'slow:plus', 'slower', 'veryslow'],
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Universal speed preset. ONLY works with libx265/libx264 encoders.
[ultrafast]   : Fastest encoding, lowest compression
[superfast]   : Very fast encoding, very low compression
[veryfast]    : Fast encoding, low compression
[faster]      : Below average compression and speed
[fast]        : Slightly below average compression and speed
[medium]      : Balanced compression and speed
[medium:plus] : Slightly better compression and quality than medium, with a moderate speed decrease
[slow]        : Above average compression, slower encoding
[slow:plus]   : better quality/speed tradeoff than slow
[slower]      : High compression, slow encoding
[veryslow]    : Maximum compression, very slow encoding

Note: This parameter is NOT compatible with NVENC encoders. Use --encoder-params instead.\n
"""
    )

    convert_parser.add_argument(
        '--grain',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Analyze grain in the input video and optimize encoding settings accordingly.
[off]              : Default: Do not analyze grain
[auto]             : Automatically detect grain and adjust encoding settings
[cat1]             : Apply light grain settings
[cat2]             : Apply medium grain settings
[cat3]             : Apply strong grain settings\n
"""
    )

    convert_parser.add_argument(
        '--remove-logo',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Remove logos from video. Not supported for Dolby Vision encoding.
Examples:
    --remove-logo off
    --remove-logo auto
    --remove-logo delogo:top-left
    --remove-logo mask:auto
[off]              : Default: Do not remove logos
[auto]             : Automatically detect and remove logo

[delogo:auto]      : Automatically detect and remove logo with delogo filter
[delogo:top-left]  : Automatically detect (top-left) and remove logo with delogo filter
[delogo:top-right] : Automatically detect (top-right) and remove logo with delogo filter
[delogo:bot-left]  : Automatically detect (bottom-left) and remove logo with delogo filter
[delogo:bot-right] : Automatically detect (bottom-right) and remove logo with delogo filter

[mask:auto]        : Automatically detect logo and apply mask-based removal
[mask:top-left]    : Automatically detect (top-left) logo and apply mask-based removal
[mask:top-right]   : Automatically detect (top-right) logo and apply mask-based removal
[mask:bot-left]    : Automatically detect (bottom-left) logo and apply mask-based removal
[mask:bot-right]   : Automatically detect (bottom-right) logo and apply\n
"""
    )

    convert_parser.add_argument(
        '--crop',
        help=f"""{sdr_dot} {hdr_dot}
Crop black bars from video. Not supported for Dolby Vision encoding.
[off]              : Default: No cropping
[auto]             : Automatically detect and crop black bars
[width:height:x:y] : Manually specify crop dimensions. The basis for the calculation is the original video, not the target resolution.
[16:9] or [1.77:1] : 16:9, 21:9 etc. to crop to specific aspect ratio
[european]         : European Widescreen 1.66:1 ratio
[us-widescreen]    : US Widescreen 1.85:1 ratio
[cinema]           : CinemaScope Classic 2.35:1 ratio
[cinema-modern]    : CinemaScope Modern 2.39:1 ratio\n
"""
    )

    convert_parser.add_argument(
        '--scale',
        help=f"""{sdr_dot} {hdr_dot}
Scale video to specified resolution. Default is original resolution.
[FUHD]     : 4320p (8K)
[UHD]      : 2160p (4K)
[QHD+]     : 1800p
[WQHD]     : 1440p
[FHD]      : 1080p (Full HD)
[HD]       : 720p  (HD ready)
[QHD]      : 540p
[SD]       : 480p
[<height>] : Specify target height in pixels (e.g., 1440 for 2560x1440). Width is calculated based on aspect ratio.
             If not specified, original resolution is maintained.\n
"""
    )

    convert_parser.add_argument(
        '--scale-mode',
        choices=['height', 'adaptive'],
        default="height",
        help=f"""{sdr_dot} {hdr_dot}
Specifies how the video should be scaled after cropping. Not supported for Dolby Vision encoding.
[height]   : Uses the target height as a fixed reference. The width is calculated
             from the aspect ratio. Ideal for standardized output formats like 1080p or 4K.
[adaptive] : Scales the video dynamically to fit optimally within the target resolution,
             without exceeding the specified width or height. Maintains the aspect ratio
             and avoids unnecessary upscaling.\n
"""
    )

    convert_parser.add_argument(
        '--dar-ratio',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Set custom Display Aspect Ratio (DAR) for the output video.
This only changes the display, not the pixel ratio.
Format:
    [width:height]     : Specify aspect ratio (e.g., 16:9, 4:3, 1.85:1)
    [european]         : European Widescreen 1.66:1 ratio
    [us-widescreen]    : US Widescreen 1.85:1 ratio
    [cinema]           : CinemaScope Classic 2.35:1 ratio
    [cinema-modern]    : CinemaScope Modern 2.39:1 ratio
Example:
    --dar-ratio 16:9
    --dar-ratio cinema
    --dar-ratio 1.4:1\n
"""
    )

    convert_parser.add_argument(
        '--hdr-sdr-format',
        choices=['auto', 'hdr10', 'hdr', 'sdr'],
        default='auto',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
User-specified target color format for the output video.
[auto]   : Automatically determine target color format based on input video
[hdr10]  : Convert to HDR10 format
[hdr]    : Convert to HDR format, without HDR10 metadata
[sdr]    : Convert to SDR format\n
"""
    )

    convert_parser.add_argument(
        '--dv-profile',
        choices=['auto', '8'],
        default='auto',
        help=f"""{dolby_vision_dot}
Dolby Vision profile for encoding (auto = automatic detection, 8 = force profile 8.1)\n
"""
    )

    convert_parser.add_argument(
        '--sample',
        help=f"""{sdr_dot} {hdr_dot} {expert_dot}
Process only a short sample of the video for testing purposes. Not supported for Dolby Vision encoding.
[auto]      : Process a 30 seconds sample starting at 1 minute into the video
[start:end] : Specify start and end time in seconds (e.g., 60:90 for a sample from 1:00 to 1:30)\n
"""
    )

    convert_parser.add_argument(
        '--vfilter',
        help=f"""{sdr_dot} {hdr_dot} {expert_dot}
Expert Option:
Add custom FFmpeg video filters.
If you want to overwrite settings, avoid using these arguments.
    --crop, --scale, --scale-mode, --hdr-sdr-format
Otherwise, your filter will be placed at the beginning of the filter chain.

Format:
    filter1,filter2,filter3
Example:
    --vfilter "eq=contrast=1.2:brightness=0.05:saturation=1.25:gamma=1.15,crop=1920:800:0:140"
"""
    )

    convert_parser.add_argument(
        '--master-display',
        help=f"""{hdr_dot} {expert_dot}
Expert Option:
    Set custom Master Display metadata for HDR10 videos.
    Not supported for GPU encoding.

Example:
    --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"
    --master-display "display-p3"
    --master-display "bt.2020"
    --master-display "bt.709"

Input Video Master Display metadata will be used if not specified.
"""
    )

    convert_parser.add_argument(
        '--max-cll',
        help=f"""{hdr_dot} {expert_dot}
Expert Option:
    Set custom MaxCLL and MaxFALL values for HDR10 videos.
    Not supported for GPU encoding.

Example:
    --max-cll "1000,400"

Input Video MaxCLL and MaxFALL values will be used if not specified.
"""
    )

    convert_parser.add_argument(
        '--encoder',
        choices=['auto', 'libx265', 'libx264', 'libsvtav1', 'hevc_nvenc', 'h264_nvenc'],
        default='auto',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot} {expert_dot}
Expert Option:
    Encoder selection override. By default, encoder is automatically selected based on --hw-preset.
[auto]         : Automatic encoder selection (default)
[libx265]      : Force libx265 encoder
[libx264]      : Force libx264 encoder
[libsvtav1]    : Force libsvtav1 encoder
[hevc_nvenc]   : Force NVIDIA NVENC HEVC encoder
[h264_nvenc]   : Force NVIDIA NVENC H.264 encoder\n
"""
    )

    convert_parser.add_argument(
        '--encoder-params',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot} {expert_dot}
Expert Option:
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
        '-s', '--shutdown',
        action='store_true',
        help=f"""{sdr_dot} {hdr_dot} {dolby_vision_dot}
Shutdown the system after conversion is complete.\n
"""
    )

    convert_parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help=f"""{expert_dot}
Enable debug output\n
"""
    )

def _add_extract_dolby_vision_hdr_metadata_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'extract_dv_metadata' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    inject_parser: argparse.ArgumentParser = parser.add_parser('extract-metadata',
        description="""
Extract Dolby Vision/HDR10 and/or HDR10Plus metadata from a encoded video file.
""",
        help='Extract Dolby Vision metadata'
    )

    inject_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input Video file'
    )

    inject_parser.add_argument(
        '-o', '--output',
        required=False,
        help='Output folder for extracted HDR-JSON, RPU and EL files'
    )

    inject_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )

def _add_inject_dolby_vision_hdr_metadata_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'inject_metadata' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    inject_parser: argparse.ArgumentParser = parser.add_parser('inject-metadata',
        description="""
Inject Dolby Vision/HDR10 and/or HDR10Plus metadata into an existing HEVC video stream, without re-encoding.
NVENC GPU-encoded videos cannot be retroactively assigned HDR metadata using this function.
Only CPU-encoded videos can be retroactively assigned HDR metadata.
""",
        help='Inject Dolby Vision metadata'
    )

    inject_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input Video file'
    )

    inject_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output video file'
    )

    inject_parser.add_argument(
        '--rpu',
        required=False,
        help="""
Path to the RPU file containing Dolby Vision metadata to be injected.
Example:
    --rpu "path/to/dolby_vision.rpu"
"""
    )

    inject_parser.add_argument(
        '--el',
        required=False,
        help="""
Path to the EL file containing Dolby Vision enhancement layer data to be injected.
The “.hevc” extension is important; without this change, an error will occur.
Example:
    --el "path/to/dolby_vision.hevc"
"""
    )

    inject_parser.add_argument(
        '--hdr10',
        required=False,
        help="""
Path to HDR10 metadata JSON file to be injected.
Example:
    --hdr10 "path/to/hdr10_metadata.json"
"""
    )

    inject_parser.add_argument(
        '--hdr10plus',
        required=False,
        help="""
Path to HDR10 metadata JSON file to be injected.
Example:
    --hdr10plus "path/to/hdr10plus_metadata.json"
"""
    )

#     inject_parser.add_argument(
#         '--master-display',
#         required=True,
#         help="""
# Set custom Master Display metadata for HDR10 videos. Format:
# G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)

# Example:
#     --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"
# """
#     )

#     inject_parser.add_argument(
#         '--max-cll',
#         required=False,
#         help="""
# Set custom MaxCLL and MaxFALL values for HDR10 videos. Format:

# Example:
#     --max-cll "1000,400"
# """
#     )

    inject_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )

def parse_args():
    """Parse command-line arguments with subcommands.

    Returns:
        Parsed arguments namespace
    """
    print(HDR_FORGE_LOGO + "\n")
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

    _add_extract_dolby_vision_hdr_metadata_subcommand(parser=subparsers)

    _add_inject_dolby_vision_hdr_metadata_subcommand(parser=subparsers)

    _add_detect_logo_subcommand(parser=subparsers)

    return parser.parse_args()
