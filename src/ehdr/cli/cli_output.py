"""CLI output and progress tracking functionality."""

import sys
import time
import subprocess
from datetime import timedelta
from typing import Callable, Optional

from ffmpeg import Progress


# Constants
SUMMARY_LINE_WIDTH = 60
PROGRESS_BAR_WIDTH = 70
# ANSI escape codes for terminal control
CURSOR_UP_ONE = '\033[1A'
CLEAR_LINE = '\033[2K'  # Clears the current line
MOVE_TO_START = '\r'    # Moves cursor to the beginning of the line

# Complete code to clear current and previous line
CLEAR_TWO_LINES = f"{CLEAR_LINE}{CURSOR_UP_ONE}{CLEAR_LINE}{MOVE_TO_START}"

# ANSI Farbcodes
YELLOW = '\033[93m'
RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
RESET = '\033[0m'

DEBUG_MODE = False


def color_str(value: str | int | float | None, color: str) -> str:
    """Wrap text with ANSI color codes.

    Args:
        text: The text to color
        color_code: The ANSI color code

    Returns:
        Colored text string
    """
    return f"{color}{str(value)}{RESET}"

def print_warn(msg: str) -> None:
    """Print a warning message in yellow color.

    Args:
        message: The warning message to print
    """
    print(f"{color_str('Warning:', YELLOW)} {msg}")

def print_err(msg: str) -> None:
    """Print an error message in red color.

    Args:
        message: The error message to print
    """
    print(f"{color_str('Error:', RED)} {msg}")

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

    bar: str = f"{GREEN}{'█' * filled}{RESET}"
    if empty > 0:
        bar += f"{GREEN}{'░'}{RESET}"
        bar += f"{'░' * (empty - 1)}"
    return bar


def calculate_eta(fps: float, current_frame: int, total_frames: int) -> str:
    # Calculate ETA
    eta: str = "00:00:00"
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


def print_progress_info(first_update: bool, current_frame: int, total_frames: int, fps: float, speed: float | None, time_seconds: float | None, bitrate_kbs: float | None, size_bytes: int | None) -> None:
    # Calculate percentage
    percent: float = (current_frame / total_frames * 100) if total_frames > 0 else 0.0

    # Calculate ETA
    eta: str = calculate_eta(fps=fps, current_frame=current_frame, total_frames=total_frames)

    # Create progress bar
    progress_bar: str = create_progress_bar(percent=percent)

    time_str: str = format_time(seconds=time_seconds) if time_seconds is not None else "--:--:--"

    speed_str: str = f"{speed:.2f}x" if speed is not None else "--.-x"

    bitrate_str: str = f"{bitrate_kbs:.2f} kb/s" if bitrate_kbs is not None else "--.- kb/s"

    size_str: str = f"{size_bytes / 1024:.2f} KB" if size_bytes is not None else "--.- KB"

    # Format for multi-line output
    bar_line: str = f"{progress_bar} {percent:5.1f}%"
    info_line: str = f"Frame: {current_frame}/{total_frames} | Speed: {speed_str} | FPS: {fps} | ETA: {eta} | Time: {time_str} | Bitrate: {bitrate_str} | Size: {size_str}"

    # For the first output, we only need to print both lines
    if first_update:
        print()
        print(bar_line)
        print(info_line, end="", flush=True)
    else:
        # For subsequent updates, we first clear both lines completely
        print(CLEAR_TWO_LINES, end="")
        print(bar_line)
        print(info_line, end="", flush=True)


def finish_progress(total_frames: int, duration: float = 0.0) -> None:
    """Finalize the progress display by setting it to 100%.

    Args:
        total_frames: Total number of frames in the video
        duration: Total video duration in seconds
    """
    print_progress_info(
        first_update=False,
        current_frame=total_frames,
        total_frames=total_frames,
        fps=0.0,
        speed=0.0,
        time_seconds=duration,
        bitrate_kbs=0.0,
        size_bytes=None,
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
    first_update = True

    def on_progress(progress: Progress) -> None:
        """Handle progress updates from ffmpeg."""
        nonlocal first_update

        time_seconds: float = 0.0
        if progress.time and duration > 0:
            # Convert timedelta to seconds if necessary
            time_seconds = (
                progress.time.total_seconds()
                if isinstance(progress.time, timedelta)
                else float(progress.time)
            )

        current_frame: int = progress.frame
        fps: float = progress.fps if progress.fps else 0.0

        print_progress_info(
            first_update=first_update,
            current_frame=current_frame,
            total_frames=total_frames,
            fps=fps,
            speed=progress.speed,
            time_seconds=time_seconds,
            bitrate_kbs=progress.bitrate,
            size_bytes=progress.size,
        )
        if first_update:
            first_update = False

    return on_progress


def print_conversion_summary(success_count: int, fail_count: int) -> None:
    """Print conversion summary.

    Args:
        success_count: Number of successful conversions
        fail_count: Number of failed conversions
    """
    color = BLUE
    print(f"{color_str('_', color)}" * 70)
    print("Conversion complete:")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")
    print(f"{color_str('_', color)}" * 70)


def monitor_process_progress(process: subprocess.Popen, description: str) -> None:
    """Monitor a running process and display a progress bar.

    Args:
        process: The subprocess.Popen process to monitor
        description: Description text to show before the progress bar
    """
    if not process:
        return

    print(f"{description}", flush=True)

    spinner = ['|', '/', '-', '\\']
    i = 0

    while process.poll() is None:
        bar = create_progress_bar(percent=(i % 20) * 5)  # Indeterminate progress
        status = f"{CLEAR_LINE}{MOVE_TO_START}{spinner[i % 4]} {bar} Processing..."
        print(status, end='', flush=True)
        time.sleep(0.1)
        i += 1

    # Clear the progress line after completion
    print(f"{CLEAR_LINE}{MOVE_TO_START}", end='', flush=True)

def create_aspect_ratio_str(width: int, height: int, tolerance: float = 0.02) -> str:
    """
    Calculates the aspect ratio of a given resolution and returns a string like '16:9' or '21:9'.
    Attempts to match known standard aspect ratios within a small tolerance.

    Args:
        width (int): Image or video width in pixels
        height (int): Image or video height in pixels
        tolerance (float): Allowed ratio deviation (default = 0.02 = 2%)

    Returns:
        str: Human-readable aspect ratio (e.g. '16:9', '21:9', '4:3')
    """

    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive integers")

    # calculate exact ratio
    ratio: float = width / height

    # known common aspect ratios
    common_ratios: dict = {
        "1:1": 1.0,
        "5:4": 1.25,
        "4:3": 1.3333,
        "3:2": 1.5,
        "16:10": 1.6,
        "16:9": 1.7777,
        "18:9": 2.0,
        "2.20:1 (70mm)": 2.20,
        "21:9": 2.3333,
        "2.35:1 (Cinema)": 2.35,
        "2.39:1 (Cinema-Modern)": 2.39,
        "32:9": 3.5555,
    }

    # Find the closest ratio within tolerance
    closest_label = None
    smallest_difference = float('inf')

    for label, value in common_ratios.items():
        difference = abs(ratio - value)
        max_allowed_difference = value * tolerance

        if difference <= max_allowed_difference and difference < smallest_difference:
            smallest_difference = difference
            closest_label = label

    if closest_label:
        return closest_label

    # fallback: compute ratio in X:1 format
    ratio_x_to_1: float = width / height
    return f"{ratio_x_to_1:.2f}:1"
