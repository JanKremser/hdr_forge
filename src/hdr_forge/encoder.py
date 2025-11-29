"""Video encoder configuration and parameter building."""

from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, Optional, Tuple

from hdr_forge.cli.cli_output import create_ffmpeg_progress_handler, print_debug, print_err
from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.core.service import build_ffmpeg_cmd_dict_to_str
from hdr_forge.tools import mkvmerge
from hdr_forge.ffmpeg.ffmpeg_wrapper import run_ffmpeg
from hdr_forge.ffmpeg.video_codec.h264_nvenc import H264NvencCodec
from hdr_forge.ffmpeg.video_codec.hevc_nvenc import HevcNvencCodec
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.ffmpeg.video_codec.libx264 import Libx264Codec
from hdr_forge.ffmpeg.video_codec.libx265 import Libx265Codec
from hdr_forge.ffmpeg.video_codec.libsvtav1 import LibSvtAV1Codec
from hdr_forge.tools import dovi_tool
from hdr_forge.typedefs.encoder_typing import EncoderOverride, HdrSdrFormat, EncoderSettings, SampleSettings, VideoCodec, VideoEncoderLibrary
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionProfile, DolbyVisionProfileEncodingMode
from hdr_forge.video import Video


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
        self.temp_dir: Path = get_global_temp_directory()

        self._video: Video = video
        self._target_file: Path = target_file
        self._target_video_codec: VideoCodec = settings.video_codec
        self._encoder_settings: EncoderSettings = settings

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

    def get_available_hw_encoders(self) -> list[VideoEncoderLibrary]:
        """
        Gibt eine Liste von Enum-Mitgliedern zurück, deren Encoder
        auf dem System über FFmpeg verfügbar sind UND Hardware-beschleunigt sind.

        :param enum_class: Enum-Klasse, z. B. VideoEncoderLibrary
        :return: Liste der Enum-Mitglieder, die verfügbar und HW-Encoder sind
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                check=True
            )

            lines = result.stdout.splitlines()
            available_hw_encoders = set()

            for line in lines:
                if line.startswith(" V"):
                    parts = line.split()
                    if len(parts) > 1:
                        encoder_name = parts[1]
                        # typische HW-Kennzeichen
                        if any(hw in encoder_name for hw in ["nvenc", "qsv", "vaapi", "amf", "v4l2"]):
                            available_hw_encoders.add(encoder_name)

            result_members: list[VideoEncoderLibrary] = [
                member
                for member in VideoEncoderLibrary
                if member.value in available_hw_encoders
            ]

            return result_members

        except subprocess.CalledProcessError as e:
            print("Fehler beim Abfragen der Encoder:", e)
            return []


    def _get_video_codec_lib_instance(
        self,
        encoder_settings: EncoderSettings,
        video: Video,
        scale_tuple: Tuple[int, int],
    ) -> VideoCodecBase | None:
        """Get the codec library instance based on encoder override or automatic selection.

        Priority:
            1. encoder_override (if not AUTO)
            2. video_codec + enable_gpu_acceleration (automatic selection)

        Args:
            encoder_settings: EncoderSettings object with encoding parameters

        Returns:
            VideoCodecBase instance for the selected video codec
        """
        # Priority 1: Check encoder_override
        if encoder_settings.encoder_override != EncoderOverride.AUTO:
            return self._get_codec_from_override(encoder_settings, video, scale_tuple)

        # Priority 2: Automatic selection based on video_codec and GPU acceleration
        if encoder_settings.video_codec == VideoCodec.H265:
            if encoder_settings.enable_gpu_acceleration:
                test: list[VideoEncoderLibrary] = self.get_available_hw_encoders()
                if VideoEncoderLibrary.HEVC_NVENC in test:
                    return HevcNvencCodec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
                else:
                    print_err("Only NVENC hardware acceleration is supported currently.")
                    sys.exit(1)
            else:
                return Libx265Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
        elif encoder_settings.video_codec == VideoCodec.H264:
            if encoder_settings.enable_gpu_acceleration:
                test: list[VideoEncoderLibrary] = self.get_available_hw_encoders()
                if VideoEncoderLibrary.H264_NVENC in test:
                    return H264NvencCodec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
                else:
                    print_err("Only NVENC hardware acceleration is supported currently.")
                    sys.exit(1)
            else:
                return Libx264Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)

        return None

    def _get_codec_from_override(
        self,
        encoder_settings: EncoderSettings,
        video: Video,
        scale_tuple: Tuple[int, int],
    ) -> VideoCodecBase | None:
        """Get codec instance based on encoder override.

        Args:
            encoder_settings: EncoderSettings object with encoding parameters
            video: Video object
            scale_tuple: Scale dimensions tuple

        Returns:
            VideoCodecBase instance for the overridden encoder
        """
        override = encoder_settings.encoder_override

        if override == EncoderOverride.LIBX265:
            return Libx265Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)

        elif override == EncoderOverride.LIBX264:
            return Libx264Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)

        elif override == EncoderOverride.HEVC_NVENC:
            available_encoders = self.get_available_hw_encoders()
            if VideoEncoderLibrary.HEVC_NVENC in available_encoders:
                return HevcNvencCodec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
            else:
                print_err("Error: HEVC NVENC encoder not available on this system.")
                sys.exit(1)

        elif override == EncoderOverride.H264_NVENC:
            available_encoders = self.get_available_hw_encoders()
            if VideoEncoderLibrary.H264_NVENC in available_encoders:
                return H264NvencCodec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
            else:
                print_err("Error: H264 NVENC encoder not available on this system.")
                sys.exit(1)

        elif override == EncoderOverride.LIBSVTAV1:
            return LibSvtAV1Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)

        return None

    def get_video_codec_lib(self) -> VideoCodecBase | None:
        """Get the codec library instance.

        Returns:
            VideoCodecBase instance or None if copying
        """
        return self._video_codec_lib

    def get_encoder_settings(self) -> EncoderSettings:
        """Get the encoder settings.

        Returns:
            EncoderSettings object
        """
        return self._encoder_settings

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

        # Auto sample: 30 seconds starting at 1 minute
        start_time = min(video_duration, 60)
        end_time = min(video_duration, 60 + 30)
        if start_time == video_duration:
            start_time = 0
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
            if self._video.get_hdr_sdr_format() == HdrSdrFormat.DOLBY_VISION and self._encoder_settings.hdr_sdr_format == HdrSdrFormat.HDR10:
                return HdrSdrFormat.HDR10
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

    def _build_ffmpeg_output_options(self) -> Dict[str, str]:
        """Build FFmpeg output options dictionary for encoding.

        Returns:
            Dictionary of FFmpeg output options
        """
        output_options: dict = {
            "map": "0",
        }

        if self._video_sample_in_sec is not None:
            start_time, end_time = self._video_sample_in_sec
            output_options['ss'] = str(start_time)
            output_options['t'] = str(end_time-start_time)

        if self._video_codec_lib:
            output_options = self._video_codec_lib.get_ffmpeg_params(exist_params=output_options)
        else:
            output_options.update({
                'c:v': 'copy',
            })

        output_options.update({
            'c:a': 'copy',
            'c:s': 'copy'
        })

        return output_options

    def _run_ffmpeg_encoding_process(
        self,
        input_file: Path,
        target_file: Path,
    ):
        total_frames = self._video.get_total_frames()
        duration = self._video.get_duration_seconds()

        progress_callback = None

        process_start_time: float = time.time()

        if duration > 0:
            progress_callback = create_ffmpeg_progress_handler(
                duration=duration,
                total_frames=total_frames,
                process_start_time=process_start_time,
                video_fps=self._video.get_fps(),
            )

        try:
            # Build output options
            output_options: dict = self._build_ffmpeg_output_options()

            # Debug output
            debug_ffmpeg: str = build_ffmpeg_cmd_dict_to_str(output_options)
            print_debug(f'Run command: ffmpeg -y -i "{input_file}" {debug_ffmpeg} "{target_file}"')

            # Execute FFmpeg with progress tracking
            success: bool = run_ffmpeg(
                input_file=input_file,
                output_file=target_file,
                output_options=output_options,
                progress_callback=progress_callback
            )
            print()

            return success

        except Exception as e:
            print_err(f"Error during encoding: {e}")
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
        input_file: Path = self._video.get_filepath()

        return self._run_ffmpeg_encoding_process(
            input_file=input_file,
            target_file=self._target_file,
        )

    def convert_dolby_vision_to_hdr10_without_re_encoding(
        self,
    ) -> bool:
        input_file: Path = self._video.get_filepath()
        total_frames: int = self._video.get_total_frames()
        duration: int = self._video.get_total_frames()

        # Step 1: Extract base layer (HEVC without EL+RPU) from original video
        base_layer_hevc_path: Path = dovi_tool.extract_base_layer(
            input_path=input_file,
            output_hevc=self.temp_dir / f"video_BL.hevc",
            total_frames=total_frames,
            duration=duration,
        )

        # Step 2: Mux base layer HEVC with original audio/subtitles into final MKV
        # This creates a playable MKV file with base layer video + original audio/subs
        _base_layer_mkv_path: Path = mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=base_layer_hevc_path,
            input_mkv=input_file,
            output_mkv=self._target_file,
        )

        return True

    def _convert_dolby_profile(
        self,
        input_file: Path,
        hevc_bl: Path,
        source_dv_profile: DolbyVisionProfile | None,
        target_dv_profile: DolbyVisionProfile | None,
    ) -> Path:
        temp_dir: Path = self.temp_dir
        total_frames: int = self._video.get_total_frames()
        duration: int = self._video.get_total_frames()

        # Step 1: Extract RPU metadata from original Dolby Vision video
        rpu_file_path: Path = dovi_tool.extract_rpu(
            input_path=input_file,
            output_rpu=temp_dir / f"RPU.rpu",
            dv_profile_source=source_dv_profile,
            dv_profile_encoding=target_dv_profile,
            total_frames=total_frames,
            duration=duration,
            use_cache=True,
        )

        hevc: Path = hevc_bl
        # Setup 2: If AUTO profile and source is profile 7, demux EL profile 7 RPU
        if self._target_dv_el is not None:
            # start demux EL profile 7 for profile 7 encoding
            el_path: Path = dovi_tool.extract_enhancement_layer(
                input_path=input_file,
                output_el=temp_dir / f"video_EL.hevc",
                total_frames=total_frames,
                duration=duration,
            )
            bl_el_hevc: Path = dovi_tool.inject_dolby_vision_layers(
                bl_path=hevc_bl,
                el_path=el_path,
                output_bl_el=temp_dir / f"video_encoded_BL_EL.hevc",
            )
            hevc = bl_el_hevc

        # Step 3: Inject original RPU metadata back into encoded HEVC
        encoded_hevc_with_rpu_path: Path = dovi_tool.inject_rpu(
            input_path=hevc,
            input_rpu=rpu_file_path,
            output_hevc=temp_dir / f"video_encoded_BL_{'EL_' if self._target_dv_el else ''}RPU.hevc"
        )

        return encoded_hevc_with_rpu_path


    def convert_dolby_vision_to_other_profile_without_re_encoding(
        self,
    ) -> bool:
        input_file: Path = self._video.get_filepath()
        total_frames: int = self._video.get_total_frames()
        duration: int = self._video.get_total_frames()

        # Create temporary directory for all intermediate files
        temp_dir: Path = self.temp_dir

        # Step 1: Extract base layer (HEVC without RPU) from original video
        base_layer_hevc_path: Path = dovi_tool.extract_base_layer(
            input_path=input_file,
            output_hevc=temp_dir / f"video_BL.hevc",
            total_frames=total_frames,
            duration=duration,
        )

        # Step 2: Convert Dolby Vision profile by injecting RPU into base layer HEVC
        hevc_with_rpu: Path = self._convert_dolby_profile(
            input_file=input_file,
            hevc_bl=base_layer_hevc_path,
            source_dv_profile=self._video.get_dolby_vision_profile(),
            target_dv_profile=self._target_dv_profile,
        )

        # Step 3: Mux final HEVC (with RPU) + audio/subtitles into target file
        mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=hevc_with_rpu,
            input_mkv=input_file,
            output_mkv=self._target_file,
        )

        return True

    def convert_dolby_vision(
        self,
    ) -> bool:
        """Convert Dolby Vision video by re-encoding base layer and optionally re-injecting RPU or EL+RPU.

        This workflow:
        1. Extracts RPU metadata from the original video.
        2. Extracts the base layer (HEVC without RPU or EL).
        3. Muxes the base layer into MKV with original audio/subtitles.
           -> Deletes the base layer HEVC.
        4. Re-encodes the base layer with FFmpeg.
           -> Deletes the base layer MKV.
        5. Optionally extracts the Enhancement Layer (EL) for profile 7 encoding.
        6. Optionally injects EL into the encoded base layer.
        7. Injects RPU metadata back into the encoded HEVC.
           -> Deletes intermediate files like encoded HEVC without RPU or EL.
        8. Muxes the final HEVC (with RPU or EL+RPU) and audio/subtitles into the target file.
        9. Cleans up the temporary directory.

        All intermediate files are stored in a temporary directory and deleted
        incrementally as soon as they are no longer needed to minimize disk usage.

        Returns:
            True if conversion succeeded, False otherwise.
        """
        only_hdr10_or_sdr_encoding: bool = not self.is_dolby_vision_encoding()

        input_file: Path = self._video.get_filepath()
        total_frames: int = self._video.get_total_frames()
        duration: int = self._video.get_total_frames()

        # Create temporary directory for all intermediate files
        temp_dir: Path = self.temp_dir

        # Step 1: Extract base layer (HEVC without RPU) from original video
        base_layer_hevc_path: Path = dovi_tool.extract_base_layer(
            input_path=input_file,
            output_hevc=temp_dir / f"video_BL.hevc",
            total_frames=total_frames,
            duration=duration,
        )

        # Step 2: Mux base layer HEVC with original audio/subtitles into temporary MKV
        # This creates a playable MKV file with base layer video + original audio/subs
        base_layer_mkv_path: Path = mkvmerge.mux_hevc_to_mkv(
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
            return True

        print()

        # Step 4: Extract encoded HEVC video stream from MKV
        encoded_hevc_bl_path: Path = mkvmerge.extract_hevc(
            input_path=encoded_base_layer_mkv,
            output_hevc=temp_dir / f"video_encoded_BL.hevc",
            total_frames=total_frames,
            duration=duration,
        )

        # Step 5: Convert Dolby Vision profile by injecting RPU into encoded base layer HEVC
        hevc_with_rpu: Path = self._convert_dolby_profile(
            input_file=input_file,
            hevc_bl=encoded_hevc_bl_path,
            source_dv_profile=self._video.get_dolby_vision_profile(),
            target_dv_profile=self._target_dv_profile,
        )

        # Cleanup: Delete encoded HEVC without RPU (no longer needed after RPU injection)
        encoded_hevc_bl_path.unlink(missing_ok=True)

        # Step 6: Mux final HEVC (with RPU) + audio/subtitles into target file
        mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=hevc_with_rpu,
            input_mkv=encoded_base_layer_mkv,
            output_mkv=self._target_file,
        )

        return True

    def convert(
        self,
    ) -> bool:
        if self._video.is_dolby_vision_video():

            # Convert Dolby Vision to HDR10, without re-encoding
            if (self.get_encoding_video_codec() == VideoCodec.COPY):
                if (self.is_hdr10_encoding()):
                    return self.convert_dolby_vision_to_hdr10_without_re_encoding()
                elif (self.is_dolby_vision_encoding()):
                    return self.convert_dolby_vision_to_other_profile_without_re_encoding()

            # Dolby Vision encoding workflow
            return self.convert_dolby_vision()

        return self.convert_sdr_hdr10()
