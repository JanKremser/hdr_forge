"""FFmpeg wrapper for direct subprocess execution with progress tracking."""

import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

from hdr_forge.cli.cli_output import print_err
from hdr_forge.typedefs.ffmpeg_typing import ProgressInfo


def _parse_progress_line(line: str, progress_data: Dict[str, str]) -> None:
    """Parse a single line from FFmpeg progress output.

    Args:
        line: Line from FFmpeg progress output (format: key=value)
        progress_data: Dictionary to store parsed key-value pairs
    """
    line = line.strip()
    if '=' in line:
        key, value = line.split('=', 1)
        progress_data[key.strip()] = value.strip()


def _create_progress_info(progress_data: Dict[str, str]) -> ProgressInfo:
    """Create ProgressInfo from parsed progress data.

    Args:
        progress_data: Dictionary with parsed FFmpeg progress data

    Returns:
        ProgressInfo object with parsed values
    """
    # Parse frame
    frame = int(progress_data.get('frame', 0))

    # Parse fps
    fps = float(progress_data.get('fps', 0.0))

    # Parse speed (format: "0.837x")
    speed = None
    speed_str = progress_data.get('speed')
    if speed_str and speed_str != 'N/A':
        speed_match = re.match(r'([\d.]+)x', speed_str)
        if speed_match:
            speed = float(speed_match.group(1))

    # Parse time (from out_time_us in microseconds)
    time_seconds = None
    out_time_us = progress_data.get('out_time_us')
    if out_time_us and out_time_us != 'N/A':
        try:
            time_seconds = float(out_time_us) / 1_000_000
        except ValueError:
            pass

    # Fallback: parse from out_time (format: "00:00:06.640000")
    if time_seconds is None:
        out_time = progress_data.get('out_time')
        if out_time and out_time != 'N/A':
            time_match = re.match(r'(\d+):(\d+):([\d.]+)', out_time)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                seconds = float(time_match.group(3))
                time_seconds = hours * 3600 + minutes * 60 + seconds

    # Parse bitrate (format: "483.46kbits/s")
    bitrate = None
    bitrate_str = progress_data.get('bitrate')
    if bitrate_str and bitrate_str != 'N/A':
        bitrate_match = re.match(r'([\d.]+)kbits/s', bitrate_str)
        if bitrate_match:
            bitrate = float(bitrate_match.group(1))

    # Parse size (in bytes)
    size = None
    total_size = progress_data.get('total_size')
    if total_size and total_size != 'N/A':
        try:
            size = int(total_size)
        except ValueError:
            pass

    return ProgressInfo(
        frame=frame,
        fps=fps,
        speed=speed,
        time=time_seconds,
        bitrate=bitrate,
        size=size
    )


def _progress_reader_thread(pipe, progress_callback: Callable[[ProgressInfo], None], stderr_buffer: list) -> None:
    """Thread function to read and parse FFmpeg progress output.

    Args:
        pipe: File-like object (stderr) to read from
        progress_callback: Callback function to call with ProgressInfo
        stderr_buffer: List to store all stderr lines for error reporting
    """
    progress_data: Dict[str, str] = {}

    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break

            line = line.strip()

            # Store all lines in buffer for error reporting
            stderr_buffer.append(line)

            # Parse key=value pair
            _parse_progress_line(line, progress_data)

            # When we get "progress=continue" or "progress=end", we have a complete update
            if line.startswith('progress='):
                if progress_data:
                    progress_info: ProgressInfo = _create_progress_info(progress_data=progress_data)
                    if progress_callback:
                        progress_callback(progress_info)

                # For "progress=end", we're done
                if line == 'progress=end':
                    break

    except Exception:
        # Silently ignore parsing errors
        pass
    finally:
        pipe.close()


def run_ffmpeg(
    input_file: Path,
    output_file: Path,
    output_options: Dict[str, str],
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    timeout: Optional[float] = None
) -> bool:
    """Execute FFmpeg with progress tracking.

    Args:
        input_file: Path to input video file
        output_file: Path to output video file
        output_options: Dictionary of FFmpeg output options (key: value pairs)
        progress_callback: Optional callback function for progress updates
        timeout: Optional timeout in seconds

    Returns:
        True if FFmpeg executed successfully, False otherwise

    Raises:
        RuntimeError: If FFmpeg execution fails
    """
    # Build FFmpeg command
    cmd = ['ffmpeg', '-y']

    # Add progress reporting to stderr
    if progress_callback:
        cmd.extend(['-progress', 'pipe:2'])

    # Add input file
    cmd.extend(['-i', str(input_file)])

    # Add output options
    # Handle multiple identical keys (e.g., multiple -metadata:s:v arguments)
    for key, value in output_options.items():
        if isinstance(value, list):
            # If value is a list, add the key multiple times
            for v in value:
                cmd.extend([f'-{key}', str(v)])
        else:
            cmd.extend([f'-{key}', str(value)])

    # Add output file
    cmd.append(str(output_file))

    # Buffer to store stderr for error reporting
    stderr_buffer = []

    try:
        # Start FFmpeg process - always capture stderr
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )

        # Start progress reader thread
        reader_thread = None
        if process.stderr:
            reader_thread = threading.Thread(
                target=_progress_reader_thread,
                args=(process.stderr, progress_callback, stderr_buffer),
                daemon=True
            )
            reader_thread.start()

        # Wait for process to complete
        returncode = process.wait(timeout=timeout)

        # Wait for reader thread to finish
        if reader_thread:
            reader_thread.join(timeout=1.0)

        if returncode != 0:
            # Print stderr output for debugging
            if stderr_buffer:
                print_err("\n=== FFmpeg Error Output ===")
                for line in stderr_buffer:
                    if line:  # Skip empty lines
                        print_err(line)
                print_err("===========================\n")
            return False

        return True

    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f"FFmpeg execution timed out after {timeout} seconds")
    except Exception as e:
        raise RuntimeError(f"FFmpeg execution failed: {e}")
