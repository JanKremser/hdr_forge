from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import os
import subprocess
import sys
from typing import Callable, Counter, Optional, Tuple, Type, TypeVar

from hdr_forge.cli.cli_output import print_err, print_warn
from hdr_forge.cli.video_codec_base import callback_handler_crop_video
from hdr_forge.ffmpeg.video_codec.service.presets import calc_hw_prest_params
from hdr_forge.typedefs.encoder_typing import CropHandler, CropMode, CropSettings, EncoderSettings, HdrSdrFormat, ScaleMode, VideoEncoderLibrary
from hdr_forge.video import Video

T = TypeVar("T")

class VideoCodecBase(ABC):

    PIXEL_RESOLUTIONS: dict[str, int] = {
        'UHD': 3840*2160,
        'QHD': 2560*1440,
        'FHD': 1920*1080,
        'HD': 1280*720,
        'SD': 854*480
    }

    def __init__(
        self,
        lib: VideoEncoderLibrary,
        encoder_settings: EncoderSettings,
        video: Video,
        scale: Tuple[int, int],
        supported_hdr_sdr_formats: list[HdrSdrFormat] = [],
    ):
        self.lib: VideoEncoderLibrary = lib
        self._video = video
        self._scale = scale
        self._encoder_settings: EncoderSettings = encoder_settings
        self._supported_hdr_sdr_formats: list[HdrSdrFormat] = supported_hdr_sdr_formats

        self._hdr_sdr_format_for_encoding: HdrSdrFormat = self._get_hdr_sdr_format_for_encoding(
            hdr_sdr_format=encoder_settings.hdr_sdr_format
        )
        if self._hdr_sdr_format_for_encoding not in supported_hdr_sdr_formats:
            print_err(f"{self.lib.value} does not support the selected {self._hdr_sdr_format_for_encoding.value}-format for encoding.")
            sys.exit(1)

        self._crop_width: int = video.width
        self._crop_height: int = video.height
        self._crop_x: int = 0
        self._crop_y: int = 0
        if encoder_settings.crop.mode != CropMode.OFF:
            self._crop_video(
                crop_settings=encoder_settings.crop,
            )

        self._scale_width: Optional[int]
        self._scale_height: Optional[int]
        self._scale_width, self._scale_height = self._determine_scale_width_height(
            scale_mode=encoder_settings.scale_mode,
            new_height=encoder_settings.scale_height,
        )


    @abstractmethod
    def get_ffmpeg_params(self) -> dict:
        """Get FFmpeg parameters for this codec."""
        output_options: dict = {
            "c:v": self.lib.value
        }
        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        # Add video filters (crop and scale), Only for SDR/HDR10 encoding
        if encoding_hdr_sdr_format != HdrSdrFormat.DOLBY_VISION:
            crop_filter: str | None = self._get_crop_filter()
            if crop_filter:
                output_options['vf'] = crop_filter

            scale_filter: str | None = self._get_scale_filter()
            if scale_filter:
                if 'vf' in output_options:
                    output_options['vf'] += f',{scale_filter}'
                else:
                    output_options['vf'] = scale_filter

        if encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            if self._video.is_hdr_video():
                # Tone mapping for HDR to SDR conversion
                output_options['vf'] = (
                    (output_options.get('vf', '') + ',') if 'vf' in output_options else ''
                ) + 'zscale=t=linear:npl=100,format=gbrpf32le,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:p=bt709:r=tv,format=yuv420p'

                # Set correct metadata for SDR output
                output_options.update({
                    "metadata:s:v": [
                        "colour_primaries=bt709",
                        "colour_transfer=bt709",
                        "colour_space=bt709"
                    ],
                })

                # Neu: 'zscale=t=linear:npl=100,format=gbrpf32le,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:p=bt709:r=tv,format=yuv420p'
                # alt: 'zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p'

                # alternativ, aber nicht so ganu und macht kein tonmapping: -vf colorspace=all=bt709
        return output_options

    @abstractmethod
    def get_custom_lib_parameters(self) -> dict:
        """Get custom parameters specific to the codec library."""
        pass

    def get_name(self) -> str:
        return self.lib.value

    def get_encoding_hdr_sdr_format(self) -> HdrSdrFormat:
        """Get the effective color format used for encoding.

        Returns:
            HdrSdrFormat used for encoding
        """
        return self._hdr_sdr_format_for_encoding

    def is_hdr_encoding(self) -> bool:
        """Check if encoding is HDR (HDR10 or Dolby Vision).

        Returns:
            True if encoding is HDR, False otherwise
        """
        return self._hdr_sdr_format_for_encoding in [HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]

    def is_cropped(self) -> bool:
        """Check if video has cropping applied.

        Returns:
            True if cropping is applied, False otherwise
        """
        return (self._crop_width != self._video.width or
                self._crop_height != self._video.height or
                self._crop_x != 0 or
                self._crop_y != 0)

    def get_crop(self) -> Optional[Tuple[int, int, int, int]]:
        """Get ffmpeg crop filter string if cropping is needed.

        Returns:
            Crop filter string or None if no cropping needed
        """
        if self.is_cropped():
            return (self._crop_width, self._crop_height, self._crop_x, self._crop_y)
        return None

    def get_encoding_resolution(self) -> Tuple[int, int]:
        if self._scale_width and self._scale_height:
            return self._scale_width, self._scale_height

        if self.is_cropped():
            return self._crop_width, self._crop_height
        return self._video.width, self._video.height

    def calc_hw_preset_settings(self, cls: Type[T]) -> T:
        pixel: int = self._get_pixel_count()

        return cls(**calc_hw_prest_params(
            pixels=pixel,
            hw_preset=self._encoder_settings.hdr_forge_encoding_preset.hardware_preset,
            lib=self.lib
        ))

    def __str__(self):
        return f"{self.__class__.__name__}({self.lib.value})"

    def _get_scale_filter(self) -> Optional[str]:
        """Get ffmpeg scale filter string if scaling is needed.

        Returns:
            Scale filter string or None if no scaling needed
        """
        if self._scale_width and self._scale_height:
            return f"scale={self._scale_width}:{self._scale_height}"
        return None

    def _get_crop_filter(self) -> Optional[str]:
        """Get ffmpeg crop filter string if cropping is needed.

        Returns:
            Crop filter string or None if no cropping needed
        """
        crop: Tuple[int, int, int, int] | None = self.get_crop()
        if crop:
            width, height, x, y = crop
            return f"crop={width}:{height}:{x}:{y}"
        return None

    def _get_pixel_count(self) -> int:
        """Get total pixel count considering scale and crop.

        Returns:
            Total number of pixels for encoding
        """
        w, h = self.get_encoding_resolution()
        return w * h

    def _get_hdr_sdr_format_for_encoding(self, hdr_sdr_format: HdrSdrFormat) -> HdrSdrFormat:
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
            print_warn(f"Warning: Cannot upgrade from {source_format.value} to {hdr_sdr_format.value}. Keeping source format.")
            return source_format

        # Valid downgrade
        return hdr_sdr_format

    def _detect_crop_at_position(self, position_seconds: int) -> Optional[Tuple[int, int, int, int]]:
        """Detect crop parameters at a specific video position.

        Args:
            position_seconds: Time position in seconds to analyze

        Returns:
            Tuple of (width, height, x, y) or None if detection fails
        """
        hdr_cropdetect_filter: str = ""
        if self._video.is_hdr_video():
            hdr_cropdetect_filter = "zscale=transfer=bt709,format=yuv420p,hqdn3d=1.5:1.5:6:6,"

        cmd: list[str] = [
            'ffmpeg',
            '-ss', str(position_seconds),
            '-i', str(self._video._filepath),
            '-vf', f'{hdr_cropdetect_filter}cropdetect=24:16:0',
            '-frames:v', '30',
            '-f', 'null',
            '-'
        ]

        try:
            result: subprocess.CompletedProcess[str] = subprocess.run(
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

    def _detect_crop_auto(
        self,
        check_samples: int = 10,
        max_workers: int = 16,
        callback: Optional[Callable[[CropHandler], None]] = None,
    ) -> Optional[Tuple[int, int, int, int]]:
        if callback:
            callback(CropHandler(
                finish_progress=False,
                completed_samples=0,
                total_samples=check_samples,
            ))

        # Get video duration
        duration = self._video.get_duration_seconds()

        if duration <= 0:
            return

        # Calculate positions to sample (evenly distributed)
        interval: float = duration / (check_samples + 1)
        positions: list[int] = [int(interval * (i + 1)) for i in range(check_samples)]

        # Run crop detection in parallel
        crop_results: list = []
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
                        total_samples=check_samples,
                    ))

        # Send final crop handler
        if callback:
            callback(CropHandler(
                finish_progress=True,
                completed_samples=completed,
                total_samples=check_samples,
            ))

        if not crop_results:
            return

        # Find most common crop dimensions
        crop_counter = Counter(crop_results)
        most_common_crop: Tuple[int, int, int, int] = crop_counter.most_common(1)[0][0]

        return most_common_crop

    def _crop_video(
        self,
        crop_settings: CropSettings,
    ) -> None:
        """Detect and apply optimal crop parameters using multi-threaded analysis.

        Args:
            num_threads: Number of concurrent threads for crop detection
            callback: Optional callback function for progress updates
        """

        if crop_settings.mode == CropMode.OFF:
            return

        if (
            self.get_encoding_hdr_sdr_format() == HdrSdrFormat.DOLBY_VISION
        ):
            print_err(msg="Crop detection is not supported for Dolby Vision encoding.")
            sys.exit(1)

        if crop_settings.mode == CropMode.AUTO:
            cpu_kerne: int = min(crop_settings.check_samples, os.cpu_count() or 4)
            c: Tuple[int, int, int, int] | None = self._detect_crop_auto(
                check_samples=crop_settings.check_samples,
                max_workers=cpu_kerne,
                callback=callback_handler_crop_video,
            )
            if c is None:
                print_warn("Auto crop detection failed or no crop needed.")
                return
            self._crop_width, self._crop_height, self._crop_x, self._crop_y = c

        if crop_settings.mode == CropMode.MANUAL:
            if crop_settings.manual_crop is not None:
                self._crop_x, self._crop_y, self._crop_width, self._crop_height = crop_settings.manual_crop

        if crop_settings.mode == CropMode.RATIO:
            if crop_settings.ratio is not None:
                ar_w, ar_h = crop_settings.ratio
                target_aspect_ratio: float = ar_w / ar_h
                current_aspect_ratio: float = self._video.width / self._video.height

                if current_aspect_ratio > target_aspect_ratio:
                    # Video is wider than target aspect ratio - crop width
                    new_width: int = int(self._video.height * target_aspect_ratio)
                    self._crop_width = new_width
                    self._crop_height = self._video.height
                    self._crop_x = (self._video.width - new_width) // 2
                    self._crop_y = 0
                elif current_aspect_ratio < target_aspect_ratio:
                    # Video is taller than target aspect ratio - crop height
                    new_height: int = int(self._video.width / target_aspect_ratio)
                    self._crop_width = self._video.width
                    self._crop_height = new_height
                    self._crop_x = 0
                    self._crop_y = (self._video.height - new_height) // 2
                else:
                    # Aspect ratios match - no cropping needed
                    pass

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

        if self.is_cropped() is False:
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
