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
            value_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in value)
        else:
            value_str = f'"{value}"' if ' ' in value else value
        parts.append(f'-{key} {value_str}')
    return ' '.join(parts)
