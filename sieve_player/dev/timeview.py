"""Dev > Monitor: what the catalogue found, leading, over the ledger drawn as its evidence. Problems
lists the log's entries that hold, the costliest first; picking one marks its nodes in Table and in the
stacks, outlines the Panel it is about and flags its first sighting on the axis. A Track paints one
reading of a view's buckets on the axis every track shares, TimeView lays out the tracks it is given
and is drawn out, scrolled back, held and pointed at, and Window polls the ledger of the video its
source holds, the player or a simulation's run, over the list of its parts. Every figure drawn is the
catalogue's value and none is made here. Colour is the product type's, the canvas's connector hue,
never a node's; what no node ran is a gray, LEVEL is a problem's, and OURS is SIEVE's share of the machine.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache, wraps
from typing import NamedTuple

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QImage, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from .. import stream, theme
from ..canvas import type_color
from ..catalogue import (Log, alike, bucket_row_ms, finished, gui, machine, needs, realtime_multiple, resource_shares, rows,
                         size, store_name, tight, unprobed_row_ms, walk_row_ms)
from ..document import produces
from ..ledger import coarsen, save
from ..pace import clock as as_clock
from ..pacecontrol import PaceControl
from ..report import report
from ..store import commit
from ..theme import GAP, GROUND, HEAD, INK, INK_2, LEVEL, LINE_LIFT, PAD, RADIUS, ROW_H, layer, qgray

THREAD = "worker"               # the name graph.Readers.reap asserts of the worker's thread
MONITOR = "monitor"             # the name its turns go under in the stream, which catalogue.gui tells the monitor's own by
OTHER = qgray(INK_2 - 30)       # unprobed, never a type's hue
SLOT, PAINT = qgray(INK), qgray(INK_2)      # the GUI thread's spans by kind, having no type
MINE = qgray(INK_2 - 60)        # a consumer's own work, the monitor's and the dump's, on whichever thread
SEAM = 3                        # px; a band at least this tall has its top edge cut, so two of one hue are told apart
STEPS = (1, 2, 5, 10, 30, 60, 120, 300, 600)    # seconds between the ruler's ticks, the first that leaves LABEL px
LABEL = 64
LATE = 50.0                     # ms; the least the lateness track's full height stands for, so a quiet thread draws low
MARK = 4                        # px; a recomputation's mark, and a first sighting's in the ruler
SIGHTED = 110                   # of 255; the alpha of a first sighting's line up the tracks, so it is no recomputation's mark
LEAST = 20                      # px a unit of a track's stretch, under which the track leaves
NARROW, SHORT = 720, 420        # px; a window narrower or shorter than these is compact
SMALLEST = (488, 260)           # the least the window is sized to: the figure and the copy across, the costliest problem and the stack down
SIDE = 300                      # px; the side panels' column
ARMED = 6.0                     # s; how long a first press of the cold walk's control waits for the second
SAID = 6.0                      # s; how long the status says what was just done before what stands returns
CLEARED = 3                     # the cleared entries the problems' foot names, the latest first, the rest counted
OURS = QColor(224, 192, 112)    # SIEVE's share of the machine: the mockup's amber
ELSE = qgray(INK_2 - 40)        # everything on the machine that is not SIEVE
PICKED, PICKED_EDGE = QColor(58, 42, 41), QColor(168, 72, 63)      # a picked problem's row, LEVEL toward the ground
TINT = QColor(245, 168, 161)    # a problem's target and a figure past its limit, LEVEL toward the ink
ABOUT = {"thrash": "stores", "waits": "gui", "signals": "gui"}        # a class -> the panel its problems are about; the rest are the table's


@lru_cache(maxsize=None)
def hatch(rgb):
    """The colour `rgb` cut by diagonal stripes of the ground: a picked problem's mark on a band or a bar."""
    img = QImage(6, 6, QImage.Format.Format_RGB32)
    for x in range(6):
        for y in range(6):
            img.setPixelColor(x, y, QColor(rgb) if (x + y) % 6 < 3 else qgray(GROUND))
    return QBrush(QPixmap.fromImage(img))


def turned(kind):
    """A decorator of a widget's method: each call is a turn of `kind` named MONITOR in the stream of
    the video its window's `source` holds; bare under a window with no source or no video."""
    def wrap(method):
        @wraps(method)
        def turn(self, *args, **kwargs):
            graph = getattr(getattr(self.window(), "source", None), "graph", None)
            if graph is None:
                return method(self, *args, **kwargs)
            with graph.stream.turn(kind, MONITOR):
                return method(self, *args, **kwargs)
        return turn
    return wrap


painted, slotted = turned(stream.PAINT), turned(stream.SLOT)


