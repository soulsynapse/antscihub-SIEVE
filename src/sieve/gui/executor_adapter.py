from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal, Slot

from sieve.bench.metrics import METRICS, MetricBus, Sample


class ExecutorAdapter(QObject):
    sample = Signal(Sample)

    missed = Signal(Sample)

    _relayed = Signal(Sample)

    def __init__(
        self, bus: MetricBus | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._relayed.connect(self._on_relayed, Qt.ConnectionType.QueuedConnection)
        self._unsubscribe = (METRICS if bus is None else bus).subscribe(self._receive)

    def close(self) -> None:
        self._unsubscribe()

    def _receive(self, sample: Sample) -> None:
        self._relayed.emit(sample)

    @Slot(Sample)
    def _on_relayed(self, sample: Sample) -> None:
        self.sample.emit(sample)
        if not sample.within_budget:
            self.missed.emit(sample)
