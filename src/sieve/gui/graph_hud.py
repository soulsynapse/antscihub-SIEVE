from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from sieve.bench.metrics import Sample
from sieve.gui.band_plot import ACCENT, BAND, DIM, BandPlot, plot_font
from sieve.gui.resource_probe import ResourceSample


REPAINT_MS = 33


MIN_CEILING_MS = 10.0


WATCHED: dict[str, str] = {
    "full_preview_render": "render",
    "slider_to_preview": "first frame",
    "filter_to_first_tick": "first tick",
}


class GraphHud(BandPlot):
    title = "render cost · ms per frame"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._costs: dict[int, float] = {}
        self._ceiling = MIN_CEILING_MS
        self._flush_pending = False
        self._watched: dict[str, Sample] = {}
        self._spans: dict[str, Sample] = {}
        self._resources: ResourceSample | None = None
        self.setMinimumHeight(110)

    @Slot()
    def begin(self) -> None:
        self._costs.clear()
        self._ceiling = MIN_CEILING_MS
        self.update()

    @Slot(int, float)
    def add_cost(self, index: int, elapsed_ms: float) -> None:
        self._costs[index] = elapsed_ms
        if elapsed_ms > self._ceiling:
            self._ceiling = elapsed_ms
        self._schedule_repaint()

    @Slot(Sample)
    def show_sample(self, sample: Sample) -> None:
        self._spans[sample.key] = sample
        if sample.key in WATCHED:
            self._watched[sample.key] = sample
        self._schedule_repaint()

    @Slot(object)
    def show_resources(self, sample: object) -> None:
        if isinstance(sample, ResourceSample):
            self._resources = sample
            self._schedule_repaint()

    def costs(self) -> tuple[tuple[int, float], ...]:
        return tuple(sorted(self._costs.items()))

    @property
    def ceiling_ms(self) -> float:
        return self._ceiling

    def budget_line(self) -> tuple[str, bool]:
        parts: list[str] = []
        missed = False
        for key, name in WATCHED.items():
            sample = self._watched.get(key)
            if sample is None:
                continue
            parts.append(
                f"{name} {sample.elapsed_ms:.0f}/{sample.budget.limit_ms:.0f} ms"
            )
            missed = missed or not sample.within_budget
        return "  ·  ".join(parts), missed

    def attribution_line(self) -> tuple[str, bool]:
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
        sample = self._resources
        if sample is None:
            return "", False
        gib = 1024**3
        if sample.rss_bytes is None:
            memory = f"mem unreadable/{sample.ledger_bytes / gib:.1f} GB"
        else:
            memory = (
                f"mem {sample.rss_bytes / gib:.1f}/{sample.ledger_bytes / gib:.1f} GB"
            )
        pools = [
            f"{pool.name} {pool.utilisation:.0%}"
            + (f" q{pool.depth}" if pool.depth else "")
            for pool in sample.pools
        ]
        line = "  ·  ".join([memory, *pools, sample.mode])
        return line, sample.over_ledger is not False

    def _range(self) -> tuple[float, float]:
        return 0.0, self._ceiling

    def _grabbable(self, pos: QPointF) -> str | None:
        del pos
        return None

    def _paint_handles(self, painter: QPainter, r: QRect) -> None:
        del painter, r

    def paint_content(self, painter: QPainter, r: QRect) -> None:
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

    def _schedule_repaint(self) -> None:
        if self._flush_pending:
            return
        self._flush_pending = True
        QTimer.singleShot(REPAINT_MS, self._flush)

    def _flush(self) -> None:
        self._flush_pending = False
        self.update()
