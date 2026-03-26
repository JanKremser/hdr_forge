"""Edit subcommand handler for in-place MKV file modifications."""

from pathlib import Path

from hdr_forge.cli.cli_output import print_conversion_summary, print_err, print_warn
from hdr_forge.edit_files.subtitle_editor import build_subtitle_track_edits
from hdr_forge.video import Video


# Supported formats for edit command (MKV only, as in-place editing requires specific container)
MKV_ONLY_FORMAT: list[str] = ['.mkv']


def edit_mkv_file(input_file: Path, subtitle_flags_str: str | None) -> bool:
    """Apply in-place edits to a single MKV file.

    Args:
        input_file: Path to the MKV file
        subtitle_flags_str: Raw --subtitle-flags string from CLI, or None

    Returns:
        True if all applied edits succeeded, False otherwise
    """
    from hdr_forge.cli.args.pars_encoder_settings import _get_subtitle_flags_from_string
    from hdr_forge.tools import mkvpropedit
    from hdr_forge.tools.mkvmerge import extract_container_info_json
    from hdr_forge.typedefs.encoder_typing import SubtitleMode

    if subtitle_flags_str is None:
        # Nothing to do
        return True

    subtitle_flags, overrides = _get_subtitle_flags_from_string(subtitle_flags_str)

    if subtitle_flags.mode == SubtitleMode.REMOVE:
        print_warn(
            f"'remove' mode is not applicable for in-place editing of {input_file.name} "
            "(track removal requires a remux). Skipping subtitle edits."
        )
        return True

    try:
        video = Video(filepath=input_file, with_out_rpu_extraction=True)
        source_subtitle_tracks = video.get_container_subtitles_tracks()

        if not source_subtitle_tracks:
            print_warn(f"No subtitle tracks found in {input_file.name}, skipping.")
            return True

        # For in-place editing, source == output (same file, same tracks)
        output_info = extract_container_info_json(input_file)
        output_subtitle_tracks = [
            t for t in output_info.tracks
            if t.type.value.lower() == 'subtitles'
        ]

        if not output_subtitle_tracks:
            return True

        edits = build_subtitle_track_edits(
            source_subtitle_tracks=source_subtitle_tracks,
            output_subtitle_tracks=output_subtitle_tracks,
            subtitle_flags=subtitle_flags,
            overrides=overrides,
        )

        if edits:
            success = mkvpropedit.set_subtitle_track_properties(input_file, edits)
            if success:
                print(f"Edited: {input_file.name}")
            return success

        return True

    except Exception as e:
        print_err(f"Error editing {input_file.name}: {e}")
        return False


def process_edit_command(args) -> int:
    """Process the edit subcommand.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from hdr_forge.main import get_video_files

    input_path = Path(args.input)
    subtitle_flags_str: str | None = getattr(args, 'subtitle_flags', None)

    if not input_path.exists():
        print_err(f"Error: Input path does not exist: {input_path}")
        return 1

    # Collect MKV files to process
    mkv_files: list[Path] = get_video_files(
        path=input_path,
        supported_formats=MKV_ONLY_FORMAT,
    )

    if not mkv_files:
        print_err(f"Error: No MKV files found at: {input_path}")
        return 1

    success_count = 0
    fail_count = 0

    for mkv_file in mkv_files:
        success = edit_mkv_file(
            input_file=mkv_file,
            subtitle_flags_str=subtitle_flags_str,
        )
        if success:
            success_count += 1
        else:
            fail_count += 1

    print_conversion_summary(success_count=success_count, fail_count=fail_count)
    return 0 if fail_count == 0 else 1
