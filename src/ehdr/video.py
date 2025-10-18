"""Video metadata extraction and analysis module."""

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, LiteralString, Optional, Tuple

from ffmpeg import FFmpeg

# Ersetze TypedDict durch dataclass
@dataclass
class DolbyVisionInfo:
    """Structure for Dolby Vision metadata information."""
    dv_profile: Optional[int] = None
    dv_level: Optional[int] = None
    rpu_present_flag: int = 0

DEFAULT_MASTER_DISPLAY: LiteralString = (
    f"G(13250,34500)"
    f"B(7500,3000)"
    f"R(34000,16000)"
    f"WP(15635,16450)"
    f"L(10000000,1)"
)


class Video:
    """Handles video file metadata extraction and analysis."""

    def __init__(self, filepath: str, crf: Optional[int], preset: Optional[str]):
        """Initialize video object and extract metadata using ffprobe.

        Args:
            filepath: Path to the video file

        Raises:
            RuntimeError: If ffprobe fails to extract metadata
        """
        self.filepath = Path(filepath)
        self.metadata = self._extract_metadata()

        # Extract dimensions from video stream
        video_stream = self._get_video_stream()
        self.width = video_stream.get('width', 0)
        self.height = video_stream.get('height', 0)

        # Crop dimensions (initialized to full frame)
        self.crop_width = self.width
        self.crop_height = self.height
        self.crop_x = 0
        self.crop_y = 0

        if crf is None:
            self.crf = self._get_auto_crf()
        else:
            self.crf = crf

        if preset is None:
            self.preset = self._get_auto_preset()
        else:
            self.preset = preset

    def _extract_metadata(self) -> Dict:
        """Extract video metadata using ffprobe.

        Returns:
            Dictionary containing video metadata

        Raises:
            RuntimeError: If ffprobe command fails
        """
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    str(self.filepath)
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract metadata: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse ffprobe output: {e}")

    def _get_video_stream(self) -> Dict:
        """Get the first video stream from metadata.

        Returns:
            Dictionary containing video stream information
        """
        streams = self.metadata.get('streams', [])
        for stream in streams:
            if stream.get('codec_type') == 'video':
                return stream
        return {}

    def get_crf(self) -> int:
        """Get the CRF value for encoding.

        Returns:
            CRF value
        """
        return self.crf

    def get_preset(self) -> str:
        """Get the preset value for encoding.

        Returns:
            Preset string
        """
        return self.preset

    def get_width(self) -> int:
        """Get video width.

        Returns:
            Width in pixels
        """
        return self.width

    def get_height(self) -> int:
        """Get video height.

        Returns:
            Height in pixels
        """
        return self.height

    def get_pix_fmt(self) -> str:
        """Get pixel format of the video.

        Returns:
            Pixel format string (e.g., 'yuv420p10le' for HDR)
        """
        return self._get_video_stream().get('pix_fmt', '')

    def get_color_primaries(self) -> str:
        """Get color primaries information.

        Returns:
            Color primaries string
        """
        return self._get_video_stream().get('color_primaries', '')

    def get_color_space(self) -> str:
        """Get color space information.

        Returns:
            Color space string
        """
        return self._get_video_stream().get('color_space', '')

    def get_color_transfer(self) -> str:
        """Get color transfer characteristics.

        Returns:
            Color transfer string
        """
        return self._get_video_stream().get('color_transfer', '')

    def get_dolby_vision_infos(self) -> Optional[DolbyVisionInfo]:
        """Extract Dolby Vision metadata.

        Returns:
            DolbyVisionInfo object containing Dolby Vision metadata or None if not found
        """
        video_stream = self._get_video_stream()
        side_data = video_stream.get('side_data_list', [])

        for data in side_data:
            if data.get('side_data_type') == 'DOVI configuration record':
                return DolbyVisionInfo(
                    dv_profile=data.get('dv_profile'),
                    dv_level=data.get('dv_level'),
                    rpu_present_flag=data.get('rpu_present_flag', 0)
                )

        return None

    def get_master_display(self) -> Optional[str]:
        """Extract HDR master display metadata.

        Returns:
            Master display metadata string or None if not found
        """
        video_stream = self._get_video_stream()
        side_data = video_stream.get('side_data_list', [])

        for data in side_data:
            if data.get('side_data_type') == 'Mastering display metadata':
                # Extract red, green, blue, white point coordinates
                red_x = data.get('red_x', '')
                red_y = data.get('red_y', '')
                green_x = data.get('green_x', '')
                green_y = data.get('green_y', '')
                blue_x = data.get('blue_x', '')
                blue_y = data.get('blue_y', '')
                white_x = data.get('white_point_x', '')
                white_y = data.get('white_point_y', '')
                max_lum = data.get('max_luminance', '')
                min_lum = data.get('min_luminance', '')

                if all([red_x, red_y, green_x, green_y, blue_x, blue_y,
                       white_x, white_y, max_lum, min_lum]):
                    return (f"G({green_x},{green_y})"
                           f"B({blue_x},{blue_y})"
                           f"R({red_x},{red_y})"
                           f"WP({white_x},{white_y})"
                           f"L({max_lum},{min_lum})")

        return DEFAULT_MASTER_DISPLAY

    def get_max_cll_max_fall(self, return_fallback: bool | None = False) -> Tuple[int, int] | None:
        """Extract HDR MaxCLL and MaxFALL metadata.

        Returns:
            Tuple of (MaxCLL, MaxFALL) or None if not found
        """
        # video_stream = self._get_video_stream()
        # side_data = video_stream.get('side_data_list', [])

        # for data in side_data:
        #     if data.get('side_data_type') == 'Content light level information':
        #         max_cll = data.get('max_content_light_level')
        #         max_fall = data.get('max_frame_average_light_level')
        #         if max_cll is not None and max_fall is not None:
        #             return (int(max_cll), int(max_fall))

        if return_fallback:
            return 0, 0
        return None

    def is_hdr_video(self) -> bool:
        """Check if video is HDR by detecting 10-bit pixel format.

        Returns:
            True if video is HDR (10-bit), False otherwise
        """
        return '10le' in self.get_pix_fmt()

    def get_pixel_count(self) -> int:
        """Get total pixel count (width * height).

        Returns:
            Total number of pixels
        """
        return self.width * self.height

    def get_fps(self) -> float:
        """Get video frame rate (frames per second).

        Returns:
            Frame rate as float (e.g., 23.976, 30.0)
        """
        video_stream = self._get_video_stream()
        frame_rate_str = video_stream.get('r_frame_rate', '24/1')

        try:
            # Parse frame rate (format: "24000/1001" or "30/1")
            num, denom = map(float, frame_rate_str.split('/'))
            return num / denom if denom > 0 else 24.0
        except (ValueError, ZeroDivisionError):
            return 24.0

    def get_total_frames(self) -> int:
        """Calculate total number of frames in the video.

        Returns:
            Total frame count
        """
        duration = float(self.metadata.get('format', {}).get('duration', 0))
        if duration <= 0:
            return 0

        fps = self.get_fps()
        return int(duration * fps)

    def _get_auto_crf(self) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)
        """
        pixels = self.get_pixel_count()

        # UHD 4K (3840x2160 = 8,294,400 pixels)
        if pixels >= 6_144_000:
            return 13

        # 2K to 4K range - scale linearly
        if pixels >= 2_211_841:
            # Linear interpolation between 14 (at 6.14M) and 18 (at 2.21M)
            ratio = (pixels - 2_211_841) / (6_144_000 - 2_211_841)
            return int(18 - (4 * ratio))

        # Full HD (1920x1080 = 2,073,600 pixels)
        if pixels >= 2_073_600:
            return 18

        # Lower resolutions
        if pixels >= 1_000_000:
            return 19

        return 20

    def _get_auto_preset(self) -> str:
        """Select optimal encoding preset based on resolution.

        Returns:
            Preset string (faster preset = quicker encoding, lower compression)
        """
        pixels = self.get_pixel_count()

        # 4K+ (4096x2160 = 8,847,360 pixels)
        if pixels >= 8_847_361:
            return 'superfast'

        # 2K to 4K range
        if pixels >= 2_073_601:
            return 'faster'

        # Full HD
        if pixels >= 2_073_600:
            return 'fast'

        # Lower resolutions
        return 'medium'

    def _detect_crop_at_position(self, position_seconds: int) -> Optional[Tuple[int, int, int, int]]:
        """Detect crop parameters at a specific video position.

        Args:
            position_seconds: Time position in seconds to analyze

        Returns:
            Tuple of (width, height, x, y) or None if detection fails
        """
        try:
            ffmpeg = FFmpeg()

            # Capture stderr to get cropdetect output
            import io
            import sys

            stderr_capture = io.StringIO()

            ffmpeg.option('ss', str(position_seconds))
            ffmpeg.input(str(self.filepath))
            ffmpeg.option('t', '5')  # Analyze 5 seconds
            ffmpeg.option('vf', 'cropdetect')
            ffmpeg.option('f', 'null')
            ffmpeg.output('-')

            # Execute and capture stderr
            process = ffmpeg.execute(stream=True, stderr=subprocess.PIPE, text=True)
            stderr_output = process.stderr.read() if hasattr(process, 'stderr') and process.stderr else ""

            # Parse cropdetect output
            crop_pattern = re.compile(r'crop=(\d+):(\d+):(\d+):(\d+)')
            matches = crop_pattern.findall(stderr_output)

            if matches:
                # Get the last (most stable) crop detection
                w, h, x, y = matches[-1]
                return (int(w), int(h), int(x), int(y))

        except Exception:
            pass

        return None

    def crop_video(self, num_threads: int = 10) -> None:
        """Detect and apply optimal crop parameters using multi-threaded analysis.

        Args:
            num_threads: Number of concurrent threads for crop detection
        """
        # Get video duration
        duration = float(self.metadata.get('format', {}).get('duration', 0))

        if duration <= 0:
            return

        # Calculate positions to sample (evenly distributed)
        interval = duration / (num_threads + 1)
        positions = [int(interval * (i + 1)) for i in range(num_threads)]

        # Run crop detection in parallel
        crop_results = []
        completed = 0
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                executor.submit(self._detect_crop_at_position, pos): pos
                for pos in positions
            }

            for future in as_completed(futures):
                result = future.result()
                if result:
                    crop_results.append(result)
                completed += 1
                # Show progress
                print(f"\rAnalyzing crop: {completed}/{num_threads} samples", end='', flush=True)

        print()  # New line after progress

        if not crop_results:
            return

        # Find most common crop dimensions
        from collections import Counter
        crop_counter = Counter(crop_results)
        most_common_crop = crop_counter.most_common(1)[0][0]

        self.crop_width, self.crop_height, self.crop_x, self.crop_y = most_common_crop

    def get_crop_filter(self) -> Optional[str]:
        """Get ffmpeg crop filter string if cropping is needed.

        Returns:
            Crop filter string or None if no cropping needed
        """
        if (self.crop_width != self.width or
            self.crop_height != self.height or
            self.crop_x != 0 or
            self.crop_y != 0):
            return f"crop={self.crop_width}:{self.crop_height}:{self.crop_x}:{self.crop_y}"
        return None
