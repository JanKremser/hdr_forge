"""CLI output and progress tracking functionality."""

import time
import subprocess
from typing import Callable, Optional

from hdr_forge.core import config
from hdr_forge.typedefs.ffmpeg_typing import FfmpegProgressInfo, FfmpegMiniProgressInfo


# Constants
SUMMARY_LINE_WIDTH = 60
PROGRESS_BAR_WIDTH = 70
# ANSI escape codes for terminal control
ANSI_CURSOR_UP_ONE = '\033[1A'
ANSI_CLEAR_LINE = '\033[2K'  # Clears the current line
ANSI_MOVE_TO_START = '\r'    # Moves cursor to the beginning of the line

# Complete code to clear current and previous line
ANSI_CLEAR_TWO_LINES = f"{ANSI_CLEAR_LINE}{ANSI_CURSOR_UP_ONE}{ANSI_CLEAR_LINE}{ANSI_MOVE_TO_START}"

# ANSI color codes
ANSI_RED = '\033[91m'
ANSI_GREEN = '\033[92m'
ANSI_YELLOW = '\033[93m'
ANSI_BLUE = '\033[94m'
ANSI_PURPLE = '\033[95m'
ANSI_CYAN = '\033[96m'
ANSI_BLACK = '\033[30m'
ANSI_ORANGE = '\033[38;5;208m'
ANSI_PINK = '\033[38;5;213m'

ANSI_GREEN_BG = '\033[102m'
ANSI_GRAY_BG = '\033[100m'

ANSI_RESET = '\033[0m'

# Rainbow color sequence
RAINBOW_COLORS = [
    ANSI_RED,
    ANSI_PINK,
    ANSI_ORANGE,
    ANSI_YELLOW,
    ANSI_GREEN,
    ANSI_CYAN,
    ANSI_BLUE,
    ANSI_PURPLE,
]


def clear_lines(n: int) -> str:
    """Generate ANSI escape codes to clear n lines in the terminal.

    Args:
        n: Number of lines to clear

    Returns:
        ANSI escape code string to clear n lines
    """
    return ''.join(f"{ANSI_CLEAR_LINE}{ANSI_CURSOR_UP_ONE}" for _ in range(n-1)) + ANSI_CLEAR_LINE + ANSI_MOVE_TO_START


def color_str(value: str | int | float | None, color: str) -> str:
    """Wrap text with ANSI color codes.

    Args:
        text: The text to color
        color_code: The ANSI color code

    Returns:
        Colored text string
    """
    return f"{color}{str(value)}{ANSI_RESET}"


def rainbow_text(text: str, color_sequence: list[str] | None = None) -> str:
    """Apply rainbow colors to each character in a multi-line text.

    Each non-whitespace character gets a different color from the rainbow sequence.
    Whitespace characters (spaces, newlines, tabs) are preserved without color.

    Args:
        text: The multi-line text to colorize
        color_sequence: Optional custom color sequence (default: RAINBOW_COLORS)

    Returns:
        Text with rainbow color codes applied to each character
    """
    if color_sequence is None:
        color_sequence = RAINBOW_COLORS

    colored_text = []
    color_index = 0

    for char in text:
        # Skip coloring whitespace characters
        if char in (' ', '\n', '\t', '\r'):
            colored_text.append(char)
        else:
            # Apply color to non-whitespace character
            color = color_sequence[color_index % len(color_sequence)]
            colored_text.append(f"{color}{char}{ANSI_RESET}")
            color_index += 1

    return ''.join(colored_text)


def print_warn(msg: str) -> None:
    """Print a warning message in yellow color.

    Args:
        message: The warning message to print
    """
    print(f"{color_str('Warning:',ANSI_YELLOW)} {msg}")


def print_err(msg: str) -> None:
    """Print an error message in red color.

    Args:
        message: The error message to print
    """
    print(f"{color_str('Error:', ANSI_RED)} {msg}")


def print_debug(msg: str) -> None:
    """Print an Debug message in purple color.

    Args:
        message: The Debug message to print
    """
    if config.debug_mode == False:
        return
    print(f"{color_str(f'Debug: {msg}', ANSI_PURPLE)}")

