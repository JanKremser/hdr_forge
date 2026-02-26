"""GUI entry point for HDR Forge video converter."""

import re
import sys
import threading
from argparse import Namespace
from pathlib import Path
from tkinter import Tk, messagebox, filedialog, StringVar, IntVar, Button, Frame
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

# Optional PIL support for rounded corners
try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# GTK4 Adwaita-inspired color palettes
_LIGHT: dict[str, str] = {
    'win_bg':       '#f6f5f4',
    'widget_bg':    '#ffffff',
    'border':       '#deddda',
    'fg':           '#2e2e2e',
    'label_title':  '#777777',
    'btn_bg':       '#e0dfe6',
    'btn_hover':    '#ccccd1',
    'btn_pressed':  '#b5b5ba',
    'accent':       '#3584e4',
    'accent_hover': '#4a96f5',
    'accent_press': '#2469be',
    'accent_fg':    '#ffffff',
    'status_bg':    '#eeeeec',
    'disabled_fg':  '#999999',
    'disabled_bg':  '#e8e8e5',
    'select_bg':    '#3584e4',
    'select_fg':    '#ffffff',
    'insert':       '#2e2e2e',
    'trough':       '#e0dfe6',
    'scroll_thumb': '#b0afb5',
    'scroll_hover': '#909095',
}

_DARK: dict[str, str] = {
    'win_bg':       '#1d1d1d',
    'widget_bg':    '#2e2e2e',
    'border':       '#484848',
    'fg':           '#deddda',
    'label_title':  '#aaaaaa',
    'btn_bg':       '#383838',
    'btn_hover':    '#484848',
    'btn_pressed':  '#585858',
    'accent':       '#3584e4',
    'accent_hover': '#4a96f5',
    'accent_press': '#2469be',
    'accent_fg':    '#ffffff',
    'status_bg':    '#242424',
    'disabled_fg':  '#777777',
    'disabled_bg':  '#2a2a2a',
    'select_bg':    '#3584e4',
    'select_fg':    '#ffffff',
    'insert':       '#deddda',
    'trough':       '#252525',
    'scroll_thumb': '#555555',
    'scroll_hover': '#707070',
}


