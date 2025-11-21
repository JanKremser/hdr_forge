import os
from pathlib import Path


debug_mode: bool = False


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

session_temp_folder: str = os.path.join(CURRENT_DIR, ".hdr_forge_temp")

def set_session_temp_folder(input_path_str: str | None, output_path_str: str | None) -> None:
    input_path: Path | None = None
    if input_path_str:
        input_path = Path(input_path_str)

    output_path: Path | None = None
    if output_path_str:
        output_path = Path(output_path_str)

    if input_path and input_path.is_file():
        base_temp_folder = input_path.parent
    elif output_path and output_path.is_file():
        base_temp_folder = output_path.parent

    session_temp_folder = os.path.join(base_temp_folder, ".hdr_forge_temp")
