from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QObject, QThread, Signal, Slot

from sieve.core.pool_meter import PoolMeter
from sieve.core.wavelet import default_freqs, morlet_power
from sieve.detect import gate_to
from sieve.detect import settled_for as settled_for_settings
from sieve.gui.chain_model import DetectorState, DetectorUpdate, recompute
from sieve.gui.concurrency import resolve_worker_split
from sieve.gui.density_plot import DensitySurface, density_surface

FloatArray = NDArray[np.floating[Any]]


@dataclass(frozen=True, slots=True)
class DetectorRequest:
    revision: int

    series: NDArray[np.float32] | tuple[NDArray[np.float32], ...]

    start_index: int
    fps: float
    state: DetectorState

    final: bool


@dataclass(frozen=True, slots=True)
class DetectorResult:
    revision: int
    update: DetectorUpdate
    start_index: int

    series2d: NDArray[np.float32]
    grid: tuple[int, int]

    frames: int

    settled: int

    pooled_power: NDArray[np.float32]

    density: DensitySurface

    density_ms: float
    final: bool


def settled_for(frames: int, fps: float, state: DetectorState, *, final: bool) -> int:
    return settled_for_settings(frames, fps, state.to_settings(), final=final)


def derive(request: DetectorRequest) -> DetectorResult:
    series = request.series
    grids: NDArray[np.float32] = (
        np.stack(series) if isinstance(series, tuple) else series
    )
    frames = int(grids.shape[0])
    grid = (int(grids.shape[1]), int(grids.shape[2]))
    series2d = grids.reshape(frames, -1)
    fps = request.fps
    freqs = default_freqs(fps)
    workers = resolve_worker_split().detector
    update = recompute(
        series2d, fps, request.state, start_index=request.start_index, workers=workers
    )
    pooled = morlet_power(series2d.mean(axis=1), fps, freqs, workers=workers)
    settled = settled_for(frames, fps, request.state, final=request.final)
    started = perf_counter()
    density = density_surface(update.band_power)
    density_ms = (perf_counter() - started) * 1000.0
    return DetectorResult(
        revision=request.revision,
        update=gate_to(update, settled, request.start_index),
        start_index=request.start_index,
        series2d=series2d,
        grid=grid,
        frames=frames,
        settled=settled,
        pooled_power=pooled,
        density=density,
        density_ms=density_ms,
        final=request.final,
    )


@dataclass(frozen=True, slots=True)
class DetectorFailure:
    revision: int

    message: str


class _DetectorWorker(QObject):
    computed = Signal(object)
    failed = Signal(object)

    def __init__(self, meter: PoolMeter) -> None:
        super().__init__()
        self._meter = meter

    @Slot(DetectorRequest)
    def compute(self, request: DetectorRequest) -> None:
        try:
            with self._meter.working():
                result = derive(request)
        except (ValueError, FloatingPointError, MemoryError) as error:
            self.failed.emit(
                DetectorFailure(
                    revision=request.revision,
                    message=f"{type(error).__name__}: {error}",
                )
            )
            return
        self.computed.emit(result)


class DetectorRunner(QObject):
    ready = Signal(object)

    failed = Signal(object)

    _requested = Signal(DetectorRequest)

    def __init__(
        self, parent: QObject | None = None, *, meter: PoolMeter | None = None
    ) -> None:
        super().__init__(parent)
        self._revision = 0
        self._busy = False
        self._pending: DetectorRequest | None = None
        self._meter = PoolMeter() if meter is None else meter
        self._thread = QThread()
        self._thread.setObjectName("sieve-detector")
        self._worker = _DetectorWorker(self._meter)
        self._worker.moveToThread(self._thread)
        self._requested.connect(self._worker.compute)
        self._worker.computed.connect(self._on_computed)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def meter(self) -> PoolMeter:
        return self._meter

    def set_revision(self, revision: int) -> None:
        self._revision = revision
        self._pending = None
        self._meter.set_depth(0)

    def submit(self, request: DetectorRequest) -> bool:
        if request.revision != self._revision:
            return False
        if self._busy:
            self._pending = request
            self._meter.set_depth(1)
            return True
        self._issue(request)
        return True

    def shutdown(self) -> None:
        self._pending = None
        self._thread.quit()
        self._thread.wait()

    def _issue(self, request: DetectorRequest) -> None:
        self._busy = True
        self._requested.emit(request)

    @Slot(object)
    def _on_computed(self, result: DetectorResult) -> None:
        self._busy = False
        self._issue_pending()
        if result.revision == self._revision:
            self.ready.emit(result)

    @Slot(object)
    def _on_failed(self, failure: DetectorFailure) -> None:
        self._busy = False
        self._issue_pending()
        if failure.revision == self._revision:
            self.failed.emit(failure)

    def _issue_pending(self) -> None:
        pending, self._pending = self._pending, None
        self._meter.set_depth(0)
        if pending is not None and pending.revision == self._revision:
            self._issue(pending)