def _detect_system_theme() -> str:
    """Detect the OS dark/light mode preference. Returns 'dark' or 'light'."""
    # Linux: gsettings (GNOME/GTK)
    try:
        import subprocess
        result = subprocess.run(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and 'dark' in result.stdout.lower():
            return 'dark'
        if result.returncode == 0:
            return 'light'
    except Exception:
        pass

    # Linux: GTK4 settings.ini fallback
    try:
        import configparser
        from pathlib import Path
        settings_paths = [
            Path.home() / '.config/gtk-4.0/settings.ini',
            Path.home() / '.config/gtk-3.0/settings.ini',
        ]
        for settings_path in settings_paths:
            if settings_path.exists():
                cfg = configparser.ConfigParser()
                cfg.read(settings_path)
                if cfg.getboolean('Settings', 'gtk-application-prefer-dark-theme', fallback=False):
                    return 'dark'
    except Exception:
        pass

    # Windows: registry
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize')
        value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        return 'light' if value == 1 else 'dark'
    except Exception:
        pass

    # macOS: defaults
    try:
        import subprocess
        result = subprocess.run(
            ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and 'dark' in result.stdout.lower():
            return 'dark'
    except Exception:
        pass

    return 'light'  # safe default


class RoundedButton:
    """A styled ttk.Button that looks modern (uses ttk for reliability)."""

    def __init__(self, parent, text="", bg_color="#ffffff", fg_color="#000000",
                 width=100, height=36, radius=8, command=None, font_size=9, bold=False, **kwargs):
        """Initialize styled button.

        Args:
            parent: Parent widget
            text: Button text
            bg_color: Background color (hex) - used for ttk style
            fg_color: Foreground/text color (hex) - used for ttk style
            width: Button width (ignored, for compatibility)
            height: Button height (ignored, for compatibility)
            radius: Corner radius (ignored, ttk doesn't support it)
            command: Click callback
            font_size: Font size
            bold: Bold text
        """
        self.text = text
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.font_size = font_size
        self.bold = bold
        self.photo_image = None

        # Store style name for later updates
        self.button_style = 'RoundedButton.TButton'

        # Create the actual ttk.Button
        self.button = ttk.Button(
            parent, text=text, command=command,
            style=self.button_style,
            **kwargs
        )

    def grid(self, **kwargs):
        """Grid layout wrapper."""
        return self.button.grid(**kwargs)

    def pack(self, **kwargs):
        """Pack layout wrapper."""
        return self.button.pack(**kwargs)

    def cget(self, key):
        """Get widget option."""
        if key == 'text':
            return self.text
        elif key == 'bg':
            return self.bg_color
        elif key == 'fg':
            return self.fg_color
        elif key == 'image':
            return self.photo_image
        elif key == 'width':
            return 10
        elif key == 'height':
            return 2
        elif key == 'compound':
            return 'center'
        return self.button.cget(key)

    def config(self, **kwargs):
        """Configure widget."""
        if 'text' in kwargs:
            self.text = kwargs['text']
        return self.button.config(**kwargs)

    def configure(self, **kwargs):
        """Alias for config (tk compatibility)."""
        return self.config(**kwargs)

    def set_colors(self, bg_color, fg_color):
        """Update button colors."""
        self.bg_color = bg_color
        self.fg_color = fg_color
        # Note: ttk button colors are set via styles, not direct config


def _create_rounded_button_image(width, height, color, text="", text_color="#000000", radius=8, font_size=9, bold=False):
    """Create a rounded rectangle image with text using PIL.

    Args:
        width: Image width
        height: Image height
        color: Background hex color string (e.g., '#3584e4')
        text: Button text
        text_color: Text hex color string
        radius: Corner radius
        font_size: Font size in points
        bold: Bold text

    Returns:
        PIL.Image or None if PIL not available
    """
    if not HAS_PIL:
        return None

    # Convert hex colors to RGB
    color_rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    text_rgb = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    # Create image with rounded corners
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle (x0, y0, x1, y1)
    draw.rounded_rectangle(
        [(0, 0), (width - 1, height - 1)],
        radius=radius,
        fill=color_rgb,
        outline=None
    )

    # Draw text on the image
    if text:
        font = None
        try:
            from PIL import ImageFont
            # Try to find a system font
            font_paths = [
                # Linux
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                # macOS
                '/Library/Fonts/Arial.ttf',
                # Windows
                'C:\\Windows\\Fonts\\arialbd.ttf' if bold else 'C:\\Windows\\Fonts\\arial.ttf',
            ]
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except (FileNotFoundError, OSError):
                    pass
        except ImportError:
            pass

        # Calculate text position (center)
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # Fallback: estimate text size
            text_width = len(text) * (font_size // 2)
            text_height = font_size

        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # Draw text
        draw.text((x, y), text, fill=text_rgb, font=font)

    return img


def _apply_theme(root, style, c, output_text):
    """Apply a color theme to all GUI widgets.

    Args:
        root: tkinter root window
        style: ttk.Style instance
        c: Color dictionary (either _LIGHT or _DARK)
        output_text: ScrolledText widget to style
    """
    # Root background
    root.configure(bg=c['win_bg'])

    # Combobox dropdown popup (plain tk.Listbox — only reachable via option_add)
    root.option_add('*TCombobox*Listbox.background',       c['widget_bg'], 80)
    root.option_add('*TCombobox*Listbox.foreground',       c['fg'],        80)
    root.option_add('*TCombobox*Listbox.selectBackground', c['select_bg'], 80)
    root.option_add('*TCombobox*Listbox.selectForeground', c['select_fg'], 80)
    root.option_add('*TCombobox*Listbox.relief',           'flat',         80)
    root.option_add('*TCombobox*Listbox.borderWidth',      '0',            80)

    # TFrame / TLabelframe
    style.configure('TFrame', background=c['win_bg'])
    style.configure('TLabelframe',
        background=c['win_bg'], bordercolor=c['border'],
        lightcolor=c['win_bg'], darkcolor=c['border'],
        relief='groove', borderwidth=1, padding=8)
    style.configure('TLabelframe.Label',
        background=c['win_bg'], foreground=c['label_title'],
        font=('TkDefaultFont', 9))

    # TLabel / Status.TLabel / Hint.TLabel
    style.configure('TLabel',
        background=c['win_bg'], foreground=c['fg'], font=('TkDefaultFont', 9))
    style.configure('Status.TLabel',
        background=c['status_bg'], foreground=c['fg'],
        relief='flat', padding=(6, 3), font=('TkDefaultFont', 9))
    style.configure('Hint.TLabel',
        background=c['win_bg'], foreground=c['label_title'],
        font=('TkDefaultFont', 8))

    # TEntry
    style.configure('TEntry',
        fieldbackground=c['widget_bg'], foreground=c['fg'],
        bordercolor=c['border'], lightcolor=c['widget_bg'], darkcolor=c['border'],
        insertcolor=c['insert'], selectbackground=c['select_bg'],
        selectforeground=c['select_fg'], relief='flat', borderwidth=1, padding=(5, 4))
    style.map('TEntry',
        bordercolor=[('focus', c['accent']), ('!focus', c['border'])],
        lightcolor=[('focus', c['accent']), ('!focus', c['widget_bg'])],
        fieldbackground=[('readonly', c['win_bg']), ('disabled', c['disabled_bg'])],
        foreground=[('disabled', c['disabled_fg'])])

    # TCombobox
    style.configure('TCombobox',
        fieldbackground=c['widget_bg'], background=c['btn_bg'], foreground=c['fg'],
        bordercolor=c['border'], lightcolor=c['widget_bg'], darkcolor=c['border'],
        arrowcolor=c['fg'], selectbackground=c['select_bg'], selectforeground=c['select_fg'],
        relief='flat', borderwidth=1, padding=(5, 4))
    style.map('TCombobox',
        fieldbackground=[('readonly', 'focus', c['widget_bg']),
                         ('readonly', c['widget_bg']), ('disabled', c['disabled_bg'])],
        foreground=[('readonly', 'focus', c['fg']), ('readonly', c['fg']),
                    ('disabled', c['disabled_fg'])],
        background=[('active', c['btn_hover']), ('pressed', c['btn_pressed'])],
        bordercolor=[('focus', c['accent']), ('!focus', c['border'])],
        arrowcolor=[('disabled', c['disabled_fg']), ('!disabled', c['fg'])])

    # TButton (Browse buttons)
    style.configure('TButton',
        background=c['btn_bg'], foreground=c['fg'], bordercolor=c['border'],
        lightcolor=c['btn_bg'], darkcolor=c['btn_bg'],
        relief='flat', borderwidth=1, padding=(8, 5), font=('TkDefaultFont', 9))
    style.map('TButton',
        background=[('active', c['btn_hover']), ('pressed', c['btn_pressed']),
                    ('disabled', c['disabled_bg'])],
        foreground=[('disabled', c['disabled_fg'])],
        bordercolor=[('focus', c['accent']), ('!focus', c['border'])],
        lightcolor=[('active', c['btn_hover']), ('!active', c['btn_bg'])],
        darkcolor=[('active', c['btn_hover']), ('!active', c['btn_bg'])])

    # RoundedButton.TButton (Custom styled button with more padding for rounded appearance)
    style.configure('RoundedButton.TButton',
        background=c['btn_bg'], foreground=c['fg'], bordercolor=c['border'],
        lightcolor=c['btn_bg'], darkcolor=c['btn_bg'],
        relief='flat', borderwidth=0, padding=(10, 8), font=('TkDefaultFont', 9))
    style.map('RoundedButton.TButton',
        background=[('active', c['btn_hover']), ('pressed', c['btn_pressed']),
                    ('disabled', c['disabled_bg'])],
        foreground=[('disabled', c['disabled_fg'])],
        bordercolor=[('focus', c['accent']), ('!focus', c['border'])])

    # Accent.TButton (Convert button - primary action)
    style.configure('Accent.TButton',
        background=c['accent'], foreground=c['accent_fg'],
        bordercolor=c['accent_press'], lightcolor=c['accent'], darkcolor=c['accent'],
        relief='flat', borderwidth=0, padding=(14, 8), font=('TkDefaultFont', 9, 'bold'))
    style.map('Accent.TButton',
        background=[('active', c['accent_hover']), ('pressed', c['accent_press']),
                    ('disabled', c['disabled_bg'])],
        foreground=[('disabled', c['disabled_fg'])],
        lightcolor=[('active', c['accent_hover']), ('!active', c['accent'])],
        darkcolor=[('active', c['accent_hover']), ('!active', c['accent'])])

    # AccentRounded.TButton (Accent version of RoundedButton)
    style.configure('AccentRounded.TButton',
        background=c['accent'], foreground=c['accent_fg'],
        bordercolor=c['accent_press'], lightcolor=c['accent'], darkcolor=c['accent'],
        relief='flat', borderwidth=0, padding=(14, 8), font=('TkDefaultFont', 9, 'bold'))
    style.map('AccentRounded.TButton',
        background=[('active', c['accent_hover']), ('pressed', c['accent_press']),
                    ('disabled', c['disabled_bg'])],
        foreground=[('disabled', c['disabled_fg'])])

    # ThemeToggle.TButton (moon/sun icon)
    style.configure('ThemeToggle.TButton',
        background=c['win_bg'], foreground=c['fg'], bordercolor=c['border'],
        lightcolor=c['win_bg'], darkcolor=c['win_bg'],
        relief='flat', borderwidth=1, padding=(4, 3), font=('TkDefaultFont', 10))
    style.map('ThemeToggle.TButton',
        background=[('active', c['btn_bg']), ('pressed', c['btn_hover'])],
        bordercolor=[('focus', c['accent']), ('!focus', c['border'])],
        lightcolor=[('active', c['btn_bg']), ('!active', c['win_bg'])],
        darkcolor=[('active', c['btn_bg']), ('!active', c['win_bg'])])

    # Horizontal.TProgressbar
    style.configure('Horizontal.TProgressbar',
        background=c['accent'], troughcolor=c['trough'],
        bordercolor=c['border'], lightcolor=c['accent'], darkcolor=c['accent'],
        relief='flat', thickness=6)

    # Horizontal.TScale
    style.configure('Horizontal.TScale',
        background=c['win_bg'], troughcolor=c['trough'],
        sliderlength=14, sliderrelief='flat')
    style.map('Horizontal.TScale',
        background=[('active', c['accent'])])

    # TScrollbar
    style.configure('TScrollbar',
        background=c['scroll_thumb'], troughcolor=c['trough'],
        bordercolor=c['border'], arrowcolor=c['fg'],
        lightcolor=c['scroll_thumb'], darkcolor=c['scroll_thumb'], relief='flat')
    style.map('TScrollbar',
        background=[('active', c['scroll_hover']), ('pressed', c['scroll_hover'])])

    # Non-ttk: ScrolledText (tk.Text + internal tk.Frame + tk.Scrollbar)
    output_text.configure(
        background=c['widget_bg'], foreground=c['fg'], insertbackground=c['insert'],
        selectbackground=c['select_bg'], selectforeground=c['select_fg'],
        highlightbackground=c['border'], highlightcolor=c['accent'],
        highlightthickness=1, font=('Courier', 9))
    output_text.frame.configure(background=c['widget_bg'], bd=0, highlightthickness=0)
    output_text.vbar.configure(
        background=c['scroll_thumb'], troughcolor=c['trough'],
        activebackground=c['scroll_hover'],
        relief='flat', borderwidth=0, highlightthickness=0, width=10)


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
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Theme state
        self.current_theme = _detect_system_theme()
        self.theme_toggle_btn = None
        self.rounded_buttons = []  # Track rounded buttons for theme updates

        # State flags
        self.encoding_in_progress = False
        self.stdout_redirect = None
        self.original_stdout = None

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
            height=15,
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
        """Update the quality label when the slider moves."""
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


def main_ui():
    """Main entry point for the GUI application."""
    root = Tk()
    app = HdrForgeGui(root)
    root.mainloop()


if __name__ == '__main__':
    main_ui()
