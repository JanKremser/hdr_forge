"""Video encoder configuration and parameter building."""

from pathlib import Path
import sys
import time
from typing import Dict, Optional, Tuple

from ehdr.cli.cli_output import create_progress_handler, finish_progress, print_err
from ehdr.ffmpeg_wrapper import run_ffmpeg
from ehdr.container import mkv
from ehdr.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from ehdr.ffmpeg.video_codec.libx264 import Libx264Codec
from ehdr.ffmpeg.video_codec.libx265 import Libx265Codec
from ehdr.typedefs.encoder_typing import HdrSdrFormat, EncoderSettings, SampleSettings, VideoCodec, VideoEncoderLibrary
from ehdr.typedefs.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionProfile, DolbyVisionProfileEncodingMode
from ehdr.hdr_formats import dolby_vision
from ehdr.video import Video


class Encoder:
    """Handles video encoding configuration for different color formats."""

    def __init__(
        self,
        video: Video,
        target_file: Path,
        settings: EncoderSettings,
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

        self._video_codec_lib: VideoCodecBase | None = self._get_video_codec_lib_instance(
            video=video,
            encoder_settings=settings,
            scale_tuple=(video.width, video.height),
        )

        # Dolby Vision profile (only relevant if encoding to DV)
        self._target_dv_profile: Optional[DolbyVisionProfile] = self._determine_dv_profile(
            dv_profile=settings.target_dv_profile
        )
        self._target_dv_el: DolbyVisionEnhancementLayer | None = self._determine_dv_enhancement_layer(
            target_dv_profile=self._target_dv_profile,
        )

        #samples
        self._video_sample_in_sec: Optional[Tuple[int, int]] = self._determine_video_sample(
            sample_settings=settings.sample,
        )

    def _get_video_codec_lib_instance(
        self,
        encoder_settings: EncoderSettings,
        video: Video,
        scale_tuple: Tuple[int, int],
    ) -> VideoCodecBase | None:
        """Get the codec library instance based on target video codec.

        Args:
            encoder_settings: EncoderSettings object with encoding parameters

        Returns:
            VideoCodecBase instance for the selected video codec
        """
        if encoder_settings.video_codec == VideoCodec.X265:
            return Libx265Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
        elif encoder_settings.video_codec == VideoCodec.X264:
            return Libx264Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)

        return None

    def get_video_codec_lib(self) -> VideoCodecBase | None:
        """Get the codec library instance.

        Returns:
            VideoCodecBase instance or None if copying
        """
        return self._video_codec_lib

    def _determine_video_sample(
        self,
        sample_settings: SampleSettings,
    ) -> Optional[Tuple[int, int]]:
        """Determine start and end times for video sampling.

        Args:
            sample_settings: SampleSettings object with sampling configuration
        Returns:
            Tuple of (start_time, end_time) in seconds or None if no sampling
        """
        if not sample_settings.enabled:
            return None

        if self.is_dolby_vision_encoding():
            print_err(msg="Video sampling is not supported for Dolby Vision encoding.")
            sys.exit(1)

        video_duration: float = self._video.get_duration_seconds()
        if video_duration <= 0:
            return None

        if sample_settings.start_time is not None and sample_settings.end_time is not None:
            start_time: float = max(0, min(sample_settings.start_time, video_duration))
            end_time: float = max(start_time, min(sample_settings.end_time, video_duration))
            return (int(start_time), int(end_time))

        # Auto sample: 30 seconds from middle of video
        mid_point: float = video_duration / 2
        start_time = max(0, mid_point - 15)
        end_time = min(video_duration, mid_point + 15)
        return (int(start_time), int(end_time))


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
        if self._video_codec_lib is None:
            return self._video.get_hdr_sdr_format()
        return self._video_codec_lib.get_encoding_hdr_sdr_format()

    def is_dolby_vision_encoding(self) -> bool:
        """Check if encoding to Dolby Vision format."""
        return self.get_encoding_hdr_sdr_format() == HdrSdrFormat.DOLBY_VISION

    def is_hdr10_encoding(self) -> bool:
        """Check if encoding to HDR10 format."""
        return self.get_encoding_hdr_sdr_format() == HdrSdrFormat.HDR10

    def is_sdr_encoding(self) -> bool:
        """Check if encoding to SDR format."""
        return self.get_encoding_hdr_sdr_format() == HdrSdrFormat.SDR

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
        elif self._target_video_codec == VideoCodec.X264:
            return VideoEncoderLibrary.LIBX264
        elif self._target_video_codec == VideoCodec.COPY:
            return VideoEncoderLibrary.COPY
        else:
            print_err(f"Unsupported video codec: {self._target_video_codec}")
            sys.exit(1)

    def _build_ffmpeg_output_options(self) -> Dict[str, str]:
        """Build FFmpeg output options dictionary for encoding.

        Returns:
            Dictionary of FFmpeg output options
        """
        output_options: dict = {}

        if self._video_codec_lib:
            output_options.update(self._video_codec_lib.get_ffmpeg_params())
        else:
            output_options.update({
                'c:v': 'copy',
            })

        output_options.update({
            'c:a': 'copy',
            'c:s': 'copy'
        })

        if self._video_sample_in_sec is not None:
            start_time, end_time = self._video_sample_in_sec
            output_options['ss'] = str(start_time)
            output_options['t'] = str(end_time-start_time)

        return output_options

    def _run_ffmpeg_encoding_process(
        self,
        input_file: Path,
        target_file: Path,
    ):
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None
        finish_callback = None

        process_start_time = time.time()

        if duration > 0:
            progress_callback = create_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
            )
            finish_callback = lambda: finish_progress(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
            )

        try:
            # Build output options
            output_options: dict = self._build_ffmpeg_output_options()

            # Debug output
            debug_ffmpeg = ' '.join(f"-{k} {v}" for k, v in output_options.items())
            print(f"ffmpeg command: ffmpeg -y -i {input_file} {debug_ffmpeg} {target_file}")

            # Execute FFmpeg with progress tracking
            success = run_ffmpeg(
                input_file=input_file,
                output_file=target_file,
                output_options=output_options,
                progress_callback=progress_callback
            )

            # Call finish callback if provided and successful
            if success and finish_callback:
                finish_callback()

            return success

        except Exception as e:
            print(f"Error during encoding: {e}")
            return False

    def convert_sdr_hdr10(
        self,
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
    ) -> bool:
        if self._video.is_dolby_vision_video():

            # Convert Dolby Vision to HDR10, without re-encoding
            if (
                self.is_hdr10_encoding() and
                self.get_encoding_video_codec() == VideoCodec.COPY
            ):
                return self.convert_dolby_vision_to_hdr10_without_re_encoding()

            # Dolby Vision encoding workflow
            return self.convert_dolby_vision()

        return self.convert_sdr_hdr10()
