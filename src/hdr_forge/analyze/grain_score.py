import cv2
import numpy as np

def compute_grain_score(video_path, duration_sec=5, sample_rate=1, resize_width=640):
    """
    Berechnet den Grain-Score eines Videos.

    Args:
        video_path (str): Pfad zum Video
        duration_sec (int): Anzahl der Sekunden, die analysiert werden
        sample_rate (float): Sample alle x Sekunden
        resize_width (int): Breite, um Videoframes auf kleiner Größe zu analysieren (schneller)

    Returns:
        int: Grain Score Kategorie 0-3
        float: normalisierter Grain Score
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Video konnte nicht geöffnet werden")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(min(duration_sec * fps, cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    sample_interval = max(int(fps * sample_rate), 1)

    scores = []

    for i in range(0, total_frames, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break

        # Optional: kleiner skalieren für schnellere Analyse
        h, w = frame.shape[:2]
        scale = resize_width / w
        frame_small = cv2.resize(frame, (resize_width, int(h*scale)))

        # Luma (Helligkeit) extrahieren
        gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)

        # Highpass Filter: Original - Blur
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        highpass = gray.astype(np.float32) - blur.astype(np.float32)

        # Standardabweichung der hochfrequenten Komponenten
        score = np.std(highpass) / 255.0
        scores.append(score)

    cap.release()
    if not scores:
        return 0, 0.0

    avg_score = float(np.mean(scores))

    # Umrechnung in Kategorien 0-3
    if avg_score < 0.01:
        category = 0
    elif avg_score < 0.02:
        category = 1
    elif avg_score < 0.03:
        category = 2
    else:
        category = 3

    return category, avg_score


# -----------------------
# Beispiel
video_file = "/home/jan/Dokumente/GitHub/ehdr/samples/grain_test.mp4"
grain_cat, grain_val = compute_grain_score(video_file)
print(f"Grain Kategorie: {grain_cat}, Grain Score: {grain_val:.4f}")
