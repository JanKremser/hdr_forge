import subprocess
import threading
import json
import time
from pathlib import Path
from typing import Optional

from hdr_forge.cli.cli_output import monitor_process_progress, print_debug, create_ffmpeg_minimal_progress_handler
from hdr_forge.core.service import build_cmd_array_to_str
from hdr_forge.tools.helper import _ffmpeg_progress_reader_thread
from hdr_forge.typedefs.mkv_typing import MkvInfo, parse_mkv_info

def _get_mkvmerge_path() -> str:
    """Get path to mkvmerge executable.

    Looks for mkvmerge in project directory first, then falls back to system path.

    Returns:
        Path to mkvmerge executable as string
    """
    project_root: Path = Path(__file__).parent.parent.parent
    mkvmerge_path: Path = project_root / "mkvmerge"

    if mkvmerge_path.exists():
        return str(mkvmerge_path)
    else:
        return "mkvmerge"


def extract_hevc(
    input_path: Path,
    output_hevc: Optional[Path] = None,
    total_frames: Optional[int] = None,
    duration: Optional[float] = None
) -> Path:
    """Extract HEVC bitstream from video file.

    Args:
        input_path: Path to input video file
        output_hevc: Path to output HEVC file. If None, generates filename based on input
        total_frames: Total number of frames in the video (for progress tracking)
        duration: Total duration of the video in seconds (for progress tracking)

    Returns:
        Path to the extracted HEVC file

    Raises:
        RuntimeError: If extraction fails
    """
    if output_hevc is None:
        output_hevc = input_path.with_name(f"{input_path.stem}_BL.hevc")

    try:
        # Build FFmpeg command
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
        ]

        # Add progress reporting if we have frame/duration info
        if total_frames and duration:
            ffmpeg_cmd.extend(['-progress', 'pipe:2'])

        ffmpeg_cmd.append(str(output_hevc))

        print_debug(build_cmd_array_to_str(ffmpeg_cmd))

        # FFmpeg stderr is used for progress if available, otherwise DEVNULL
        ffmpeg_stderr = subprocess.PIPE if (total_frames and duration) else subprocess.DEVNULL

        # Execute ffmpeg to extract HEVC
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=ffmpeg_stderr,
            text=True if ffmpeg_stderr == subprocess.PIPE else False,
            bufsize=1 if ffmpeg_stderr == subprocess.PIPE else -1
        )

        # Start progress tracking if we have frame/duration info
        if total_frames and duration and ffmpeg_process.stderr:
            process_start_time = time.time()
            progress_callback = create_ffmpeg_minimal_progress_handler(
                total_frames=total_frames,
                duration=duration,
                process_start_time=process_start_time,
                process_name="Extracting HEVC:"
            )

            stderr_buffer: list = []
            reader_thread = threading.Thread(
                target=_ffmpeg_progress_reader_thread,
                args=(ffmpeg_process.stderr, ffmpeg_process, progress_callback, total_frames, stderr_buffer),
                daemon=True
            )
            reader_thread.start()
        else:
            # Fallback to old spinner-based progress
            monitor_thread = threading.Thread(
                target=monitor_process_progress,
                args=(ffmpeg_process, "Extracting HEVC:"),
                daemon=True
            )
            monitor_thread.start()

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        # Wait for progress thread to finish
        if total_frames and duration:
            if ffmpeg_process.stderr:
                reader_thread.join(timeout=1.0)
        else:
            monitor_thread.join(timeout=1.0)

        if ffmpeg_process.returncode != 0:
            raise RuntimeError("FFmpeg extraction failed")

        if not output_hevc.exists():
            raise RuntimeError("HEVC file was not created")

        print_debug(f"- HEVC extracted successfully: {str(output_hevc)}")
        return output_hevc

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract HEVC: {e}")


def mux_hevc_to_mkv(input_hevc_path: Path, input_mkv: Optional[Path] = None, output_mkv: Optional[Path] = None) -> Path:
    if output_mkv is None:
        output_mkv = input_hevc_path.with_name(f"{input_hevc_path.stem}_BL.mkv")

    mkvmerge_exec: str = _get_mkvmerge_path()

    try:
        mkvmerge_cmd: list[str] = [
            mkvmerge_exec,
            '-o', str(output_mkv),
        ]

        if input_mkv is not None:
            mkvmerge_cmd.extend([
                '--no-video', str(input_mkv),
            ])

        mkvmerge_cmd.extend([
            str(input_hevc_path),
        ])

        print_debug(build_cmd_array_to_str(mkvmerge_cmd))

        # Execute mkvmerge to mux HEVC into MKV
        mkvmerge_process = subprocess.Popen(
            mkvmerge_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(mkvmerge_process, "Muxing HEVC to MKV:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for mkvmerge to complete
        mkvmerge_process.wait()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if not output_mkv.exists():
            raise RuntimeError("MKV file was not created")

        print_debug(f"HEVC muxed to MKV successfully: {str(output_mkv)}")
        return output_mkv

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure mkvmerge is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to mux HEVC to MKV: {e}")

def extract_container_info_json(input_mkv_mp4_ts_file: Path) -> MkvInfo:
    """Extracts JSON information from an MKV file using mkvmerge.

    Args:
        input_mkv: Path to the input MKV, TS, mp4 file

    Returns:
        MkvInfo object with typed information extracted from the MKV file

    Raises:
        RuntimeError: If mkvmerge is not installed or extraction fails
    """
    mkvmerge_exec: str = _get_mkvmerge_path()

    try:
        # Create mkvmerge command
        mkvmerge_cmd: list[str] = [
            mkvmerge_exec,
            '-J',
            str(input_mkv_mp4_ts_file)
        ]

        print_debug(build_cmd_array_to_str(mkvmerge_cmd))

        # Execute mkvmerge to extract JSON information
        process = subprocess.run(
            mkvmerge_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse JSON output
        mkv_info_dict = json.loads(process.stdout)

        try:
            # Try to parse into typed MkvInfo object
            return parse_mkv_info(info_dict=mkv_info_dict)
        except Exception as e:
            # Fall back to returning the raw dictionary if parsing fails
            raise RuntimeError(
                f"Warning: Could not parse MKV info into typed object: {e}"
            )

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure that mkvmerge is installed."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error extracting MKV information: {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Error parsing MKV information: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while extracting MKV information: {e}")
