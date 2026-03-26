"""HDR Forge GUI package.

Provides a tkinter-based user interface for the HDR Forge video converter.
"""

from tkinter import Tk

from hdr_forge.ui.app import HdrForgeGui


def main_ui() -> None:
    """Main entry point for the GUI application."""
    root = Tk()
    HdrForgeGui(root)
    root.mainloop()


__all__ = ['main_ui', 'HdrForgeGui']
