"""Views of the monitor's snapshot, one widget per style, picked by the window's drop-down.

Colour follows the product type (the canvas's connector hue), never the node; unprobed is the
neutral gray. Each view reports its height for a snapshot and the window scrolls.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QToolTip, QVBoxLayout, QWidget

from .. import theme
from ..canvas import type_color
from ..theme import ACCENT, GAP, GATE, HEAD, INK, INK_2, LEVEL, LINE_LIFT, PAD, layer, qgray
from .monitor import summary, table

OTHER = qgray(INK_2 - 30)       # the unprobed remainder, never a type's hue
GOOD, SHORT = GATE, LEVEL       # a store that holds the window, and one that does not
BAR = 12                        # a bar's height, px
ROW = BAR + GAP                 # one bar row
HERO = 28                       # the one big number's size, px
TILE = 60                       # a stat tile's height, px
SECTION = 5 + GAP + 12          # from a section's baseline to the first row below it
RIGHT = 236                     # the mono column right of a bar, px: "256 of 256 MB · 0.7 windows"


def _time(s):
    if s is None:
        return "-"
    if s < 60:
        return f"{s:.1f}s"
    m, s = divmod(int(round(s)), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def frame_nodes(s):
    return [n for n in s["nodes"] if not n["series"]]


def series_nodes(s):
    return [n for n in s["nodes"] if n["series"]]


def cold_parts(s):
    """[(name, ms per cold row, colour)] for the frame nodes in walk order, then the unprobed rest, then
    the series chain's share of a row, in its type's hue."""
    parts = [(n["node"], n["row_ms"], type_color(n["type"])) for n in frame_nodes(s)]
    if s["other_row_ms"] is not None:
        parts.append(("unprobed", s["other_row_ms"], OTHER))
    if s["series_row_ms"]:
        parts.append(("series", s["series_row_ms"], series_color(s)))
    return parts


def series_color(s):
    chain = series_nodes(s)
    return type_color(chain[0]["type"]) if chain else OTHER


def walk_parts(s):
    """The same, as shares of this walk's wall time; a node that did not run this walk has none."""
    wall = s["wall_s"] * 1000
    if not wall:
        return []
    parts = [(n["node"], n["ms"] / wall, type_color(n["type"])) for n in frame_nodes(s) if n["ms"]]
    parts.append(("unprobed", max(0.0, s["other_ms"] / wall), OTHER))
    return parts


def types(s):
    """[(type, colour)] in first-seen order: the legend for every view that colours by type."""
    seen = {}
    for n in s["nodes"]:
        seen.setdefault(n["type"] or "untyped", type_color(n["type"]))
    return list(seen.items())


