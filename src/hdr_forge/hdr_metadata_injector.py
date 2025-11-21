

from pathlib import Path

from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.tools import mkvmerge
from hdr_forge.tools import hevc_hdr_editor
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.video import Video


class HdrMetadataInjector:

    def __init__(self, video: Video, target_file: Path, metadata: HdrMetadata):
        self.temp_dir: Path = get_global_temp_directory()

        self._input_file: Path = video.get_filepath()
        self._video: Video = video
        self._target_file: Path = target_file
        self._hdr_metadata: HdrMetadata = metadata

    def inject_metadata(self) -> bool:
        """Inject HDR metadata into the video without re-encoding.

        Returns:
            True if injection succeeded, False otherwise
        """
        temp_hdr_metadata = self.temp_dir / "hdr_metadata.json"
        hevc_hdr_editor.create_config_json_for_hevc_hdr_editor(
            hdr_metadata=self._hdr_metadata,
            output_json=temp_hdr_metadata,
        )

        return_hevc_file: bool = self._target_file.suffix.lower() == ".hevc"
        temp_hevc_output: Path = self.temp_dir / "temp_hdr_injected.hevc"

        hevc_hdr_editor.inject_hdr_metadata(
            input_path=self._input_file,
            config_json=temp_hdr_metadata,
            output_hevc=self._target_file if return_hevc_file else temp_hevc_output,
            total_frames=self._video.get_total_frames(),
            duration=self._video.get_duration_seconds(),
        )

        if return_hevc_file:
            temp_hevc_output.unlink(missing_ok=True)
            return True

        mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=temp_hevc_output,
            input_mkv=self._input_file,
            output_mkv=self._target_file,
        )

        temp_hevc_output.unlink(missing_ok=True)

        return True
