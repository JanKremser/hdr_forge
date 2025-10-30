

from pathlib import Path

from hdr_forge.tools import mkvmerge
from hdr_forge.tools import hevc_hdr_editor
from hdr_forge.typedefs.video_typing import HdrMetadata


class HdrMetadataInjector:

    def __init__(self, input_file: Path, target_file: Path, metadata: HdrMetadata):
        self._input_file: Path = input_file
        self._target_file: Path = target_file
        self._hdr_metadata: HdrMetadata = metadata

    def _get_temp_directory(self) -> Path:
        """Get or create temporary directory for intermediate files.

        Creates a temp directory in the same location as target_file:
        {target_file_dir}/.hdr_forge_temp_{target_file_stem}/

        Returns:
            Path to temporary directory
        """
        temp_dir = self._target_file.parent / f".hdr_forge_temp_{self._target_file.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def _cleanup_temp_directory(self) -> None:
        """Remove temporary directory and all its contents.

        Deletes the temp directory created by _get_temp_directory().
        Handles errors gracefully and prints warnings if cleanup fails.
        """
        import shutil

        temp_dir = self._target_file.parent / f".hdr_forge_temp_{self._target_file.stem}"

        if temp_dir.exists() and temp_dir.is_dir():
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary files: {temp_dir}")
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory {temp_dir}: {e}")

    def inject_metadata(self) -> bool:
        """Inject HDR metadata into the video without re-encoding.

        Returns:
            True if injection succeeded, False otherwise
        """
        temp_hdr_metadata = self._get_temp_directory() / "hdr_metadata.json"
        hevc_hdr_editor.create_config_json_for_hevc_hdr_editor(
            hdr_metadata=self._hdr_metadata,
            output_json=temp_hdr_metadata,
        )
        temp_hevc_output = self._get_temp_directory() / "temp_hdr_injected.hevc"
        hevc_hdr_editor.inject_hdr_metadata(
            input_path=self._input_file,
            config_json=temp_hdr_metadata,
            output_hevc=temp_hevc_output,
        )

        mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=temp_hevc_output,
            input_mkv=self._input_file,
            output_mkv=self._target_file,
        )

        self._cleanup_temp_directory()

        return True
