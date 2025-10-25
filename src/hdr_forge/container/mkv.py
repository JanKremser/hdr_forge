import subprocess
import threading
import json
from pathlib import Path
from typing import Optional

from hdr_forge.cli.cli_output import monitor_process_progress
from hdr_forge.typedefs.mkv_typing import MkvInfo, parse_mkv_info

def get_mkvmerge_path() -> str:
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


def extract_hevc(input_path: Path, output_hevc: Optional[Path] = None) -> Path:
    if output_hevc is None:
        output_hevc = input_path.with_name(f"{input_path.stem}_BL.hevc")

    try:
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
            str(output_hevc)
        ]

        # Execute ffmpeg to extract HEVC
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(ffmpeg_process, "Extracting HEVC:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if not output_hevc.exists():
            raise RuntimeError("HEVC file was not created")

        print(f"- HEVC extracted successfully: {str(output_hevc)}")
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

    mkvmerge_exec: str = get_mkvmerge_path()

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

        print(f"- HEVC muxed to MKV successfully: {str(output_mkv)}")
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
    mkvmerge_exec: str = get_mkvmerge_path()

    try:
        # Create mkvmerge command
        mkvmerge_cmd: list[str] = [
            mkvmerge_exec,
            '-J',
            str(input_mkv_mp4_ts_file)
        ]

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
