"""One-off for docs/findings/2026-11-15-a-cut-clips-rows-against-the-plates.md: where a seek on
video-tests/00000.MTS lands against where cv2 says it did. For each target, on a fresh capture: what
CAP_PROP_POS_FRAMES says before a read, the row the read returns, found among the file's first 130
rows read in order, and the row CAP_PROP_POS_MSEC gives after it; then the same for the read after.
Target 0 is sought after a seek to 40. Run from the repo root:
python docs/findings/experiments/2026-11-15-where-a-seek-on-the-mts-lands.py"""
import cv2, numpy as np
path = "video-tests/00000.MTS"
cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
seq = []
for _ in range(130):
    ok, f = cap.read(); seq.append(f[52:336:4, 964:1168:4].copy())
fps = cap.get(cv2.CAP_PROP_FPS)
def true(f):
    g = f[52:336:4, 964:1168:4]
    return next((k for k, s in enumerate(seq) if np.array_equal(g, s)), None)
print("target: said before read, true row read, POS_FRAMES after read, row by POS_MSEC after read")
for t in (0, 1, 12, 30, 31, 40, 61, 90):
    c = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    if t == 0:
        c.set(cv2.CAP_PROP_POS_FRAMES, 40); c.read()
    c.set(cv2.CAP_PROP_POS_FRAMES, t)
    said = int(c.get(cv2.CAP_PROP_POS_FRAMES))
    ok, f = c.read()
    print(t, ":", said, true(f), int(c.get(cv2.CAP_PROP_POS_FRAMES)), round(c.get(cv2.CAP_PROP_POS_MSEC) * fps / 1000, 2))
    ok, f = c.read()
    print("    next read:", true(f), int(c.get(cv2.CAP_PROP_POS_FRAMES)), round(c.get(cv2.CAP_PROP_POS_MSEC) * fps / 1000, 2))
    c.release()
