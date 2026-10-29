"""Optional bases so a tool file stays one screen long: a settings form and a series trace."""
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QSlider, QVBoxLayout, QWidget

from . import density, theme
from .theme import CONTROL_W, GAP, ROW_H, VALUE_W, Form, mono_font, qgray


class ParamWidget(QWidget):
    """Has .changed and .params(). Add rows with add_int / add_float / add_bool / add_text /
    add_choice; each is one line of the form, a knob: slider and its mono readout together fill the
    one control width. The int and float rows return their slider, for a tool that also sets the
    value from elsewhere. A text row commits on Enter or focus loss, as a Houdini field does, so a
    half-typed pattern is never a change. `set_driven(names, by)` greys the rows a wire drives, as
    Blender does a driven property: they take no typed value until the wire is broken."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._get, self._set, self._rows = {}, {}, {}
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(GAP)
        self.form = Form()
        self._lay.addWidget(self.form)

    def params(self):
        return {k: g() for k, g in self._get.items()}

    def set_params(self, params):
        """Move the knobs to `params`; each one that moves emits changed."""
        for k, v in params.items():
            if k in self._set:
                self._set[k](v)

    def set_driven(self, names, by=None):
        """Grey the rows in `names`, which node `by` drives, and free every other."""
        names = set(names)
        for name, row in self._rows.items():
            row.setEnabled(name not in names)
            row.setToolTip(f"driven by {by}; break the wire to edit" if name in names else "")

    def _slider(self, name, lo, hi, value, fmt):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(GAP)
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(value)
        s.setFixedWidth(CONTROL_W - VALUE_W - GAP)
        out = QLabel(fmt(value))
        out.setFont(mono_font())
        out.setFixedWidth(VALUE_W)
        out.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        s.valueChanged.connect(lambda v: (out.setText(fmt(v)), self.changed.emit()))
        h.addWidget(s)
        h.addWidget(out)
        w.setFixedWidth(CONTROL_W)
        self.form.add_row(name, w)
        self._rows[name] = w
        return s

    def add_int(self, name, lo, hi, value):
        s = self._slider(name, lo, hi, int(value), str)
        self._get[name], self._set[name] = s.value, lambda v: s.setValue(int(v))
        return s

    def add_float(self, name, lo, hi, value, decimals=2):
        k = 10 ** decimals
        s = self._slider(name, round(lo * k), round(hi * k), round(value * k), lambda v: f"{v / k:.{decimals}f}")
        self._get[name], self._set[name] = lambda: s.value() / k, lambda v: s.setValue(round(v * k))
        return s

    def add_bool(self, name, value):
        c = QCheckBox()
        c.setChecked(bool(value))
        c.toggled.connect(lambda _: self.changed.emit())
        self.form.add_row(name, c)
        self._rows[name] = c
        self._get[name], self._set[name] = c.isChecked, lambda v: c.setChecked(bool(v))

    def add_text(self, name, value):
        e = QLineEdit(str(value))
        e.setFont(mono_font())
        e.setFixedWidth(CONTROL_W)
        last = [e.text()]

        def commit():
            if e.text() != last[0]:
                last[0] = e.text()
                self.changed.emit()
        e.editingFinished.connect(commit)
        self.form.add_row(name, e)
        self._rows[name] = e

        def set_(v):
            e.setText(str(v))
            commit()
        self._get[name], self._set[name] = e.text, set_
        return e

    def add_choice(self, name, options, value):
        c = QComboBox()
        c.addItems([str(o) for o in options])
        c.setCurrentText(str(value))
        c.setFixedWidth(CONTROL_W)
        c.currentTextChanged.connect(lambda _: self.changed.emit())
        self.form.add_row(name, c)
        self._rows[name] = c
        self._get[name], self._set[name] = c.currentText, lambda v: c.setCurrentText(str(v))
        return c


class Trace(QWidget):
    """A series over the loop window, drawn as a measured field on the layer it sits in: the
    series in teal, the playhead in white, and if there is a gate, the gated rows washed green
    full height: v2's plot colors. A trace with handles is a detector, as v2's count plot was,
    and draws its series green too; green is otherwise never a series. Where there are more samples than pixels each column shows the
    min and max of the samples it covers, so nothing is hidden and nothing is added. Feed it with
    set_series(values, start, gate=None, levels=()) and set_playhead(row).

    A trace built with `levels=n` has n handles, in the units of `values`: each a red line
    across the plot, run out past either edge of the field to a dot. Every trace's field is
    inset by the dots' room, handles or not, so stacked traces share their x. Two handles are a
    band (lo, hi) as rangegate reads it, and the values it shuts out are darkened: outside the
    band, or inside it when lo is above hi. A press on a handle's line or dots drags it up or down (levelDragged(index,
    value)); any other press is the playhead (pressed/dragged/released, rows). The cursor's row is
    reported as hovered(row), -1 on leave; set_hover(row) draws another widget's cursor here. The
    corner readout is the value under the cursor, else at the playhead."""
    pressed = Signal(int)
    dragged = Signal(int)
    released = Signal(int)
    hovered = Signal(int)
    levelDragged = Signal(int, float)
    GRAB = 4   # px either side of a handle's line that takes the drag
    STUB = 6   # px: a handle's line runs this far past the plot's edge
    DOT = 3.2  # px: the radius of the dot it ends in

    def __init__(self, parent=None, rows=3, levels=0):
        super().__init__(parent)
        self.values, self.gate, self.levels = None, None, [0.0] * levels
        self.start, self.playhead, self.hover = 0, 0, -1
        self._mode = None   # "head" | the index of the handle held
        self.setFixedHeight(ROW_H * rows)
        self.setMouseTracking(True)
        self.setFont(mono_font())

    def set_series(self, values, start, gate=None, levels=()):
        """`levels` moves the handles; fewer than built leave the rest where they are."""
        self.values = None if values is None else np.asarray(values, np.float32)
        self.gate = None if gate is None else np.asarray(gate, bool)
        levels = [float(v) for v in levels][: len(self.levels)]
        self.levels[: len(levels)] = levels
        self.start = start
        self.update()

    def set_playhead(self, row):
        self.playhead = row
        self.update()

    def set_hover(self, row):
        self.hover = row
        self.update()

    # -- geometry --------------------------------------------------------
    def _box(self):
        m = self.STUB + self.DOT
        return QRectF(self.rect()).adjusted(m + 0.5, 0.5, -m - 0.5, -0.5)

    def _inner(self):
        return self._box().adjusted(1, 1, -1, -1)

    def _top(self):
        return max(float(self.values.max()), *self.levels, 1e-6)

    def _y(self, v):
        inner = self._inner()
        return inner.bottom() - inner.height() * float(v) / self._top()

    def _step(self):
        return self._inner().width() / (len(self.values) - 1)

    def _row(self, x):
        if self.values is None or len(self.values) < 2:
            return self.start
        i = round((x - self._inner().left()) / self._step())
        return self.start + max(0, min(len(self.values) - 1, i))

    def _depth(self):
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, theme.Layer):
                return parent.depth
            parent = parent.parentWidget()
        return 1

    # -- painting --------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        box = self._box()
        p.setPen(Qt.NoPen)
        p.setBrush(qgray(theme.layer(self._depth()) + theme.MEASURED_LIFT))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        if self.values is None or len(self.values) < 2:
            p.end()
            return
        inner, n, step = self._inner(), len(self.values), self._step()
        width = int(inner.width())
        dense = n - 1 >= width > 1   # more samples than columns: each column is the min..max of its samples
        if dense:
            col = np.arange(n) * (width - 1) // (n - 1)         # nondecreasing, steps of at most one
            starts = np.flatnonzero(np.diff(col, prepend=-1))   # first sample of every column
            xs, w = inner.left() + np.arange(len(starts), dtype=np.float64), 1.0
            gated = None if self.gate is None else np.maximum.reduceat(self.gate[:n].astype(np.uint8), starts) > 0
        else:
            xs, w = inner.left() + step * np.arange(n), step
            gated = None if self.gate is None else self.gate[:n]
        p.setPen(Qt.NoPen)
        if len(self.levels) == 2:
            y_lo, y_hi = self._y(self.levels[0]), self._y(self.levels[1])
            shut = ([(y_lo, inner.bottom()), (inner.top(), y_hi)] if y_lo >= y_hi else [(y_lo, y_hi)])
            p.setBrush(theme.EXCLUDED)
            for y0, y1 in shut:
                p.drawRect(QRectF(inner.left(), y0, inner.width(), y1 - y0))
        if gated is not None and gated.any():
            # one rect per run, so the translucent wash has no seams between rows
            edges = np.flatnonzero(np.diff(np.concatenate(([0], gated.astype(np.int8), [0]))))
            p.setBrush(theme.GATED)
            for a, b in zip(edges[0::2], edges[1::2] - 1):
                x0, x1 = max(xs[a] - w / 2, inner.left()), min(xs[b] + w / 2, inner.right())
                p.drawRect(QRectF(x0, inner.top(), x1 - x0, inner.height()))
        line = theme.GATE if self.levels else theme.SERIES
        if dense:
            lo = np.minimum.reduceat(self.values, starts)
            hi = np.maximum.reduceat(self.values, starts)
            top = [QPointF(x, self._y(v)) for x, v in zip(xs, hi)]
            bottom = [QPointF(x, self._y(v)) for x, v in zip(xs[::-1], lo[::-1])]
            p.setPen(QPen(line, 1))
            p.setBrush(line)
            p.drawPolygon(QPolygonF(top + bottom))
        else:
            p.setPen(QPen(line, 1.6))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(x, self._y(v)) for x, v in zip(xs, self.values)]))
        for v in self.levels:
            # on a pixel's center: a 1px line between two rows antialiases to half strength in each
            y, x0, x1 = round(self._y(v) - 0.5) + 0.5, inner.left() - self.STUB, inner.right() + self.STUB
            p.setPen(QPen(theme.LEVEL, 1))
            p.setBrush(theme.LEVEL)
            p.drawLine(QPointF(x0, y), QPointF(x1, y))
            for x in (x0, x1):
                p.drawEllipse(QPointF(x, y), self.DOT, self.DOT)
            p.setBrush(Qt.NoBrush)
        for row, color, w in ((self.hover, qgray(theme.INK_2), 1.0), (self.playhead, qgray(theme.HEAD), 1.5)):
            i = row - self.start
            if 0 <= i < n:
                p.setPen(QPen(color, w))
                x = inner.left() + step * i
                p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
        i = self.hover - self.start
        if not 0 <= i < n:
            i = self.playhead - self.start
        if 0 <= i < n:
            p.setPen(qgray(theme.INK_2))
            p.drawText(inner.adjusted(0, 2, -6, 0), Qt.AlignRight | Qt.AlignTop, f"{float(self.values[i]):.4g}")
        p.end()

    # -- gestures --------------------------------------------------------
    def _hit(self, pos):
        """The nearest handle within GRAB of the cursor, at any x, else the playhead."""
        if self.values is None or len(self.values) < 2:
            return "head"
        near = [(abs(pos.y() - self._y(v)), i) for i, v in enumerate(self.levels)]
        near = [(d, i) for d, i in near if d <= self.GRAB]
        return min(near)[1] if near else "head"

    def _drag_level(self, i, y):
        inner = self._inner()
        v = max(0.0, self._top() * (inner.bottom() - y) / inner.height())
        self.levels[i] = v
        self.update()
        self.levelDragged.emit(i, v)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.values is None or len(self.values) < 2:
            return
        self._mode = self._hit(e.position())
        if self._mode != "head":
            self._drag_level(self._mode, e.position().y())
        else:
            self.pressed.emit(self._row(e.position().x()))

    def mouseMoveEvent(self, e):
        if self._mode is None:
            self.setCursor(Qt.ArrowCursor if self._hit(e.position()) == "head" else Qt.SizeVerCursor)
            row = self._row(e.position().x())
            if row != self.hover:
                self.hover = row
                self.update()
                self.hovered.emit(row)
        elif self._mode != "head":
            self._drag_level(self._mode, e.position().y())
        else:
            self.dragged.emit(self._row(e.position().x()))

    def mouseReleaseEvent(self, e):
        if self._mode == "head":
            self.released.emit(self._row(e.position().x()))
        self._mode = None

    def leaveEvent(self, _):
        if self.hover != -1:
            self.hover = -1
            self.update()
            self.hovered.emit(-1)


class Density(Trace):
    """A per-row histogram over the window, drawn as a field: each column a row, each pixel-row a value
    bin, lit by log1p(count) over log1p(the column's pixels) in theme.DENSITY, v2's ramp. Feed it with
    set_series(counts, start), counts (T, bins) on sieve_player.density's axis unless `value_of(bin)`
    names another; the readout is the value of the bin under the cursor. The field is cropped to the bins any
    row occupies, plus a margin, so the window fills it. Where there are more rows than columns a
    column is the sum of the histograms it covers: counts add, so nothing is hidden and nothing is
    added. The playhead, cursor and gestures are the Trace's; there are no handles."""
    MARGIN = 2   # bins of room past the occupied ones

    def __init__(self, parent=None, rows=6, value_of=None):
        super().__init__(parent, rows=rows)
        self.value_of = value_of or density.value_of
        self.lo = self.hi = 0   # the bins shown, inclusive
        self._y_hover = None

    def set_series(self, counts, start, gate=None, levels=()):
        self.values = None if counts is None else np.asarray(counts)
        self.start = start
        self.update()

    def _ramp(self):
        base = theme.layer(self._depth()) + theme.MEASURED_LIFT
        stops = ((base, base, base), *theme.DENSITY)
        xs = np.linspace(0, 1, len(stops))
        return np.stack([np.interp(np.linspace(0, 1, 256), xs, [c[k] for c in stops]) for k in range(3)], axis=1).astype(np.uint8)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        box = self._box()
        p.setPen(Qt.NoPen)
        p.setBrush(qgray(theme.layer(self._depth()) + theme.MEASURED_LIFT))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        if self.values is None or len(self.values) < 2:
            p.end()
            return
        inner, n, step = self._inner(), len(self.values), self._step()
        width = int(inner.width())
        dense = n - 1 >= width > 1
        c = self.values
        if dense:
            col = np.arange(n) * (width - 1) // (n - 1)
            starts = np.flatnonzero(np.diff(col, prepend=-1))
            c = np.add.reduceat(c, starts, axis=0)
        c = np.asarray(c, np.float64)
        occupied = np.flatnonzero(c.sum(axis=0))
        bins = c.shape[1]
        if len(occupied):
            self.lo, self.hi = max(0, occupied[0] - self.MARGIN), min(bins - 1, occupied[-1] + self.MARGIN)
        else:
            self.lo, self.hi = 0, bins - 1
        total = np.maximum(c.sum(axis=1, keepdims=True), 1.0)
        lit = np.log1p(c[:, self.lo:self.hi + 1]) / np.log1p(total)                  # (cols, shown bins)
        rgb = self._ramp()[(np.clip(lit, 0, 1) * 255).astype(np.uint8)]                 # (cols, shown bins, 3)
        rgb = np.ascontiguousarray(np.transpose(rgb, (1, 0, 2))[::-1])                  # (bins, cols, 3), top bin first
        h, w = rgb.shape[:2]
        img = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()
        p.save()
        p.setClipRect(inner)
        if dense:
            target = QRectF(inner.left(), inner.top(), float(w), inner.height())
        else:
            target = QRectF(inner.left() - step / 2, inner.top(), step * n, inner.height())
        p.drawImage(target, img)
        p.restore()
        for row, color, lw in ((self.hover, qgray(theme.INK_2), 1.0), (self.playhead, qgray(theme.HEAD), 1.5)):
            i = row - self.start
            if 0 <= i < n:
                p.setPen(QPen(color, lw))
                x = inner.left() + (col[i] if dense else step * i)
                p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
        if self._y_hover is not None:
            frac = (inner.bottom() - self._y_hover) / inner.height()
            b = self.lo + int(np.clip(frac, 0, 1) * (self.hi - self.lo + 1))
            p.setPen(qgray(theme.INK_2))
            p.drawText(inner.adjusted(0, 2, -6, 0), Qt.AlignRight | Qt.AlignTop, f"{self.value_of(min(b, self.hi)):.4g}")
        p.end()

    def mouseMoveEvent(self, e):
        self._y_hover = e.position().y()
        super().mouseMoveEvent(e)
        self.update()

    def leaveEvent(self, e):
        self._y_hover = None
        super().leaveEvent(e)
        self.update()
