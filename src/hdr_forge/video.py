"""Video metadata extraction and analysis module."""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.tools import hdr10plus_tool, mkvmerge
from hdr_forge.tools import dovi_tool
from hdr_forge.typedefs.encoder_typing import HdrSdrFormat
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionInfo, DolbyVisionProfile, DolbyVisionSiteDataInfo, DolbyVisionRpuInfo
from hdr_forge.typedefs.video_typing import MASTER_DISPLAY_PRESETS, ContentLightLevelMetadata, HdrMetadata, MasterDisplayColorPrimaries, MasterDisplayMetadata
from hdr_forge.typedefs.mkv_typing import MkvInfo, MkvTrack, MkvTrackType


class Video:
    """Handles video file metadata extraction and analysis."""

    def __init__(self, filepath: Path, with_out_rpu_extraction: bool = False) -> None:
        """Initialize video object and extract metadata using ffprobe.

        Args:
            filepath: Path to the video file

        Raises:
            RuntimeError: If ffprobe fails to extract metadata
        """
        self._filepath: Path = filepath
        self._video_metadata: dict = self._extract_video_metadata()
        self._hdr_metadata: HdrMetadata = self.extract_hdr_metadata()

        self._is_hdr10plus: bool = hdr10plus_tool.verify_hdr10plus(input_path=filepath)

        self._container_metadata: MkvInfo = mkvmerge.extract_container_info_json(input_mkv_mp4_ts_file=filepath)

        # Extract dimensions from video stream
        video_stream: dict = self._get_video_stream()
        self.width: int = video_stream.get('width', 0)
        self.height: int = video_stream.get('height', 0)


        self._dolby_vision_rpu_info: Optional[DolbyVisionRpuInfo] = None
        if self.is_dolby_vision_video() and not with_out_rpu_extraction:
            temp_dir: Path = get_global_temp_directory()
            ## get dolby vision rpu infos
            rpu_file_path: Path = dovi_tool.extract_rpu(
                input_path=self.get_filepath(),
                output_rpu=temp_dir / "RPU.rpu",
                dv_profile_source=self.get_dolby_vision_profile(),
                total_frames=self.get_total_frames(),
                use_cache=False,
            )
            self._dolby_vision_rpu_info = dovi_tool.get_rpu_info(
                rpu_path=Path(rpu_file_path)
            )

    def extract_hdr_metadata(self) -> HdrMetadata:
        # FFmpeg command: run showinfo only until data appears
        cmd: list = [
            "ffmpeg", "-hide_banner",
            "-i", self._filepath,
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

        #Dolby Vision Metadata Example:
        #[Parsed_showinfo_0 @ 0x7f3e94003d00]   side data - Dolby Vision Metadata:     rpu_type=2; rpu_format=18; vdr_rpu_profile=1; vdr_rpu_level=0; chroma_resampling_explicit_filter_flag=0; coef_data_type=0; coef_log2_denom=23; vdr_rpu_normalized_idc=1; bl_video_full_range_flag=0; bl_bit_depth=10; el_bit_depth=10; vdr_bit_depth=12; spatial_resampling_filter_flag=0; el_spatial_resampling_filter_flag=1; disable_residual_flag=0

        mastering_data: MasterDisplayMetadata | None = None
        light_data: ContentLightLevelMetadata | None = None

        # Regex for Mastering Display Metadata - cover both formats
        mastering_re: re.Pattern[str] = re.compile(
            r"(?:Mastering display metadata|side data - mastering display).*?"
            r"r\((?P<r_x>[\d\.]+)[\s,]+(?P<r_y>[\d\.]+)\)\s*"
            r"g\((?P<g_x>[\d\.]+)[\s,]+(?P<g_y>[\d\.]+)\)\s*"
            r"b\((?P<b_x>[\d\.]+)[\s,]+(?P<b_y>[\d\.]+)\)\s*"
            r"wp\((?P<wp_x>[\d\.]+)[\s,]+(?P<wp_y>[\d\.]+)\)\s*"
            r"min_luminance=(?P<min_lum>[\d\.]+)[\s,]*max_luminance=(?P<max_lum>[\d\.]+)"
        )

        # Regex for Content Light Level Metadata - cover both formats
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

                # If both found, terminate early
                if mastering_data and light_data:
                    process.kill()
                    break

        process.wait()

        # Clean up values (0 → None)
        if light_data:
            if light_data.maxcll == 0:
                light_data.maxcll = None
            if light_data.maxfall == 0:
                light_data.maxfall = None

        return HdrMetadata(
            mastering_display_metadata=mastering_data,
            content_light_level_metadata=light_data,
        )

    def _extract_video_metadata(self) -> dict:
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
                    str(self._filepath)
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
        streams = self._video_metadata.get('streams', [])
        for stream in streams:
            if stream.get('codec_type') == 'video':
                return stream
        return {}

    def is_video_interlaced(self) -> bool:
        """Check if the video is interlaced.

        Returns:
            True if interlaced, False otherwise
        """
        video_stream: dict = self._get_video_stream()
        field_order = video_stream.get('field_order', 'progressive').lower()
        return field_order in ['tt', 'bb', 'tb', 'bt']

    def get_filepath(self) -> Path:
        """Get the video file path.

        Returns:
            Path object of the video file
        """
        return self._filepath

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

    def get_video_profile(self) -> str | None:
        """Get video codec profile.

        Returns:
            Video profile string (e.g., 'High 10' for H.264, Main 10 for H.265)
        """
        return self._get_video_stream().get('profile', None)

    def get_pix_fmt(self) -> str | None:
        """Get pixel format of the video.

        Returns:
            Pixel format string (e.g., 'yuv420p10le' for HDR)
        """
        return self._get_video_stream().get('pix_fmt', None)

    def get_color_primaries(self) -> str | None:
        """Get color primaries information.

        Returns:
            Color primaries string
        """
        color_primaries: str | None = self._get_video_stream().get('color_primaries', None)
        if color_primaries is None and self.get_dolby_vision_profile() == DolbyVisionProfile._5:
            # DV Profile 5 implies BT.2020 color primaries
            return "bt2020"

        return color_primaries

    def get_color_space(self) -> str | None:
        """Get color space information.

        Returns:
            Color space string
        """
        return self._get_video_stream().get('color_space', None)

    def get_color_transfer(self) -> str | None:
        """Get color transfer characteristics.

        Returns:
            Color transfer string
        """
        return self._get_video_stream().get('color_transfer', None)

    def get_color_range(self) -> str | None:
        """Get color range information.

        Returns:
            Color range string
        """
        return self._get_video_stream().get('color_range', None)

    def get_container_type(self) -> str:
        """Get container format type.

        Returns:
            Container format string (e.g., 'matroska,webm' for MKV)
        """
        return self._container_metadata.container.type

    def get_container_video_tracks(self) -> list[MkvTrack]:
        """Get video tracks from the container metadata.

        Returns:
            List of MkvTrack objects representing video tracks
        """
        return [
            track
            for track in self._container_metadata.tracks
            if track.type == MkvTrackType.VIDEO
        ]

    def get_container_audio_tracks(self) -> list[MkvTrack]:
        """Get audio tracks from the container metadata.

        Returns:
            List of MkvTrack objects representing audio tracks
        """
        return [
            track
            for track in self._container_metadata.tracks
            if track.type == MkvTrackType.AUDIO
        ]

    def get_container_subtitles_tracks(self) -> list[MkvTrack]:
        """Get audio tracks from the container metadata.

        Returns:
            List of MkvTrack objects representing audio tracks
        """
        return [
            track
            for track in self._container_metadata.tracks
            if track.type == MkvTrackType.SUBTITLES
        ]

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
                    rpu_present_flag=data.get('rpu_present_flag', 0),
                    el_present_flag=data.get('el_present_flag', 0),
                )

        return None

    def get_dolby_vision_info(self) -> Optional[DolbyVisionInfo]:
        """Get Dolby Vision detailed information.

        Returns:
            DolbyVisionInfo object containing detailed Dolby Vision metadata or None if not available
        """
        if not self.is_dolby_vision_video():
            return None

        dv_profile: int | None = None
        dv_profile_el: str | None  = None
        dm_version: int | None = None
        cm_version: str | None = None

        dv_rpu_info: DolbyVisionRpuInfo | None = self._dolby_vision_rpu_info
        dv_site_data: DolbyVisionSiteDataInfo | None = self._get_dolby_vision_side_data_infos()
        if dv_rpu_info:
            dv_profile = dv_rpu_info.profile
            dv_profile_el = dv_rpu_info.profile_el
            dm_version = dv_rpu_info.dm_version
            cm_version = dv_rpu_info.cm_version
        else:
            dv_profile = dv_site_data.dv_profile if dv_site_data else None

        dv_level: Optional[int] = None
        if dv_site_data:
            dv_level = dv_site_data.dv_level

        dv_map_el: str = ''
        if dv_profile_el or dv_site_data and dv_site_data.el_present_flag == 1:
            dv_map_el = f"EL+"

        if dv_profile is None:
            return None

        return DolbyVisionInfo(
            dv_profile=dv_profile,
            dv_profile_el=dv_profile_el,
            dv_level=dv_level,
            el_preset=dv_site_data.el_present_flag == 1 if dv_site_data else False,
            rpu_preset=dv_site_data.rpu_present_flag == 1 if dv_site_data else False,
            dm_version=dm_version,
            cm_version=cm_version,
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

    def get_master_display(self) -> Optional[MasterDisplayMetadata]:
        """Extract HDR master display metadata.

        Returns:
            Master display metadata string or None if not found
        """
        if self._hdr_metadata.mastering_display_metadata:
            md: MasterDisplayMetadata = self._hdr_metadata.mastering_display_metadata
            return md

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
                    return MasterDisplayMetadata(
                        r_x=red_x,
                        r_y=red_y,
                        g_x=green_x,
                        g_y=green_y,
                        b_x=blue_x,
                        b_y=blue_y,
                        wp_x=white_x,
                        wp_y=white_y,
                        min_lum=min_lum,
                        max_lum=max_lum,
                    )

        return None

    def get_mastering_display_color_primaries(self) -> None | MasterDisplayColorPrimaries:
        """Check if the video uses Display P3 color primaries.

        Returns:
            True if color primaries indicate Display P3, False otherwise
        """
        md: MasterDisplayMetadata | None = self.get_master_display()
        if md is None:
            return None

        presets: Dict[MasterDisplayColorPrimaries, MasterDisplayMetadata] = MASTER_DISPLAY_PRESETS

        for primaries, preset_md in presets.items():
            if (md.r_x == preset_md.r_x and md.r_y == preset_md.r_y) and \
               (md.g_x == preset_md.g_x and md.g_y == preset_md.g_y) and \
               (md.b_x == preset_md.b_x and md.b_y == preset_md.b_y) and \
               (md.wp_x == preset_md.wp_x and md.wp_y == preset_md.wp_y):
                return primaries

        return None

    def get_content_light_level_metadata(self) -> Optional[ContentLightLevelMetadata]:
        return self._hdr_metadata.content_light_level_metadata

    def get_max_cll_max_fall(self, return_fallback: bool | None = False) -> Tuple[int, int] | None:
        """Extract HDR MaxCLL and MaxFALL metadata.

        Returns:
            Tuple of (MaxCLL, MaxFALL) or None if not found
        """

        if self._hdr_metadata.content_light_level_metadata:
            max_cll = self._hdr_metadata.content_light_level_metadata.maxcll
            max_fall = self._hdr_metadata.content_light_level_metadata.maxfall
            if max_cll is not None and max_fall is not None:
                return (int(max_cll), int(max_fall))

        if return_fallback:
            return 0, 0
        return None

    def get_hdr_metadata(self) -> HdrMetadata:
        """Get extracted HDR metadata.

        Returns:
            HdrMetadata object containing HDR metadata
        """
        return self._hdr_metadata

    def is_hdr_video(self) -> bool:
        """Check if video is HDR by detecting 10-bit pixel format.

        Returns:
            True if video is HDR (10-bit) and bt2020, False otherwise
        """
        hdr_colors: bool = "bt2020" in (self.get_color_primaries() or "")
        hdr_bit: bool = "10le" in (self.get_pix_fmt() or "")

        return hdr_colors and hdr_bit

    def is_hdr10_video(self) -> bool:
        """Check if video is HDR10.

        Returns:
            True if video is HDR10, False otherwise
        """
        master_display: MasterDisplayMetadata | None = self.get_master_display()
        if not master_display:
            return False
        return self.is_hdr_video()

    def is_hdr10plus_video(self) -> bool:
        """Check if video contains HDR10+ metadata.

        Returns:
            True if HDR10+ metadata is present, False otherwise
        """
        return self._is_hdr10plus

    def is_dolby_vision_video(self) -> bool:
        """Check if video contains Dolby Vision metadata.

        Returns:
            True if Dolby Vision metadata is present, False otherwise
        """
        dv_info: DolbyVisionSiteDataInfo | None = self._get_dolby_vision_side_data_infos()
        return dv_info is not None and dv_info.rpu_present_flag == 1

    def get_bit_depth(self) -> int:
        """Get the bit depth of the video.

        Returns:
            Bit depth as integer (e.g., 8, 10, 12)
        """
        pix_fmt: str = (self.get_pix_fmt() or "")
        match = re.search(r'(\d+)le', pix_fmt)
        if match:
            return int(match.group(1))
        return 8

    def get_hdr_sdr_format(self) -> list[HdrSdrFormat]:
        """Determine the color format of the video.

        Returns:
            ColorFormat enum value representing the color format
        """
        hdr_formats: list[HdrSdrFormat] = []
        if self.is_dolby_vision_video():
            hdr_formats.append(HdrSdrFormat.DOLBY_VISION)
        if self.is_hdr10plus_video():
            hdr_formats.append(HdrSdrFormat.HDR10_PLUS)
        if self.is_hdr10_video():
            hdr_formats.append(HdrSdrFormat.HDR10)

        if len(hdr_formats) > 0:
            return hdr_formats

        if self.is_hdr_video():
            return [HdrSdrFormat.HDR]
        else:
            return [HdrSdrFormat.SDR]

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
        duration = float(self._video_metadata.get('format', {}).get('duration', 0))
        if duration <= 0:
            return 0

        fps = self.get_fps()
        return int(duration * fps)

    def get_duration_seconds(self) -> float:
        """Get total duration of the video in seconds.

        Returns:
            Duration in seconds
        """
        return float(self._video_metadata.get('format', {}).get('duration', 0))
