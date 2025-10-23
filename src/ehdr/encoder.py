"""Video encoder configuration and parameter building."""

import math
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from ffmpeg import FFmpeg

from ehdr.container import mkv
from ehdr.typedefs.encoder_typing import HdrSdrFormat, CropHandler, EncoderSettings, ScaleMode, VideoCodec, VideoEncoderLibrary
from ehdr.typedefs.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionProfile, DolbyVisionProfileEncodingMode
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
        settings: EncoderSettings,
        crop_callback: Optional[Callable[[CropHandler], None]] = None,
    ):
        """Initialize encoder with video and encoder settings.

        Args:
            video: Video object with metadata
            target_file: Target output file path
            settings: Encoder settings containing all encoding parameters
            crop_callback: Optional callback for crop detection progress
        """
        self._video: Video = video
        self._target_file: Path = target_file
        self._target_video_codec: VideoCodec = settings.video_codec

        # Determine effective color format
        self._target_hdr_sdr_format: HdrSdrFormat = self._determine_effective_hdr_sdr_format(
            hdr_sdr_format=settings.hdr_sdr_format
        )

        # Dolby Vision profile (only relevant if encoding to DV)
        self._target_dv_profile: Optional[DolbyVisionProfile] = self._determine_dv_profile(
            dv_profile=settings.target_dv_profile
        )
        self._target_dv_el: DolbyVisionEnhancementLayer | None = self._determine_dv_enhancement_layer(
            target_dv_profile=self._target_dv_profile,
        )

        # Crop dimensions (initialized to full frame)
        self._crop_width: int = video.width
        self._crop_height: int = video.height
        self._crop_x = 0
        self._crop_y = 0

        # Apply cropping if enabled (not supported for Dolby Vision)
        if settings.enable_crop:
            self._crop_video(callback=crop_callback)

        # Scale dimensions
        self._scale_width: Optional[int]
        self._scale_height: Optional[int]
        self._scale_width, self._scale_height = self._determine_scale_width_height(
            scale_mode=settings.scale_mode,
            new_height=settings.scale_height,
        )

        # Calculate or use provided CRF and preset
        self._crf: int = settings.crf if settings.crf is not None else self._get_auto_crf()
        self._preset: str = settings.preset if settings.preset is not None else self._get_auto_preset()

    def get_encoding_resolution(self) -> Tuple[int, int]:
        if self._scale_width and self._scale_height:
            return self._scale_width, self._scale_height

        if self._is_cropped():
            return self._crop_width, self._crop_height
        return self._video.width, self._video.height

    def _determine_scale_width_height(
        self,
        scale_mode: ScaleMode = ScaleMode.HEIGHT,
        new_height: Optional[int] = None,
    ) -> Tuple[Optional[int], Optional[int]]:
        """Get target scale dimensions if scaling is enabled.

        Returns:
            Tuple of (width, height) or None if scaling is not applied
        """
        if new_height is None or new_height > self._video.height:
            return None, None

        orginal_aspect_ratio: float = self._video.width / self._video.height
        new_scale_width = math.ceil(new_height * orginal_aspect_ratio)
        new_scale_height = new_height

        def __check_rounding(w: int, h: int) -> Tuple[int, int]:
            new_w: int = w
            new_h: int = h
            if w % 2 != 0:
                new_w -= 1
            if h % 2 != 0:
                new_h -= 1

            return new_w, new_h

        if self._is_cropped() is False:
            return __check_rounding(new_scale_width, new_scale_height)

        new_aspect_ratio: float = self._crop_width / self._crop_height

        if scale_mode == ScaleMode.HEIGHT:
            # scale-mode height

            height: int
            if self._crop_height < new_scale_height:
                height = self._crop_height
            else:
                height = new_scale_height

            width: int = math.floor(height * new_aspect_ratio)

            return __check_rounding(width, height)

        if scale_mode == ScaleMode.ADAPTIVE:
            # scale-mode adaptive
            if self._crop_width > new_scale_width:
                new_scale_height = math.floor(new_scale_width / new_aspect_ratio)
                return (new_scale_width, new_scale_height)

            if self._crop_height > new_scale_height:
                new_scale_width = math.ceil(new_scale_height * new_aspect_ratio)
                return (new_scale_width, new_scale_height)

            return __check_rounding(self._crop_width, self._crop_height)

        return None, None

    def _determine_dv_enhancement_layer(
        self,
        target_dv_profile: Optional[DolbyVisionProfile],
    ) -> Optional[DolbyVisionEnhancementLayer]:
        """Determine the Dolby Vision Enhancement Layer for encoding.

        Args:
            target_dv_profile: Desired Dolby Vision profile for encoding
            source_el: Source video's Enhancement Layer
        """
        if not self.is_dolby_vision_encoding():
            return None

        if target_dv_profile == DolbyVisionProfile._7:
            source_el: DolbyVisionEnhancementLayer | None = self._video.get_dolby_vision_enhancement_layer()
            source_profile: DolbyVisionProfile | None = self._video.get_dolby_vision_profile()
            if source_el is not None and source_profile == DolbyVisionProfile._7:
                return source_el

        return None

    def _determine_effective_hdr_sdr_format(self, hdr_sdr_format: HdrSdrFormat) -> HdrSdrFormat:
        """Determine the effective color format based on target and source.

        Only downgrades are allowed (DV→HDR10→SDR). Upgrades are not possible.

        Returns:
            Effective ColorFormat to use for encoding
        """
        # Determine source format
        if self._video.is_dolby_vision_video():
            source_format = HdrSdrFormat.DOLBY_VISION
        elif self._video.is_hdr_video():
            source_format = HdrSdrFormat.HDR10
        else:
            source_format = HdrSdrFormat.SDR

        if hdr_sdr_format == HdrSdrFormat.AUTO:
            # Auto mode: keep source format
            return source_format

        # Check if conversion is valid (only downgrades allowed)
        format_hierarchy = {
            HdrSdrFormat.SDR: 0,
            HdrSdrFormat.HDR10: 1,
            HdrSdrFormat.DOLBY_VISION: 2
        }

        source_level = format_hierarchy[source_format]
        target_level = format_hierarchy[hdr_sdr_format]

        if target_level > source_level:
            # Attempting upgrade - not allowed, keep source
            print(f"Warning: Cannot upgrade from {source_format.value} to {hdr_sdr_format.value}. Keeping source format.")
            return source_format

        # Valid downgrade
        return hdr_sdr_format

    def _determine_dv_profile(self, dv_profile: DolbyVisionProfileEncodingMode) -> Optional[DolbyVisionProfile]:
        """Determine the Dolby Vision profile for encoding.

        Args:
            dv_profile: Desired Dolby Vision profile (AUTO, 8)

        Returns:
            Effective DolbyVisionProfile or None if not applicable
        """
        if not self.is_dolby_vision_encoding():
            return None

        source_dv_profile: DolbyVisionProfile | None = self._video.get_dolby_vision_profile()
        if source_dv_profile is None:
            return None

        if dv_profile == DolbyVisionProfileEncodingMode.AUTO:
            return source_dv_profile

        return DolbyVisionProfile._8

    def get_encoding_dolby_vision_profile(self) -> Optional[DolbyVisionProfile]:
        """Get the Dolby Vision profile number for encoding.

        Returns:
            Dolby Vision profile or None if not applicable
        """
        return self._target_dv_profile

    def get_encoding_dolby_vision_enhancement_layer(self) -> Optional[DolbyVisionEnhancementLayer]:
        """Get the Dolby Vision Enhancement Layer for encoding.

        Returns:
            DolbyVisionEnhancementLayer or None if not applicable
        """
        return self._target_dv_el

    def get_encoding_video_codec(self) -> VideoCodec:
        """Get the video codec to be used for encoding.

        Returns:
            VideoCodec enum value
        """
        return self._target_video_codec

    def get_encoding_hdr_sdr_format(self) -> HdrSdrFormat:
        """Get the effective color format for encoding.

        Returns:
            Effective ColorFormat
        """
        return self._target_hdr_sdr_format

    def is_dolby_vision_encoding(self) -> bool:
        """Check if encoding to Dolby Vision format."""
        return self._target_hdr_sdr_format == HdrSdrFormat.DOLBY_VISION

    def is_hdr10_encoding(self) -> bool:
        """Check if encoding to HDR10 format."""
        return self._target_hdr_sdr_format == HdrSdrFormat.HDR10

    def is_sdr_encoding(self) -> bool:
        """Check if encoding to SDR format."""
        return self._target_hdr_sdr_format == HdrSdrFormat.SDR

    def _is_cropped(self) -> bool:
        """Check if video has cropping applied.

        Returns:
            True if cropping is applied, False otherwise
        """
        return (self._crop_width != self._video.width or
                self._crop_height != self._video.height or
                self._crop_x != 0 or
                self._crop_y != 0)

    def _get_pixel_count(self) -> int:
        """Get total pixel count considering scale and crop.

        Returns:
            Total number of pixels for encoding
        """
        if self._scale_width and self._scale_height:
            return self._scale_width * self._scale_height

        return self._video.width * self._video.height

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
            '-i', str(self._video._filepath),
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

    def _crop_video(
        self,
        num_threads: int = 10,
        callback: Optional[Callable[[CropHandler], None]] = None,
    ) -> None:
        """Detect and apply optimal crop parameters using multi-threaded analysis.

        Args:
            num_threads: Number of concurrent threads for crop detection
            callback: Optional callback function for progress updates
        """
        if (
            self.is_dolby_vision_encoding() or
            self._target_video_codec == VideoCodec.COPY
        ):
            return

        if callback:
            callback(CropHandler(
                finish_progress=False,
                completed_samples=0,
                total_samples=num_threads,
            ))

        # Get video duration
        duration = self._video.get_duration_seconds()

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

        self._crop_width, self._crop_height, self._crop_x, self._crop_y = most_common_crop

    def get_crop_filter(self) -> Optional[str]:
        """Get ffmpeg crop filter string if cropping is needed.

        Returns:
            Crop filter string or None if no cropping needed
        """
        if self._is_cropped():
            return f"crop={self._crop_width}:{self._crop_height}:{self._crop_x}:{self._crop_y}"
        return None

    def get_scale_filter(self) -> Optional[str]:
        """Get ffmpeg scale filter string if scaling is needed.

        Returns:
            Scale filter string or None if no scaling needed
        """
        if self._scale_width and self._scale_height:
            return f"scale={self._scale_width}:{self._scale_height}"
        return None

    def get_target_file(self) -> Path:
        """Get the target output file path.

        Returns:
            Target file Path
        """
        return self._target_file

    def _get_temp_directory(self) -> Path:
        """Get or create temporary directory for intermediate files.

        Creates a temp directory in the same location as target_file:
        {target_file_dir}/.ehdr_temp_{target_file_stem}/

        Returns:
            Path to temporary directory
        """
        temp_dir = self._target_file.parent / f".ehdr_temp_{self._target_file.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def _cleanup_temp_directory(self) -> None:
        """Remove temporary directory and all its contents.

        Deletes the temp directory created by _get_temp_directory().
        Handles errors gracefully and prints warnings if cleanup fails.
        """
        import shutil

        temp_dir = self._target_file.parent / f".ehdr_temp_{self._target_file.stem}"

        if temp_dir.exists() and temp_dir.is_dir():
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary files: {temp_dir}")
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory {temp_dir}: {e}")

    def get_encoding_video_library(self) -> VideoEncoderLibrary:
        """Get the FFmpeg video codec library string.

        Returns:
            FFmpeg video codec library name
        """
        if self._target_video_codec == VideoCodec.X265:
            return VideoEncoderLibrary.LIBX265
        elif self._target_video_codec == VideoCodec.COPY:
            return VideoEncoderLibrary.COPY
        else:
            raise ValueError(f"Unsupported video codec: {self._target_video_codec}")

    def _build_ffmpeg_output_options(self) -> Dict[str, str]:
        """Build FFmpeg output options dictionary for encoding.

        Returns:
            Dictionary of FFmpeg output options
        """
        codec_lib: VideoEncoderLibrary = self.get_encoding_video_library()
        output_options: dict = {
            'c:v': codec_lib.value,
        }

        if codec_lib != VideoCodec.COPY:
            output_options.update({
                'preset': self._preset,
                'crf': str(self._crf),
            })

        output_options.update({
            'c:a': 'copy',
            'c:s': 'copy'
        })

        if codec_lib == VideoCodec.COPY:
            return output_options

        # Add video filters (crop and scale), Only for SDR/HDR10 encoding
        if self.is_dolby_vision_encoding() is False:
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
            if self._video.is_hdr_video():
                # Tone mapping for HDR to SDR conversion
                output_options['vf'] = (
                    (output_options.get('vf', '') + ',') if 'vf' in output_options else ''
                ) + 'zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p'

        return output_options

    def _build_hdr_x265_params(self) -> list[str]:
        """Build x265 parameters for HDR10 video encoding.

        Returns:
            list of x265 parameter strings
        """
        params: list[str] = self.HDR_X265_PARAMS.copy()

        master_display = self._video.get_master_display()
        if master_display:
            params.append(f'master-display={master_display}')

            max_cll_max_fall: Tuple[int, int] | None = self._video.get_max_cll_max_fall()
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
        if self._video.is_hdr_video():
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

    def _run_ffmpeg_encoding_process(
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
            output_options: dict = self._build_ffmpeg_output_options()
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
        input_file = self._video.get_filepath()

        return self._run_ffmpeg_encoding_process(
            input_file=input_file,
            target_file=self._target_file,
            progress_callback=progress_callback,
            finish_callback=finish_callback,
        )

    def convert_dolby_vision_to_hdr10_without_re_encoding(
        self,
    ) -> bool:
        input_file: Path = self._video.get_filepath()

        # Create temporary directory for all intermediate files
        temp_dir: Path = self._get_temp_directory()

        # Step 1: Extract base layer (HEVC without EL+RPU) from original video
        base_layer_hevc_path: Path = dolby_vision.extract_base_layer(
            input_path=input_file,
            output_hevc=temp_dir / f"video_BL.hevc"
        )

        # Step 2: Mux base layer HEVC with original audio/subtitles into final MKV
        # This creates a playable MKV file with base layer video + original audio/subs
        _base_layer_mkv_path: Path = mkv.mux_hevc_to_mkv(
            input_hevc_path=base_layer_hevc_path,
            input_mkv=input_file,
            output_mkv=self._target_file,
        )

        self._cleanup_temp_directory()

        return True

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

        input_file: Path = self._video.get_filepath()

        # Create temporary directory for all intermediate files
        temp_dir: Path = self._get_temp_directory()

        # Step 1: Extract base layer (HEVC without RPU) from original video
        base_layer_hevc_path: Path = dolby_vision.extract_base_layer(
            input_path=input_file,
            output_hevc=temp_dir / f"video_BL.hevc",
        )

        # Step 2: Mux base layer HEVC with original audio/subtitles into temporary MKV
        # This creates a playable MKV file with base layer video + original audio/subs
        base_layer_mkv_path: Path = mkv.mux_hevc_to_mkv(
            input_hevc_path=base_layer_hevc_path,
            input_mkv=input_file,
            output_mkv=temp_dir / f"video_BL.mkv",
        )

        # Cleanup: Delete base layer HEVC (no longer needed after muxing)
        base_layer_hevc_path.unlink(missing_ok=True)

        # Step 3: Re-encode the base layer MKV with FFmpeg (apply CRF, filters, etc.)
        encoded_base_layer_mkv: Path = temp_dir / f"video_BL_Encoded.mkv"

        # For HDR10 or SDR encoding, we can write directly to target file
        if only_hdr10_or_sdr_encoding:
            encoded_base_layer_mkv = self._target_file

        encoding_success: bool = self._run_ffmpeg_encoding_process(
            input_file=Path(base_layer_mkv_path),
            target_file=encoded_base_layer_mkv,
            progress_callback=progress_callback,
            finish_callback=finish_callback,
        )
        # Cleanup: Delete base layer MKV (no longer needed after encoding)
        base_layer_mkv_path.unlink(missing_ok=True)

        if not encoding_success:
            return False

        # For HDR10 or SDR encoding, we are done here
        if only_hdr10_or_sdr_encoding:
            self._cleanup_temp_directory()
            return True

        print()

        # Step 4: Extract encoded HEVC video stream from MKV
        encoded_hevc_bl_path: Path = mkv.extract_hevc(
            input_path=encoded_base_layer_mkv,
            output_hevc=temp_dir / f"video_encoded_BL.hevc"
        )

        # Step 5: Extract RPU metadata from original Dolby Vision video
        rpu_file_path: Path = dolby_vision.extract_rpu(
            input_path=self._video.get_filepath(),
            output_rpu=temp_dir / f"RPU.rpu",
            dv_profile_source=self._video.get_dolby_vision_profile(),
            dv_profile_encoding=self._target_dv_profile
        )

        # Setup 5.1: If AUTO profile and source is profile 7, demux EL profile 7 RPU
        if self._target_dv_el is not None:
            # start demux EL profile 7 for profile 7 encoding
            el_path: Path = dolby_vision.extract_enhancement_layer(
                input_file=input_file,
                output_el=temp_dir / f"video_EL.hevc",
            )
            bl_el_hevc: Path = dolby_vision.inject_dolby_vision_layers(
                bl_path=encoded_hevc_bl_path,
                el_path=el_path,
                output_bl_el=temp_dir / f"video_encoded_BL_EL.hevc",
            )
            encoded_hevc_bl_path.unlink(missing_ok=True)
            encoded_hevc_bl_path = bl_el_hevc

        # Step 6: Inject original RPU metadata back into encoded HEVC
        encoded_hevc_with_rpu_path: Path = dolby_vision.inject_rpu(
            input_path=encoded_hevc_bl_path,
            input_rpu=rpu_file_path,
            output_hevc=temp_dir / f"video_encoded_BL_{'EL_' if self._target_dv_el else ''}RPU.hevc"
        )

        # Cleanup: Delete encoded HEVC without RPU (no longer needed after RPU injection)
        encoded_hevc_bl_path.unlink(missing_ok=True)

        # Step 7: Mux final HEVC (with RPU) + audio/subtitles into target file
        mkv.mux_hevc_to_mkv(
            input_hevc_path=encoded_hevc_with_rpu_path,
            input_mkv=encoded_base_layer_mkv,
            output_mkv=self._target_file,
        )

        # Step 8: Clean up temporary directory (should be empty now, but removes it anyway)
        self._cleanup_temp_directory()

        return True

    def convert(
        self,
        progress_callback: Optional[Callable] = None,
        finish_callback: Optional[Callable] = None,
    ) -> bool:
        if self._video.is_dolby_vision_video():

            # Convert Dolby Vision to HDR10, without re-encoding
            if (
                self.is_hdr10_encoding() and
                self.get_encoding_video_codec() == VideoCodec.COPY
            ):
                return self.convert_dolby_vision_to_hdr10_without_re_encoding()

            # Dolby Vision encoding workflow
            return self.convert_dolby_vision(
                progress_callback=progress_callback,
                finish_callback=finish_callback
            )

        return self.convert_sdr_hdr10(
            progress_callback=progress_callback,
            finish_callback=finish_callback
        )
