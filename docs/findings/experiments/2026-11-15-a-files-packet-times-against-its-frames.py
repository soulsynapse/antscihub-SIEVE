"""One-off: whether the times of a file's packets, read by cv2 with no frame decoded, are the times
of its frames in order. Every packet of the video stream is grabbed on a capture opened with
CAP_PROP_FORMAT -1 and its CAP_PROP_POS_MSEC kept; sorted, those are compared with the
CAP_PROP_POS_MSEC after each of the first ROWS frames read in order on a capture that decodes. Says
the packets, how long reading them took, the file's size, how many times are distinct, the smallest
step between two, and the rows whose frame's time is not the sorted packet's. Run from the repo root:
python docs/findings/experiments/2026-11-15-a-files-packet-times-against-its-frames.py <video> [rows]"""
import os
import sys
import time

import cv2

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
t = time.perf_counter()
raw = cv2.VideoCapture(path, cv2.CAP_FFMPEG, [cv2.CAP_PROP_FORMAT, -1])
times = []
while raw.grab():
    times.append(raw.get(cv2.CAP_PROP_POS_MSEC))
raw.release()
took = time.perf_counter() - t
times.sort()
steps = [b - a for a, b in zip(times, times[1:])]

cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
claimed = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
off = []
for r in range(min(ROWS, len(times))):
    if not cap.read()[0]:
        off.append((r, "no frame"))
        break
    ms = cap.get(cv2.CAP_PROP_POS_MSEC)
    if abs(ms - times[r]) > 0.01:
        off.append((r, round(ms, 3), round(times[r], 3)))
cap.release()
print(f"{path}: {len(times)} packets in {took:.2f} s, {os.path.getsize(path) / 2**20:.0f} MB, the container claims {claimed} rows; "
      f"{len(set(times))} distinct times from {times[0]:.3f} ms, the smallest step {min(steps):.3f} ms, the largest {max(steps):.3f}; "
      f"of the first {min(ROWS, len(times))} rows in order {len(off)} with another time than the sorted packet's {off[:6] or ''}")
