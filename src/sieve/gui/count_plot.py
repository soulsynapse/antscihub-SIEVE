from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.gui.band_plot import DETECT, DIM, BandPlot, plot_font

FloatArray = NDArray[np.floating[Any]]


_HEADROOM = 1.06


class CountPlot(BandPlot):
    title = "blocks in band"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._windowed: NDArray[np.float32] | None = None
        self._armed = False
        self._blocks = 1
        self._notice = ""
        self._peak = 0.0
        self._frozen: tuple[float, float] | None = None

    def set_series(
        self, windowed: FloatArray, *, region_blocks: int, armed: bool
    ) -> None:
        self._windowed = np.asarray(windowed, np.float32)
        finite = self._windowed[np.isfinite(self._windowed)]
        self._peak = float(finite.max()) if finite.size > 0 else 0.0
        self._blocks = max(region_blocks, 1)
        self._armed = armed
        self.update()

    @property
    def notice(self) -> str:
        return self._notice

    def set_notice(self, text: str) -> None:
        self._notice = text
        self.update()

    def _range(self) -> tuple[float, float]:
        if self._frozen is not None:
            return self._frozen
        top = self._peak
        if self._band is not None:
            for edge in self._band:
                if math.isfinite(edge):
                    top = max(top, edge)
        top = min(top * _HEADROOM, float(self._blocks))
        return 0.0, top if top > 0.0 else min(1.0, float(self._blocks))

    def scale_label(self) -> str:
        top = self._range()[1]
        full = " · full" if top >= float(self._blocks) else ""
        return f"0-{top:.0f} of {self._blocks} blocks{full}"

    def readout_text(self) -> str:
        return self.scale_label()

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.0f}"

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if self._drag in ("lo", "hi"):
            self._frozen = self._range()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if self._drag is None and self._frozen is not None:
            self._frozen = None
            self.update()

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        if self._windowed is not None and self._count > 0:
            base = QColor(DETECT if self._armed else DIM)
            frames = len(self._windowed)
            step = max(1, frames // max(r.width(), 1))
            settled = self.settled_frames
            indices = list(range(0, frames, step))
            points = [
                QPointF(self.x_of(self._start + t), self.y_of(float(self._windowed[t])))
                for t in indices
            ]
            provisional = QColor(base)
            provisional.setAlpha(70)
            for (a, b), t in zip(pairwise(points), indices[1:], strict=True):
                painter.setPen(QPen(base if t < settled else provisional, 1.6))
                painter.drawLine(a, b)
        if self._notice:
            painter.setPen(DIM)
            painter.setFont(plot_font(8))
            painter.drawText(r, int(Qt.AlignmentFlag.AlignCenter), self._notice)
