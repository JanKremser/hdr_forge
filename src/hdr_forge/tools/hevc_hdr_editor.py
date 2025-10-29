import subprocess
import threading
from pathlib import Path
from typing import Optional

from hdr_forge.cli.cli_output import monitor_process_progress, print_debug
from hdr_forge.core.config import PROJECT_ROOT
from hdr_forge.core.service import build_cmd_pipe_str
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata

def get_hevc_hdr_editor_path() -> str:
    """Get path to hevc_hdr_editor executable.

    Looks for hevc_hdr_editor in project directory first, then falls back to system path.

    Returns:
        Path to hevc_hdr_editor executable as string
    """
    hevc_hdr_editor_path: Path = Path(PROJECT_ROOT) / "hevc_hdr_editor"

    if hevc_hdr_editor_path.exists():
        return str(hevc_hdr_editor_path)
    else:
        return "hevc_hdr_editor"

def inject_hdr_metadata(input_path: Path, config_json: Path, output_hevc: Optional[Path] = None) -> Path:
    """Inject HDR metadata into an HEVC bitstream using hevc_hdr_editor.
    Args:
        input_path (Path): Path to the input HEVC bitstream file.
        output_hevc (Optional[Path]): Path to the output HEVC file. If None, appends '.hevc' to input_path.
    Returns:
        Path to the HEVC file with injected HDR metadata.
    """
    if output_hevc is None:
        output_hevc = input_path.with_suffix('.hevc')

    hevc_hdr_editor_exec = get_hevc_hdr_editor_path()

    try:
        # Extract HEVC bitstream from video file and pipe to hevc_hdr_editor
        ffmpeg_cmd: list[str] = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-bsf:v', 'hevc_mp4toannexb',
            '-f', 'hevc',
            '-'
        ]

        hevc_hdr_editor_cmd: list[str] = [
            hevc_hdr_editor_exec,
            '--config', str(config_json),
            '-',
            '-o', str(output_hevc)
        ]

        print_debug(build_cmd_pipe_str([ffmpeg_cmd, hevc_hdr_editor_cmd]))

        # Create pipeline: ffmpeg | hevc_hdr_editor
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        hdr_hevc_hdr_process = subprocess.Popen(
            hevc_hdr_editor_cmd,
            stdin=ffmpeg_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Close ffmpeg stdout in parent to allow SIGPIPE to be sent
        if ffmpeg_process.stdout:
            ffmpeg_process.stdout.close()

        # Start a thread to monitor and show progress
        monitor_thread = threading.Thread(
            target=monitor_process_progress,
            args=(hdr_hevc_hdr_process, "Inject HDR metadata:"),
            daemon=True
        )
        monitor_thread.start()

        # Wait for hevc_hdr_editor to complete
        _stdout, stderr = hdr_hevc_hdr_process.communicate()

        # Wait for the monitor thread to finish
        monitor_thread.join(timeout=1.0)

        if hdr_hevc_hdr_process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"hevc_hdr_editor inject HDR metadata failed: {error_msg}")

        # Wait for ffmpeg to complete
        ffmpeg_process.wait()

        if not output_hevc.exists():
            raise RuntimeError("HADR10 Base Layer file was not created")

        print_debug(f"- Inject HDR metadata successfully: {str(output_hevc)}")
        return output_hevc

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Required tool not found: {e.filename}. "
            "Please ensure ffmpeg and hevc_hdr_editor are installed."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to inject HDR metadata: {e}")

def create_config_json_for_hevc_hdr_editor(hdr_metadata: HdrMetadata, output_json: Path) -> Path:
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
                int(master_display.r_x * 50000),
                int(master_display.g_x * 50000),
                int(master_display.b_x * 50000)
            ],
            "display_primaries_y": [
                int(master_display.r_y * 50000),
                int(master_display.g_y * 50000),
                int(master_display.b_y * 50000)
            ],
            "white_point": [
                int(master_display.wp_x * 10000),
                int(master_display.wp_y * 10000)
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

        with open(output_json, 'w') as json_file:
            json.dump(config_data, json_file, indent=4)

        print_debug(f"- Created hevc_hdr_editor config JSON: {str(output_json)}")
        return output_json
