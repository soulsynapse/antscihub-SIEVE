"""The graph: one refill's series, drawn where its frames are.

The first consumer of `pipeline/series_collector.py` that is not a benchmark.
Assembly stays below `gui` — the collector runs in the pipeline layer and hands
over a whole `CollectedSeries`; this panel places it and paints it, and holds it
only so a resize has something to redraw.

**The horizontal axis is the series', not the asset's.** A refill covers the
rendered window, `start_index` says which frames those are, and that is all the
panel is handed — so a graph aligned to the whole asset would be a claim about
frames nobody rendered. The scrubber is where the asset-wide axis lives
(`timeline/bar.py`), and the two meeting is a binding neither owns alone.

**Zero is the floor of the value axis.** There are no tick labels, so the bottom
of the frame reads as none, and a floor at the series minimum would draw a
stretch of small values identically to a stretch of large ones. v2's count plot
took the same decision for the same reason. The top is the peak plus headroom,
because a peak drawn on the frame reads as cut off — as a value that left the
plot rather than as the maximum.

**One value per frame, or nothing.** A node emitting a whole image per frame has
no trace until something reduces it, and a reduction here would be a computation
in `gui` and an invisible one: whatever this module picked would draw as a
plausible line for a quantity the document never named. The refusal is at
`set_series`, where the series arrives, rather than at paint.

**A non-finite value breaks the trace rather than joining across it.** `detect`
emits NaN for a frame its gate cannot answer for, and a segment drawn through
that is the same shifted-trace lie the collector refuses a frame gap for.

**Stale is labeled, not blanked.** Between the edit and the refill that answers
it, what is on screen answers to the previous parameters. Blanking would take
away the only thing the next refill can be compared against; saying nothing
would let it read as an answer about the parameters just changed. VISION's
honesty half holds outside the budget scope, and this is where the graph keeps
it.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.pipeline.series_collector import CollectedSeries

#: How much taller than the peak the value axis runs.
_HEADROOM = 1.06

_BACKGROUND = QColor(18, 18, 22)
_TRACE = QColor(120, 200, 255)
_STALE_TRACE = QColor(120, 200, 255, 90)
_HINT = QColor(120, 120, 130)

_EMPTY_HINT = "No series yet"
_STALE_NOTICE = "stale — refilling"


class GraphPanel(QWidget):
    """Draws the last completed refill, and says when it has been outlived."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._series: CollectedSeries | None = None
        self._values: NDArray[np.float32] | None = None
        self._stale = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ---- what it is handed -----------------------------------------------

    @property
    def series(self) -> CollectedSeries | None:
        """The series on screen, or None before the first refill lands."""
        return self._series

    @property
    def is_stale(self) -> bool:
        """Whether what is drawn answers to parameters that have since moved."""
        return self._stale

    def set_series(self, series: CollectedSeries | None) -> None:
        """Show `series`, which is current by definition — a refill just produced it.

        Raises:
            ValueError: if a frame of `series` holds more than one value.
        """
        self._series = series
        self._values = None if series is None else _one_value_per_frame(series)
        self._stale = False
        self.update()

    def mark_stale(self) -> None:
        """The parameters under the graph have moved; a refill is on its way."""
        self._stale = True
        self.update()

    def status_text(self) -> str:
        """The line drawn over the plot, empty when the graph speaks for itself."""
        if self._stale:
            return _STALE_NOTICE
        if self._values is None or self._values.size == 0:
            return _EMPTY_HINT
        return ""

    # ---- geometry --------------------------------------------------------

    def value_range(self) -> tuple[float, float]:
        """Floor and ceiling of the value axis, `(0.0, 1.0)` with nothing to draw.

        The floor drops below zero only for a series that goes there: a negative
        value drawn on the bottom edge would read as the same nothing a zero
        does.
        """
        finite = self._finite()
        if finite.size == 0:
            return 0.0, 1.0
        low = min(float(finite.min()), 0.0)
        top = low + (float(finite.max()) - low) * _HEADROOM
        return (low, top) if top > low else (low, low + 1.0)

    def x_of(self, frame: int) -> float:
        """Centre of the column `frame` occupies, or 0.0 when there is no axis.

        A source frame index rather than an offset into the array: `start_index`
        is what makes the graph about the frames it was rendered from, and a
        panel that read the ordinal would place every series at the origin.
        """
        if self._series is None or self._values is None or self._values.size == 0:
            return 0.0
        offset = frame - self._series.start_index
        return self.width() * (offset + 0.5) / self._values.size

    def y_of(self, value: float) -> float:
        """Where `value` sits, with the axis floor on the widget's bottom edge."""
        low, top = self.value_range()
        return self.height() * (1.0 - (value - low) / (top - low))

    def trace(self) -> list[list[QPointF]]:
        """The polylines, one per unbroken run of finite values.

        Exposed for the reason the strip exposes its rects: a painted pixel is
        not something a test can ask about, and "the graph is about the frames it
        names" is a claim about these points.
        """
        if self._series is None or self._values is None:
            return []
        runs: list[list[QPointF]] = []
        current: list[QPointF] = []
        for offset, value in enumerate(self._values.tolist()):
            if not np.isfinite(value):
                if current:
                    runs.append(current)
                    current = []
                continue
            current.append(QPointF(self.x_of(self._series.start_index + offset), self.y_of(value)))
        if current:
            runs.append(current)
        return runs

    def _finite(self) -> NDArray[np.float32]:
        if self._values is None:
            return np.empty(0, np.float32)
        return self._values[np.isfinite(self._values)]

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(_STALE_TRACE if self._stale else _TRACE, 1.6))
        for run in self.trace():
            painter.drawPolyline(QPolygonF(run))
        notice = self.status_text()
        if notice:
            painter.setPen(_HINT)
            painter.drawText(
                self.rect().adjusted(8, 4, -8, -4),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft),
                notice,
            )
        painter.end()


def _one_value_per_frame(series: CollectedSeries) -> NDArray[np.float32]:
    """`series` as `(T,)`, refusing a frame that holds more than one value."""
    rows = series.data.reshape(series.data.shape[0], -1)
    if rows.shape[1] != 1:
        raise ValueError(
            f"a graph is drawn from 1 value per frame, and this series carries "
            f"{rows.shape[1]} — reducing {series.data.shape[1:]} to a number is a tool's "
            "job, not a panel's"
        )
    return np.asarray(rows.reshape(-1), np.float32)
