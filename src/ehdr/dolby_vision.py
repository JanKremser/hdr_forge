"""Dolby Vision metadata extraction and handling."""

import subprocess
from pathlib import Path
from typing import Optional


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

    # Check if RPU file already exists (cached)
    if rpu_path.exists():
        print(f"Using cached RPU file: {rpu_path}")
        return str(rpu_path)

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
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
            '-'
        ]

        dovi_cmd = [
            dovi_tool_cmd,
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
