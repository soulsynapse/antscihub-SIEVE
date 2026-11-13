"""The monitor opened from the player, offscreen: its header's figure beside the player's, the plan on
the first walk's record, its own spans in the ledger, the selection on a walk's record, the history
written and read back, the window at its sizes, a part added, the video closed and another opened.
Then a simulation shown three times over: its class in the window's log, a line on stderr a first
sighting, the entry's report off its copy, its flag on the axis once picked; and a served walk again with gray
selected. Prints each and exits 1 where one is not so; with a folder as the argument the monitor is
grabbed there at its sizes.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-monitor-on-the-player.py [folder]
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import theme  # noqa: E402
from sieve_player.catalogue import Log  # noqa: E402
from sieve_player.dev.simulations import _Run, show  # noqa: E402
from sieve_player.dev.timeview import SMALLEST, Problems, Track  # noqa: E402
from sieve_player.ledger import saved  # noqa: E402
from sieve_player.theme import LEVEL  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tests.test_plot import series  # noqa: E402
from tools import gray  # noqa: E402

ROWS = 3000
out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
checks = {}


def walked(win, total, timeout=30.0):
    """Returns once the window lane has finished a walk of `total` rows begun after this call."""
    win.pace._walks.pop("window", None)
    t = time.perf_counter()
    while True:
        QApplication.processEvents()
        f = win.pace.figure(win.fps, win.count)
        if f is not None and f.lane == "window" and f.over and f.total == total:
            return
        assert time.perf_counter() - t < timeout, f
        time.sleep(0.002)


def turn(seconds):
    t = time.perf_counter()
    while time.perf_counter() - t < seconds:
        QApplication.processEvents()
        time.sleep(0.002)


def sized(mon, w, h, name):
    mon.resize(w, h)
    turn(0.1)
    if out is not None:
        mon.grab().save(str(out / f"{name}.png"))
    said = ([type(t).__name__ for t, _ in mon.time.rects()], mon.compact,
            [type(p).__name__ for p in mon.parts if not isinstance(p, Track) and p.isVisible()])
    print(f"at {mon.width()}x{mon.height()}: tracks {' '.join(said[0])}; {'compact' if said[1] else 'whole'}, showing {' '.join(said[2])}")
    return said


class Flat(Track):
    name, HUE = "flat", QColor(200, 60, 200)

    def paint(self, p, rect, axis, view, nodes):
        p.fillRect(rect, self.HUE)


app = QApplication.instance() or QApplication([])
theme.install_font(app)
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    head = series("head", lambda v: np.arange(len(v), dtype=np.float64))
    D.save(D.from_tools([gray, head], clip(tmp / "v.avi", n=ROWS)), tmp / "doc.json")
    clip(tmp / "w.avi", n=120)
    win = PlayerWindow(str(tmp / "doc.json"), "t", [gray, head])
    win.resize(1280, 720)
    win.show()
    if win.playing:
        win.toggle_play()
    walked(win, 300)
    win.header.figure.click()
    mon = win.__dict__["_dev_windows"]["monitor"]
    turn(1.0)
    mon.refresh()

    print("the monitor's figure:", mon.figure.figure.words().splitlines()[0])
    checks["the monitor's header leads with the player's figure"] = mon.figure.figure is not None and mon.figure.figure == win.header.figure.figure
    first = mon.view.walks[0]
    print("the first walk's plan walks", first.plan and first.plan["walk"], "over", first.length, "rows")
    checks["the first walk's record holds its plan"] = first.plan is not None and first.done == first.length == 300

    turns = {}
    for b in mon.view.buckets:
        for name, ms in b.turns.items():
            turns[name] = turns.get(name, 0.0) + ms
    print("the GUI thread's spans, ms:", {k: round(v, 1) for k, v in turns.items() if "monitor" in k})
    checks["the monitor's poll and paint are spans of the GUI thread's"] = turns.get("slot monitor", 0) > 0 and turns.get("paint monitor", 0) > 0
    mon.hide()                              # nobody takes a view: the worker folds its own backlog
    win.set_window(300, ROWS - 300)
    walked(win, ROWS - 300)
    mon.show()
    mon.refresh()
    own = {t: sum(ms for b in mon.view.buckets for n, ms in b.ms.get(t, {}).items() if n == "monitor ledger")
           for t in {t for b in mon.view.buckets for t in b.ms}}     # whichever thread's emit passed the backlog folded, the GUI thread's slots being events too
    print(f"the ledger's bookkeeping over a walk of {ROWS - 300} rows nobody read, ms by the thread that folded:", {t: round(ms, 1) for t, ms in own.items() if ms})
    own = sum(own.values())
    checks["the ledger's bookkeeping on the emitting thread is a span of its own, in no walk"] = (
        own > 0 and not any("monitor ledger" in w.nodes for w in mon.view.walks))
    if out is not None:
        mon.grab().save(str(out / "default.png"))

    win.canvas.select(["gray"])
    win.set_window(0, 50)
    walked(win, 50)
    mon.refresh()
    print("selected on the last walk's record:", mon.view.walks[-1].selected, "and on the first's:", first.selected)
    checks["the selection is on the record of a walk begun under it"] = mon.view.walks[-1].selected == ["gray"] and first.selected == []

    path = mon.save_history(str(tmp))
    back, more = saved(path)
    checks["the history is written, reads back as the view, and its path is on the clipboard"] = (
        back.view() == mon.view and QApplication.clipboard().text() == path
        and D.Document.from_dict(more["document"]).node("gray") is not None and more["video"] == win.decoder.path)

    all_tracks = ["Stack", "Load", "Late"]
    checks["at a full screen's size every track is there under the problems, the table and the panels beside"] = (
        sized(mon, 1920, 1080, "full") == (all_tracks, False, ["Problems", "Table", "MachinePanel", "StoresPanel", "GuiPanel"]))
    checks["at the smallest the stack alone is left under the figure and the problems' one line"] = (
        sized(mon, *SMALLEST, "smallest") == (["Stack"], True, ["Problems"]) and mon.figure.isVisible())
    mon.resize(1100, 600)
    QTest.keyClick(mon, Qt.Key.Key_F11)
    turn(0.1)
    by_key = mon.isFullScreen()
    mon.full.click()
    turn(0.1)
    checks["F11 takes it full screen and the control back"] = by_key and not mon.isFullScreen()

    mon.add(Flat())
    mon.resize(1100, 600)
    turn(0.1)
    flat = dict((type(t).__name__, r) for t, r in mon.time.rects()).get("Flat")
    checks["a part added to the window is laid out and painted"] = flat is not None and (
        mon.time.grab().toImage().pixelColor(int(flat.center().x()), int(flat.center().y())) == Flat.HUE)

    win._unload()
    mon.refresh()
    none = (mon.status.text(), mon.view, mon.figure.figure)
    win.load(str(tmp / "w.avi"))
    if win.playing:
        win.toggle_play()
    walked(win, 120)
    mon.refresh()
    print("with the video closed:", none, "; and another opened:", [(w.lane, w.done, w.length) for w in mon.view.walks])
    checks["with no video it says so, and it reads the next one's walk"] = none == ("no video", None, None) and (
        [(w.done, w.length) for w in mon.view.walks if w.lane == "window"] == [(120, 120)])
    win.close()

err = io.StringIO()
with contextlib.redirect_stderr(err):
    shown = show("unread", rounds=3)
lines = [x for x in err.getvalue().splitlines() if "monitor:" in x]
print("\n".join(lines))
entries = shown.log.entries
print("beside its class the log holds:", sorted(k for k in entries if k[0] != "unread") or "nothing")
checks["a simulation shown has its class in the window's log, counted a round"] = (
    {e.count for k, e in entries.items() if k[0] == "unread"} == {3})
checks["a first sighting is one line on stderr, and a later one none"] = len(lines) == len(entries)
panel = next(p for p in shown.parts if isinstance(p, Problems)).lines
key = next(iter(entries))
at = [(e.problem.kind, e.problem.subject) for e in panel.entries].index(key)
QTest.mouseClick(panel, Qt.MouseButton.LeftButton, pos=panel.copy_rect(at).center().toPoint())
said = QApplication.clipboard().text()
print(" | ".join(panel.said(panel.entries[at])))
history = said.rsplit("HISTORY  ", 1)[1].strip()
checks["an entry's copy puts its report on the clipboard, the document in the history it names"] = (
    said.startswith("SIEVE monitor report") and f"\n1  unread · {key[1]} · " in said and saved(history)[1]["document"]["nodes"])
os.remove(history)
shown.pick(key)
axis, img = shown.time.axis(), shown.time.grab().toImage()
at = int(entries[key].first // axis.seconds)
checks["its first sighting is marked on the axis"] = at in axis.visible() and (
    img.pixelColor(int(axis.x(at)) + 1, shown.time.height() - shown.time.RULER + 1) == LEVEL)

with tempfile.TemporaryDirectory() as tmp, _Run(tmp, served=True) as r:
    log = Log()
    r.walk()
    log.read(r.ledger.view())
    before = {k: e.holds for k, e in log.entries.items()}
    r.fresh()
    r.stream.watch("gray")
    r.walk()
    log.read(r.ledger.view())
    print("unread before gray is selected:", before, "and after a cold walk with it selected:", {k: (e.holds, e.count) for k, e in log.entries.items()})
    checks["a selected node's fold is no longer surfaced, and an unselected one's still is"] = (
        ("unread", "gray") in before and all(before.values())
        and all((e.holds, e.count) == ((False, 1) if k[1] == "gray" else (True, 2)) for k, e in log.entries.items()))

for what, ok in checks.items():
    print(f"{'ok ' if ok else 'NOT'}  {what}")
sys.exit(0 if all(checks.values()) else 1)
