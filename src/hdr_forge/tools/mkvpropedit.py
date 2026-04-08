"""mkvpropedit wrapper for editing Matroska track properties."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from hdr_forge.cli.cli_output import print_debug
from hdr_forge.core.service import build_cmd_array_to_str
from hdr_forge.tools.helper import get_tool_path


@dataclass
class SubtitleTrackEdit:
    """Track selector and properties to edit via mkvpropedit."""

    track_selector: str  # e.g., "track:@3" (1-based absolute track number)
    name: str | None = None  # Track name/title
    flag_default: bool = False  # Set as default track
    flag_forced: bool = False  # Set as forced track


def set_subtitle_track_properties(
    output_file: Path,
    edits: list[SubtitleTrackEdit],
) -> bool:
    """Edit subtitle track properties in a Matroska file via mkvpropedit.

    Args:
        output_file: Path to output MKV file
        edits: List of SubtitleTrackEdit objects with track selectors and properties

    Returns:
        True if successful, False otherwise

    Raises:
        RuntimeError: If mkvpropedit is not installed
    """
    if not edits:
        # No edits needed
        return True

    mkvpropedit_exec: str = get_tool_path('mkvpropedit')

    try:
        # Build mkvpropedit command
        cmd: list[str] = [mkvpropedit_exec, str(output_file)]

        # Add each track edit
        for edit in edits:
            cmd.append("--edit")
            cmd.append(edit.track_selector)

            # Set track name if provided
            if edit.name is not None:
                cmd.append("--set")
                cmd.append(f"name={edit.name}")

            # Set default track flag
            cmd.append("--set")
            cmd.append(f"flag-default={'1' if edit.flag_default else '0'}")

            # Set forced track flag
            cmd.append("--set")
            cmd.append(f"flag-forced={'1' if edit.flag_forced else '0'}")

        print_debug(build_cmd_array_to_str(cmd))

        # Execute mkvpropedit
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if process.returncode != 0:
            raise RuntimeError(
                f"mkvpropedit failed: {process.stderr if process.stderr else 'unknown error'}"
            )

        return True

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure mkvpropedit is installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to edit MKV properties: {e}")
