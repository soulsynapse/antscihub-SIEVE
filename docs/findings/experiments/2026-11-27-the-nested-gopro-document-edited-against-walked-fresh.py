"""What a player holds of a real document of a period inside a period after a clip walk and two
edits, against what a player opened on the edited document holds after a clip walk alone. The
document is a copy of video-tests/GoPro clip single nested.json, never the file; the worker's turns
are taken on this thread and no window is shown.

Run: .venv/Scripts/python.exe -X utf8 <this file> [document]. Exit 1 where a result both hold
differs or the edited player lacks one; what it holds beside, of cuts an edit moved, is counted.
"""
import faulthandler
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

faulthandler.dump_traceback_later(2400, exit=True)
TREE = Path(__file__).resolve().parents[3]
SCRATCH = tempfile.mkdtemp(prefix="sieve-nested-gopro-")
os.environ.update(QT_QPA_PLATFORM="offscreen", SIEVE_STORE=os.path.join(SCRATCH, "store"))
sys.path.insert(0, str(TREE))
os.chdir(TREE)

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder, held, store, window  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

store.CHOICE = os.path.join(SCRATCH, "store.txt")
decoder.QUIET = True
held.File.write = lambda self, *a: []
window.TELL = 0.0
Worker.start = lambda self, *a: None
window.PlayerWindow.ask_unsaved = lambda self: "discard"
app = QApplication([])
TOOLS = [e for e in discover("tools") if e.ok]
SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else TREE / "video-tests" / "GoPro clip single nested.json")


def edits(doc):
    doc.node("smooth_below").params["reach"] = 4
    doc.node("smooth_in").band = (12.0, float("inf"))


def rested(win):
    """The worker's turns taken on this thread until two rounds take none; how many."""
    taken, quiet = 0, 0
    while quiet < 2:
        took = 0
        while True:
            with win.worker._cv:
                turn = win.worker._turn()
            if turn is None and win._whole_due.isActive():
                win._show_held_whole()
                continue
            if turn is None:
                break
            for job, act in turn[1]:
                win.graph.serving(turn[0], job.name)
                act()
            took += 1
        app.processEvents()
        taken, quiet = taken + took, 0 if took else quiet + 1
    return taken


def opened(name, edited):
    folder = Path(SCRATCH) / name
    folder.mkdir()
    shutil.copy(SOURCE, folder / "doc.json")
    if edited:
        said = json.loads((folder / "doc.json").read_text(encoding="utf-8"))
        for n in said["nodes"]:
            if n["id"] == "smooth_below":
                n["params"]["reach"] = 4
            if n["id"] == "smooth_in":
                n["band"] = [12.0, float("inf")]
        (folder / "doc.json").write_text(json.dumps(said), encoding="utf-8", newline="\n")
    win = window.PlayerWindow(str(folder / "doc.json"), "t", TOOLS)
    if win.playing:
        win.toggle_play()
    rested(win)
    return win


def holds(win):
    return {(nid, run.cut, run.start): r["signal"] for run in win.runs for nid, r in run.results.items() if held.good(r, win._key(nid))}


def cuts(win):
    p = win.graph.snapshot()
    return {n.id: len(p.entries[n.id].cuts) for n in win.doc.nodes if n.tool == "period"}


def timed(what, act, win):
    t = time.perf_counter()
    act()
    turns = rested(win)
    print(f"{what}: {time.perf_counter() - t:.1f} s, {turns} turns, cuts {cuts(win)}, {len(holds(win))} results held in {len(win.runs)} runs")
    sys.stdout.flush()


win = opened("edited", False)
print(f"{SOURCE.name}: {win.count} rows; standing of the cutting nodes before a clip walk: "
      f"{ {n.id: win.graph.standing(n.id) for n in win.doc.nodes if n.tool == 'period'} }")
timed("clip walk", win._toggle_clip, win)


def edit_below():
    win.doc.node("smooth_below").params["reach"] = 4
    win._params_changed("smooth_below")


def edit_band():
    win.doc.node("smooth_in").band = (12.0, float("inf"))
    win._params_changed("smooth_in")


timed("param edited below the inner cuts", edit_below, win)
timed("the inner gate's band edited", edit_band, win)
fresh = opened("fresh", True)
timed("the edited document opened and clip walked", fresh._toggle_clip, fresh)
got, want = holds(win), holds(fresh)
lacks, more = sorted(map(str, want.keys() - got.keys())), sorted(map(str, got.keys() - want.keys()))
differ = sorted(str(k) for k in got.keys() & want.keys() if not np.array_equal(got[k], want[k], equal_nan=True))
print(f"the edited player holds {len(got)} results and the fresh one {len(want)}: {len(differ)} differ, "
      f"{len(lacks)} the edited one lacks, {len(more)} it has beside")
for name, some in (("differs", differ), ("lacks", lacks), ("beside", more)):
    for k in some[:4]:
        print(f"  {name}: {k}")
sys.stdout.flush()
os._exit(1 if differ or lacks or not want else 0)
