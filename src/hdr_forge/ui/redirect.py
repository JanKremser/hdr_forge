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
        self._progress_line_count = 0  # lines in current progress/append block
        self._overwrite_next = False  # cursor-up received, content arrives in next write
        self._pending_cursor_ups = 0  # cursor-ups to apply when content arrives
        self._pending_progress_lines = []  # accumulated lines when in replace mode

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
        cursor_up_count = text.count('\x1b[1A')
        has_cursor_up = cursor_up_count > 0

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
            if not stripped or not all(c in '█░─│ ' for c in stripped):
                filtered_lines.append(line)

        # Handle progress block replacement or normal append
        if filtered_lines:
            if has_cursor_up or self._overwrite_next:
                # In replace mode: accumulate all lines until we exit replace mode
                self._pending_progress_lines.extend(filtered_lines)
                self._overwrite_next = False
                # Accumulate cursor-ups (add them up)
                if cursor_up_count > 0:
                    self._pending_cursor_ups += cursor_up_count
            else:
                # Exiting replace mode: flush any pending progress lines first
                if self._pending_progress_lines:
                    # Use the accumulated progress line count to determine deletion
                    lines_to_delete = self._progress_line_count
                    new_lines_count = len(self._pending_progress_lines)
                    self.root.after(0, self._update_progress, self._pending_progress_lines, lines_to_delete)
                    self._pending_progress_lines = []
                    self._pending_cursor_ups = 0
                    # Update progress count with newly inserted lines
                    self._progress_line_count = new_lines_count
                else:
                    # Normal append: reset progress count when entering normal append
                    self._progress_line_count = 0

                # Normal append: add each line individually
                for line in filtered_lines:
                    self.root.after(0, self._append_line, line)
                # Accumulate lines when appending normally
                self._progress_line_count += len(filtered_lines)
        elif has_cursor_up:
            # Cursor-up received but no content yet; content will arrive in next write()
            self._overwrite_next = True
            self._pending_cursor_ups += cursor_up_count

        return len(text) if isinstance(text, str) else 0

    def flush(self):
        """Flush any remaining buffer content."""
        # First, flush any pending progress lines
        if self._pending_progress_lines:
            # Delete the previous progress block lines
            lines_to_delete = self._progress_line_count
            new_lines_count = len(self._pending_progress_lines)
            self.root.after(0, self._update_progress, self._pending_progress_lines, lines_to_delete)
            self._pending_progress_lines = []
            self._pending_cursor_ups = 0
            # Update progress count with newly inserted lines
            self._progress_line_count = new_lines_count

        # Then handle any remaining buffer content
        if self.buffer.strip():
            stripped = self.buffer.strip()
            if not stripped or not all(c in '█░─│ ' for c in stripped):
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
            # "end - {N}l linestart" to "end" removes exactly N complete lines
            delete_start = f"end - {lines_to_delete + 1}l linestart"
            delete_end = "end"
            self.text_widget.delete(delete_start, delete_end)
        # Insert new progress lines
        for line in lines:
            self.text_widget.insert('end', line + '\n')
        self.text_widget.see('end')  # Auto-scroll to bottom
        self.text_widget.config(state='disabled')
