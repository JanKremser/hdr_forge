"""Main CLI entry point for EHDR video converter."""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ffmpeg import FFmpeg, Progress

from . import __version__
from .dolby_vision import build_dolby_vision_params, extract_rpu
from .video import Video

# Supported input video formats
SUPPORTED_FORMATS = ['.mkv', '.m2ts', '.ts', '.mp4']

# Constants
DOLBY_VISION_PROFILE = '8.1'
SUMMARY_LINE_WIDTH = 60
HDR_X265_PARAMS = [
    'hdr-opt=1',
    'repeat-headers=1',
    'colorprim=bt2020',
    'transfer=smpte2084',
    'colormatrix=bt2020nc',
]
HDR_PIXEL_FORMAT = 'yuv420p10le'


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def create_progress_handler(duration: float) -> Callable[[Progress], None]:
    """Create a progress handler for ffmpeg encoding.

    Args:
        duration: Total video duration in seconds

    Returns:
        Progress handler function
    """
    def on_progress(progress: Progress) -> None:
        """Handle progress updates from ffmpeg."""
        if progress.time and duration > 0:
            # Convert timedelta to seconds if necessary
            time_seconds = progress.time.total_seconds() if hasattr(progress.time, 'total_seconds') else float(progress.time)
            percent = min((time_seconds / duration) * 100, 100)
            time_str = format_time(time_seconds)
            speed = progress.speed if progress.speed else 0

            # Print progress on same line
            print(
                f"\rProgress: {percent:5.1f}% | Time: {time_str} | Speed: {speed:.2f}x", end='', flush=True)

    return on_progress


def determine_encoding_params(video: Video, crf: Optional[int], preset: Optional[str]) -> tuple[int, str]:
    """Determine CRF and preset values (auto-calculate if not provided).

    Args:
        video: Video object with metadata
        crf: User-specified CRF or None for auto
        preset: User-specified preset or None for auto

    Returns:
        Tuple of (crf, preset)
    """
    if crf is None:
        crf = video.get_auto_crf()
        print(f"Auto CRF: {crf}")

    if preset is None:
        preset = video.get_auto_preset()
        print(f"Auto preset: {preset}")

    return crf, preset


def build_hdr_x265_params(video: Video) -> List[str]:
    """Build x265 parameters for HDR video encoding.

    Args:
        video: Video object with HDR metadata

    Returns:
        List of x265 parameter strings
    """
    params = HDR_X265_PARAMS.copy()

    master_display = video.get_master_display()
    if master_display:
        params.append(f'master-display={master_display}')

    return params


def build_ffmpeg_output_options(
    video: Video,
    crf: int,
    preset: str,
    crop_filter: Optional[str] = None
) -> Dict[str, str]:
    """Build FFmpeg output options dictionary for encoding.

    Args:
        video: Video object with metadata
        crf: Constant Rate Factor value
        preset: Encoding preset
        crop_filter: Optional crop filter string

    Returns:
        Dictionary of FFmpeg output options
    """
    output_options = {
        'c:v': 'libx265',
        'preset': preset,
        'crf': str(crf),
        'c:a': 'copy',
        'c:s': 'copy'
    }

    if video.is_hdr_video():
        print("HDR video detected")
        x265_params = build_hdr_x265_params(video)
        output_options['pix_fmt'] = HDR_PIXEL_FORMAT
        output_options['x265-params'] = ':'.join(x265_params)

    if crop_filter:
        output_options['vf'] = crop_filter

    return output_options


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


def get_video_files(path: Path) -> List[Path]:
    """Get list of video files from path.

    Args:
        path: File or directory path

    Returns:
        List of video file paths
    """
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_FORMATS else []

    if path.is_dir():
        video_files = []
        for fmt in SUPPORTED_FORMATS:
            video_files.extend(path.glob(f'*{fmt}'))
        return sorted(video_files)

    return []


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
        video = Video(str(input_file))

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

        # Determine CRF and preset
        crf, preset = determine_encoding_params(video, crf, preset)

        # Build ffmpeg command
        ffmpeg = FFmpeg()
        ffmpeg.option('y')
        ffmpeg.input(str(input_file))

        # Build output options
        output_options = build_ffmpeg_output_options(video, crf, preset, crop_filter)
        ffmpeg.output(str(output_file), output_options)

        print(f"Encoding to: {output_file.name}")

        # Execute with progress tracking
        duration = float(video.metadata.get('format', {}).get('duration', 0))
        if duration > 0:
            progress_handler = create_progress_handler(duration)
            ffmpeg.on('progress', progress_handler)
            ffmpeg.execute()
            print()
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
        video = Video(str(input_file))

        # Extract RPU metadata
        rpu_file = extract_rpu(str(input_file))

        # Determine CRF and preset
        crf, preset = determine_encoding_params(video, crf, preset)

        # Build x265 parameters
        x265_params = build_dolby_vision_params(video, crf, preset)
        x265_params.append('log-level=error')
        x265_params.append(f'dolby-vision-rpu={rpu_file}')
        x265_params.append(f'dolby-vision-profile={DOLBY_VISION_PROFILE}')

        # Build ffmpeg to x265 pipeline
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', str(input_file),
            '-c:v', 'copy',
            '-vbsf', 'hevc_mp4toannexb',
            '-f', 'hevc',
            '-'
        ]

        x265_cmd = [
            'x265',
            '--y4m',
            '--input', '-',
            '--input-depth', '10',
            '--output-depth', '10',
            '--x265-params', ':'.join(x265_params),
            '--output', str(output_file)
        ]

        print(f"Encoding Dolby Vision to: {output_file.name}")

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

        # Wait for x265 to complete
        _, stderr = x265_process.communicate()

        if x265_process.returncode != 0:
            print("Error: x265 encoding failed")
            print(stderr)
            return False

        # Wait for ffmpeg
        ffmpeg_process.wait()

        print(f"Success: {output_file.name}")
        return True

    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def print_conversion_summary(success_count: int, fail_count: int) -> None:
    """Print conversion summary.

    Args:
        success_count: Number of successful conversions
        fail_count: Number of failed conversions
    """
    separator = '=' * SUMMARY_LINE_WIDTH
    print(f"\n{separator}")
    print("Conversion complete:")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")
    print(separator)


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
    video_files = get_video_files(input_path)

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
