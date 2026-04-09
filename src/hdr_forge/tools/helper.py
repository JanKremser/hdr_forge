"""Shared helper functions for external tool operations."""

from typing import Callable, Optional

from hdr_forge.core.config import PROJECT_ROOT
from pathlib import Path


def dovi_tool_progress_reader_thread(
    pipe,
    progress_callback: Optional[Callable[[float], None]],
    total_steps: int = 3
) -> None:
    """Thread function to read dovi_tool progress output.

    dovi_tool outputs progress by printing status lines when not attached to TTY:
    "Parsing RPU file..."
    "Processing input video for frame order info..."
    "Rewriting file with interleaved RPU NALs.."

    This thread counts each non-empty line as one progress step and calculates
    the percentage: (steps_done / total_steps) * 100

    Args:
        pipe: The stdout/stderr pipe from the dovi_tool subprocess
        progress_callback: Optional callback function to handle progress updates (receives percent: float)
        total_steps: Total number of expected steps/lines (default 3 for inject-rpu)
    """
    steps_done = 0

    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            steps_done += 1
            percent = min((steps_done / total_steps) * 100, 100.0)

            if progress_callback:
                progress_callback(percent)

    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def get_tool_path(tool_name: str) -> str:
    """Get path to an external tool executable.

    Looks for the tool in the project lib/ directory first, then falls back to system PATH.

    Args:
        tool_name: Name of the tool (e.g., 'dovi_tool', 'hevc_hdr_editor')

    Returns:
        Path to the tool executable as string
    """
    tool_path: Path = Path(PROJECT_ROOT) / f"lib/{tool_name}"
    if tool_path.exists():
        return str(tool_path)
    return tool_name
