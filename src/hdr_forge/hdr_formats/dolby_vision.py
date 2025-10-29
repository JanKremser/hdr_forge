"""Dolby Vision metadata extraction and handling."""

import re
import subprocess
import threading
from pathlib import Path
from typing import Optional

from hdr_forge.cli.cli_output import monitor_process_progress, print_debug
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfile, DolbyVisionRpuInfo


def get_dovi_tool_path() -> str:
    """Get path to dovi_tool executable.

    Looks for dovi_tool in project directory first, then falls back to system path.

    Returns:
        Path to dovi_tool executable as string
    """
    # Get path to local dovi_tool (in project root)
    project_root = Path(__file__).parent.parent.parent
    dovi_tool_path = project_root / "dovi_tool"

    # Fallback to system dovi_tool if local one doesn't exist
    if dovi_tool_path.exists():
        return str(dovi_tool_path)
    else:
        return "dovi_tool"


def extract_base_layer(input_path: Path, output_hevc: Optional[Path] = None) -> Path:
    """Extract Dolby Vision base layer (HEVC without RPU).

    Args:
        input_path: Path to input video file
        output_hevc: Optional path for HEVC output file. If None, generates
                    filename based on input (input.mkv -> input.hevc)

    Returns:
        Path to the extracted base layer HEVC file

    Raises:
        RuntimeError: If base layer extraction fails
    """
    if output_hevc is None:
        output_hevc = input_path.with_suffix('.hevc')

    dovi_tool_exec = get_dovi_tool_path()

    try:
        # Extract HEVC bitstream from video file and pipe to dovi_tool
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
            '-'
        ]

        dovi_cmd: list[str] = [
            dovi_tool_exec,
            'remove',
            '-',
            '-o', str(output_hevc)
        ]

        # Create pipeline: ffmpeg | dovi_tool
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        dovi_process = subprocess.Popen(
            dovi_cmd,
            stdin=ffmpeg_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Close ffmpeg stdout in parent to allow SIGPIPE to be sent
        if ffmpeg_process.stdout:
            ffmpeg_process.stdout.close()

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(dovi_process, "Extracting HDR10 Base Layer:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for dovi_tool to complete
        _stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool Base Layer extraction failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not output_hevc.exists():
            raise RuntimeError("HADR10 Base Layer file was not created")

        print_debug(f"- HDR10 Base Layer extracted successfully: {str(output_hevc)}")
        return output_hevc

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract Base Layer: {e}")


def inject_rpu(input_path: Path, input_rpu: Path, output_hevc: Optional[Path] = None) -> Path:
    """Inject Dolby Vision RPU metadata into HEVC HDR10 Base Layer.

    Args:
        input_file: Path to input HEVC HDR10 Base Layer file
        input_rpu: Path to RPU file to inject
        output_hevc: Optional path for output HEVC file. If None, generates
                    filename based on input (input.hevc -> input_BL+RPU.hevc)

    Returns:
        Path to the HEVC file with injected RPU

    Raises:
        RuntimeError: If RPU injection fails
    """
    if output_hevc is None:
        output_hevc = input_path.with_name(f"{input_path.stem}_BL_RPU.hevc")

    dovi_tool_exec: str = get_dovi_tool_path()

    try:
        dovi_cmd: list[str] = [
            dovi_tool_exec,
            'inject-rpu',
            '-i', str(input_path),
            '--rpu-in', str(input_rpu),
            '-o', str(output_hevc)
        ]

        dovi_process = subprocess.Popen(
            dovi_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(dovi_process, "Injecting RPU metadata:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for dovi_tool to complete
        dovi_process.wait()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if not output_hevc.exists():
            raise RuntimeError("HEVC file with RPU was not created")

        print_debug(f"- RPU injected successfully: {str(output_hevc)}")
        return output_hevc

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure dovi_tool is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to inject RPU: {e}")


def extract_rpu(input_path: Path, output_rpu: Optional[Path] = None, dv_profile_source: Optional[DolbyVisionProfile] = None, dv_profile_encoding: Optional[DolbyVisionProfile] = None) -> Path:
    """Extract Dolby Vision RPU (Reference Processing Unit) metadata.

    Args:
        video: Video object with metadata
        output_rpu: Optional path for RPU output file. If None, generates
                   filename based on input (input.mkv -> input.rpu)

    Returns:
        Path to the extracted RPU file

    Raises:
        RuntimeError: If RPU extraction fails
    """
    if output_rpu is None:
        output_rpu = input_path.with_suffix('.rpu')

    dovi_tool_exec = get_dovi_tool_path()

    map_dv_profile8_mode: dict[int, str] = {
        5: '3',
        7: '2',
        8: '2',
    }

    try:
        # Extract HEVC bitstream from video file and pipe to dovi_tool
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
            '-'
        ]

        dovi_cmd: list[str] = [
            dovi_tool_exec,
        ]

        if dv_profile_source and dv_profile_encoding and dv_profile_source != dv_profile_encoding:
            if dv_profile_encoding == DolbyVisionProfile._8:
                if dv_profile_source.value in map_dv_profile8_mode:
                    dovi_cmd.extend(['-m', map_dv_profile8_mode[dv_profile_source.value]])

        dovi_cmd.extend([
            'extract-rpu',
            '-',
            '-o', str(output_rpu)
        ])

        # Create pipeline: ffmpeg | dovi_tool
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        dovi_process = subprocess.Popen(
            dovi_cmd,
            stdin=ffmpeg_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Close ffmpeg stdout in parent to allow SIGPIPE to be sent
        if ffmpeg_process.stdout:
            ffmpeg_process.stdout.close()

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(dovi_process, "Extracting RPU metadata:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for dovi_tool to complete
        _stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not output_rpu.exists():
            raise RuntimeError("RPU file was not created")

        print_debug(f"- RPU extracted successfully: {str(output_rpu)}")
        return output_rpu

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract RPU: {e}")


def inject_dolby_vision_layers(bl_path: Path, el_path: Path, output_bl_el: Optional[Path] = None) -> Path:
    """Multiplex Dolby Vision Base Layer and Enhancement Layer.

    Args:
        bl_path: Path to HEVC base layer file
        el_path: Path to Enhancement Layer (EL) file
        output_file: Optional path for output file. If None, generates
                    filename based on input (base.hevc -> base_BL_EL.hevc)

    Returns:
        Path to the multiplexed Dolby Vision HEVC file

    Raises:
        RuntimeError: If multiplexing fails
    """
    if output_bl_el is None:
        output_bl_el = bl_path.with_name(f"{bl_path.stem}_BL_EL.hevc")

    dovi_tool_exec = get_dovi_tool_path()

    try:
        dovi_cmd: list[str] = [
            dovi_tool_exec,
            'mux',
            '--bl', str(bl_path),
            '--el', str(el_path),
            '-o', str(output_bl_el)
        ]

        dovi_process = subprocess.Popen(
            dovi_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(dovi_process, "Multiplexing Dolby Vision layers:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for dovi_tool to complete
        _stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool muxing failed: {error_msg}")

        if not output_bl_el.exists():
            raise RuntimeError("Multiplexed file was not created")

        print_debug(f"- Dolby Vision layers multiplexed successfully: {str(output_bl_el)}")
        return output_bl_el

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure dovi_tool is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to multiplex Dolby Vision layers: {e}")


def extract_enhancement_layer(input_file: Path, output_el: Optional[Path] = None) -> Path:
    """Extract Dolby Vision Enhancement Layer (EL).

    Args:
        input_file: Path to input video file
        output_el: Optional path for EL output file. If None, generates
                   filename based on input (input.mkv -> input_EL.hevc)

    Returns:
        Path to the extracted Enhancement Layer file

    Raises:
        RuntimeError: If Enhancement Layer extraction fails
    """
    if output_el is None:
        output_el = input_file.with_name(f"{input_file.stem}_EL.hevc")

    dovi_tool_exec = get_dovi_tool_path()

    try:
        # Extract HEVC bitstream from video file and pipe to dovi_tool
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_file),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
            '-'
        ]

        dovi_cmd: list[str] = [
            dovi_tool_exec,
            'demux',
            '-',
            '--el-only',
            '--el-out', str(output_el)
        ]

        # Create pipeline: ffmpeg | dovi_tool
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        dovi_process = subprocess.Popen(
            dovi_cmd,
            stdin=ffmpeg_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Close ffmpeg stdout in parent to allow SIGPIPE to be sent
        if ffmpeg_process.stdout:
            ffmpeg_process.stdout.close()

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(dovi_process, "Extracting Enhancement Layer:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for dovi_tool to complete
        _stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool Enhancement Layer extraction failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not output_el.exists():
            raise RuntimeError("Enhancement Layer file was not created")

        print_debug(f"- Enhancement Layer extracted successfully: {str(output_el)}")
        return output_el

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract Enhancement Layer: {e}")

def _parse_rpu_info(output: str) -> DolbyVisionRpuInfo:
    """Parse dovi_tool info --summary output into RpuInfo dataclass.

    Args:
        output: The text output from dovi_tool info --summary command

    Returns:
        RpuInfo dataclass with parsed data

    Raises:
        ValueError: If required fields cannot be parsed
    """
    # Extract frames
    frames_match = re.search(r'Frames:\s+(\d+)', output)
    if not frames_match:
        raise ValueError("Could not parse frames from RPU info")
    frames = int(frames_match.group(1))

    # Extract profile and profile name (name is optional, e.g. Profile 8 has no name)
    profile_match = re.search(r'Profile:\s+(\d+)(?:\s+\(([^)]+)\))?', output)
    if not profile_match:
        raise ValueError("Could not parse profile from RPU info")
    profile = int(profile_match.group(1))
    profile_el = profile_match.group(2) if profile_match.group(2) else None

    # Extract DM version
    dm_version_match = re.search(r'DM version:\s+(\d+)\s+\(([^)]+)\)', output)
    if not dm_version_match:
        raise ValueError("Could not parse DM version from RPU info")
    dm_version = int(dm_version_match.group(1))
    cm_version = dm_version_match.group(2)

    # Extract scene/shot count
    scene_shot_match = re.search(r'Scene/shot count:\s+(\d+)', output)
    if not scene_shot_match:
        raise ValueError("Could not parse scene/shot count from RPU info")
    scene_shot_count = int(scene_shot_match.group(1))

    # Extract RPU mastering display
    rpu_display_match = re.search(r'RPU mastering display:\s+([\d.]+)/([\d.]+)\s+nits', output)
    if not rpu_display_match:
        raise ValueError("Could not parse RPU mastering display from RPU info")
    rpu_min_nits = float(rpu_display_match.group(1))
    rpu_max_nits = float(rpu_display_match.group(2))

    # Extract L1 content light level
    l1_match = re.search(r'RPU content light level \(L1\):\s+MaxCLL:\s+([\d.]+)\s+nits,\s+MaxFALL:\s+([\d.]+)\s+nits', output)
    if not l1_match:
        raise ValueError("Could not parse L1 content light level from RPU info")
    l1_max_cll = float(l1_match.group(1))
    l1_max_fall = float(l1_match.group(2))

    # Extract L6 metadata (optional)
    l6_min_nits = None
    l6_max_nits = None
    l6_max_cll = None
    l6_max_fall = None

    l6_match = re.search(r'L6 metadata:\s+Mastering display:\s+([\d.]+)/([\d.]+)\s+nits\.\s+MaxCLL:\s+(\d+)\s+nits,\s+MaxFALL:\s+(\d+)\s+nits', output)
    if l6_match:
        l6_min_nits = float(l6_match.group(1))
        l6_max_nits = float(l6_match.group(2))
        l6_max_cll = int(l6_match.group(3))
        l6_max_fall = int(l6_match.group(4))

    # Extract L5 offsets (optional, may be N/A)
    l5_offset_top = None
    l5_offset_bottom = None
    l5_offset_left = None
    l5_offset_right = None

    l5_match = re.search(r'L5 offsets:\s+top=([^,]+),\s+bottom=([^,]+),\s+left=([^,]+),\s+right=(.+)', output)
    if l5_match:
        try:
            top_str = l5_match.group(1).strip()
            bottom_str = l5_match.group(2).strip()
            left_str = l5_match.group(3).strip()
            right_str = l5_match.group(4).strip()

            l5_offset_top = None if top_str == "N/A" else int(top_str)
            l5_offset_bottom = None if bottom_str == "N/A" else int(bottom_str)
            l5_offset_left = None if left_str == "N/A" else int(left_str)
            l5_offset_right = None if right_str == "N/A" else int(right_str)
        except ValueError:
            # If parsing fails, leave as None
            pass

    return DolbyVisionRpuInfo(
        frames=frames,
        profile=profile,
        profile_el=profile_el,
        dm_version=dm_version,
        cm_version=cm_version,
        scene_shot_count=scene_shot_count,
        rpu_min_nits=rpu_min_nits,
        rpu_max_nits=rpu_max_nits,
        l1_max_cll=l1_max_cll,
        l1_max_fall=l1_max_fall,
        l6_min_nits=l6_min_nits,
        l6_max_nits=l6_max_nits,
        l6_max_cll=l6_max_cll,
        l6_max_fall=l6_max_fall,
        l5_offset_top=l5_offset_top,
        l5_offset_bottom=l5_offset_bottom,
        l5_offset_left=l5_offset_left,
        l5_offset_right=l5_offset_right
    )


def get_rpu_info(rpu_path: Path) -> DolbyVisionRpuInfo:
    """Get detailed information about a Dolby Vision RPU file.

    Args:
        rpu_file: Path to the RPU file (.bin or .rpu)

    Returns:
        RpuInfo dataclass with parsed information

    Raises:
        RuntimeError: If dovi_tool execution fails
        ValueError: If output parsing fails
    """
    if not rpu_path.exists():
        raise FileNotFoundError(f"RPU file not found: {str(rpu_path)}")

    dovi_tool_exec = get_dovi_tool_path()

    try:
        dovi_cmd: list[str] = [
            dovi_tool_exec,
            'info',
            '--input', str(rpu_path),
            '--summary'
        ]

        result = subprocess.run(
            dovi_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return _parse_rpu_info(result.stdout)

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise RuntimeError(f"dovi_tool info failed: {error_msg}")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure dovi_tool is installed."
        )
