"""Video metadata extraction and analysis module."""

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, LiteralString, Optional, Tuple

from ffmpeg import FFmpeg

@dataclass
class DolbyVisionInfo:
    """Structure for Dolby Vision metadata information."""
    dv_profile: Optional[int] = None
    dv_level: Optional[int] = None
    rpu_present_flag: int = 0

@dataclass
class MasterDisplayMetadata:
    r_x: float
    r_y: float
    g_x: float
    g_y: float
    b_x: float
    b_y: float
    wp_x: float
    wp_y: float
    min_lum: float
    max_lum: float

@dataclass
class ContentLightLevelMetadata:
    """Structure for Content Light Level metadata information."""
    maxcll: Optional[int] = None
    maxfall: Optional[int] = None

@dataclass
class HdrMetadata:
    mastering_display_metadata: Optional[MasterDisplayMetadata] = None
    content_light_level_metadata: Optional[ContentLightLevelMetadata] = None

DEFAULT_MASTER_DISPLAY: LiteralString = (
    f"G(13250,34500)"
    f"B(7500,3000)"
    f"R(34000,16000)"
    f"WP(15635,16450)"
    f"L(10000000,1)"
)


class Video:
    """Handles video file metadata extraction and analysis."""

    def __init__(self, filepath: Path, crf: Optional[int] = None, preset: Optional[str] = None):
        """Initialize video object and extract metadata using ffprobe.

        Args:
            filepath: Path to the video file

        Raises:
            RuntimeError: If ffprobe fails to extract metadata
        """
        self.filepath: Path = filepath
        self.metadata: dict = self._extract_metadata()

        self.hdr_metadata: HdrMetadata = self.extract_hdr_metadata()

        # Extract dimensions from video stream
        video_stream: dict = self._get_video_stream()
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

    def extract_hdr_metadata(self) -> HdrMetadata:
        # ffmpeg-Kommando: showinfo nur so lange laufen lassen, bis Daten auftauchen
        cmd: list = [
            "ffmpeg", "-hide_banner",
            "-i", self.filepath,
            "-vf", "showinfo",
            "-frames:v", "10",  # bis 10 Frames prüfen (meist reicht 1)
            "-f", "null", "-",
        ]

        process = subprocess.Popen(
            args=cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
        )

        mastering_data: MasterDisplayMetadata | None = None
        light_data: ContentLightLevelMetadata | None = None

        # Regex für Mastering Display Metadata - beide Formate abdecken
        mastering_re: re.Pattern[str] = re.compile(
            r"(?:Mastering display metadata|side data - mastering display).*?"
            r"r\((?P<r_x>[\d\.]+)[\s,]+(?P<r_y>[\d\.]+)\)\s*"
            r"g\((?P<g_x>[\d\.]+)[\s,]+(?P<g_y>[\d\.]+)\)\s*"
            r"b\((?P<b_x>[\d\.]+)[\s,]+(?P<b_y>[\d\.]+)\)\s*"
            r"wp\((?P<wp_x>[\d\.]+)[\s,]+(?P<wp_y>[\d\.]+)\)\s*"
            r"min_luminance=(?P<min_lum>[\d\.]+)[\s,]*max_luminance=(?P<max_lum>[\d\.]+)"
        )

        # Regex für Content Light Level Metadata - beide Formate abdecken
        light_re: re.Pattern[str] = re.compile(
            r"(?:Content light level metadata|side data - Content Light Level information).*?"
            r"MaxCLL=(?P<maxcll>\d+),\s*MaxFALL=(?P<maxfall>\d+)"
        )

        if process.stderr:
            for line in process.stderr.readlines():
                if not mastering_data:
                    m: re.Match[str] | None = mastering_re.search(line)
                    if m:
                        mastering_data = MasterDisplayMetadata(**{k: float(v) for k, v in m.groupdict().items()})
                if not light_data:
                    l: re.Match[str] | None = light_re.search(line)
                    if l:
                        light_data = ContentLightLevelMetadata(**{k: int(v) for k, v in l.groupdict().items()})

                # Falls beide gefunden wurden, abbrechen
                if mastering_data and light_data:
                    process.kill()
                    break

        process.wait()

        # Werte bereinigen (0 → None)
        if light_data:
            if light_data.maxcll == 0:
                light_data.maxcll = None
            if light_data.maxfall == 0:
                light_data.maxfall = None

        return HdrMetadata(
            mastering_display_metadata=mastering_data,
            content_light_level_metadata=light_data,
        )


    def _extract_metadata(self) -> dict:
        """Extract video metadata using ffprobe.

        Returns:
            Dictionary containing video metadata

        Raises:
            RuntimeError: If ffprobe command fails
        """
        try:
            result = subprocess.run(
                args=[
                    'ffprobe',
                    '-v', 'debug',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    str(self.filepath)
                ],
                capture_output=True,
                text=True,
                check=True
            )

            stdout_json = result.stdout.strip()

            return json.loads(stdout_json)
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

    def get_filepath(self) -> Path:
        """Get the video file path.

        Returns:
            Path object of the video file
        """
        return self.filepath

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
        if self.hdr_metadata.mastering_display_metadata:
            md: MasterDisplayMetadata = self.hdr_metadata.mastering_display_metadata
            return (f"G({int(md.g_x*50000)},{int(md.g_y*50000)})"
                    f"B({int(md.b_x*50000)},{int(md.b_y*50000)})"
                    f"R({int(md.r_x*50000)},{int(md.r_y*50000)})"
                    f"WP({int(md.wp_x*50000)},{int(md.wp_y*50000)})"
                    f"L({int(md.max_lum*10000)},{int(md.min_lum*10000)})")

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

        if self.hdr_metadata.content_light_level_metadata:
            max_cll = self.hdr_metadata.content_light_level_metadata.maxcll
            max_fall = self.hdr_metadata.content_light_level_metadata.maxfall
            if max_cll is not None and max_fall is not None:
                return (int(max_cll), int(max_fall))

        if return_fallback:
            return 0, 0
        return None

    def is_hdr_video(self) -> bool:
        """Check if video is HDR by detecting 10-bit pixel format.

        Returns:
            True if video is HDR (10-bit), False otherwise
        """
        return '10le' in self.get_pix_fmt()

    def is_dolby_vision_video(self) -> bool:
        """Check if video contains Dolby Vision metadata.

        Returns:
            True if Dolby Vision metadata is present, False otherwise
        """
        dv_info: DolbyVisionInfo | None = self.get_dolby_vision_infos()
        return dv_info is not None and dv_info.rpu_present_flag == 1

    def is_cropped_video(self) -> bool:
        """Check if video has been cropped.

        Returns:
            True if cropping parameters differ from original dimensions, False otherwise
        """
        return (self.crop_width != self.width or
                self.crop_height != self.height or
                self.crop_x != 0 or
                self.crop_y != 0)

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