def print_info(msg: str) -> None:
    """Print an Info message in blue color.

    Args:
        message: The Info message to print
    """
    print(f"{color_str(f'Info: {msg}', ANSI_BLUE)}")


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
                bar_chars.append(f"{ANSI_GREEN_BG}{ANSI_BLACK}{text[i - text_pos]}{ANSI_RESET}")
            else:
                bar_chars.append(f"{ANSI_GRAY_BG}{ANSI_BLACK}{text[i - text_pos]}{ANSI_RESET}")
        elif i < filled:
            bar_chars.append(f"{ANSI_GREEN}█{ANSI_RESET}")
        elif i == filled and empty > 0:
            bar_chars.append(f"{ANSI_GREEN}░{ANSI_RESET}")
        else:
            bar_chars.append(f"{ANSI_GRAY_BG} {ANSI_RESET}")

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


def print_progress_info(first_update: bool, current_frame: int, total_frames: int, duration_seconds: float, process_time_seconds: float, fps: float, speed: float | None, time_seconds: float | None, bitrate_kbs: float | None, size_bytes: int | None, video_fps: float | None) -> None:
    #fix current_frame
    if current_frame > total_frames:
        current_frame = total_frames
    elif current_frame < 0:
        current_frame = total_frames

    # Calculate percentage
    percent: float = (current_frame / total_frames * 100) if total_frames > 0 else 0.0

    # Calculate ETA
    eta: str = calculate_eta(fps=fps, current_frame=current_frame, total_frames=total_frames)

    # Create progress bar
    progress_bar: str = create_progress_bar_with_percent(percent=percent)

    #if time_seconds is None or (time_seconds == 0 and current_frame > 0):
    time_seconds = calculate_time_seconds(
        current_frame=current_frame,
        total_frames=total_frames,
        duration_seconds=duration_seconds,
        backup_time_seconds=time_seconds,
    )
    time_str: str = format_time(seconds=time_seconds) if time_seconds is not None else "--:--:--"

    duration_str: str = format_time(seconds=duration_seconds) if duration_seconds is not None else "--:--:--"
    process_time_str: str = format_time(seconds=process_time_seconds)

    speed = calculate_speed(
        actual_fps=fps,
        video_fps=video_fps,
        backup_speed=speed,
    )
    speed_str: str = f"{speed:.2f}" if speed is not None else "--.-"

    bitrate_str: str = f"{bitrate_kbs:.2f}" if bitrate_kbs is not None else "--.-"

    size_kb_str: str = "--.- KB"
    size_gb_str: str = "--.- GB"
    if size_bytes is not None:
        size_kb_str: str = f"{size_bytes / 1024:.2f}"
        size_gb_str: str = f"{size_bytes / 1024 / 1024 / 1204:.2f}"

    # Estimate final file size
    estimated_size_bytes = estimate_final_size(size_bytes, current_frame, total_frames)
    estimated_size_kb_str = "--.- KB"
    estimated_size_gb_str = "--.- GB"
    if estimated_size_bytes is not None:
        estimated_size_kb_str: str = f"{estimated_size_bytes / 1024:.2f}"
        estimated_size_gb_str: str = f"{estimated_size_bytes / 1024 / 1024 / 1024:.2f}"

    # Format for multi-line output
    info_line: str = f"""
{color_str("-" * 70, ANSI_GREEN)}
Frame         : {color_str(current_frame, ANSI_GREEN)}/{total_frames}
Speed         : {color_str(speed_str, ANSI_GREEN)}x | {color_str(fps, ANSI_GREEN)} FPS

ETA           : {color_str(eta, ANSI_GREEN)}
Time          : {color_str(time_str, ANSI_GREEN)}/{duration_str}
Process Time  : {color_str(process_time_str, ANSI_GREEN)}

Bitrate       : {color_str(bitrate_str, ANSI_GREEN)} kb/s
Size          : {color_str(size_kb_str, ANSI_GREEN)} KB ~> {color_str(size_gb_str, ANSI_GREEN)} GB
Final size    : {color_str(estimated_size_kb_str, ANSI_GREEN)} KB ~> {color_str(estimated_size_gb_str, ANSI_GREEN)} GB
{progress_bar}
{color_str("-" * 70, ANSI_GREEN)}"""

    # For the first output, we only need to print both lines
    print(clear_lines(14) if first_update is False else "", end="")
    print(info_line, end="", flush=True)

