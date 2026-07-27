"""Blocks in band, windowed over D: the graph where detection becomes visible.

This is the only plot that paints green, and only when the detector is armed
— green is a status color, never a data series (parity plan § 2). The gate
underpaint comes from the base (`set_gate`), spans floored to 1 px so a
single-frame detection survives any zoom.

**The threshold handle speaks counts; the state stores a fraction.** The axis
runs 0..B for the region's B blocks, drags emit count values, and the tab
divides by B on the way into `DetectorState.count_frac` —
`core.detection.count_band_to_counts` is the one conversion back. The widget
never learns the fraction, which is the point: re-denomination on a block-size
change is the state's problem, not a repaint's (the v1 foot-gun this design
deletes).

**Unset is disarmed, and the plot says so.** With no band placed the line
draws in the dim data color, nothing is green, and the notice line explains —
same for a chain whose detection step is unreachable, where the tab passes
the reason through `set_notice` ("no reachable detection step"). A plot that
went visually quiet without saying why would read as "no events", which is an
armed claim this state is not making.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.gui.band_plot import DETECT, DIM, BandPlot, plot_font

FloatArray = NDArray[np.floating[Any]]


class CountPlot(BandPlot):
    """Windowed # blocks in band, gate spans, one draggable count threshold."""

    title = "blocks in band"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._windowed: NDArray[np.float32] | None = None
        self._armed = False
        self._blocks = 1
        self._notice = ""

    # ---- data ---------------------------------------------------------------

    def set_series(self, windowed: FloatArray, *, region_blocks: int, armed: bool) -> None:
        """The `(T,)` windowed count over a region of `region_blocks` blocks.

        `armed` decides the line's color, not its presence — a disarmed
        detector still shows the signal it would count, in a data color.
        """
        self._windowed = np.asarray(windowed, np.float32)
        self._blocks = max(region_blocks, 1)
        self._armed = armed
        self.update()

    @property
    def notice(self) -> str:
        """The current explanation line, empty when there is nothing to explain."""
        return self._notice

    def set_notice(self, text: str) -> None:
        """Why there is nothing green — disarmed, or no reachable detection step.

        Empty string clears it. The notice draws inside the plot, because the
        absence it explains is inside the plot.
        """
        self._notice = text
        self.update()

    # ---- the value axis -------------------------------------------------

    def _range(self) -> tuple[float, float]:
        return 0.0, float(self._blocks)

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.0f}"

    # ---- painting ---------------------------------------------------------

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
            # Past the settled frontier the value is still moving: it is inside
            # the transform's cone of influence at the record's cut and will be
            # redrawn when the next frames land. Faded rather than withheld —
            # the shape is real and worth watching arrive, and the fade is the
            # same claim the scalogram's COI ramp makes on the same frames.
            # The gate underpaint the base draws stops at the frontier instead,
            # because a detection is navigation and must not blink in and out.
            provisional = QColor(base)
            provisional.setAlpha(70)
            for (a, b), t in zip(pairwise(points), indices[1:], strict=True):
                painter.setPen(QPen(base if t < settled else provisional, 1.6))
                painter.drawLine(a, b)
        if self._notice:
            painter.setPen(DIM)
            painter.setFont(plot_font(8))
            painter.drawText(r, int(Qt.AlignmentFlag.AlignCenter), self._notice)
