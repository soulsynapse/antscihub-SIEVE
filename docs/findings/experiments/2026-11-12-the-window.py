"""The monitor's time view read off its painted image: a ledger fed by hand a walk of ten seconds whose
second half costs twice its first, the GUI thread's slots beside it, a memo that fills and computes one
row again, one late sample, and the monitor's own spans on both threads. Then the view pointed at,
marked, shortened, given a track of one colour, and over a longer history drawn out and scrolled back.
Prints what each shows and exits 1 where one is not as fed; with a path as the argument the first
view is saved there as a PNG.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-window.py [png]
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import theme  # noqa: E402
from sieve_player.dev.timeview import MINE, OTHER, SLOT, Late, RowCost, Stack, Stores, TimeView, Track, Turns  # noqa: E402
from sieve_player.graph import Event  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.theme import INK, INK_2, LEVEL, qgray  # noqa: E402
from sieve_player.trace import FIELDS  # noqa: E402

ROWS, EVERY, HUE = 200, 0.05, QColor(40, 200, 160)
EARLY, LATE, AGAIN, OWN = 8, 30, 36, 20     # a bucket of each half, the one the memo computes again in, and one of the monitor's own


def event(kind, t, ms=0.0, node=None, row=None, **more):
    return Event(**{f: None for f in FIELDS} | {"kind": kind, "t": t, "ms": ms, "cpu_ms": ms, "node": node, "row": row, "bytes": 0,
                                                "thread": "worker", "lane": "window"} | more)


app = QApplication.instance() or QApplication([])
theme.install_font(app)
led = Ledger(width=0.25)
led.event(event("begin", 0.0, row=0, length=ROWS))
led.event(event("evict", AGAIN * 0.25 - 1, key="k", row=AGAIN * 5))
for r in range(ROWS):
    t, ms = r * EVERY, 10.0 if r < ROWS // 2 else 20.0
    led.event(event("run", t, ms, "a", row=r, key="k"))
    led.event(event("slot", t + 0.03, 5.0, "walked", thread="MainThread", lane=None))
    led.event(event("progress", t + EVERY - 0.001, row=r + 1, length=ROWS,
                    facts={"memo": {"bytes": r + 1, "limit": ROWS}, "caches": {}}))
led.sample("late", 40.0, LATE * 0.25 + 0.1)
led.event(event("monitor", OWN * 0.25, 100.0, "ledger", lane=None))
led.event(event("slot", OWN * 0.25, 100.0, "monitor", thread="MainThread", lane=None))

view = TimeView([Stack(), Turns(), RowCost(), Stores(), Late()])
view.resize(600, 480)
view.set_view(led.view(), {"a": HUE}, ROWS * EVERY - 0.001)
img = view.grab().toImage()
if len(sys.argv) > 1:
    img.save(sys.argv[1])
axis, rects = view.axis(), {type(t).__name__: r for t, r in view.rects()}


def at(track, bucket, up):
    """The colour in `bucket`'s column of `track`, `up` of the track's height from its bottom."""
    r = rects[track]
    return img.pixelColor(int(axis.x(bucket)) + 1, int(r.bottom() - 1 - up * (r.height() - 2)))


def height(track, bucket, colour):
    """How far up `track` the topmost pixel of `colour` in `bucket`'s column is, of the track's height; None with none."""
    r = rects[track]
    ys = [y for y in range(int(r.top()), int(r.bottom())) if img.pixelColor(int(axis.x(bucket)) + 1, y) == colour]
    return (r.bottom() - min(ys)) / r.height() if ys else None


checks = {
    "the stack is the node's hue at 0.1 of its height in both halves": at("Stack", EARLY, 0.1) == HUE == at("Stack", LATE, 0.1),
    "at 0.3 the first half is unprobed and the second the node": (at("Stack", EARLY, 0.3), at("Stack", LATE, 0.3)) == (OTHER, HUE),
    "the GUI thread's stack holds its slot": at("Turns", EARLY, 0.02) == SLOT and height("Turns", EARLY, HUE) is None,
    "the row cost's mark is higher in the second half": height("RowCost", LATE, qgray(INK)) > 1.5 * height("RowCost", EARLY, qgray(INK)),
    "the memo's bytes rise toward its limit": height("Stores", LATE, qgray(INK_2)) > 2 * height("Stores", EARLY, qgray(INK_2)),
    "a recomputation is marked where it happened and nowhere else": (height("Stores", AGAIN, LEVEL) is not None
                                                                     and height("Stores", AGAIN - 1, LEVEL) is None),
    "the lateness is drawn in its bucket alone": height("Late", LATE, qgray(INK_2)) is not None and height("Late", EARLY, qgray(INK_2)) is None,
}
checks["the monitor's own is a band of its own gray on the worker's stack and the GUI thread's"] = (
    height("Stack", OWN, MINE) is not None and height("Turns", OWN, MINE) is not None and height("Stack", EARLY, MINE) is None)


def point(track, bucket, up):
    r = rects[track]
    return view.tip_at(int(axis.x(bucket)) + 1, int(r.bottom() - 1 - up * (r.height() - 2)))


print("pointed at the node's band, the unprobed above it, and the monitor's:\n ", "\n  ".join(
    repr(t) for t in (point("Stack", EARLY, 0.1), point("Stack", EARLY, 0.3), point("Stack", OWN, 0.7), point("Turns", OWN, 0.3))))
checks["pointing tells the node and its figure"] = point("Stack", EARLY, 0.1).splitlines()[1].startswith("a  50.0 ms, 20%")
checks["and what no node ran, and the monitor's own"] = ("unprobed" in point("Stack", EARLY, 0.3) and "monitor ledger" in point("Stack", OWN, 0.7)
                                                         and "slot monitor" in point("Turns", OWN, 0.3))
names = [(x, y) for x in range(int(axis.right) + 2, view.width()) for y in range(int(rects["Stack"].top()), int(rects["Stack"].bottom()))
         if img.pixelColor(x, y) == qgray(INK_2)]
checks["a band tall enough is named in the margin"] = bool(names)

view.set_view(led.view(), {"a": HUE}, ROWS * EVERY - 0.001, [(LATE * 0.25 + 0.1, "first seen: x")])
img = view.grab().toImage()
ruler = view.height() - view.RULER
checks["a mark is in the ruler at its moment's column, and in the tip there"] = (
    img.pixelColor(int(axis.x(LATE)) + 1, ruler + 1) == LEVEL and img.pixelColor(int(axis.x(LATE - 1)) + 1, ruler + 1) != LEVEL
    and "first seen: x" in view.tip_at(int(axis.x(LATE)) + 1, 5))


class Flat(Track):
    name, HUE = "flat", QColor(200, 60, 200)

    def paint(self, p, rect, axis, view, nodes):
        p.fillRect(rect, self.HUE)


view.tracks.append(Flat())
view.update()
flat = dict((type(t).__name__, r) for t, r in view.rects())["Flat"]
checks["a track added to the list is laid out and painted"] = view.grab().toImage().pixelColor(int(flat.center().x()), int(flat.center().y())) == Flat.HUE
view.tracks.pop()
left = []
for h in (480, 230, 200, 160, 130):
    view.resize(600, h)
    left.append([type(t).__name__ for t, _ in view.rects()])
    print(f"at {h} px high:", " ".join(left[-1]))
checks["as it shortens the tracks leave from the last, the stack never"] = (
    left[0] == ["Stack", "Turns", "RowCost", "Stores", "Late"] and left[-1] == ["Stack"]
    and all(a[:len(b)] == b for a, b in zip(left, left[1:])) and len({len(x) for x in left}) == 5)

long = Ledger(width=0.25)
long.event(event("run", 0.0, 200.0, "a", row=0, key="k"))
long.event(event("run", 100.0, 200.0, "a", row=1, key="k"))
view.resize(600, 480)
view.set_view(long.view(), {"a": HUE}, 100.2)


def first():
    """The colour low in the stack in the history's first bucket's column, or None while it is off the axis."""
    a, r = view.axis(), dict((type(t).__name__, r) for t, r in view.rects())["Stack"]
    at = int(0.0 // a.seconds)
    return view.grab().toImage().pixelColor(int(a.x(at)) + 1, int(r.bottom()) - 2) if at in a.visible() else None


was = first()
view.draw(view.whole())
out, k = first(), view.k
view.draw(1)
view.scroll(1e9)
back, held = first(), view.held
view.set_view(long.view(), {"a": HUE}, 130.0)       # the stream continues
print(f"{len(long.view().buckets)} buckets on {view._cols()} columns: drawn out at {k} a column; scrolled back the edge is held at {held:.2f} s")
checks["a history longer than the axis is off it, on it drawn out, and on it scrolled back"] = (was, out, back) == (None, HUE, HUE)
checks["scrolled back, the axis holds where it was put while the stream continues"] = first() == HUE and view.held == held
view.mouseDoubleClickEvent(None)
checks["and a double click returns it to now"] = view.held is None and first() is None

for what, ok in checks.items():
    print(f"{'ok ' if ok else 'NOT'}  {what}")
sys.exit(0 if all(checks.values()) else 1)
