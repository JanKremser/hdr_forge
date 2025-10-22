"""
HDR10 MaxCLL/MaxFALL analyzer using parallel video segment processing.

This module provides functions to calculate Maximum Content Light Level (MaxCLL)
and Maximum Frame-Average Light Level (MaxFALL) from HDR10 video files using
parallel processing with hardware acceleration support.
"""

import subprocess
import math
import time
from typing import Tuple, List, Dict, Any
from multiprocessing import Pool, cpu_count, Manager
from multiprocessing.managers import SyncManager

import numpy as np

from ehdr.cli.cli_output import create_progress_bar

# Constants
SEGMENT_DURATION = 30  # Duration per segment in seconds (adjustable)
RGB48LE_BYTES_PER_PIXEL = 6  # 3 channels * 2 bytes (16-bit per channel)

# ITU-R BT.2100 PQ EOTF (ST.2084) constants
PQ_M1 = 2610 / 16384
PQ_M2 = 2523 / 32
PQ_C1 = 3424 / 4096
PQ_C2 = 2413 / 128
PQ_C3 = 2392 / 128
PQ_NITS_SCALE = 10000

# BT.2020 luminance coefficients
LUMA_RED = 0.2627
LUMA_GREEN = 0.6780
LUMA_BLUE = 0.0593


def pq_to_nits(pq: np.ndarray) -> np.ndarray:
    """
    Convert PQ (Perceptual Quantizer) values to nits using ITU-R BT.2100 EOTF.

    Args:
        pq: Normalized PQ values (0.0-1.0)

    Returns:
        Luminance values in nits (cd/m²)
    """
    pq_inv = np.maximum(pq ** (1 / PQ_M2) - PQ_C1, 0)
    denominator = PQ_C2 - PQ_C3 * pq ** (1 / PQ_M2)
    luminance = (pq_inv / denominator) ** (1 / PQ_M1)
    return luminance * PQ_NITS_SCALE


def _get_video_stream_info(video_path: str) -> Tuple[int, int, float]:
    """
    Extract video stream information using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (width, height, fps)
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "csv=p=0:s=x", video_path
    ]
    output = subprocess.check_output(cmd).decode().strip()
    width, height, fps_str = output.split("x")
    return int(width), int(height), eval(fps_str)


def _get_video_duration(video_path: str) -> float:
    """
    Extract video duration using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    return float(subprocess.check_output(cmd).decode().strip())


def get_video_info(video_path: str) -> Tuple[int, int, float, float]:
    """
    Get complete video information including dimensions, framerate and duration.

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (width, height, fps, duration)
    """
    width, height, fps = _get_video_stream_info(video_path)
    duration = _get_video_duration(video_path)
    return width, height, fps, duration


def detect_gpu_acceleration() -> str:
    """
    Detect available hardware acceleration method.

    Returns:
        Hardware acceleration type: "cuda", "qsv", or "cpu"
    """
    try:
        result = subprocess.check_output(
            ["ffmpeg", "-hwaccels"],
            stderr=subprocess.DEVNULL
        ).decode()
        if "cuda" in result:
            return "cuda"
        elif "qsv" in result:
            return "qsv"
    except Exception:
        pass
    return "cpu"


def build_ffmpeg_cmd(
    video_path: str,
    start: float,
    duration: float,
    hw_accel: str
) -> List[str]:
    """
    Build ffmpeg command for frame extraction with optional hardware acceleration.

    Args:
        video_path: Path to video file
        start: Start time in seconds
        duration: Duration to extract in seconds
        hw_accel: Hardware acceleration type ("cpu", "cuda", or "qsv")

    Returns:
        ffmpeg command as list of strings
    """
    base_args = [
        "-ss", str(start),
        "-t", str(duration),
        "-i", video_path,
        "-f", "rawvideo",
        "-pix_fmt", "rgb48le",
        "-"
    ]

    if hw_accel == "cuda":
        # Note: No hwaccel_output_format cuda to ensure rgb48le arrives in CPU space
        return ["ffmpeg", "-hwaccel", "cuda"] + base_args
    elif hw_accel == "qsv":
        return ["ffmpeg", "-hwaccel", "qsv", "-c:v", "h264_qsv"] + base_args
    else:
        return ["ffmpeg"] + base_args


def _calculate_luminance(rgb_frame: np.ndarray) -> np.ndarray:
    """
    Calculate luminance from RGB frame using BT.2020 coefficients.

    Args:
        rgb_frame: RGB frame with normalized values (0.0-1.0)

    Returns:
        Luminance values
    """
    return (
        LUMA_RED * rgb_frame[..., 0] +
        LUMA_GREEN * rgb_frame[..., 1] +
        LUMA_BLUE * rgb_frame[..., 2]
    )


