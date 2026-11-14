"""What the catalogue says where no finished walk shows it, offscreen, on the simulations' graph. A
clip walked once over a memo it does not fit: the stores panel's line read before the walk's last
row, the log empty after it, and a second walk of the clip computing it again as the line said. The
window's range asked for again every few rows by no hand: what each begin in the stream says began
it, and the history, a long call in it too, saved and read back the same. A playhead running ahead
of a walk: no beginning but the one, and whatever else the log then holds printed. Prints each and
exits 1 where one is not so.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-14-the-catalogue-says-what-no-finished-walk-shows.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import theme  # noqa: E402
from sieve_player.catalogue import CLASSES, SPANS, Log  # noqa: E402
from sieve_player.dev.simulations import MS, ROW, ROWS, _again, _Run  # noqa: E402
from sieve_player.dev.timeview import StoresPanel, Window  # noqa: E402
from sieve_player.ledger import save, saved  # noqa: E402
from sieve_player.report import line  # noqa: E402
from sieve_player.stream import HAND  # noqa: E402

checks = {}
app = QApplication.instance() or QApplication([])
theme.install_font(app)


def walk_clip(r, during=None):
    """Walks the clip and waits for its last row, `during` called on the GUI thread at each row told."""
    told = []
    hook = r.worker.clipWalked.connect(lambda done, n, *was: (told.append((done, n)), during and during(done)))
    r.worker.walk_clip(HAND)
    if not r.worker.isRunning():
        r.worker.start()
    r.wait(lambda: told and told[-1] == (ROWS, ROWS), "the clip walk")
    r.worker.clipWalked.disconnect(hook)


with tempfile.TemporaryDirectory() as tmp, _Run(tmp, memo_bytes=ROWS * ROW * 2) as r:
    r.tools["work"].ms = 5 * MS         # rows long enough that the panel is read with the walk under way
    win = Window(r)
    win.resize(1280, 860)
    win.show()
    # The waits class is left out, as the one-off of 2026-11-12 leaves it: the monitor's own paint beside a walk this short is sighted in some runs.
    win.log = win._log = Log({k: v for k, v in CLASSES.items() if k != "waits"}, SPANS)
    stores = next(p for p in win.parts if isinstance(p, StoresPanel))
    read = []

    def midway(done):
        if not read and done >= ROWS // 4:
            win.refresh()
            read.append((win.view.walks[-1].done, {ln.name: ln for ln in stores.lines}["memo"]))
    walk_clip(r, midway)
    r.settle()
    win.refresh()
    done, memo = read[0]
    print(f"the stores panel at {done} of the clip's {ROWS} rows: memo · {memo.value} · {memo.note}")
    print("the log after the walk:", [line(e) for e in win.log.ordered()] or "empty")
    checks["the panel says before the clip's last row that the clip needs more of the memo than its limit and that its next walk computes it again"] = (
        done < ROWS and memo.over and memo.note.startswith("the clip needs ") and memo.note.endswith("past the limit: its next walk computes it again"))
    checks["and it is no problem: the log is empty after the walk"] = not win.log.entries
    walk_clip(r)
    r.settle()
    win.refresh()
    print("after a second walk of the clip:", [line(e) for e in win.log.ordered()])
    checks["the next walk of the clip did compute it again, which is then a problem"] = set(win.log.entries) == {("thrash", "store", "memo")}
    win.close()

with tempfile.TemporaryDirectory() as tmp, _Run(tmp) as r:
    events, emit = [], r.stream.on_event
    r.stream.on_event = lambda ev: (events.append(ev), emit(ev))
    _again(r, "asked", times=6)
    r.tools["work"].hold = 0.2
    r.walk(ask=r.change("gray", k=1))
    r.settle()
    by = [(ev.facts or {}).get("by") for ev in events if ev.kind == "begin"]
    print("what each begin said began it:", by)
    checks["a begin says what began it: a hand's, an ask's that named none, an edit's"] = by == ["hand", *["asked"] * 6, "edit"]
    path = os.path.join(tmp, "history.json")
    view = r.ledger.view()
    save(view, path)
    back = saved(path)[0].view()
    checks["a history with beginnings and a long call in it reads back as it was written"] = (
        any(b.begins for b in view.buckets) and any(b.longest for b in view.buckets) and back.buckets == view.buckets and back.walks == view.walks)

with tempfile.TemporaryDirectory() as tmp, _Run(tmp) as r:
    hook = r.worker.walked.connect(lambda done, n, *was: r.worker.request_row(min(done + 8, ROWS - 1)))
    r.walk()
    r.worker.walked.disconnect(hook)
    r.settle()
    seen = r.seen()
    print("a playhead eight rows ahead of the walk:", [line(e) for e in seen.log.ordered()] or "nothing found")
    began = sum(n for b in seen.view.buckets for by in b.begins.values() for n in by.values())
    checks["a playhead ahead of the walk begins nothing again and is no restart"] = began == 1 and not any(k[0] == "restarts" for k in seen.log.entries)

for what, ok in checks.items():
    print(f"{'ok ' if ok else 'NOT'}  {what}")
sys.exit(0 if all(checks.values()) else 1)
