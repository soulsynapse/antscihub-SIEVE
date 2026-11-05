"""Encode speed, size, frame survival, sequential decode and random seek cost for a raw 1080p60 H.264
stream remuxed or re-encoded several ways."""
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2

src = Path(sys.argv[1])
tmp = Path(tempfile.mkdtemp())
raw = tmp / "raw.h264"
subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-an", "-c:v", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "h264", str(raw)])
fps = "60000/1001"

VARIANTS = [
    ("copy mp4", "mp4", ["-c", "copy"]),
    ("copy mkv", "mkv", ["-c", "copy"]),
    ("x264 ultrafast crf18", "mp4", ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18"]),
    ("x264 medium crf18", "mp4", ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]),
    ("x264 medium crf18 g=10", "mp4", ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", "10", "-bf", "0"]),
    ("x264 all-intra crf18", "mp4", ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", "1"]),
    ("nvenc p4 cq18", "mp4", ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "18", "-b:v", "0"]),
    ("nvenc p4 cq18 g=10", "mp4", ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-g", "10", "-bf", "0"]),
    ("hevc nvenc cq18", "mp4", ["-c:v", "hevc_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "18", "-b:v", "0"]),
    ("mjpeg q3", "avi", ["-c:v", "mjpeg", "-q:v", "3"]),
    ("ffv1 lossless", "mkv", ["-c:v", "ffv1", "-level", "3"]),
]


def decode_stats(path, seeks=20):
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
    claimed = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    t = time.perf_counter()
    n = 0
    while cap.read()[0]:
        n += 1
    seq = (time.perf_counter() - t) * 1000 / max(n, 1)
    rnd = random.Random(0)
    rows = [rnd.randrange(0, max(n, 1)) for _ in range(seeks)]
    t = time.perf_counter()
    ok = 0
    for r in rows:
        cap.set(cv2.CAP_PROP_POS_FRAMES, r)
        ok += bool(cap.read()[0])
    seek = (time.perf_counter() - t) * 1000 / seeks
    cap.release()
    return claimed, n, seq, seek, ok


print(f"source: {src.name}, raw stream {raw.stat().st_size / 2**20:.1f} MB")
print(f"{'variant':<24}{'encode s':>9}{'MB':>7}{'claimed':>8}{'decoded':>8}{'step ms':>9}{'seek ms':>9}")
for name, ext, args in VARIANTS:
    out = tmp / (name.replace(" ", "_").replace("=", "") + "." + ext)
    t = time.perf_counter()
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", fps, "-i", str(raw), *args, str(out)], capture_output=True, text=True)
    enc = time.perf_counter() - t
    if r.returncode:
        print(f"{name:<24} failed: {r.stderr.strip().splitlines()[-1][:60]}")
        continue
    claimed, n, seq, seek, ok = decode_stats(out)
    print(f"{name:<24}{enc:>9.1f}{out.stat().st_size / 2**20:>7.1f}{claimed:>8}{n:>8}{seq:>9.2f}{seek:>9.1f}" + ("" if ok == 20 else f"  {20 - ok} seeks failed"))
