"""Band power by block: the population the count comes from, as a density.

**A histogram, not a mean line** (parity plan § 2). The detector counts
blocks whose band-power value sits inside the value band, so the graph the
user tunes that band against must show the whole population per frame — a
mean line would hide exactly the spread the count is made of. Each pixel
column is the distribution of all blocks' values at that frame, on a log1p
value axis (the noise floor and the bursts differ by orders of magnitude and
both must be placeable).

**Solo answers the opposite question.** The trace overlaid on the density is
one block's series — "what is *this* block doing" — and which block that is
belongs to the state model, not to this widget: the tab passes the already
selected column through `set_series`, so there is nothing here to go stale
when solo changes hands.

The value band handles are the base's: dragging past the top reads as
unbounded (``inf``), which for a band that *shapes a signal* is the correct
default resting state.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.gui.band_plot import ACCENT, BandPlot, argb_to_qimage, ramp_lut

FloatArray = NDArray[np.floating[Any]]

#: Cyan sequential ramp — the density's own surface, distinct from the
#: scalogram's warm one so the two heatmaps never read as one scale.
DENSITY_STOPS: tuple[tuple[int, int, int], ...] = (
    (21, 22, 25),
    (24, 56, 74),
    (32, 110, 138),
    (70, 180, 200),
    (190, 240, 248),
)

#: Vertical resolution of the histogram, in value bins.
_BINS = 96


class DensityPlot(BandPlot):
    """Per-frame value histogram over all blocks, with the value band on top."""

    title = "band power by block"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self._max = 1.0
        self._solo: NDArray[np.float32] | None = None

    # ---- data ---------------------------------------------------------------

    def set_series(self, band_power: FloatArray, solo: FloatArray | None = None) -> None:
        """The `(T, B)` band power to bin, and one block's `(T,)` trace or None.

        The histogram image is rebuilt here, inside the cheap tier — binning
        `(T, B)` into `(bins, T)` is one `np.add.at`, which is what makes a
        frequency-band drag repaint this surface live.
        """
        m = np.asarray(band_power, np.float32)
        frames, blocks = m.shape
        self._max = float(m.max()) or 1.0
        top = math.log1p(self._max)
        idx: NDArray[np.int32] = np.minimum(
            (np.log1p(m) / top * (_BINS - 1)).astype(np.int32), np.int32(_BINS - 1)
        )
        counts = np.zeros((_BINS, frames), np.float32)
        cols: NDArray[np.intp] = np.repeat(np.arange(frames, dtype=np.intp), blocks)
        np.add.at(counts, (idx.ravel(), cols), 1.0)
        norm = np.log1p(counts) / math.log1p(max(blocks, 2))
        lut = ramp_lut(DENSITY_STOPS)
        self._image = argb_to_qimage(lut[(norm * 255).astype(np.uint8)][::-1])
        self._solo = None if solo is None else np.asarray(solo, np.float32)
        self.update()

    # ---- the value axis -------------------------------------------------

    def _fwd(self, value: float) -> float:
        return math.log1p(max(value, 0.0))

    def _inv(self, t: float) -> float:
        return math.expm1(t)

    def _range(self) -> tuple[float, float]:
        return 0.0, self._max

    # ---- painting ---------------------------------------------------------

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(*DENSITY_STOPS[0]))
        if self._image is not None:
            painter.drawImage(QRectF(r), self._image)
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
