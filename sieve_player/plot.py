"""The plot under the frame: one widget the frame's width where every shown node is drawn over
the loop window, the selection at full strength with its band's handles, the pinned in dimmed ink
each scaled to its own range, a field under the lines, and a press anywhere but a handle is the
playhead; Stage is the frame over it inside one outline, Head the playhead's circle astride their
seam. Paints what it is told and proposes gestures; of the document it knows the shown rule alone,
of the runtime nothing.
"""
import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QFontMetrics, QImage, QMouseEvent, QPainter, QPainterPath, QPen, QPolygonF, QRegion
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from . import density, theme
from .document import shown
from .theme import FADED_ALPHA, FADED_FIELD, FIELD_ALPHA, GAP, INK_ALPHA, PAD, ROW_H, SHUT_ALPHA, mono_font, qgray

OPEN = (0.0, float("inf"))   # a band that shuts nothing out, as document.OPEN
AXIS_W = 52       # px: the gutter at the left where the selection's axis is labelled
CHIP_GAP = 3      # px: between a chip's name and its pin
LABEL_ROOM = ROW_H  # px: the least distance between two labels on the axis
TICK_SPACINGS = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600)   # whole seconds between ticks
TICK_ROOM = 24    # px: the least distance between two ticks
TICK_H = 5        # px: a tick's length down from the top edge


def nice(x):
    """The least of 1, 2 or 5 times a power of ten that is at least `x`."""
    e = 10.0 ** np.floor(np.log10(x)) if x > 0 else 1.0
    return float(next(m * e for m in (1, 2, 5, 10) if m * e >= x))


def label(v):
    return "∞" if v == float("inf") else f"{v:.4g}"


class Line:
    """A series node's signal from row `start`, with its gate when it has one."""

    def __init__(self, values, start, gate=None):
        self.values = np.asarray(values, np.float32)
        self.start, self.gate = int(start), None if gate is None else np.asarray(gate, bool)

    @property
    def top(self):
        return max(float(self.values.max()), 1e-6) if len(self.values) else 1e-6


class Field:
    """A frame node's density from row `start`: (rows, bins) counts on sieve_player.density's axis
    unless `value_of(bin)` names another. `lo`..`hi` are the bins shown, the whole axis until crop()
    narrows them to the ones the window's rows occupy."""
    MARGIN = 2   # bins of room past the occupied ones

    def __init__(self, counts, start, value_of=None):
        self.counts, self.start = np.asarray(counts), int(start)
        self.value_of = value_of or density.value_of
        self.lo, self.hi = 0, self.counts.shape[1] - 1 if self.counts.ndim == 2 else 0

    def crop(self, start, n):
        """Sets `lo`..`hi` to the bins any row in start..start+n occupies plus MARGIN either side, the
        whole axis when none does."""
        if self.counts.ndim != 2:
            return
        i0 = self.start - start
        rows = self.counts[max(0, -i0):max(0, min(len(self.counts), n - i0))]
        occupied = np.flatnonzero(rows.any(axis=0))
        bins = self.counts.shape[1]
        if len(occupied):
            self.lo, self.hi = max(0, occupied[0] - self.MARGIN), min(bins - 1, occupied[-1] + self.MARGIN)
        else:
            self.lo, self.hi = 0, bins - 1

    def pos(self, v):
        """A value's place on the shown axis, in bins from the first shown, clipped to its ends."""
        return min(max(density.pos_of(v) - self.lo, 0.0), self.hi - self.lo + 1.0)

    def kept(self, levels):
        """Which shown bins the band keeps, (shown bins,) bool, by each bin's centre."""
        centres = np.arange(self.lo, self.hi + 1) + 0.5 - self.lo
        a, b = self.pos(levels[0]), self.pos(levels[1])
        return (centres >= a) & (centres <= b) if a <= b else (centres >= a) | (centres <= b)


