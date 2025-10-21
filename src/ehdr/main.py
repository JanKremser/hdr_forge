"""Main CLI entry point for EHDR video converter."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from ehdr import __version__
from ehdr.cli_output import callback_handler_crop_video, create_progress_handler, finish_progress, print_conversion_summary, print_encoding_params, print_video_infos
from ehdr.dataclass import ColorFormat
from ehdr.encoder import Encoder
from ehdr.video import Video

# Supported input video formats
SUPPORTED_FORMATS: list[str] = ['.mkv', '.m2ts', '.ts', '.mp4']

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

    # "info" subcommand
    info_parser = subparsers.add_parser('calc_maxcll',
        description='Shows information about a video file',
        help='Display video information'
    )

    info_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for information display'
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

def get_video_files(path: Path, supported_formats: list[str]) -> list[Path]:
    """Get list of video files from path.

    Args:
        path: File or directory path
        supported_formats: list of supported file extensions

    Returns:
        list of video file paths
    """
    if path.is_file():
        return [path] if path.suffix.lower() in supported_formats else []

    if path.is_dir():
        video_files: list = []
        for fmt in supported_formats:
            video_files.extend(path.glob(f'*{fmt}'))
        return sorted(video_files)

    return []


def determine_output_file(video_file: Path, output_path: Path, is_batch: bool) -> Path:
    """Determine output file path for a video file.

    Args:
        video_file: Input video file
        output_path: Output path (file or directory)
        is_batch: Whether this is batch processing

    Returns:
        Output file path
    """
    if is_batch:
        return output_path / video_file.with_suffix('.mkv').name
    return output_path



def show_video_info(input_file: Path) -> bool:
    """Show detailed information about a video file.

    Args:
        input_file: Input video file path

    Returns:
        True if successful, False otherwise
    """
    try:
        if not input_file.exists():
            print(f"Error: The file {input_file} does not exist.")
            return False

        video = Video(filepath=input_file)

        print_video_infos(video=video)
        return True

    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def convert_video(
    video: Video,
    target_file: Path,
    target_format: ColorFormat = ColorFormat.AUTO,
    crf: Optional[int] = None,
    preset: Optional[str] = None,
    scale_height: Optional[int] = None,
    enable_crop: bool = False,
) -> bool:
    """Convert SDR or HDR10 video using ffmpeg with libx265.

    Args:
        video: Video object with metadata
        target_file: Target output file path
        target_format: Target color format (AUTO, SDR, HDR10)
        crf: Optional CRF value (auto-calculated if None)
        preset: Optional preset (auto-calculated if None)
        scale_height: Optional target height for scaling
        enable_crop: Enable automatic cropping
        crop_callback: Optional crop detection progress callback

    Returns:
        True if conversion succeeded, False otherwise
    """
    input_file: Path = video.get_filepath()

    # Create encoder for Dolby Vision
    encoder = Encoder(
        video=video,
        target_file=target_file,
        color_format=target_format,
        crf=crf,
        preset=preset,
        scale_height=scale_height,
        enable_crop=enable_crop,
        crop_callback=callback_handler_crop_video,
    )

    try:
        print_encoding_params(encoder=encoder)

        # Prepare progress monitoring
        total_frames = video.get_total_frames()

        success: bool = False
        if encoder.is_dolby_vision():
            # progress_handler = None

            # if total_frames > 0:
            #     progress_handler = lambda stderr, frames: monitor_x265_progress(stderr=stderr, total_frames=frames)

            # # Execute conversion
            # success = encoder.convert_dolby_vision(
            #     progress_callback=progress_handler
            # )
            duration = video.get_duration_seconds()

            progress_handler = None
            finish_callback = None

            if duration > 0:
                progress_handler = create_progress_handler(duration=duration, total_frames=total_frames)
                finish_callback = lambda: finish_progress(total_frames=total_frames, duration=duration)

            # Execute conversion
            success: bool = encoder.convert_dolby_vision(
                progress_callback=progress_handler,
                finish_callback=finish_callback
            )
        else:
            duration = video.get_duration_seconds()

            progress_handler = None
            finish_callback = None

            if duration > 0:
                progress_handler = create_progress_handler(duration=duration, total_frames=total_frames)
                finish_callback = lambda: finish_progress(total_frames=total_frames, duration=duration)

            # Execute conversion
            success: bool = encoder.convert(
                progress_callback=progress_handler,
                finish_callback=finish_callback
            )

        if success:
            print()  # New line after progress
            print(f"Success: {target_file.name}")

        return success

    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def process_convert_command(args) -> None:
    """Process the convert subcommand."""
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)

    # Get list of video files to process
    video_files = get_video_files(input_path, SUPPORTED_FORMATS)

    if not video_files:
        print(f"Error: No supported video files found in: {input_path}")
        print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)

    # Determine if batch processing
    is_batch = len(video_files) > 1

    if is_batch:
        # Ensure output is a directory for batch processing
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            print("Error: Output must be a directory for batch processing")
            sys.exit(1)

    # Determine target height from scale argument if present
    scale_height: int | None = get_scale_height(args.scale)

    color_format: ColorFormat = get_color_format_from_string(args.color_format)

    # Process each video file
    success_count = 0
    fail_count = 0

    for video_file in video_files:
        # Determine output file
        out_file: Path = determine_output_file(video_file=video_file, output_path=output_path, is_batch=is_batch)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        video = Video(filepath=video_file)
        print_video_infos(video=video)

        success = convert_video(
            video=video,
            target_file=out_file,
            target_format=color_format,
            crf=args.crf,
            preset=args.preset,
            scale_height=scale_height,
            enable_crop=not args.ncrop,
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

    print_conversion_summary(success_count, fail_count)
    sys.exit(0 if fail_count == 0 else 1)


def process_info_command(args) -> None:
    """Process the info subcommand."""
    input_path = Path(args.input)

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)

    # Determine if it's a file or directory
    if input_path.is_file():
        show_video_info(input_path)
    else:
        # Get list of video files to process
        video_files = get_video_files(input_path, SUPPORTED_FORMATS)

        if not video_files:
            print(f"Error: No supported video files found in: {input_path}")
            print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
            sys.exit(1)

        # Show info for each video file
        for video_file in video_files:
            show_video_info(video_file)


def main() -> None:
    """Main entry point for CLI."""
    args = parse_args()

    # Execute the corresponding subcommand
    if args.command == 'info':
        process_info_command(args)
    elif args.command == 'convert':
        process_convert_command(args)
    elif args.command == 'calc_maxcll':
        from ehdr.hdr_formats.hdr10 import calc_maxcll
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input path does not exist: {input_path}")
            sys.exit(1)
        calc_maxcll(video_path=str(input_path))
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
