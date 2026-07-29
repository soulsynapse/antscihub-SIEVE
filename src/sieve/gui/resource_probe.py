from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter_ns

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot

from sieve.core.machine import MemoryUnreadableError, process_memory_bytes
from sieve.core.pool_meter import PoolMeter
from sieve.core.shares import WorkerSplit, ledger_ceiling
from sieve.gui.concurrency import resolve_worker_split


SAMPLE_INTERVAL_MS = 1000


MODE_RENDER_FED_PLAYBACK = "render-fed playback"
MODE_PLAYBACK = "playback"
MODE_RENDER = "render"
MODE_IDLE = "idle"


@dataclass(frozen=True, slots=True)
class PoolReading:
    name: str

    workers: int

    utilisation: float

    depth: int


@dataclass(frozen=True, slots=True)
class ResourceSample:
    mode: str

    rss_bytes: int | None

    ledger_bytes: int
    pools: tuple[PoolReading, ...]

    @property
    def over_ledger(self) -> bool | None:
        if self.rss_bytes is None:
            return None
        return self.rss_bytes > self.ledger_bytes


class _MemoryWorker(QObject):
    sampled = Signal(object)

    def __init__(self, read_memory: Callable[[], int]) -> None:
        super().__init__()
        self._read_memory = read_memory

    @Slot(str, object)
    def complete(self, mode: str, pools: tuple[PoolReading, ...]) -> None:
        try:
            rss: int | None = self._read_memory()
        except MemoryUnreadableError:
            rss = None
        self.sampled.emit(
            ResourceSample(
                mode=mode, rss_bytes=rss, ledger_bytes=ledger_ceiling(), pools=pools
            )
        )


class ResourceProbe(QObject):
    sample = Signal(object)

    _requested = Signal(str, object)

    def __init__(
        self,
        meters: Mapping[str, PoolMeter],
        mode: Callable[[], str],
        parent: QObject | None = None,
        *,
        interval_ms: int = SAMPLE_INTERVAL_MS,
        read_memory: Callable[[], int] = process_memory_bytes,
        split: WorkerSplit | None = None,
    ) -> None:
        super().__init__(parent)
        self._meters = dict(meters)
        self._mode = mode
        resolved = resolve_worker_split() if split is None else split
        self._workers = {
            "player": resolved.player,
            "preview": resolved.preview,
            "detector": resolved.detector,
        }
        self._last_busy = {name: meter.busy_ns for name, meter in self._meters.items()}
        self._last_tick_ns = perf_counter_ns()
        self._awaiting = False
        self._thread = QThread()
        self._thread.setObjectName("sieve-resource-probe")
        self._worker = _MemoryWorker(read_memory)
        self._worker.moveToThread(self._thread)
        self._requested.connect(self._worker.complete)
        self._worker.sampled.connect(
            self._on_sampled, Qt.ConnectionType.QueuedConnection
        )
        self._thread.start()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def shutdown(self) -> None:
        self._timer.stop()
        self._thread.quit()
        self._thread.wait()

    @Slot()
    def _tick(self) -> None:
        if self._awaiting:
            return
        now = perf_counter_ns()
        wall = now - self._last_tick_ns
        self._last_tick_ns = now
        readings: list[PoolReading] = []
        for name, meter in self._meters.items():
            busy = meter.busy_ns
            workers = self._workers.get(name, 1)
            share = busy - self._last_busy[name]
            self._last_busy[name] = busy
            utilisation = (
                min(max(share / (wall * workers), 0.0), 1.0) if wall > 0 else 0.0
            )
            readings.append(
                PoolReading(
                    name=name,
                    workers=workers,
                    utilisation=utilisation,
                    depth=meter.depth,
                )
            )
        self._awaiting = True
        self._requested.emit(self._mode(), tuple(readings))

    @Slot(object)
    def _on_sampled(self, sample: object) -> None:
        self._awaiting = False
        self.sample.emit(sample)
