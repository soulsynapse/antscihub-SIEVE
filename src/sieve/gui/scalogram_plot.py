from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from sieve.core.wavelet import coi_edge_samples
from sieve.gui.band_plot import DIM, BandPlot, argb_to_qimage, plot_font, ramp_lut

FloatArray = NDArray[np.floating[Any]]


SCALO_STOPS: tuple[tuple[int, int, int], ...] = (
    (12, 8, 20),
    (86, 24, 48),
    (168, 60, 44),
    (226, 130, 56),
    (250, 214, 130),
)


_COI_FLOOR = 0.15


class ScalogramPlot(BandPlot):
    title = "scalogram"
    unbounded = False

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._norm: NDArray[np.float32] | None = None
        self._freqs: FloatArray = np.array([0.5, 25.0])
        self._fps = 30.0
        self._image: QImage | None = None
        self._image_width = 0

    def set_power(self, power: FloatArray, freqs: FloatArray, fps: float) -> None:
        self._freqs = np.asarray(freqs, np.float64)
        self._fps = fps
        log_p = np.log10(np.asarray(power, np.float64) + 1e-12)
        lo, hi = float(log_p.min()), float(log_p.max())
        self._norm = ((log_p - lo) / max(hi - lo, 1e-12)).astype(np.float32)
        self._image = None
        self._image_width = 0
        self.update()

    def _fwd(self, value: float) -> float:
        return math.log10(max(value, 1e-12))

    def _inv(self, t: float) -> float:
        return 10.0**t

    def _range(self) -> tuple[float, float]:
        return float(self._freqs[0]), float(self._freqs[-1])

    def format_value(self, value: float) -> str:
        return f"{value:.2f}"

    def _reduced(self, width: int) -> QImage:
        assert self._norm is not None
        frames = self._norm.shape[1]
        if frames > width > 0:
            edges = (np.arange(width, dtype=np.int64) * frames) // width
            reduced = np.maximum.reduceat(self._norm, edges, axis=1)
            columns = width
        else:
            reduced = self._norm
            columns = frames
        lut = ramp_lut(SCALO_STOPS)
        argb = lut[(reduced * 255).astype(np.uint8)]
        coi = coi_edge_samples(self._freqs, self._fps) * (columns / max(frames, 1))
        for row in range(argb.shape[0]):
            edge = int(min(coi[row], columns))
            if edge <= 1:
                continue
            fade = np.linspace(_COI_FLOOR, 1.0, edge)
            for sl, ramp in (
                (np.s_[:edge], fade),
                (np.s_[columns - edge :], fade[::-1]),
            ):
                cell = argb[row, sl]
                alpha = ((cell >> np.uint32(24)) * ramp).astype(np.uint32)
                argb[row, sl] = (alpha << np.uint32(24)) | (
                    cell & np.uint32(0x00FFFFFF)
                )
        return argb_to_qimage(argb[::-1])

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(*SCALO_STOPS[0]))
        if self._norm is None:
            return
        target = self.content_rect()
        if target.width() <= 0:
            return
        if self._image is None or self._image_width != target.width():
            self._image = self._reduced(target.width())
            self._image_width = target.width()
        painter.drawImage(QRectF(target), self._image)
        painter.setPen(DIM)
        painter.setFont(plot_font(7))
        low, high = self._range()
        for f in (low, math.sqrt(low * high), high):
            painter.drawText(
                QRectF(r.left() - 42.0, self.y_of(f) - 7.0, 38.0, 14.0),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                f"{f:.3g} Hz",
            )
