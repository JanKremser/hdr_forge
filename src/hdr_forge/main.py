"""Main CLI entry point for HDR Forge video converter."""

import sys
from pathlib import Path

from hdr_forge.cli.args import pars_args, pars_encoder_settings
from hdr_forge.cli.cli_output import print_conversion_summary, print_debug, print_err, print_warn
from hdr_forge.cli.encoder import print_encoding_params
from hdr_forge.cli.video import print_video_infos
from hdr_forge.core import config
from hdr_forge.core.service import shutdown_system
from hdr_forge.hdr_metadata_injector import HdrMetadataInjector
from hdr_forge.typedefs.encoder_typing import EncoderSettings
from hdr_forge.encoder import Encoder
from hdr_forge.video import Video
from hdr_forge.analyze.maxcll import calc_maxcll

# Supported input video formats
SUPPORTED_FORMATS: list[str] = ['.mkv', '.m2ts', '.ts', '.mp4']


def get_video_files(path: Path, supported_formats: list[str]) -> list[Path]:
    """Get list of video files from path.

    Args:
        path: File or directory path
        supported_formats: list of supported file extensions

    Returns:
        list of video file paths
    """
    if path.is_file():
        return [path] if path.suffix.lower() in supported_formats else []

    if path.is_dir():
        video_files: list = []
        for fmt in supported_formats:
            video_files.extend(path.glob(f'*{fmt}'))
        return sorted(video_files)

    return []


def determine_output_file(video_file: Path, output_path: Path, is_batch: bool) -> Path:
    """Determine output file path for a video file.

    Args:
        video_file: Input video file
        output_path: Output path (file or directory)
        is_batch: Whether this is batch processing

    Returns:
        Output file path
    """
    if is_batch:
        return output_path / video_file.with_suffix('.mkv').name
    return output_path



def show_video_info(input_file: Path) -> bool:
    """Show detailed information about a video file.

    Args:
        input_file: Input video file path

    Returns:
        True if successful, False otherwise
    """
    try:
        if not input_file.exists():
            print(f"Error: The file {input_file} does not exist.")
            return False

        video = Video(filepath=input_file)

        print_video_infos(video=video)
        return True

    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def convert_video(
    video: Video,
    target_file: Path,
    settings: EncoderSettings,
) -> bool:
    """Convert SDR or HDR10 video using ffmpeg with libx265.

    Args:
        video: Video object with metadata
        target_file: Target output file path
        settings: Encoder settings containing all encoding parameters

    Returns:
        True if conversion succeeded, False otherwise
    """
    input_file: Path = video.get_filepath()

    # Create encoder with settings
    encoder = Encoder(
        video=video,
        target_file=target_file,
        settings=settings,
    )

    try:
        print_encoding_params(encoder=encoder)

        success: bool = encoder.convert()

        if success:
            print()  # New line after progress
            print(f"Success: {target_file.name}")

        return success
    except KeyboardInterrupt:
        print("\n" * 3)
        print_warn("Encoding cancelled by user.")
        return False
    except Exception as e:
        print(f"Error processing {input_file.name}: {e}")
        return False


def process_convert_command(args) -> int:
    """Process the convert subcommand."""
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)

    # Get list of video files to process
    video_files = get_video_files(input_path, SUPPORTED_FORMATS)

    if not video_files:
        print(f"Error: No supported video files found in: {input_path}")
        print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)

    # Determine if batch processing
    is_batch = len(video_files) > 1

    if is_batch:
        # Ensure output is a directory for batch processing
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            print("Error: Output must be a directory for batch processing")
            sys.exit(1)

    # Create encoder settings from CLI arguments
    settings: EncoderSettings = pars_encoder_settings.create_encoder_settings_from_args(args)

    # Process each video file
    success_count = 0
    fail_count = 0

    for video_file in video_files:
        # Determine output file
        out_file: Path = determine_output_file(video_file=video_file, output_path=output_path, is_batch=is_batch)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        video = Video(filepath=video_file)
        print_video_infos(video=video)

        success: bool = convert_video(
            video=video,
            target_file=out_file,
            settings=settings,
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

    print_conversion_summary(success_count, fail_count)

    return 0 if fail_count == 0 else 1


def process_info_command(args) -> int:
    """Process the info subcommand."""
    input_path = Path(args.input)

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        return 1

    # Determine if it's a file or directory
    if input_path.is_file():
        show_video_info(input_path)
    else:
        # Get list of video files to process
        video_files = get_video_files(input_path, SUPPORTED_FORMATS)

        if not video_files:
            print(f"Error: No supported video files found in: {input_path}")
            print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
            return 1

        # Show info for each video file
        for video_file in video_files:
            show_video_info(video_file)
    return 0

def process_inject_hdr_metadata_command(args) -> int:
    """Process the inject-hdr-metadata subcommand."""
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        return 1

    # Determine output file
    if output_path is None:
        output_path = input_path.with_suffix('.mkv')

    video = Video(filepath=input_path)

    hdr_metadata: pars_encoder_settings.HdrMetadata = pars_encoder_settings.get_hdr_metadata_from_args(args)

    injector = HdrMetadataInjector(
        video=video,
        target_file=output_path,
        metadata=hdr_metadata,
    )

    success: bool = injector.inject_metadata()

    return 0 if success else 1


def main() -> None:
    """Main entry point for CLI."""
    args = pars_args.parse_args()
    config.debug_mode = getattr(args, 'debug', False) or False
    if config.debug_mode:
        print_debug("Debug mode enabled")

    code: int = 0
    # Execute the corresponding subcommand
    if args.command == 'info':
        code = process_info_command(args)
    elif args.command == 'convert':
        code = process_convert_command(args)
    elif args.command == 'inject-hdr-metadata':
        code = process_inject_hdr_metadata_command(args)
    elif args.command == 'calc_maxcll':
        input_path = Path(args.input)
        if not input_path.exists():
            print_err(f"Input path does not exist: {input_path}")
            sys.exit(1)
        calc_maxcll(video_path=str(input_path))
    else:
        print_err(f"Unknown command: {args.command}")
        code = 1

    shutdown: bool = getattr(args, 'shutdown', False) or False
    if shutdown:
        shutdown_system()

    if config.debug_mode and code != 0:
        print_debug("skipping sys.exit()")
        return
    sys.exit(code)


if __name__ == '__main__':
    main()
