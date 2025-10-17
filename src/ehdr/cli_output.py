"""CLI output and progress tracking functionality."""

import re
from typing import Callable, IO

from ffmpeg import Progress

# Constants
SUMMARY_LINE_WIDTH = 60


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
            time_seconds = (
                progress.time.total_seconds()
                if hasattr(progress.time, 'total_seconds')
                else float(progress.time)
            )
            percent = min((time_seconds / duration) * 100, 100)
            time_str = format_time(time_seconds)
            speed = progress.speed if progress.speed else 0

            # Print progress on same line
            print(
                f"\rProgress: {percent:5.1f}% | Time: {time_str} | Speed: {speed:.2f}x",
                end='',
                flush=True
            )

    return on_progress


def monitor_x265_progress(stderr: IO[str], total_frames: int) -> None:
    """Monitor and display x265 encoding progress in real-time.

    Args:
        stderr: x265 process stderr stream
        total_frames: Total number of frames in the video
    """
    # Regex pattern to match x265 progress output
    # Format: 160 frames: 20.64 fps, 483.46 kb/s
    progress_pattern = re.compile(
        r'(\d+)\s+frames:\s+([\d.]+)\s+fps'
    )

    for line in stderr:
        line = line.strip()

        # Try to match progress line
        match = progress_pattern.search(line)
        if match:
            current_frame = int(match.group(1))
            fps = float(match.group(2))

            # Calculate percentage
            percent = (current_frame / total_frames * 100) if total_frames > 0 else 0

            # Calculate ETA
            if fps > 0 and total_frames > 0:
                remaining_frames = total_frames - current_frame
                eta_seconds = remaining_frames / fps
                eta = format_time(eta_seconds)
            else:
                eta = "--:--:--"

            # Print progress on same line
            print(
                f"\rProgress: {percent:5.1f}% | Frame: {current_frame}/{total_frames} | Speed: {fps:.2f} fps | ETA: {eta}",
                end='',
                flush=True
            )


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
