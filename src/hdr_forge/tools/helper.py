"""Shared helper functions for FFmpeg pipeline operations with progress tracking."""

import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from hdr_forge.cli.cli_output import ProgressBarSpinner, monitor_process_progress, print_debug, create_ffmpeg_minimal_progress_handler, create_dovi_tool_progress_handler
from hdr_forge.core.service import build_cmd_pipe_str
from hdr_forge.typedefs.ffmpeg_typing import FfmpegMiniProgressInfo


def _parse_ffmpeg_progress_line(line: str, progress_data: dict) -> None:
    """Parse a single line from FFmpeg progress output.

    FFmpeg outputs progress in key=value format when started with -progress pipe:2.
    This function parses these lines and updates the progress_data dictionary.

    Args:
        line: A single line from FFmpeg stderr output
        progress_data: Dictionary to store parsed progress data
    """
    if '=' not in line:
        return

    key, _, value = line.partition('=')
    key = key.strip()
    value = value.strip()

    if key == 'frame':
        try:
            progress_data['frame'] = int(value)
        except ValueError:
            pass
    elif key == 'fps':
        try:
            progress_data['fps'] = float(value)
        except ValueError:
            pass
    elif key == 'progress':
        progress_data['progress'] = value


def _create_ffmpeg_progress_info(progress_data: dict, total_frames: int) -> FfmpegMiniProgressInfo:
    """Create a DoviProgressInfo object from parsed FFmpeg progress data.

    Args:
        progress_data: Dictionary with parsed progress data
        total_frames: Total number of frames

    Returns:
        DoviProgressInfo object with progress information
    """
    return FfmpegMiniProgressInfo(
        frame=progress_data.get('frame', 0),
        fps=progress_data.get('fps', 0.0),
        total_frames=total_frames
    )


def dovi_tool_progress_reader_thread(
    pipe,
    progress_callback: Optional[Callable[[float], None]],
    total_steps: int = 3
) -> None:
    """Thread function to read dovi_tool progress output.

    dovi_tool outputs progress by printing status lines when not attached to TTY:
    "Parsing RPU file..."
    "Processing input video for frame order info..."
    "Rewriting file with interleaved RPU NALs.."

    This thread counts each non-empty line as one progress step and calculates
    the percentage: (steps_done / total_steps) * 100

    Args:
        pipe: The stdout/stderr pipe from the dovi_tool subprocess
        progress_callback: Optional callback function to handle progress updates (receives percent: float)
        total_steps: Total number of expected steps/lines (default 3 for inject-rpu)
    """
    steps_done = 0

    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Each non-empty line is one progress step
            steps_done += 1
            percent = min((steps_done / total_steps) * 100, 100.0)

            if progress_callback:
                progress_callback(percent)

    except Exception:
        # Silently ignore errors in reader thread to avoid crashing main process
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _ffmpeg_progress_reader_thread(
    pipe,
    tool_process: subprocess.Popen,
    progress_callback: Optional[Callable[[FfmpegMiniProgressInfo], None]],
    total_frames: int,
    stderr_buffer: list
) -> None:
    """Thread function to read and parse FFmpeg progress output.

    This runs in a background thread and continuously reads FFmpeg's stderr output,
    parses progress information, and calls the progress callback.

    Args:
        pipe: The stderr pipe from the FFmpeg subprocess
        progress_callback: Optional callback function to handle progress updates
        total_frames: Total number of frames to process
        stderr_buffer: List to store stderr lines for error reporting
    """
    progress_data = {}

    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break

            line = line.strip()
            stderr_buffer.append(line)

            # Parse FFmpeg progress line
            _parse_ffmpeg_progress_line(line, progress_data)

            # When we get "progress=continue" or "progress=end", trigger callback
            if line.startswith('progress='):
                if progress_data and progress_callback:
                    progress_info: FfmpegMiniProgressInfo = _create_ffmpeg_progress_info(progress_data, total_frames)
                    progress_callback(progress_info)

                # Exit on "progress=end"
                if line == 'progress=end':
                    break
    except Exception as e:
        # Silently ignore errors in reader thread to avoid crashing main process
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass

    if not tool_process:
        return

    spinner = ProgressBarSpinner(
        description=None,
        without_headline=True
    )
    spinner.start()

    while tool_process.poll() is None:
        spinner.update(2)
        time.sleep(0.1)

    spinner.stop("100.0%")


def run_ffmpeg_tool_pipeline(
    input_path: Path,
    tool_cmd: list[str],
    process_name: str,
    total_frames: Optional[int] = None,
) -> tuple[int, bytes]:
    """Execute FFmpeg→Tool pipeline with optional progress tracking.

    This helper function handles the complete pipeline execution including:
    - FFmpeg HEVC extraction
    - Piping to external tool (dovi_tool, hevc_hdr_editor, etc.)
    - Progress tracking (FFmpeg-based or spinner fallback)
    - Process cleanup and error collection

    Args:
        input_path: Input video file path
        tool_cmd: Complete tool command list (starting with tool executable)
        process_name: Display name for progress tracking (e.g., "Extracting RPU metadata:")
        total_frames: Total number of frames for progress tracking (optional)

    Returns:
        Tuple of (returncode, stderr_bytes) from tool process

    Raises:
        RuntimeError: If FFmpeg or the tool are not found
    """
    # Build FFmpeg HEVC extraction command
    ffmpeg_cmd: list[str] = [
        'ffmpeg',
        '-i', str(input_path),
        '-c:v', 'copy',
        '-bsf:v', 'hevc_mp4toannexb',
        '-f', 'hevc',
    ]

    # Add progress reporting if we have frame info
    if total_frames:
        ffmpeg_cmd.extend(['-progress', 'pipe:2'])

    ffmpeg_cmd.append('-')

    print_debug(build_cmd_pipe_str([ffmpeg_cmd, tool_cmd]))

    # Create pipeline: ffmpeg | tool
    # FFmpeg stderr is used for progress if available, otherwise DEVNULL
    ffmpeg_stderr = subprocess.PIPE if total_frames else subprocess.DEVNULL

    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=ffmpeg_stderr,
        text=True if ffmpeg_stderr == subprocess.PIPE else False,
        bufsize=1 if ffmpeg_stderr == subprocess.PIPE else -1
    )

    tool_process = subprocess.Popen(
        tool_cmd,
        stdin=ffmpeg_process.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Close ffmpeg stdout in parent to allow SIGPIPE to be sent
    if ffmpeg_process.stdout:
        ffmpeg_process.stdout.close()

    # Start progress tracking if we have frame info
    if total_frames and ffmpeg_process.stderr:
        process_start_time = time.time()
        progress_callback = create_ffmpeg_minimal_progress_handler(
            total_frames=total_frames,
            process_start_time=process_start_time,
            process_name=process_name
        )

        stderr_buffer: list = []
        reader_thread = threading.Thread(
            target=_ffmpeg_progress_reader_thread,
            args=(ffmpeg_process.stderr, tool_process, progress_callback, total_frames, stderr_buffer),
            daemon=True
        )
        reader_thread.start()
    else:
        # Fallback to old spinner-based progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(tool_process, process_name),
            daemon=True
        )
        monitor_thread.start()

    # Wait for tool to complete
    _stdout, stderr = tool_process.communicate()

    # Wait for progress thread to finish
    if total_frames and ffmpeg_process.stderr:
        reader_thread.join(timeout=1.0)
    else:
        monitor_thread.join(timeout=1.0)

    # Wait for ffmpeg to complete
    ffmpeg_process.wait()

    return tool_process.returncode, stderr
