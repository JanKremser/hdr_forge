"""Main CLI entry point for HDR Forge video converter."""

import sys
from pathlib import Path


from hdr_forge.analyze.detect_logo import LogoDetector, MaskResult
from hdr_forge.cli.args import pars_args, pars_encoder_settings
from hdr_forge.cli.cli_output import create_progress_bar, print_conversion_summary, print_debug, print_err, print_warn
from hdr_forge.cli.detect_logo import print_mask_infos
from hdr_forge.cli.encoder import print_encoding_params
from hdr_forge.cli.video import print_video_infos
from hdr_forge.core import config
from hdr_forge.core.service import shutdown_system
from hdr_forge.metadata_injector import MetadataInjector
from hdr_forge.tools import dovi_tool, hdr10plus_tool, hevc_hdr_editor
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfile
from hdr_forge.typedefs.encoder_typing import EncoderSettings, LogoRemovalAutoDetectMode, LogoRemovalMode, LogoRemovelSettings
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
    video_file: Path,
    target_file: Path,
    settings: EncoderSettings,
    count_video_file: int | None = None,
    total_video_files: int | None = None,
) -> bool | None:
    """Convert SDR or HDR10 video using ffmpeg with libx265.

    Args:
        video_file: input Video file
        target_file: Target output file path
        settings: Encoder settings containing all encoding parameters

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        video = Video(filepath=video_file, with_out_rpu_extraction=True)
        print_video_infos(video=video)

        # Create encoder with settings
        encoder = Encoder(
            video=video,
            target_file=target_file,
            settings=settings,
        )
        print_encoding_params(encoder=encoder)

        if count_video_file is not None and total_video_files is not None and not (
            total_video_files == 1 and count_video_file == 1
        ):
            procent: float = (count_video_file / total_video_files) * 100
            bar = create_progress_bar(
                percent=procent,
                text=f"Processing file {count_video_file} of {total_video_files}..."
            )
            print(bar)
            print()

        success: bool = encoder.convert()

        if success:
            print()  # New line after progress
            print(f"Success: {target_file.name}")

        return success
    except KeyboardInterrupt:
        print("\n" * 3)
        print_warn("Encoding cancelled by user.")
        return None
    except Exception as e:
        print(f"Error processing {video.get_filepath().name}: {e}")
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
    count_video_file = 0
    len_video_files: int = len(video_files)

    for video_file in video_files:
        count_video_file += 1
        # Determine output file
        out_file: Path = determine_output_file(video_file=video_file, output_path=output_path, is_batch=is_batch)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        success: bool | None = convert_video(
            video_file=video_file,
            target_file=out_file,
            settings=settings,
            count_video_file=count_video_file,
            total_video_files=len_video_files,
        )
        if success is None:
            # Conversion was cancelled
            break

        if success:
            success_count += 1
        else:
            fail_count += 1

    print_conversion_summary(success_count=success_count, fail_count=fail_count)

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

def process_extract_metadata_command(args) -> int:
    """Process the extract-dv-metadata subcommand."""
    input_path = Path(args.input)
    output_path: Path = Path(args.output) if args.output else input_path.parent

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        return 1

    success: bool = False
    try:
        video = Video(filepath=input_path, with_out_rpu_extraction=True)

        if video.is_hdr10_video():
            hdr_file_path: Path = output_path / f"{input_path.stem}_hdr10.json"
            hevc_hdr_editor.create_config_json_for_hevc_hdr_editor(
                hdr_metadata=video.get_hdr_metadata(),
                mastering_display_color_primaries=video.get_mastering_display_color_primaries(),
                output_json=hdr_file_path,
            )

        if video.is_hdr10plus_video():
            hdr10plus_tool.extract_hdr10plus_metadata(
                input_path=video.get_filepath(),
                output_path=output_path / f"{input_path.stem}_hdr10plus.json",
            )

        if video.is_dolby_vision_video():
            rpu_file_path: Path = output_path / f"{input_path.stem}.rpu"
            to_dv_profile_8: bool = args.getattr('to_dv_8', False)
            dovi_tool.extract_rpu(
                input_path=video.get_filepath(),
                output_rpu=rpu_file_path,
                total_frames=video.get_total_frames(),
                dv_profile_source=video.get_dolby_vision_profile(),
                dv_profile_encoding=DolbyVisionProfile._8 if to_dv_profile_8 else None,
            )
            dv_info: dovi_tool.DolbyVisionRpuInfo = dovi_tool.get_rpu_info(
                rpu_path=rpu_file_path,
            )
            if dv_info.profile_el:
                el_file_path: Path = output_path / f"{input_path.stem}_el.hevc"
                dovi_tool.extract_enhancement_layer(
                    input_path=video.get_filepath(),
                    output_el=el_file_path,
                    total_frames=video.get_total_frames(),
                )
    except Exception as e:
        print_err(f"Error processing {input_path.name}: {e}")
        return 1

    return 0 if success else 1

def process_inject_metadata_command(args) -> int:
    """Process the inject-dv-metadata subcommand."""
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Validate input
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        return 1

    success: bool = False
    try:
        video = Video(filepath=input_path, with_out_rpu_extraction=True)

        rpu_path_str: str | None = getattr(args, 'rpu', None)
        el_path_str: str | None = getattr(args, 'el', None)
        hdr10_path_str: str | None = getattr(args, 'hdr10', None)
        hdr10plus_path_str: str | None = getattr(args, 'hdr10plus', None)

        metadata_injector = MetadataInjector(
            video=video,
            target_file=output_path,
            rpu_file=Path(rpu_path_str) if rpu_path_str else None,
            el_file=Path(el_path_str) if el_path_str else None,
            hdr10plus_metadata=Path(hdr10plus_path_str) if hdr10plus_path_str else None,
            hdr_metadata=Path(hdr10_path_str) if hdr10_path_str else None,
        )
        success = metadata_injector.inject_metadata()
    except Exception as e:
        print_err(msg=f"Error processing {input_path.name}: {e}")
        return 1

    return 0 if success else 1

def process_detect_logo_command(args) -> int:
    """Process the detect-logo subcommand."""
    input_path = Path(args.input)

    export_path_str: str | None = getattr(args, 'export', None)
    export_path: Path | None = Path(export_path_str) if export_path_str else None

    # Validate input
    if not input_path.exists():
        print_err(f"Error: Input path does not exist: {input_path}")
        return 1

    # Determine if it's a file or directory
    if input_path.is_file() is False:
        print_err("Error: detect-logo command only supports single video files.")
        return 1

    video = Video(filepath=input_path, with_out_rpu_extraction=True)

    logo_detector = LogoDetector(video=video, logo_removal=LogoRemovelSettings(
        mode=LogoRemovalMode.DELOGO,
        position=LogoRemovalAutoDetectMode.AUTO,
    ))
    mask: MaskResult | None = logo_detector.create_mask()
    if export_path and mask:
        logo_detector.save_mask_image(output_path=export_path)
    print_mask_infos(mask=mask)

    return 0


def main() -> None:
    """Main entry point for CLI."""
    args = pars_args.parse_args()
    config.debug_mode = getattr(args, 'debug', False) or False
    if config.debug_mode:
        print_debug("Debug mode enabled")

    config.set_global_temp_directory(input_path_str=getattr(args, 'input', None), output_path_str=getattr(args, 'output', None))

    code: int = 0
    # Execute the corresponding subcommand
    if args.command == 'info':
        code = process_info_command(args)
    elif args.command == 'convert':
        code = process_convert_command(args)
    elif args.command == 'extract-metadata':
        code = process_extract_metadata_command(args)
    elif args.command == 'inject-metadata':
        code = process_inject_metadata_command(args)
    elif args.command == 'detect-logo':
        code = process_detect_logo_command(args)
    elif args.command == 'calc_maxcll':
        input_path = Path(args.input)
        if not input_path.exists():
            print_err(f"Input path does not exist: {input_path}")
            sys.exit(1)
        calc_maxcll(video_path=str(input_path))
    else:
        print_err(f"Unknown command: {args.command}")
        code = 1

    config.clear_global_temp_directory()

    shutdown: bool = getattr(args, 'shutdown', False) or False
    if shutdown:
        shutdown_system()

    if config.debug_mode and code != 0:
        print_debug("skipping sys.exit()")
        return
    sys.exit(code)


if __name__ == '__main__':
    main()
