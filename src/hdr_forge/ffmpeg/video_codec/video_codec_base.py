from abc import ABC, abstractmethod
import math
from pathlib import Path
import sys
from typing import Optional, Tuple, Type, TypeVar

from hdr_forge.analyze.crop_video import CropResult, VideoCropper
from hdr_forge.analyze.detect_logo import LogoDetector
from hdr_forge.analyze.grain_score import GrainAnalyzer
from hdr_forge.cli.cli_output import print_err, print_warn
from hdr_forge.ffmpeg.video_codec.service.presets import calc_hw_prest_params
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrSdrFormat, ScaleMode, VideoEncoderLibrary
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.video import Video

T = TypeVar("T")

class VideoCodecBase(ABC):

    def __init__(
        self,
        lib: VideoEncoderLibrary,
        encoder_settings: EncoderSettings,
        video: Video,
        scale: Tuple[int, int],
        supported_hdr_sdr_formats: list[HdrSdrFormat] = [],
        gpu_encoding: bool = False,
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

        self._logo_remover = LogoDetector(
            video=video,
            logo_removal=encoder_settings.logo_removal,
        )
        self._logo_remover.detect_logo()

        self._cropper = VideoCropper(
            video=video,
            crop_settings=encoder_settings.crop,
            encoding_hdr_sdr_format=self._hdr_sdr_format_for_encoding,
        )
        self._cropper.detect_crop()

        self._grain = GrainAnalyzer(
            video=video,
            grain_mode=encoder_settings.grain,
        )
        self._grain.analyze_by_mode()

        self._scale_width: Optional[int]
        self._scale_height: Optional[int]
        self._scale_width, self._scale_height = self._determine_scale_width_height(
            scale_mode=encoder_settings.scale_mode,
            new_height=encoder_settings.scale_height,
        )
        self._gpu_encoding: bool = gpu_encoding

    def is_gpu_encoding(self) -> bool:
        """Check if the codec uses GPU encoding.

        Returns:
            True if GPU encoding is used, False otherwise
        """
        return self._gpu_encoding

    @abstractmethod
    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        """Get FFmpeg parameters for this codec."""
        output_options: dict = {
            **exist_params,
            "c:v": self.lib.value,
        }

        new_input: Path | None = self._logo_remover.get_ffmpeg_overlay_video_input()
        if new_input:
            filter_complex: str | None = self._logo_remover.get_ffmpeg_filter_filter_complex()
            if filter_complex:
                output_options = {
                    "i": str(new_input),
                    **output_options
                }
                output_options["map"] = ['[v]', '0:a?', '0:s?']
                output_options["filter_complex"] = filter_complex

        vf: str | None = self._get_default_video_filter()
        if vf:
            output_options["vf"] = vf

        if self._encoder_settings.dar_ratio is not None:
            dar_w, dar_h = self._encoder_settings.dar_ratio
            output_options["aspect"] = f"{dar_w}:{dar_h}"

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()
        if encoding_hdr_sdr_format == HdrSdrFormat.SDR and self._video.is_hdr_video():
            # Set correct metadata for SDR output
            output_options.update({
                "metadata:s:v": [
                    "colour_primaries=bt709",
                    "colour_transfer=bt709",
                    "colour_space=bt709"
                ],
            })

        return output_options

    @abstractmethod
    def get_custom_lib_parameters(self) -> dict:
        """Get custom parameters specific to the codec library."""
        pass

    @abstractmethod
    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        """Get HDR metadata to be used for encoding.

        Returns:
            HdrMetadata or None if not applicable
        """
        pass

    @abstractmethod
    def get_pix_format_for_encoding(self) -> str:
        return self._video.get_pix_fmt()

    @abstractmethod
    def get_bit_depth_for_encoding(self) -> int:
        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        if encoding_hdr_sdr_format in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]:
            return 10
        elif encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            if self._video.is_hdr_video():
                return 8

        # keep original bit depth for SDR source videos
        return self._video.get_bit_depth()

    def get_name(self) -> str:
        return self.lib.value

    def _get_default_video_filter(self) -> str | None:
        """Get default video filter string for ffmpeg (crop and scale).

        Returns:
            Video filter string
        """
        filters: list[str] = []
        vf: str | None = self._encoder_settings.vfilter
        if vf is not None:
            _filter: list[str] = vf.split(',')
            filters.extend(_filter)

        delogo_filter: str | None = self._logo_remover.get_ffmpeg_delogo_filter()
        if delogo_filter:
            filters.append(delogo_filter)

        encoding_hdr_sdr_format: HdrSdrFormat = self.get_encoding_hdr_sdr_format()

        # Add video filters (crop and scale), Only for SDR/HDR10 encoding
        if encoding_hdr_sdr_format != HdrSdrFormat.DOLBY_VISION:
            crop_filter: str | None = self._get_crop_filter()
            if crop_filter:
                filters.append(crop_filter)

            scale_filter: str | None = self._get_scale_filter()
            if scale_filter:
                filters.append(scale_filter)

        if encoding_hdr_sdr_format == HdrSdrFormat.SDR:
            if self._video.is_hdr_video():
                # Tone mapping for HDR to SDR conversion
                filters.extend([
                    'zscale=t=linear:npl=100',
                    'format=gbrpf32le',
                    'tonemap=tonemap=hable:desat=0',
                    'zscale=t=bt709:m=bt709:p=bt709:r=tv',
                    'format=yuv420p'
                ])
        if len(filters) == 0:
            return None
        return ','.join(filters)

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
        return self._hdr_sdr_format_for_encoding in [HdrSdrFormat.HDR, HdrSdrFormat.HDR10, HdrSdrFormat.DOLBY_VISION]

    def is_hdr10_encoding(self) -> bool:
        """Check if encoding is HDR (HDR10 or Dolby Vision).

        Returns:
            True if encoding is HDR, False otherwise
        """
        return self._hdr_sdr_format_for_encoding in [HdrSdrFormat.HDR10]

    def get_crop(self) -> CropResult:
        """Get ffmpeg crop filter string if cropping is needed.

        Returns:
            Crop filter
        """
        return self._cropper.get_crop_result()

    def get_encoding_resolution(self) -> Tuple[int, int]:
        if self._scale_width and self._scale_height:
            return self._scale_width, self._scale_height

        if self._cropper.is_cropped():
            crop: CropResult = self._cropper.get_crop_result()
            return crop.width, crop.height
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
        crop: CropResult = self._cropper.get_crop_result()
        if crop.is_valid:
            return f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}"
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
        format_hierarchy: dict[HdrSdrFormat, int] = {
            HdrSdrFormat.SDR: 0,
            HdrSdrFormat.HDR: 1,
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

        crop_result: CropResult = self._cropper.get_crop_result()
        if crop_result.is_valid is False:
            return __check_rounding(new_scale_width, new_scale_height)

        new_aspect_ratio: float = crop_result.width / crop_result.height

        if scale_mode == ScaleMode.HEIGHT:
            # scale-mode height

            height: int
            if crop_result.height < new_scale_height:
                height = crop_result.height
            else:
                height = new_scale_height

            width: int = math.floor(height * new_aspect_ratio)

            return __check_rounding(width, height)

        if scale_mode == ScaleMode.ADAPTIVE:
            # scale-mode adaptive
            if crop_result.width > new_scale_width:
                new_scale_height = math.floor(new_scale_width / new_aspect_ratio)
                return (new_scale_width, new_scale_height)

            if crop_result.height > new_scale_height:
                new_scale_width = math.ceil(new_scale_height * new_aspect_ratio)
                return (new_scale_width, new_scale_height)

            return __check_rounding(crop_result.width, crop_result.height)

        return None, None

    def _calculate_crf_adjustment_weight(
        self,
        current_crf: float,
        crf_delta: float,
        min_weight: float = 0.1,
        max_weight: float = 1.0,
        min_crf: float = 10.0,
        max_crf: float = 30.0
    ) -> float:
        """
        Berechnet einen Gewichtungsfaktor für die CRF-Anpassung nach unten.

        Args:
            current_crf: Basis-CRF des Videos
            crf_delta: gewünschte Anpassung nach unten (z.B. 2 für -2 CRF)
            min_weight: minimale Gewichtung
            max_weight: maximale Gewichtung
            min_crf: kleinster Basis-CRF für Skalierung
            max_crf: größter Basis-CRF für Skalierung

        Rückgabe:
            float zwischen min_weight und max_weight
        """
        if crf_delta == 0.0:
            return 0.0

        # Skaliere Basis-CRF auf 0..1
        crf_norm = (current_crf - min_crf) / (max_crf - min_crf)
        crf_norm = max(0.0, min(crf_norm, 1.0))

        # Gewicht proportional zum CRF-Delta und Basis-CRF
        weight = crf_norm * (crf_delta / crf_delta)  # hier nur skalierende Logik
        # Clamp auf min/max
        weight = max(min_weight, min(weight, max_weight))

        return weight