class ChipRow:
    """One chip per name in a row ROW_H tall ending at `bottom`, laid from `right` leftwards so the
    first name is leftmost: a pin glyph GLYPH square with the name to its left, CHIP_GAP between, GAP
    between chips. A name is elided in the middle, the longest giving way first, while the row would
    otherwise reach `left`; a pin is never dropped. `chips` is (name, name rect, pin rect, text
    drawn) per name, and hit(pos) is ("name" | "pin", name) for the chip part under a point, else
    None."""

    def __init__(self, font, names, left, right, bottom):
        fm = QFontMetrics(font)
        widths = {n: fm.horizontalAdvance(n) + 2 for n in names}
        free = right - left - len(names) * (theme.GLYPH + CHIP_GAP) - max(len(names) - 1, 0) * GAP
        texts = {}
        for k, n in enumerate(sorted(names, key=widths.__getitem__)):
            share = max(free / (len(names) - k), 0.0)
            texts[n] = n if widths[n] <= share else fm.elidedText(n, Qt.ElideMiddle, int(share) - 2)
            free -= min(widths[n], share)
        self.chips = []
        for n in reversed(names):
            pin = QRectF(right - theme.GLYPH, bottom - ROW_H + (ROW_H - theme.GLYPH) / 2, theme.GLYPH, theme.GLYPH)
            w = fm.horizontalAdvance(texts[n]) + 2
            name = QRectF(pin.left() - CHIP_GAP - w, bottom - ROW_H, w, ROW_H)
            self.chips.append((n, name, pin, texts[n]))
            right = name.left() - GAP
        self.chips.reverse()

    def hit(self, pos):
        for n, name, pin, _ in self.chips:
            if name.contains(pos):
                return "name", n
            if pin.contains(pos):
                return "pin", n
        return None


