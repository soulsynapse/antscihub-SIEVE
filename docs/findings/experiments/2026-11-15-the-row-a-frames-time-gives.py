"""One-off: whether the frame's time after a read, CAP_PROP_POS_MSEC, gives the row that was read,
on any file. The first ROWS rows are read in order and the row by the time is compared with the
count; then, each on a fresh capture, a seek to every target of TARGETS and of a spread over the
rows held: what CAP_PROP_POS_FRAMES says before the read, the row read, found among the rows held,
and the row by the time after it. Stops reading at BUDGET seconds and says how far it got. Run from
the repo root:
python docs/findings/experiments/2026-11-15-the-row-a-frames-time-gives.py <video> [rows]"""
import sys
import time

import cv2
import numpy as np

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 400
BUDGET = 40.0
TARGETS = (0, 1, 2, 5, 12, 13, 29, 30, 31, 32, 59, 60, 61)
began = time.perf_counter()

cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
fps = cap.get(cv2.CAP_PROP_FPS)
h, w = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
ys, xs = slice(h // 4, 3 * h // 4, 8), slice(w // 4, 3 * w // 4, 8)


def by_time(c):
    return c.get(cv2.CAP_PROP_POS_MSEC) * fps / 1000


held, times = [], []
while len(held) < ROWS and time.perf_counter() - began < BUDGET / 2:
    ok, f = cap.read()
    if not ok:
        break
    held.append(f[ys, xs].copy())
    times.append(by_time(cap))
cap.release()
n = len(held)
offset = times[0]
wrong = [(r, round(t, 3)) for r, t in enumerate(times) if int(t - offset + 0.5) != r]
frac = max(abs(t - offset - round(t - offset)) for t in times)
same = sum(np.array_equal(held[r], held[r - 1]) for r in range(1, n))
print(f"{path}: fps {fps:.4f}, {n} rows in order; row 0's time is row {offset:.3f}; rows whose time gives another row "
      f"than the count: {len(wrong)} {wrong[:8]}; furthest a time lies from a whole row {frac:.4f}; "
      f"rows equal to the one before {same}")


def true(f):
    g = f[ys, xs]
    hits = [k for k, s in enumerate(held) if np.array_equal(g, s)]
    return hits[0] if len(hits) == 1 else (hits or None)


spread = [int(x) for x in np.linspace(62, n - 3, 14)] if n > 80 else []
print("target: said before the read, row read, row by the time after it")
bad_said = bad_time = done = 0
for t in sorted({*TARGETS, *spread}):
    if t >= n - 2 or time.perf_counter() - began > BUDGET:
        continue
    c = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    c.set(cv2.CAP_PROP_POS_FRAMES, t)
    said = int(c.get(cv2.CAP_PROP_POS_FRAMES))
    ok, f = c.read()
    was, timed = true(f) if ok else "no read", int(by_time(c) - offset + 0.5)
    c.release()
    done += 1
    bad_said += said != was
    bad_time += timed != was
    if said != was or timed != was:
        print(f"  {t}: {said}, {was}, {timed}")
print(f"{done} seeks: {bad_said} where what was said is not the row read, {bad_time} where the time is not; "
      f"{time.perf_counter() - began:.0f} s")
