"""The graph HUD: what each frame of the working window cost, as a plot.

VISION step 4's benchmark feedback, drawn. `gui/preview_runner.py` emits
`frame_cost(source index, ms)` per delivered frame of the newest render, and
this is the view that turns six hundred of those into an answer to the question
the two whole-render numbers on the bus cannot carry: *where* in the
representative clip the expensive frames are.

**x is the source frame index across the working window, y is milliseconds for
that frame.** Not sample arrival order — over arrival order the playhead means
nothing, and the playhead is the whole reason the axis was chosen. VISION asks
for a vertical bar showing where in the clip the graph currently is, and with
this axis that bar *is* the playhead: `VideoPlayer.frame_changed` in one more
view rather than a second source of truth, exactly as it is for every plot in
the `BandPlot` family this extends.

**The series is replaced, not appended to.** The runner's `render_started`
carries a revision and a superseded render's frames never arrive on the GUI
side, so this widget never decides for itself what is stale: it clears on
`begin` and accumulates until the next one. Frames are keyed by source index
rather than listed in arrival order for the same reason the axis is what it is
— the runner promises only that every point belongs to the newest render, not
that the window starts where the last one did.

**The repaint is throttled here, not upstream.** A cold render delivers the
whole window in a burst, and each `frame_cost` is its own queued event — Qt's
own paint compression cannot help across events, so a HUD repainting per point
would spend the GUI thread on paint while the render thread waits behind it on
the event queue. `add_cost` therefore marks the series dirty and arms one
trailing single-shot; however many points land inside the interval, one repaint
follows the last of them, and no point is ever dropped — only its paint is
deferred.

**No handles, no band.** The base class's one drag gesture falls through to the
scrub tier by construction (`_grabbable` refuses every press), so a drag on the
cost plot moves the shared playhead like a drag on any other plot — a cost
spike is a *place*, and the gesture to go there is the one the user already
knows. The band machinery paints nothing because a threshold on this plot would
be a lie: the per-frame interval has no budget key on purpose (six hundred
samples of one interval with no ceiling of its own), so there is no line to
place.

**The whole-render verdicts land here too.** `gui/executor_adapter.py` carries
the bus's samples to the GUI thread and until now nothing drew them.
`show_sample` keeps the newest sample per watched key and paints one line —
elapsed against ceiling, in the band color when missed — because a budget miss
is a defect (ARCHITECTURE.md non-negotiable #4) and a defect reported only to a
status bar the user has scrolled past is one nobody sees.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from sieve.bench.metrics import Sample
from sieve.gui.band_plot import ACCENT, BAND, DIM, BandPlot, plot_font

#: The trailing-flush interval. One repaint at most this often while points are
#: arriving, and always one after the last of them — a 30 Hz HUD over a render
#: that delivers frames faster than that is the render's audience, not its
#: bottleneck.
REPAINT_MS = 33

#: The y axis never collapses below this, so a fast render reads as a low flat
#: line rather than as full-scale noise over a 0.3 ms ceiling.
MIN_CEILING_MS = 10.0

#: The whole-render intervals worth a line on the HUD, with the short names the
#: line has room for. Everything else on the bus (scrub, band drags, knob
#: settles) belongs to the gesture that produced it, not to this plot.
WATCHED: dict[str, str] = {
    "full_preview_render": "render",
    "slider_to_preview": "first frame",
    "filter_to_first_tick": "first tick",
}


class GraphHud(BandPlot):
    """Per-frame render cost over the working window, playhead as cursor."""

    title = "render cost · ms per frame"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._costs: dict[int, float] = {}
        self._ceiling = MIN_CEILING_MS
        self._flush_pending = False
        self._watched: dict[str, Sample] = {}
        self.setMinimumHeight(110)

    # ---- what it is told ---------------------------------------------------

    @Slot()
    def begin(self) -> None:
        """A new render is about to produce frames: drop the old series.

        Connected to the runner's `render_started`. An unthrottled `update` is
        fine here — renders start once per submission, not once per frame.
        """
        self._costs.clear()
        self._ceiling = MIN_CEILING_MS
        self.update()

    @Slot(int, float)
    def add_cost(self, index: int, elapsed_ms: float) -> None:
        """One frame's cost, keyed by its source index. Repaint is deferred."""
        self._costs[index] = elapsed_ms
        if elapsed_ms > self._ceiling:
            self._ceiling = elapsed_ms
        self._schedule_repaint()

    @Slot(Sample)
    def show_sample(self, sample: Sample) -> None:
        """A whole-render interval from the bus, if it is one this plot watches."""
        if sample.key not in WATCHED:
            return
        self._watched[sample.key] = sample
        self._schedule_repaint()

    # ---- the series (exposed because these are the claims worth testing) ----

    def costs(self) -> tuple[tuple[int, float], ...]:
        """The series in source-index order, whatever order it arrived in."""
        return tuple(sorted(self._costs.items()))

    @property
    def ceiling_ms(self) -> float:
        """The y axis's top, in milliseconds."""
        return self._ceiling

    def budget_line(self) -> tuple[str, bool]:
        """The whole-render verdict line and whether anything in it missed."""
        parts: list[str] = []
        missed = False
        for key, name in WATCHED.items():
            sample = self._watched.get(key)
            if sample is None:
                continue
            parts.append(f"{name} {sample.elapsed_ms:.0f}/{sample.budget.limit_ms:.0f} ms")
            missed = missed or not sample.within_budget
        return "  ·  ".join(parts), missed

    # ---- the value axis ------------------------------------------------------

    def _range(self) -> tuple[float, float]:
        return 0.0, self._ceiling

    # ---- the gesture: every press is a scrub ---------------------------------

    def _grabbable(self, pos: QPointF) -> str | None:
        del pos
        return None

    # ---- painting -------------------------------------------------------------

    def _paint_handles(self, painter: QPainter, r: QRect) -> None:
        del painter, r

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        """The cost polyline, the axis ceiling, and the budget verdict line."""
        series = self.costs()
        if series:
            painter.setPen(QPen(ACCENT, 1.2))
            points = [QPointF(self.x_of(index), self.y_of(ms)) for index, ms in series]
            if len(points) == 1:
                painter.setBrush(ACCENT)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(points[0], 2.0, 2.0)
            else:
                painter.drawPolyline(QPolygonF(points))

        painter.setFont(plot_font(8))
        painter.setPen(QColor(DIM))
        painter.drawText(
            QRect(r.left() + 4, r.top() + 2, r.width() - 8, 12),
            int(Qt.AlignmentFlag.AlignLeft),
            f"{self._ceiling:.0f} ms",
        )

        line, missed = self.budget_line()
        if line:
            painter.setPen(QColor(BAND) if missed else QColor(DIM))
            painter.drawText(
                QRect(r.left() + 4, r.top() + 2, r.width() - 8, 12),
                int(Qt.AlignmentFlag.AlignRight),
                line,
            )

    # ---- the throttle ----------------------------------------------------------

    def _schedule_repaint(self) -> None:
        """Arm one trailing repaint. Every call inside the interval rides it."""
        if self._flush_pending:
            return
        self._flush_pending = True
        QTimer.singleShot(REPAINT_MS, self._flush)

    def _flush(self) -> None:
        self._flush_pending = False
        self.update()
