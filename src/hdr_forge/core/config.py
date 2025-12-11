import os
from pathlib import Path
import sys

from hdr_forge.cli.cli_output import print_warn

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def _get_project_root():
    # 2) PyInstaller One-Folder oder One-File mit externen Daten:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

    # 3) Normaler Python-Run:
    return os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

PROJECT_ROOT = _get_project_root()

debug_mode: bool = False

global_temp_dir: Path = Path(f"{PROJECT_ROOT}/.hdr_forge_temp")

def set_global_temp_directory(input_path_str: str | None, output_path_str: str | None) -> None:
    global global_temp_dir
    input_path: Path | None = None
    if input_path_str:
        input_path = Path(input_path_str)

    output_path: Path | None = None
    if output_path_str:
        output_path = Path(output_path_str)

    base_temp_folder: Path = Path("/tmp/.hdr_forge_temp")

    if output_path:
        if output_path.is_dir():
            base_temp_folder = output_path / f".hdr_forge_temp_{output_path.stem}"
        else:
            base_temp_folder = output_path.parent / f".hdr_forge_temp_{output_path.stem}"
    elif input_path and input_path.exists():
        if input_path.is_dir():
            base_temp_folder = input_path / f".hdr_forge_temp_{input_path.stem}"
        else:
            base_temp_folder = input_path.parent / f".hdr_forge_temp_{input_path.stem}"

    global_temp_dir = base_temp_folder

def get_global_temp_directory(sub_folder: str | None = None) -> Path:
    """Get or create temporary directory for intermediate files.

    Creates a temp directory in the same location as target_file:
    {target_file_dir}/.hdr_forge_temp_{target_file_stem}/

    Returns:
        Path to temporary directory
    """
    temp_dir: Path = global_temp_dir
    if sub_folder:
        temp_dir = temp_dir / sub_folder
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def clear_global_temp_directory() -> None:
    """Remove temporary directory and all its contents.

    Deletes the temp directory created by get_temp_directory().
    Handles errors gracefully and prints warnings if cleanup fails.
    """
    import shutil

    temp_dir: Path = global_temp_dir

    if temp_dir.exists() and temp_dir.is_dir():
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary files: {temp_dir}")
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory {temp_dir}: {e}")