def _process_raw_frame(
    raw_data: bytes,
    width: int,
    height: int
) -> Tuple[float, float]:
    """
    Process a single raw frame to extract MaxCLL and MaxFALL values.

    Args:
        raw_data: Raw frame data in rgb48le format
        width: Frame width
        height: Frame height

    Returns:
        Tuple of (max_cll, max_fall) for this frame
    """
    # Convert raw bytes to numpy array (16-bit RGB)
    frame = np.frombuffer(raw_data, np.uint16).reshape((height, width, 3))
    rgb_normalized = frame.astype(np.float32) / 65535.0

    # Calculate luminance and convert to nits
    luminance = _calculate_luminance(rgb_normalized)
    nits = pq_to_nits(luminance)

    # Return max pixel value (CLL) and average (FALL)
    return float(np.max(nits)), float(np.mean(nits))


def process_segment(
    video_path: str,
    start: float,
    duration: float,
    width: int,
    height: int,
    frame_sample_rate: int,
    hw_accel: str,
    progress_dict: Dict,
    segment_id: int
) -> Tuple[float, float]:
    """
    Process a single video segment to calculate MaxCLL and MaxFALL.

    Args:
        video_path: Path to video file
        start: Segment start time in seconds
        duration: Segment duration in seconds
        width: Video width
        height: Video height
        frame_sample_rate: Process every Nth frame
        hw_accel: Hardware acceleration type
        progress_dict: Shared dictionary for progress tracking
        segment_id: Unique segment identifier

    Returns:
        Tuple of (max_cll, max_fall) for this segment
    """
    ffmpeg_cmd = build_ffmpeg_cmd(video_path, start, duration, hw_accel)
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    frame_size = width * height * RGB48LE_BYTES_PER_PIXEL
    total_read_frames = 0
    processed_frames = 0
    max_cll = 0.0
    max_fall = 0.0

    while True:
        if process.stdout is None:
            break

        raw = process.stdout.read(frame_size)
        if len(raw) < frame_size:
            break

        total_read_frames += 1

        # Frame sampling: only process every Nth frame
        if (total_read_frames - 1) % frame_sample_rate != 0:
            continue

        processed_frames += 1
        frame_cll, frame_fall = _process_raw_frame(raw, width, height)

        max_cll = max(max_cll, frame_cll)
        max_fall = max(max_fall, frame_fall)

        # Update progress (only for processed frames)
        progress_dict[segment_id] = processed_frames

    process.wait()
    return max_cll, max_fall


def _create_video_segments(
    video_path: str,
    duration: float,
    width: int,
    height: int,
    fps: float,
    frame_sample_rate: int,
    hw_accel: str
) -> List[Tuple]:
    """
    Split video into time-based segments for parallel processing.

    Args:
        video_path: Path to video file
        duration: Total video duration in seconds
        width: Video width
        height: Video height
        fps: Video framerate
        frame_sample_rate: Process every Nth frame
        hw_accel: Hardware acceleration type

    Returns:
        List of segment tuples with processing parameters
    """
    segments = []
    start = 0.0
    segment_id = 0

    while start < duration:
        segment_duration = min(SEGMENT_DURATION, duration - start)
        segments.append((
            video_path,
            start,
            segment_duration,
            width,
            height,
            frame_sample_rate,
            hw_accel,
            segment_id,
            fps
        ))
        start += SEGMENT_DURATION
        segment_id += 1

    return segments


def _calculate_total_frames(
    segments: List[Tuple],
    frame_sample_rate: int
) -> int:
    """
    Calculate total number of frames that will be processed.

    Args:
        segments: List of video segments
        frame_sample_rate: Process every Nth frame

    Returns:
        Total estimated frame count after sampling
    """
    total = 0
    for segment in segments:
        seg_duration = segment[2]  # Duration is at index 2
        seg_fps = segment[8]  # FPS is at index 8
        frames_in_segment = int(math.ceil(seg_duration * seg_fps))
        sampled_frames = (frames_in_segment + frame_sample_rate - 1) // frame_sample_rate
        total += sampled_frames
    return total


def _initialize_progress_dict(
    manager: SyncManager,
    segments: List[Tuple]
) -> Any:
    """
    Initialize shared progress dictionary for all segments.

    Args:
        manager: Multiprocessing manager
        segments: List of video segments

    Returns:
        Initialized progress dictionary
    """
    progress_dict = manager.dict()
    for segment in segments:
        segment_id = segment[7]  # Segment ID is at index 7
        progress_dict[segment_id] = 0
    return progress_dict


def _format_eta(seconds: float) -> str:
    """
    Format ETA seconds into HH:MM:SS string.

    Args:
        seconds: Remaining seconds

    Returns:
        Formatted time string
    """
    return time.strftime("%H:%M:%S", time.gmtime(seconds))


