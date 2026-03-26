"""Custom widgets for the HDR Forge GUI.

Provides styled button implementations with optional rounded corner support via PIL.
"""

from tkinter import ttk

# Optional PIL support for rounded corners
try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class RoundedButton:
    """A styled ttk.Button that looks modern (uses ttk for reliability)."""

    def __init__(self, parent, text="", bg_color="#ffffff", fg_color="#000000",
                 width=100, height=36, radius=8, command=None, font_size=9, bold=False):
        """Initialize styled button.

        Args:
            parent: Parent widget
            text: Button text
            bg_color: Background color (hex) - used for ttk style
            fg_color: Foreground/text color (hex) - used for ttk style
            width: Button width (ignored, for compatibility)
            height: Button height (ignored, for compatibility)
            radius: Corner radius (ignored, ttk doesn't support it)
            command: Click callback (optional)
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
        if command is not None:
            self.button = ttk.Button(
                parent, text=text, command=command,
                style=self.button_style
            )
        else:
            self.button = ttk.Button(
                parent, text=text,
                style=self.button_style
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
        """Update button colors.

        Args:
            bg_color: New background color (hex)
            fg_color: New foreground color (hex)
        """
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
