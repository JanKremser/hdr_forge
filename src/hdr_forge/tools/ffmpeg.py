"""ffmpeg/ffprobe utilities — treats ffmpeg as an external system tool."""

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Tuple

from hdr_forge.cli.cli_output import (
    ProgressBarSpinner,
    create_ffmpeg_minimal_progress_handler,
    monitor_process_progress,
    print_debug,
)
from hdr_forge.core.service import build_cmd_array_to_str, build_cmd_pipe_str
from hdr_forge.typedefs.codec_typing import VideoEncoderLibrary
from hdr_forge.typedefs.ffmpeg_typing import FfmpegMiniProgressInfo
from hdr_forge.typedefs.video_typing import (
    ContentLightLevelMetadata,
    HdrMetadata,
    MasterDisplayMetadata,
)


def clean_subprocess_env() -> dict:
    """Return a copy of the current environment with LD_LIBRARY_PATH removed.

    Required when running as a PyInstaller bundle: OpenCV bundles its own
    libglib-2.0.so.0 and sets LD_LIBRARY_PATH to its temp dir, which causes
    symbol lookup errors in the system ffmpeg.

    Returns:
        dict: A copy of os.environ with LD_LIBRARY_PATH removed
    """
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    return env


def probe_video_metadata(filepath: Path) -> dict:
    """Extract video metadata using ffprobe.

    Args:
        filepath: Path to the video file

    Returns:
        Dictionary containing all stream and format metadata

    Raises:
        RuntimeError: If ffprobe command fails or output cannot be parsed
    """
    try:
        result = subprocess.run(
            args=[
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(filepath)
            ],
            capture_output=True,
            text=True,
            check=True,
            env=clean_subprocess_env(),
        )
        return json.loads(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffprobe failed:\nSTDERR:\n{e.stderr}\nSTDOUT:\n{e.stdout}"
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ffprobe output: {e}")


def extract_hdr_metadata_from_frames(filepath: Path) -> HdrMetadata:
    """Extract HDR mastering display and content light level metadata from video frames.

    Runs ffmpeg with the showinfo filter on the first 10 frames and parses the
    mastering display and content light level metadata from stderr. Terminates
    early once both values are found.

    Args:
        filepath: Path to the video file

    Returns:
        HdrMetadata with mastering display and content light level metadata
    """
    cmd: list = [
        "ffmpeg", "-hide_banner",
        "-i", str(filepath),
        "-vf", "showinfo",
        "-frames:v", "10",
        "-f", "null", "-",
    ]

    process = subprocess.Popen(
        args=cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        env=clean_subprocess_env(),
    )

    mastering_data: MasterDisplayMetadata | None = None
    light_data: ContentLightLevelMetadata | None = None

    mastering_re: re.Pattern[str] = re.compile(
        r"(?:Mastering display metadata|side data - mastering display).*?"
        r"r\((?P<r_x>[\d\.]+)[\s,]+(?P<r_y>[\d\.]+)\)\s*"
        r"g\((?P<g_x>[\d\.]+)[\s,]+(?P<g_y>[\d\.]+)\)\s*"
        r"b\((?P<b_x>[\d\.]+)[\s,]+(?P<b_y>[\d\.]+)\)\s*"
        r"wp\((?P<wp_x>[\d\.]+)[\s,]+(?P<wp_y>[\d\.]+)\)\s*"
        r"min_luminance=(?P<min_lum>[\d\.]+)[\s,]*max_luminance=(?P<max_lum>[\d\.]+)"
    )
    light_re: re.Pattern[str] = re.compile(
        r"(?:Content light level metadata|side data - Content Light Level information).*?"
        r"MaxCLL=(?P<maxcll>\d+),\s*MaxFALL=(?P<maxfall>\d+)"
    )

    if process.stderr:
        for line in process.stderr.readlines():
            if not mastering_data:
                m = mastering_re.search(line)
                if m:
                    mastering_data = MasterDisplayMetadata(**{k: float(v) for k, v in m.groupdict().items()})
            if not light_data:
                l = light_re.search(line)
                if l:
                    light_data = ContentLightLevelMetadata(**{k: int(v) for k, v in l.groupdict().items()})
            if mastering_data and light_data:
                process.kill()
                break

    process.wait()

    if light_data:
        if light_data.maxcll == 0:
            light_data.maxcll = None
        if light_data.maxfall == 0:
            light_data.maxfall = None

    return HdrMetadata(
        mastering_display_metadata=mastering_data,
        content_light_level_metadata=light_data,
    )


def query_available_hw_encoders() -> list[VideoEncoderLibrary]:
    """Query ffmpeg for available hardware-accelerated encoders.

    Returns:
        List of VideoEncoderLibrary enum members available on the system

    Raises:
        RuntimeError: If ffmpeg cannot be executed
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=True,
            env=clean_subprocess_env()
        )

        available_hw_encoders = set()
        for line in result.stdout.splitlines():
            if line.startswith(" V"):
                parts = line.split()
                if len(parts) > 1:
                    encoder_name = parts[1]
                    if any(hw in encoder_name for hw in ["nvenc", "qsv", "vaapi", "amf", "v4l2"]):
                        available_hw_encoders.add(encoder_name)

        return [
            member
            for member in VideoEncoderLibrary
            if member.value in available_hw_encoders
        ]
    except subprocess.CalledProcessError as e:
        print("Error querying encoders:", e)
        return []
    except FileNotFoundError:
        print("ffmpeg not found")
        return []


def detect_crop_at_position(
    filepath: Path,
    position_seconds: int,
    is_hdr: bool,
) -> Optional[Tuple[int, int, int, int]]:
    """Detect crop parameters at a specific position in the video.

    Args:
        filepath: Path to the video file
        position_seconds: Position in seconds to analyze
        is_hdr: Whether the video is HDR (applies tone mapping before cropdetect)

    Returns:
        Tuple of (width, height, x, y) or None if detection failed
    """
    hdr_cropdetect_filter: str = ""
    if is_hdr:
        hdr_cropdetect_filter = "zscale=transfer=bt709,format=yuv420p,hqdn3d=1.5:1.5:6:6,"

    cmd: list[str] = [
        'ffmpeg',
        '-ss', str(position_seconds),
        '-i', str(filepath),
        '-vf', f'{hdr_cropdetect_filter}cropdetect=24:16:0',
        '-frames:v', '30',
        '-f', 'null',
        '-'
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, env=clean_subprocess_env()
        )
        crop_pattern = re.compile(r'crop=(\d+):(\d+):(\d+):(\d+)')
        for line in result.stderr.split('\n'):
            match = crop_pattern.search(line)
            if match:
                w, h, x, y = map(int, match.groups())
                return (w, h, x, y)
    except (subprocess.TimeoutExpired, Exception):
        pass

    return None


def _parse_ffmpeg_progress_line(line: str, progress_data: dict) -> None:
    """Parse a single line from FFmpeg progress output (key=value format)."""
    if '=' not in line:
        return

    key, _, value = line.partition('=')
    key = key.strip()
    value = value.strip()

    if key == 'frame':
        try:
            progress_data['frame'] = int(value)
        except ValueError:
            pass
    elif key == 'fps':
        try:
            progress_data['fps'] = float(value)
        except ValueError:
            pass
    elif key == 'progress':
        progress_data['progress'] = value


def _create_ffmpeg_progress_info(progress_data: dict, total_frames: int) -> FfmpegMiniProgressInfo:
    """Create a FfmpegMiniProgressInfo object from parsed FFmpeg progress data."""
    return FfmpegMiniProgressInfo(
        frame=progress_data.get('frame', 0),
        fps=progress_data.get('fps', 0.0),
        total_frames=total_frames
    )


def _ffmpeg_progress_reader_thread(
    pipe,
    tool_process: subprocess.Popen,
    progress_callback: Optional[Callable[[FfmpegMiniProgressInfo], None]],
    total_frames: int,
    stderr_buffer: list
) -> None:
    """Thread function to read and parse FFmpeg progress output."""
    progress_data = {}

    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break

            line = line.strip()
            stderr_buffer.append(line)

            _parse_ffmpeg_progress_line(line, progress_data)

            if line.startswith('progress='):
                if progress_data and progress_callback:
                    progress_info: FfmpegMiniProgressInfo = _create_ffmpeg_progress_info(progress_data, total_frames)
                    progress_callback(progress_info)

                if line == 'progress=end':
                    break
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass

    if not tool_process:
        return

    spinner = ProgressBarSpinner(
        description=None,
        without_headline=True
    )
    spinner.start()

    while tool_process.poll() is None:
        spinner.update(2)
        time.sleep(0.1)

    spinner.stop("100.0%")


def extract_hevc(
    input_path: Path,
    output_hevc: Optional[Path] = None,
    total_frames: Optional[int] = None,
) -> Path:
    """Extract HEVC bitstream from video file.

    Args:
        input_path: Path to input video file
        output_hevc: Path to output HEVC file. If None, generates filename based on input
        total_frames: Total number of frames in the video (for progress tracking)

    Returns:
        Path to the extracted HEVC file

    Raises:
        RuntimeError: If extraction fails
    """
    if output_hevc is None:
        output_hevc = input_path.with_name(f"{input_path.stem}_BL.hevc")

    try:
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
        ]

        if total_frames:
            ffmpeg_cmd.extend(['-progress', 'pipe:2'])

        ffmpeg_cmd.append(str(output_hevc))

        print_debug(build_cmd_array_to_str(ffmpeg_cmd))

        ffmpeg_stderr = subprocess.PIPE if total_frames else subprocess.DEVNULL

        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=ffmpeg_stderr,
            text=True if ffmpeg_stderr == subprocess.PIPE else False,
            bufsize=1 if ffmpeg_stderr == subprocess.PIPE else -1,
            env=clean_subprocess_env()
        )

        if total_frames and ffmpeg_process.stderr:
            process_start_time = time.time()
            progress_callback = create_ffmpeg_minimal_progress_handler(
                total_frames=total_frames,
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
            monitor_thread = threading.Thread(
                target=monitor_process_progress,
                args=(ffmpeg_process, "Extracting HEVC:"),
                daemon=True
            )
            monitor_thread.start()

        ffmpeg_process.wait()

        if total_frames:
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


def run_ffmpeg_tool_pipeline(
    input_path: Path,
    tool_cmd: list[str],
    process_name: str,
    total_frames: Optional[int] = None,
) -> tuple[int, bytes]:
    """Execute FFmpeg→Tool pipeline with optional progress tracking.

    Pipes ffmpeg HEVC extraction directly into an external tool (dovi_tool,
    hevc_hdr_editor, etc.) without writing an intermediate file.

    Args:
        input_path: Input video file path
        tool_cmd: Complete tool command list (starting with tool executable)
        process_name: Display name for progress tracking
        total_frames: Total number of frames for progress tracking (optional)

    Returns:
        Tuple of (returncode, stderr_bytes) from tool process

    Raises:
        RuntimeError: If ffmpeg or the tool are not found
    """
    ffmpeg_cmd: list[str] = [
        'ffmpeg',
        '-i', str(input_path),
        '-c:v', 'copy',
        '-bsf:v', 'hevc_mp4toannexb',
        '-f', 'hevc',
    ]

    if total_frames:
        ffmpeg_cmd.extend(['-progress', 'pipe:2'])

    ffmpeg_cmd.append('-')

    print_debug(build_cmd_pipe_str([ffmpeg_cmd, tool_cmd]))

    ffmpeg_stderr = subprocess.PIPE if total_frames else subprocess.DEVNULL

    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=ffmpeg_stderr,
        text=True if ffmpeg_stderr == subprocess.PIPE else False,
        bufsize=1 if ffmpeg_stderr == subprocess.PIPE else -1,
        env=clean_subprocess_env()
    )

    tool_process = subprocess.Popen(
        tool_cmd,
        stdin=ffmpeg_process.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_subprocess_env()
    )

    if ffmpeg_process.stdout:
        ffmpeg_process.stdout.close()

    if total_frames and ffmpeg_process.stderr:
        process_start_time = time.time()
        progress_callback = create_ffmpeg_minimal_progress_handler(
            total_frames=total_frames,
            process_start_time=process_start_time,
            process_name=process_name
        )
        stderr_buffer: list = []
        reader_thread = threading.Thread(
            target=_ffmpeg_progress_reader_thread,
            args=(ffmpeg_process.stderr, tool_process, progress_callback, total_frames, stderr_buffer),
            daemon=True
        )
        reader_thread.start()
    else:
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(tool_process, process_name),
            daemon=True
        )
        monitor_thread.start()

    _stdout, stderr = tool_process.communicate()

    if total_frames and ffmpeg_process.stderr:
        reader_thread.join(timeout=1.0)
    else:
        monitor_thread.join(timeout=1.0)

    ffmpeg_process.wait()

    return tool_process.returncode, stderr
