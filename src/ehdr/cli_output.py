"""CLI output and progress tracking functionality."""

import re
from datetime import timedelta
from typing import Callable, IO

from ffmpeg import Progress

# Constants
SUMMARY_LINE_WIDTH = 60
PROGRESS_BAR_WIDTH = 50
# ANSI escape codes für Terminal-Steuerung
CURSOR_UP_ONE = '\033[1A'
CLEAR_LINE = '\033[2K'  # Löscht die aktuelle Zeile
MOVE_TO_START = '\r'    # Bewegt Cursor zum Zeilenanfang

# Kompletter Code zum Löschen der aktuellen und der vorherigen Zeile
CLEAR_TWO_LINES = f"{CLEAR_LINE}{CURSOR_UP_ONE}{CLEAR_LINE}{MOVE_TO_START}"

# ANSI Farbcodes
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

DEBUG_MODE = False


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

    # Format für mehrzeilige Ausgabe
    bar_line: str = f"{progress_bar} {percent:5.1f}%"
    info_line: str = f"Frame: {current_frame}/{total_frames} | Speed: {speed_str} | FPS: {fps} | ETA: {eta} | Time: {time_str} | Bitrate: {bitrate_str} | Size: {size_str}"

    # Bei der ersten Ausgabe müssen wir nur die beiden Zeilen ausgeben
    if first_update:
        print()
        print(bar_line)
        print(info_line, end="", flush=True)
    else:
        # Bei nachfolgenden Updates löschen wir zuerst beide Zeilen komplett
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

        if progress.time and duration > 0:
            # Convert timedelta to seconds if necessary
            time_seconds: float = (
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


def monitor_x265_progress(stderr: IO[str], total_frames: int) -> None:
    """Monitor and display x265 encoding progress in real-time.

    Args:
        stderr: x265 process stderr stream
        total_frames: Total number of frames in the video
    """
    # Regex pattern to match x265 progress output
    # Format: 160 frames: 20.64 fps, 483.46 kb/s
    progress_pattern: re.Pattern[str] = re.compile(
        r'(\d+)\s+frames:\s+([\d.]+)\s+fps,\s+([\d.]+)\s+kb/s'
    )

    # Regex für Info-, Warn- und Fehlerausgaben - akzeptiert beliebige Präfixe
    info_pattern: re.Pattern[str] = re.compile(
        r'(\S+)\s+\[(info|warning|error)\]:\s+(.*)'
    )

    first_update = True

    for line in stderr:
        line = line.strip()

        # Try to match progress line
        match: re.Match[str] | None = progress_pattern.search(line)
        if match:
            current_frame = int(match.group(1))
            fps = float(match.group(2))
            bitrate = float(match.group(3))  # Extrahiere die Bitrate

            print_progress_info(
                first_update=first_update,
                current_frame=current_frame,
                total_frames=total_frames,
                fps=fps,
                speed=None,
                time_seconds=None,
                bitrate_kbs=bitrate,
                size_bytes=None,
            )
            if first_update:
                first_update = False

        # Prüfe zuerst auf Info/Warning/Error Zeilen
        info_match: re.Match[str] | None = info_pattern.search(line)
        if info_match:
            prefix = info_match.group(1)  # Beliebiges Präfix
            level = info_match.group(2)   # info, warning oder error
            message = info_match.group(3) # Die eigentliche Nachricht

            # Wähle Farbe basierend auf dem Level
            color = ""
            if level == "warning":
                color = YELLOW
            elif level == "error":
                color = RED

            if DEBUG_MODE == False and level == "info":
                continue

            # Gib die Nachricht mit Farbe aus
            print(f"\r{color}{prefix} [{level}]: {message}{RESET}")
            continue


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
