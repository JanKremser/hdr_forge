import subprocess
import threading
import json
from pathlib import Path

from hdr_forge.cli.cli_output import monitor_process_progress, print_debug
from hdr_forge.core.service import build_cmd_array_to_str
from hdr_forge.tools.helper import get_tool_path
from hdr_forge.tools.ffmpeg import clean_subprocess_env
from hdr_forge.typedefs.mkv_typing import MkvInfo, parse_mkv_info


def mux_hevc_to_mkv(input_hevc_path: Path, input_mkv: Path | None = None, output_mkv: Path | None = None) -> Path:
    if output_mkv is None:
        output_mkv = input_hevc_path.with_name(f"{input_hevc_path.stem}_BL.mkv")

    mkvmerge_exec: str = get_tool_path('mkvmerge')

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
            stderr=subprocess.DEVNULL,
            env=clean_subprocess_env()
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
    mkvmerge_exec: str = get_tool_path('mkvmerge')

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
            check=True,
            env=clean_subprocess_env()
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
