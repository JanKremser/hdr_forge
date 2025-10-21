"""Dolby Vision metadata extraction and handling."""

import subprocess
import threading
from pathlib import Path
from typing import Optional

from ehdr.cli.cli_output import monitor_process_progress
from ehdr.dataclass import DolbyVisionProfile
from ehdr.video import Video


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


def extract_base_layer(input_file: str, output_hevc: Optional[str] = None) -> str:
    """Extract Dolby Vision base layer (HEVC without RPU).

    Args:
        input_file: Path to input video file
        output_hevc: Optional path for HEVC output file. If None, generates
                    filename based on input (input.mkv -> input.hevc)

    Returns:
        Path to the extracted base layer HEVC file

    Raises:
        RuntimeError: If base layer extraction fails
    """
    input_path = Path(input_file)

    if output_hevc is None:
        output_hevc = str(input_path.with_suffix('.hevc'))

    hevc_base_layer_path = Path(output_hevc)

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
            '-o', str(hevc_base_layer_path)
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
        stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool Base Layer extraction failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not hevc_base_layer_path.exists():
            raise RuntimeError("HADR10 Base Layer file was not created")

        print(f"- HDR10 Base Layer extracted successfully: {hevc_base_layer_path}")
        return str(hevc_base_layer_path)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract Base Layer: {e}")


def inject_rpu(input_file: str, input_rpu: str, output_hevc: Optional[str] = None) -> str:
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
    input_path = Path(input_file)

    if output_hevc is None:
        output_hevc = str(input_path.with_name(f"{input_path.stem}_BL_RPU.hevc"))

    hevc_bl_and_rpu_path = Path(output_hevc)

    dovi_tool_exec = get_dovi_tool_path()

    try:
        dovi_cmd: list[str] = [
            dovi_tool_exec,
            'inject-rpu',
            '-i', input_file,
            '--rpu-in', input_rpu,
            '-o', str(hevc_bl_and_rpu_path)
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

        if not hevc_bl_and_rpu_path.exists():
            raise RuntimeError("HEVC file with RPU was not created")

        print(f"- RPU injected successfully: {hevc_bl_and_rpu_path}")
        return str(hevc_bl_and_rpu_path)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure dovi_tool is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to inject RPU: {e}")


def extract_rpu(video: Video, output_rpu: Optional[str] = None, dv_profile_encoding: Optional[DolbyVisionProfile] = None) -> str:
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
    input_path = video.get_filepath()

    if output_rpu is None:
        output_rpu = str(input_path.with_suffix('.rpu'))

    rpu_path = Path(output_rpu)

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

        if dv_profile_encoding and dv_profile_encoding != DolbyVisionProfile.AUTO:
            profile: int | None = video.get_dolby_vision_profile()
            if profile and profile in map_dv_profile8_mode:
                dovi_cmd.extend(['-m', map_dv_profile8_mode[profile]])

        dovi_cmd.extend([
            'extract-rpu',
            '-',
            '-o', str(rpu_path)
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
        stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not rpu_path.exists():
            raise RuntimeError("RPU file was not created")

        print(f"- RPU extracted successfully: {rpu_path}")
        return str(rpu_path)

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
        stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool muxing failed: {error_msg}")

        if not output_bl_el.exists():
            raise RuntimeError("Multiplexed file was not created")

        print(f"- Dolby Vision layers multiplexed successfully: {str(output_bl_el)}")
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
        stdout, stderr = dovi_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool Enhancement Layer extraction failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not output_el.exists():
            raise RuntimeError("Enhancement Layer file was not created")

        print(f"- Enhancement Layer extracted successfully: {str(output_el)}")
        return output_el

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract Enhancement Layer: {e}")


# def build_dolby_vision_params(video, crf: int, preset: str) -> list:
#     """Build x265 parameters for Dolby Vision encoding.

#     Args:
#         video: Video object with metadata
#         crf: Constant Rate Factor for quality
#         preset: Encoding preset

#     Returns:
#         List of x265 parameter strings
#     """
#     params = [
#         f"crf={crf}",
#         f"preset={preset}",
#         "profile=main10",  # 10-bit profile required for Dolby Vision
#         "level-idc=5.1",
#         "high-tier=1",
#         "hdr10=1",
#         "repeat-headers=1",
#         "colorprim=bt2020",
#         "transfer=smpte2084",
#         "colormatrix=bt2020nc",
#         "vbv-bufsize=20000",
#         "vbv-maxrate=20000",
#     ]
#         video: Video object with metadata
#         crf: Constant Rate Factor for quality
#         preset: Encoding preset
#     Returns:master_display()
#         List of x265 parameter strings#     if master_display:
#     """ms.append(f"master-display={master_display}")
#     params = [
#         f"crf={crf}",urn params
#         f"preset={preset}",#         "profile=main10",  # 10-bit profile required for Dolby Vision#         "level-idc=5.1",#         "high-tier=1",#         "hdr10=1",#         "repeat-headers=1",#         "colorprim=bt2020",#         "transfer=smpte2084",#         "colormatrix=bt2020nc",#         "vbv-bufsize=20000",#         "vbv-maxrate=20000",#     ]#     # Add master display metadata if available#     master_display = video.get_master_display()#     if master_display:#         params.append(f"master-display={master_display}")#     return params
