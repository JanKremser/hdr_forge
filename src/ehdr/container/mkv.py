import subprocess
import threading
from pathlib import Path
from typing import Optional

from ehdr.cli.cli_output import monitor_process_progress


def extract_hevc(input_mkv: str, output_hevc: Optional[Path] = None) -> Path:
    input_mkv_path = Path(input_mkv)

    if output_hevc is None:
        output_hevc = input_mkv_path.with_name(f"{input_mkv_path.stem}_BL.hevc")

    try:
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_mkv_path),
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


def mux_hevc_to_mkv(input_hevc: str, input_mkv: Optional[str] = None, output_mkv: Optional[str] = None) -> str:
    input_hevc_path = Path(input_hevc)

    if output_mkv is None:
        output_mkv = str(input_hevc_path.with_name(f"{input_hevc_path.stem}_BL.mkv"))

    mkv_output_path = Path(output_mkv)

    project_root = Path(__file__).parent.parent.parent
    mkvmerge_path = project_root / "mkvmerge"

    if mkvmerge_path.exists():
        mkvmerge_exec = str(mkvmerge_path)
    else:
        mkvmerge_exec = "mkvmerge"

    try:
        mkvmerge_cmd: list[str] = [
            mkvmerge_exec,
            '-o', str(mkv_output_path),
        ]

        if input_mkv is not None:
            mkvmerge_cmd.extend([
                '--no-video', input_mkv,
            ])

        mkvmerge_cmd.extend([
            input_hevc,
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

        if not mkv_output_path.exists():
            raise RuntimeError("MKV file was not created")

        print(f"- HEVC muxed to MKV successfully: {mkv_output_path}")
        return str(mkv_output_path)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure mkvmerge is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to mux HEVC to MKV: {e}")
