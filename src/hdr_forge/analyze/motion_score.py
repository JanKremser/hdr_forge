import cv2
import numpy as np
import sys

def compute_motion_score(video_path, resize_width=320, resize_height=180):
    """
    Calculates a motion score for a video.
    Score = Average motion between frames, normalized to 0..1
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video '{video_path}'")
        return None

    ret, prev_frame = cap.read()
    if not ret:
        print("Error: Could not read first frame")
        return None

    # Resize frames and convert to grayscale
    prev_frame = cv2.resize(prev_frame, (resize_width, resize_height))
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    motion_values = []

    frame_count = 1
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (resize_width, resize_height))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Absolute difference between frames
        diff = cv2.absdiff(gray, prev_gray)
        diff = diff.astype(np.float32)  # Convert to float32 for compatibility
        motion_level = np.mean(diff) / 255.0  # Normalize to 0..1
        motion_values.append(motion_level)

        prev_gray = gray
        frame_count += 1

    cap.release()

    if not motion_values:
        return 0.0

    # Average motion score
    motion_score = np.mean(motion_values)
    return motion_score

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python motion_score.py <video_file>")
        sys.exit(1)

    video_file = sys.argv[1]
    score = compute_motion_score(video_file)
    print(f"Motion score for '{video_file}': {score:.3f}")
