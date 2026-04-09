"""ffmpeg/ffprobe utilities — treats ffmpeg as an external system tool."""

import os


def clean_subprocess_env() -> dict:
    """Return a copy of the current environment with LD_LIBRARY_PATH removed.

    Required when running as a PyInstaller bundle: OpenCV bundles its own
    libglib-2.0.so.0 and sets LD_LIBRARY_PATH to its temp dir, which causes
    symbol lookup errors in the system ffmpeg.

    Returns:
        dict: A copy of os.environ with LD_LIBRARY_PATH removed
    """
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    return env
