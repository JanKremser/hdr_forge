"""GUI entry point for HDR Forge video converter."""

import re
import sys
import threading
from argparse import Namespace
from pathlib import Path
from tkinter import Tk, messagebox, filedialog, StringVar
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


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
        """Write text to the widget after stripping ANSI codes."""
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
        """Append a line to the text widget (must run in main thread)."""
        self.text_widget.config(state='normal')
        self.text_widget.insert('end', line + '\n')
        self.text_widget.see('end')  # Auto-scroll to bottom
        self.text_widget.config(state='disabled')


class HdrForgeGui:
    """Simple tkinter GUI for HDR Forge video converter."""

    def __init__(self, root):
        """Initialize the GUI.

        Args:
            root: tkinter root window
        """
        self.root = root
        self.root.title("HDR Forge - Video Converter")
        self.root.geometry("750x650")
        self.root.minsize(700, 580)

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        # State flags
        self.encoding_in_progress = False
        self.stdout_redirect = None
        self.original_stdout = None

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the user interface."""
        # Files section
        files_frame = ttk.LabelFrame(self.root, text="Files", padding=10)
        files_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(files_frame, text="Input:").grid(row=0, column=0, sticky='w')
        self.input_var = StringVar()
        self.input_entry = ttk.Entry(files_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Button(files_frame, text="Browse", command=self._browse_input).grid(row=0, column=2)

        ttk.Label(files_frame, text="Output:").grid(row=1, column=0, sticky='w', pady=5)
        self.output_var = StringVar()
        self.output_entry = ttk.Entry(files_frame, textvariable=self.output_var)
        self.output_entry.grid(row=1, column=1, sticky='ew', padx=5)
        ttk.Button(files_frame, text="Browse", command=self._browse_output).grid(row=1, column=2)

        files_frame.columnconfigure(1, weight=1)

        # Settings section
        settings_frame = ttk.LabelFrame(self.root, text="Settings", padding=10)
        settings_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(settings_frame, text="Video Codec:").grid(row=0, column=0, sticky='w')
        self.video_codec_var = StringVar(value='h265')
        self.video_codec_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.video_codec_var,
            values=['h265', 'h264', 'av1', 'copy'],
            state='readonly',
            width=20
        )
        self.video_codec_combo.grid(row=0, column=1, sticky='w', padx=5)

        ttk.Label(settings_frame, text="Audio:").grid(row=1, column=0, sticky='w', pady=5)
        self.audio_codec_var = StringVar(value='copy')
        self.audio_codec_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.audio_codec_var,
            values=['copy', 'remove', 'aac', 'ac3', 'eac3', 'flac'],
            state='readonly',
            width=20
        )
        self.audio_codec_combo.grid(row=1, column=1, sticky='w', padx=5)

        ttk.Label(settings_frame, text="Subtitles:").grid(row=2, column=0, sticky='w', pady=5)
        self.subtitle_var = StringVar(value='copy')
        self.subtitle_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.subtitle_var,
            values=['copy', 'remove', 'auto'],
            state='readonly',
            width=20
        )
        self.subtitle_combo.grid(row=2, column=1, sticky='w', padx=5)

        settings_frame.columnconfigure(1, weight=1)

        # Control section (Convert button + progress bar)
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)

        self.convert_button = ttk.Button(control_frame, text="Convert", command=self._on_convert_click)
        self.convert_button.pack(side='left', padx=5)

        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=5)

        # Output section
        output_label = ttk.Label(self.root, text="Output:")
        output_label.pack(anchor='w', padx=10, pady=(10, 0))

        self.output_text = ScrolledText(
            self.root,
            state='disabled',
            font=('Courier', 9),
            wrap='word',
            height=15
        )
        self.output_text.pack(fill='both', expand=True, padx=10, pady=5)

        # Status bar
        self.status_var = StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        self.status_bar.pack(fill='x', side='bottom')

    def _browse_input(self):
        """Open file dialog for input video."""
        filename = filedialog.askopenfilename(
            title="Select input video",
            filetypes=[
                ("Video files", "*.mkv *.mp4 *.m2ts *.ts"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_var.set(filename)
            # Auto-fill output if empty
            if not self.output_var.get():
                input_path = Path(filename)
                output_path = input_path.parent / f"{input_path.stem}.converted.mkv"
                self.output_var.set(str(output_path))

    def _browse_output(self):
        """Open file dialog for output video."""
        filename = filedialog.asksaveasfilename(
            title="Select output video path",
            defaultextension=".mkv",
            filetypes=[
                ("Matroska", "*.mkv"),
                ("MP4", "*.mp4"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.output_var.set(filename)

    def _on_convert_click(self):
        """Handle Convert button click."""
        input_path = self.input_var.get().strip()
        output_path = self.output_var.get().strip()

        # Validate inputs
        if not input_path:
            messagebox.showerror("Error", "Please select an input file.")
            return

        if not output_path:
            messagebox.showerror("Error", "Please select an output file.")
            return

        if not Path(input_path).exists():
            messagebox.showerror("Error", f"Input file does not exist: {input_path}")
            return

        # Disable Convert button and start progress
        self.encoding_in_progress = True
        self.convert_button.config(state='disabled')
        self.progress_bar.start(10)
        self.status_var.set("Encoding...")

        # Clear previous output
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', 'end')
        self.output_text.config(state='disabled')

        # Start encoding in background thread
        thread = threading.Thread(
            target=self._encoding_worker,
            args=(input_path, output_path),
            daemon=True
        )
        thread.start()

    def _encoding_worker(self, input_path: str, output_path: str):
        """Worker thread that runs the encoding job.

        Args:
            input_path: Input video file path
            output_path: Output video file path
        """
        # Lazy import to avoid circular imports
        from hdr_forge.cli.args.pars_encoder_settings import create_encoder_settings_from_args
        from hdr_forge.core import config
        from hdr_forge.main import convert_video

        success = False
        error_msg = None

        try:
            # Redirect stdout
            self.original_stdout = sys.stdout
            self.stdout_redirect = GuiStdoutRedirect(self.output_text, self.root)
            sys.stdout = self.stdout_redirect

            # Set temp directory
            config.set_global_temp_directory(input_path, output_path)

            # Build argparse.Namespace with all required fields
            ns = Namespace(
                input=input_path,
                output=output_path,
                video_codec=self.video_codec_var.get(),
                audio_codec=self.audio_codec_var.get(),
                audio_default='copy',
                subtitle_flags=self.subtitle_var.get(),
                hdr_sdr_format='auto',
                dv_profile='auto',
                preset='auto',
                hw_preset='cpu:balanced',
                quality=None,
                speed=None,
                grain=None,
                crop=None,
                scale=None,
                scale_mode='height',
                sample=None,
                encoder='auto',
                encoder_params=None,
                bit_depth='auto',
                color_primaries_flag='auto',
                try_fix=False,
                threads=None,
                vfilter=None,
                dar_ratio=None,
                master_display=None,
                max_cll=None,
                remove_logo=None,
                debug=False,
                shutdown=False,
            )

            # Create encoder settings
            settings = create_encoder_settings_from_args(ns)

            # Run conversion
            print(f"Starting conversion: {Path(input_path).name}")
            print()

            result = convert_video(
                video_file=Path(input_path),
                target_file=Path(output_path),
                settings=settings
            )

            success = result is True

            if success:
                print()
                print("=" * 60)
                print("Encoding completed successfully!")
                print("=" * 60)
            else:
                print()
                print("=" * 60)
                print("Encoding failed or was cancelled.")
                print("=" * 60)

        except SystemExit as e:
            # Catch sys.exit() calls in encoder code
            if e.code != 0:
                error_msg = f"Encoding error (exit code {e.code})"
            # Otherwise it's a normal exit, treat as success
            else:
                success = True

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print()
            print(f"Exception: {error_msg}")

        finally:
            # Restore stdout
            if self.stdout_redirect:
                self.stdout_redirect.flush()
            if self.original_stdout:
                sys.stdout = self.original_stdout

            # Clear temp directory
            try:
                from hdr_forge.core import config as config_module
                config_module.clear_global_temp_directory()
            except Exception:
                pass

            # Notify main thread
            self.root.after(0, self._on_encoding_done, success, error_msg)

    def _on_encoding_done(self, success: bool, error_msg: str | None):
        """Called in main thread when encoding completes.

        Args:
            success: True if encoding succeeded
            error_msg: Error message if encoding failed, None otherwise
        """
        self.progress_bar.stop()
        self.convert_button.config(state='normal')
        self.encoding_in_progress = False

        if error_msg:
            self.status_var.set(error_msg)
            messagebox.showerror("Encoding Error", error_msg)
        elif success:
            self.status_var.set("Done")
            messagebox.showinfo("Success", "Video conversion completed successfully!")
        else:
            self.status_var.set("Failed")
            messagebox.showerror("Failed", "Video conversion failed. Check output for details.")


def main_ui():
    """Main entry point for the GUI application."""
    root = Tk()
    app = HdrForgeGui(root)
    root.mainloop()


if __name__ == '__main__':
    main_ui()
