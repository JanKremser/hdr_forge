"""CLI output and progress tracking functionality."""

from typing import Callable

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
