"""Video encoder configuration and parameter building."""

from pathlib import Path
import sys
import time
from typing import Dict, Optional, Tuple

from hdr_forge.cli.cli_output import create_ffmpeg_progress_handler, print_err, print_warn
from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.tools import mkvmerge, mkvpropedit
from hdr_forge.tools.ffmpeg import query_available_hw_encoders, extract_hevc, run_ffmpeg
from hdr_forge.ffmpeg.video_codec.h264_nvenc import H264NvencCodec
from hdr_forge.ffmpeg.video_codec.hevc_nvenc import HevcNvencCodec
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.ffmpeg.video_codec.libx264 import Libx264Codec
from hdr_forge.ffmpeg.video_codec.libx265 import Libx265Codec
from hdr_forge.ffmpeg.video_codec.libsvtav1 import LibSvtAV1Codec
from hdr_forge.tools import dovi_tool
from hdr_forge.typedefs.codec_typing import VideoEncoderLibrary
from hdr_forge.typedefs.encoder_typing import AudioCodec, AudioCodecItem, EncoderConfigurationError, EncoderOverride, HdrSdrFormat, EncoderSettings, SampleSettings, SubtitleMode, SubtitleModeItem, SubtitleTrackAction, SubtitleTrackOverride, VideoCodec
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionInfo, DolbyVisionProfile, DolbyVisionProfileEncodingMode
from hdr_forge.typedefs.mkv_typing import MkvTrack
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
        self._video: Video = video
        self._target_file: Path = target_file
        self._target_video_codec: VideoCodec = settings.video_codec
        self._encoder_settings: EncoderSettings = settings
        self._hw_encoders_cache: list[VideoEncoderLibrary] | None = None

        # Effective HDR/SDR formats that will be present in the output (including base layer formats for DV)
        self._target_hdr_sdr_format: list[HdrSdrFormat] = self._determine_hdr_sdr_format()

        self._video_codec_lib: VideoCodecBase | None = self._get_video_codec_lib_instance(
            video=video,
            encoder_settings=settings,
            scale_tuple=(video.width, video.height),
        )

        # Dolby Vision profile (only relevant if encoding to DV)
        self._target_dv_profile: Optional[DolbyVisionProfile] = self._determine_dv_profile(
            dv_profile=settings.target_dv_profile
        )
        self._dv_el_present: bool | None = self._determine_dv_el_present(
            target_dv_profile=self._target_dv_profile,
        )

        #samples
        self._video_sample_in_sec: Optional[Tuple[int, int]] = self._determine_video_sample(
            sample_settings=settings.sample,
        )

    def get_available_hw_encoders(self) -> list[VideoEncoderLibrary]:
        """
        Returns a list of enum members whose encoders are available on the
        system via FFmpeg AND are hardware-accelerated.

        :return: List of enum members that are available and are HW encoders
        """
        if self._hw_encoders_cache is not None:
            return self._hw_encoders_cache

        self._hw_encoders_cache = query_available_hw_encoders()
        return self._hw_encoders_cache


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
                    raise EncoderConfigurationError("Only NVENC hardware acceleration is supported currently.")
            else:
                return Libx265Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
        elif encoder_settings.video_codec == VideoCodec.H264:
            if encoder_settings.enable_gpu_acceleration:
                test: list[VideoEncoderLibrary] = self.get_available_hw_encoders()
                if VideoEncoderLibrary.H264_NVENC in test:
                    return H264NvencCodec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
                else:
                    raise EncoderConfigurationError("Only NVENC hardware acceleration is supported currently.")
            else:
                return Libx264Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
        elif encoder_settings.video_codec == VideoCodec.AV1:
            if encoder_settings.enable_gpu_acceleration:
                raise EncoderConfigurationError("Hardware acceleration is not supported for AV1 encoding.")
            return LibSvtAV1Codec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
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
                raise EncoderConfigurationError("Error: HEVC NVENC encoder not available on this system.")

        elif override == EncoderOverride.H264_NVENC:
            available_encoders = self.get_available_hw_encoders()
            if VideoEncoderLibrary.H264_NVENC in available_encoders:
                return H264NvencCodec(encoder_settings=encoder_settings, video=video, scale=scale_tuple)
            else:
                raise EncoderConfigurationError("Error: H264 NVENC encoder not available on this system.")

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
            raise EncoderConfigurationError("Video sampling is not supported for Dolby Vision encoding.")

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


    def _determine_dv_el_present(
        self,
        target_dv_profile: Optional[DolbyVisionProfile],
    ) -> Optional[bool]:
        """Determine the Dolby Vision Enhancement Layer for encoding.

        Args:
            target_dv_profile: Desired Dolby Vision profile for encoding
            source_el: Source video's Enhancement Layer
        """
        if not self.is_dolby_vision_encoding():
            return None

        source_dv_profile: DolbyVisionProfile | None = self._video.get_dolby_vision_profile()
        if target_dv_profile == source_dv_profile:
            dv_info: DolbyVisionInfo | None = self._video.get_dolby_vision_info()
            if dv_info is not None and dv_info.dv_profile == DolbyVisionProfile._7.value:
                return dv_info.el_preset

        return False

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

        if dv_profile == DolbyVisionProfileEncodingMode.AUTO and self.get_encoding_video_codec() == VideoCodec.COPY:
            return source_dv_profile

        return DolbyVisionProfile._8

    def _determine_hdr_sdr_format(self) -> list[HdrSdrFormat]:
        """Determine the effective HDR/SDR formats that will be present in the output.

        This includes the primary format determined by the video codec and any additional formats
        that will be present due to Dolby Vision base layer encoding or HDR10+ preservation.

        Returns:
            List of HdrSdrFormat values representing all formats in the output
        """
        encoder_settings_formats: list[HdrSdrFormat] = [self._encoder_settings.hdr_sdr_format]

        # COPY mode: source formats pass through directly
        if self.get_encoding_video_codec() == VideoCodec.COPY:
            if HdrSdrFormat.DOLBY_VISION in self._video.get_hdr_sdr_format() and HdrSdrFormat.HDR10 in encoder_settings_formats:
                return [HdrSdrFormat.HDR10]
            return self._video.get_hdr_sdr_format()

        # Re-encoding: start with the codec's primary format and add secondary formats
        formats: list[HdrSdrFormat] = []

        video_formats: list[HdrSdrFormat] = self._video.get_hdr_sdr_format()
        if HdrSdrFormat.AUTO in encoder_settings_formats:
            encoder_settings_formats = video_formats

        if HdrSdrFormat.DOLBY_VISION in encoder_settings_formats:
            if HdrSdrFormat.DOLBY_VISION in video_formats:
                formats.append(HdrSdrFormat.DOLBY_VISION)
                dv_version: DolbyVisionProfile | None = self._video.get_dolby_vision_profile()
                if dv_version is not None and dv_version == DolbyVisionProfile._5:
                    # Profile 5: libplacebo tone-maps base layer to HDR, so add HDR as effective output format
                    formats.append(HdrSdrFormat.HDR)
                elif dv_version is not None and dv_version in (DolbyVisionProfile._7, DolbyVisionProfile._8):
                    # Profile 7/8: HDR10-compatible base layer, so add HDR10 as effective output format if source is HDR10 or HDR
                    if self._video.is_hdr10_video():
                        formats.append(HdrSdrFormat.HDR10)
                    elif self._video.is_hdr_video():
                        formats.append(HdrSdrFormat.HDR)
            else:
                raise EncoderConfigurationError("Cannot encode to Dolby Vision format because source video does not contain Dolby Vision.")
        if HdrSdrFormat.HDR10 in encoder_settings_formats and HdrSdrFormat.HDR10 not in formats:
            if HdrSdrFormat.HDR10 in video_formats:
                formats.append(HdrSdrFormat.HDR10)
            else:
                raise EncoderConfigurationError("Cannot encode to HDR10 format because source video does not contain HDR10.")
        if HdrSdrFormat.HDR in encoder_settings_formats and HdrSdrFormat.HDR not in formats:
            if HdrSdrFormat.HDR in video_formats or HdrSdrFormat.HDR10 in video_formats:
                formats.append(HdrSdrFormat.HDR)
            else:
                raise EncoderConfigurationError("Cannot encode to HDR format because source video does not contain HDR.")
        if HdrSdrFormat.SDR in encoder_settings_formats and HdrSdrFormat.SDR not in formats:
            if HdrSdrFormat.SDR in video_formats:
                formats.append(HdrSdrFormat.SDR)
            else:
                raise EncoderConfigurationError("Cannot encode to SDR format because source video does not contain SDR.")

        if (
            HdrSdrFormat.HDR10_PLUS in video_formats and
            HdrSdrFormat.SDR not in formats and
            HdrSdrFormat.HDR not in formats and
            HdrSdrFormat.HDR10_PLUS not in formats
        ):
            # HDR10+ is preserved during encoding if source has it and output is not SDR/plain HDR
            formats.append(HdrSdrFormat.HDR10_PLUS)

        return formats

    def get_encoding_dolby_vision_profile(self) -> Optional[DolbyVisionProfile]:
        """Get the Dolby Vision profile number for encoding.

        Returns:
            Dolby Vision profile or None if not applicable
        """
        return self._target_dv_profile

    def get_encoding_dolby_vision_el_present(self) -> Optional[bool]:
        """Get the Dolby Vision Enhancement Layer for encoding.

        Returns:
            DolbyVisionEnhancementLayer or None if not applicable
        """
        return self._dv_el_present

    def get_encoding_video_codec(self) -> VideoCodec:
        """Get the video codec to be used for encoding.

        Returns:
            VideoCodec enum value
        """
        return self._target_video_codec

    def get_audio_codec_items(self) -> Dict[str, AudioCodecItem]:
        """Get the audio codec items for encoding.

        Returns:
            Dictionary of audio codec items
        """
        return self._encoder_settings.audio_codecs

    def get_encoding_hdr_sdr_format(self) -> list[HdrSdrFormat]:
        """Get the effective HDR/SDR formats that will be present in the output.

        Returns:
            List of HdrSdrFormat values representing all formats in the output
        """
        return self._target_hdr_sdr_format

    def is_dolby_vision_encoding(self) -> bool:
        """Check if encoding to Dolby Vision format."""
        return HdrSdrFormat.DOLBY_VISION in self.get_encoding_hdr_sdr_format()

    def is_hdr10_encoding(self) -> bool:
        """Check if encoding to HDR10 format."""
        return HdrSdrFormat.HDR10 in self.get_encoding_hdr_sdr_format()

    def is_hdr_encoding(self) -> bool:
        """Check if encoding to HDR format."""
        return HdrSdrFormat.HDR in self.get_encoding_hdr_sdr_format()

    def is_hdr10plus_encoding(self) -> bool:
        """Check if encoding to HDR10+ format."""
        return HdrSdrFormat.HDR10_PLUS in self.get_encoding_hdr_sdr_format()

    def is_sdr_encoding(self) -> bool:
        """Check if encoding to SDR format."""
        return HdrSdrFormat.SDR in self.get_encoding_hdr_sdr_format()

    def is_audio_copy_encoding(self) -> bool:
        audio: dict[str, AudioCodecItem] = self._encoder_settings.audio_codecs

        if audio.get('default') and audio['default'].to_codec == AudioCodec.COPY:
            return True

        return False

    def get_target_file(self) -> Path:
        """Get the target output file path.

        Returns:
            Target file Path
        """
        return self._target_file

    def _build_ffmpeg_audio_options(self, options: dict) -> dict:
        audio_codecs: dict[str, AudioCodecItem] = self._encoder_settings.audio_codecs
        audio_tracks: list[MkvTrack] = self._video.get_container_audio_tracks()

        audio_default_track: str | None = self._encoder_settings.audio_default_track

        for track in audio_tracks:
            track_id_str = str(track.id)
            audio_codec_item: AudioCodecItem | None = None
            if track_id_str in audio_codecs:
                audio_codec_item = audio_codecs[track_id_str]
            elif track.properties.language in audio_codecs:
                audio_codec_item = audio_codecs[track.properties.language]
            elif 'default' in audio_codecs:
                audio_codec_item = audio_codecs['default']

            if audio_codec_item and audio_codec_item.to_codec == AudioCodec.REMOVE:
                continue
            elif audio_codec_item and audio_codec_item.to_codec != AudioCodec.COPY:
                track_codec = track.codec.lower().replace('-', '')
                if audio_codec_item.from_codec == track_codec or audio_codec_item.from_codec is None:
                    options['map'].append(f'0:a:{track.ffmpeg_index}')
                    options[f'c:a:{track.ffmpeg_index}'] = audio_codec_item.to_codec.value
                    count_ch = 2
                    if track.properties.audio_channels:
                        count_ch: int = track.properties.audio_channels

                    if audio_codec_item.to_codec == AudioCodec.FLAC and count_ch > 8:
                        raise EncoderConfigurationError(f"FLAC codec supports a maximum of 8 (7.1) channels. Track ID {track.id} has {count_ch} channels.")
                    elif audio_codec_item.to_codec == AudioCodec.FLAC and count_ch > 6:
                        print_warn(f"FLAC codec with more than 6 channels may not be widely supported. Track ID {track.id} has {count_ch} channels.")
                    if audio_codec_item.to_codec == AudioCodec.FLAC:
                        options['compression_level'] = '12' # 0-12 / 12 is a best kompression but slowest
                        continue # no bitrate setting for FLAC

                    if audio_codec_item.to_codec == AudioCodec.AC3 and count_ch > 6:
                        raise EncoderConfigurationError(f"AC3 codec supports a maximum of 6 (5.1) channels. Track ID {track.id} has {count_ch} channels.")

                    if audio_codec_item.to_codec == AudioCodec.AAC and count_ch > 6:
                        print_warn(f"AAC codec with more than 6 channels may not be widely supported. Track ID {track.id} has {count_ch} channels.")

                    bitrate: int
                    if count_ch == 1: # Mono
                        if audio_codec_item.to_codec == AudioCodec.AC3 or audio_codec_item.to_codec == AudioCodec.EAC3:
                            bitrate = 128 # 96-128 = AC3
                        else:
                            bitrate = 128
                    elif count_ch == 2: # Stereo
                        if audio_codec_item.to_codec == AudioCodec.AC3:
                            bitrate = 384 # 192-384 = AC3
                        elif audio_codec_item.to_codec == AudioCodec.EAC3:
                            bitrate = 256 # 128-256 = EAC3
                        else:
                            bitrate = 256 # 128-256 = AAC / default 192
                    elif count_ch == 6: # 5.1
                        if audio_codec_item.to_codec == AudioCodec.AC3:
                            bitrate = 640 # 640 = AC3
                        elif audio_codec_item.to_codec == AudioCodec.EAC3:
                            bitrate = 1024 # 1024 = EAC3
                        else:
                            bitrate = 640 # 384-640 = AAC / default 512
                    elif count_ch == 8: # 7.1
                        if audio_codec_item.to_codec == AudioCodec.EAC3:
                            bitrate = 1536 # 768-1536 = EAC3
                        else:
                            bitrate = 1024 # 512-1024 = AAC / default 768
                    elif count_ch == 10: # 7.1.2
                        if audio_codec_item.to_codec == AudioCodec.EAC3:
                            bitrate = 2048 # 1024-2048 = EAC3
                        else:
                            bitrate = 1536 # 768–1536 for 7.1.2 / default 1024
                    else:
                        bitrate = 64 * count_ch

                    if track.properties.tag_bps is not None:
                        try:
                            source_bitrate: float = int(track.properties.tag_bps) / 1000
                            if source_bitrate < bitrate:
                                bitrate = int(source_bitrate)
                        except ValueError:
                            pass

                    options[f'b:a:{track.ffmpeg_index}'] = f"{bitrate}k"
                    options[f'ac:a:{track.ffmpeg_index}'] = str(count_ch)
            else:
                options['map'].append(f'0:a:{track.ffmpeg_index}')
                options[f'c:a:{track.ffmpeg_index}'] = 'copy'

            # Set default audio track
            if audio_default_track == "copy":
                continue
            if audio_default_track == track_id_str or track.properties.language == audio_default_track:
                options[f'disposition:a:{track.ffmpeg_index}'] = 'default'
            else:
                options[f'disposition:a:{track.ffmpeg_index}'] = '0'

        return options

    def _build_ffmpeg_subtitle_options(self, options: dict) -> dict:
        subtitle_flags: SubtitleModeItem = self._encoder_settings.subtitle_flags
        overrides: dict[str, SubtitleTrackOverride] = self._encoder_settings.subtitle_track_overrides

        if subtitle_flags.mode == SubtitleMode.REMOVE:
            return options

        # COPY and AUTO modes: map all subtitle tracks (except those with REMOVE override), disposition will be set via mkvpropedit
        subtitle_tracks: list[MkvTrack] = self._video.get_container_subtitles_tracks()

        if not subtitle_tracks:
            # Fallback for files where track list is unavailable (e.g., some TS files)
            options['map'].append('0:s?')
            options.update({'c:s': 'copy'})
            return options

        # Map each subtitle track individually, skipping those marked for removal
        for track in subtitle_tracks:
            # Resolve per-track override (same lookup order as audio: id first, then language)
            track_id_str = str(track.id)
            override: SubtitleTrackOverride | None = (
                overrides.get(track_id_str)
                or overrides.get(track.properties.language or '')
            )

            # Skip tracks marked for removal
            if override and override.action == SubtitleTrackAction.REMOVE:
                continue

            options['map'].append(f'0:s:{track.ffmpeg_index}')
            options[f'c:s:{track.ffmpeg_index}'] = 'copy'

        return options

    def _apply_subtitle_properties(self, output_file: Path) -> bool:
        """Apply subtitle track properties to output file via mkvpropedit.

        This sets track names, default flags, and forced flags based on subtitle_flags mode.
        Supports COPY (preserve source), REMOVE (skip), and AUTO (intelligent selection).
        Per-track overrides can modify default/forced flags or remove specific tracks.

        Args:
            output_file: Path to output MKV file to edit

        Returns:
            True if successful, False otherwise
        """
        subtitle_flags: SubtitleModeItem = self._encoder_settings.subtitle_flags
        overrides: dict[str, SubtitleTrackOverride] = self._encoder_settings.subtitle_track_overrides

        if subtitle_flags.mode == SubtitleMode.REMOVE:
            # No subtitle edits needed for REMOVE mode
            return True

        if subtitle_flags.mode == SubtitleMode.COPY and not overrides:
            # No mkvpropedit needed: FFmpeg already copies subtitle tracks as-is
            return True

        try:
            from hdr_forge.tools.mkvmerge import extract_container_info_json
            from hdr_forge.edit_files.subtitle_editor import build_subtitle_track_edits

            # Extract output file track information
            output_info = extract_container_info_json(output_file)
            output_subtitle_tracks = [
                track for track in output_info.tracks if track.type.value.lower() == 'subtitles'
            ]

            if not output_subtitle_tracks:
                # No subtitles in output, nothing to do
                return True

            # Get source subtitle tracks
            source_subtitle_tracks = self._video.get_container_subtitles_tracks()
            if not source_subtitle_tracks:
                # No source subtitles, nothing to do
                return True

            # Build subtitle track edits
            edits = build_subtitle_track_edits(
                source_subtitle_tracks=source_subtitle_tracks,
                output_subtitle_tracks=output_subtitle_tracks,
                subtitle_flags=subtitle_flags,
                overrides=overrides,
            )

            # Apply edits via mkvpropedit
            if edits:
                return mkvpropedit.set_subtitle_track_properties(output_file, edits)

            return True

        except Exception as e:
            print_err(f"Failed to apply subtitle properties: {e}")
            return False

    def _build_ffmpeg_output_options(self) -> Dict[str, str]:
        """Build FFmpeg output options dictionary for encoding.

        Returns:
            Dictionary of FFmpeg output options
        """
        output_options: dict = {
            "map": ["0:V"],
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

        metadata: list[str] = [
            'hdr_forge_version=' + str(getattr(sys.modules['hdr_forge'], '__version__', 'unknown')),
            #'title="Mein Film – Extended Cut"',
        ]
        if 'metadata' in output_options:
            output_options['metadata'].extend(metadata)
        else:
            output_options['metadata'] = metadata

        output_options = self._build_ffmpeg_audio_options(options=output_options)

        output_options = self._build_ffmpeg_subtitle_options(options=output_options)

        if self._encoder_settings.threads:
            output_options['threads'] = str(self._encoder_settings.threads)

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
                process_name=f"Encoding: {target_file.name}",
            )

        try:
            # Build output options
            output_options: dict = self._build_ffmpeg_output_options()

            init_hw_device_vulkan: bool = False
            if (self._video.get_dolby_vision_profile() == DolbyVisionProfile._5):
                init_hw_device_vulkan = True

            # Execute FFmpeg with progress tracking
            success: bool = run_ffmpeg(
                input_file=input_file,
                output_file=target_file,
                output_options=output_options,
                progress_callback=progress_callback,
                try_fix=self._encoder_settings.try_fix,
                init_hw_device_vulkan=init_hw_device_vulkan,
            )
            print()

            return success

        except Exception as e:
            print_err(f"Error during encoding: {e}")
            return False

    def convert_sdr_hdr10_or_video_copy(
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

        success = self._run_ffmpeg_encoding_process(
            input_file=input_file,
            target_file=self._target_file,
        )

        if success:
            # Apply subtitle properties via mkvpropedit
            success = self._apply_subtitle_properties(self._target_file)

        return success

    def convert_dolby_vision_to_hdr10_without_re_encoding(
        self,
    ) -> bool:
        temp_dir: Path = get_global_temp_directory()

        input_file: Path = self._video.get_filepath()
        total_frames: int = self._video.get_total_frames()

        # Step 1: Extract base layer (HEVC without EL+RPU) from original video
        base_layer_hevc_path: Path = dovi_tool.extract_base_layer(
            input_path=input_file,
            output_hevc=temp_dir / f"video_BL.hevc",
            total_frames=total_frames,
        )

        # Step 2: Mux base layer HEVC with original audio/subtitles into final MKV
        # This creates a playable MKV file with base layer video + original audio/subs
        _base_layer_mkv_path: Path = mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=base_layer_hevc_path,
            input_mkv=input_file,
            output_mkv=self._target_file,
        )

        # Apply subtitle properties via mkvpropedit
        return self._apply_subtitle_properties(self._target_file)

    def _convert_dolby_profile(
        self,
        input_file: Path,
        hevc_bl: Path,
        source_dv_profile: DolbyVisionProfile | None,
        target_dv_profile: DolbyVisionProfile | None,
    ) -> Path:
        temp_dir: Path = get_global_temp_directory()

        total_frames: int = self._video.get_total_frames()

        has_crop: bool = self._video_codec_lib.has_crop() if self._video_codec_lib else False

        # Step 1: Extract RPU metadata from original Dolby Vision video
        rpu_file_path: Path = dovi_tool.extract_rpu(
            input_path=input_file,
            output_rpu=temp_dir / f"RPU.rpu",
            dv_profile_source=source_dv_profile,
            dv_profile_encoding=target_dv_profile,
            total_frames=total_frames,
            use_cache=False,
            crop=has_crop,
        )

        hevc: Path = hevc_bl
        # Setup 2: If AUTO profile and source is profile 7, demux EL profile 7 RPU
        if self._dv_el_present:
            # start demux EL profile 7 for profile 7 encoding
            el_path: Path = dovi_tool.extract_enhancement_layer(
                input_path=input_file,
                output_el=temp_dir / f"video_EL.hevc",
                total_frames=total_frames,
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
            output_hevc=temp_dir / f"video_encoded_BL_{'EL_' if self._dv_el_present else ''}RPU.hevc"
        )

        return encoded_hevc_with_rpu_path


    def convert_dolby_vision_to_other_profile_without_re_encoding(
        self,
    ) -> bool:
        input_file: Path = self._video.get_filepath()
        total_frames: int = self._video.get_total_frames()

        # Create temporary directory for all intermediate files
        temp_dir: Path = get_global_temp_directory()

        # Step 1: Extract base layer (HEVC without RPU) from original video
        base_layer_hevc_path: Path = dovi_tool.extract_base_layer(
            input_path=input_file,
            output_hevc=temp_dir / f"video_BL.hevc",
            total_frames=total_frames,
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

        # Apply subtitle properties via mkvpropedit
        return self._apply_subtitle_properties(self._target_file)

    def convert_dolby_vision(
        self,
        extract_base_layer: bool = True,
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

        # Create temporary directory for all intermediate files
        temp_dir: Path = get_global_temp_directory()

        if extract_base_layer:
            # Step 1: Extract base layer (HEVC without RPU) from original video
            base_layer_hevc_path: Path = dovi_tool.extract_base_layer(
                input_path=input_file,
                output_hevc=temp_dir / f"video_BL.hevc",
                total_frames=total_frames,
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

        ffmpeg_encoding_input_file: Path = base_layer_mkv_path if extract_base_layer else input_file

        encoding_success: bool = self._run_ffmpeg_encoding_process(
            input_file=ffmpeg_encoding_input_file,
            target_file=encoded_base_layer_mkv,
        )
        if extract_base_layer:
            # Cleanup: Delete base layer MKV (no longer needed after encoding)
            base_layer_mkv_path.unlink(missing_ok=True)

        if not encoding_success:
            return False

        # For HDR10 or SDR encoding, apply subtitle properties and we are done here
        if only_hdr10_or_sdr_encoding:
            return self._apply_subtitle_properties(self._target_file)

        print()

        # Step 4: Extract encoded HEVC video stream from MKV
        encoded_hevc_bl_path: Path = extract_hevc(
            input_path=encoded_base_layer_mkv,
            output_hevc=temp_dir / f"video_encoded_BL.hevc",
            total_frames=total_frames,
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

        # Apply subtitle properties via mkvpropedit
        return self._apply_subtitle_properties(self._target_file)

    def convert(
        self,
    ) -> bool:
        # Validate Dolby Vision requirements
        if self._encoder_settings.hdr_sdr_format == HdrSdrFormat.DOLBY_VISION:
            # Check if source is Dolby Vision
            if self._video.get_dolby_vision_profile() is None:
                raise EncoderConfigurationError("Error: --hdr dv/dv8 requires a Dolby Vision source. Use --hdr auto to preserve the source format.")

            # Check if AV1 codec is being used
            if self.get_encoding_video_codec() == VideoCodec.AV1:
                raise EncoderConfigurationError("Error: Dolby Vision encoding is not supported with AV1 (libsvtav1).")

        if self._video.is_dolby_vision_video():

            if (self.get_encoding_video_codec() == VideoCodec.COPY and self._encoder_settings.target_dv_profile == DolbyVisionProfileEncodingMode.AUTO):
                # Dolby Vision Profile copy without re-encoding
                return self.convert_sdr_hdr10_or_video_copy()

            if (self._video.get_dolby_vision_profile() == DolbyVisionProfile._5):
                # Dolby Vision Profile 5 cannot be converted to other profiles without re-encoding
                return self.convert_dolby_vision(
                    extract_base_layer=False,
                )

            # Convert Dolby Vision to HDR10, without re-encoding
            if (self.get_encoding_video_codec() == VideoCodec.COPY and self.is_audio_copy_encoding()):
                if (self.is_dolby_vision_encoding()):
                    return self.convert_dolby_vision_to_other_profile_without_re_encoding()
                elif (self.is_hdr10_encoding()):
                    return self.convert_dolby_vision_to_hdr10_without_re_encoding()

            # Dolby Vision encoding workflow
            return self.convert_dolby_vision(
                extract_base_layer=False,
            )

        return self.convert_sdr_hdr10_or_video_copy()
