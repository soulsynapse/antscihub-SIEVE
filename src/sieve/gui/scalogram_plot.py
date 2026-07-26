"""The scalogram: pooled Morlet power on a log-frequency axis, band on top.

Three of its rules come straight from the plot contracts (parity plan § 2):

**Per-column max reduction, not averaging.** A working window is hundreds to
thousands of frames wide and the plot a few hundred pixels; letting
`drawImage` average them would dissolve a single-frame event into the noise
floor. Each pixel column takes the *max* over the source columns it covers,
so anything the transform saw survives any width. The reduction is cached per
width and rebuilt only when the data or the width moves.

**The COI is graded, not clipped.** Within an e-folding time of either end of
the record the coefficients are zero-padding artifact, decaying — so the fade
is an alpha ramp over that wedge per row (`core.wavelet.coi_edge_samples`),
not a mask. A reader sees *that* the edge is untrustworthy and *how much*.

**Frequency handles clamp.** The bank has edges; a band outside it would be
silently snapped by `band_indices` anyway, and a handle that can say ``inf``
here would be drawing a value the transform cannot use. The *snapped* band —
the truth the transform uses — is the tab's to render through `set_readout`,
because snapping needs the bank and the detector state, and plots own
neither.
"""

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

#: Warm sequential ramp, dark → light, one family. The scalogram is the only
#: surface that uses it (one ramp per magnitude surface).
SCALO_STOPS: tuple[tuple[int, int, int], ...] = (
    (12, 8, 20),
    (86, 24, 48),
    (168, 60, 44),
    (226, 130, 56),
    (250, 214, 130),
)

#: Alpha the fade bottoms out at, at the record's very edge. Not zero: the
#: wedge is contaminated, not absent.
_COI_FLOOR = 0.15


class ScalogramPlot(BandPlot):
    """Pooled Morlet power over the working window, frequency band handles."""

    title = "scalogram"
    unbounded = False  # the bank has edges; handles clamp to them

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._norm: NDArray[np.float32] | None = None  # (F, T) in [0, 1]
        self._freqs: FloatArray = np.array([0.5, 25.0])
        self._fps = 30.0
        self._image: QImage | None = None
        self._image_width = 0

    # ---- data ---------------------------------------------------------------

    def set_power(self, power: FloatArray, freqs: FloatArray, fps: float) -> None:
        """The pooled `(F, T)` power to show, over `freqs` (row 0 = lowest).

        Normalized in log space here, once — contrast belongs to the whole
        surface, not to whichever columns a resize happens to group.
        """
        self._freqs = np.asarray(freqs, np.float64)
        self._fps = fps
        log_p = np.log10(np.asarray(power, np.float64) + 1e-12)
        lo, hi = float(log_p.min()), float(log_p.max())
        self._norm = ((log_p - lo) / max(hi - lo, 1e-12)).astype(np.float32)
        self._image = None
        self._image_width = 0
        self.update()

    # ---- the value axis -------------------------------------------------

    def _fwd(self, value: float) -> float:
        return math.log10(max(value, 1e-12))

    def _inv(self, t: float) -> float:
        return 10.0**t

    def _range(self) -> tuple[float, float]:
        return float(self._freqs[0]), float(self._freqs[-1])

    def format_value(self, value: float) -> str:
        return f"{value:.2f}"

    # ---- the image --------------------------------------------------------

    def _reduced(self, width: int) -> QImage:
        """The surface at `width` pixel columns: max-reduce, ramp, COI fade."""
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
            for sl, ramp in ((np.s_[:edge], fade), (np.s_[columns - edge :], fade[::-1])):
                cell = argb[row, sl]
                alpha = ((cell >> np.uint32(24)) * ramp).astype(np.uint32)
                argb[row, sl] = (alpha << np.uint32(24)) | (cell & np.uint32(0x00FFFFFF))
        # Row 0 is the lowest frequency; the axis runs upward.
        return argb_to_qimage(argb[::-1])

    # ---- painting ---------------------------------------------------------

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(*SCALO_STOPS[0]))
        if self._norm is None:
            return
        if self._image is None or self._image_width != r.width():
            self._image = self._reduced(r.width())
            self._image_width = r.width()
        painter.drawImage(QRectF(r), self._image)
        painter.setPen(DIM)
        painter.setFont(plot_font(7))
        low, high = self._range()
        for f in (low, math.sqrt(low * high), high):
            painter.drawText(
                QRectF(r.left() - 42.0, self.y_of(f) - 7.0, 38.0, 14.0),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                f"{f:.3g} Hz",
            )