class View(QWidget):
    """A painted view. `set_snapshot` hands it the dict and sizes it; `_hits` is what hovers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.s = None
        self._hits = []
        self.setMouseTracking(True)
        self.ui, self.mono = theme.ui_font(), theme.mono_font()
        self.big = theme.ui_font()
        self.big.setPixelSize(HERO)
        self.big.setWeight(QFont.Weight.DemiBold)

    def set_snapshot(self, s):
        self.s = s
        self.setMinimumHeight(self.height_for(s))
        self.update()

    def height_for(self, s):
        return 400

    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            for rect, text in self._hits:
                if rect.contains(e.pos()):
                    QToolTip.showText(e.globalPos(), text, self)
                    return True
            QToolTip.hideText()
        return super().event(e)

    # -- painting helpers -------------------------------------------------
    def text(self, p, x, y, s, ink=INK, font=None, right=False):
        """Draws `s` with its baseline at `y`; right-aligned to `x` when `right`. Returns its width."""
        font = font or self.ui
        p.setFont(font)
        p.setPen(qgray(ink) if isinstance(ink, int) else ink)
        adv = QFontMetrics(font).horizontalAdvance(s)
        p.drawText(QPointF(x - adv if right else x, y), s)
        return adv

    def section(self, p, y, name, key, w):
        """The section's name left, its key figure right, a hairline under both. Returns the y below."""
        self.text(p, PAD, y, name, HEAD)
        self.text(p, w - PAD, y, key, INK_2, self.mono, right=True)
        p.setPen(QPen(qgray(layer(1) + LINE_LIFT), 1))
        p.drawLine(PAD, y + 5, w - PAD, y + 5)
        return y + SECTION

    def bar(self, p, x, y, w, h, c):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(x, y, max(w, 0.0), h), 2, 2)

    def trough(self, p, x, y, w, h):
        self.bar(p, x, y, w, h, qgray(layer(1) + 6))

    def vline(self, p, x, y, h, ink):
        p.setPen(QPen(qgray(ink) if isinstance(ink, int) else ink, 1))
        p.drawLine(QRectF(x, y, 0, h).topLeft(), QRectF(x, y, 0, h).bottomLeft())

    def store_bar(self, p, x, y, w, name, st):
        """A store in windows held, tick at one: green past it, red short of it."""
        win = st["windows"]
        axis = max(2.0, float(int(win) + 1)) if win else 2.0
        self.text(p, x, y + BAR, name, INK)
        bx, bw = x + 48, w - 48 - RIGHT
        self.trough(p, bx, y, bw, BAR)
        if win:
            self.bar(p, bx, y, bw * min(win, axis) / axis, BAR, GOOD if win >= 1 else SHORT)
        self.vline(p, bx + bw / axis, y - 3, BAR + 6, HEAD)
        held = f"{st['bytes'] / 2**20:.0f}" + (f" of {st['limit'] / 2**20:.0f} MB" if st["limit"] else " MB")
        self.text(p, bx + bw + GAP, y + BAR, f"{held} · {win:.1f} windows" if win else held, INK_2, self.mono)
        self._hits.append((QRectF(bx, y, bw, BAR), f"{name}: {st['row_bytes'] / 2**20:.2f} MB per row; the tick is one window"))

    def stacked(self, p, x, y, w, parts, total, label_fn):
        """One stacked bar with a 2px surface gap between segments; hover names a segment."""
        if not total:
            return
        gap, cx = 2.0, x
        for name, v, c in parts:
            sw = w * v / total - gap
            if sw > 0:
                self.bar(p, cx, y, sw, BAR, c)
                self._hits.append((QRectF(cx, y, sw, BAR), label_fn(name, v)))
            cx += w * v / total

    def legend(self, p, x, y, w, items):
        """Chips flowing left to right, wrapping; `items` is [(text, colour)]. Returns the y below."""
        cx, cy, fm = x, y, QFontMetrics(self.ui)
        for s, c in items:
            adv = fm.horizontalAdvance(s) + 14 + GAP * 2
            if cx + adv > x + w and cx > x:
                cx, cy = x, cy + 18
            self.bar(p, cx, cy - 10, 10, 10, c)
            self.text(p, cx + 14, cy, s, INK)
            cx += adv
        return cy + 18

    def tiles(self, p, y, w, items, h=TILE):
        """A row of stat tiles: [(caption, value, windows or None)]; windows colours the left edge. Returns the y below."""
        tw = (w - PAD * 2 - GAP * (len(items) - 1)) / len(items)
        for i, (cap, val, win) in enumerate(items):
            tx = PAD + i * (tw + GAP)
            self.bar(p, tx, y, tw, h, qgray(layer(2)))
            if win is not None:
                self.bar(p, tx, y, 3, h, GOOD if win >= 1 else SHORT)
            self.text(p, tx + PAD, y + 15, cap, INK_2)
            self.text(p, tx + PAD, y + h - 10, val, HEAD, self.big if len(val) < 9 else self.mono)
        return y + h + GAP

    def hero(self, p, y, w, s):
        """The realtime multiple and whole-clip tiles every view opens with. Returns the y below."""
        return self.tiles(p, y, w, [("realtime", f"{s['multiple']:.1f}×" if s["multiple"] else "-", None),
                                    (f"whole clip, {_time(s['footage_s'])} of footage, cold", f"~{_time(s['clip_s'])}" if s["clip_s"] else "-", None)])

    def series_lines(self, p, y, s):
        for n in series_nodes(s):
            self.text(p, PAD, y + 10, f"{n['node']}  {n['run_ms']:.1f} ms per emit, {n['runs']} emits this walk", INK_2)
            y += 18
        return y


