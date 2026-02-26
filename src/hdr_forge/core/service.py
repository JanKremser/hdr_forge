import platform
import subprocess

from hdr_forge.cli.cli_output import print_warn

def build_cmd_array_to_str(cmd: list[str]) -> str:
    """Convert a command array to a single string for logging or display.
    Args:
        cmd (list[str]): Command array.
    Returns:
        str: Command as a single string.
    """
    return ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)

def build_cmd_pipe_str(cmd: list[list[str]]) -> str:
    """Convert a list of command arrays (pipeline) to a single string for logging or display.
    Args:
        cmd (list[list[str]]): List of command arrays.
    Returns:
        str: Pipeline command as a single string.
    """
    return ' | '.join(build_cmd_array_to_str(part) for part in cmd)

def build_ffmpeg_cmd_dict_to_str(cmd: dict[str, list[str] | str]) -> str:
    """Convert a command dictionary to a single string for logging or display.
    Args:
        cmd (dict[str, list[str] | str]): Command dictionary.
    Returns:
        str: Command as a single string.
    """
    parts = []
    for key, value in cmd.items():
        if isinstance(value, list):
            for v in value:
                value_str = f'"{v}"' if ' ' in v else v
                parts.append(f'-{key} {value_str}')
        else:
            value_str = f'"{value}"' if ' ' in value else value
            parts.append(f'-{key} {value_str}')
    return ' '.join(parts)

def shutdown_system() -> None:
    """Shutdown the system after a delay."""
    system: str = platform.system()

    try:
        if system == "Linux":
            print_warn("Shutting down the linux-system in 1 minute...")
            subprocess.run(["shutdown", "-h", "+1"])
        elif system == "Windows":
            print_warn("Shutting down the windows-system in 1 minute...")
            subprocess.run(["shutdown", "/s", "/t", "60"])
        else:
            print("Unbekanntes Betriebssystem")
    except Exception as e:
        print(f"Fehler: {e}")
