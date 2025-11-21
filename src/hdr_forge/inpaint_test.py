import cv2
from pyinpaint import Inpaint
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
import numpy as np

def test_inpaint_correct(frame_path: Path, mask_path: Path, output_path: Path, ps: int = 7):
    """
    Testet PyInpaint auf einem einzelnen Frame und Maske (PNG)
    und speichert das tatsächlich inpainted Ergebnis als PNG.
    """
    # Prüfen, dass die Dateien existieren
    if not frame_path.exists():
        raise ValueError(f"Frame-Datei existiert nicht: {frame_path}")
    if not mask_path.exists():
        raise ValueError(f"Masken-Datei existiert nicht: {mask_path}")

    # PyInpaint aufrufen
    inpainter = Inpaint(str(frame_path), str(mask_path), ps)

    # Korrektes Ergebnis abrufen
    result_rgb = inpainter(4, 1000, 5)

    #plt.imsave(output_path, result_rgb)

    result_uint8 = (result_rgb * 255).clip(0,255).astype(np.uint8)

    # RGB -> BGR für OpenCV
    result_bgr = cv2.cvtColor(result_uint8, cv2.COLOR_RGB2BGR)

    # mit OpenCV speichern
    cv2.imwrite("frame_result_cv2.png", result_bgr)


    print(f"Inpaint-Ergebnis gespeichert: {output_path}")


frame_path = Path("frame.png")
mask_path = Path("maske.png")
output_path = Path("frame_result.png")

test_inpaint_correct(frame_path, mask_path, output_path)
