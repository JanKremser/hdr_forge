"""Main GUI application for HDR Forge.

Provides the primary user interface for video conversion.
"""

import sys
import threading
from argparse import Namespace
from pathlib import Path
from tkinter import Tk, messagebox, filedialog, StringVar, IntVar, Frame
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from hdr_forge.ui.theme import _LIGHT, _DARK, _detect_system_theme, _apply_theme
from hdr_forge.ui.widgets import RoundedButton
from hdr_forge.ui.redirect import GuiStdoutRedirect


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
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Theme state
        self.current_theme = _detect_system_theme()
        self.theme_toggle_btn: ttk.Button
        self.rounded_buttons = []  # Track rounded buttons for theme updates

        # State flags
        self.encoding_in_progress = False
        self.stdout_redirect = None
        self.original_stdout = None
        self.output_text: ScrolledText

        # Build UI
        self._build_ui()

        # Apply initial theme
        initial_colors = _DARK if self.current_theme == 'dark' else _LIGHT
        initial_icon = '\u2600' if self.current_theme == 'dark' else '\U0001f319'
        self.theme_toggle_btn.configure(text=initial_icon)
        _apply_theme(self.root, self.style, initial_colors, self.output_text)
        self._update_rounded_buttons(initial_colors)
        self._update_convert_state()

    def _build_ui(self):
        """Build the user interface."""
        # Header with title and theme toggle
        header = ttk.Frame(self.root)
        header.pack(fill='x', padx=10, pady=(8, 0))

        ttk.Label(header, text="HDR Forge", font=('TkDefaultFont', 11, 'bold')).pack(side='left')

        toggle_frame = ttk.Frame(header, width=32, height=32)
        toggle_frame.pack_propagate(False)
        toggle_frame.pack(side='right', padx=4)
        self.theme_toggle_btn = ttk.Button(
            toggle_frame, text='\U0001f319', command=self._toggle_theme,
            style='ThemeToggle.TButton')
        self.theme_toggle_btn.pack(fill='both', expand=True)

        # Files section
        files_frame = ttk.LabelFrame(self.root, text="Files", padding=10)
        files_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(files_frame, text="Input:").grid(row=0, column=0, sticky='w')
        self.input_var = StringVar()
        self.input_var.trace_add('write', self._update_convert_state)
        self.input_entry = ttk.Entry(files_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=1, sticky='ew', padx=5)
        browse_input_btn = RoundedButton(
            files_frame, text="Browse", command=self._browse_input,
            bg_color=_LIGHT['btn_bg'], fg_color=_LIGHT['fg'],
            width=90, height=32, font_size=9)
        browse_input_btn.grid(row=0, column=2, padx=5)
        self.rounded_buttons.append((browse_input_btn, 'secondary'))

        ttk.Label(files_frame, text="Output:").grid(row=1, column=0, sticky='w', pady=5)
        self.output_var = StringVar()
        self.output_var.trace_add('write', self._update_convert_state)
        self.output_entry = ttk.Entry(files_frame, textvariable=self.output_var)
        self.output_entry.grid(row=1, column=1, sticky='ew', padx=5)
        browse_output_btn = RoundedButton(
            files_frame, text="Browse", command=self._browse_output,
            bg_color=_LIGHT['btn_bg'], fg_color=_LIGHT['fg'],
            width=90, height=32, font_size=9)
        browse_output_btn.grid(row=1, column=2, padx=5)
        self.rounded_buttons.append((browse_output_btn, 'secondary'))

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

        ttk.Label(settings_frame, text="Preset:").grid(row=3, column=0, sticky='w', pady=5)
        self.preset_var = StringVar(value='auto')
        self.preset_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.preset_var,
            values=['auto', 'film', 'film4k', 'film4k:fast', 'banding', 'video',
                    'action', 'animation', 'grain', 'grain:ffmpeg'],
            state='readonly',
            width=20
        )
        self.preset_combo.grid(row=3, column=1, sticky='w', padx=5)

        ttk.Label(settings_frame, text="Quality (CRF):").grid(row=4, column=0, sticky='w', pady=5)
        self.quality_scale_var = IntVar(value=0)
        self.quality_label_var = StringVar(value='Auto')
        self.quality_scale = ttk.Scale(
            settings_frame,
            variable=self.quality_scale_var,
            from_=0, to=51,
            orient='horizontal',
            length=160,
            command=self._on_quality_change
        )
        self.quality_scale.grid(row=4, column=1, sticky='w', padx=5)
        ttk.Label(settings_frame, textvariable=self.quality_label_var,
                  style='Hint.TLabel', width=5).grid(row=4, column=2, sticky='w', padx=2)

        ttk.Label(settings_frame, text="Speed:").grid(row=5, column=0, sticky='w', pady=5)
        self.speed_var = StringVar(value='')
        self.speed_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.speed_var,
            values=['', 'ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
                    'medium', 'medium:plus', 'slow', 'slow:plus', 'slower', 'veryslow'],
            state='readonly',
            width=20
        )
        self.speed_combo.grid(row=5, column=1, sticky='w', padx=5)

        settings_frame.columnconfigure(1, weight=1)

        # Control section (Convert button + progress bar)
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)

        self.convert_button = RoundedButton(
            control_frame, text="Convert", command=self._on_convert_click,
            bg_color=_LIGHT['accent'], fg_color=_LIGHT['accent_fg'],
            width=100, height=36, radius=8, font_size=9, bold=True)
        self.convert_button.button.config(style='AccentRounded.TButton')
        self.convert_button.pack(side='left', padx=5)
        self.rounded_buttons.append((self.convert_button, 'primary'))

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
            height=14,
            relief='flat',
            borderwidth=0,
            highlightthickness=1
        )
        self.output_text.pack(fill='both', expand=True, padx=10, pady=5)

        # Status bar
        self.status_var = StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var,
            style='Status.TLabel')
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

    def _update_rounded_buttons(self, colors):
        """Update colors for all rounded buttons.

        Args:
            colors: Color dictionary (_LIGHT or _DARK)
        """
        for btn_ref in self.rounded_buttons:
            btn, btn_type = btn_ref
            if btn_type == 'primary':  # Convert button
                btn.set_colors(colors['accent'], colors['accent_fg'])
            elif btn_type == 'secondary':  # Browse buttons
                btn.set_colors(colors['btn_bg'], colors['fg'])

    def _update_convert_state(self, *_args):
        """Enable Convert button only when both input and output are non-empty."""
        has_input = bool(self.input_var.get().strip())
        has_output = bool(self.output_var.get().strip())
        can_convert = has_input and has_output and not self.encoding_in_progress
        state = 'normal' if can_convert else 'disabled'
        self.convert_button.button.config(state=state)

    def _on_quality_change(self, value: str) -> None:
        """Update the quality label when the slider moves.

        Args:
            value: Quality slider value
        """
        int_val = int(float(value))
        self.quality_scale_var.set(int_val)   # snap to integer
        self.quality_label_var.set('Auto' if int_val == 0 else str(int_val))

    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        if self.current_theme == 'light':
            self.current_theme = 'dark'
            self.theme_toggle_btn.configure(text='\u2600')  # ☀ (sun)
            c = _DARK
        else:
            self.current_theme = 'light'
            self.theme_toggle_btn.configure(text='\U0001f319')  # 🌙 (moon)
            c = _LIGHT
        _apply_theme(self.root, self.style, c, self.output_text)
        self._update_rounded_buttons(c)

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
                preset=self.preset_var.get() or 'auto',
                hw_preset='cpu:balanced',
                quality=self.quality_scale_var.get() if self.quality_scale_var.get() > 0 else None,
                speed=self.speed_var.get() if self.speed_var.get().strip() else None,
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
        self.encoding_in_progress = False
        self._update_convert_state()

        if error_msg:
            self.status_var.set(error_msg)
            messagebox.showerror("Encoding Error", error_msg)
        elif success:
            self.status_var.set("Done")
            messagebox.showinfo("Success", "Video conversion completed successfully!")
        else:
            self.status_var.set("Failed")
            messagebox.showerror("Failed", "Video conversion failed. Check output for details.")
