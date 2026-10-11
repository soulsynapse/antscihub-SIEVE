"""Series tool: mean |frame-to-frame difference| over the loop window, gated by a threshold."""
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve_player import ParamWidget

NAME, KIND, EXPECTS = "motion", "series", "gray"
DEFAULTS = {"gate": 2.0}

_cache = {}  # series.key -> activity computed so far; the stack only grows under one key


def run(series, params):
    d = series.data
    prev = _cache.get(series.key)
    n0 = min(len(prev), len(d)) if prev is not None else 0
    act = np.empty(len(d), np.float32)
    act[:n0] = prev[:n0] if n0 else act[:0]
    if n0 == 0 and len(d):
        act[0], n0 = 0.0, 1
    for i in range(n0, len(d)):
        act[i] = cv2.absdiff(d[i], d[i - 1]).mean()
    _cache.clear()
    _cache[series.key] = act
    return {"activity": act, "gate": act > params["gate"]}


class _Plot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.act, self.gate, self.start, self.playhead = None, None, 0, 0
        self.setMinimumHeight(120)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 30, 30))
        if self.act is None or not len(self.act):
            return
        n, w, h = len(self.act), self.width(), self.height()
        top = max(float(self.act.max()), 1e-6)
        xs = np.arange(n) * (w / n)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(120, 40, 40))
        for i in np.flatnonzero(self.gate):
            p.drawRect(int(xs[i]), 0, max(1, int(w / n) + 1), h)
        p.setPen(QPen(QColor(120, 200, 120), 1))
        pts = [(int(xs[i]), int(h - 1 - self.act[i] / top * (h - 2))) for i in range(n)]
        for a, b in zip(pts, pts[1:]):
            p.drawLine(*a, *b)
        i = self.playhead - self.start
        if 0 <= i < n:
            p.setPen(QPen(QColor(255, 200, 60), 2))
            p.drawLine(int(xs[i]), 0, int(xs[i]), h)


class _Widget(ParamWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_float("gate", 0.0, 30.0, DEFAULTS["gate"])
        self.plot = _Plot()
        self.layout().addWidget(self.plot)

    def show_result(self, result, start, fps):
        self.plot.act, self.plot.gate, self.plot.start = result["activity"], result["gate"], start
        self.plot.update()

    def set_playhead(self, row):
        self.plot.playhead = row
        self.plot.update()


def settings(parent=None):
    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