def print_progress_info_minimal(process_name: str, first_update: bool, current_frame: int, total_frames: int, duration_seconds: float, process_time_seconds: float, fps: float, time_seconds: float | None) -> None:
    #fix current_frame
    if current_frame > total_frames:
        current_frame = total_frames
    elif current_frame < 0:
        current_frame = total_frames

    # Calculate percentage
    percent: float = (current_frame / total_frames * 100) if total_frames > 0 else 0.0

    # Calculate ETA
    eta: str = calculate_eta(fps=fps, current_frame=current_frame, total_frames=total_frames)

    # Create progress bar
    progress_bar: str = create_progress_bar_with_percent(percent=percent)

    process_time_str: str = format_time(seconds=process_time_seconds)

    bar_len = 70
    bar_len: int = bar_len - (len(process_name) + 4)
    # Format for multi-line output
    info_line: str = f"""
{color_str(f"-- {process_name} " + ("-" * bar_len), ANSI_GREEN)}
Frame         : {color_str(current_frame, ANSI_GREEN)}/{total_frames}
ETA           : {color_str(eta, color=ANSI_GREEN)}
Process Time  : {color_str(process_time_str, ANSI_GREEN)}
{progress_bar}
{color_str("-" * 70, ANSI_GREEN)}"""

    # For the first output, we only need to print both lines
    print(clear_lines(7) if first_update is False else "", end="")
    print(info_line, end="", flush=True)


def create_ffmpeg_progress_handler(duration: float, total_frames: int, process_start_time: float, video_fps: float | None) -> Callable[[FfmpegProgressInfo], None]:
    """Create a progress handler for ffmpeg encoding.

    Args:
        duration: Total video duration in seconds

    Returns:
        Progress handler function
    """
    first_update = True

    def on_progress(progress: FfmpegProgressInfo) -> None:
        """Handle progress updates from ffmpeg."""
        nonlocal first_update

        time_seconds: float = 0.0
        if progress.time and duration > 0:
            time_seconds = progress.time


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
            video_fps=video_fps,
        )
        if first_update:
            first_update = False

    return on_progress


