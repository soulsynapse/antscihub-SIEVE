"""The Checks of docs/spec/held-results.md, offscreen: a copy of video-tests/purb-168-178.json in a
temporary folder, its window moved about and its clip walked in one PlayerWindow, and both read back
in a second.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-held-series.py

Says what each box asks for and exits 1 on the first that does not hold.
"""
import os
import pickle
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
PATIENCE = 40.0     # s any one wait may take
A, B, ROWS = 100, 300, 120

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document, held  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from sieve_player.worker import _Walk  # noqa: E402

STEPS = []          # (the walk's lane, the rows it was stepped up to), at every call


def wait(app, until, what):
    t0 = time.perf_counter()
    while not until():
        if time.perf_counter() - t0 > PATIENCE:
            sys.exit(f"FAILED waiting {PATIENCE:.0f} s for {what}")
        app.processEvents()
        time.sleep(0.01)


def walked(w):
    return w.worker._win.i >= w.worker._win.length > 0 and w.worker._win.start == w.window_[0]


def main():
    step = _Walk.step
    _Walk.step = lambda self, rows: (STEPS.append((self.name, rows)), step(self, rows))[1]
    app = QApplication.instance() or QApplication(sys.argv)
    entries = discover(os.path.join(ROOT, "tools"))
    tools = {e.name: e.module for e in entries if e.ok}
    folder = tempfile.mkdtemp(prefix="sieve-held-")
    path = os.path.join(folder, "doc.json")
    document.save(document.load(DOC, tools), path)
    file = held.path_for(path)

    a = PlayerWindow(path, tools=entries)
    a.toggle_play()
    a._select("track")
    for s in (A, B):
        a.set_window(s, ROWS)
        wait(app, lambda: any(run[:2] == (s, ROWS) for run in a.runs), f"the window at {s} held as a run")
    first = a.results["track"]["signal"].copy()
    del STEPS[:]
    a.set_window(A, ROWS)
    if not a._spared or len(a.results["track"]["signal"]) != ROWS:
        sys.exit("FAILED: the window moved back onto rows it walked is not served from the run")
    wait(app, lambda: walked(a), "the served window's frames, walked")
    if STEPS or a.worker._win.stack is not None or any(a.graph.peek(A + d) is None for d in (0, 7, ROWS - 1)):
        sys.exit(f"FAILED: a window on held rows stepped the chain, or its frames are not in the memo: {STEPS[:3]}")
    print("the served window's frames are walked into the memo, and no step of the chain")
    a._select("threshold")
    wait(app, lambda: "threshold" in a.plot.fields, "a frame node's field over the served window")
    a._select("track")
    if sorted(a.timeline.strip.held) != [(A, ROWS), (B, ROWS)]:
        sys.exit(f"FAILED: the strip's bar is over {a.timeline.strip.held}")
    drawn = sorted((s, len(v)) for v, s, _ in [a.timeline.strip.series["track"], *a.timeline.strip.more["track"]])
    if drawn != [(A, ROWS), (B, ROWS)]:      # the window's own, and the run its rows are not over
        sys.exit(f"FAILED: the strip draws the selection's signal over {drawn}")
    print(f"window at {A}, at {B}, and back at {A}: served from its run, no step of the chain; the strip's bar is over both")
    wait(app, lambda: os.path.exists(file), "the held file, written in a quiet moment")
    print(f"the file after the moves: {os.path.getsize(file)} bytes, {len(a.runs)} runs")

    a._show_size()
    line = a.pane.sizes["track"].text()
    a._toggle_clip()
    wait(app, lambda: any(run[:2] == (0, a.count) for run in a.runs), "the clip walk held as a run")
    clip = next(run for run in a.runs if run[:2] == (0, a.count))
    actual = len(pickle.dumps(clip[2]["track"], protocol=pickle.HIGHEST_PROTOCOL))
    print(f"track's card: {line!r}; track's result over the clip pickled alone: {actual} bytes")
    a.close()
    print(f"the file at close: {os.path.getsize(file)} bytes")

    del STEPS[:]
    b = PlayerWindow(path, tools=entries)
    b.toggle_play()
    b._select("track")
    b.set_window(B, ROWS)
    if not b._spared or "track" not in b.timeline.strip.series or len(b._clip_result("track")["signal"]) != b.count:
        sys.exit("FAILED: the second window is not served from the file, or the strip does not draw the clip's signal")
    wait(app, lambda: walked(b), "the second window's frames, walked")
    if STEPS or b.worker._win.stack is not None or b.worker._clip.i or b.timeline.strip.held != [(0, b.count)]:
        sys.exit(f"FAILED: the second session stepped the chain or walked the clip: {STEPS[:3]}")
    print(f"second window at {B}: served from the file, the clip's signal on the strip, no step and no clip row")

    held_before = len(b.runs)
    b.doc.add_node("count", id="counted")
    b.doc.connect("track", "counted")
    b.sync()
    wait(app, lambda: len(b.results.get("counted", {}).get("signal", ())) == ROWS, "the node added under track, stepped over the window")
    win = b.worker._win
    if not b._given or win.stack is not None or win.stepped["track"].bytes or not win.stepped["counted"].bytes:
        sys.exit("FAILED: a node added under track did not read track's held rows: the window's rows were walked, or track stepped again")
    if len(b.runs) != held_before:
        sys.exit("FAILED: a window stepped from held rows was held as a run of its own, those rows in it a second time")
    print("a node added under track: stepped from track's held rows, no row walked, track not stepped, and nothing held twice")
    b._toggle_clip()
    wait(app, lambda: len(b.clip_results.get("counted", {}).get("signal", ())) == b.count, "the clip walked for the added node")
    clip = b.worker._clip
    if clip.stack is not None or clip.stepped["track"].bytes or clip.stepped["counted"].rows != b.count:
        sys.exit("FAILED: the clip walk for the added node walked the clip's rows or stepped track again")
    print(f"the clip walked for it: {b.count} rows of the added node stepped from track's, no row walked")
    wait(app, lambda: any(run[:2] == (0, b.count) and "counted" in run[2] for run in b.runs), "that clip walk held")
    if sum(run[:2] == (0, b.count) for run in b.runs) != 1:
        sys.exit("FAILED: the clip run the added node's walk was given is still held beside the run that has its rows and more")
    t0 = time.perf_counter()
    b.clip_results = {}
    b._toggle_clip()
    wait(app, lambda: len(b.clip_results.get("counted", {}).get("signal", ())) == b.count, "a clip walk with every node held")
    if any(h.bytes for h in b.worker._clip.stepped.values()) or b.worker._clip.stack is not None:
        sys.exit("FAILED: a clip walk with every node held stepped one or walked a row")
    print(f"a clip walk asked with every node held: ended in {time.perf_counter() - t0:.2f} s with nothing stepped")
    del STEPS[:]

    was = dict(b.doc.node("track").params)
    b.doc.node("track").params = {**was, "min_rows": was["min_rows"] + 1}
    b._params_changed("track")
    turned = b._spared or b._clip_result("track") is not None or b.timeline.strip.held
    wait(app, lambda: b.results.get("track", {}).get("key") == b.graph.key("track") and len(b.results["track"]["signal"]) == ROWS,
         "the window walked under the turned knob")
    stepped = bool(STEPS)
    b.doc.node("track").params = was
    b._params_changed("track")
    if turned or not stepped or not b._spared:
        sys.exit("FAILED: a held run was served under another key, or not served under its own again")
    print("a knob turned: nothing held is served and the chain is stepped; turned back: served")
    b.close()

    whole = len(held.File(file, b._stamp).load())
    with open(file, "r+b") as f:
        f.truncate(os.path.getsize(file) - 16)
    c = PlayerWindow(path, tools=entries)
    if len(c.runs) != whole - 1 or any(len(r["signal"]) != rows for _, rows, results, _ in c.runs for r in results.values()):
        sys.exit("FAILED: a file cut short in its last record was not read as the runs before it")
    print(f"a file cut short in its last record: the {whole - 1} runs before it held")
    c._unwritten = False
    c.close()
    with open(file, "wb") as f:
        f.write(b"not a held file")
    c = PlayerWindow(path, tools=entries)
    if c.runs:
        sys.exit("FAILED: a file that does not read was read as runs")
    print("a file that does not read: nothing held")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