# -- the views -----------------------------------------------------------------------------

class Text(QWidget):
    """The mono readouts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP)
        self.clip, self.nodes = theme.readout("", mono=True, wrap=False), theme.readout("", mono=True, wrap=False)
        for w in (self.clip, self.nodes):
            box = theme.Layer(1)
            box.add(w)
            lay.addWidget(box)
        lay.addStretch(1)

    def set_snapshot(self, s):
        self.clip.setText(summary(s))
        self.nodes.setText(table(s))


class Bars(View):
    """A hero multiple, the walk and the stores as bars; one bar per node against the cold row."""

    def height_for(self, s):
        return PAD + 12 + SECTION + TILE + GAP + ROW * 3 + 20 + GAP + 8 + SECTION + ROW * (len(frame_nodes(s)) + 1) \
            + 18 * len(series_nodes(s)) + 24 + PAD

    def paintEvent(self, _):
        s, w = self.s, self.width()
        if s is None:
            return
        self._hits = []
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        y = self.section(p, PAD + 12, "clip", f"{s['count']} rows · {s['fps']:.2f} fps" + (f" · {s['cold_row_ms']:.2f} ms per cold row" if s["cold_row_ms"] else ""), w)
        y = self.hero(p, y - 12, w, s)
        self.text(p, PAD, y + BAR, "walk", INK)
        bx, bw = PAD + 48, w - PAD * 2 - 48 - RIGHT
        self.trough(p, bx, y, bw, BAR)
        if s["length"]:
            self.bar(p, bx, y, bw * s["done"] / s["length"], BAR, ACCENT)
        self.text(p, bx + bw + GAP, y + BAR, f"{s['done']} / {s['length']} rows" + (f" · {_time(s['wall_s'])}" if s["wall_s"] else ""), INK_2, self.mono)
        y += ROW
        for name in ("memo", "cache"):
            self.store_bar(p, PAD, y, w - PAD * 2, name, s[name])
            y += ROW
        if s["wall_s"]:
            wall = s["wall_s"] * 1000
            self.text(p, PAD, y + 10, f"this walk: {s['probed_ms'] / wall:.0%} in frame nodes, {s['series_ms'] / wall:.0%} series, "
                      f"{s['other_ms'] / wall:.0%} unprobed"
                      + (f" · {s['scrub']['runs']} scrub runs" if s["scrub"]["runs"] else "")
                      + (f" · {s['syncs']} changes, last {', '.join(s['changed']) or 'nothing'}" if s["syncs"] else ""), INK_2)
        y += 20
        y = self.section(p, y + GAP + 8, "nodes", f"one cold row · {s['cold_row_ms']:.2f} ms" if s["cold_row_ms"] else "", w)
        total = s["cold_row_ms"] or 1.0
        label_w = max([QFontMetrics(self.ui).horizontalAdvance(n["node"]) for n in s["nodes"]] + [60]) + GAP
        bx, bw = PAD + label_w, w - PAD * 2 - label_w - RIGHT
        by_name = {n["node"]: n for n in s["nodes"]}
        for name, ms, c in cold_parts(s):
            self.text(p, PAD, y + BAR, name, INK)
            self.trough(p, bx, y, bw, BAR)
            self.bar(p, bx, y, bw * ms / total, BAR, c)
            n = by_name.get(name)
            if n and n["fold_ms"]:                   # the fold, same hue thinned
                fx = bx + bw * n["run_ms"] / total
                self.bar(p, fx, y, bw * n["fold_ms"] / total, BAR, QColor(c.red(), c.green(), c.blue(), 110))
            tail = f"{ms:5.2f} ms {ms / total:4.0%}" + (f" {n['run_bytes'] / 2**20:5.2f} MB" if n else "")
            self.text(p, bx + bw + GAP, y + BAR, tail, INK_2, self.mono)
            if n:
                self._hits.append((QRectF(bx, y, bw, BAR), f"{name} ({n['type']}): a change here reruns ~{_time(n['change_s'])} over the window; "
                                   f"{n['runs']} runs this walk"))
            y += ROW
        y = self.series_lines(p, y, s)
        self.legend(p, PAD, y + 14, w - PAD * 2, types(s) + [("unprobed", OTHER)])
        p.end()


class Stacked(View):
    """Two stacked bars, the cold row and this walk; segments named on hover."""

    def height_for(self, s):
        return PAD + 12 + SECTION + TILE + GAP + ROW * 3 + GAP + 8 + SECTION + ROW * 2 + 6 + 18 * (2 + len(types(s)) // 6) \
            + 18 * len(series_nodes(s)) + PAD

    def paintEvent(self, _):
        s, w = self.s, self.width()
        if s is None:
            return
        self._hits = []
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        y = self.section(p, PAD + 12, "clip", f"{s['count']} rows · {s['fps']:.2f} fps", w)
        y = self.hero(p, y - 12, w, s)
        self.text(p, PAD, y + BAR, f"walk {s['done']} / {s['length']}" + (f" in {_time(s['wall_s'])}" if s["wall_s"] else ""), INK)
        y += ROW
        for name in ("memo", "cache"):
            self.store_bar(p, PAD, y, w - PAD * 2, name, s[name])
            y += ROW
        y = self.section(p, y + GAP * 2 + 4, "nodes", f"one cold row · {s['cold_row_ms']:.2f} ms · {len(frame_nodes(s))} nodes" if s["cold_row_ms"] else "", w)
        cold, total = cold_parts(s), s["cold_row_ms"] or 0.0
        self.text(p, PAD, y + BAR, "cold row", INK)
        self.stacked(p, PAD + 70, y, w - PAD * 2 - 70, cold, total, lambda n, v: f"{n}: {v:.2f} ms, {v / total:.0%} of a cold row")
        y += ROW
        self.text(p, PAD, y + BAR, "this walk", INK)
        self.stacked(p, PAD + 70, y, w - PAD * 2 - 70, walk_parts(s), 1.0, lambda n, v: f"{n}: {v:.0%} of this walk's {_time(s['wall_s'])}")
        y += ROW + 6
        y = self.legend(p, PAD, y + 10, w - PAD * 2, types(s) + [("unprobed", OTHER)])
        self.series_lines(p, y - 6, s)
        p.end()


class Tiles(View):
    """Six stat tiles, then the nodes as a table whose ms column carries its own bar."""

    TILE_H = 60

    def height_for(self, s):
        return PAD + 12 + SECTION + (self.TILE_H + GAP) * 2 + GAP + SECTION + 18 + ROW * (len(s["nodes"]) + 1 + bool(s["series_row_ms"])) + PAD

    def paintEvent(self, _):
        s, w = self.s, self.width()
        if s is None:
            return
        self._hits = []
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        y = self.section(p, PAD + 12, "clip", f"{s['count']} rows · {s['fps']:.2f} fps", w)
        wall = s["wall_s"] * 1000
        y = self.hero(p, y - 12, w, s)
        y = self.tiles(p, y, w, [("walk", f"{s['done']} / {s['length']}", None),
                                 ("memo", f"{s['memo']['windows']:.1f} win" if s["memo"]["windows"] else "-", s["memo"]["windows"]),
                                 ("cache", f"{s['cache']['windows']:.1f} win" if s["cache"]["windows"] else "-", s["cache"]["windows"]),
                                 ("unprobed, this walk", f"{s['other_ms'] / wall:.0%}" if wall else "-", None)])
        y = self.section(p, y + 12, "nodes", "per run; share and runs are this walk's", w)
        label_w = max([QFontMetrics(self.ui).horizontalAdvance(n["node"]) for n in s["nodes"]] + [60]) + GAP
        bar_w = max(60.0, min(160.0, w - PAD * 2 - label_w - 300))
        cx = {"node": PAD, "ms": PAD + label_w, "MB": PAD + label_w + bar_w + 56, "share": PAD + label_w + bar_w + 112,
              "runs": PAD + label_w + bar_w + 160, "change": PAD + label_w + bar_w + 212}
        for k, x in cx.items():
            self.text(p, x, y, k, INK_2, self.mono)
        y += 18
        frame = frame_nodes(s)
        top = max([n["row_ms"] for n in frame] + [s["other_row_ms"] or 0.0, s["series_row_ms"] or 0.0, 1e-9])    # the bars share one scale, the unprobed and series ones too
        for n in s["nodes"]:
            self.text(p, cx["node"], y + BAR, n["node"], INK)
            if not n["series"]:
                c = type_color(n["type"])
                self.bar(p, cx["ms"], y, bar_w * n["row_ms"] / top, BAR, c)
                if n["fold_ms"]:
                    self.bar(p, cx["ms"] + bar_w * n["run_ms"] / top, y, bar_w * n["fold_ms"] / top, BAR, QColor(c.red(), c.green(), c.blue(), 110))
            self.text(p, cx["ms"] + bar_w + 6, y + BAR, f"{n['run_ms'] + n.get('fold_ms', 0.0):.2f}", INK_2, self.mono)
            self.text(p, cx["MB"], y + BAR, f"{n['run_bytes'] / 2**20:.2f}", INK_2, self.mono)
            if not n["series"]:
                self.text(p, cx["share"], y + BAR, f"{n['share']:.0%}" if n["share"] is not None else "-", INK_2, self.mono)
            self.text(p, cx["runs"], y + BAR, str(n["runs"]), INK_2, self.mono)
            self.text(p, cx["change"], y + BAR, "per emit" if n["series"] else f"~{_time(n['change_s'])}", INK_2, self.mono)
            self._hits.append((QRectF(PAD, y, w - PAD * 2, BAR), f"{n['node']} produces {n['type']}"))
            y += ROW
        rest = [("unprobed", s["other_row_ms"], OTHER), ("series, per row", s["series_row_ms"], series_color(s))]
        for name, ms, colour in rest:
            if ms is not None and frame and (ms or name == "unprobed"):
                self.text(p, cx["node"], y + BAR, name, INK_2)
                self.bar(p, cx["ms"], y, bar_w * ms / top, BAR, colour)
                self.text(p, cx["ms"] + bar_w + 6, y + BAR, f"{ms:.2f}", INK_2, self.mono)
                y += ROW
        p.end()


class Pipeline(View):
    """The nodes as a wrapping chain of boxes, width per ms; the stores drawn against the window."""

    BOX = 30

    def _rows(self, s, w):
        """Boxes laid into rows, [[(name, ms, colour, x, width)]], on one px-per-ms scale across rows."""
        parts = cold_parts(s)
        fm = QFontMetrics(self.ui)
        mins = [max(44.0, fm.horizontalAdvance(n) + 12) for n, _, _ in parts]
        avail = w - PAD * 2
        total = sum(v for _, v, _ in parts) or 1.0
        px_per_ms = max(0.0, avail * 1.5 - sum(mins) - GAP * len(parts)) / total
        rows, row, x = [], [], PAD
        for (name, v, c), mn in zip(parts, mins):
            bw = mn + v * px_per_ms
            if row and x + bw > PAD + avail:
                rows.append(row)
                row, x = [], PAD
            row.append((name, v, c, x, bw))
            x += bw + GAP
        if row:
            rows.append(row)
        return rows

    def height_for(self, s):
        rows = len(self._rows(s, max(self.width(), 400)))
        return PAD + 12 + SECTION + TILE + GAP + (18 + GAP) * 2 + 24 + GAP + SECTION + rows * (self.BOX + 36 + GAP) + 18 * len(series_nodes(s)) + 24 + PAD

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.s is not None:
            self.setMinimumHeight(self.height_for(self.s))

    def paintEvent(self, _):
        s, w = self.s, self.width()
        if s is None:
            return
        self._hits = []
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        y = self.section(p, PAD + 12, "clip", f"walk {s['done']} / {s['length']}" + (f" in {_time(s['wall_s'])}" if s["wall_s"] else ""), w)
        y = self.hero(p, y - 12, w, s)
        sx, sw = PAD + 48, w - PAD * 2 - 48
        for name in ("memo", "cache"):
            st, win = s[name], s[name]["windows"]
            self.text(p, PAD, y + 14, name, INK)
            self.trough(p, sx, y, sw, 18)
            if win:
                self.bar(p, sx, y, sw * min(win, 1.0), 18, GOOD if win >= 1 else SHORT)
                label = f"holds the window, {win:.1f}× over" if win >= 1 else f"holds {win:.0%} of the window: the walk evicts ahead of itself"
                self.text(p, sx + 6, y + 14, label, qgray(layer(0)) if win >= 1 else HEAD)
            self._hits.append((QRectF(sx, y, sw, 18), f"{name}: {st['bytes'] / 2**20:.0f} of {(st['limit'] or 0) / 2**20:.0f} MB, "
                               f"{st['row_bytes'] / 2**20:.2f} MB per row, window {s['length']} rows"))
            y += 18 + GAP
        self.text(p, sx, y + 8, f"the window: {s['length']} rows", INK_2)
        y = self.section(p, y + GAP * 2 + 28, "nodes", f"one cold row, left to right · {s['cold_row_ms']:.2f} ms" if s["cold_row_ms"] else "", w)
        total = s["cold_row_ms"] or 1.0
        by_name = {n["node"]: n for n in s["nodes"]}
        for row in self._rows(s, w):
            for name, v, c, x, bw in row:
                self.bar(p, x, y, bw, self.BOX, qgray(layer(2)))
                self.bar(p, x, y, bw, 3, c)
                self.text(p, x + 6, y + 21, name, INK)
                self.text(p, x + 6, y + self.BOX + 14, f"{v:.2f} ms", INK_2, self.mono)
                n = by_name.get(name)
                if n:
                    self.text(p, x + 6, y + self.BOX + 28, f"{n['run_bytes'] / 2**20:.2f} MB", INK_2, self.mono)
                    self._hits.append((QRectF(x, y, bw, self.BOX), f"{name} ({n['type']}): {v / total:.0%} of a cold row; a change reruns ~{_time(n['change_s'])}"))
                if x > PAD:
                    p.setPen(QPen(qgray(INK_2), 1))
                    p.drawLine(QRectF(x - GAP, y + self.BOX / 2, GAP, 0).topLeft(), QRectF(x - GAP, y + self.BOX / 2, GAP, 0).topRight())
            y += self.BOX + 36 + GAP
        for n in series_nodes(s):
            self.text(p, PAD, y + 4, f"→ {n['node']}  {n['run_ms']:.1f} ms per emit, after the walk", INK_2)
            y += 18
        self.legend(p, PAD, y + 14, w - PAD * 2, types(s) + [("unprobed", OTHER)])
        p.end()


VIEWS = {"bars": Bars, "stacked": Stacked, "tiles": Tiles, "pipeline": Pipeline, "text": Text}  # the drop-down's order; opens on the first
