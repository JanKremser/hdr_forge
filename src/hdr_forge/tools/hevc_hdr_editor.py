from pathlib import Path
from typing import Optional

from hdr_forge.cli.cli_output import print_debug
from hdr_forge.core.config import PROJECT_ROOT
from hdr_forge.tools.helper import run_ffmpeg_tool_pipeline
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayColorPrimaries, MasterDisplayMetadata

def _get_hevc_hdr_editor_path() -> str:
    """Get path to hevc_hdr_editor executable.

    Looks for hevc_hdr_editor in project directory first, then falls back to system path.

    Returns:
        Path to hevc_hdr_editor executable as string
    """
    hevc_hdr_editor_path: Path = Path(PROJECT_ROOT) / "lib/hevc_hdr_editor"

    if hevc_hdr_editor_path.exists():
        return str(hevc_hdr_editor_path)
    else:
        return "hevc_hdr_editor"

def inject_hdr_metadata(
    input_path: Path,
    config_json: Path,
    output_hevc: Optional[Path] = None,
    total_frames: Optional[int] = None,
    duration: Optional[float] = None
) -> Path:
    """Inject HDR metadata into an HEVC bitstream using hevc_hdr_editor.

    Args:
        input_path: Path to the input video file
        config_json: Path to hevc_hdr_editor JSON config file
        output_hevc: Path to the output HEVC file. If None, appends '.hevc' to input_path
        total_frames: Total number of frames in the video (for progress tracking)
        duration: Total duration of the video in seconds (for progress tracking)

    Returns:
        Path to the HEVC file with injected HDR metadata
    """
    if output_hevc is None:
        output_hevc = input_path.with_suffix('.hevc')

    hevc_hdr_editor_exec = _get_hevc_hdr_editor_path()

    try:
        # Build hevc_hdr_editor command
        hevc_hdr_editor_cmd: list[str] = [
            hevc_hdr_editor_exec,
            '--config', str(config_json),
            '-',
            '-o', str(output_hevc)
        ]

        print()
        # Execute pipeline using helper function
        returncode, stderr = run_ffmpeg_tool_pipeline(
            input_path=input_path,
            tool_cmd=hevc_hdr_editor_cmd,
            process_name="Injecting HDR metadata:",
            total_frames=total_frames,
            duration=duration
        )

        if returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"hevc_hdr_editor inject HDR metadata failed: {error_msg}")

        if not output_hevc.exists():
            raise RuntimeError("HDR metadata injection output file was not created")

        print_debug(f"Inject HDR metadata successfully: {str(output_hevc)}")
        return output_hevc

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and hevc_hdr_editor are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to inject HDR metadata: {e}")

def create_config_json_for_hevc_hdr_editor(hdr_metadata: HdrMetadata, output_json: Path, mastering_display_color_primaries: MasterDisplayColorPrimaries | None = None) -> Path:
        """Create a JSON configuration file for hevc_hdr_editor based on HdrMetadata.

        Args:
            hdr_metadata (HdrMetadata): HDR metadata to include in the config.
            output_json (Path): Path to save the generated JSON config file.
        Returns:
            Path to the generated JSON config file.
        """
        import json

        master_display: MasterDisplayMetadata | None = hdr_metadata.mastering_display_metadata
        if master_display is None:
            master_display = MasterDisplayMetadata(
                r_x=0.0, r_y=0.0,
                g_x=0.0, g_y=0.0,
                b_x=0.0, b_y=0.0,
                wp_x=0.0, wp_y=0.0,
                min_lum=0.0,
                max_lum=0.0
            )

        # If present, the specific primaries to use.
        primaries_json: dict = {
            # X, Y display primaries in RGB order as 16 bit integers
            "display_primaries_x": [
                int(master_display.g_x * 50000),
                int(master_display.b_x * 50000),
                int(master_display.r_x * 50000),
            ],
            "display_primaries_y": [
                int(master_display.g_y * 50000),
                int(master_display.b_y * 50000),
                int(master_display.r_y * 50000),
            ],
            "white_point": [
                int(master_display.wp_x * 50000),
                int(master_display.wp_y * 50000)
            ]
        }

        cll: ContentLightLevelMetadata | None = hdr_metadata.content_light_level_metadata
        cll_json: dict = {
            # MaxCLL value to set
            "max_content_light_level": cll.maxcll or 0 if cll else 0,
            # MaxFALL value to set
            "max_average_light_level": cll.maxfall or 0 if cll else 0
        }

        config_data: dict = {
            "mdcv": {
                # Existing preset display primaries (BT.709, Display-P3 or BT.2020)
                # Options: "BT.709", "DisplayP3", "BT.2020"
                "preset": "DisplayP3",

                "primaries": {**primaries_json},

                # min, max mastering display luminance in nits
                "max_display_mastering_luminance": int(master_display.max_lum),
                "min_display_mastering_luminance": master_display.min_lum
            },

            # Replace the Content light level metadata
            "cll": {**cll_json}
        }

        if mastering_display_color_primaries is not None:
            config_data["mdcv"]["preset"] = mastering_display_color_primaries.value
            #del config_data["mdcv"]["primaries"]  # Use preset primaries
        else:
            del config_data["mdcv"]["preset"] # Use custom primaries only

        with open(output_json, 'w') as json_file:
            json.dump(config_data, json_file, indent=4)

        print_debug(f"Created hevc_hdr_editor config JSON: {str(output_json)}")
        return output_json
