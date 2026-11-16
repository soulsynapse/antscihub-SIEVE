"""One-off: what the timeline strip's paint takes as a clip walk's signal grows, offscreen, no window
shown. A signal of noise with a gate, over a clip of 345595 rows on a strip 1800 px wide, is set at
five lengths; at each, the paint after 120 more rows, the best of five, and the paint of a strip
that has drawn nothing yet. Then strips grown in steps are held against strips painted whole, pixel
for pixel, over four clips: many rows a column, a row a column, and columns between the rows. Run
from the repo root:
python docs/findings/experiments/2026-11-15-what-a-strip-paint-costs-as-a-clip-walk-grows.py"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

import numpy as np
from PySide6.QtWidgets import QApplication

app = QApplication([])
from sieve_player.timeline import Strip

rng = np.random.default_rng(0)
COUNT, WIDTH, STEP = 345595, 1800, 120


def strip(count, width):
    s = Strip()
    s.resize(width, Strip.H)
    s.set_count(count, 60.0)
    return s


def paint(s):
    t = time.perf_counter()
    s.grab()
    return (time.perf_counter() - t) * 1000


signal = (rng.random(COUNT) * 3).astype(np.float32)
gate = signal > 0.5
s = strip(COUNT, WIDTH)
for n in (20000, 80000, 160000, 240000, 330000):
    s.set_series({"count": (signal[:n], 0, gate[:n])}, "count")
    s.grab()
    grown = []
    for k in range(1, 6):
        s.set_series({"count": (signal[:n + k * STEP], 0, gate[:n + k * STEP])}, "count")
        grown.append(paint(s))
    whole = strip(COUNT, WIDTH)
    whole.set_series({"count": (signal[:n], 0, gate[:n])}, "count")
    print(f"{n // 1000:>4}k rows: {min(grown):5.2f} ms a paint after {STEP} more rows, {paint(whole):5.1f} ms whole")

paints = differ = 0
for count, width, steps in ((COUNT, WIDTH, 37), (5000, 700, 23), (90, 400, 11), (1000, 1000, 13)):
    signal = (rng.random(count) * 3).astype(np.float32)
    gate, other = signal > 0.7, (rng.random(count // 2 + 1) * 9).astype(np.float32)
    for gated in (False, True):
        grown = strip(count, width)
        for n in np.linspace(1, count, steps).astype(int):
            at = min(n + 5, count - 1)
            series = {"pinned": (other[:n // 2 + 1], 0, None), "selected": (signal[:n], 0, gate[:n] if gated else None)}
            more = {"selected": [(signal[at:], at, gate[at:] if gated else None)]} if n < count // 2 else {}
            whole = strip(count, width)
            for one in (grown, whole):
                one.set_series(series, "selected", more)
                one.set_window(int(n) // 2, 600)
            paints += 1
            differ += grown.grab().toImage() != whole.grab().toImage()
print(f"{paints} paints of a strip grown in steps against one painted whole: {differ} differ")
