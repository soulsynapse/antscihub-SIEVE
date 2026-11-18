"""Experiment behind docs/findings/2026-11-17-a-clip-walk-under-a-playing-window.md: a document's
clip walk in a PlayerWindow on the screen, ms a row by node in buckets of the walk's rows, what the
GUI thread's turns took beside them, the events counted a bucket, and who asked the worker for a
display row.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-17-a-clip-walk-under-a-playing-window.py <document.json> <seconds> <rows a bucket> [paused] [hidden]

The document, the files beside it that begin with its name and its held file are copied to a
temporary folder and opened there. QT_QPA_PLATFORM=offscreen runs it with no window shown."""
import collections
import glob
import os
import shutil
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC, SECONDS, BUCKET = os.path.splitext(sys.argv[1])[0], float(sys.argv[2]), int(sys.argv[3])
sys.path.insert(0, ROOT)
HERE = tempfile.mkdtemp()
for path in glob.glob(glob.escape(SRC) + "*.json*"):
    shutil.copy(path, HERE)
DOC = os.path.join(HERE, os.path.basename(SRC) + ".json")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sieve_player.registry import discover
from sieve_player.window import PlayerWindow

app = QApplication([])
win = PlayerWindow(DOC, "t", discover(os.path.join(ROOT, "tools")))
events, inner = [], win.stream.on_event
gui = threading.get_ident()


def on_event(ev):
    events.append((ev.node, ev.row, ev.kind, ev.ms, ev.t, threading.get_ident() == gui))
    inner(ev)


win.stream.on_event = on_event
if "hidden" not in sys.argv:
    win.show()
seen = []
win.worker.clipWalked.connect(lambda done, total, *_: seen.append((time.perf_counter(), done)))
from sieve_player import catalogue as C


def table():
    view = win.ledger.view()
    ws = [x for x in view.walks if x.lane == "clip"]
    if ws and ws[-1].done:
        w = ws[-1]
        print(f"monitor at done {w.done:5}: " + ", ".join(f"{n} {r.ms_row:.2f} ({r.spans})" for n, r in C.rows(w, view).items()), flush=True)


import traceback
stacks = collections.Counter()
ask = win.worker.request_row


def asked(row):
    stacks[" < ".join(f"{f.name}:{f.lineno}" for f in reversed(traceback.extract_stack()[-7:-1]))] += 1
    ask(row)


win.worker.request_row = asked
import atexit
atexit.register(lambda: [print(n, s) for s, n in stacks.most_common(6)])
print("playing at open:", win.playing)
if "paused" in sys.argv and win.playing:
    win.toggle_play()
tick = QTimer()
tick.timeout.connect(table)
tick.start(6000)
QTimer.singleShot(2500, win._toggle_clip)
QTimer.singleShot(int(2500 + SECONDS * 1000), app.quit)
app.exec()
t0 = seen[0][0]
done = seen[-1][1]
print(f"clip rows {done} in {seen[-1][0] - t0:.1f} s")
# rows by time, to bucket the GUI's turns by where the walk was
import bisect
ts = [t for t, _ in seen]
by, guis, kinds = collections.defaultdict(lambda: collections.defaultdict(float)), collections.defaultdict(lambda: collections.defaultdict(float)), collections.Counter()
for node, row, kind, ms, t, on_gui in events:
    if t is None or t < t0:
        continue
    i = bisect.bisect_right(ts, t) - 1
    b = seen[max(i, 0)][1] // BUCKET
    kinds[(b, f"{kind}:{node}" if on_gui or node == "video" or kind in ("evict", "uncache") else kind)] += 1
    if on_gui:
        guis[b][f"{kind}:{node}"] += ms
    else:
        by[b][node] += ms
names = sorted({n for b in by.values() for n in b}, key=str)
print(f"{'rows from':>9} " + " ".join(f"{str(n)[:9]:>9}" for n in names) + "   gui ms/row")
for b in sorted(by):
    if (b + 1) * BUCKET > done:
        break
    print(f"{b * BUCKET:>9} " + " ".join(f"{by[b][n] / BUCKET:9.3f}" for n in names) + f"   {sum(guis[b].values()) / BUCKET:.3f}")
bs = sorted(b for b in guis if (b + 1) * BUCKET <= done)
for b in (bs[0], bs[len(bs) // 2], bs[-1]):
    top = sorted(guis[b].items(), key=lambda kv: -kv[1])[:6]
    print(f"gui from row {b * BUCKET}: " + ", ".join(f"{k} {v / BUCKET:.2f}" for k, v in top))
for b in bs:
    print(f"counts from row {b * BUCKET}: " + ", ".join(f"{k} {n}" for (bb, k), n in sorted(kinds.items(), key=str) if bb == b and (":" in k)))
win.close()
