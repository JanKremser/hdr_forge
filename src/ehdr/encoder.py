"""Video encoder configuration and parameter building."""

import math
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from ffmpeg import FFmpeg

from ehdr.container import mkv
from ehdr.dataclass import ColorFormat, CropHandler
from ehdr.hdr_formats import dolby_vision
from ehdr.video import Video


class Encoder:
    """Handles video encoding configuration for different color formats."""

    # HDR x265 parameters for HDR10 encoding
    HDR_X265_PARAMS: list[str] = [
        'hdr-opt=1',
        'repeat-headers=1',
        'colorprim=bt2020',
        'transfer=smpte2084',
        'colormatrix=bt2020nc',
    ]

    # SDR x265 parameters
    SDR_X265_PARAMS: list[str] = [
        'colorprim=bt709',
        'transfer=bt709',
        'colormatrix=bt709',
        'no-hdr10-opt=1',
    ]

    HDR_PIXEL_FORMAT = 'yuv420p10le'
    SDR_PIXEL_FORMAT = 'yuv420p'

    def __init__(
        self,
        video: Video,
        target_file: Path,
        color_format: ColorFormat = ColorFormat.AUTO,
        crf: Optional[int] = None,
        preset: Optional[str] = None,
        enable_crop: bool = False,
        scale_height: Optional[int] = None,
        crop_callback: Optional[Callable[[CropHandler], None]] = None,
    ):
        """Initialize encoder with video and target color format.

        Args:
            video: Video object with metadata
            target_file: Target output file path
            color_format: Target color format (AUTO, SDR, HDR10, DOLBY_VISION)
            crf: Optional CRF override (uses auto-calculation if None)
            preset: Optional preset override (uses auto-calculation if None)
            enable_crop: Enable automatic black bar detection and cropping
            scale_height: Optional target height for scaling (downscaling only)
            crop_callback: Optional callback for crop detection progress
        """
        self.video = video
        self.target_file = target_file

        # Determine effective color format
        self.effective_format: ColorFormat = self._determine_effective_format(
            color_format=color_format
        )

        # Crop dimensions (initialized to full frame)
        self.crop_width = video.width
        self.crop_height = video.height
        self.crop_x = 0
        self.crop_y = 0

        # Apply cropping if enabled (not supported for Dolby Vision)
        if enable_crop and not self.is_dolby_vision_encoding():
            self._crop_video(callback=crop_callback)

        # Scale dimensions
        self.scale_video = False
        self.scale_width: Optional[int] = None
        self.scale_height: Optional[int] = None

        if scale_height is not None and scale_height < video.height:
            aspect_ratio: float = video.width / video.height
            self.scale_video = True
            self.scale_width = math.ceil(scale_height * aspect_ratio)
            self.scale_height = scale_height

        # Calculate or use provided CRF and preset
        self.crf = crf if crf is not None else self._get_auto_crf()
        self.preset = preset if preset is not None else self._get_auto_preset()

    def _determine_effective_format(self, color_format: ColorFormat) -> ColorFormat:
        """Determine the effective color format based on target and source.

        Only downgrades are allowed (DV→HDR10→SDR). Upgrades are not possible.

        Returns:
            Effective ColorFormat to use for encoding
        """
        # Determine source format
        if self.video.is_dolby_vision_video():
            source_format = ColorFormat.DOLBY_VISION
        elif self.video.is_hdr_video():
            source_format = ColorFormat.HDR10
        else:
            source_format = ColorFormat.SDR

        if color_format == ColorFormat.AUTO:
            # Auto mode: keep source format
            return source_format

        # Check if conversion is valid (only downgrades allowed)
        format_hierarchy = {
            ColorFormat.SDR: 0,
            ColorFormat.HDR10: 1,
            ColorFormat.DOLBY_VISION: 2
        }

        source_level = format_hierarchy[source_format]
        target_level = format_hierarchy[color_format]

        if target_level > source_level:
            # Attempting upgrade - not allowed, keep source
            print(f"Warning: Cannot upgrade from {source_format.value} to {color_format.value}. Keeping source format.")
            return source_format

        # Valid downgrade
        return color_format

    def get_color_format(self) -> ColorFormat:
        """Get the effective color format for encoding.

        Returns:
            Effective ColorFormat
        """
        return self.effective_format

    def is_dolby_vision_encoding(self) -> bool:
        """Check if encoding to Dolby Vision format."""
        return self.effective_format == ColorFormat.DOLBY_VISION

    def is_hdr10_encoding(self) -> bool:
        """Check if encoding to HDR10 format."""
        return self.effective_format == ColorFormat.HDR10

    def is_sdr_encoding(self) -> bool:
        """Check if encoding to SDR format."""
        return self.effective_format == ColorFormat.SDR

    def _is_cropped(self) -> bool:
        """Check if video has cropping applied.

        Returns:
            True if cropping is applied, False otherwise
        """
        return (self.crop_width != self.video.width or
                self.crop_height != self.video.height or
                self.crop_x != 0 or
                self.crop_y != 0)

    def _get_pixel_count(self) -> int:
        """Get total pixel count considering scale and crop.

        Returns:
            Total number of pixels for encoding
        """
        scale_d = self._get_scale_dimensions()
        if scale_d:
            w, h = scale_d
            return w * h

        if self._is_cropped():
            return self.crop_width * self.crop_height

        return self.video.width * self.video.height

    def _get_scale_dimensions(self) -> Optional[Tuple[int, int]]:
        """Get target scale dimensions if scaling is enabled.

        Returns:
            Tuple of (width, height) or None if scaling is not applied
        """
        if self.scale_video and self.scale_width and self.scale_height:
            if self._is_cropped():
                width = self.crop_width
                height = self.crop_height
                new_aspect_ratio: float = width / height

                if self.crop_width > self.scale_width:
                    new_scale_height = math.floor(self.scale_width / new_aspect_ratio)
                    return (self.scale_width, new_scale_height)

                if self.crop_height > self.scale_height:
                    new_scale_width = math.ceil(self.scale_height * new_aspect_ratio)
                    return (new_scale_width, self.scale_height)

                return (width, height)
            else:
                return (self.scale_width, self.scale_height)

        return None

    def _get_auto_crf(self) -> int:
        """Calculate optimal CRF value based on resolution.

        Returns:
            CRF value (lower = higher quality)
        """
        pixels = self._get_pixel_count()

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
        pixels = self._get_pixel_count()

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
        cmd = [
            'ffmpeg',
            '-ss', str(position_seconds),
            '-i', str(self.video.filepath),
            '-vf', 'cropdetect=24:16:0',
            '-frames:v', '10',
            '-f', 'null',
            '-'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse cropdetect output
            import re
            crop_pattern = re.compile(r'crop=(\d+):(\d+):(\d+):(\d+)')

            for line in result.stderr.split('\n'):
                match = crop_pattern.search(line)
                if match:
                    w, h, x, y = map(int, match.groups())
                    return (w, h, x, y)

        except (subprocess.TimeoutExpired, Exception):
            pass

        return None

    def _crop_video(self, num_threads: int = 10,
                   callback: Optional[Callable[[CropHandler], None]] = None) -> None:
        """Detect and apply optimal crop parameters using multi-threaded analysis.

        Args:
            num_threads: Number of concurrent threads for crop detection
            callback: Optional callback function for progress updates
        """
        if callback:
            callback(CropHandler(
                finish_progress=False,
                completed_samples=0,
                total_samples=num_threads,
            ))

        # Get video duration
        duration = self.video.get_duration_seconds()

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

                if callback:
                    callback(CropHandler(
                        finish_progress=False,
                        completed_samples=completed,
                        total_samples=num_threads,
                    ))

        # Send final crop handler
        if callback:
            callback(CropHandler(
                finish_progress=True,
                completed_samples=completed,
                total_samples=num_threads,
            ))

        if not crop_results:
            return

        # Find most common crop dimensions
        crop_counter = Counter(crop_results)
        most_common_crop = crop_counter.most_common(1)[0][0]

        self.crop_width, self.crop_height, self.crop_x, self.crop_y = most_common_crop

    def get_crop_filter(self) -> Optional[str]:
        """Get ffmpeg crop filter string if cropping is needed.

        Returns:
            Crop filter string or None if no cropping needed
        """
        if self._is_cropped():
            return f"crop={self.crop_width}:{self.crop_height}:{self.crop_x}:{self.crop_y}"
        return None

    def get_scale_filter(self) -> Optional[str]:
        """Get ffmpeg scale filter string if scaling is needed.

        Returns:
            Scale filter string or None if no scaling needed
        """
        scale_d = self._get_scale_dimensions()
        if scale_d:
            w, h = scale_d
            return f"scale={w}:{h}"
        return None

    def get_target_file(self) -> Path:
        """Get the target output file path.

        Returns:
            Target file Path
        """
        return self.target_file

    def _get_temp_directory(self) -> Path:
        """Get or create temporary directory for intermediate files.

        Creates a temp directory in the same location as target_file:
        {target_file_dir}/.ehdr_temp_{target_file_stem}/

        Returns:
            Path to temporary directory
        """
        temp_dir = self.target_file.parent / f".ehdr_temp_{self.target_file.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def _cleanup_temp_directory(self) -> None:
        """Remove temporary directory and all its contents.

        Deletes the temp directory created by _get_temp_directory().
        Handles errors gracefully and prints warnings if cleanup fails.
        """
        import shutil

        temp_dir = self.target_file.parent / f".ehdr_temp_{self.target_file.stem}"

        if temp_dir.exists() and temp_dir.is_dir():
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary files: {temp_dir}")
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory {temp_dir}: {e}")

    def build_ffmpeg_output_options(self) -> Dict[str, str]:
        """Build FFmpeg output options dictionary for encoding.

        Returns:
            Dictionary of FFmpeg output options
        """
        output_options: dict = {
            'c:v': 'libx265',
            'preset': self.preset,
            'crf': str(self.crf),
            'c:a': 'copy',
            'c:s': 'copy'
        }


        # Add video filters (crop and scale)
        crop_filter: str | None = self.get_crop_filter()
        if crop_filter:
            output_options['vf'] = crop_filter

        scale_filter: str | None = self.get_scale_filter()
        if scale_filter:
            if 'vf' in output_options:
                output_options['vf'] += f',{scale_filter}'
            else:
                output_options['vf'] = scale_filter

        # Add format-specific parameters
        if self.is_hdr10_encoding() or self.is_dolby_vision_encoding():
            x265_params: list[str] = self._build_hdr_x265_params()
            output_options['pix_fmt'] = self.HDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)
        elif self.is_sdr_encoding():
            x265_params: list[str] = self._build_sdr_x265_params()
            output_options['pix_fmt'] = self.SDR_PIXEL_FORMAT
            output_options['x265-params'] = ':'.join(x265_params)
            if self.video.is_hdr_video():
                # Tone mapping for HDR to SDR conversion
                output_options['vf'] = (
                    (output_options.get('vf', '') + ',') if 'vf' in output_options else ''
                ) + 'zscale=primaries=bt2020:transfer=smpte2084:matrix=bt2020nc:t=linear:npl=100,format=gbrpf32le,zscale=primaries=bt709:transfer=bt709:matrix=bt709:range=tv,tonemap=hable,format=yuv420p'

        return output_options

    def _build_hdr_x265_params(self) -> list[str]:
        """Build x265 parameters for HDR10 video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.HDR_X265_PARAMS.copy()

        master_display = self.video.get_master_display()
        if master_display:
            params.append(f'master-display={master_display}')

            max_cll_max_fall: Tuple[int, int] | None = self.video.get_max_cll_max_fall()
            if max_cll_max_fall:
                max_cll, max_fall = max_cll_max_fall
                params.append(f'max-cll={max_cll},{max_fall}')

        return params

    def _build_sdr_x265_params(self) -> list[str]:
        """Build x265 parameters for SDR video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.SDR_X265_PARAMS.copy()
        if self.video.is_hdr_video():
            # remove HDR metadata if present
            params.append('master-display=G(0,0)B(0,0)R(0,0)WP(0,0)L(0,0)')
            params.append('max-cll=0,0')
        return params

    def get_format_name(self) -> str:
        """Get human-readable format name.

        Returns:
            Format name string
        """
        if self.is_dolby_vision_encoding():
            return "Dolby Vision"
        elif self.is_hdr10_encoding():
            return "HDR10"
        else:
            return "SDR"

    def _start_ffmpeg_process(
        self,
        input_file: Path,
        target_file: Path,
        progress_callback: Optional[Callable] = None,
        finish_callback: Optional[Callable] = None,
    ):
        try:
            # Build ffmpeg command
            ffmpeg = FFmpeg()
            ffmpeg.option('y')
            ffmpeg.input(str(input_file))

            # Build output options
            output_options: dict = self.build_ffmpeg_output_options()
            ffmpeg.output(url=str(target_file), options=output_options)

            # Execute with optional progress tracking
            if progress_callback:
                ffmpeg.on('progress', progress_callback)

            ffmpeg.execute()

            # Call finish callback if provided
            if finish_callback:
                finish_callback()

            return True

        except Exception as e:
            print(f"Error during encoding: {e}")
            return False

    def convert_sdr_hdr10(
        self,
        progress_callback: Optional[Callable] = None,
        finish_callback: Optional[Callable] = None,
    ) -> bool:
        """Execute FFmpeg conversion with configured parameters.

        Args:
            output_file: Output file path
            progress_callback: Optional progress handler callback
            finish_callback: Optional finish callback (called after successful encoding)

        Returns:
            True if conversion succeeded, False otherwise
        """
        input_file = self.video.get_filepath()

        return self._start_ffmpeg_process(
            input_file=input_file,
            target_file=self.target_file,
            progress_callback=progress_callback,
            finish_callback=finish_callback,
        )

    def convert_dolby_vision(
        self,
        progress_callback: Optional[Callable] = None,
        finish_callback: Optional[Callable] = None,
    ) -> bool:
        """Convert Dolby Vision video by re-encoding base layer and re-injecting RPU.

        This workflow:
        1. Extracts RPU metadata from original video
        2. Extracts base layer (HEVC without RPU)
        3. Muxes base layer into MKV with original audio/subtitles
           -> Deletes base layer HEVC
        4. Re-encodes the base layer with FFmpeg
           -> Deletes base layer MKV
        5. Extracts encoded HEVC from MKV
        6. Injects original RPU back into encoded HEVC
           -> Deletes encoded HEVC without RPU
           -> Deletes RPU file
        7. Muxes final video with audio/subtitles into target file
           -> Deletes encoded HEVC with RPU
           -> Deletes encoded base layer MKV
        8. Cleans up temporary directory

        All intermediate files are stored in a temporary directory and deleted
        incrementally as soon as they are no longer needed to minimize disk usage.

        Args:
            progress_callback: Optional progress handler callback
            finish_callback: Optional finish callback

        Returns:
            True if conversion succeeded, False otherwise
        """
        only_hdr10_or_sdr_encoding: bool = not self.is_dolby_vision_encoding()

        input_file = self.video.get_filepath()

        # Create temporary directory for all intermediate files
        temp_dir = self._get_temp_directory()

        # Step 1: Extract base layer (HEVC without RPU) from original video
        base_layer_hevc_path: str = dolby_vision.extract_base_layer(
            input_file=str(input_file),
            output_hevc=str(temp_dir / f"video_BL.hevc")
        )

        # Step 2: Mux base layer HEVC with original audio/subtitles into temporary MKV
        # This creates a playable MKV file with base layer video + original audio/subs
        base_layer_mkv_path: str = mkv.mux_hevc_to_mkv(
            input_hevc=base_layer_hevc_path,
            input_mkv=str(input_file),
            output_mkv=str(temp_dir / f"video_BL.mkv")
        )

        # Cleanup: Delete base layer HEVC (no longer needed after muxing)
        Path(base_layer_hevc_path).unlink(missing_ok=True)

        # Step 3: Re-encode the base layer MKV with FFmpeg (apply CRF, filters, etc.)
        encoded_base_layer_mkv = temp_dir / f"video_BL_Encoded.mkv"

        # For HDR10 or SDR encoding, we can write directly to target file
        if only_hdr10_or_sdr_encoding:
            encoded_base_layer_mkv = self.target_file

        encoding_success: bool = self._start_ffmpeg_process(
            input_file=Path(base_layer_mkv_path),
            target_file=encoded_base_layer_mkv,
            progress_callback=progress_callback,
            finish_callback=finish_callback,
        )

        if not encoding_success:
            return False

        # Cleanup: Delete base layer MKV (no longer needed after encoding)
        Path(base_layer_mkv_path).unlink(missing_ok=True)

        # For HDR10 or SDR encoding, we are done here
        if only_hdr10_or_sdr_encoding:
            self._cleanup_temp_directory()
            return True

        print()

        # Step 4: Extract encoded HEVC video stream from MKV
        encoded_hevc_path: str = mkv.extract_hevc(
            input_mkv=str(encoded_base_layer_mkv),
            output_hevc=str(temp_dir / f"video_BL_Encoded.hevc")
        )

        # Step 5: Extract RPU metadata from original Dolby Vision video
        rpu_file_path: str = dolby_vision.extract_rpu(
            input_file=str(input_file),
            output_rpu=str(temp_dir / f"RPU.rpu")
        )

        # Step 6: Inject original RPU metadata back into encoded HEVC
        encoded_hevc_with_rpu_path: str = dolby_vision.inject_rpu(
            input_file=encoded_hevc_path,
            input_rpu=rpu_file_path,
            output_hevc=str(temp_dir / f"video_BL_Encoded_RPU.hevc")
        )

        # Cleanup: Delete encoded HEVC without RPU (no longer needed after RPU injection)
        Path(encoded_hevc_path).unlink(missing_ok=True)
        # Cleanup: Delete RPU file (no longer needed after injection)
        Path(rpu_file_path).unlink(missing_ok=True)

        # Step 7: Mux final HEVC (with RPU) + audio/subtitles into target file
        mkv.mux_hevc_to_mkv(
            input_hevc=encoded_hevc_with_rpu_path,
            input_mkv=str(encoded_base_layer_mkv),
            output_mkv=str(self.target_file),
        )

        # Step 8: Clean up temporary directory (should be empty now, but removes it anyway)
        self._cleanup_temp_directory()

        return True

    def convert(
        self,
        progress_callback: Optional[Callable] = None,
        finish_callback: Optional[Callable] = None,
    ) -> bool:
        success: bool = False
        if self.video.is_dolby_vision_video():
            success: bool = self.convert_dolby_vision(
                progress_callback=progress_callback,
                finish_callback=finish_callback
            )
        else:
            success: bool = self.convert_sdr_hdr10(
                progress_callback=progress_callback,
                finish_callback=finish_callback
            )
        return success