def _monitor_progress(
    results_async,
    progress_dict: Dict,
    num_segments: int,
    total_frames: int,
    start_time: float
) -> None:
    """
    Monitor and display progress of parallel segment processing.

    Args:
        results_async: Async result object from pool.starmap_async
        progress_dict: Shared progress dictionary
        num_segments: Total number of segments
        total_frames: Total estimated frames to process
        start_time: Processing start time
    """
    try:
        while not results_async.ready():
            frames_done = sum(
                progress_dict.get(i, 0) for i in range(num_segments)
            )
            elapsed = time.time() - start_time

            if frames_done > 0:
                est_total_time = elapsed / frames_done * total_frames
                remaining = est_total_time - elapsed
                eta = _format_eta(remaining)
            else:
                eta = "--:--:--"

            percent = min(
                (frames_done / total_frames * 100) if total_frames > 0 else 100,
                100.0
            )
            bar = create_progress_bar(percent=percent, width=40)
            print(
                f"{bar} {percent:.2f}% | ETA: {eta} | "
                f"{frames_done}/{total_frames} Frames",
                end='\r'
            )
            time.sleep(0.5)
    except KeyboardInterrupt:
        raise


def _display_final_progress(
    progress_dict: Dict,
    num_segments: int,
    total_frames: int
) -> None:
    """
    Display final 100% progress bar.

    Args:
        progress_dict: Shared progress dictionary
        num_segments: Total number of segments
        total_frames: Total estimated frames
    """
    frames_done = sum(progress_dict.get(i, 0) for i in range(num_segments))
    percent = min(
        (frames_done / total_frames * 100) if total_frames > 0 else 100,
        100.0
    )
    bar = create_progress_bar(percent=percent, width=40)
    print(
        f"{bar} {percent:.2f}% | ETA: 00:00:00 | "
        f"{frames_done}/{total_frames} Frames",
        end='\r'
    )


def _aggregate_results(results: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Aggregate MaxCLL and MaxFALL results from all segments.

    Args:
        results: List of (max_cll, max_fall) tuples from each segment

    Returns:
        Tuple of overall (max_cll, max_fall) rounded to 2 decimals
    """
    if not results:
        return 0.0, 0.0

    max_cll = max(result[0] for result in results)
    max_fall = max(result[1] for result in results)

    return round(max_cll, 2), round(max_fall, 2)


def calculate_maxcll_maxfall_parallel(
    video_path: str,
    frame_sample_rate: int = 10
) -> Tuple[float, float]:
    """
    Calculate MaxCLL and MaxFALL using parallel segment processing.

    This function splits the video into time-based segments and processes them
    in parallel using multiple CPU cores. Each segment is analyzed to find the
    maximum and average luminance values.

    Args:
        video_path: Path to video file
        frame_sample_rate: Process every Nth frame (default: 10)

    Returns:
        Tuple of (max_cll, max_fall) in nits, rounded to 2 decimals

    Raises:
        KeyboardInterrupt: If user cancels the operation
    """
    # Get video information
    width, height, fps, duration = get_video_info(video_path)
    hw_accel = detect_gpu_acceleration()

    print(
        f"Analyzing {video_path} "
        f"({width}x{height}, {fps:.2f} fps, {duration:.2f}s) "
        f"with {hw_accel}"
    )

    # Create processing segments
    segments = _create_video_segments(
        video_path, duration, width, height, fps, frame_sample_rate, hw_accel
    )

    # Initialize progress tracking
    manager = Manager()
    progress_dict = _initialize_progress_dict(manager, segments)
    total_frames = _calculate_total_frames(segments, frame_sample_rate)

    # Prepare multiprocessing pool
    pool_args = [
        (seg[0], seg[1], seg[2], seg[3], seg[4], seg[5], seg[6], progress_dict, seg[7])
        for seg in segments
    ]
    num_processes = min(cpu_count(), len(segments))
    pool = Pool(processes=num_processes)

    # Start async processing
    results_async = pool.starmap_async(process_segment, pool_args)

    # Monitor progress
    start_time = time.time()
    try:
        _monitor_progress(
            results_async,
            progress_dict,
            len(segments),
            total_frames,
            start_time
        )
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
        raise

    # Collect results
    results = results_async.get()
    pool.close()
    pool.join()

    # Display final progress
    _display_final_progress(progress_dict, len(segments), total_frames)

    # Aggregate and return results
    return _aggregate_results(results)


def calc_maxcll(video_path: str) -> None:
    """
    Calculate and print MaxCLL/MaxFALL values for a video file.

    This is a convenience function that calculates the values and prints
    them to stdout.

    Args:
        video_path: Path to video file
    """
    maxcll, maxfall = calculate_maxcll_maxfall_parallel(
        video_path=video_path,
        frame_sample_rate=24
    )
    print(f"\nResult:")
    print(f"  MaxCLL : {maxcll:.2f} nits")
    print(f"  MaxFALL: {maxfall:.2f} nits")
