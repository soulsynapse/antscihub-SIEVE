"""Optional bases so a tool file stays one screen long: a settings form and a series trace."""
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from . import theme
from .theme import CONTROL_W, GAP, ROW_H, VALUE_W, Form, mono_font, qgray


class ParamWidget(QWidget):
    """Has .changed and .params(). Add rows with add_int / add_float / add_bool; each is one line of
    the form, a knob: slider and its mono readout together fill the one control width."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._get = {}
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(GAP)
        self.form = Form()
        self._lay.addWidget(self.form)

    def params(self):
        return {k: g() for k, g in self._get.items()}

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
        self._get[name] = s.value

    def add_float(self, name, lo, hi, value, decimals=2):
        k = 10 ** decimals
        s = self._slider(name, round(lo * k), round(hi * k), round(value * k), lambda v: f"{v / k:.{decimals}f}")
        self._get[name] = lambda: s.value() / k

    def add_bool(self, name, value):
        c = QCheckBox()
        c.setChecked(bool(value))
        c.toggled.connect(lambda _: self.changed.emit())
        self.form.add_row(name, c)
        self._get[name] = c.isChecked


class Trace(QWidget):
    """A series over the loop window, one layer deeper than the box it sits in: the trace in the
    accent, the playhead in white, and if there is a gate, its level as a dashed amber line with the
    gated rows shaded. Feed it with set_series(values, start, gate=None, level=None) and
    set_playhead(row); `level` is in the units of `values`."""

    def __init__(self, parent=None, rows=3):
        super().__init__(parent)
        self.values, self.gate, self.level = None, None, None
        self.start, self.playhead = 0, 0
        self.setFixedHeight(ROW_H * rows)

    def set_series(self, values, start, gate=None, level=None):
        self.values = None if values is None else np.asarray(values, np.float32)
        self.gate = None if gate is None else np.asarray(gate, bool)
        self.level, self.start = level, start
        self.update()

    def set_playhead(self, row):
        self.playhead = row
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        depth = 2
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, theme.Layer):
                depth = min(theme.MAX_DEPTH, parent.depth + 1)
                break
            parent = parent.parentWidget()
        p.setPen(QPen(qgray(theme.layer(depth) + theme.LINE_LIFT), 1))
        p.setBrush(qgray(theme.layer(depth)))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        if self.values is None or len(self.values) < 2:
            p.end()
            return
        inner = box.adjusted(1, 1, -1, -1)
        n = len(self.values)
        top = max(float(self.values.max()), float(self.level or 0.0), 1e-6)
        step = inner.width() / (n - 1)

        def y(v):
            return inner.bottom() - inner.height() * float(v) / top

        if self.gate is not None:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.AMBER.red(), theme.AMBER.green(), theme.AMBER.blue(), 50))
            for i in np.flatnonzero(self.gate[:n]):
                p.drawRect(QRectF(inner.left() + step * i - step / 2, inner.top(), step, inner.height()))
        if self.level is not None:
            pen = QPen(theme.AMBER, 1)
            pen.setDashPattern([4, 3])
            p.setPen(pen)
            p.drawLine(QPointF(inner.left(), y(self.level)), QPointF(inner.right(), y(self.level)))
        p.setPen(QPen(theme.ACCENT, 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(inner.left() + step * i, y(v)) for i, v in enumerate(self.values)]))
        i = self.playhead - self.start
        if 0 <= i < n:
            p.setPen(QPen(qgray(theme.HEAD), 1.5))
            x = inner.left() + step * i
            p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
        p.end()