@dataclass(frozen=True)
class Axis:
    """Bucket `end` has its right edge at pixel `right` and each bucket is `px` wide, back to `left`;
    `whole` is the newest bucket on it that wall time has left."""
    seconds: float      # a bucket's width
    end: int
    px: float
    left: float
    right: float
    whole: int

    def x(self, i):
        return self.right - (self.end - i + 1) * self.px

    def at(self, x):
        """The bucket whose column pixel `x` is in."""
        return self.end - int((self.right - 1 - x) // self.px)

    def visible(self):
        return range(self.end - int((self.right - self.left) // self.px) + 1, self.end + 1)


def columns(view, axis):
    """(bucket index, Bucket) for each bucket of `view` on `axis`."""
    for i in axis.visible():
        if 0 <= i - view.first < len(view.buckets):
            yield i, view.buckets[i - view.first]


def stack(p, rect, x, px, parts, full):
    """One column of (value, colour, whether it is marked) from the bottom of `rect`, `full` being its whole height."""
    y, ground = rect.bottom(), qgray(layer(2))
    for v, c, marked in parts:
        h = rect.height() * v / full
        if h <= 0:
            continue
        p.fillRect(QRectF(x, y - h, px, h), hatch(c.rgb()) if marked else c)
        if h >= SEAM:
            p.fillRect(QRectF(x, y - h, px, 1), ground)
        y -= h


class Track:
    """One reading of the buckets. `paint` draws into `rect`, a column per bucket of `axis`, and
    may write in the gutter left of it and the margin right; `view` is a ledger's View at the axis's
    width and `nodes` is {node: colour} in walk order. `tip` is what the view's bucket `at` shows `up`
    of the track's height from its bottom, in words, or "". The view names the track at the gutter's top.
    `marked` is the names the picked problem is about, which a track that draws them marks."""
    name = ""
    stretch = 1         # its share of the height the tracks divide
    marked = frozenset()

    def paint(self, p, rect, axis, view, nodes):
        raise NotImplementedError

    def tip(self, at, up, axis, view, nodes):
        return ""

    def body(self, rect):
        """The part of `rect` its columns stand in, which `up` is a share of."""
        return rect

    def note(self, p, rect, text, y=None):
        """`text` in the gutter, on the line under the track's name or with its baseline at `y`."""
        fm = p.fontMetrics()
        p.setPen(qgray(INK_2))
        p.drawText(QPointF(0, rect.top() + fm.ascent() + fm.lineSpacing() if y is None else y), text)


class Bands(Track):
    """A stack of named bands, a column's full height the bucket's own wall time. `parts(b, nodes)`
    is [(name, ms, colour)] from the bottom. A band is told by pointing, and by its name in the
    margin beside the axis's newest whole column where it is tall enough there to take one; a
    marked band is hatched."""

    def parts(self, b, nodes):
        raise NotImplementedError

    def paint(self, p, rect, axis, view, nodes):
        full, fm = axis.seconds * 1000, p.fontMetrics()
        for i, b in columns(view, axis):
            stack(p, rect, axis.x(i), axis.px, [(v, c, name in self.marked) for name, v, c in self.parts(b, nodes)], full)
        at, y = axis.whole - view.first, rect.bottom()
        p.setPen(qgray(INK_2))
        for name, v, _ in self.parts(view.buckets[at], nodes) if 0 <= at < len(view.buckets) else ():
            h = rect.height() * v / full
            if h >= fm.height():
                p.drawText(QPointF(axis.right + 4, y - h / 2 + fm.ascent() / 2 - 1),
                           fm.elidedText(name, Qt.TextElideMode.ElideRight, TimeView.MARGIN - 4))
            y -= h

    def tip(self, at, up, axis, view, nodes):
        full, top = axis.seconds * 1000, 0.0
        for name, v, _ in self.parts(view.buckets[at], nodes):
            top += v / full
            if v > 0 and up < top:
                return f"{name}  {v:.1f} ms, {v / full:.0%} of the bucket"
        return ""


class Stack(Bands):
    """Where the worker's time went: each node's exclusive ms from the bottom in walk order, what
    `nodes` does not hold after them, the monitor's own among it, then unprobed; what is left empty
    the worker spent idle."""
    name = "worker"
    stretch = 4
    HEAD = 16           # px over the columns for the walks, each a segment from its beginning to its last row

    def body(self, rect):
        return rect.adjusted(0, self.HEAD, 0, 0)

    @staticmethod
    def label(w):
        """A walk as its segment says it."""
        over = "" if w.start is None else f" · rows {w.start}..{w.start + w.length - 1}"
        return f"{w.lane or 'walk'}{over} · {walk_row_ms(w):.2f} ms a row"

    def segments(self, axis, view):
        """[(x0, x1, walk)] for the walks of `view` with a row done that are on `axis`."""
        edge, out = (axis.end + 1) * axis.seconds, []
        for w in view.walks:
            x0, x1 = (axis.right - (edge - t) / axis.seconds * axis.px for t in (w.t0, w.t1))
            if w.done and x1 > axis.left and x0 < axis.right:
                x0 = min(max(x0, axis.left), axis.right - 2)
                x1 = min(max(x1, x0 + 2), axis.right)
                out.append((x0, x1, w))
        return out

    def paint(self, p, rect, axis, view, nodes):
        super().paint(p, self.body(rect), axis, view, nodes)
        fm = p.fontMetrics()
        for x0, x1, w in self.segments(axis, view):
            p.fillRect(QRectF(x0, rect.top(), max(x1 - x0 - 1, 1), self.HEAD - 2), qgray(layer(3)))
            if x1 - x0 > 24:
                p.setPen(qgray(INK))
                p.drawText(QPointF(x0 + 4, rect.top() + fm.ascent()), fm.elidedText(self.label(w), Qt.TextElideMode.ElideRight, int(x1 - x0 - 8)))

    def tip(self, at, up, axis, view, nodes):
        if up <= 1:
            return super().tip(at, up, axis, view, nodes)
        t = (view.first + at) * view.width
        return next((self.label(w) for w in reversed(view.walks) if w.done and w.t0 < t + view.width and w.t1 >= t), "")

    def parts(self, b, nodes):
        ms = b.ms.get(THREAD, {})
        return [*((n, ms[n], c) for n, c in nodes.items() if n in ms),
                *((n, v, MINE if n.split()[0] in stream.OWN else type_color(None)) for n, v in ms.items() if n not in nodes),
                ("unprobed", b.unprobed, OTHER)]


class Turns(Bands):
    """Every other thread's time on the worker's scale: what ran on a thread, a node in its type hue
    and a consumer's own work, named with the thread, then the GUI thread's paints and slots by
    name, each kind one gray and the monitor's a third."""
    name = "gui"
    stretch = 2

    def parts(self, b, nodes):
        parts = [(f"{n} on {t}", v, MINE if n.split()[0] in stream.OWN else nodes.get(n, type_color(None)))
                 for t, ms in b.ms.items() if t != THREAD for n, v in ms.items()]
        return parts + [(name, v, MINE if name.endswith(f" {MONITOR}") else SLOT if name.startswith(stream.SLOT) else PAINT)
                        for name, v in sorted(b.turns.items())]


class RowCost(Track):
    """What a row cost: the worker's ms in nodes over the rows the lanes finished, a bucket at a
    time, as the catalogue costs a walk; a bucket that finished none has no mark. The full height
    is the most on the axis, written in the gutter."""
    name = "row"

    def paint(self, p, rect, axis, view, nodes):
        cols = [(i, c[0]) for i, b in columns(view, axis) if (c := bucket_row_ms(b, THREAD))]
        top = max((v for _, v in cols), default=0.0)
        if not top:
            return
        self.note(p, rect, f"{top:.2f} ms")
        for i, v in cols:
            p.fillRect(QRectF(axis.x(i), rect.bottom() - 2 - (rect.height() - 2) * v / top, axis.px, 2), qgray(INK))

    def tip(self, at, up, axis, view, nodes):
        c = bucket_row_ms(view.buckets[at], THREAD)
        return f"{c[0]:.2f} ms a row over {c[1]} rows" if c else ""


class Stores(Track):
    """Each store a row of its own, named in the gutter, the memo first and a cache by its node:
    the bytes held against the limit, the row's top, at each bucket's last progress, and a mark at
    the top of each bucket in which the store computed again what it had discarded. A bucket with
    no progress has no bytes drawn."""
    name = ""
    stretch = 2

    def paint(self, p, rect, axis, view, nodes):
        cols = list(columns(view, axis))
        seen = {s for _, b in cols for s in (*b.stores, *b.recomputed)}
        if not seen:
            return self.note(p, rect, "stores", rect.top() + p.fontMetrics().ascent())
        h = rect.height() / len(seen)
        for at, store in enumerate(sorted(seen, key=lambda s: (s != "memo", store_name(s, view)))):
            top = rect.top() + at * h
            self.note(p, rect, store_name(store, view), top + p.fontMetrics().ascent())
            p.fillRect(QRectF(rect.left(), top, rect.width(), 1), qgray(layer(2) + LINE_LIFT))
            for i, b in cols:
                held, limit = b.stores.get(store, (0, 0))
                if limit:
                    full = (h - 2) * min(1.0, held / limit)
                    p.fillRect(QRectF(axis.x(i), top + h - 1 - full, axis.px, full), qgray(INK_2))
                if b.recomputed.get(store):
                    p.fillRect(QRectF(axis.x(i), top, axis.px, MARK), LEVEL)

    def tip(self, at, up, axis, view, nodes):
        b = view.buckets[at]
        return "; ".join([*(f"{store_name(s, view)} {size(held)} of {size(limit or 0)}" for s, (held, limit) in b.stores.items()),
                          *(f"{store_name(s, view)} computed again {n}" for s, n in b.recomputed.items())])


class Late(Track):
    """The worst lateness of the GUI thread's timer sampled in each bucket; the full height is the
    most on the axis and no less than LATE, written in the gutter."""
    name = "late"

    def paint(self, p, rect, axis, view, nodes):
        cols = [(i, b.late) for i, b in columns(view, axis) if b.late]
        top = max([LATE, *(v for _, v in cols)])
        self.note(p, rect, f"{top:.0f} ms")
        for i, v in cols:
            h = rect.height() * v / top
            p.fillRect(QRectF(axis.x(i), rect.bottom() - h, axis.px, h), qgray(INK_2))

    def tip(self, at, up, axis, view, nodes):
        late = view.buckets[at].late
        return f"the GUI thread's timer {late:.0f} ms late" if late else ""


class Load(Track):
    """The machine, a row a resource named in the gutter, memory, cores and disk as far as they
    are read: in each bucket the share of it in use, SIEVE's from the row's bottom and
    everything else's over it in ELSE, SIEVE's in OURS, by the last sample up to that bucket."""
    name = ""
    stretch = 2
    ROWS = ("memory", "cores", "disk")

    @staticmethod
    def shares(m, name):
        """`catalogue.resource_shares` of resource `name` in sample `m`, or None unread."""
        v = m.get(name)
        return resource_shares(name, v) if v else None

    @staticmethod
    def sample(view, at):
        """The last machine sample up to bucket `at` of `view`, {} with none."""
        for i in range(min(at, len(view.buckets) - 1), -1, -1):
            if view.buckets[i].machine:
                return view.buckets[i].machine
        return {}

    def paint(self, p, rect, axis, view, nodes):
        shown = axis.visible()
        cols, last = [], self.sample(view, shown[0] - view.first - 1) if len(shown) else {}
        for i in shown:
            at = i - view.first
            last = (view.buckets[at].machine if 0 <= at < len(view.buckets) else {}) or last
            cols.append((i, last))
        names = [n for n in self.ROWS if any(m.get(n) for _, m in cols)]
        if not names:
            return self.note(p, rect, "machine", rect.top() + p.fontMetrics().ascent())
        h = rect.height() / len(names)
        for at, name in enumerate(names):
            top = rect.top() + at * h
            self.note(p, rect, name, top + p.fontMetrics().ascent())
            p.fillRect(QRectF(rect.left(), top, rect.width(), 1), qgray(layer(2) + LINE_LIFT))
            for i, m in cols:
                s = self.shares(m, name)
                if s is not None:
                    ours, others = (h - 2) * min(1.0, s[0]), (h - 2) * min(1.0, s[1])
                    p.fillRect(QRectF(axis.x(i), top + h - 1 - ours, axis.px, ours), OURS)
                    p.fillRect(QRectF(axis.x(i), top + h - 1 - ours - others, axis.px, others), ELSE)

    def tip(self, at, up, axis, view, nodes):
        m = self.sample(view, at)
        said = [f"{n} {s[0] + s[1]:.0%} in use, SIEVE {s[0]:.0%}" for n in self.ROWS if (s := self.shares(m, n)) is not None]
        faults = m.get("faults")
        return "; ".join(said + ([] if faults is None else [f"{faults:.0f} hard faults a second"]))


class TimeView(QWidget):
    """`tracks`, top to bottom on one axis, each named in the gutter at its left, over a ruler of
    time before now. `set_view` hands over a ledger's View, the nodes as a Track takes them, now on
    the probe's clock, and `marks`, [(t, text)], each a flag at its moment. The axis ends at now and
    holds a bucket a column until it is drawn out, by the wheel or `draw`, to as many a column as
    put the view's whole history on it. `held` is the time at its right edge while that is not now:
    dragged or `scroll`ed back, or put by `hold`, it stays where it was put while the stream
    continues, until it is scrolled forward to now, double clicked or `release`d. `behind` is how
    long ago the view handed over was read, its holder's to set, which the ruler and a tooltip count
    in what they say is before now. What is under the pointer is its tooltip."""
    PX, GUTTER, MARGIN, RULER = 3, 96, 96, 18

    def __init__(self, tracks, parent=None):
        super().__init__(parent)
        self.tracks = tracks
        self.view = self.shown = None       # the View handed over, and it at the width drawn
        self.nodes, self.now, self.marks, self.behind = {}, 0.0, (), 0.0
        self.k, self.held = 1, None         # buckets a column
        self._drag, self.alone = None, False
        self.setMinimumSize(self.GUTTER + self.MARGIN + 120, self.RULER + LEAST * 4)
        self.setFont(theme.mono_font())
        self.setMouseTracking(True)

    def set_view(self, view, nodes, now, marks=()):
        self.view, self.nodes, self.now, self.marks = view, nodes, now, marks
        self.shown = None if view is None else coarsen(view, self.k)
        self.update()

    def _cols(self):
        return max(1, int((self.width() - self.GUTTER - self.MARGIN) // self.PX))

    def whole(self):
        """The buckets a column, a power of two, at which the view's whole history is on the axis."""
        k = 1
        while self.view is not None and k * self._cols() < len(self.view.buckets):
            k *= 2
        return k

    def draw(self, k):
        """The axis at `k` buckets a column, no more than `whole()` and no fewer than one."""
        self.k = max(1, min(k, self.whole()))
        self.set_view(self.view, self.nodes, self.now, self.marks)
        self.scroll(0)

    def scroll(self, seconds):
        """Moves the axis's right edge `seconds` back along the history, forward when negative, no
        further back than the history fills it; moved forward to now it follows the clock again."""
        if self.view is None or (self.held is None and seconds <= 0):
            return
        t = (self.now if self.held is None else self.held) - seconds
        t = max(t, (self.view.first // self.k + self._cols() - 1) * self.view.width * self.k)
        self.held = None if t >= self.now and (self.held is None or seconds < 0) else min(t, self.now)
        self.update()

    def hold(self):
        """Holds the axis where it is, at now when it was following the clock."""
        if self.held is None:
            self.held = self.now

    def release(self):
        self.held = None
        self.update()

    def axis(self):
        seconds = (self.view.width if self.view is not None else 1.0) * self.k
        end = int((self.now if self.held is None else self.held) // seconds)
        return Axis(seconds, end, self.PX, self.GUTTER, self.width() - self.MARGIN, min(end, int(self.now // seconds) - 1))

    def rects(self):
        """[(track, the QRectF it paints into)] for the tracks the height takes, the height above the
        ruler divided by stretch. A track needs LEAST px a unit of its stretch; while they do not
        all have it the last in the list leaves, and the first never does. While `alone` is set the
        first is the only one."""
        tracks = list(self.tracks)[:1 if self.alone else None]
        while len(tracks) > 1 and self.height() - self.RULER - GAP * (len(tracks) - 1) < LEAST * sum(t.stretch for t in tracks):
            tracks.pop()
        room = self.height() - self.RULER - GAP * (len(tracks) - 1)
        total, y, out = sum(t.stretch for t in tracks) or 1, 0.0, []
        for t in tracks:
            h = max(0.0, room * t.stretch / total)
            out.append((t, QRectF(self.GUTTER, y, self.width() - self.GUTTER - self.MARGIN, h)))
            y += h + GAP
        return out

    def tip_at(self, x, y):
        """What is at the pixel, as the tooltip says it: how long before now its bucket ended, the
        track's reading of the bucket there, and any mark in it; "" off the axis."""
        if self.shown is None or not self.GUTTER <= x < self.width() - self.MARGIN:
            return ""
        axis = self.axis()
        i = axis.at(x)
        at, lines = i - self.shown.first, [said for t, said in self.marks if int(t // axis.seconds) == i]
        for track, rect in self.rects():
            if rect.top() <= y < rect.bottom() and 0 <= at < len(self.shown.buckets):
                said = track.tip(at, (rect.bottom() - y) / track.body(rect).height(), axis, self.shown, self.nodes)
                if said:
                    lines.insert(0, said)
        return f"{as_clock(max(0.0, self.behind + self.now - (i + 1) * axis.seconds))} ago\n" + "\n".join(lines) if lines else ""

    @painted
    def paintEvent(self, _):
        p = QPainter(self)
        axis, fm = self.axis(), p.fontMetrics()
        for track, rect in self.rects():
            p.fillRect(rect, qgray(layer(2)))
            p.setPen(qgray(INK_2))
            p.drawText(QPointF(0, rect.top() + fm.ascent()), track.name)
            if self.shown is not None:
                p.save()
                p.setClipRect(QRectF(0, rect.top(), self.width(), rect.height()))
                track.paint(p, rect, axis, self.shown, self.nodes)
                p.restore()
        top, lag = self.height() - self.RULER, self.behind + self.now - (self.now if self.held is None else self.held)
        for t, said in self.marks:
            if (i := int(t // axis.seconds)) in axis.visible():
                x, w = axis.x(i), fm.horizontalAdvance(said) + 10
                p.fillRect(QRectF(x, 0, 1, top), QColor(LEVEL.red(), LEVEL.green(), LEVEL.blue(), SIGHTED))
                p.fillRect(QRectF(x, top, axis.px, MARK), LEVEL)
                flag = QRectF(x + 4 if x + 4 + w <= axis.right else x - 4 - w, 3, w, fm.height() + 2)
                p.fillRect(flag, LEVEL)
                p.setPen(qgray(GROUND))
                p.drawText(flag, Qt.AlignmentFlag.AlignCenter, said)
        step = next((s for s in STEPS if s / axis.seconds * axis.px >= LABEL), STEPS[-1])
        ago = step * math.ceil(lag / step) or step
        p.setPen(qgray(INK_2))
        while (x := axis.right - (ago - lag) / axis.seconds * axis.px) >= axis.left:
            p.drawLine(QPointF(x, top), QPointF(x, top + 4))
            p.drawText(QPointF(x + 4, top + 4 + fm.ascent()), "-" + as_clock(ago))
            ago += step

    def wheelEvent(self, e):
        self.draw(self.k * 2 if e.angleDelta().y() < 0 else self.k // 2)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.position().x()

    def mouseMoveEvent(self, e):
        x = e.position().x()
        if self._drag is not None:
            self.scroll((x - self._drag) / self.PX * self.axis().seconds)
            self._drag = x
        else:
            QToolTip.showText(e.globalPosition().toPoint(), self.tip_at(int(x), int(e.position().y())), self)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.held = None
        self.draw(1)


def _key(entry):
    return entry.problem.kind, entry.problem.subject


class _Lines(QWidget):
    """The problems' rows, painted: `entries` a row each, the one under `picked` lit, drawn as
    `written`, each entry's (share, `said`) when the rows were handed over, an entry being the log's
    to change under them. A press on a row's copy copies it and anywhere else on the row picks it,
    through the monitor's window it is in."""
    H, BAR, SHARE, MS, SEEN, COPY = ROW_H + 6, 60, 36, 104, 150, 52

    def __init__(self):
        super().__init__()
        self.entries, self.written, self.picked = [], [], None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def said(self, e):
        """An entry's row as it is written, cell by cell."""
        p = e.problem
        return ("-" if p.share is None else f"{p.share:.0%}", p.says, p.target, f"{p.ms_row:.2f} ms a row",
                f"{p.kind} · {e.count} walk{'s' * (e.count != 1)}")

    def copy_rect(self, i):
        return QRectF(self.width() - self.COPY, i * self.H + 2, self.COPY, self.H - 6)

    @painted
    def paintEvent(self, _):
        p = QPainter(self)
        ui, mono = theme.ui_font(), theme.mono_font()
        for i, (e, (part, (share, says, target, ms, seen))) in enumerate(zip(self.entries, self.written)):
            row = QRectF(0, i * self.H, self.width() - self.COPY - GAP, self.H - 2)
            lit = _key(e) == self.picked
            p.setPen(PICKED_EDGE if lit else qgray(layer(2) + LINE_LIFT))
            p.setBrush(PICKED if lit else qgray(layer(2)))
            p.drawRoundedRect(row.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
            x, mid = PAD, row.center().y()
            p.fillRect(QRectF(x, mid - 4, self.BAR, 8), qgray(GROUND))
            p.fillRect(QRectF(x, mid - 4, self.BAR * min(1.0, part or 0.0), 8), LEVEL)
            x += self.BAR + GAP
            p.setFont(mono)
            fm = p.fontMetrics()
            base = mid + fm.ascent() / 2 - 1
            p.setPen(qgray(HEAD - 15))
            p.drawText(QPointF(x, base), share)
            x += self.SHARE
            right = row.right() - PAD
            if row.width() >= 640:
                p.setPen(qgray(INK_2))
                p.drawText(QPointF(right - self.SEEN, base), fm.elidedText(seen, Qt.TextElideMode.ElideRight, self.SEEN))
                right -= self.SEEN + GAP
            p.setPen(qgray(INK))
            p.drawText(QPointF(right - self.MS, base), ms)
            right -= self.MS + GAP
            p.setFont(ui)
            says = p.fontMetrics().elidedText(says, Qt.TextElideMode.ElideRight, int(right - x))
            p.setPen(qgray(HEAD - 15))
            p.drawText(QPointF(x, base), says)
            x += p.fontMetrics().horizontalAdvance(says) + GAP
            p.setFont(mono)
            p.setPen(TINT)
            p.drawText(QPointF(x, base), fm.elidedText(target, Qt.TextElideMode.ElideRight, int(max(0.0, right - x))))
            button = self.copy_rect(i)
            p.setPen(qgray(layer(3) + LINE_LIFT))
            p.setBrush(qgray(layer(3)))
            p.drawRoundedRect(button.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
            p.setFont(ui)
            p.setPen(qgray(INK))
            p.drawText(button, Qt.AlignmentFlag.AlignCenter, "Copy")

    def mousePressEvent(self, e):
        i = int(e.position().y() // self.H)
        if e.button() != Qt.MouseButton.LeftButton or not 0 <= i < len(self.entries):
            return
        if self.copy_rect(i).contains(e.position()):
            self.window().copy([_key(self.entries[i])])
        else:
            self.window().pick(_key(self.entries[i]))


class Problems(QWidget):
    """What leads the monitor: the log's entries that hold, the costliest first, a row each, its
    share of a row, the class's sentence, its target, its ms a row, its class and the walks it was
    seen in, with its own copy; `all` copies them all. Under them one line, the entries cleared, the
    latest CLEARED named and the rest counted, and the classes that found nothing. A press on a row picks it. While `compact` it is the costliest's
    sentence and target and how many more there are, beside the copy of them all. A part of the
    monitor's: `refresh(window)` reads the window's `log`, `picked` and `now`."""
    place = "lead"

    def __init__(self):
        super().__init__()
        self.compact = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP // 2)
        head = QHBoxLayout()
        head.setSpacing(GAP)
        self.head = theme.readout(wrap=False)
        self.head.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        self.all = QPushButton("Copy all")
        self.all.setFixedSize(84, ROW_H)
        self.all.setToolTip("every problem that holds as one report, to the clipboard; the history is written beside it")
        self.lines, self.foot = _Lines(), theme.readout(mono=True, wrap=False)
        self.foot.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        head.addWidget(self.head, 1)
        head.addWidget(self.all)
        lay.addLayout(head)
        lay.addWidget(self.lines)
        lay.addWidget(self.foot)
        self.all.clicked.connect(lambda: self.window().copy())

    def refresh(self, window):
        entries = window.log.ordered()
        holds, cleared = [e for e in entries if e.holds], [e for e in entries if not e.holds]
        judged = window.view is not None and bool(finished(window.view))
        quiet = [k for k in window.log.classes if judged and not any(e.problem.kind == k for e in entries)]
        drawn = self.lines.written, self.lines.picked
        self.lines.entries, self.lines.picked = holds, window.picked
        self.lines.written = [(e.problem.share, self.lines.said(e)) for e in holds]
        self.lines.setFixedHeight(len(holds) * _Lines.H)
        self.lines.setVisible(bool(holds) and not self.compact)
        if drawn != (self.lines.written, window.picked):
            self.lines.update()
        self.all.setText(f"Copy all {len(holds)}" if holds else "Copy all")
        self.all.setEnabled(bool(holds))
        self.head.setWordWrap(self.compact)     # the sentence, the target and how many more are all read, on as many lines as they take
        if not holds:
            self.head.setText("no video" if window.view is None else "nothing found" if judged else "no walk finished yet")
        elif self.compact:
            p = holds[0].problem
            self.head.setText(f"{p.says} · {p.target}" + (f" · and {len(holds) - 1} more" if len(holds) > 1 else ""))
        else:
            self.head.setText(f"{len(holds)} problem{'s hold' if len(holds) != 1 else ' holds'} · costliest first · pick one to see it below")
        cleared.sort(key=lambda e: -e.problem.t)
        self.foot.setText(" · ".join(
            [*(["cleared: " + "; ".join(f"{e.problem.kind} {e.problem.subject}, {as_clock(window.now - e.problem.t)} ago" for e in cleared[:CLEARED])
                + (f"; and {len(cleared) - CLEARED} earlier" if len(cleared) > CLEARED else "")]
               if cleared else []), *(["checked and quiet: " + ", ".join(quiet)] if quiet else [])]))
        self.foot.setVisible(bool(self.foot.text()) and not self.compact)


class Table(QWidget):
    """The pipeline as one table in walk order, a row a node of the walk the window shows: its ms a
    row with a bar on one scale, the median and the 99th percentile of its ms a run, its ms per
    megapixel of what it read, what asked for most of it, and the rate the walk would reach were
    the node free; what no node ran is the last row. A node the picked problem names has its bar
    hatched and what asked for it in the problem's ink. `lines` is the rows as written."""
    place = "left"
    LINE, NAME, MS, SPREAD, MP, ASKED, FREE = 20, 136, 44, 104, 48, 170, 52

    def __init__(self):
        super().__init__()
        self.lines, self.marked, self._colours, self._ms = [], frozenset(), {}, {}
        self.setFont(theme.mono_font())

    def refresh(self, window):
        drawn = self.lines, self.marked, self._colours
        w, self.marked, self._colours = window.walk, window.marked, window.nodes
        self.lines, self._ms = [], {}
        if w is not None:
            by = rows(w, window.view)
            for nid in [*(n for n in window.nodes if n in by), *(n for n in by if n not in window.nodes)]:
                r = by[nid]
                self.lines.append((nid, f"{r.ms_row:.2f}", "-" if r.median is None else f"{r.median:.2f} – {r.p99:.2f}",
                                   "-" if r.per_mp is None else f"{r.per_mp:.2f}", r.asked_by(),
                                   "-" if (free := r.rate_if_free(window.rate)) is None else f"{free:.1f}×"))
                self._ms[nid] = r.ms_row
            if w.done:
                self._ms["unprobed"] = unprobed_row_ms(w)
                self.lines.append(("unprobed", f"{self._ms['unprobed']:.2f}", "", "", "", ""))
        self.setFixedHeight((len(self.lines) + 1) * self.LINE + 2 * PAD)
        if drawn != (self.lines, self.marked, self._colours):
            self.update()

    @painted
    def paintEvent(self, _):
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qgray(layer(2)))
        p.drawRoundedRect(QRectF(self.rect()), RADIUS, RADIUS)
        fm, top = p.fontMetrics(), max(self._ms.values(), default=0.0)
        asked = self.ASKED if self.width() >= 700 else 0
        spread, mp = (self.SPREAD + GAP, self.MP + GAP) if self.width() >= 480 else (0, 0)
        bar = self.width() - 2 * PAD - self.NAME - self.MS - spread - mp - asked - self.FREE - 3 * GAP
        after = PAD + self.NAME + self.MS + GAP + bar + GAP
        cols = (PAD, PAD + self.NAME, after, after + spread, after + spread + mp, self.width() - PAD - self.FREE)
        p.setPen(qgray(INK_2))
        for x, said in zip(cols, ("node", "ms a row", "median – p99" if spread else "", "ms/MP" if mp else "", "asked by" if asked else "", "if free")):
            p.drawText(QPointF(x, PAD + fm.ascent()), said)
        for i, (nid, ms, run, per, by, free) in enumerate(self.lines, 1):
            y = PAD + i * self.LINE
            base, hit = y + (self.LINE + fm.ascent()) / 2 - 2, nid in self.marked
            colour = self._colours.get(nid, OTHER)
            p.fillRect(QRectF(cols[0], y + self.LINE / 2 - 4, 8, 8), colour)
            p.setPen(qgray(INK))
            p.drawText(QPointF(cols[0] + 14, base), fm.elidedText(nid, Qt.TextElideMode.ElideRight, self.NAME - 18))
            p.drawText(QPointF(cols[1], base), ms)
            at = QRectF(cols[1] + self.MS + GAP, y + self.LINE / 2 - 5, max(bar, 0), 10)
            p.fillRect(at, qgray(GROUND))
            if top:
                p.fillRect(QRectF(at.left(), at.top(), at.width() * self._ms[nid] / top, at.height()), hatch(colour.rgb()) if hit else colour)
            p.setPen(qgray(INK_2))
            if spread:
                p.drawText(QPointF(cols[2], base), run)
                p.drawText(QPointF(cols[3], base), per)
            if asked:
                p.setPen(TINT if hit else qgray(INK_2))
                p.drawText(QPointF(cols[4], base), fm.elidedText(by, Qt.TextElideMode.ElideRight, asked - GAP))
            p.setPen(qgray(INK))
            p.drawText(QPointF(cols[5], base), free)


class Line(NamedTuple):
    """One line of a Panel: a bar is its pieces, each (where it begins and where it ends as shares
    of the bar, and how it is filled, a key of Panel.FILLS, or "dot", a mark where it begins)."""
    name: str
    value: str
    bar: list | None = None
    note: str = ""          # written under it
    over: bool = False      # whether it is past its limit


class Panel(QWidget):
    """A side panel: `title` over `says`, one sentence or "", over `lines`, each a Line; outlined
    while the picked problem is of a class in `about`. A subclass's `read(window)` gives the lines
    and may set `says`."""
    FILLS = {"ink": lambda: qgray(INK_2), "ours": lambda: OURS, "else": lambda: ELSE, "hatch": lambda: hatch(LEVEL.rgb()), "dot": lambda: qgray(INK)}
    place, title, about = "side", "", ""

    def __init__(self):
        super().__init__()
        self.lines, self.outlined, self.says = [], False, ""
        self.setFont(theme.mono_font())

    def read(self, window):
        raise NotImplementedError

    def refresh(self, window):
        drawn = self.lines, self.outlined, self.says
        self.says = ""
        self.lines = [] if window.view is None else self.read(window)
        entry = window.log.entries.get(window.picked)
        self.outlined = entry is not None and ABOUT.get(entry.problem.kind) == self.about
        if drawn != (self.lines, self.outlined, self.says):
            self._fit()
            self.update()

    def _fit(self):
        said = self._wrapped(self.says, QFontMetrics(theme.ui_font())) if self.says else []
        self.setFixedHeight(2 * PAD + ROW_H + ROW_H * len(said) + sum(self._height(ln) for ln in self.lines))

    def resizeEvent(self, e):
        self._fit()     # the lines wrap by the width
        super().resizeEvent(e)

    def _wrapped(self, text, fm=None):
        """`text` as the lines the panel's width takes in the font of `fm`, the panel's own when not given, broken at its spaces."""
        fm, w, out = fm or self.fontMetrics(), self.width() - 2 * PAD, []
        for word in text.split(" "):
            if out and fm.horizontalAdvance(f"{out[-1]} {word}") <= w:
                out[-1] += " " + word
            else:
                out.append(word)
        return out

    def _height(self, ln):
        return self.fontMetrics().lineSpacing() * (1 + (len(self._wrapped(ln.note)) if ln.note else 0)) + (12 if ln.bar else 0) + 4

    @painted
    def paintEvent(self, _):
        p = QPainter(self)
        p.setPen(PICKED_EDGE if self.outlined else Qt.PenStyle.NoPen)
        p.setBrush(qgray(layer(2)))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
        fm, w = p.fontMetrics(), self.width() - 2 * PAD
        p.setFont(theme.ui_font())
        p.setPen(qgray(HEAD - 15))
        p.drawText(QPointF(PAD, PAD + p.fontMetrics().ascent()), self.title)
        y = PAD + ROW_H
        p.setPen(TINT if any(ln.over for ln in self.lines) else qgray(INK))
        for said in self._wrapped(self.says, p.fontMetrics()) if self.says else ():
            p.drawText(QPointF(PAD, y + p.fontMetrics().ascent()), said)
            y += ROW_H
        p.setFont(self.font())
        for name, value, bar, note, over in self.lines:
            p.setPen(qgray(INK))
            p.drawText(QPointF(PAD, y + fm.ascent()), name)
            p.setPen(TINT if over else qgray(INK_2))
            p.drawText(QPointF(PAD + w - fm.horizontalAdvance(value), y + fm.ascent()), value)
            y += fm.lineSpacing()
            if bar:
                p.fillRect(QRectF(PAD, y + 2, w, 8), qgray(GROUND))
                for a, b, how in bar:
                    a, b = min(1.0, max(0.0, a)), min(1.0, max(0.0, b))
                    p.fillRect(QRectF(PAD + (w - 3) * a, y + 2, 3, 8) if how == "dot" else QRectF(PAD + w * a, y + 2, w * (b - a), 8), self.FILLS[how]())
                y += 12
            p.setPen(TINT if over else qgray(INK_2))
            for said in self._wrapped(note) if note else ():
                p.drawText(QPointF(PAD, y + fm.ascent()), said)
                y += fm.lineSpacing()
            y += 4


class StoresPanel(Panel):
    """Each store as the window lane's last walk found it: what it holds of its limit and what it
    ran again, over what the window needs of it by `catalogue.needs`, which stands before the
    store discards anything; a store the window does not fit has its bar drawn to the need, hatched
    past the limit."""
    title, about = "Stores", "stores"

    def read(self, window):
        view = window.view
        w = next((w for w in reversed(view.walks) if w.lane == "window"), window.walk)
        stores = next((b.stores for b in reversed(view.buckets) if b.stores), {})
        need = {} if w is None else needs(view, w)
        out = []
        for s, (held, limit) in sorted(stores.items(), key=lambda x: (x[0] != "memo", store_name(x[0], view))):
            again, n = 0 if w is None else w.recomputed.get(s, 0), need.get(s)
            over = bool(limit and n and n > limit)
            full = max(n or 0, limit or 0) or 1
            out.append(Line(store_name(s, view), f"{size(held)} of {size(limit or 0)} · {again or 'none'} again",
                            [(0, held / full, "ink"), *([(limit / full, 1, "hatch")] if over else [])], f"this window needs {size(n)}" if n else "", over))
        return out


class GuiPanel(Panel):
    """The GUI thread over the walk the window shows, by `catalogue.gui`: its worst lateness, and
    its slots, its paints and the monitor's own as shares of the wall, the longest of each named."""
    title, about = "The interface thread", "gui"

    def read(self, window):
        if window.walk is None:
            return []
        late, turns = gui(window.view, window.walk)
        return [Line("worst", f"{late:.0f} ms late"),
                *(Line("this monitor" if what == "monitor" else f"{what}s" + (f", {top} the longest" if top else ""), f"{share:.1%}")
                  for what, share, top in turns)]


class MachinePanel(Panel):
    """The machine over the walk the window shows, by `catalogue.machine`: in one sentence which
    resource is tight or that none is, each resource as SIEVE's and everything else's against the
    whole, and by `catalogue.alike` the walks under the plan now walked and as cold, a mark each
    from the least ms a row to the most."""
    title, about = "The machine", "machine"

    def read(self, window):
        if window.walk is None:
            return []
        res, like = machine(window.view, window.walk), alike(window.view, window.walk)
        self.says = tight(res)
        out = [Line(r.name, r.value, None if r.ours is None else [(0, r.ours, "ours"), (r.ours, r.ours + r.others, "else")],
                    r.note, r.tight) for r in res]
        if len(like) > 1:
            lo, hi = min(like), max(like)
            out.append(Line(f"{len(like)} walks alike", f"{lo:.2f} – {hi:.2f} ms a row", [((x - lo) / ((hi - lo) or 1), 0, "dot") for x in like],
                            "under this plan and as cold"))
        return out


def colours(graph):
    """{node: its product type's colour}: the frame nodes by depth from the video, document order
    within a depth, and the chain after them in run order."""
    doc, depth = graph.doc, {}

    def of(nid, above=()):
        if nid not in depth:
            w = doc.source(nid)
            depth[nid] = 0 if w is None or w.src in above else of(w.src, (*above, nid)) + 1
        return depth[nid]
    chain = list(graph.chain)
    ids = [n.id for n in doc.nodes if n.id not in chain]
    return {n: type_color(produces(doc, graph.tools, n)) for n in [*sorted(ids, key=lambda n: (of(n), ids.index(n))), *chain]}


def context(graph, dump=None):
    """What an entry's text and a saved history take beside the view, read off `graph`; `dump` is
    the path of the dump being written, when one is."""
    d = graph.decoder
    return {"document": graph.doc.to_dict(), "video": d.path, "memo_limit": graph.memo.limit, "commit": commit(),
            "dump": None if dump is None else str(dump),
            "decoder": {k: getattr(d, k, None) for k in ("width", "height", "fps", "count", "output", "cache_limit")}}


class Window(QWidget):
    """`source` holds `graph`, `ledger` and `pace`, each None while no video is open, and may hold
    `dump`: the player's window or a simulation's run. `parts` is what the window shows, each a
    Track on the time view's axis or a panel, a widget with `refresh(window)` and a `place`, "lead"
    over everything, "left" over the time view or "side" beside it; `add` takes another. It is
    polled every `period_ms` while shown, `clock` being the probe's.

    What a part reads is the last poll's: `view`, `now`, `log`, the catalogue's over the open
    video, `walk`, the walk that progressed last, `rate`, its multiple of realtime, `nodes`,
    {node: colour} in walk order, `picked`, the (class, subject) of the entry the window is about,
    the one `pick` named while it holds and else the costliest that does, and `marked`, the names
    that entry's problem is about. A first sighting is a line on stderr.

    Paused, by `toggle_pause` or the axis scrolled back, which is one holding, it draws what it
    drew, `log` being the entries as they stood, and says how far behind now that is in the status,
    the ruler and a tooltip, the ledger taking the stream and the log reading it for stderr, a copy
    and a history.

    What was just done is said in the status for SAID seconds. `source` may hold `worker`, which
    `walk_cold` has walk the window again over emptied stores. Narrower than NARROW or shorter than
    SHORT it is compact: the figure, the costliest problem's sentence and target, how many more
    there are, the copy of them all and the time view. Its poll, what a press in it does and its
    paints are in the stream, each a "slot" or a "paint" named "monitor"."""

    def __init__(self, source, period_ms=250, clock=time.perf_counter, parts=None):
        super().__init__(source if isinstance(source, QWidget) else None, Qt.WindowType.Window)
        self.setWindowTitle("Monitor")
        self.setObjectName("monitor")       # the sheet grounds a main window's children only, and a simulation's window has no parent
        self.setStyleSheet(theme.sheet() + f"#monitor {{ background: {theme.gray(theme.GROUND)}; }}")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.source, self.clock = source, clock
        self.view, self.now, self._ledger = None, clock(), None
        self.log = self._log = Log()        # what the parts read, and the one that reads the ledger: one Log but while paused
        self.walk, self.rate, self.nodes, self.picked, self.marked, self._pick = None, None, {}, None, frozenset(), None
        self.parts, self.compact, self._armed = [], False, None
        self._judged, self._said, self._until = None, "", -math.inf     # (the view the log read last, its now); the status's word and when it lapses
        self.setMinimumSize(*SMALLEST)
        self.resize(1200, 780)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(PAD, PAD, PAD, PAD)
        lay.setSpacing(GAP)
        head = QHBoxLayout()
        head.setSpacing(GAP)
        self.figure = PaceControl()
        self.status = theme.readout("no video", wrap=False)
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)     # it takes what the controls leave and asks for none
        self.pause, self.history, self.full = QPushButton("Pause"), QPushButton("History"), QPushButton("Full screen")
        self.cold = QPushButton("Cold walk")
        self.cold.setToolTip("empty the memo and the caches and walk the window again, every row run; a first press says what is held")
        self.pause.setToolTip("hold what is drawn while the ledger goes on taking the stream")
        self.history.setToolTip("write the recent history to a file, for a slowdown no problem names; its path to the clipboard")
        self.full.setToolTip("F11")
        head.addWidget(self.figure)
        head.addWidget(self.status, 1)
        for b, slot in ((self.cold, self.walk_cold), (self.pause, self.toggle_pause), (self.history, self.save_history),
                        (self.full, self.toggle_full)):
            b.setFixedSize(76, ROW_H)
            b.clicked.connect(lambda _=False, slot=slot: slot())
            head.addWidget(b)
        lay.addLayout(head)
        self.lead = QVBoxLayout()
        self.lead.setSpacing(GAP)
        lay.addLayout(self.lead)
        body = QHBoxLayout()
        body.setSpacing(GAP)
        self.left = QVBoxLayout()
        self.left.setSpacing(GAP)
        self.time = TimeView([])
        self.left.addWidget(self.time, 1)
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(SIDE)
        self.side = QVBoxLayout(self.sidebar)
        self.side.setContentsMargins(0, 0, 0, 0)
        self.side.setSpacing(GAP)
        self.side.addStretch(1)
        body.addLayout(self.left, 1)
        body.addWidget(self.sidebar)
        lay.addLayout(body, 1)
        for part in [Problems(), Table(), Stack(), Load(), Late(), MachinePanel(), StoresPanel(), GuiPanel()] if parts is None else parts:
            self.add(part)
        QShortcut(QKeySequence(Qt.Key.Key_F11), self, self.toggle_full)
        self._timer = QTimer(self, interval=period_ms)
        self._timer.timeout.connect(self.refresh)

    def add(self, part):
        self.parts.append(part)
        if isinstance(part, Track):
            self.time.tracks.append(part)
            self.time.update()
            return
        place = getattr(part, "place", "side")
        if place == "lead":
            self.lead.addWidget(part)
        elif place == "left":
            self.left.insertWidget(self.left.count() - 1, part)
        else:
            self.side.insertWidget(self.side.count() - 1, part)
        self._fit()

    def refresh(self):
        graph, ledger = self.source.graph, self.source.ledger
        if ledger is not self._ledger:
            self._ledger, self.view, self._judged, self._pick, self._armed = ledger, None, None, None, None
            self.log = self._log = Log()
            self.time.release()
        if graph is None or ledger is None:
            self.figure.set_figure(None)
            self.walk = self.rate = None
            self.time.set_view(None, {}, self.clock())
            self._show()
        else:
            with graph.stream.turn(stream.SLOT, MONITOR):
                if self.time.held is None:
                    self.log = self._log
                elif self.log is self._log:
                    self.log = self._log.copy()
                self._judge(ledger)
                if self.time.held is None:
                    self._read(graph)
        behind = 0.0 if self.time.held is None else self.clock() - self.now
        if behind != self.time.behind:
            self.time.behind = behind
            self.time.update()
        if self._armed is not None and self.clock() - self._armed > ARMED:
            self._armed = None
        self.pause.setText("Resume" if self.time.held is not None else "Pause")
        self.cold.setText("Cold walk" if self._armed is None else "Walk it")
        self.status.setText(self._status())

    def _status(self):
        """The status line: no video, else what was said inside its time, else that the window is paused."""
        if self.source.graph is None or self.source.ledger is None:
            return "no video"
        if self.clock() < self._until:
            return self._said
        if self.time.held is not None:
            return f"paused · showing {as_clock(self.clock() - self.time.held)} ago · still recording"
        return ""

    def _say(self, text, seconds=SAID):
        self._said, self._until = text, self.clock() + seconds
        self.status.setText(self._status())

    def _judge(self, ledger):
        """Takes the ledger's view now into the log, paused or not, a first sighting a line on stderr."""
        self._judged = ledger.view(), self.clock()
        for e in self._log.read(self._judged[0]):
            print(f"SIEVE {time.strftime('%H:%M:%S')}: monitor: {e.problem.kind} {e.problem.subject}: {e.problem.line}", file=sys.stderr)

    def _read(self, graph):
        (self.view, self.now), self.nodes = self._judged, colours(graph)
        pace = self.source.pace
        figure = None if pace is None else pace.figure(graph.fps, graph.count)
        self.figure.set_figure(figure)
        self.walk = w = max((w for w in self.view.walks if w.done), key=lambda w: w.t1, default=None)
        self.rate = (None if w is None else figure.multiple if figure is not None and figure.lane == w.lane and figure.multiple
                     else realtime_multiple(w, graph.fps))
        self._show()

    def _show(self):
        """Hands the parts what the last poll read, about the entry now picked."""
        entries = {} if self.view is None else self.log.entries
        holds = [_key(e) for e in self.log.ordered() if e.holds] if entries else []
        self.picked = self._pick if self._pick in holds else holds[0] if holds else None
        e = entries.get(self.picked)
        self.marked = frozenset(e.problem.nodes) if e else frozenset()
        for part in self.parts:
            if isinstance(part, Track):
                part.marked = self.marked
            else:
                part.refresh(self)
        if self.view is not None:
            self.time.set_view(self.view, self.nodes, self.now,
                               [(e.first, f"first seen: {e.problem.kind} {e.problem.subject}")] if e else [])

    @slotted
    def pick(self, key):
        """Makes the log's entry under `key`, its (class, subject), the one the window is about."""
        self._pick = key
        self._show()

    @slotted
    def toggle_pause(self):
        if self.time.held is None:
            self.time.hold()
        else:
            self.time.release()
        self.refresh()

    def context(self):
        return context(self.source.graph, getattr(getattr(self.source, "dump", None), "path", None))

    def _write(self, context, folder=None):
        """The path the history was written to with `context` beside it, or None where it could not be, the status saying why."""
        path = os.path.join(folder or tempfile.gettempdir(), f"sieve-history-{time.strftime('%Y%m%d-%H%M%S')}.json")
        try:
            save(self._judged[0], path, **context)
        except OSError as exc:
            self._say(f"the history was not written: {exc}")
            return None
        return path

    @slotted
    def copy(self, keys=None):
        """Puts on the clipboard one report of the entries under `keys`, each a (class, subject), or
        of every entry that holds, as the log read them last, and returns it; None with none. The
        history is written as `save_history` writes it and the report names the file, which holds
        the document; where the file cannot be written nothing is copied and None returned."""
        entries = [e for e in self._log.ordered() if (e.holds if keys is None else _key(e) in keys)]
        if not entries or self._judged is None or self.source.graph is None:
            return None
        view, now = self._judged
        context = self.context()
        path = self._write(context)
        if path is None:
            return None
        said = report(entries, view, context | {"history": path, "now": now, "when": time.strftime("%Y-%m-%d %H:%M:%S")})
        QApplication.clipboard().setText(said)
        self._say(f"{len(entries)} problem{'s' * (len(entries) != 1)} copied, the history written to {path}")
        return said

    @slotted
    def save_history(self, folder=None):
        """Writes the view the log read last, which while paused is later than the one drawn, with
        the document and the rest of `context` to a file under `folder`, the system's temporary one
        when not given, puts its path on the clipboard and returns it; None with no video or where
        the file cannot be written."""
        if self._judged is None or self.source.graph is None:
            return None
        path = self._write(self.context(), folder)
        if path is None:
            return None
        QApplication.clipboard().setText(path)
        self._say(f"history written to {path}, and the path to the clipboard")
        return path

    @slotted
    def walk_cold(self):
        """A first call says what the stores hold and that it will be computed again; a second
        inside ARMED seconds empties them and has the worker walk the window again, every row run.
        Returns whether it walked."""
        graph, worker = self.source.graph, getattr(self.source, "worker", None)
        if graph is None or worker is None:
            return False
        if self._armed is None or self.clock() - self._armed > ARMED:
            held = graph.decoder.cache_bytes + sum(d.cache_bytes for d in graph.readers.decoders())
            self._armed = self.clock()
            self._say(f"a cold walk computes again what is held, {size(graph.memo.bytes)} in the memo and "
                      f"{size(held)} in the caches · press again to walk", ARMED)
            self.cold.setText("Walk it")
            return False
        self._armed = None
        graph.empty()
        worker.invalidate()
        self._say("walking the window cold")
        self.cold.setText("Cold walk")
        return True

    def toggle_full(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _fit(self):
        self.compact = self.width() < NARROW or self.height() < SHORT
        for part in self.parts:
            if hasattr(part, "compact"):
                part.compact = self.compact
            elif not isinstance(part, Track):
                part.setVisible(not self.compact)
        self.sidebar.setVisible(not self.compact)
        self.time.alone = self.compact
        for b in (self.cold, self.pause, self.history, self.full):
            b.setVisible(not self.compact)

    def resizeEvent(self, e):
        was = self.compact
        self._fit()
        if was != self.compact:
            self._show()
        super().resizeEvent(e)

    def showEvent(self, e):
        self.refresh()
        self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)