class Plot(QWidget):
    """Feed it the window with set_window(start, length, fps), the lines with set_lines({node: (values,
    gate)}, start) and the fields with set_fields({node: counts}, start), each from the row the walk
    began at; set_selection(node), set_pinned([node, ...]) and set_bands({node: (lo, hi)}) say what
    is shown and how. A node is drawn while it is the selection or pinned and has a line or a
    field. Where there are more rows than pixel columns each column is the min and max of the
    rows it covers, so nothing is hidden and nothing is added; a walk still filling in draws what it
    has at its rows and leaves the rest empty. The selection's line is teal, or green with a gate
    whose rows are washed; its field is the DENSITY ramp; its band is two LEVEL lines with a dot at
    either end, the values shut out darkened, a handle at the top infinity. Its axis is labelled
    in a gutter at the left, AXIS_W wide, in its own units: each band value in LEVEL at its line's
    height, and a few of the scale's values in ink between them, axis_labels() saying which. A
    pinned line is ink at INK_ALPHA over the whole height, down to SHUT_ALPHA over the rows its own
    band shuts out, with no handles or axis; a pinned field is under every line at FIELD_ALPHA, at
    most one; while a handle is held both fade to FADED_ALPHA and FADED_FIELD.

    A press on a handle drags it, proposing the band: bandDragged(node, levels) as it moves and
    bandReleased(node, levels) once when let go, neither moving the band drawn, which is what
    set_bands last handed over; any other press is the playhead, pressed, dragged and released in
    rows, and a press on the playhead's circle is the playhead whatever handle lies under it. The
    circle is centred on the top edge, so only its lower half is drawn here; head_x() and headMoved
    let a widget astride the edge draw the whole of it. The cursor's row is
    hovered(row), -1 on leave, and set_hover(row) draws another widget's cursor here: a dotted
    line, and where it crosses each shown line a dot with the node's name and value beside it,
    readouts() saying where. The corner readout is the selection's value at the playhead while
    there is no hover; over a field it is the bin under the cursor.

    The chip row along the bottom is a ChipRow of the nodes drawn kept right of the gutter, the
    selection's name in head white and the rest in ink, a pin glyph beside each filled while the
    node is pinned; chips() says where each sits. A press on a name is chipClicked(node), on a pin
    pinToggled(node), and neither seeks."""
    pressed = Signal(int)
    dragged = Signal(int)
    released = Signal(int)
    hovered = Signal(int)
    bandDragged = Signal(str, object)
    bandReleased = Signal(str, object)
    chipClicked = Signal(str)
    pinToggled = Signal(str)
    headMoved = Signal()
    ROWS = 7     # the plot's height in form rows
    GRAB = 4     # px either side of a handle's line that takes the drag
    STUB = 6     # px: a handle's line runs this far past the field's edge
    DOT = 3.2    # px: the radius of the dot it ends in
    HEAD_R = 5.0 # px: the playhead's circle

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start, self.length, self.fps = 0, 0, 30.0
        self.playhead, self.hover = 0, -1
        self.lines, self.fields, self.bands = {}, {}, {}
        self.selection, self.pinned = None, []
        self._mode = None       # "head" | the index of the handle held
        self._y_hover = None
        self.setFixedHeight(ROW_H * self.ROWS)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setFont(mono_font())

    # -- what is shown ---------------------------------------------------
    def set_window(self, start, length, fps=None):
        self.start, self.length = int(start), int(length)
        if fps:
            self.fps = float(fps)
        self._crop()
        self.update()
        self.headMoved.emit()

    def set_lines(self, lines, start):
        self.lines = {nid: Line(v, start, g) for nid, (v, g) in lines.items()}
        self.update()

    def set_fields(self, fields, start):
        self.fields = {nid: Field(c, start) for nid, c in fields.items()}
        self._crop()
        self.update()

    def _crop(self):
        for f in self.fields.values():
            f.crop(self.start, self._axis())

    def set_bands(self, bands):
        self.bands = {nid: [float(v) for v in (b if b is not None else OPEN)] for nid, b in bands.items()}
        self.update()

    def set_selection(self, nid):
        self.selection = nid
        self.update()

    def set_pinned(self, ids):
        self.pinned = list(ids)
        self.update()

    def set_playhead(self, row):
        self.playhead = row
        self.update()
        self.headMoved.emit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.headMoved.emit()

    def head_x(self):
        """The playhead's x, or None when its row is outside the window or there is no window."""
        return self._x(self.playhead) if self.length >= 2 and 0 <= self.playhead - self.start < self._axis() else None

    def set_hover(self, row):
        self.hover = row
        self.update()

    def shown(self):
        return shown(self.selection, self.pinned)

    def field_shown(self):
        """The one field drawn: the selection's, else the first pinned with one."""
        return next((nid for nid in self.shown() if nid in self.fields), None)

    def levels(self, nid):
        return self.bands.get(nid) or list(OPEN)

    # -- geometry --------------------------------------------------------
    def _inner(self):
        """The field the series fill: the widget inset by the handles' dots at either side and the
        axis gutter at the left."""
        m = self.STUB + self.DOT
        return QRectF(self.rect()).adjusted(AXIS_W + m + 1.5, 1.5, -m - 1.5, -ROW_H - 1.5)

    def chips(self):
        return self._chips().chips

    def _chips(self):
        drawn = [nid for nid in self.shown() if nid in self.lines or nid in self.fields]
        return ChipRow(self.font(), drawn, AXIS_W, self.width() - PAD, self.height())

    def _chip_hit(self, pos):
        """(signal, node) for a press on a chip's name or pin, else None."""
        hit = self._chips().hit(pos)
        if hit is None:
            return None
        part, nid = hit
        return (self.chipClicked if part == "name" else self.pinToggled), nid

    def _label_right(self):
        """Where a label in the gutter ends, right-aligned, clear of the handle's dot."""
        return self._inner().left() - self.STUB - self.DOT - 3

    def ink_alpha(self):
        """What a pinned line is drawn at now: faded while a handle of the selection's is held."""
        return FADED_ALPHA if self._mode not in (None, "head") else INK_ALPHA

    def axis_labels(self):
        """The gutter's labels, (value, y, kind): the selection's band values, kind "band", and the
        scale's values that keep LABEL_ROOM from them and each other, kind "axis"; none when the
        selection has no line or field."""
        nid = self.selection
        if self.length < 2 or not self._handled():
            return []
        inner = self._inner()
        out = [(v, self._y(v, nid), "band") for v in self.levels(nid)]
        for v in self._scale(nid):
            y = self._y(v, nid)
            if inner.top() <= y <= inner.bottom() and all(abs(y - t) >= LABEL_ROOM / 2 for _, t, _ in out):
                out.append((v, y, "axis"))
        return out

    def _scale(self, nid):
        """The scale's values for `nid`: multiples of a 1-2-5 step for a line, whose axis is linear
        in its range; for a field the 1-2-5 numbers along its log axis that keep LABEL_ROOM apart."""
        slots = max(int(self._inner().height() // LABEL_ROOM), 1)
        if nid in self.lines:
            top = self.lines[nid].top
            step = nice(top / slots)
            return [k * step for k in range(int(top // step) + 1)]
        f = self.fields[nid]
        out = [0.0] if f.lo == 0 else []
        v, last = 1.0 if f.lo == 0 else nice(f.value_of(f.lo)), f.value_of(f.hi)
        while v <= last:
            if not out or abs(self._y(v, nid) - self._y(out[-1], nid)) >= LABEL_ROOM:
                out.append(v)
            v = nice(v * 1.01)
        return out

    def _axis(self):
        return max(self.length, 2)

    def _step(self):
        return self._inner().width() / (self._axis() - 1)

    def _row(self, x):
        i = round((x - self._inner().left()) / self._step())
        return self.start + max(0, min(self._axis() - 1, i))

    def _x(self, row):
        return self._inner().left() + self._step() * (row - self.start)

    def _y(self, v, nid):
        """A value's height for `nid`: a line over its own top, a field over its shown bins."""
        inner = self._inner()
        f = self.fields.get(nid)
        if f is not None and nid not in self.lines:
            return inner.bottom() - inner.height() * f.pos(v) / (f.hi - f.lo + 1)
        return inner.bottom() - inner.height() * min(float(v) / self.lines[nid].top, 1.0)

    def ticks(self):
        """The ticks' rows: the window's first and last, and every whole-second multiple of a spacing
        between them that keeps the ticks TICK_ROOM apart."""
        if self.length < 2:
            return []
        per_px = self.length / self.fps / max(self._inner().width(), 1)
        spacing = next((s for s in TICK_SPACINGS if s / per_px >= TICK_ROOM), TICK_SPACINGS[-1])
        first, last = self.start, self.start + self.length - 1
        apart = TICK_ROOM * per_px * self.fps
        rows = [first]
        k = int(np.ceil(first / self.fps / spacing))
        while (row := int(round(k * spacing * self.fps))) <= last:
            if row - rows[-1] >= apart and last - row >= apart:
                rows.append(row)
            k += 1
        return rows + [last]

    # -- painting --------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        inner = self._inner()
        p.setPen(Qt.NoPen)
        p.setBrush(qgray(theme.layer(0) + theme.MEASURED_LIFT))
        field = QPainterPath()
        field.addRoundedRect(QRectF(self.rect()).adjusted(0, -theme.RADIUS, 0, 0), theme.RADIUS, theme.RADIUS)   # square at the top, where it meets the frame
        p.drawPath(field)
        self._paint_ticks(p, inner)
        if self.length < 2:
            p.end()
            return
        sel = self.selection
        fid = self.field_shown()
        held = self._mode not in (None, "head")
        if fid is not None:
            self._paint_field(p, inner, fid, 1.0 if fid == sel else FADED_FIELD if held else FIELD_ALPHA)
        if sel in self.lines:
            self._paint_shut(p, inner, sel)
        for nid in self.shown():
            if nid in self.lines and nid != sel:
                self._paint_pinned_line(p, inner, nid)
        if sel in self.lines:
            line = self.lines[sel]
            self._paint_line(p, inner, sel, theme.GATE if line.gate is not None else theme.SERIES, True)
        if self._handled():
            self._paint_levels(p, inner, sel)
            self._paint_axis(p, inner)
        self._paint_cursor(p, inner)
        self._paint_readouts(p)
        self._paint_readout(p, inner, sel)
        self._paint_chips(p)
        p.end()

    def _paint_chips(self, p):
        for nid, name, pin, text in self.chips():
            p.setPen(qgray(theme.HEAD if nid == self.selection else theme.INK))
            p.drawText(name, Qt.AlignLeft | Qt.AlignVCenter, text)
            pinned = nid in self.pinned
            pm = theme.glyph("pinned" if pinned else "pin", theme.INK if pinned else theme.INK_2, theme.GLYPH, self.devicePixelRatioF())
            p.drawPixmap(pin.topLeft(), pm)

    def _columns(self, nid):
        """How a node's rows lie over the axis: (xs, width per column, first-sample indices for a dense
        series or None, the slice of its rows inside the window), or None with nothing inside."""
        item = self.lines.get(nid) or self.fields.get(nid)
        inner, N, step = self._inner(), self._axis(), self._step()
        n = len(item.values) if isinstance(item, Line) else len(item.counts)
        i0 = item.start - self.start
        lo, hi = max(0, -i0), min(n, N - i0)
        if hi - lo < 1:
            return None
        rows = np.arange(lo, hi) + i0
        width = int(inner.width())
        if N - 1 >= width > 1:
            col = rows * (width - 1) // (N - 1)
            starts = np.flatnonzero(np.diff(col, prepend=-1))
            return inner.left() + col[starts].astype(np.float64), 1.0, starts, slice(lo, hi)
        return inner.left() + step * rows, step, None, slice(lo, hi)

    def _paint_line(self, p, inner, nid, color, washed):
        line = self.lines[nid]
        placed = self._columns(nid)
        if placed is None:
            return
        xs, w, starts, rows = placed
        values = line.values[rows]
        p.setPen(Qt.NoPen)
        if washed and line.gate is not None:
            gate = line.gate[rows]
            gated = np.maximum.reduceat(gate.astype(np.uint8), starts) > 0 if starts is not None else gate
            if gated.any():
                # one rect per run, so the translucent wash has no seams between rows
                edges = np.flatnonzero(np.diff(np.concatenate(([0], gated.astype(np.int8), [0]))))
                p.setBrush(theme.GATED)
                for a, b in zip(edges[0::2], edges[1::2] - 1):
                    x0, x1 = max(xs[a] - w / 2, inner.left()), min(xs[b] + w / 2, inner.right())
                    p.drawRect(QRectF(x0, inner.top(), x1 - x0, inner.height()))
        if len(values) < 2:
            if len(values) == 1:
                p.setPen(QPen(color, 1.6))
                p.drawPoint(QPointF(xs[0], self._y(values[0], nid)))
            return
        if starts is not None:
            lo, hi = np.minimum.reduceat(values, starts), np.maximum.reduceat(values, starts)
            top = [QPointF(x, self._y(v, nid)) for x, v in zip(xs, hi)]
            bottom = [QPointF(x, self._y(v, nid)) for x, v in zip(xs[::-1], lo[::-1])]
            p.setPen(QPen(color, 1))
            p.setBrush(color)
            p.drawPolygon(QPolygonF(top + bottom))
        else:
            p.setPen(QPen(color, 1.6))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(x, self._y(v, nid)) for x, v in zip(xs, values)]))

    def _paint_pinned_line(self, p, inner, nid):
        """The band is on values and y is monotonic in them, so the kept rows are a y range: the
        line at SHUT_ALPHA over the whole height, then again at full ink clipped to that range."""
        alpha = self.ink_alpha()
        lo, hi = self.levels(nid)
        if (lo, hi) == OPEN:
            self._paint_line(p, inner, nid, qgray(theme.INK, alpha), False)
            return
        self._paint_line(p, inner, nid, qgray(theme.INK, round(alpha * SHUT_ALPHA / INK_ALPHA)), False)
        y_lo, y_hi = self._y(lo, nid), self._y(hi, nid)
        kept = [(y_hi, y_lo)] if y_lo >= y_hi else [(inner.top(), y_lo), (y_hi, inner.bottom())]
        region = QRegion()
        for y0, y1 in kept:
            region += QRegion(QRectF(inner.left() - 2, y0, inner.width() + 4, y1 - y0).toAlignedRect())
        p.save()
        p.setClipRegion(region)
        self._paint_line(p, inner, nid, qgray(theme.INK, alpha), False)
        p.restore()

    def _ramp(self):
        base = theme.layer(0) + theme.MEASURED_LIFT
        stops = ((base, base, base), *theme.DENSITY)
        xs = np.linspace(0, 1, len(stops))
        return np.stack([np.interp(np.linspace(0, 1, 256), xs, [c[k] for c in stops]) for k in range(3)], axis=1).astype(np.uint8)

    def _paint_field(self, p, inner, nid, opacity):
        """Each column a row, each pixel-row a value bin lit by log1p(count) over log1p(the column's
        pixels); the picture is the field's cropped bins, and the bins the band drops count for
        nothing, so the ramp spends its range on the values kept."""
        f = self.fields[nid]
        placed = self._columns(nid)
        if placed is None or f.counts.ndim != 2:
            return
        xs, w, starts, rows = placed
        c = f.counts[rows]
        if starts is not None:
            c = np.add.reduceat(c, starts, axis=0)
        c = np.asarray(c, np.float64)[:, f.lo:f.hi + 1] * f.kept(self.levels(nid))
        total = np.maximum(c.sum(axis=1, keepdims=True), 1.0)
        lit = np.log1p(c) / np.log1p(total)
        rgb = self._ramp()[(np.clip(lit, 0, 1) * 255).astype(np.uint8)]
        rgb = np.ascontiguousarray(np.transpose(rgb, (1, 0, 2))[::-1])
        h, wd = rgb.shape[:2]
        img = QImage(rgb.data, wd, h, rgb.strides[0], QImage.Format_RGB888).copy()
        p.save()
        p.setClipRect(inner)
        p.setOpacity(opacity)
        p.drawImage(QRectF(xs[0] - w / 2 if starts is None else xs[0], inner.top(), float(wd) if starts is not None else w * wd, inner.height()), img)
        p.restore()

    def _paint_shut(self, p, inner, nid):
        """Darken what the selection's band shuts out: outside it, or inside when lo is above hi."""
        lo, hi = self.levels(nid)
        y_lo, y_hi = self._y(lo, nid), self._y(hi, nid)
        shut = ([(y_lo, inner.bottom()), (inner.top(), y_hi)] if y_lo >= y_hi else [(y_lo, y_hi)])
        p.setPen(Qt.NoPen)
        p.setBrush(theme.EXCLUDED)
        for y0, y1 in shut:
            p.drawRect(QRectF(inner.left(), y0, inner.width(), y1 - y0))

    def _paint_levels(self, p, inner, nid):
        for v in self.levels(nid):
            # on a pixel's centre: a 1px line between two rows antialiases to half strength in each
            y, x0, x1 = round(self._y(v, nid) - 0.5) + 0.5, inner.left() - self.STUB, inner.right() + self.STUB
            p.setPen(QPen(theme.LEVEL, 1))
            p.setBrush(theme.LEVEL)
            p.drawLine(QPointF(x0, y), QPointF(x1, y))
            for x in (x0, x1):
                p.drawEllipse(QPointF(x, y), self.DOT, self.DOT)
            p.setBrush(Qt.NoBrush)

    def _paint_axis(self, p, inner):
        right, h = self._label_right(), p.fontMetrics().height()
        for v, y, kind in self.axis_labels():
            p.setPen(QPen(theme.LEVEL if kind == "band" else qgray(theme.INK_2), 1))
            if kind == "axis":
                p.drawLine(QPointF(inner.left() - TICK_H, y), QPointF(inner.left(), y))
            top = min(max(y - h / 2, 0.0), self.height() - h)
            p.drawText(QRectF(0, top, right, h), Qt.AlignRight | Qt.AlignVCenter, label(v))

    def _paint_ticks(self, p, inner):
        p.setPen(QPen(qgray(theme.INK_2), 1))
        for row in self.ticks():
            x = self._x(row)
            p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.top() + TICK_H))

    def readouts(self):
        """What the hover's line says where it crosses each shown line: (node, text, dot, rect) per
        node with a value at the hovered row, text the node's name and that value, the rect where
        the text sits, beside the dot and pushed apart from the others' so none overprint; none
        without a hover."""
        out = []
        fm = QFontMetrics(self.font())
        h, inner = fm.height(), self._inner()
        for nid in self.shown():
            line = self.lines.get(nid)
            if line is None or not 0 <= self.hover - line.start < len(line.values):
                continue
            v = float(line.values[self.hover - line.start])
            dot = QPointF(self._x(self.hover), self._y(v, nid))
            text = f"{nid} {v:.4g}"
            w = fm.horizontalAdvance(text) + 2
            x = dot.x() + self.DOT + 4
            if x + w > inner.right():
                x = dot.x() - self.DOT - 4 - w
            out.append([nid, text, dot, QRectF(x, dot.y() - h / 2, w, h)])
        out.sort(key=lambda r: r[3].top())
        for a, b in zip(out, out[1:]):
            if b[3].top() < a[3].bottom():
                b[3].moveTop(a[3].bottom())
        for a, b in zip(reversed(out[:-1]), reversed(out)):
            b[3].moveBottom(min(b[3].bottom(), inner.bottom()))
            if a[3].bottom() > b[3].top():
                a[3].moveBottom(b[3].top())
        return [tuple(r) for r in out]

    def _paint_readouts(self, p):
        for nid, text, dot, rect in self.readouts():
            colour = (theme.GATE if self.lines[nid].gate is not None else theme.SERIES) if nid == self.selection else qgray(theme.INK)
            p.setPen(Qt.NoPen)
            p.setBrush(colour)
            p.drawEllipse(dot, self.DOT, self.DOT)
            p.setPen(colour)
            p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)

    def _paint_cursor(self, p, inner):
        N = self._axis()
        i = self.hover - self.start
        if 0 <= i < N:
            p.setPen(QPen(qgray(theme.INK_2), 1, Qt.DotLine))
            x = self._x(self.hover)
            p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
        i = self.playhead - self.start
        if 0 <= i < N:
            x = self._x(self.playhead)
            p.setPen(QPen(qgray(theme.HEAD), 1.5))
            p.drawLine(QPointF(x, 0.0), QPointF(x, inner.bottom()))
            p.setPen(Qt.NoPen)
            p.setBrush(qgray(theme.HEAD))
            p.drawEllipse(QPointF(x, 0.0), self.HEAD_R, self.HEAD_R)

    def _paint_readout(self, p, inner, nid):
        """The corner: the selection's value at the playhead while no hover reads it at the dot, or
        over a field the value of the bin under the cursor."""
        text = None
        if nid in self.lines:
            line = self.lines[nid]
            i = self.playhead - line.start
            if self.hover < 0 and 0 <= i < len(line.values):
                text = f"{float(line.values[i]):.4g}"
        elif nid in self.fields and self._y_hover is not None:
            f = self.fields[nid]
            frac = (inner.bottom() - self._y_hover) / inner.height()
            b = f.lo + int(np.clip(frac, 0, 1) * (f.hi - f.lo + 1))
            text = f"{f.value_of(min(b, f.hi)):.4g}"
        if text is not None:
            p.setPen(qgray(theme.INK_2))
            p.drawText(inner.adjusted(0, 2, -6, 0), Qt.AlignRight | Qt.AlignTop, text)

    # -- gestures --------------------------------------------------------
    def _handled(self):
        """Whether the selection has handles to drag: a line or a field of its own."""
        return self.selection in self.lines or self.selection in self.fields

    def _hit(self, pos):
        """The playhead's circle, else the nearest handle of the selection within GRAB of the cursor,
        at any x, else the playhead."""
        x = self.head_x()
        if not self._handled() or (x is not None and (pos.x() - x) ** 2 + pos.y() ** 2 <= self.HEAD_R ** 2):
            return "head"
        near = [(abs(pos.y() - self._y(v, self.selection)), i) for i, v in enumerate(self.levels(self.selection))]
        near = [(d, i) for d, i in near if d <= self.GRAB]
        return min(near)[1] if near else "head"

    def _drag_level(self, i, y):
        """Proposes the selection's band with handle `i` at `y` through bandDragged; nothing here
        changes until set_bands hands a band back."""
        nid, inner = self.selection, self._inner()
        frac = (inner.bottom() - y) / inner.height()
        levels = list(self.levels(nid))
        if nid in self.lines:
            levels[i] = float("inf") if frac >= 1.0 else max(0.0, self.lines[nid].top * frac)
        else:
            f = self.fields[nid]
            levels[i] = float("inf") if frac >= 1.0 else f.value_of(f.lo + max(frac, 0.0) * (f.hi - f.lo + 1))
        self.bandDragged.emit(nid, levels)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.length < 2:
            return
        chip = self._chip_hit(e.position())
        if chip is not None:
            chip[0].emit(chip[1])
            return
        self._mode = self._hit(e.position())
        if self._mode != "head":
            self._drag_level(self._mode, e.position().y())
        else:
            self.pressed.emit(self._row(e.position().x()))

    def mouseMoveEvent(self, e):
        self._y_hover = e.position().y()
        if self._mode is None:
            self.setCursor(Qt.PointingHandCursor if self._chip_hit(e.position()) else
                           Qt.ArrowCursor if self._hit(e.position()) == "head" else Qt.SizeVerCursor)
            row = self._row(e.position().x()) if self.length >= 2 else -1
            if row != self.hover:
                self.hover = row
                self.hovered.emit(row)
            self.update()
        elif self._mode != "head":
            self._drag_level(self._mode, e.position().y())
        else:
            self.dragged.emit(self._row(e.position().x()))

    def mouseReleaseEvent(self, e):
        if self._mode == "head":
            self.released.emit(self._row(e.position().x()))
        elif self._mode is not None:
            self.bandReleased.emit(self.selection, list(self.levels(self.selection)))
        self._mode = None
        self.update()

    def leaveEvent(self, _):
        self._y_hover = None
        if self.hover != -1:
            self.hover = -1
            self.hovered.emit(-1)
        self.update()


