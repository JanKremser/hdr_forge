"""Stdout redirection to GUI widgets.

Provides a file-like object that redirects output to a tkinter Text widget
while stripping ANSI color codes.
"""

import re


class GuiStdoutRedirect:
    """Redirects stdout to a tkinter Text widget, stripping ANSI codes."""

    def __init__(self, text_widget, root):
        """Initialize the redirect.

        Args:
            text_widget: tkinter.Text widget to write to
            root: tkinter root window (for thread-safe after() calls)
        """
        self.text_widget = text_widget
        self.root = root
        self.buffer = ""

    def write(self, text):
        """Write text to the widget after stripping ANSI codes.

        Args:
            text: Text to write

        Returns:
            Number of characters written
        """
        if not text:
            return len(text) if isinstance(text, str) else 0

        # Strip ANSI escape codes
        # Pattern: \033 (ESC) followed by [ and any number of digits/semicolons, then a letter
        cleaned = re.sub(r'\x1b\[[0-9;]*[mAKHFJG]', '', text)
        # Remove carriage returns (used for in-place overwrites)
        cleaned = cleaned.replace('\r', '')

        # Add to buffer
        self.buffer += cleaned

        # Process lines
        lines = self.buffer.split('\n')

        # Keep last incomplete line in buffer
        self.buffer = lines[-1]

        # Add complete lines to widget (skip empty lines and progress-bar-only lines)
        for line in lines[:-1]:
            stripped = line.strip()
            # Skip lines that are only progress bar characters
            if stripped and not all(c in '█░─│ ' for c in stripped):
                self.root.after(0, self._append_line, line)

        return len(text) if isinstance(text, str) else 0

    def flush(self):
        """Flush any remaining buffer content."""
        if self.buffer.strip():
            stripped = self.buffer.strip()
            if stripped and not all(c in '█░─│ ' for c in stripped):
                self.root.after(0, self._append_line, self.buffer)
            self.buffer = ""

    def _append_line(self, line):
        """Append a line to the text widget (must run in main thread).

        Args:
            line: Line of text to append
        """
        self.text_widget.config(state='normal')
        self.text_widget.insert('end', line + '\n')
        self.text_widget.see('end')  # Auto-scroll to bottom
        self.text_widget.config(state='disabled')
