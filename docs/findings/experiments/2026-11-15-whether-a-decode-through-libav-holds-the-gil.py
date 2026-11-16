"""One-off: whether a thread decoding through libav, by PyAV, holds the interpreter from another
thread as one decoding through cv2's plugin does not. PyAV is no requirement of the player: install
it somewhere and put that on PYTHONPATH. The main thread stands for the window's: it counts in a
bare Python loop, and separately wakes every millisecond and says how late it woke. Alone first;
then beside a thread reading ROWS rows in order by each way, the plugin's BGR, libav's frame
converted to BGR, libav's luma plane copied out; and beside a thread that holds the interpreter
outright, a Python loop, for what holding it looks like. Said of each: the count's rate as a share
of the rate alone, the lateness of a wake at the median, the 99th percentile and the worst, and the
ms a row the decode took with the main thread busy beside it. Run from the repo root:
python docs/findings/experiments/2026-11-15-whether-a-decode-through-libav-holds-the-gil.py <video> [rows]"""
import sys
import threading
import time

import av
import cv2
import numpy as np

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
WARM = 20


def plugin(done):
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    for _ in range(WARM):
        cap.read()
    done["ready"].set()
    t = time.perf_counter()
    for _ in range(ROWS):
        cap.read()
    done["took"] = time.perf_counter() - t
    cap.release()


def libav(take):
    def run(done):
        with av.open(path) as c:
            s = c.streams.video[0]
            s.thread_type = "AUTO"
            for i, f in enumerate(c.decode(s)):
                if i == WARM:
                    done["ready"].set()
                    t = time.perf_counter()
                take(f)
                if i == WARM + ROWS - 1:
                    break
            done["took"] = time.perf_counter() - t
    return run


def luma(f):
    p = f.planes[0]
    return np.frombuffer(p, np.uint8).reshape(p.height, p.line_size)[:, :p.width].copy()


def python_loop(done):
    done["ready"].set()
    t, n = time.perf_counter(), 0
    while time.perf_counter() - t < 1.5:
        n += 1
    done["took"] = time.perf_counter() - t


def beside(work):
    """(counts a second, [each wake's lateness in ms], the worker's seconds): the main thread counting
    for the first half of the worker's run and waking each ms for the rest."""
    done = {"ready": threading.Event()}
    th = None
    if work is not None:
        th = threading.Thread(target=work, args=(done,))
        th.start()
        done["ready"].wait()
    alive = (lambda: th.is_alive()) if th else (lambda: True)
    t, n = time.perf_counter(), 0
    while time.perf_counter() - t < 0.5 and alive():
        n += 1
    rate = n / (time.perf_counter() - t)
    late, until = [], time.perf_counter() + 0.5
    while time.perf_counter() < until and alive():
        t = time.perf_counter()
        time.sleep(0.001)
        late.append((time.perf_counter() - t - 0.001) * 1000)
    if th:
        th.join()
    return rate, late, done.get("took")


alone, late, _ = beside(None)
print(f"{path}: {ROWS} rows; alone the main thread counts {alone / 1e6:.2f} million a second, a wake "
      f"{np.median(late):.2f} ms late at the median, {np.percentile(late, 99):.2f} at the 99th, {max(late):.2f} at worst")
for name, work in [("the plugin's BGR", plugin), ("libav's frame converted to BGR", libav(lambda f: f.to_ndarray(format="bgr24"))),
                   ("libav's luma plane copied out", libav(luma)), ("a Python loop", python_loop)]:
    rate, late, took = beside(work)
    row = "" if work is python_loop else f"; the decode {took * 1000 / ROWS:.2f} ms a row"
    print(f"  beside {name}: counts at {rate / alone:.2f} of alone; a wake {np.median(late):.2f} ms late at the median, "
          f"{np.percentile(late, 99):.2f} at the 99th, {max(late):.2f} at worst, {len(late)} wakes{row}")