def create_ffmpeg_minimal_progress_handler(total_frames: int, duration: float, process_start_time: float, process_name: str) -> Callable[[FfmpegMiniProgressInfo], None]:
    """Create a progress handler for dovi_tool operations.

    Args:
        total_frames: Total number of frames to process
        duration: Total video duration in seconds
        process_start_time: Start time of the process

    Returns:
        Progress handler function that accepts DoviProgressInfo
    """
    first_update = True

    def on_progress(progress: FfmpegMiniProgressInfo) -> None:
        """Handle progress updates from dovi_tool FFmpeg pipeline."""
        nonlocal first_update

        current_frame: int = progress.frame
        fps: float = progress.fps if progress.fps else 0.0

        process_time_seconds: float = _calc_process_time_seconds(
            process_start_time=process_start_time
        )

        # Calculate time_seconds based on frame progress
        time_seconds: float | None = None
        if total_frames > 0 and duration > 0 and current_frame >= 0:
            time_seconds = (current_frame / total_frames) * duration

        print_progress_info_minimal(
            process_name=process_name,
            first_update=first_update,
            current_frame=current_frame,
            total_frames=total_frames,
            duration_seconds=duration,
            process_time_seconds=process_time_seconds,
            fps=fps,
            time_seconds=time_seconds,
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
    color = ANSI_BLUE
    print(f"{color_str('_', color)}" * 70)
    print("Conversion complete:")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")
    print(f"{color_str('_', color)}" * 70)


class ProgressBarSpinner:
    """Simple spinner progress indicator for indeterminate tasks."""

    def __init__(self, description: str | None = None, without_headline: bool = False) -> None:
        self.description: str = description or "Processing"
        self.spinner = ['|', '/', '-', '\\']
        self.index = 0
        self.running = False
        self.without_headline: bool = without_headline

    def start(self) -> None:
        """Start the spinner."""
        self.running = True

        if self.without_headline:
            return
        start_line_len = 70
        start_line_len: int = start_line_len - (len(self.description) + 4)
        print(color_str(f"-- {self.description} " + ("-" * start_line_len), ANSI_GREEN), flush=True)

    def update(self, count_clear_lines: int | None = None, percent: float | None = None) -> None:
        """Update the spinner state."""
        if not self.running:
            return

        if percent is not None:
            bar: str = create_progress_bar(
                percent=percent,
                text=f"{percent:.1f}% | {self.spinner[self.index % 4]}"
            )
        else:
            bar: str = create_progress_bar(
                percent=(self.index % 20) * 5,
                text=f"Processing {self.spinner[self.index % 4]}"
            )  # Indeterminate progress

        end_line = color_str("-" * 70, ANSI_GREEN)

        clear_lines_str: str = ""
        if count_clear_lines:
            clear_lines_str = clear_lines(count_clear_lines)
        else:
            if self.index == 0:
                clear_lines_str = clear_lines(1)
            else:
                clear_lines_str = clear_lines(2)

        status: str = f"{clear_lines_str}{bar}\n{end_line}"
        print(status, end='', flush=True)
        self.index += 1

    def stop(self, text: str | None, long_info_text: str | None = None) -> None:
        """Stop the spinner."""
        self.running = False
        bar: str = create_progress_bar(percent=100, text=text or "Processing Done")
        end_line = color_str("-" * 70, ANSI_GREEN)
        long_info: str = f"{long_info_text}\n" if long_info_text else ""
        status: str = f"{ANSI_CLEAR_TWO_LINES}{bar}\n{long_info}{end_line}\n"
        print(status, end='', flush=True)

def monitor_process_progress(process: subprocess.Popen, description: str) -> None:
    """Monitor a running process and display a progress bar.

    Args:
        process: The subprocess.Popen process to monitor
        description: Description text to show before the progress bar
    """
    if not process:
        return

    spinner = ProgressBarSpinner(description=description)
    spinner.start()

    while process.poll() is None:
        spinner.update()
        time.sleep(0.1)

    spinner.stop(None)

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
        "1.37:1 (Academy)": 1.37,
        "3:2": 1.5,
        "16:10": 1.6,
        "1.66:1 (European Widescreen)": 1.6667,
        "16:9": 1.7777,
        "1.85:1 (US Widescreen)": 1.85,
        "18:9": 2.0,
        "2.20:1 (70mm)": 2.20,
        "21:9": 2.3333,
        "2.35:1 (CinemaScope Classic)": 2.35,
        "2.39:1 (CinemaScope Modern)": 2.39,
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

def calculate_speed(actual_fps: float, video_fps: float | None, backup_speed: float | None) -> float | None:
    """
    Calculates a backup speed value if speed is None.
    Uses current frames and elapsed process time.

    Args:
        actual_fps (float): Actual frames processed per second
        video_fps (float): Original video frames per second
        backup_speed (float | None): Backup speed value

    Returns:
        float | None: Calculated speed (e.g. 1.23 for 1.23x), or None if not calculable
    """
    if actual_fps > 0 and video_fps and video_fps > 0:
        return actual_fps / video_fps
    return backup_speed

def calculate_time_seconds(current_frame: int, total_frames: int, duration_seconds: float, backup_time_seconds: float | None) -> float | None:
    """
    Calculates a backup time value (time_seconds) if it is None.
    Uses the ratio of current_frame to total_frames and multiplies by duration_seconds.

    Args:
        current_frame (int): Current frame number
        total_frames (int): Total number of frames
        duration_seconds (float): Total video duration in seconds
        backup_time_seconds (float | None): Backup time value

    Returns:
        float | None: Calculated time in seconds or None if not calculable
    """
    if total_frames > 0 and duration_seconds > 0 and current_frame >= 0:
        return (current_frame / total_frames) * duration_seconds
    return backup_time_seconds
