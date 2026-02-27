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
        self._progress_line_count = 0  # lines in the current overwritable block
        self._overwrite_next = False  # cursor-up received, content arrives in next write

    def write(self, text):
        """Write text to the widget after stripping ANSI codes.

        Args:
            text: Text to write

        Returns:
            Number of characters written
        """
        if not text:
            return len(text) if isinstance(text, str) else 0

        # Count cursor-up sequences before stripping (indicates progress block overwrite)
        has_cursor_up = text.count('\x1b[1A') > 0

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

        # Get complete lines and filter out progress-bar-only lines
        complete_lines = lines[:-1]
        filtered_lines = []
        for line in complete_lines:
            stripped = line.strip()
            # Skip lines that are only progress bar characters
            if stripped and not all(c in '█░─│ ' for c in stripped):
                filtered_lines.append(line)

        # Handle progress block replacement or normal append
        if filtered_lines:
            if has_cursor_up or self._overwrite_next:
                # Schedule in-place replacement of previous progress block
                self.root.after(0, self._update_progress, filtered_lines, self._progress_line_count)
                self._overwrite_next = False
            else:
                # Normal append: add each line individually
                for line in filtered_lines:
                    self.root.after(0, self._append_line, line)
            # Update progress line count for next potential overwrite
            self._progress_line_count = len(filtered_lines)
        elif has_cursor_up:
            # Cursor-up received but no content yet; content will arrive in next write()
            self._overwrite_next = True

        return len(text) if isinstance(text, str) else 0

    def flush(self):
        """Flush any remaining buffer content."""
        if self.buffer.strip():
            stripped = self.buffer.strip()
            if stripped and not all(c in '█░─│ ' for c in stripped):
                if self._overwrite_next:
                    # Overwrite previous progress block if cursor-up was received
                    self.root.after(0, self._update_progress, [self.buffer], self._progress_line_count)
                    self._overwrite_next = False
                else:
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

    def _update_progress(self, lines, lines_to_delete):
        """Replace previous progress block with new lines (must run in main thread).

        Args:
            lines: List of new lines to insert
            lines_to_delete: Number of lines from the end to delete
        """
        self.text_widget.config(state='normal')
        if lines_to_delete > 0:
            # Delete previous progress block (N lines from end).
            # Tkinter adds empty lines after newlines, so we need to adjust: use
            # "end - (N+1)l linestart" to properly delete N content lines.
            delete_start = f"end - {lines_to_delete + 1}l linestart"
            self.text_widget.delete(delete_start, "end")
            # After deletion, ensure content ends with a newline for proper line separation
            remaining = self.text_widget.get("1.0", "end")
            if remaining and not remaining.endswith('\n'):
                self.text_widget.insert('end', '\n')
        # Insert new progress lines
        for line in lines:
            self.text_widget.insert('end', line + '\n')
        self.text_widget.see('end')  # Auto-scroll to bottom
        self.text_widget.config(state='disabled')
