"""The cold projection and the cold walk's control on the simulations' graph, offscreen, with the monitor
open on the run: a cold walk and a held one, a change at work, the control pressed once and twice, and
the bake served after the live walks. Prints what each shows and exits 1 where one is not as built.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-old-monitor-goes.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.catalogue import cold, reach  # noqa: E402
from sieve_player.dev.simulations import ROWS, _Run  # noqa: E402
from sieve_player.dev.timeview import Window  # noqa: E402

checks = {}
app = QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as tmp, _Run(tmp) as r:
    win = Window(r)
    win.show()
    r.walk()
    r.walk()
    view = r.ledger.view()
    first, again = view.walks[-2:]
    p = cold(view)
    print("after a cold walk and a held one:", {n: (round(c.ms_row, 3), c.walk and round(c.walk[1] - first.t0, 2), c.stale) for n, c in p.nodes.items()})
    checks["a held walk moves no frame node's figure, which is the cold walk's; the chain ran again and its figures are the held walk's"] = (
        set(p.nodes) == reach(again.plan) == {"video", "gray", "work", "bake", "edge", "mean", "pile"} and not p.missing
        and all(c.walk == ("window", (again if n in again.plan["chain"] else first).t0) and not c.stale for n, c in p.nodes.items()))

    r.walk(ask=r.change("work", k=1))
    view = r.ledger.view()
    changed = view.walks[-1]
    p = cold(view)
    print("after a change at work:", {n: (round(c.ms_row, 3), "the first" if c.walk[1] == first.t0 else "the last", c.stale) for n, c in p.nodes.items()})
    checks["after a change at work, it and what reads it are the last walk's and what it reads the first's, unmarked"] = (
        {n for n, c in p.nodes.items() if c.walk == ("window", changed.t0)} == {"work", "bake", "edge", "mean", "pile"}
        and {n for n, c in p.nodes.items() if c.walk == ("window", first.t0)} == {"video", "gray"}
        and not any(c.stale for c in p.nodes.values()))

    before = len(r.ledger.view().walks)
    walked = win.cold.click() or win.status.text()
    print("the control, pressed once:", walked)
    QApplication.processEvents()
    checks["a first press says what is held will be computed again, and walks nothing"] = (
        "computes again what is held" in walked and "press again" in walked and win.cold.text() == "Walk it"
        and len(r.ledger.view().walks) == before and r.graph.memo.bytes > 0)
    r.walk(ask=win.cold.click)
    view = r.ledger.view()
    w = view.walks[-1]
    r.log.read(view)
    print("pressed again:", {n: (x.ran, x.held, x.served) for n, x in w.nodes.items()}, "recomputed", w.recomputed,
          "| the log:", sorted(k for k, e in r.log.entries.items() if e.holds))
    checks["a second press walks the window with every row of every node run, and no store is said to have discarded"] = (
        len(view.walks) == before + 1 and all(not x.held and (x.ran == ROWS or not w.plan["nodes"][n]["steps"] and n in w.plan["chain"])
                                              for n, x in w.nodes.items())
        and not w.recomputed and not any(k[0] == "thrash" for k in r.log.entries))

    if shutil.which("ffmpeg") is None:
        print("no ffmpeg on PATH: the bake is not served")
    else:
        D.land(r.doc.node("bake"), r.bake())
        r.walk(ask=lambda: (r.graph.sync(), r.worker.set_window(0, ROWS)))      # the bake's own walk left the window at two rows
        view = r.ledger.view()
        w = view.walks[-1]
        p = cold(view)
        print("the bake served:", sorted(reach(w.plan)), {n: (round(c.ms_row, 3), c.stale) for n, c in p.nodes.items()},
              "against", round(p.ms_row(), 3), "ms a cold row")
        checks["the bake served after the live walks, the projection holds nothing behind it"] = (
            reach(w.plan) == set(p.nodes) == {"bake", "edge", "mean", "pile"} and not any(c.stale for c in p.nodes.values()))
    win.close()

for name, ok in checks.items():
    print(f"{'ok  ' if ok else 'NOT '} {name}")
sys.exit(0 if all(checks.values()) else 1)
