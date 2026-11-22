"""Where the GUI thread's time goes while the clip lane walks a document's cuts in time, in a
player offscreen: the clip walk is asked, the event loop is turned under cProfile for SECONDS, and
the periods held in that time and the player's own functions by cumulative time are printed. The
runs of cuts the held file has are let go first, in this process alone, so every period walks. The
held file's write is put out and the process leaves without closing, so nothing is written beside
the document. The document needs a run of its gate held over the clip whole, or it has no period.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-21-the-gui-thread-while-the-clip-lane-walks-periods.py <document> [seconds]"""
import cProfile
import os
import pstats
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import held  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402

SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
held.File.write = lambda self, *a: []
app = QApplication([])
win = PlayerWindow(os.path.abspath(sys.argv[1]), "t", discover("tools"))
if win.playing:
    win.toggle_play()


def turn(seconds):
    t0, longest = time.perf_counter(), 0.0
    while time.perf_counter() - t0 < seconds:
        t = time.perf_counter()
        app.processEvents()
        longest = max(longest, time.perf_counter() - t)
        time.sleep(0.002)
    return longest


turn(3)
cuts = sum(len(w.cuts) for w in win.graph.snapshot().timed)
of_cut = lambda: sum(run.cut is not None for run in win.runs)
win._take_runs([run for run in win.runs if run.cut is None])     # every period is to walk: the runs of cuts go, in this process alone
win._show_held()
had = of_cut()
win._toggle_clip()
prof = cProfile.Profile()
prof.enable()
longest = turn(SECONDS)
prof.disable()
print(f"{cuts} cuts in time, {had} held at first, {of_cut() - had} more in {SECONDS:.0f} s; the longest turn of the event loop {1000 * longest:.0f} ms", flush=True)
stats = pstats.Stats(prof)
rows = sorted(((ct, tt, nc, f"{os.path.basename(fn)}:{line} {name}") for (fn, line, name), (cc, nc, tt, ct, _) in stats.stats.items()
               if "sieve_player" in fn or os.sep + "tools" + os.sep in fn), reverse=True)
for ct, tt, nc, where in rows[:28]:
    print(f"{ct:7.2f} s cumulative {tt:6.2f} own {nc:>8} calls  {where}", flush=True)
os._exit(0)
