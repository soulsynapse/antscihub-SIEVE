"""One-off: what asking a capture for the frame's time after every read costs beside the read. ROWS
rows are read in order on one cv2 capture, each read and each CAP_PROP_POS_MSEC after it timed apart.
Says the mean of each and the share. Run from the repo root:
python docs/findings/experiments/2026-11-15-what-timing-every-step-costs.py <video> [rows]"""
import sys
import time

import cv2

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
read = asked = 0.0
done = 0
for _ in range(ROWS):
    t = time.perf_counter()
    ok, _f = cap.read()
    read += time.perf_counter() - t
    if not ok:
        break
    t = time.perf_counter()
    cap.get(cv2.CAP_PROP_POS_MSEC)
    asked += time.perf_counter() - t
    done += 1
cap.release()
print(f"{path}: {done} rows, a read {read / done * 1000:.3f} ms in the mean, its time {asked / done * 1e6:.2f} us, "
      f"{asked / read * 100:.3f}% of the read")
