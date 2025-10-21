"""CLI output and progress tracking functionality."""

from typing import Tuple


from ehdr.cli.cli_output import BLUE, color_str, create_progress_bar
from ehdr.dataclass import CropHandler
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
    print(f"  CRF: {color_str(encoder.crf, color)}")
    print(f"  Preset: {color_str(encoder.preset, color)}")
    if encoder._is_cropped():
        crop_filter: str | None = encoder.get_crop_filter()
        print(f"  Crop: {color_str(crop_filter, color)}")
    else:
        print(f"  Crop: {color_str('No cropping applied', color)}")
    scale_dimensions: Tuple[int, int] | None = encoder._get_scale_dimensions()
    if scale_dimensions:
        w, h = scale_dimensions
        print(f"  Scale: {color_str(f"{w}x{h}", color)}")
    print(f"  HDR/SDR: {color_str(encoder.get_color_format().value.upper(), color)}")
    if encoder.is_dolby_vision_encoding():
        print(f"  Dolby Vision:")
        print(f"    Profile: {color_str(encoder.get_encoding_dolby_vision_profile(), color)}")
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
