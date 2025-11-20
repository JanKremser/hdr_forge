from hdr_forge.cli.cli_output import create_progress_bar
from hdr_forge.typedefs.encoder_typing import CropHandler


def callback_handler_crop_video(crop_handler: CropHandler) -> None:
    """Callback handler for crop video progress.

    Args:
        crop_handler: CropHandler instance
    """

    if crop_handler.finish_progress:
        print()  # New line on completion
        return

    completed_samples = crop_handler.completed_samples
    total_samples = crop_handler.total_samples
    percent: float = (completed_samples / total_samples * 100) if total_samples > 0 else 0.0
    progress_bar: str = create_progress_bar(percent=percent, text=f"{percent:.1f}% | {completed_samples}/{total_samples}")
    if completed_samples == 0:
        print("\nCropping Progress:")
    print(f"\r{progress_bar}", end="", flush=True)
