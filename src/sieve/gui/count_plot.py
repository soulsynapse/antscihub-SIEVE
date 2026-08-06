"""Elements in band, windowed over D: the graph where detection becomes visible.

This is the only plot that paints green, and only when the detector is armed
— green is a status color, never a data series (parity plan § 2). The gate
underpaint comes from the base (`set_gate`), spans floored to 1 px so a
single-frame detection survives any zoom.

**The threshold handle speaks counts; the state stores a fraction.** Drags
emit count values and the tab divides by B on the way into
`DetectorState.count_frac` — `core.ops.detection.count_band_to_counts` is the one
conversion back. The widget never learns the fraction, which is the point:
re-denomination on a block-size change is the state's problem, not a
repaint's (the v1 foot-gun this design deletes).

**The axis is the data, not the region.** A count of 30 elements out of 4096 on
a 0..B axis is a line on the bottom pixel row with no handle travel above it,
so the top comes from the tallest thing actually on the plot: the series peak,
or a band edge above it. Unioning in the band is what keeps a threshold placed
against a loud stretch reachable after a scrub to a quiet one — a handle that
fell off the top of its own axis could only be recovered by scrubbing back.
B survives as the ceiling, because a count above it is not a number this plot
can honestly show. Nothing is latched: the axis is the current window's, which
is v1's one deliberate exception to its sticky axes and for v1's reason —
accumulating pins the scale to the loudest burst the whole run ever saw.

**And the axis says which ceiling it is on.** A moving axis with no reading is
a shape whose height means nothing across two tunings, so the title row
carries `scale_label()` — the ceiling in force and the region's block count,
both always, plus `· full` when they meet. That line is derived at paint time
rather than pushed in (`readout_text`), because an axis this plot computes
inside `_range` is one nobody outside it can keep a label in step with.

**A drag freezes the axis.** Both ends are otherwise live at once — the range
widens to hold the band, the band follows the mouse through the range — and
the handle would chase its own rescale. The gesture finishes in the axis it
started in and the plot re-derives on release; that is the same rule
`set_band` follows mid-drag, applied to the frame rather than the value.

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
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.core.filter_base import ElementNames
from sieve.gui.band_plot import DETECT, DIM, BandPlot, plot_font

FloatArray = NDArray[np.floating[Any]]

#: How much taller than the tallest thing on it the axis runs. A peak drawn on
#: the frame reads as clipped — as a value that left the plot rather than as
#: the maximum — and the line has width, so the top pixel row is not free.
_HEADROOM = 1.06


class CountPlot(BandPlot):
    """Windowed element count in band, gate spans, one draggable threshold."""

    title = "elements in band"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._windowed: NDArray[np.float32] | None = None
        self._armed = False
        self._elements = 1
        self._element_names = ElementNames("element", "elements")
        self._notice = ""
        # The series peak, kept rather than recomputed: `_range` is called once
        # per point per repaint (`y_of`), so a scan there would be quadratic in
        # the series length.
        self._peak = 0.0
        # The axis a handle drag started in, held for its duration.
        self._frozen: tuple[float, float] | None = None

    # ---- data ---------------------------------------------------------------

    def set_series(
        self,
        windowed: FloatArray,
        *,
        region_elements: int,
        element_names: ElementNames,
        armed: bool,
    ) -> None:
        """The `(T,)` windowed count over a region of `region_elements`.

        `armed` decides the line's color, not its presence — a disarmed
        detector still shows the signal it would count, in a data color.
        """
        self._windowed = np.asarray(windowed, np.float32)
        finite = self._windowed[np.isfinite(self._windowed)]
        self._peak = float(finite.max()) if finite.size > 0 else 0.0
        self._elements = max(region_elements, 1)
        self._element_names = element_names
        self.title = f"{element_names.plural} in band"
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
        """0 up to the tallest thing on the plot, capped at the region's elements.

        Zero is the floor rather than the series minimum: with no tick labels
        the bottom of the frame is read as none, and a floor of 20 would draw
        twenty elements in band as nothing at all (rule 6).
        """
        if self._frozen is not None:
            return self._frozen
        top = self._peak
        if self._band is not None:
            for edge in self._band:
                if math.isfinite(edge):
                    top = max(top, edge)
        top = min(top * _HEADROOM, float(self._elements))
        return 0.0, top if top > 0.0 else min(1.0, float(self._elements))

    def scale_label(self) -> str:
        """The ceiling in force and the region it is a fraction of.

        Both numbers, always, because the regime is the thing a reader has to
        be able to tell apart: "0-7 of 512 blocks" and "0-512 of 512 blocks ·
        full" are the same sentence with different numbers, and neither can be
        mistaken for the other at a glance. A plot that autoscaled silently
        would make two tunings whose counts differ by two orders of magnitude
        draw identically — a result looking better-founded than it is (rule 6),
        which is the cost the fixed 0..B axis was paying to avoid.
        """
        top = self._range()[1]
        full = " · full" if top >= float(self._elements) else ""
        return f"0-{top:.0f} of {self._elements} {self._element_names.plural}{full}"

    def readout_text(self) -> str:
        """The scale label is this plot's truth line, derived rather than told."""
        return self.scale_label()

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.0f}"

    # ---- the gesture ------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Grab as the base does, then hold the axis still for the gesture."""
        super().mousePressEvent(event)
        if self._drag in ("lo", "hi"):
            self._frozen = self._range()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Release as the base does, then let the axis re-derive.

        Guarded on the base having ended the drag: a second button coming up
        mid-gesture is not the end of it, and unfreezing there would rescale
        under a handle still being held.
        """
        super().mouseReleaseEvent(event)
        if self._drag is None and self._frozen is not None:
            self._frozen = None
            self.update()

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
