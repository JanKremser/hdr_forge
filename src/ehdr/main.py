"""Main CLI entry point for EHDR video converter."""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from ffmpeg import FFmpeg

from . import __version__
from .cli_output import create_progress_handler, finish_progress, monitor_x265_progress, print_conversion_summary, print_encoding_params, print_video_infos
from .dolby_vision import extract_rpu
from .encoding import (
    build_ffmpeg_output_options,
    determine_output_file,
    get_video_files,
)
from .video import Video

# Supported input video formats
SUPPORTED_FORMATS = ['.mkv', '.m2ts', '.ts', '.mp4']

# Constants
DOLBY_VISION_PROFILE = '8.1'


def parse_args():
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='EHDR - Easy HDR Video Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ehdr -i input.mkv -o output.mkv
  ehdr -i input.mkv -o output.mkv --crf 16 --preset slow
  ehdr -i input.mkv -o output.mkv --dv --ncrop
  ehdr -i ./input_folder -o ./output_folder
        """
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input video file or folder'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output video file or folder'
    )

    parser.add_argument(
        '--crf',
        type=int,
        help='Constant Rate Factor for quality (lower = higher quality). Auto-calculated if not specified.'
    )

    parser.add_argument(
        '-p', '--preset',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster',
                 'fast', 'medium', 'slow', 'slower', 'veryslow'],
        help='Encoding preset (speed vs compression). Auto-calculated if not specified.'
    )

    parser.add_argument(
        '--ncrop',
        action='store_true',
        help='Disable automatic black bar cropping'
    )

    parser.add_argument(
        '--dv',
        action='store_true',
        help='Enable Dolby Vision mode (requires dovi_tool and 10-bit x265)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'EHDR {__version__}'
    )

    return parser.parse_args()


def convert_sdr_hdr10(
    input_file: Path,
    output_file: Path,
    crf: Optional[int] = None,
    preset: Optional[str] = None,
    enable_crop: bool = True
) -> bool:
    """Convert SDR or HDR10 video using ffmpeg with libx265.

    Args:
        input_file: Input video file path
        output_file: Output video file path
        crf: Constant Rate Factor (None for auto)
        preset: Encoding preset (None for auto)
        enable_crop: Enable automatic cropping

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        print(f"\nProcessing: {input_file.name}")

        # Load video metadata
        video = Video(filepath=str(input_file), crf=crf, preset=preset)
        print_video_infos(video=video)

        # Detect crop if enabled
        crop_filter = None
        if enable_crop:
            print("Detecting black bars...")
            video.crop_video()
            crop_filter = video.get_crop_filter()
            if crop_filter:
                print(f"Crop detected: {crop_filter}")
            else:
                print("No cropping needed")

        print_encoding_params(video=video)

        # Determine CRF and preset
        crf = video.get_crf()
        preset = video.get_preset()

        # Build ffmpeg command
        ffmpeg = FFmpeg()
        ffmpeg.option('y')
        ffmpeg.input(str(input_file))

        # Build output options
        output_options: dict = build_ffmpeg_output_options(video=video, crf=crf, preset=preset, crop_filter=crop_filter)
        ffmpeg.output(url=str(output_file), options=output_options)

        print(f"Encoding to: {output_file.name}")

        # Execute with progress tracking
        duration = float(video.metadata.get('format', {}).get('duration', 0))
        total_frames = video.get_total_frames()
        print()
        if duration > 0:
            progress_handler = create_progress_handler(duration, total_frames)
            ffmpeg.on('progress', progress_handler)
            ffmpeg.execute()
            finish_progress(total_frames=total_frames, duration=duration)
        else:
            ffmpeg.execute()


        print(f"Success: {output_file.name}")
        return True

    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def convert_dolby_vision(
    input_file: Path,
    output_file: Path,
    crf: Optional[int] = None,
    preset: Optional[str] = None
) -> bool:
    """Convert Dolby Vision video using x265 with RPU injection.

    Args:
        input_file: Input video file path
        output_file: Output video file path
        crf: Constant Rate Factor (None for auto)
        preset: Encoding preset (None for auto)

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        print(f"\nProcessing Dolby Vision: {input_file.name}")

        # Load video metadata
        video = Video(filepath=str(input_file), crf=crf, preset=preset)
        print_video_infos(video=video)

        # Extract RPU metadata
        rpu_file = extract_rpu(str(input_file))

        # Determine CRF and preset
        crf = video.get_crf()
        preset = video.get_preset()

        print_encoding_params(video=video)

        # Build ffmpeg to x265 pipeline
        ffmpeg_cmd: list[str] = [
            'ffmpeg', '-y',
            '-i', str(input_file),
            '-f', 'yuv4mpegpipe',
            '-strict', '-1',
            '-pix_fmt', video.get_pix_fmt(),
            '-'
        ]

        # Build x265 command with separate arguments (like Rust version)
        x265_cmd: list[str] = [
            'x265',
            '-',
            '--input-depth', '10',
            '--output-depth', '10',
            '--y4m',
            '--preset', preset,
            '--crf', str(crf),
        ]

        # Add master display metadata
        master_display = video.get_master_display()
        if master_display:
            x265_cmd.extend(['--master-display', master_display])

        # Add max CLL and FALL if available
        max_cll_max_fall: Tuple[int, int] | None = video.get_max_cll_max_fall(return_fallback=True)
        if max_cll_max_fall:
            max_cll, max_fall = max_cll_max_fall
            x265_cmd.extend(['--max-cll', f'{max_cll},{max_fall}'])

        # Add remaining HDR parameters
        x265_cmd.extend([
            '--colormatrix', video.get_color_space(),
            '--colorprim', video.get_color_primaries(),
            '--transfer', video.get_color_transfer(),
            '--dolby-vision-rpu', rpu_file,
            '--dolby-vision-profile', DOLBY_VISION_PROFILE,
            '--vbv-bufsize', '20000',
            '--vbv-maxrate', '20000',
            f'{str(output_file)}.hevc'
        ])

        print(f"Encoding Dolby Vision to: {output_file.name}")

        # Calculate total frames for progress tracking
        total_frames = video.get_total_frames()

        # Create pipeline
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        x265_process = subprocess.Popen(
            x265_cmd,
            stdin=ffmpeg_process.stdout,
            stderr=subprocess.PIPE,
            text=True
        )

        # Close ffmpeg stdout in parent
        if ffmpeg_process.stdout:
            ffmpeg_process.stdout.close()

        # Monitor x265 progress in real-time
        if total_frames > 0 and x265_process.stderr:
            monitor_x265_progress(stderr=x265_process.stderr, total_frames=total_frames)
            x265_process.wait()
            print()  # New line after progress
        else:
            # Fallback: just wait for completion
            _, stderr = x265_process.communicate()
            if x265_process.returncode != 0:
                print("Error: x265 encoding failed")
                print(stderr)
                return False

        if x265_process.returncode != 0:
            print("Error: x265 encoding failed")
            return False

        # Wait for ffmpeg
        ffmpeg_process.wait()

        print(f"Success: {output_file.name}")
        return True

    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def main() -> None:
    """Main entry point for CLI."""
    args = parse_args()

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

    # Process each video file
    success_count = 0
    fail_count = 0

    for video_file in video_files:
        # Determine output file
        out_file = determine_output_file(video_file, output_path, is_batch)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert based on mode
        if args.dv:
            success = convert_dolby_vision(
                input_file=video_file,
                output_file=out_file,
                crf=args.crf,
                preset=args.preset
            )
        else:
            success = convert_sdr_hdr10(
                input_file=video_file,
                output_file=out_file,
                crf=args.crf,
                preset=args.preset,
                enable_crop=not args.ncrop
            )

        if success:
            success_count += 1
        else:
            fail_count += 1

    print_conversion_summary(success_count, fail_count)
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == '__main__':
    main()
