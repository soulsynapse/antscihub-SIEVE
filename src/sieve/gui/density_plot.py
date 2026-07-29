

































from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.gui.band_plot import ACCENT, BandPlot, argb_to_qimage, ramp_lut

FloatArray = NDArray[np.floating[Any]]



DENSITY_STOPS: tuple[tuple[int, int, int], ...] = (
    (21, 22, 25),
    (24, 56, 74),
    (32, 110, 138),
    (70, 180, 200),
    (190, 240, 248),
)


_BINS = 96


def bin_counts(band_power: FloatArray, value_max: float, bins: int = _BINS) -> NDArray[np.float32]:































    m = np.asarray(band_power, np.float32)
    frames = m.shape[0]
    top = math.log1p(max(value_max, 0.0)) or 1.0
    with np.errstate(invalid="ignore"):


        idx = np.clip((np.log1p(m) / top * (bins - 1)).astype(np.int32), 0, bins - 1)
    counts = np.zeros((bins, frames), np.float32)
    for t in range(frames):
        counts[:, t] = np.bincount(idx[t], minlength=bins)
    return counts


@dataclass(frozen=True, slots=True)
class DensitySurface:









    value_max: float


    argb: NDArray[np.uint32]



    blocks: int


def density_surface(band_power: FloatArray) -> DensitySurface:













    m = np.asarray(band_power, np.float32)
    blocks = m.shape[1]
    value_max = float(m.max()) or 1.0
    counts = bin_counts(m, value_max)
    norm = np.log1p(counts) / math.log1p(max(blocks, 2))
    lut = ramp_lut(DENSITY_STOPS)
    return DensitySurface(
        value_max=value_max, argb=lut[(norm * 255).astype(np.uint8)][::-1], blocks=blocks
    )


class DensityPlot(BandPlot):


    title = "band power by block"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self._max = 1.0
        self._solo: NDArray[np.float32] | None = None


        self._source: FloatArray | None = None



    def set_series(
        self,
        band_power: FloatArray,
        solo: FloatArray | None = None,
        *,
        surface: DensitySurface | None = None,
    ) -> None:





























        m = np.asarray(band_power, np.float32)
        if m is not self._source:
            self._source = m




            built = density_surface(m) if surface is None else surface
            self._max = built.value_max
            self._image = argb_to_qimage(built.argb)
        self._solo = None if solo is None else np.asarray(solo, np.float32)
        self.update()



    def _fwd(self, value: float) -> float:
        return math.log1p(max(value, 0.0))

    def _inv(self, t: float) -> float:
        return math.expm1(t)

    def _range(self) -> tuple[float, float]:
        return 0.0, self._max



    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(*DENSITY_STOPS[0]))
        target = self.content_rect()
        if self._image is not None and target.width() > 0:
            painter.drawImage(QRectF(target), self._image)
        if self._solo is None or self._count <= 0:
            return
        painter.setPen(QPen(ACCENT, 1.4))
        frames = len(self._solo)
        step = max(1, frames // max(r.width(), 1))
        points = [
            QPointF(self.x_of(self._start + t), self.y_of(float(self._solo[t])))
            for t in range(0, frames, step)
        ]
        for a, b in pairwise(points):
            painter.drawLine(a, b)
