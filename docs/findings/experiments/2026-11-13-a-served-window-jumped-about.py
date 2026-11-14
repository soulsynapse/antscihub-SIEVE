"""What a jump costs in a window served from a held run against one walked, offscreen: a copy of
video-tests/test.json and its held file in a temporary folder, the window placed about the clip and
the playhead moved about inside it, once with the run held and once with it let go.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-a-served-window-jumped-about.py

Prints, for each, the GUI thread's time inside set_window, the wait for the first frame after a
placing, the wait for a frame after each move of the playhead, and what a drag and two seconds of
play showed.
"""
import os
import pickle
import shutil
import statistics
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
DOC = os.path.join(ROOT, "video-tests", "test.json")
PATIENCE = 8.0      # s any one wait may take
ROWS = 300
STARTS = (4000, 19000, 9000, 26000, 14000)
MOVES = (211, 37, 150, 289, 90, 5)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document, held  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402


def wait(app, until, what):
    t0 = time.perf_counter()
    while not until():
        if time.perf_counter() - t0 > PATIENCE:
            sys.exit(f"FAILED waiting {PATIENCE:.0f} s for {what}")
        app.processEvents()
        time.sleep(0.0005)
    return (time.perf_counter() - t0) * 1000


def ms(xs):
    return f"median {statistics.median(xs):7.2f}  max {max(xs):7.2f} ms" if xs else "none"


def jumps(app, w, label, starts):
    placed, first, moved, walked = [], [], [], []
    shown = []
    set_frame = w.display.set_frame
    w.display.set_frame = lambda a, key=None: (shown.append(w.row), set_frame(a, key))[1]
    for s in starts:
        t0 = time.perf_counter()
        w.set_window(s, ROWS, playhead=s)
        placed.append((time.perf_counter() - t0) * 1000)
        first.append(wait(app, lambda: s in shown, f"the first frame of the window at {s}"))
        walked.append(wait(app, lambda: w.worker._win.i >= ROWS and w.worker._win.start == s, "the window walked"))
        for d in MOVES:
            del shown[:]
            w.goto(s + d, commit=True)
            moved.append(wait(app, lambda: s + d in shown, f"the frame at {s + d}"))
    s = starts[-1] + 2 * ROWS       # rows no pass has read
    w.set_window(s, ROWS, playhead=s)
    wait(app, lambda: s in shown and w.worker._win.i >= ROWS and w.worker._win.start == s,"the window the drag is in")
    del shown[:]
    for d in range(10, 250, 4):     # a drag: the guesses a held playhead makes, none committed
        w.seek(s + d, commit=False)
        app.processEvents()
    dragged = len(set(shown))
    w.goto(s, commit=True)
    wait(app, lambda: s in shown, "the frame at the window's start")
    del shown[:]
    w.toggle_play()
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 2.0:
        app.processEvents()
        time.sleep(0.0005)
    w.toggle_play()
    played, ticks = len(set(shown)), round(2.0 * w.fps)
    w.display.set_frame = set_frame
    print(f"{label}: spared {w._spared}")
    print(f"  set_window on the GUI thread     {ms(placed)}")
    print(f"  first frame after a placing      {ms(first)}")
    print(f"  the window walked after it       {ms(walked)}")
    print(f"  a frame after a playhead move    {ms(moved)}")
    print(f"  a drag over 60 rows showed {dragged} of them; 2 s of play showed {played} rows of {ticks} ticked")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    entries = discover(os.path.join(ROOT, "tools"))
    folder = tempfile.mkdtemp(prefix="sieve-jumps-")
    path = os.path.join(folder, "doc.json")
    shutil.copy(DOC, path)
    with open(held.path_for(DOC), "rb") as f:
        _, runs = pickle.load(f)
    tools = {e.name: e.module for e in entries if e.ok}
    video = document.load(DOC, tools).video
    held.File(held.path_for(path), held.stamp(video, held.tools_print(tools))).write(runs)   # under the tool files as they are now
    w = PlayerWindow(path, tools=entries)
    w.toggle_play()
    print(f"{w.count} rows at {w.fps:.2f} fps, {len(w.runs)} runs held: {[run[:2] for run in w.runs]}")
    if not w.runs:
        sys.exit("FAILED: the held file was not read; it is of other footage or other tool files")
    w._select("smooth")
    jumps(app, w, "served", STARTS)
    w.runs.take([])
    w._unwritten = False
    jumps(app, w, "walked", [s + 1000 for s in STARTS])     # rows the served pass left in no cache
    w._unwritten = False
    w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
