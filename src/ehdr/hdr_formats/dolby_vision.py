"""Dolby Vision metadata extraction and handling."""

import subprocess
from pathlib import Path
from typing import Optional


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

    print(f"Extracting Dolby Vision base layer from {input_path.name}...")

    # Get path to local dovi_tool (in project root)
    project_root = Path(__file__).parent.parent.parent
    dovi_tool_path = project_root / "dovi_tool"

    # Fallback to system dovi_tool if local one doesn't exist
    if dovi_tool_path.exists():
        dovi_tool_cmd = str(dovi_tool_path)
    else:
        dovi_tool_cmd = "dovi_tool"

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
            dovi_tool_cmd,
            # '-m', '2',
            # 'convert',
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

        # Wait for dovi_tool to complete
        stdout, stderr = dovi_process.communicate()

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool base layer extraction failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not hevc_base_layer_path.exists():
            raise RuntimeError("HEVC BaseLayer file was not created")

        print(f"HEVC Base Layer extracted successfully: {hevc_base_layer_path}")
        return str(hevc_base_layer_path)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract base layer: {e}")

def inject_rpu(input_file: str, input_rpu: str, output_hevc: Optional[str] = None) -> str:
    """Inject Dolby Vision RPU metadata into HEVC base layer.

    Args:
        input_file: Path to input HEVC base layer file
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
        output_hevc = str(input_path.with_name(f"{input_path.stem}_BL+RPU.hevc"))

    hevc_bl_and_rpu_path = Path(output_hevc)

    print(f"Injecting Dolby Vision RPU metadata to {input_path.name}...")

    # Get path to local dovi_tool (in project root)
    project_root = Path(__file__).parent.parent.parent
    dovi_tool_path = project_root / "dovi_tool"

    # Fallback to system dovi_tool if local one doesn't exist
    if dovi_tool_path.exists():
        dovi_tool_exec = str(dovi_tool_path)
    else:
        dovi_tool_exec = "dovi_tool"

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

        # Wait for dovi_tool to complete
        dovi_process.wait()

        if not hevc_bl_and_rpu_path.exists():
            raise RuntimeError("HEVC file with RPU was not created")

        print(f"RPU injected successfully: {hevc_bl_and_rpu_path}")
        return str(hevc_bl_and_rpu_path)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure dovi_tool is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to inject RPU: {e}")

def extract_rpu(input_file: str, output_rpu: Optional[str] = None) -> str:
    """Extract Dolby Vision RPU (Reference Processing Unit) metadata.

    Args:
        input_file: Path to input video file
        output_rpu: Optional path for RPU output file. If None, generates
                   filename based on input (input.mkv -> input.rpu)

    Returns:
        Path to the extracted RPU file

    Raises:
        RuntimeError: If RPU extraction fails
    """
    input_path = Path(input_file)

    if output_rpu is None:
        output_rpu = str(input_path.with_suffix('.rpu'))

    rpu_path = Path(output_rpu)

    print(f"Extracting Dolby Vision RPU metadata from {input_path.name}...")

    # Get path to local dovi_tool (in project root)
    project_root = Path(__file__).parent.parent.parent
    dovi_tool_path = project_root / "dovi_tool"

    # Fallback to system dovi_tool if local one doesn't exist
    if dovi_tool_path.exists():
        dovi_tool_cmd = str(dovi_tool_path)
    else:
        dovi_tool_cmd = "dovi_tool"

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
            dovi_tool_cmd,
            '-m', '2',
            'extract-rpu',
            '-',
            '-o', str(rpu_path)
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

        # Wait for dovi_tool to complete
        stdout, stderr = dovi_process.communicate()

        if dovi_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"dovi_tool failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not rpu_path.exists():
            raise RuntimeError("RPU file was not created")

        print(f"RPU extracted successfully: {rpu_path}")
        return str(rpu_path)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and dovi_tool are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to extract RPU: {e}")


def build_dolby_vision_params(video, crf: int, preset: str) -> list:
    """Build x265 parameters for Dolby Vision encoding.

    Args:
        video: Video object with metadata
        crf: Constant Rate Factor for quality
        preset: Encoding preset

    Returns:
        List of x265 parameter strings
    """
    params = [
        f"crf={crf}",
        f"preset={preset}",
        "profile=main10",  # 10-bit profile required for Dolby Vision
        "level-idc=5.1",
        "high-tier=1",
        "hdr10=1",
        "repeat-headers=1",
        "colorprim=bt2020",
        "transfer=smpte2084",
        "colormatrix=bt2020nc",
        "vbv-bufsize=20000",
        "vbv-maxrate=20000",
    ]

    # Add master display metadata if available
    master_display = video.get_master_display()
    if master_display:
        params.append(f"master-display={master_display}")

    return params
