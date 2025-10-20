import subprocess
import numpy as np

def pq_to_nits(pq):
    # ITU-R BT.2100 EOTF (ST.2084)
    m1 = 2610 / 16384
    m2 = 2523 / 32
    c1 = 3424 / 4096
    c2 = 2413 / 128
    c3 = 2392 / 128
    L = ((np.maximum(pq ** (1/m2) - c1, 0)) / (c2 - c3 * pq ** (1/m2))) ** (1/m1)
    return L * 10000  # nits

def get_video_info(video_path):
    """Liest Videoinformationen mit ffprobe"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "csv=p=0:s=x", video_path
    ]
    out = subprocess.check_output(cmd).decode().strip()
    width, height, fps = out.split("x")
    width = int(width)
    height = int(height)
    fps = eval(fps)
    return width, height, fps

def detect_gpu_acceleration():
    """Versucht die beste Hardware-Decodierung zu finden"""
    # NVIDIA
    try:
        subprocess.run(["ffmpeg", "-hwaccels"], capture_output=True, check=True)
        result = subprocess.check_output(["ffmpeg", "-hwaccels"]).decode()
        if "cuda" in result:
            return "cuda"
        elif "qsv" in result:
            return "qsv"  # Intel/AMD QuickSync
    except Exception:
        pass
    return "cpu"

def build_ffmpeg_cmd(video_path, hw_accel):
    cmd = ["ffmpeg", "-i", video_path, "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
    if hw_accel != "cpu":
        if hw_accel == "cuda":
            cmd = ["ffmpeg", "-hwaccel", "cuda", "-i", video_path,
                   "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
        elif hw_accel == "qsv":
            cmd = ["ffmpeg", "-hwaccel", "qsv", "-c:v", "h264_qsv", "-i", video_path,
                   "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
    return cmd

def calculate_maxcll_maxfall(video_path, frame_sample_rate=10):
    width, height, fps = get_video_info(video_path)
    hw_accel = detect_gpu_acceleration()
    print(f"Analysiere {video_path} ({width}x{height}, {fps:.2f} fps) mit {hw_accel}-Beschleunigung …")

    ffmpeg_cmd = build_ffmpeg_cmd(video_path, hw_accel)
    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_size = width * height * 3 * 2  # 3 Kanäle * 2 Bytes (16 Bit)
    frame_idx = 0
    max_cll = 0.0
    max_fall = 0.0

    while True:
        raw = process.stdout.read(frame_size)
        if len(raw) < frame_size:
            break  # Ende des Videos

        if frame_idx % frame_sample_rate != 0:
            frame_idx += 1
            continue

        frame = np.frombuffer(raw, np.uint16).reshape((height, width, 3))
        rgb = frame.astype(np.float32) / 65535.0

        # Rec.2020 Luminanz
        luminance = 0.2627 * rgb[..., 0] + 0.6780 * rgb[..., 1] + 0.0593 * rgb[..., 2]

        # PQ → Nits
        nits = pq_to_nits(luminance)

        frame_max = np.max(nits)
        frame_avg = np.mean(nits)

        max_cll = max(max_cll, frame_max)
        max_fall = max(max_fall, frame_avg)

        print(f"Frame {frame_idx}: MaxCLL={frame_max:.2f} nits, AvgLuminance={frame_avg:.2f} nits", end='\r')

        frame_idx += 1

    process.wait()

    return round(max_cll, 2), round(max_fall, 2)

def calc_maxcll(video_path: str):
    maxcll, maxfall = calculate_maxcll_maxfall(video_path, frame_sample_rate=10)
    print(f"\nErgebnis:")
    print(f"  MaxCLL : {maxcll} nits")
    print(f"  MaxFALL: {maxfall} nits")
