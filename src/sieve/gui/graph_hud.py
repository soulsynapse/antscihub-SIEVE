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

**And one span is named as the dominant cost.** `WATCHED` above is a fixed
three lines for the whole-render intervals; the attribution field is the
opposite — every key that arrives is ranked, by elapsed against its *own*
ceiling rather than by raw milliseconds, and the leader is printed with
whatever `Sample.detail` its publisher attached. Raw milliseconds would name
the render every time, since a 3000 ms ceiling dwarfs a 100 ms one; the ratio
is what makes a density rebuild at B = 65,536 outrank a render that is merely
large. This is what stands in for the block-count cap that was removed
(`docs/todo/budgets-attribute-cost-they-do-not-cap-it.md`): the user may ask
for any grain, and the obligation the budget creates is that the application
*say what is costing the time* rather than refuse. Persistent, not a warning —
it is drawn whether or not anything is over, because a field that appeared only
on a miss would be a modal with extra steps.

**And so do the resource readings.** `gui/resource_probe.py` publishes the
session's RSS against the ledger's ceiling and each pool's utilisation once a
second, and this plot is where the symptom of both being wrong shows up — a
slow fill is either the machine being divided badly or the budget being
missed, and the two lines belong on the same surface. The memory half renders
its refusal: an unreadable session prints as `unreadable` in the band color,
never as a quiet zero (rule 6, both directions).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from sieve.bench.metrics import Sample
from sieve.gui.band_plot import ACCENT, BAND, DIM, BandPlot, plot_font
from sieve.gui.resource_probe import ResourceSample

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
        #: Newest sample per key, for *every* key — the ranking pool. Separate
        #: from `_watched` because that one is three named lines in a fixed
        #: order and this one is a leaderboard nothing enumerates.
        self._spans: dict[str, Sample] = {}
        self._resources: ResourceSample | None = None
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
        """Any interval from the bus: ranked always, given a line if watched."""
        self._spans[sample.key] = sample
        if sample.key in WATCHED:
            self._watched[sample.key] = sample
        self._schedule_repaint()

    @Slot(object)
    def show_resources(self, sample: object) -> None:
        """The probe's once-a-second reading. Newest wins; repaint is deferred."""
        if isinstance(sample, ResourceSample):
            self._resources = sample
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

    def attribution_line(self) -> tuple[str, bool]:
        """The dominant span, named with what it was for, and whether it is over.

        Ranked by `elapsed / limit`, not by elapsed — see the module docstring.
        The ceiling is printed alongside so the ratio is checkable rather than
        asserted, and the flag is a genuine miss on the leader rather than a
        threshold of its own.
        """
        if not self._spans:
            return "", False
        top = max(self._spans.values(), key=lambda s: s.elapsed_ms / s.budget.limit_ms)
        detail = f" {top.detail}" if top.detail else ""
        line = (
            f"cost: {top.key}{detail} · {top.elapsed_ms:.0f} ms "
            f"({top.elapsed_ms / top.budget.limit_ms:.1f}x its {top.budget.limit_ms:.0f})"
        )
        return line, not top.within_budget

    def resource_line(self) -> tuple[str, bool]:
        """The probe's verdict line and whether it warrants the band color.

        Flagged both when the session is over its ledger and when the reading
        was refused: an unreadable session must not look calmer than a full
        one. Depth is only printed when nonzero — a quiet queue is the normal
        state, and six `q0`s would bury the one that matters.
        """
        sample = self._resources
        if sample is None:
            return "", False
        gib = 1024**3
        if sample.rss_bytes is None:
            memory = f"mem unreadable/{sample.ledger_bytes / gib:.1f} GB"
        else:
            memory = f"mem {sample.rss_bytes / gib:.1f}/{sample.ledger_bytes / gib:.1f} GB"
        pools = [
            f"{pool.name} {pool.utilisation:.0%}" + (f" q{pool.depth}" if pool.depth else "")
            for pool in sample.pools
        ]
        line = "  ·  ".join([memory, *pools, sample.mode])
        return line, sample.over_ledger is not False

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

        resources, flagged = self.resource_line()
        if resources:
            painter.setPen(QColor(BAND) if flagged else QColor(DIM))
            painter.drawText(
                QRect(r.left() + 4, r.bottom() - 14, r.width() - 8, 12),
                int(Qt.AlignmentFlag.AlignLeft),
                resources,
            )

        attribution, over = self.attribution_line()
        if attribution:
            painter.setPen(QColor(BAND) if over else QColor(DIM))
            painter.drawText(
                QRect(r.left() + 4, r.bottom() - 14, r.width() - 8, 12),
                int(Qt.AlignmentFlag.AlignRight),
                attribution,
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
