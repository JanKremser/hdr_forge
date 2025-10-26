"""Command-line argument parsing for HDR Forge."""

import argparse
import sys

from hdr_forge import __version__
from hdr_forge.cli.cli_output import print_err
from hdr_forge.typedefs.encoder_typing import CropMode, CropSettings, HdrForgeEncodingHardwarePresets, HdrForgeEncodingPresetSettings, HdrForgeEncodingPresets, HdrSdrFormat, EncoderSettings, SampleSettings, ScaleMode, VideoCodec, X264Params, X264Tune, X265Params, X265Tune, x265_x264_Preset
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfileEncodingMode
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata


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
        description='HDR Forge - HDR Video Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'HDR Forge {__version__}'
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
    maxcll_parser: argparse.ArgumentParser = subparsers.add_parser('calc_maxcll',
        description='BETA function. Calculate MaxCLL and MaxFALL values for HDR videos',
        help='Calculate MaxCLL and MaxFALL'
    )

    maxcll_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for MaxCLL and MaxFALL calculation'
    )

    # "convert" subcommand
    convert_parser: argparse.ArgumentParser = subparsers.add_parser('convert',
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
        '--x265-params',
        help="""Custom x265 parameters for advanced users. Format:
Example:
    preset=medium,crf=20
Parameters:
    preset= : x265 encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
              [ultrafast] : Lowest compression, fastest encoding
              [superfast] : Very low compression, very fast encoding
              [veryfast]  : Low compression, fast encoding
              [faster]    : Below average compression and speed
              [fast]      : Slightly below average compression and speed
              [medium]    : Balanced compression and speed
              [slow]      : Above average compression, slower encoding
              [slower]    : High compression, slow encoding
              [veryslow]  : Maximum compression, very slow encoding
    crf=    : Constant Rate Factor for quality control (lower = better quality).
              The range of the CRF scale is 0–51
    tune=   : x265 tuning for specific content types (animation, grain)
"""
    )

    convert_parser.add_argument(
        '--x264-params',
        help="""Custom x264 parameters for advanced users. Format:
Example:
    preset=medium:crf=20:tune=film
Parameters:
    preset= : x264 encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
              [ultrafast] : Lowest compression, fastest encoding
              [superfast] : Very low compression, very fast encoding
              [veryfast]  : Low compression, fast encoding
              [faster]    : Below average compression and speed
              [fast]      : Slightly below average compression and speed
              [medium]    : Balanced compression and speed
              [slow]      : Above average compression, slower encoding
              [slower]    : High compression, slow encoding
              [veryslow]  : Maximum compression, very slow encoding
    crf=    : Constant Rate Factor for quality control (lower = better quality).
              The range of the CRF scale is 0–51
    tune=   : x264 tuning for specific content types (film, animation, grain)
"""
    )

    convert_parser.add_argument(
        '-p', '--preset',
        choices=["auto", "film", "grain", "action", "animation", "web"],
        default="auto",
        help="""HDR Forge encoding preset for simplified settings. Default is the automation mode. Not x265/x264 presets.
You can combine Presets with HW-Presets.
Examples:
    hdr_forge convert -i input.mkv -o output.mkv --preset auto
    hdr_forge convert -i input.mkv -o output.mkv --preset film
Presets:
    [auto]        : Automatic preset selection based on input video characteristics. This is the default.

    [film]        : Optimized for film content with moderate motion
    [grain]       : Optimized for content with film grain preservation
    [action]      : Optimized for action-packed content with fast motion
    [animation]   : Optimized for animated content with vibrant colors\n
"""
    )

    convert_parser.add_argument(
        '--hw-preset',
        choices=["cpu:balanced", "cpu:opt", "cpu:quality", "cpu:best"],
        default="cpu:balanced",
        help="""HDR Forge hardware preset for encoding optimization. Not x265/x264 presets.
Examples:
    hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality
Presets:
  CPU based encoding:
    [cpu:balanced] : Balanced speed and quality, this is the default for CPU encoding
    [cpu:quality]  : Focus on quality. You need a high-performance system for this preset.\n
"""
    # [cpu:opt]      : Optimized settings for your system with balanced speed and quality
    # [gpu-balanced]
    # [gpu-opt]
    # [gpu-quality]
    # [gpu-best]
    )

    convert_parser.add_argument(
        '--crop',
        help="""Crop black bars from video. Not supported for Dolby Vision encoding.
[auto]             : Automatically detect and crop black bars
[width:height:x:y] : Manually specify crop dimensions. The basis for the calculation is the original video, not the target resolution.
[16:9] or [1.77:1] : 16:9, 21:9 etc. to crop to specific aspect ratio
[cinema]           : CinemaScope Classic 2.35:1 ratio\n
[cinema-modern]    : CinemaScope Modern 2.39:1 ratio\n
"""
    )

    convert_parser.add_argument(
        '--scale',
        help='Scale video to specified resolution (4K, 2K, UHD, FHD, HD, SD or height in pixels)'
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
        '--master-display',
        help="""Set custom Master Display metadata for HDR10 videos. Format:
G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)
Example:
--master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"
Input Video Master Display metadata will be used if not specified.
"""
    )

    convert_parser.add_argument(
        '--max-cll',
        help="""Set custom MaxCLL and MaxFALL values for HDR10 videos. Format:
MaxCLL,MaxFALL
Example:
--max-cll "1000,400"
Input Video MaxCLL and MaxFALL values will be used if not specified.
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
        '-d', '--debug',
        action='store_true',
        help='Enable debug output'
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
    elif codec_str == 'x264':
        return VideoCodec.X264

    return VideoCodec.X265


def get_crop_settings_from_string(crop_str: str | None) -> CropSettings:
    """Convert crop argument string to CropSettings object.

    Args:
        crop_str: Crop argument string

    Returns:
        CropSettings object
    """
    if crop_str is None:
        return CropSettings(mode=CropMode.OFF)

    # Preset for cinema aspect ratios
    if crop_str.lower() == 'cinema':
        crop_str = '2.35:1'
    elif crop_str.lower() == 'cinema-modern':
        crop_str = '2.39:1'

    if crop_str.lower() == 'auto':
        return CropSettings(mode=CropMode.AUTO)
    elif ':' in crop_str:
        parts = crop_str.split(':')
        if len(parts) == 4:
            try:
                w, h, x, y = map(int, parts)
                return CropSettings(mode=CropMode.MANUAL, manual_crop=(x, y, w, h))
            except ValueError:
                pass
        elif len(parts) == 2:
            try:
                ar_w, ar_h = map(float, parts)
                return CropSettings(mode=CropMode.RATIO, ratio=(ar_w, ar_h))
            except ValueError:
                pass
    print_err(f"Invalid crop value '{crop_str}', using automatic cropping")
    sys.exit(1)


def get_sample_settings_from_string(sample_str: str | None) -> SampleSettings:
    """Convert sample argument string to SampleSettings object.

    Args:
        sample_str: Sample argument string

    Returns:
        SampleSettings object
    """
    if sample_str is None:
        return SampleSettings(enabled=False)

    if sample_str.lower() == 'auto':
        return SampleSettings(enabled=True, start_time=None, end_time=None)

    if ':' in sample_str:
        parts = sample_str.split(':')
        if len(parts) == 2:
            try:
                start = float(parts[0])
                end = float(parts[1])
                return SampleSettings(enabled=True, start_time=start, end_time=end)
            except ValueError:
                pass
    print(f"Warning: Invalid sample value '{sample_str}', not using sampling")
    return SampleSettings(enabled=False)


def get_master_display_from_string(md_str: str | None) -> MasterDisplayMetadata | None:
    """Convert master display argument string.

    Args:
        md_str: Master display argument string

    Returns:
        Master display MasterDisplayMetadata
    """
    if md_str is None:
        return None

    try:
        parts = md_str.split('L(')
        lum_part = parts[1].rstrip(')')
        max_lum, min_lum = map(float, lum_part.split(','))

        md_values = parts[0]
        r_x = float(md_values.split('R(')[1].split(',')[0])
        r_y = float(md_values.split('R(')[1].split(')')[0].split(',')[1])
        g_x = float(md_values.split('G(')[1].split(',')[0])
        g_y = float(md_values.split('G(')[1].split(')')[0].split(',')[1])
        b_x = float(md_values.split('B(')[1].split(',')[0])
        b_y = float(md_values.split('B(')[1].split(')')[0].split(',')[1])
        wp_x = float(md_values.split('WP(')[1].split(',')[0])
        wp_y = float(md_values.split('WP(')[1].split(')')[0].split(',')[1])

        return MasterDisplayMetadata(
            r_x=r_x, r_y=r_y,
            g_x=g_x, g_y=g_y,
            b_x=b_x, b_y=b_y,
            wp_x=wp_x, wp_y=wp_y,
            min_lum=min_lum,
            max_lum=max_lum
        )
    except (IndexError, ValueError):
        print_err(f"Invalid master display value '{md_str}'")
        sys.exit(1)


def get_content_lightLevel_metadata_from_string(cll_str: str | None) -> ContentLightLevelMetadata | None:
    """Convert content light level argument string.

    Args:
        cll_str: Content light level argument string

    Returns:
        ContentLightLevelMetadata object
    """
    if cll_str is None:
        return None

    try:
        maxcll_str, maxfall_str = cll_str.split(',')
        maxcll = int(maxcll_str)
        maxfall = int(maxfall_str)
        return ContentLightLevelMetadata(maxcll=maxcll, maxfall=maxfall)
    except (ValueError, IndexError):
        print_err(f"Invalid content light level value '{cll_str}'")
        sys.exit(1)

def get_x265_params_from_string(params_str: str | None) -> X265Params:
    """Convert x265 parameters argument string to X265Params object.

    Args:
        params_str: x265 parameters argument string

    Returns:
        X265Params object
    """
    params = X265Params()
    if params_str is None:
        return params

    parts: list[str] = params_str.split(',')
    try:
        for part in parts:
            if part.startswith('crf='):
                params.crf = int(part.split('=')[1])
                if not (0 <= params.crf <= 51):
                    raise ValueError("CRF out of range")
            elif part.startswith('preset='):
                params.preset = x265_x264_Preset(part.split('=')[1])
            elif part.startswith('tune='):
                params.tune = X265Tune(part.split('=')[1])
    except ValueError as err:
        print_err(msg=f"Invalid x265 parameters value '{params_str}'. Err: {err}")
        sys.exit(1)

    return params

def get_x264_params_from_string(params_str: str | None) -> X264Params:
    """Convert x264 parameters argument string to X264Params object.

    Args:
        params_str: x264 parameters argument string

    Returns:
        X264Params object
    """
    params = X264Params()
    if params_str is None:
        return params

    parts: list[str] = params_str.split(':')
    try:
        for part in parts:
            if part.startswith('crf='):
                params.crf = int(part.split('=')[1])
                if not (0 <= params.crf <= 51):
                    raise ValueError("CRF out of range")
            elif part.startswith('preset='):
                params.preset = x265_x264_Preset(part.split('=')[1])
            elif part.startswith('tune='):
                params.tune = X264Tune(part.split('=')[1])
    except ValueError as err:
        print_err(msg=f"Invalid x264 parameters value '{params_str}'. Err: {err}")
        sys.exit(1)

    return params

def get_hdr_forge_encoder_presets_from_args(args) -> HdrForgeEncodingPresetSettings:
    """Create HdrForgeEncodingPresetSettings object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()

    Returns:
        HdrForgeEncodingPresetSettings object with preset and hardware preset
    """
    preset: HdrForgeEncodingPresets
    hw_preset: HdrForgeEncodingHardwarePresets
    if args.preset is None:
        preset = HdrForgeEncodingPresets.AUTO
    else:
        try:
            preset = HdrForgeEncodingPresets(args.preset)
        except ValueError:
            print_err(msg=f"Invalid preset value '{args.preset}'")
            sys.exit(1)

    if args.hw_preset is None:
        hw_preset = HdrForgeEncodingHardwarePresets.CPU_BALANCED
    else:
        try:
            hw_preset = HdrForgeEncodingHardwarePresets(args.hw_preset)
        except ValueError:
            print_err(msg=f"Invalid hardware preset value '{args.hw_preset}'")
            sys.exit(1)

    return HdrForgeEncodingPresetSettings(
        preset=preset,
        hardware_preset=hw_preset,
    )

def create_encoder_settings_from_args(args) -> EncoderSettings:
    """Create EncoderSettings object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()

    Returns:
        EncoderSettings object with all encoding parameters
    """
    hdr_metadata = HdrMetadata(
        mastering_display_metadata=get_master_display_from_string(getattr(args, 'master_display', None)),
        content_light_level_metadata=get_content_lightLevel_metadata_from_string(getattr(args, 'max_cll', None))
    )
    return EncoderSettings(
        video_codec=get_video_codec_from_string(args.video_codec),
        hdr_forge_encoding_preset=get_hdr_forge_encoder_presets_from_args(args),
        hdr_sdr_format=get_hdr_sdr_format_from_string(args.hdr_sdr_format),
        target_dv_profile=get_dolby_vision_profile_from_string(args.dv_profile),
        x265_prams=get_x265_params_from_string(getattr(args, 'x265_params', None)),
        x264_prams=get_x264_params_from_string(getattr(args, 'x264_params', None)),
        scale_height=get_scale_height(args.scale),
        scale_mode=ScaleMode(args.scale_mode),
        crop=get_crop_settings_from_string(args.crop),
        sample=get_sample_settings_from_string(args.sample),
        hdr_metadata=hdr_metadata,
    )
