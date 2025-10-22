"""CLI output and progress tracking functionality."""



from ehdr.cli.cli_output import BLUE, color_str, create_aspect_ratio_str, create_progress_bar
from ehdr.typing.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionProfile
from ehdr.typing.encoder_typing import CropHandler, VideoCodec
from ehdr.encoder import Encoder




def print_encoding_params(encoder: Encoder) -> None:
    """Print encoding parameters.

    Args:
        encoder: Encoder object with encoding configuration
    """
    color = BLUE
    print()
    print(f"{color_str('_', color)}" * 70)
    print("Encoding Parameters:")
    print(f"  Output File: {color_str(str(encoder.get_target_file()), color)}")

    video_codec = encoder.get_encoding_video_codec()
    print(f"  Video Codec: {color_str(video_codec.value, color)}")
    if video_codec != VideoCodec.COPY:
        encoding_video_library = encoder.get_encoding_video_library()
        print(f"  Video Encoder Library: {color_str(encoding_video_library.value, color)}")
        print(f"  CRF: {color_str(encoder._crf, color)}")
        print(f"  Preset: {color_str(encoder._preset, color)}")
        if encoder._is_cropped():
            crop_filter: str | None = encoder.get_crop_filter()
            print(f"  Crop: {color_str(crop_filter, color)}")
        else:
            print(f"  Crop: {color_str('-', color)}")

        resolution_w, resolution_h = encoder.get_encoding_resolution()
        aspect_ratio: str = create_aspect_ratio_str(resolution_w, resolution_h)
        print(f"  Resolution: {color_str(f"{resolution_w}x{resolution_h}", color)}")
        print(f"  Aspect Ratio: {color_str(aspect_ratio, color)}")
        print(f"  HDR/SDR: {color_str(encoder.get_encoding_hdr_sdr_format().value.upper(), color)}")
    if encoder.is_dolby_vision_encoding():
        dv_profile: DolbyVisionProfile | None = encoder.get_encoding_dolby_vision_profile()
        assert dv_profile is not None
        print(f"  Dolby Vision:")
        print(f"    Profile: {color_str(dv_profile.value, color)}")

        dv_el: DolbyVisionEnhancementLayer | None = encoder.get_encoding_dolby_vision_enhancement_layer()

        dv_layout: str = f"BL+{'EL+' if dv_el else ''}RPU"
        print(f"    Layout: {color_str(dv_layout, color)}")

        dv_el_str: str | None = dv_el.value if dv_el else None
        print(f"    Enhancement Layer (EL): {color_str(dv_el_str or '-', color)}")
    print(f"{color_str('_', color)}" * 70)
    print()

def callback_handler_crop_video(crop_handler: CropHandler) -> None:
    """Callback handler for crop video progress.

    Args:
        crop_handler: CropHandler instance
        message: Optional message to display
    """

    if crop_handler.finish_progress:
        print()  # New line on completion
        return

    completed_samples = crop_handler.completed_samples
    total_samples = crop_handler.total_samples
    percent: float = (completed_samples / total_samples * 100) if total_samples > 0 else 0.0
    progress_bar: str = create_progress_bar(percent=percent)
    if completed_samples == 0:
        print("\nCropping Progress:")
    print(f"\r{progress_bar} {percent:.1f}% | {completed_samples}/{total_samples}", end="", flush=True)
