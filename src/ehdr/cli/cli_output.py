"""CLI output and progress tracking functionality."""

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
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BLACK = '\033[30m'

GREEN_BG = '\033[102m'
GRAY_BG = '\033[100m'

RESET = '\033[0m'

DEBUG_MODE = False


def clear_lines(n: int) -> str:
    """Generate ANSI escape codes to clear n lines in the terminal.

    Args:
        n: Number of lines to clear

    Returns:
        ANSI escape code string to clear n lines
    """
    return ''.join(f"{CLEAR_LINE}{CURSOR_UP_ONE}" for _ in range(n)) + CLEAR_LINE + MOVE_TO_START


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

def create_progress_bar(percent: float, text: Optional[str] = None, width: int = PROGRESS_BAR_WIDTH) -> str:
    """Create a visual progress bar.

    Args:
        percent: Completion percentage (0-100)
        width: Width of the progress bar in characters

    Returns:
        Progress bar string (e.g., "████████░░░░░░░░░░")
    """
    text_len: int = 0
    text_pos: int = 0
    if text is not None:
        text_len = len(text)
        text_pos = (width - text_len) // 2

    filled = int(width * percent / 100)
    empty = width - filled

    bar_chars = []
    for i in range(width):
        if text is not None and text_pos <= i < text_pos + text_len:
            # Percent string in filled area: green foreground + green background
            if i < filled:
                bar_chars.append(f"{GREEN_BG}{BLACK}{text[i - text_pos]}{RESET}")
            else:
                bar_chars.append(f"{GRAY_BG}{BLACK}{text[i - text_pos]}{RESET}")
        elif i < filled:
            bar_chars.append(f"{GREEN}█{RESET}")
        elif i == filled and empty > 0:
            bar_chars.append(f"{GREEN}░{RESET}")
        else:
            bar_chars.append(f"{GRAY_BG} {RESET}")

    bar = ''.join(bar_chars)
    return bar


def create_progress_bar_with_percent(percent: float, width: int = PROGRESS_BAR_WIDTH) -> str:
    """
    Progress bar with centered percent number.
    If the percent number is inside the filled area, both foreground and background are green.
    Otherwise, foreground is white and background is default.

    Args:
        percent: Progress in percent (0-100)
        width: Width of the bar

    Returns:
        Progress bar string, e.g. "██████ 42.3% ░░░░░"
    """
    percent_str_raw = f"{percent:5.1f}%".strip()

    return create_progress_bar(percent=percent, text=percent_str_raw, width=width)


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


def _calc_process_time_seconds(process_start_time: float) -> float:
    process_end_time = time.time()
    elapsed = process_end_time - process_start_time
    return elapsed


def estimate_final_size(current_size_bytes: int | None, current_frame: int, total_frames: int) -> float | None:
    """
    Estimate the final output file size based on current size and frame progress.

    Args:
        current_size_bytes (int | None): Current file size in bytes
        current_frame (int): Current frame number
        total_frames (int): Total number of frames

    Returns:
        float | None: Estimated final size in bytes, or None if estimation is not possible
    """
    if current_size_bytes is None or current_frame == 0 or total_frames == 0:
        return None
    # Linear extrapolation based on current progress
    estimated_size = current_size_bytes * (total_frames / current_frame)
    return estimated_size


