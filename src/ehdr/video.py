"""Video metadata extraction and analysis module."""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, LiteralString, Optional, Tuple

from ehdr.hdr_formats import dolby_vision
from ehdr.typing.encoder_typing import HdrSdrFormat
from ehdr.typing.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionInfo, DolbyVisionProfile, DolbyVisionSiteDataInfo, DolbyVisionRpuInfo
from ehdr.typing.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata


DEFAULT_MASTER_DISPLAY: LiteralString = (
    f"G(13250,34500)"
    f"B(7500,3000)"
    f"R(34000,16000)"
    f"WP(15635,16450)"
    f"L(10000000,1)"
)


class Video:
    """Handles video file metadata extraction and analysis."""

    def __init__(self, filepath: Path) -> None:
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

        self.dolby_vision_rpu_info: Optional[DolbyVisionRpuInfo] = None
        if self.is_dolby_vision_video():
            ## get dolby vision rpu infos
            rpu_file_path: str = dolby_vision.extract_rpu(
                input_path=self.get_filepath(),
                output_rpu=str(f"/tmp/RPU.rpu"),
                dv_profile_source=self.get_dolby_vision_profile(),
            )
            self.dolby_vision_rpu_info = dolby_vision.get_rpu_info(
                rpu_path=Path(rpu_file_path)
            )


    def extract_hdr_metadata(self) -> HdrMetadata:
        # ffmpeg-Kommando: showinfo nur so lange laufen lassen, bis Daten auftauchen
        cmd: list = [
            "ffmpeg", "-hide_banner",
            "-i", self.filepath,
            "-vf", "showinfo",
            "-frames:v", "10",
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

    def _get_dolby_vision_side_data_infos(self) -> Optional[DolbyVisionSiteDataInfo]:
        """Extract Dolby Vision metadata.

        Returns:
            DolbyVisionInfo object containing Dolby Vision metadata or None if not found
        """
        video_stream = self._get_video_stream()
        side_data = video_stream.get('side_data_list', [])

        for data in side_data:
            if data.get('side_data_type') == 'DOVI configuration record':
                return DolbyVisionSiteDataInfo(
                    dv_profile=data.get('dv_profile'),
                    dv_level=data.get('dv_level'),
                    rpu_present_flag=data.get('rpu_present_flag', 0)
                )

        return None

    def _get_dolby_vision_rpu_info(self) -> Optional[DolbyVisionRpuInfo]:
        """Get Dolby Vision RPU information.

        Returns:
            RpuInfo object containing RPU metadata or None if not available
        """
        return self.dolby_vision_rpu_info

    def get_dolby_vision_info(self) -> Optional[DolbyVisionInfo]:
        """Get Dolby Vision detailed information.

        Returns:
            DolbyVisionInfo object containing detailed Dolby Vision metadata or None if not available
        """
        if not self.is_dolby_vision_video():
            return None
        dv_rpu_info: DolbyVisionRpuInfo | None = self._get_dolby_vision_rpu_info()

        if not dv_rpu_info:
            return None
        dv_site_data: DolbyVisionSiteDataInfo | None = self._get_dolby_vision_side_data_infos()

        dv_level: Optional[int] = None
        if dv_site_data:
            dv_level = dv_site_data.dv_level

        dv_map_el: str = ''
        if dv_rpu_info.profile_el:
            dv_map_el = f"EL+"

        return DolbyVisionInfo(
            dv_profile=dv_rpu_info.profile,
            dv_profile_el=dv_rpu_info.profile_el,
            dv_level=dv_level,
            dm_version=dv_rpu_info.dm_version,
            cm_version=dv_rpu_info.cm_version,
            dv_layout=f"BL+{dv_map_el}RPU",
        )

    def get_dolby_vision_enhancement_layer(self) -> Optional[DolbyVisionEnhancementLayer]:
        """Get Dolby Vision Enhancement Layer type.

        Returns:
            DolbyVisionEnhancementLayer enum value or None if not available
        """
        dv_info: DolbyVisionInfo | None = self.get_dolby_vision_info()
        if dv_info and dv_info.dv_profile_el:
            if dv_info.dv_profile_el.upper() == DolbyVisionEnhancementLayer.FEL.value:
                return DolbyVisionEnhancementLayer.FEL
            elif dv_info.dv_profile_el.upper() == DolbyVisionEnhancementLayer.MEL.value:
                return DolbyVisionEnhancementLayer.MEL
        return None

    def get_dolby_vision_profile(self) -> Optional[DolbyVisionProfile]:
        """Get Dolby Vision profile number.

        Returns:
            Dolby Vision profile as integer or None if not found
        """
        dv_info: DolbyVisionInfo | None = self.get_dolby_vision_info()
        if dv_info is None:
            return None

        try:
            return DolbyVisionProfile(dv_info.dv_profile)
        except ValueError:
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
        dv_info: DolbyVisionSiteDataInfo | None = self._get_dolby_vision_side_data_infos()
        return dv_info is not None and dv_info.rpu_present_flag == 1

    def get_hdr_sdr_format(self) -> HdrSdrFormat:
        """Determine the color format of the video.

        Returns:
            ColorFormat enum value representing the color format
        """
        if self.is_dolby_vision_video():
            return HdrSdrFormat.DOLBY_VISION
        elif self.is_hdr_video():
            return HdrSdrFormat.HDR10
        else:
            return HdrSdrFormat.SDR

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

    def get_duration_seconds(self) -> float:
        """Get total duration of the video in seconds.

        Returns:
            Duration in seconds
        """
        return float(self.metadata.get('format', {}).get('duration', 0))
