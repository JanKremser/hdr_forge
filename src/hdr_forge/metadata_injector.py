

from pathlib import Path

from hdr_forge.core.config import get_global_temp_directory
from hdr_forge.tools import dovi_tool, hdr10plus_tool, hevc_hdr_editor, mkvmerge
from hdr_forge.video import Video


class MetadataInjector:

    def __init__(self, video: Video, target_file: Path, rpu_file: Path | None = None, el_file: Path | None = None, hdr10plus_metadata: Path | None = None, hdr_metadata: Path | None = None):
        self._input_file: Path = video.get_filepath()
        self._video: Video = video
        self._target_file: Path = target_file

        self._rpu_file: Path | None = rpu_file
        self._el_file: Path | None = el_file
        self._dv_info: dovi_tool.DolbyVisionRpuInfo | None = dovi_tool.get_rpu_info(rpu_path=rpu_file) if rpu_file else None

        self._hdr10plus_metadata: Path | None = hdr10plus_metadata
        self._hdr_metadata: Path | None = hdr_metadata

    def inject_metadata(self) -> bool:
        """Inject Dolby Vision metadata into the video without re-encoding.

        Returns:
            True if injection succeeded, False otherwise
        """
        temp_dir: Path = get_global_temp_directory()

        if self._dv_info and self._dv_info.profile_el and self._el_file is None:
            raise ValueError("EL file is required for Dolby Vision profiles with enhancement layer.")

        hevc_file: Path | None = None

        if self._hdr_metadata is not None:
            # Inject HDR10 metadata first
            hevc_file = hevc_hdr_editor.inject_hdr_metadata(
                input_path=self._input_file,
                config_json=self._hdr_metadata,
                output_hevc=temp_dir / "hdr10.hevc",
                total_frames=self._video.get_total_frames(),
            )

        if hevc_file is None:
            # Extract HEVC from MKV if no HDR10 metadata injection was done
            hevc_file = dovi_tool.extract_base_layer(
                input_path=self._input_file,
                output_hevc=temp_dir / "extracted_video.hevc",
                total_frames=self._video.get_total_frames(),
            )

        if self._hdr10plus_metadata is not None:
            # Inject HDR10+ metadata
            assert hevc_file is not None
            hdr10plus_hevc_file: Path = hdr10plus_tool.inject_hdr10plus_metadata(
                input_path=hevc_file,
                hdr10plus_metadata_path=self._hdr10plus_metadata,
                output_path=temp_dir / "hdr10plus.hevc",
            )
            hevc_file.unlink(missing_ok=True)
            hevc_file = hdr10plus_hevc_file

        if self._rpu_file is not None:
            # Inject RPU into the HEVC file
            assert hevc_file is not None
            hevc_file = dovi_tool.inject_rpu(
                input_path=hevc_file,
                input_rpu=self._rpu_file,
                output_hevc=temp_dir / "dv_bl_rpu.hevc",
            )

        if self._el_file is not None:
            # Inject EL layer into the HEVC file
            assert hevc_file is not None
            bl_el_rpu_hevc: Path = dovi_tool.inject_dolby_vision_layers(
                bl_path=hevc_file,
                el_path=self._el_file,
                output_bl_el=temp_dir / "dv_bl_el_rpu.hevc",
            )
            hevc_file.unlink(missing_ok=True)
            hevc_file = bl_el_rpu_hevc

        # Mux the final HEVC file back into an MKV
        assert hevc_file is not None
        mkvmerge.mux_hevc_to_mkv(
            input_hevc_path=hevc_file,
            input_mkv=self._input_file,
            output_mkv=self._target_file,
        )

        return True