def print_progress_info(first_update: bool, current_frame: int, total_frames: int, duration_seconds: float, process_time_seconds: float, fps: float, speed: float | None, time_seconds: float | None, bitrate_kbs: float | None, size_bytes: int | None) -> None:
    # Calculate percentage
    percent: float = (current_frame / total_frames * 100) if total_frames > 0 else 0.0

    # Calculate ETA
    eta: str = calculate_eta(fps=fps, current_frame=current_frame, total_frames=total_frames)

    # Create progress bar
    progress_bar: str = create_progress_bar_with_percent(percent=percent)


    if time_seconds is None or (time_seconds == 0 and current_frame > 0):
        time_seconds = calculate_time_seconds_backup(
            current_frame=current_frame,
            total_frames=total_frames,
            duration_seconds=duration_seconds,
        )
    time_str: str = format_time(seconds=time_seconds) if time_seconds is not None else "--:--:--"
    
    duration_str: str = format_time(seconds=duration_seconds) if duration_seconds is not None else "--:--:--"
    process_time_str: str = format_time(seconds=process_time_seconds)

    if speed is None or (speed == 0 and current_frame > 0):
        speed = calculate_speed_backup(
            current_frame=current_frame,
            process_time_seconds=process_time_seconds,
            fps=fps,
        )
    speed_str: str = f"{speed:.2f}x" if speed is not None else "--.-x"

    bitrate_str: str = f"{bitrate_kbs:.2f} kb/s" if bitrate_kbs is not None else "--.- kb/s"

    size_str: str = "--.- KB"
    if size_bytes is not None:
        size_kb: float = size_bytes / 1024
        size_gb: float = size_kb / 1024 / 1024
        size_str: str = f"{size_bytes / 1024:.2f} KB ~> {size_gb:.2f} GB"

    # Estimate final file size
    estimated_size_bytes = estimate_final_size(size_bytes, current_frame, total_frames)
    estimated_size_str = "--.- KB"
    if estimated_size_bytes is not None:
        estimated_size_kb = estimated_size_bytes / 1024
        estimated_size_gb = estimated_size_kb / 1024 / 1024
        estimated_size_str = f"{estimated_size_bytes / 1024:.2f} KB ~> {estimated_size_gb:.2f} GB"

    # Format for multi-line output
    info_line: str = f"""
{color_str("-" * 70, GREEN)}
Frame         : {color_str(current_frame, GREEN)}/{total_frames}
Speed         : {speed_str} | {fps} FPS

ETA           : {eta}
Time          : {color_str(time_str, GREEN)}/{duration_str}
Process Time  : {color_str(process_time_str, GREEN)}

Bitrate       : {bitrate_str}
Size          : {size_str}
Final size    : {estimated_size_str}
{progress_bar}
{color_str("-" * 70, GREEN)}"""

    # For the first output, we only need to print both lines
    print(clear_lines(13) if first_update is False else "", end="")
    print(info_line, end="", flush=True)


def finish_progress(duration: float, total_frames: int, process_start_time: float) -> None:
    """Finalize the progress display by setting it to 100%.

    Args:
        total_frames: Total number of frames in the video
        duration: Total video duration in seconds
    """

    process_time_seconds: float = _calc_process_time_seconds(
        process_start_time=process_start_time
    )

    print_progress_info(
        first_update=False,
        current_frame=total_frames,
        total_frames=total_frames,
        duration_seconds=duration,
        process_time_seconds=process_time_seconds,
        fps=0.0,
        speed=0.0,
        time_seconds=duration,
        bitrate_kbs=0.0,
        size_bytes=None,
    )

    # Add an empty line after finishing progress
    print()


def create_progress_handler(duration: float, total_frames: int, process_start_time: float) -> Callable[[Progress], None]:
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

        process_time_seconds: float = _calc_process_time_seconds(
            process_start_time=process_start_time
        )

        print_progress_info(
            first_update=first_update,
            current_frame=current_frame,
            total_frames=total_frames,
            duration_seconds=duration,
            process_time_seconds=process_time_seconds,
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
        bar = create_progress_bar(percent=(i % 20) * 5, text=f"Processing {spinner[i % 4]}")  # Indeterminate progress
        status = f"{CLEAR_LINE}{MOVE_TO_START}{bar}"
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

def calculate_speed_backup(current_frame: int, process_time_seconds: float, fps: float) -> float | None:
    """
    Berechnet eine Backup-Speed falls speed None ist.
    Nutzt aktuelle Frames und vergangene Prozesszeit.

    Args:
        current_frame (int): Aktueller Frame
        process_time_seconds (float): Vergangene Prozesszeit in Sekunden
        fps (float): Aktuelle FPS

    Returns:
        float | None: Berechnete Geschwindigkeit (z.B. 1.23 für 1.23x), oder None falls nicht berechenbar
    """
    if process_time_seconds > 0 and fps > 0 and current_frame > 0:
        # Tatsächliche Geschwindigkeit = (verarbeitete Frames pro Sekunde) / (Soll-FPS)
        actual_fps = current_frame / process_time_seconds
        return actual_fps / fps
    return None

def calculate_time_seconds_backup(current_frame: int, total_frames: int, duration_seconds: float) -> float | None:
    """
    Berechnet eine Backup-Zeit (time_seconds), falls diese None ist.
    Nutzt das Verhältnis von current_frame zu total_frames und multipliziert mit duration_seconds.

    Args:
        current_frame (int): Aktueller Frame
        total_frames (int): Gesamtanzahl Frames
        duration_seconds (float): Gesamtdauer in Sekunden

    Returns:
        float | None: Berechnete Zeit in Sekunden oder None, falls nicht berechenbar
    """
    if total_frames > 0 and duration_seconds > 0 and current_frame >= 0:
        return (current_frame / total_frames) * duration_seconds
    return None
