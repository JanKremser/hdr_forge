from hdr_forge.analyze.detect_logo import MaskResult
from hdr_forge.cli.cli_output import ANSI_BLUE, color_str, print_err

import numpy as np

def _print_mask_unicode(mask: np.ndarray, max_width=70):
    """
    Outputs an ndarray as a mask with Unicode half-block characters (▀▄█).
    Creates square pixels in the terminal without distortion.

    Two vertical pixels (top/bottom) are combined into one character:
    - 0,0 -> ' '
    - 1,0 -> '▀'
    - 0,1 -> '▄'
    - 1,1 -> '█'
    """

    # Convert to bool
    mask = mask.astype(bool)

    h, w = mask.shape

    # Limit width (proportional)
    if w > max_width:
        scale = max_width / w
        new_w = max_width
        new_h = max(1, int(h * scale))

        # Resize
        y_idx = np.linspace(0, h, new_h + 1).astype(int)
        x_idx = np.linspace(0, w, new_w + 1).astype(int)

        resized = np.zeros((new_h, new_w), dtype=bool)
        for i in range(new_h):
            for j in range(new_w):
                block = mask[y_idx[i]:y_idx[i+1], x_idx[j]:x_idx[j+1]]
                resized[i, j] = block.mean() > 0.5

        mask = resized
        h, w = mask.shape

    # Make height an even number
    if h % 2 == 1:
        mask = mask[:-1]
        h -= 1

    # Character mapping
    for y in range(0, h, 2):
        upper = mask[y]
        lower = mask[y + 1]

        line = []
        for u, l in zip(upper, lower):
            if u and l:
                line.append("█")
            elif u and not l:
                line.append("▀")
            elif not u and l:
                line.append("▄")
            else:
                line.append(" ")
        print("".join(line))


def print_mask_infos(mask: MaskResult | None) -> None:
    """Print information about the detected logo mask.
    Args:

        mask: Detected logo mask result
    """
    color = ANSI_BLUE
    if mask is None:
        print_err(f"  Logo Mask: No mask created.")
        return

    print()
    print(f"{color_str('_', color)}" * 70)

    print(f"  Logo Detected:")
    if mask.region:
        print(f"    Region: {color_str(mask.region, color)}")
    print(f"    Position: x={color_str(str(mask.x), color)}, y={color_str(str(mask.y), color)}")
    print(f"    Size: width={color_str(str(mask.width), color)}, height={color_str(str(mask.height), color)}")
    print(f"    Mask Path:")
    if mask.mask is not None:
        _print_mask_unicode(mask=mask.mask, max_width=140)

    print(f"{color_str('_', color)}" * 70)
