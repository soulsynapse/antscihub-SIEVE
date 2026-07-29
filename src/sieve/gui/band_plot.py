from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

FloatArray = NDArray[np.floating[Any]]


GRAB_PX = 8.0


_EDGE_PX = 4.0

_MARGIN_L = 48
_MARGIN_R = 66
_MARGIN_T = 24
_MARGIN_B = 8


PANEL = QColor(31, 33, 38)
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)

ACCENT = QColor(94, 200, 180)

BAND = QColor(240, 110, 100)

DETECT = QColor(96, 210, 120)


def plot_font(size: int, *, bold: bool = False, spaced: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    if spaced:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    return font


def ramp_lut(stops: tuple[tuple[int, int, int], ...]) -> NDArray[np.uint32]:
    positions = np.linspace(0.0, 1.0, len(stops))
    t = np.linspace(0.0, 1.0, 256)
    channels: list[NDArray[np.float64]] = [
        np.interp(t, positions, [float(s[k]) for s in stops]) for k in range(3)
    ]
    r, g, b = (c.astype(np.uint32) for c in channels)
    return (
        (np.uint32(255) << np.uint32(24))
        | (r << np.uint32(16))
        | (g << np.uint32(8))
        | b
    )


def argb_to_qimage(argb: NDArray[np.uint32]) -> QImage:
    height, width = argb.shape
    data = np.ascontiguousarray(argb, dtype=np.uint32)
    return QImage(
        data.tobytes(), width, height, width * 4, QImage.Format.Format_ARGB32
    ).copy()


class BandPlot(QWidget):
    band_changed = Signal(float, float)

    band_committed = Signal(float, float)

    pressed = Signal(int)

    scrubbed = Signal(int)

    committed = Signal(int)

    title = ""

    unbounded = True

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._start = 0
        self._count = 0
        self._filled: int | None = None
        self._settled: int | None = None
        self._playhead = 0
        self._band: tuple[float, float] | None = None
        self._gate: NDArray[np.bool_] | None = None
        self._readout = ""
        self._drag: str | None = None
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_span(self, start: int, count: int) -> None:
        self._start = start
        self._count = max(count, 0)
        self.update()

    def set_filled(self, filled: int | None, settled: int | None = None) -> None:
        self._filled = None if filled is None else max(filled, 0)
        self._settled = None if settled is None else max(settled, 0)
        self.update()

    @property
    def filled_frames(self) -> int:
        return self._count if self._filled is None else min(self._filled, self._count)

    @property
    def settled_frames(self) -> int:
        filled = self.filled_frames
        return filled if self._settled is None else min(self._settled, filled)

    def set_playhead(self, frame: int) -> None:
        self._playhead = frame
        self.update()

    def set_band(self, lo: float, hi: float) -> None:
        if self._drag == "lo" and self._band is not None:
            self._band = (self._band[0], hi)
        elif self._drag == "hi" and self._band is not None:
            self._band = (lo, self._band[1])
        else:
            self._band = (lo, hi)
        self.update()

    def clear_band(self) -> None:
        if self._drag is None:
            self._band = None
            self.update()

    def set_gate(self, gate: NDArray[np.bool_] | None) -> None:
        self._gate = gate
        self.update()

    def set_readout(self, text: str) -> None:
        self._readout = text
        self.update()

    def readout_text(self) -> str:
        return self._readout

    def _fwd(self, value: float) -> float:
        return value

    def _inv(self, t: float) -> float:
        return t

    def _range(self) -> tuple[float, float]:
        return 0.0, 1.0

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.3g}"

    def plot_rect(self) -> QRect:
        return self.rect().adjusted(_MARGIN_L, _MARGIN_T, -_MARGIN_R, -_MARGIN_B)

    def x_of(self, frame: int) -> float:
        r = self.plot_rect()
        span = max(self._count - 1, 1)
        return r.left() + (frame - self._start) / span * r.width()

    def content_rect(self) -> QRect:
        r = self.plot_rect()
        filled = self.filled_frames
        if self._count <= 0 or filled >= self._count:
            return r
        if filled <= 0:
            return QRect(r.left(), r.top(), 0, r.height())
        right = self.x_of(self._start + filled - 1)
        return QRect(r.left(), r.top(), max(round(right - r.left()), 1), r.height())

    def frame_of(self, x: float) -> int:
        r = self.plot_rect()
        t = (x - r.left()) / max(r.width(), 1)
        offset = round(t * max(self._count - 1, 0))
        return self._start + min(max(offset, 0), max(self._count - 1, 0))

    def y_of(self, value: float) -> float:
        lo, hi = self._range()
        r = self.plot_rect()
        value = min(max(value, lo), hi)
        t = (self._fwd(value) - self._fwd(lo)) / max(
            self._fwd(hi) - self._fwd(lo), 1e-12
        )
        return r.bottom() - t * r.height()

    def value_of(self, y: float) -> float:
        lo, hi = self._range()
        r = self.plot_rect()
        t = (r.bottom() - y) / max(r.height(), 1)
        t = min(max(t, 0.0), 1.0)
        return self._inv(self._fwd(lo) + t * (self._fwd(hi) - self._fwd(lo)))

    def handle_y(self, which: str) -> float:
        lo, hi = self._range()
        if self._band is None:
            value = lo if which == "lo" else hi
        else:
            value = self._band[0] if which == "lo" else self._band[1]
        return self.y_of(min(max(value, lo), hi))

    def gate_rects(self) -> list[QRectF]:
        if self._gate is None or self._count <= 0:
            return []
        r = self.plot_rect()
        edges = np.flatnonzero(np.diff(np.r_[0, self._gate.view(np.int8), 0]))
        rects: list[QRectF] = []
        for lo_idx, hi_idx in zip(edges[::2], edges[1::2], strict=True):
            x0 = self.x_of(self._start + int(lo_idx))
            x1 = self.x_of(self._start + int(hi_idx))
            rects.append(QRectF(x0, r.top(), max(x1 - x0, 1.0), r.height()))
        return rects

    def _grabbable(self, pos: QPointF) -> str | None:
        r = self.plot_rect()
        zone = QRectF(r).adjusted(0.0, -GRAB_PX, float(_MARGIN_R), GRAB_PX)
        if not zone.contains(pos):
            return None
        near = min(("lo", "hi"), key=lambda w: abs(self.handle_y(w) - pos.y()))
        if abs(self.handle_y(near) - pos.y()) <= GRAB_PX:
            return near
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._count <= 0 or event.button() is not Qt.MouseButton.LeftButton:
            return
        handle = self._grabbable(event.position())
        if handle is not None:
            self._drag = handle
            return
        self._drag = "scrub"
        self.pressed.emit(self.frame_of(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag in ("lo", "hi"):
            self._drag_handle(event.position().y())
        elif self._drag == "scrub":
            self.scrubbed.emit(self.frame_of(event.position().x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        if self._drag in ("lo", "hi") and self._band is not None:
            self.band_committed.emit(self._band[0], self._band[1])
        elif self._drag == "scrub":
            self.committed.emit(self.frame_of(event.position().x()))
        self._drag = None

    def _drag_handle(self, y: float) -> None:
        r = self.plot_rect()
        lo, hi = self._band if self._band is not None else (-math.inf, math.inf)
        if self.unbounded and y < r.top() - _EDGE_PX:
            value = math.inf
        elif self.unbounded and y > r.bottom() + _EDGE_PX:
            value = -math.inf
        else:
            value = self.value_of(y)
        if self._drag == "lo":
            lo = value
            if lo > hi:
                lo, hi = hi, lo
                self._drag = "hi"
        else:
            hi = value
            if hi < lo:
                lo, hi = hi, lo
                self._drag = "lo"
        self._band = (lo, hi)
        self.band_changed.emit(lo, hi)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), PANEL)
        r = self.plot_rect()
        painter.setPen(DIM)
        painter.setFont(plot_font(8, bold=True, spaced=True))
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, self.title.upper())
        readout = self.readout_text()
        if readout:
            painter.drawText(
                QRect(10, 4, self.width() - 20, 14),
                int(Qt.AlignmentFlag.AlignRight),
                readout,
            )
        grid = QColor(LINE)
        grid.setAlpha(90)
        painter.setPen(QPen(grid, 1.0))
        for k in range(1, 4):
            y = r.top() + k * r.height() / 4
            painter.drawLine(QPointF(float(r.left()), y), QPointF(float(r.right()), y))
        painter.save()
        painter.setClipRect(r)
        fill = QColor(DETECT)
        fill.setAlpha(52)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        for span in self.gate_rects():
            painter.drawRect(span)
        self.paint_content(painter, r)
        painter.restore()
        if self._count > 0:
            x = self.x_of(self._playhead)
            head = QColor(TEXT)
            head.setAlpha(130)
            painter.setPen(QPen(head, 1.0))
            painter.drawLine(QPointF(x, float(r.top())), QPointF(x, float(r.bottom())))
        self._paint_handles(painter, r)
        painter.end()

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        pass

    def _paint_handles(self, painter: QPainter, r: QRect) -> None:
        band = self._band
        for which in ("lo", "hi"):
            y = self.handle_y(which)
            color = QColor(BAND)
            value = None if band is None else (band[0] if which == "lo" else band[1])
            if value is None or math.isinf(value):
                color.setAlpha(110)
            painter.setPen(QPen(color, 1.0))
            painter.drawLine(QPointF(float(r.left()), y), QPointF(r.right() + 22.0, y))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(r.right() + 22.0, y), 3.2, 3.2)
            painter.setPen(QPen(color, 1.0))
            painter.setFont(plot_font(8))
            painter.drawText(
                QRectF(r.right() + 28.0, y - 8.0, _MARGIN_R - 30.0, 16.0),
                int(Qt.AlignmentFlag.AlignVCenter),
                "—" if value is None else self.format_value(value),
            )
