"""Video encoding parameter building and configuration."""

from pathlib import Path
from typing import Dict, List, Optional

from .video import Video

# Constants
HDR_X265_PARAMS = [
    'hdr-opt=1',
    'repeat-headers=1',
    'colorprim=bt2020',
    'transfer=smpte2084',
    'colormatrix=bt2020nc',
]
HDR_PIXEL_FORMAT = 'yuv420p10le'


def determine_encoding_params(
    video: Video,
    crf: Optional[int],
    preset: Optional[str]
) -> tuple[int, str]:
    """Determine CRF and preset values (auto-calculate if not provided).

    Args:
        video: Video object with metadata
        crf: User-specified CRF or None for auto
        preset: User-specified preset or None for auto

    Returns:
        Tuple of (crf, preset)
    """
    if crf is None:
        crf = video.get_auto_crf()
        print(f"Auto CRF: {crf}")

    if preset is None:
        preset = video.get_auto_preset()
        print(f"Auto preset: {preset}")

    return crf, preset


def build_hdr_x265_params(video: Video) -> List[str]:
    """Build x265 parameters for HDR video encoding.

    Args:
        video: Video object with HDR metadata

    Returns:
        List of x265 parameter strings
    """
    params = HDR_X265_PARAMS.copy()

    master_display = video.get_master_display()
    if master_display:
        params.append(f'master-display={master_display}')

    return params


def build_ffmpeg_output_options(
    video: Video,
    crf: int,
    preset: str,
    crop_filter: Optional[str] = None
) -> Dict[str, str]:
    """Build FFmpeg output options dictionary for encoding.

    Args:
        video: Video object with metadata
        crf: Constant Rate Factor value
        preset: Encoding preset
        crop_filter: Optional crop filter string

    Returns:
        Dictionary of FFmpeg output options
    """
    output_options = {
        'c:v': 'libx265',
        'preset': preset,
        'crf': str(crf),
        'c:a': 'copy',
        'c:s': 'copy'
    }

    if video.is_hdr_video():
        print("HDR video detected")
        x265_params = build_hdr_x265_params(video)
        output_options['pix_fmt'] = HDR_PIXEL_FORMAT
        output_options['x265-params'] = ':'.join(x265_params)

    if crop_filter:
        output_options['vf'] = crop_filter

    return output_options


def get_video_files(path: Path, supported_formats: List[str]) -> List[Path]:
    """Get list of video files from path.

    Args:
        path: File or directory path
        supported_formats: List of supported file extensions

    Returns:
        List of video file paths
    """
    if path.is_file():
        return [path] if path.suffix.lower() in supported_formats else []

    if path.is_dir():
        video_files = []
        for fmt in supported_formats:
            video_files.extend(path.glob(f'*{fmt}'))
        return sorted(video_files)

    return []


def determine_output_file(video_file: Path, output_path: Path, is_batch: bool) -> Path:
    """Determine output file path for a video file.

    Args:
        video_file: Input video file
        output_path: Output path (file or directory)
        is_batch: Whether this is batch processing

    Returns:
        Output file path
    """
    if is_batch:
        return output_path / video_file.with_suffix('.mkv').name
    return output_path
