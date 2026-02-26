"""Theme management for the HDR Forge GUI.

Provides color palettes and theme application logic for GTK4 Adwaita-inspired styling.
"""

import subprocess
from pathlib import Path
from tkinter import ttk


# GTK4 Adwaita-inspired light color palette
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

# GTK4 Adwaita-inspired dark color palette
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
    """Detect the OS dark/light mode preference.

    Returns:
        'dark' or 'light' (defaults to 'light' if detection fails)
    """
    # Linux: gsettings (GNOME/GTK)
    try:
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
        result = subprocess.run(
            ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and 'dark' in result.stdout.lower():
            return 'dark'
    except Exception:
        pass

    return 'light'  # safe default


def _apply_theme(root, style: ttk.Style, c: dict[str, str], output_text) -> None:
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
