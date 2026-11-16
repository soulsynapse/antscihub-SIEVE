"""One-off: what a row read in order takes through libav asked directly, by PyAV, against cv2's
plugin, each from a fresh open of the file and over the same ROWS rows after WARM read and not
timed. PyAV is no requirement of the player: install it somewhere and put that on PYTHONPATH. Said
for each, in ms a row and rows a second: the plugin's BGR; the plugin's unconverted plane; libav
with the frame decoded and nothing taken of it; libav's luma plane copied out; libav's frame
converted to BGR; and sieve_player's Decoder handing out bgr and luma, which is the plugin with the
Decoder's cache and its time asked at each step. Beside each after the plugin's, whether the last
row it handed out has the plugin's values. libav runs with the threads its codec sets, as the plugin does.
Stops at BUDGET seconds, the ways not reached left unsaid. Run from the repo root:
python docs/findings/experiments/2026-11-15-what-a-row-in-order-takes-through-libav-against-the-plugin.py <video> [rows]"""
import os
import sys
import time

import av
import cv2
import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player import decoder  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
WARM, BUDGET = 30, 45.0
began = time.perf_counter()
decoder.QUIET = True


def plugin(convert):
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, convert)
    try:
        for i in range(WARM + ROWS):
            if i == WARM:
                t = time.perf_counter()
            ok, f = cap.read()
            assert ok
        return time.perf_counter() - t, f
    finally:
        cap.release()


def libav(take):
    with av.open(path) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        for i, f in enumerate(c.decode(s)):
            if i == WARM:
                t = time.perf_counter()
            out = take(f)
            if i == WARM + ROWS - 1:
                return time.perf_counter() - t, out


def luma(f):
    p = f.planes[0]
    return np.frombuffer(p, np.uint8).reshape(p.height, p.line_size)[:, :p.width].copy()


def through_decoder(output):
    d = Decoder(path, cache_bytes=1 << 30)
    d.output = output
    try:
        for r in range(WARM + ROWS):
            if r == WARM:
                t = time.perf_counter()
            f = d.read(r)
        return time.perf_counter() - t, f
    finally:
        d.close()


ways = [("the plugin's BGR", lambda: plugin(1)),
        ("the plugin's plane, unconverted", lambda: plugin(0)),
        ("libav, the frame decoded and not taken", lambda: libav(lambda f: None)),
        ("libav's luma plane copied out", lambda: libav(luma)),
        ("libav's frame converted to BGR", lambda: libav(lambda f: f.to_ndarray(format="bgr24"))),
        ("the Decoder's bgr", lambda: through_decoder("bgr")),
        ("the Decoder's luma", lambda: through_decoder("luma"))]
print(f"{path}: {ROWS} rows in order after {WARM}")
handed = {}     # shape -> the last row the first way of that shape handed out, the plugin's
for name, run in ways:
    if time.perf_counter() - began > BUDGET:
        print("  out of time; the rest not run")
        break
    took, last = run()
    first = handed.setdefault(getattr(last, "shape", None), last)
    same = "" if last is None or first is last else ", the plugin's values" if np.array_equal(first, last) else ", OTHER VALUES than the plugin's"
    print(f"  {name}: {took * 1000 / ROWS:.2f} ms a row, {ROWS / took:.0f} rows a second, handing out {getattr(last, 'shape', None)}{same}")
