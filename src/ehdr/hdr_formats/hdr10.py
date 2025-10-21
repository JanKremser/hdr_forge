import subprocess
import numpy as np
from multiprocessing import Pool, cpu_count, Manager
import time
import math

from ehdr.cli.cli_output import create_progress_bar

SEGMENT_DURATION = 30  # Sekunden pro Segment (anpassbar)

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
    # Stream-Infos
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

    # Dauer aus Format-Ebene
    cmd_dur = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    duration = float(subprocess.check_output(cmd_dur).decode().strip())

    return width, height, fps, duration

def detect_gpu_acceleration():
    try:
        result = subprocess.check_output(["ffmpeg", "-hwaccels"]).decode()
        if "cuda" in result:
            return "cuda"
        elif "qsv" in result:
            return "qsv"
    except Exception:
        pass
    return "cpu"

def build_ffmpeg_cmd(video_path, start, duration, hw_accel):
    base = ["-ss", str(start), "-t", str(duration), "-i", video_path,
            "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
    if hw_accel == "cpu":
        cmd = ["ffmpeg"] + base
    elif hw_accel == "cuda":
        # Wichtig: keine hwaccel_output_format cuda, damit rgb48le im CPU-Space ankommt
        cmd = ["ffmpeg", "-hwaccel", "cuda"] + base
    elif hw_accel == "qsv":
        cmd = ["ffmpeg", "-hwaccel", "qsv", "-c:v", "h264_qsv"] + base
    else:
        cmd = ["ffmpeg"] + base
    return cmd

def process_segment(video_path, start, duration, width, height, frame_sample_rate, hw_accel, progress_dict, segment_id):
    ffmpeg_cmd = build_ffmpeg_cmd(video_path, start, duration, hw_accel)
    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_size = width * height * 3 * 2  # rgb48le = 16 bit per channel
    total_read_frames = 0
    processed_frames = 0  # nur die Frames, die tatsächlich analysiert werden
    max_cll = 0.0
    max_fall = 0.0

    while True:
        if process.stdout is None:
            break

        raw = process.stdout.read(frame_size)
        if len(raw) < frame_size:
            break

        # gezählte gelesene Frames (unabhängig vom Sampling)
        total_read_frames += 1

        # Sampling: nur jedes n-te Frame verarbeiten
        if (total_read_frames - 1) % frame_sample_rate != 0:  # -1 weil wir bei 0 starten wollen
            continue

        # Jetzt wird wirklich verarbeitet
        processed_frames += 1
        frame = np.frombuffer(raw, np.uint16).reshape((height, width, 3))
        rgb = frame.astype(np.float32) / 65535.0

        luminance = 0.2627 * rgb[...,0] + 0.6780 * rgb[...,1] + 0.0593 * rgb[...,2]
        nits = pq_to_nits(luminance)

        max_cll = max(max_cll, float(np.max(nits)))
        max_fall = max(max_fall, float(np.mean(nits)))

        # Fortschritt (nur verarbeitete Frames)
        progress_dict[segment_id] = processed_frames

    process.wait()
    # sicherstellen, dass das Ende korrekt gemeldet wird
    progress_dict[segment_id] = progress_dict.get(segment_id, 0)
    return max_cll, max_fall

def calculate_maxcll_maxfall_parallel(video_path, frame_sample_rate=10):
    width, height, fps, duration = get_video_info(video_path)
    hw_accel = detect_gpu_acceleration()
    print(f"Analysiere {video_path} ({width}x{height}, {fps:.2f} fps, {duration:.2f}s) mit {hw_accel}")

    # Segmente erstellen
    segments = []
    start = 0.0
    segment_id = 0
    while start < duration:
        seg_duration = min(SEGMENT_DURATION, duration - start)
        segments.append((video_path, start, seg_duration, width, height, frame_sample_rate, hw_accel, segment_id, fps))
        start += SEGMENT_DURATION
        segment_id += 1

    manager = Manager()
    progress_dict = manager.dict()
    # initialisiere Fortschritt für alle Segmente mit 0 (wichtig für Summierung)
    for seg in segments:
        progress_dict[seg[7]] = 0

    # Berechne total_frames_estimate korrekt (Summe der tatsächlich zu verarbeitenden Frames)
    total_frames_estimate = 0
    for (_, _, seg_dur, _, _, fsr, _, seg_id, seg_fps) in segments:
        frames_in_segment = int(math.ceil(seg_dur * seg_fps))
        sampled = (frames_in_segment + fsr - 1) // fsr  # Ganzzahliges Ceil für sampling
        total_frames_estimate += sampled

    # Pool vorbereiten
    pool_args = [(v[0], v[1], v[2], v[3], v[4], v[5], v[6], progress_dict, v[7]) for v in segments]
    num_processes = min(cpu_count(), len(segments))
    pool = Pool(processes=num_processes)

    # Async Map starten
    results_async = pool.starmap_async(process_segment, pool_args)

    # Globale Fortschrittsanzeige
    start_time = time.time()
    frames_done = 0
    percent = 0.0
    total_frames_estimate = math.ceil((fps * duration) / frame_sample_rate)
    try:
        while not results_async.ready():
            frames_done = sum(progress_dict.get(i, 0) for i in range(len(segments)))
            elapsed = time.time() - start_time
            if frames_done > 0:
                est_total_time = elapsed / frames_done * total_frames_estimate
                remaining = est_total_time - elapsed
                eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
            else:
                eta = "--:--:--"

            percent = min((frames_done / total_frames_estimate) * 100 if total_frames_estimate > 0 else 100, 100.0)
            bar = create_progress_bar(percent=percent, width=40)
            print(f"{bar} {percent:.2f}% | ETA: {eta} | {frames_done}/{total_frames_estimate} Frames", end='\r')
            time.sleep(0.5)
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
        raise

    results = results_async.get()
    pool.close()
    pool.join()

    # final: setze frames_done = total_frames_estimate um 100% anzuzeigen
    frames_done = sum(progress_dict.get(i, 0) for i in range(len(segments)))
    percent = min((frames_done / total_frames_estimate) * 100 if total_frames_estimate > 0 else 100, 100.0)
    bar = create_progress_bar(percent=percent, width=40)
    print(f"{bar} {percent:.2f}% | ETA: 00:00:00 | {frames_done}/{total_frames_estimate} Frames", end='\r')

    # Ergebnis zusammenführen und sauber runden
    max_cll_val = max(r[0] for r in results) if results else 0.0
    max_fall_val = max(r[1] for r in results) if results else 0.0

    max_cll = float(round(float(max_cll_val), 2))
    max_fall = float(round(float(max_fall_val), 2))

    return max_cll, max_fall

def calc_maxcll(video_path: str):
    maxcll, maxfall = calculate_maxcll_maxfall_parallel(video_path=video_path, frame_sample_rate=24)
    print(f"\nErgebnis:")
    print(f"  MaxCLL : {maxcll:.2f} nits")
    print(f"  MaxFALL: {maxfall:.2f} nits")
