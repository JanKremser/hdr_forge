"""CLI output and progress tracking functionality."""

import re
from datetime import timedelta
from typing import Callable, IO

from ffmpeg import Progress

# Constants
SUMMARY_LINE_WIDTH = 60
PROGRESS_BAR_WIDTH = 30


def create_progress_bar(percent: float, width: int = PROGRESS_BAR_WIDTH) -> str:
    """Create a visual progress bar.

    Args:
        percent: Completion percentage (0-100)
        width: Width of the progress bar in characters

    Returns:
        Progress bar string (e.g., "[████████░░░░░░░░░░]")
    """
    filled = int(width * percent / 100)
    empty = width - filled
    return f"{'█' * filled}{'░' * empty}"


def calculate_eta(fps: float, current_frame: int, total_frames: int) -> str:
    # Calculate ETA
    eta: str = "--:--:--"
    if fps > 0 and total_frames > 0:
        remaining_frames: int = total_frames - current_frame
        eta_seconds: float = remaining_frames / fps
        eta = format_time(eta_seconds)
    return eta


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


def finish_progress(total_frames: int, duration: float = 0.0) -> None:
    """Finalize the progress display by setting it to 100%.

    Args:
        total_frames: Total number of frames in the video
        duration: Total video duration in seconds
    """
    progress_bar = create_progress_bar(100.0)
    time_str = format_time(duration) if duration > 0 else "--:--:--"

    print(
        f"\r{progress_bar}[100.0%]   --   Frame: {total_frames}/{total_frames} | Speed: -.--x | ETA: 00:00:00 | Time: {time_str}",
        end='',
        flush=True
    )
    # Add an empty line after finishing progress
    print()


def create_progress_handler(duration: float, total_frames: int = 0) -> Callable[[Progress], None]:
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
            time_seconds: float = (
                progress.time.total_seconds()
                if isinstance(progress.time, timedelta)
                else float(progress.time)
            )
            time_str: str = format_time(time_seconds)
            speed: float = progress.speed if progress.speed else 0.0
            current_frame: int = progress.frame
            fps: float = progress.fps if progress.fps else 0.0

            # Calculate ETA
            eta: str = calculate_eta(fps=fps, current_frame=current_frame, total_frames=total_frames)

            # Create progress bar
            percent: float = min((time_seconds / duration) * 100, 100)
            progress_bar: str = create_progress_bar(percent)

            # Print progress on same line
            print(
                f"\r{progress_bar}[{percent:5.1f}%]   --   Frame: {current_frame}/{total_frames} | Speed: {speed:.2f}x | ETA: {eta} | Time: {time_str}",
                end='\n',
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
    progress_pattern: re.Pattern[str] = re.compile(
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
            percent: float = (current_frame / total_frames * 100) if total_frames > 0 else 0.0

            # Calculate ETA
            eta: str = calculate_eta(fps=fps, current_frame=current_frame, total_frames=total_frames)

            # Create progress bar
            progress_bar: str = create_progress_bar(percent)

            # Print progress on same line
            print(
                f"\r{progress_bar}[{percent:5.1f}%]   --   Frame: {current_frame}/{total_frames} | Speed: {fps:.2f} fps | ETA: {eta}",
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
