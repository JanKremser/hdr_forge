import subprocess
import threading
from pathlib import Path

from hdr_forge.cli.cli_output import monitor_process_progress, print_debug
from hdr_forge.core.service import build_cmd_array_to_str
from hdr_forge.tools.helper import get_tool_path
from hdr_forge.tools.ffmpeg import clean_subprocess_env

def verify_hdr10plus(input_path: Path) -> bool:
    """Verify if input file contains HDR10+ metadata.

    Args:
        input_path: Path to input media file
    Returns:
        True if HDR10+ metadata is present, False otherwise
    Raises:
        FileNotFoundError: If input file does not exist
        RuntimeError: If hdr10plus_tool fails to execute
    """
    if not input_path.exists():
        raise FileNotFoundError(f"file not found: {str(input_path)}")

    tool_exec = get_tool_path('hdr10plus_tool')

    try:
        tool_cmd: list[str] = [
            tool_exec,
            '--verify',
            'extract',
            str(input_path)
        ]

        print_debug(build_cmd_array_to_str(tool_cmd))

        result = subprocess.run(
            tool_cmd,
            capture_output=True,
            text=True,
            check=True,
            env=clean_subprocess_env()
        )

        return True if "Dynamic HDR10+ metadata detected" in result.stdout else False

    except subprocess.CalledProcessError as e:
        #error_msg = e.stderr if e.stderr else str(e)
        return False
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure hdr10plus_tool is installed."
        )

def extract_hdr10plus_metadata(input_path: Path, output_path: Path) -> Path:
    """Extract HDR10+ metadata from input file.

    Args:
        input_path: Path to input media file

    Returns:
        Path to extracted HDR10+ JSON metadata file

    Raises:
        RuntimeError: If multiplexing fails
    """

    if not input_path.exists():
        raise FileNotFoundError(f"file not found: {str(input_path)}")

    tool_exec = get_tool_path('hdr10plus_tool')

    try:
        tool_cmd: list[str] = [
            tool_exec,
            'extract',
            str(input_path),
            '-o', f"{str(output_path)}",
        ]

        print_debug(build_cmd_array_to_str(tool_cmd))

        tool_process = subprocess.Popen(
            tool_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=clean_subprocess_env()
        )

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(tool_process, "Extracting HDR10+ metadata:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait to complete
        _stdout, stderr = tool_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if tool_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"hdr10plus tool failed: {error_msg}")

        if not output_path.exists():
            raise RuntimeError("HDR10+ metadata file was not created")

        print_debug(f"HDR10+ metadata file successfully: {str(output_path)}")
        return output_path

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure hdr10plus_tool is installed."
        )
    except Exception as e:
        raise RuntimeError(f"hdr10plus_tool failed: {e}")


def inject_hdr10plus_metadata(input_path: Path, hdr10plus_metadata_path: Path, output_path: Path) -> Path:
    """Extract HDR10+ metadata from input file.

    Args:
        input_path: Path to input media file

    Returns:
        Path to extracted HDR10+ JSON metadata file

    Raises:
        RuntimeError: If multiplexing fails
    """

    if not input_path.exists():
        raise FileNotFoundError(f"file not found: {str(input_path)}")

    if not hdr10plus_metadata_path.exists():
        raise FileNotFoundError(f"HDR10+ metadata file not found: {str(hdr10plus_metadata_path)}")

    tool_exec = get_tool_path('hdr10plus_tool')

    try:
        tool_cmd: list[str] = [
            tool_exec,
            'inject',
            '-i', str(input_path),
            '-j', str(hdr10plus_metadata_path),
            '-o', str(output_path),
        ]

        print_debug(build_cmd_array_to_str(tool_cmd))

        tool_process = subprocess.Popen(
            tool_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=clean_subprocess_env()
        )

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(tool_process, "Inject HDR10+ metadata:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait to complete
        _stdout, stderr = tool_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if tool_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"hdr10plus tool failed: {error_msg}")

        if not output_path.exists():
            raise RuntimeError("hevc file with injected HDR10+ metadata was not created")

        print_debug(f"hevc file with injected HDR10+ metadata successfully: {str(output_path)}")
        return output_path

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure hdr10plus_tool is installed."
        )
    except Exception as e:
        raise RuntimeError(f"hdr10plus_tool failed: {e}")
