"""Optional bases so a tool file stays one screen long: a settings form and a series trace."""
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from . import theme
from .theme import CONTROL_W, GAP, ROW_H, VALUE_W, Form, mono_font, qgray


class ParamWidget(QWidget):
    """Has .changed and .params(). Add rows with add_int / add_float / add_bool; each is one line of
    the form, a knob: slider and its mono readout together fill the one control width. The int and
    float rows return their slider, for a tool that also sets the value from elsewhere."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._get, self._set = {}, {}
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
        self._get[name], self._set[name] = c.isChecked, lambda v: c.setChecked(bool(v))


class Trace(QWidget):
    """A series over the loop window, drawn as a measured field on the layer it sits in: the
    series in the accent, the playhead in white, and if there is a gate, its level as a dashed
    amber line and the gated rows as an amber bar along the bottom edge. Where there are more
    samples than pixels each column shows the min and max of the samples it covers, so nothing is
    hidden and nothing is added. Feed it with set_series(values, start, gate=None, level=None) and
    set_playhead(row); `level` is in the units of `values`.

    A press is the playhead (pressed/dragged/released, rows), unless it lands on the level line,
    which then follows the cursor (levelDragged, in the units of `values`). The cursor's row is
    reported as hovered(row), -1 on leave; set_hover(row) draws another widget's cursor here. The
    corner readout is the value under the cursor, else at the playhead."""
    pressed = Signal(int)
    dragged = Signal(int)
    released = Signal(int)
    hovered = Signal(int)
    levelDragged = Signal(float)
    GRAB = 4   # px either side of the level line that takes the drag
    BAR = 3    # px: the gate bar along the bottom edge

    def __init__(self, parent=None, rows=3):
        super().__init__(parent)
        self.values, self.gate, self.level = None, None, None
        self.start, self.playhead, self.hover = 0, 0, -1
        self._mode = None   # "head" | "level"
        self.setFixedHeight(ROW_H * rows)
        self.setMouseTracking(True)
        self.setFont(mono_font())

    def set_series(self, values, start, gate=None, level=None):
        self.values = None if values is None else np.asarray(values, np.float32)
        self.gate = None if gate is None else np.asarray(gate, bool)
        self.level, self.start = level, start
        self.update()

    def set_playhead(self, row):
        self.playhead = row
        self.update()

    def set_hover(self, row):
        self.hover = row
        self.update()

    # -- geometry --------------------------------------------------------
    def _inner(self):
        return QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

    def _top(self):
        return max(float(self.values.max()), float(self.level or 0.0), 1e-6)

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
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(qgray(theme.layer(self._depth()) + theme.MEASURED_LIFT))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        if self.values is None or len(self.values) < 2:
            p.end()
            return
        inner, n, step = self._inner(), len(self.values), self._step()
        width = int(inner.width())
        if n - 1 >= width > 1:
            # more samples than columns: each column is the min..max of the samples in it
            col = np.arange(n) * (width - 1) // (n - 1)         # nondecreasing, steps of at most one
            starts = np.flatnonzero(np.diff(col, prepend=-1))   # first sample of every column
            lo = np.minimum.reduceat(self.values, starts)
            hi = np.maximum.reduceat(self.values, starts)
            xs = inner.left() + np.arange(len(starts), dtype=np.float64)
            top = [QPointF(x, self._y(v)) for x, v in zip(xs, hi)]
            bottom = [QPointF(x, self._y(v)) for x, v in zip(xs[::-1], lo[::-1])]
            p.setPen(QPen(theme.ACCENT, 1))
            p.setBrush(theme.ACCENT)
            p.drawPolygon(QPolygonF(top + bottom))
            gate_x = [] if self.gate is None else xs[np.maximum.reduceat(self.gate[:n].astype(np.uint8), starts) > 0]
            bar_w = 1.0
        else:
            p.setPen(QPen(theme.ACCENT, 1.4))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(inner.left() + step * i, self._y(v)) for i, v in enumerate(self.values)]))
            gate_x = [] if self.gate is None else inner.left() + step * np.flatnonzero(self.gate[:n])
            bar_w = step
        if len(gate_x):
            p.setPen(Qt.NoPen)
            p.setBrush(theme.AMBER)
            for x in gate_x:
                p.drawRect(QRectF(x - bar_w / 2, inner.bottom() - self.BAR, bar_w, self.BAR))
        if self.level is not None:
            pen = QPen(theme.AMBER, 1)
            pen.setDashPattern([4, 3])
            p.setPen(pen)
            p.drawLine(QPointF(inner.left(), self._y(self.level)), QPointF(inner.right(), self._y(self.level)))
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
        if self.values is not None and len(self.values) >= 2 and self.level is not None \
                and abs(pos.y() - self._y(self.level)) <= self.GRAB:
            return "level"
        return "head"

    def _drag_level(self, y):
        inner = self._inner()
        v = max(0.0, self._top() * (inner.bottom() - y) / inner.height())
        self.level = v
        self.update()
        self.levelDragged.emit(v)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.values is None or len(self.values) < 2:
            return
        self._mode = self._hit(e.position())
        if self._mode == "level":
            self._drag_level(e.position().y())
        else:
            self.pressed.emit(self._row(e.position().x()))

    def mouseMoveEvent(self, e):
        if self._mode is None:
            self.setCursor(Qt.SizeVerCursor if self._hit(e.position()) == "level" else Qt.ArrowCursor)
            row = self._row(e.position().x())
            if row != self.hover:
                self.hover = row
                self.update()
                self.hovered.emit(row)
        elif self._mode == "level":
            self._drag_level(e.position().y())
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
