"""What a second clip walk costs the frame nodes after an edit below the walked node, with and
without the walked rows a held cut hands a walk of it, under a memo large, a memo tiny, and the
plate's cache tiny beside it: gray hands out the plate's own luma plane, which the memo holds as a
reference into that cache. The miniature's document and clip (docs/playground/sim/miniature.py):
video, gray, a banded reduce gating a period of gray, reduce `below` and smooth below it. A clip
walk is turned to its end, then one node's param is moved, smooth's reach or below's method, and
the walk that follows is counted by the lane each turn served: gray's runs, the plate decoder's
reads, the keeper's answers, and the legs each lane began and those handed rows; beside them the
plate's decodes and the cuts held under the edited node's new key. The window is the first cut
alone, so the clip lane's legs are not walked behind the window's over the same rows. The
worker's thread is never started: its turns are taken here, one at a time. Each cell is a fresh
player over its own clip, store and keeper folder, under a temp folder.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-21-what-walked-rows-save-a-rewalk.py
"""
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRATCH = tempfile.mkdtemp(prefix="sieve-rewalk-")
os.environ.update(QT_QPA_PLATFORM="offscreen", SIEVE_STORE=os.path.join(SCRATCH, "store"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import budget, decoder, held, result_keeper, store, window, worker  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.stream import HAND  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

CUTS, PERIOD, KEPT = 40, 8, 4
TINY_GB = "0.0001"      # about 100 KB: some 30 of gray's 3 KB rows, the memo's and the plate cache's

store.CHOICE = os.path.join(SCRATCH, "store.txt")
decoder.read_frame_times_ahead = lambda path, then=None: None
decoder.STORE = None
decoder.QUIET = True
held.File.write = lambda self, *a: []
window.TELL = 0.0
Worker.start = lambda self, *a: None
window.PlayerWindow.ask_unsaved = lambda self: "discard"
app = QApplication([])
TOOLS = [e for e in discover("tools") if e.ok]
GRAY = next(e.module for e in TOOLS if e.name == "gray")

counts, lane = Counter(), [lambda: None]     # (what, the lane the worker's turn serves) -> how many; the open player's lane
run, read, ask, start = GRAY.run, decoder.Decoder.read, result_keeper.Keeper.ask, worker._Legs._start


def counted_run(frames, row, params):
    counts["gray", lane[0]()] += 1
    return run(frames, row, params)


def counted_read(self, row):
    counts["read", lane[0]()] += 1
    return read(self, row)


def counted_ask(self, *a):
    got = ask(self, *a)
    counts["kept", lane[0]()] += got is not None
    return got


def counted_start(self, leg, sub, ask):
    start(self, leg, sub, ask)
    counts["legs", self.walk.name] += 1
    counts["handed legs", self.walk.name] += self.walk.handed is not None


GRAY.run, decoder.Decoder.read, result_keeper.Keeper.ask, worker._Legs._start = counted_run, counted_read, counted_ask, counted_start
held_periods = window.held_periods


def unhanded(*a, **k):
    return {cut: h._replace(handed=None) for cut, h in held_periods(*a, **k).items()}


def edit(params):
    if "reach" in params:
        params["reach"] += 2
    else:
        params["method"] = "max"


EDITS = ("smooth", "below")     # below the head, whose own result a held cut gives; the head, which reads the walked rows


def clip(path):
    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for r in range(CUTS * PERIOD):
        wr.write(np.full((48, 64, 3), 200 if r % PERIOD < KEPT else 20, np.uint8))
    wr.release()
    return str(path)


def document(path, video):
    doc = D.Document(video=video)
    doc.add_node(D.VIDEO_TOOL)
    for nid, tool, src, into in (("gray", "gray", D.VIDEO_TOOL, None), ("gate", "reduce", "gray", None), ("period", "period", "gray", None),
                                 ("below", "reduce", "period", None), ("smooth", "smooth", "below", None), (None, None, "gate", "gate")):
        if tool is not None:
            doc.add_node(tool, (0.0, 100.0 * len(doc.nodes)), None, nid)
        doc.connect(src, nid or "period", *([into] if into else []))
    doc.node("gate").band = (100.0, 255.0)
    D.save(doc, path)
    return str(path)


def settled(win):
    for _ in range(4):
        w, g = win.worker, win.graph
        while True:
            with w._cv:
                turn = w._turn()
            if turn is None:
                break
            for job, act in turn[1]:
                g.serving(turn[0], job.name)
                act()
        app.processEvents()


def cell(handed, tiny, edited):
    """The counts by lane over the walk after the edit, the memo's limit, the plate's decodes
    then, and the cuts held under smooth's new key."""
    name = f"{edited}-{'handed' if handed else 'unhanded'}-{'+'.join(tiny) or 'large'}"
    folder = Path(SCRATCH) / name
    folder.mkdir()
    os.environ["SIEVE_RESULTS"] = str(folder / "results")
    for holder, env in budget.OVERRIDES.items():
        os.environ.pop(env, None)
        if holder in tiny:
            os.environ[env] = TINY_GB
    budget.here.cache_clear()
    window.held_periods = held_periods if handed else unhanded
    win = window.PlayerWindow(document(folder / "doc.json", clip(folder / "v.avi")), "t", TOOLS)
    lane[0] = lambda: win.graph.stream.lane
    if win.playing:
        win.toggle_play()
    win.set_window(0, PERIOD, by=HAND)
    settled(win)
    win._toggle_clip()
    settled(win)
    edit(win.doc.node(edited).params)
    counts.clear()
    decodes = win.decoder.decodes
    win._params_changed(edited)
    settled(win)
    key = win._key(edited)
    rehelds = sum(run.cut is not None and edited in run.results and held.good(run.results[edited], key) for run in win.runs)
    return name, dict(counts), win.graph.memo.limit, win.decoder.cache_limit, win.decoder.decodes - decodes, rehelds


LANES = ("scrub", "window", "clip")
WHAT = ("gray", "read", "kept", "legs", "handed legs")
print(f"{CUTS} cuts of {KEPT} rows, every {PERIOD}; counts over the walk after the edit, by the lane the turn served")
print(f"{'cell':30} {'memo bytes':>11} {'cache bytes':>11} {'decodes':>8} {'held anew':>10}  " + "  ".join(f"{w} {'/'.join(LANES)}" for w in WHAT))
for edited in EDITS:
  for handed in (True, False):
    for tiny in ((), ("memo",), ("memo", "cache")):
        name, got, limit, cache, decodes, rehelds = cell(handed, tiny, edited)
        print(f"{name:30} {limit:>11} {cache:>11} {decodes:>8} {rehelds:>10}  " + "  ".join(
            f"{w} {'/'.join(str(got.get((w, ln), 0)) for ln in LANES)}" for w in WHAT))
sys.stdout.flush()
os._exit(0)
