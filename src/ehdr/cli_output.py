"""CLI output and progress tracking functionality."""

import re
from datetime import timedelta
from typing import Callable, IO, Tuple

from ffmpeg import Progress

from ehdr.dataclass import CropHandler, DolbyVisionInfo
from ehdr.encoder import Encoder
from ehdr.video import Video

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


def monitor_x265_progress(stderr: IO[str], total_frames: int) -> None:
    """Monitor and display x265 encoding progress in real-time.

    Args:
        stderr: x265 process stderr stream
        total_frames: Total number of frames in the video
    """
    # Regex pattern to match x265 progress output
    # Format: 160 frames: 20.64 fps, 483.46 kb/s
    progress_pattern: re.Pattern[str] = re.compile(
        pattern=r'(\d+)\s+frames:\s+([\d.]+)\s+fps,\s+([\d.]+)\s+kb/s'
    )

    # Regex for info, warning, and error outputs - accepts arbitrary prefixes
    info_pattern: re.Pattern[str] = re.compile(
        pattern=r'(\S+)\s+\[(info|warning|error)\]:\s+(.*)'
    )

    first_update = True

    for line in stderr:
        line: str = line.strip()

        # Try to match progress line
        match: re.Match[str] | None = progress_pattern.search(line)
        if match:
            current_frame = int(match.group(1))
            fps = float(match.group(2))
            bitrate = float(match.group(3))  # Extract the bitrate

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

        # First check for Info/Warning/Error lines
        info_match: re.Match[str] | None = info_pattern.search(line)
        if info_match:
            prefix = info_match.group(1)  # Any prefix
            level = info_match.group(2)   # info, warning, or error
            message = info_match.group(3) # The actual message

            # Choose color based on level
            color = ""
            if level == "warning":
                color = YELLOW
            elif level == "error":
                color = RED

            if DEBUG_MODE == False and level == "info":
                continue

            # Output the message with color
            print(color_str(value=f"\r{prefix} [{level}]: {message}", color=color))
            continue


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

def print_video_infos(video: Video) -> None:
    """Print extracted video information.

    Args:
        video: Video object with metadata
    """
    resolution: str = f"{video.get_width()}x{video.get_height()}"

    color = BLUE
    print()
    print(f"{color_str('_', color)}" * 70)
    print("Video Information:")
    print(f"  Input File: {color_str(str(video.get_filepath()), color)}")
    print(f"  Resolution: {color_str(resolution, color)}")
    print(f"  Frame Rate: {color_str(video.get_fps(), color)}")
    print(f"  Color Primaries: {color_str(video.get_color_primaries(), color)}")
    print(f"  Color Transfer: {color_str(video.get_color_transfer(), color)}")
    print(f"  Color Space: {color_str(video.get_color_space(), color)}")
    print(f"  HDR/SDR: {color_str(video.get_color_format().value.upper(), color)}")
    if video.is_hdr_video():
        print("  HDR10 Metadata:")
        max_cll_max_fall = video.get_max_cll_max_fall()
        print(f"    MasterDisplay: {color_str(video.get_master_display() or 'N/A', color)}")
        if max_cll_max_fall:
            max_cll, max_fall = max_cll_max_fall
            print(f"    MaxCLL/MaxFALL: {color_str(f'{max_cll}, {max_fall}', color)}")
        else:
            print(f"    MaxCLL/MaxFALL: {color_str('N/A', color)}")

    dolby_vision_info: DolbyVisionInfo | None = video.get_dolby_vision_infos()
    if dolby_vision_info:
        print("  Dolby Vision Metadata:")
        print(f"    Profile: {color_str(dolby_vision_info.dv_profile or 'N/A', color)}")
        print(f"    Level: {color_str(dolby_vision_info.dv_level or 'N/A', color)}")
        print(f"    RPU Present: {color_str('YES' if dolby_vision_info.rpu_present_flag == 1 else 'NO', color)}")
    print(f"{color_str('_', color)}" * 70)
    print()

def print_encoding_params(encoder: Encoder) -> None:
    """Print encoding parameters.

    Args:
        encoder: Encoder object with encoding configuration
    """
    color = BLUE
    print()
    print(f"{color_str('_', color)}" * 70)
    print("Encoding Parameters:")
    print(f"  Output File: {color_str(str(encoder.get_target_file()), color)}")
    print(f"  CRF: {color_str(encoder.crf, color)}")
    print(f"  Preset: {color_str(encoder.preset, color)}")
    print(f"  Color-Format: {color_str(encoder.get_color_format().value.upper(), color)}")
    if encoder._is_cropped():
        crop_filter: str | None = encoder.get_crop_filter()
        print(f"  Crop: {color_str(crop_filter, color)}")
    else:
        print(f"  Crop: {color_str('No cropping applied', color)}")
    scale_dimensions: Tuple[int, int] | None = encoder._get_scale_dimensions()
    if scale_dimensions:
        w, h = scale_dimensions
        print(f"  Scale: {color_str(f"{w}x{h}", color)}")
    print(f"{color_str('_', color)}" * 70)
    print()

def callback_handler_crop_video(crop_handler: CropHandler) -> None:
    """Callback handler for crop video progress.

    Args:
        crop_handler: CropHandler instance
        message: Optional message to display
    """

    if crop_handler.finish_progress:
        print()  # New line on completion
        return

    completed_samples = crop_handler.completed_samples
    total_samples = crop_handler.total_samples
    percent: float = (completed_samples / total_samples * 100) if total_samples > 0 else 0.0
    progress_bar: str = create_progress_bar(percent=percent)
    if completed_samples == 0:
        print("\nCropping Progress:")
    print(f"\r{progress_bar} {percent:.1f}% | {completed_samples}/{total_samples}", end="", flush=True)