class Head(QWidget):
    """The playhead's circle astride the seam between the frame and the plot: a sibling over both,
    shaped to the circle so the frame keeps the rest of the band, and every gesture on it is the
    plot's, forwarded in the plot's coordinates."""
    R = Plot.HEAD_R + 1   # the mask's radius: a pixel of room for the circle's antialiased edge

    def __init__(self, plot, parent):
        super().__init__(parent)
        self.plot = plot
        self.setMouseTracking(True)
        plot.headMoved.connect(self.place)

    def place(self):
        self.setGeometry(self.plot.x(), self.plot.y() - self.R, self.plot.width(), 2 * self.R)
        x = self.plot.head_x()
        if x is None:
            self.hide()
            return
        self.setMask(QRegion(QRect(round(x) - self.R, 0, 2 * self.R, 2 * self.R), QRegion.Ellipse))
        self.show()
        self.update()

    def paintEvent(self, _):
        x = self.plot.head_x()
        if x is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(qgray(theme.HEAD))
        p.drawEllipse(QPointF(x, self.R), Plot.HEAD_R, Plot.HEAD_R)
        p.end()

    def _forward(self, e, handler):
        pos = QPointF(e.position().x(), e.position().y() - self.R)
        handler(QMouseEvent(e.type(), pos, e.globalPosition(), e.button(), e.buttons(), e.modifiers()))

    def mousePressEvent(self, e):
        self._forward(e, self.plot.mousePressEvent)

    def mouseMoveEvent(self, e):
        self._forward(e, self.plot.mouseMoveEvent)

    def mouseReleaseEvent(self, e):
        self._forward(e, self.plot.mouseReleaseEvent)


class Stage(QWidget):
    """The left side: the frame over the plot, flush, inside one hairline outline so the two read as
    one object; neither child draws an edge of its own."""

    def __init__(self, display, plot, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)
        lay.addWidget(display, 1)
        lay.addWidget(plot, 0)
        self.head = Head(plot, self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.layout().activate()
        self.head.place()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(qgray(theme.GROUND + theme.LINE_LIFT), 1))
        p.setBrush(qgray(theme.GROUND))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), theme.RADIUS, theme.RADIUS)
        p.end()
