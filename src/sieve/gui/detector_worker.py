"""The detector's own thread: derive the graphs from a series still being filled.

Before this, the graphs appeared all at once. `SeriesCollector` accumulated the
working window on the render thread and `FilterTab._on_render_finished` turned
the whole of it into a `DetectorUpdate` in one go — so a user watching a long
window render sat in front of an empty count plot for the duration and then got
everything. The value of the tab is the tuning loop, and a loop whose feedback
arrives only at the end is not one.

**Why a third thread rather than the two that exist.** The recompute is an FFT
over `(T, B)` — `morlet_band_power` plus a pooled `morlet_power` for the
scalogram — and neither existing thread can host it. On the GUI thread it
blocks the repaint it exists to cause, which is the one thing this application
sells. On the render thread it is worse: `RenderRequest.consumer` runs inside
the timed spans, so every partial derive would inflate `full_preview_render`
and steal decode throughput to buy graph liveness — which ARCHITECTURE.md
non-negotiable #5 calls a defect rather than a tuning choice, in as many words.
So the derivation gets a thread, and the two budgets either side of it keep
measuring what they already measured.

**Self-pacing, not a timer.** One request in flight and one pending, latest
wins — `preview_runner.py`'s shape, for its reason: there is one desired
derivation at any moment and it is always over the longest prefix. What is
deliberately absent is a cadence. The tab kicks a pass when frames arrive and
the worker is idle, so the partial rate settles at exactly
`render_time / recompute_time` passes with no number for anyone to tune: on a
cheap chain the graphs nearly stream, on an expensive one they step, and
neither case can spend more than half its wall clock deriving. A fixed interval
would have to be wrong in one of those two directions.

**No cancellation, on purpose.** `preview_runner.py` can abandon between frames
because `execute` is a generator with a boundary to check at. A single FFT has
no such boundary — a flag would be read once, before the work, which is a
check the submission already did. Stale passes are dropped by revision on the
GUI side and their cost is bounded by the one-in-flight rule.

**What a partial pass may claim.** Two frontiers, and the smaller wins. The
transform zero-pads past the cut, so the trailing cone of influence is
provisional (`core.ops.wavelet.settled_frames`); a centered detection window near
the cut averages frames that have not arrived (`core.ops.detection.settled_frames`).
`DetectorResult.settled` is where they meet, and it is the whole record once
`final` is set — a render that is over has no moving frontier, and its edges
mean what the clip means.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QObject, QThread, Signal, Slot

import sieve.filters.detect as detect_filter
from sieve.core.pool_meter import PoolMeter
from sieve.filters.detect import DetectorUpdate, DetectParams
from sieve.gui.chain_model import DetectorState
from sieve.gui.concurrency import resolve_worker_split
from sieve.gui.density_plot import DensitySurface, density_surface

FloatArray = NDArray[np.floating[Any]]


@dataclass(frozen=True, slots=True)
class DetectorRequest:
    """One derivation to run off the GUI thread. Crosses to the worker whole.

    `series` must be a snapshot the GUI thread will not touch again — the
    worker reads it without a lock, and `SeriesCollector.snapshot` stacks a
    fresh array for exactly this reason.
    """

    #: The render revision this prefix came from. Carried so the GUI can drop a
    #: result for a chain that has since been edited, the same stamp-not-a-flag
    #: rule `preview_runner.py` runs on.
    revision: int
    #: `T` frames of `(ny, nx)` block grids as the collector assembled them —
    #: a `(T, ny, nx)` array, or the collector's unstacked row tuple, which
    #: `derive` stacks on this thread so the GUI thread never pays the copy.
    #: Flattened to columns inside `derive` rather than by the caller, so the
    #: reshape and the grid it implies are stated once.
    series: NDArray[np.float32] | tuple[NDArray[np.float32], ...]
    #: Source index of `series[0]`, so intervals come back absolute.
    start_index: int
    fps: float
    state: DetectorState
    #: Whether the render that produced `series` is over. Final passes claim
    #: the whole record settled and are the only ones that may.
    final: bool


@dataclass(frozen=True, slots=True)
class DetectorResult:
    """One derivation, with the frontier it is allowed to be read up to."""

    revision: int
    update: DetectorUpdate
    start_index: int
    #: The `(T, B)` columns `update` was derived from, and the `(ny, nx)` grid
    #: they flatten. Carried back rather than re-read from the collector,
    #: which by now holds *more* rows: a tab that re-snapshotted would pair a
    #: longer series with a shorter update and every index into the two would
    #: silently disagree.
    series2d: NDArray[np.float32]
    grid: tuple[int, int]
    #: Frames the series covered. `settled <= frames`, and they are equal
    #: exactly when the pass was final.
    frames: int
    #: Frames from `start_index` whose values will not change as the record
    #: grows. Everything past it is drawn provisionally and gates nothing.
    settled: int
    #: `(F, T)` pooled scalogram power over the whole bank.
    pooled_power: NDArray[np.float32]
    #: The density picture for `update.band_power`, binned here rather than by
    #: the widget. Carried as a value so the GUI thread is left with a `QImage`
    #: wrap; the plot's identity check is what makes handing it one safe.
    density: DensitySurface
    #: Milliseconds the surface above took. The `density_rebuild` producer —
    #: published by the GUI thread on arrival, measured on this one, because
    #: the interval is the binning wherever it runs and the thread it ran on is
    #: the thing that changed.
    density_ms: float
    final: bool


def settled_for(frames: int, fps: float, state: DetectorState, *, final: bool) -> int:
    """The detect filter frontier with the live state converted at the boundary.

    Kept as a name here because `FilterTab`'s cheap tier calls it with the
    state it is dragging: a D drag over a partial series *moves* this frontier,
    and a tab that kept the frontier the worker last reported would go on
    painting a gate over frames the wider window no longer settles.
    """
    params = DetectParams.from_settings(state.to_settings(), fps=fps)
    return detect_filter.settled_for(frames, params, final=final)


def derive(request: DetectorRequest) -> DetectorResult:
    """The whole derivation, as a pure function. Qt-free and thread-free.

    Separate from the worker because everything worth pinning about a partial
    pass — which frontier wins, that a final pass claims the record, that the
    gate stops where the window stops being honest — is arithmetic, and a test
    of it should not need an event loop or a thread to reach it.
    """
    series = request.series
    grids: NDArray[np.float32] = np.stack(series) if isinstance(series, tuple) else series
    frames = int(grids.shape[0])
    grid = (int(grids.shape[1]), int(grids.shape[2]))
    series2d = grids.reshape(frames, -1)
    fps = request.fps
    workers = resolve_worker_split().detector
    params = DetectParams.from_settings(request.state.to_settings(), fps=fps)
    update = detect_filter.detect_series(
        series2d, params, start_index=request.start_index, workers=workers
    )
    pooled = detect_filter.pooled_scalogram(series2d, params, workers=workers)

    settled = detect_filter.settled_for(frames, params, final=request.final)

    # Beside `morlet_power` because this thread already holds the array the
    # binning reads. `gate_to` below rebuilds the update but passes
    # `band_power` through untouched, so the surface stays the picture of the
    # array the tab will hand back to the plot.
    started = perf_counter()
    density = density_surface(update.band_power)
    density_ms = (perf_counter() - started) * 1000.0

    return DetectorResult(
        revision=request.revision,
        update=detect_filter.gate_to(update, settled, request.start_index),
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
    """A derivation that raised, carried back so the graphs can say so."""

    revision: int
    #: One line for the plot's notice. The exception's own text, prefixed with
    #: its type, because the two together are what distinguishes a shape
    #: mismatch from an allocation that could not be met — and the second is
    #: the one a user can act on by making the block size larger.
    message: str


class _DetectorWorker(QObject):
    """Lives on the detector thread. Its one slot runs off the GUI thread."""

    computed = Signal(object)
    failed = Signal(object)

    def __init__(self, meter: PoolMeter) -> None:
        super().__init__()
        self._meter = meter

    @Slot(DetectorRequest)
    def compute(self, request: DetectorRequest) -> None:
        """Derive and report — the result, or the failure. Never neither.

        The original argument for swallowing was sound about modals and wrong
        about silence: every input here was validated by the chain that
        produced it, so a raise *is* a defect in this module rather than
        something a user can act on, and a partial pass must not replace a
        merely-incomplete graph with one claiming to be broken. None of that
        licenses the graph going quiet with nothing said, which is rule 6
        exactly — unexamined must not render as quiet. So the failure crosses
        back and the tab renders it as a notice on the plot: no modal, no
        stale curve passed off as current.

        `MemoryError` is caught with the two value errors because it is the
        failure this path actually reaches under a large block count, and it
        was the one escaping to kill the pass some other way.
        """
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
    """Derives the detector off the GUI thread, one pass in flight at a time.

    Construct on the GUI thread. Owns the detector thread for its whole life,
    so `shutdown` is required before the application exits — the same
    obligation `PreviewRunner` and `VideoPlayer` carry.
    """

    #: A finished derivation the GUI should paint, as a `DetectorResult`.
    #: Already filtered: a result for a superseded revision never gets here.
    ready = Signal(object)

    #: A derivation that raised, as a `DetectorFailure`. Filtered by revision
    #: the same way `ready` is: a failure on a chain the user has already
    #: edited is not a fact about the chain they are looking at.
    failed = Signal(object)

    _requested = Signal(DetectorRequest)

    def __init__(self, parent: QObject | None = None, *, meter: PoolMeter | None = None) -> None:
        super().__init__(parent)
        self._revision = 0
        self._busy = False
        self._pending: DetectorRequest | None = None
        #: Busy time is accumulated on the detector thread around `derive`;
        #: depth is the pending slot (0 or 1 — latest wins is the queue).
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
        """Whether a pass is in flight. The tab's idle gate reads this."""
        return self._busy

    @property
    def meter(self) -> PoolMeter:
        """The pool's busy-time and depth counters, for a sampler to read."""
        return self._meter

    def set_revision(self, revision: int) -> None:
        """Declare `revision` the only one still worth painting.

        Called when a render starts. Anything the worker is still deriving for
        an older revision is finished — it is one FFT and abandoning it buys
        nothing — but its result is dropped on arrival rather than painted over
        a chain the user has already changed.
        """
        self._revision = revision
        self._pending = None
        self._meter.set_depth(0)

    def submit(self, request: DetectorRequest) -> bool:
        """Derive `request`, superseding anything waiting. Returns whether it
        was accepted at all.

        A request for a stale revision is refused outright. A request that
        arrives while the worker is busy replaces the pending one rather than
        queueing behind it: the pending slot always holds the longest prefix
        anybody has asked about, and deriving the same graph twice over two
        prefixes when the second is available is work with no reader.
        """
        if request.revision != self._revision:
            return False
        if self._busy:
            self._pending = request
            self._meter.set_depth(1)
            return True
        self._issue(request)
        return True

    def shutdown(self) -> None:
        """Stop the detector thread. Call before the application exits."""
        self._pending = None
        self._thread.quit()
        self._thread.wait()

    def _issue(self, request: DetectorRequest) -> None:
        self._busy = True
        self._requested.emit(request)

    @Slot(object)
    def _on_computed(self, result: DetectorResult) -> None:
        """A pass reported back. Free the slot, forward it if anyone still wants it.

        The slot is freed before the signal goes out, so a slot that reacts by
        submitting the next prefix — which is the tab's whole pacing loop —
        finds the worker idle rather than queueing behind a pass that has
        already finished.
        """
        self._busy = False
        self._issue_pending()
        if result.revision == self._revision:
            self.ready.emit(result)

    @Slot(object)
    def _on_failed(self, failure: DetectorFailure) -> None:
        """A pass raised. Free the slot exactly as a success does, then report.

        The pacing loop must not care which way a pass ended — a worker left
        marked busy by a failure would take the tab's idle gate down with it
        and stop every later prefix, turning one raised derivation into a tab
        that never derives again.
        """
        self._busy = False
        self._issue_pending()
        if failure.revision == self._revision:
            self.failed.emit(failure)

    def _issue_pending(self) -> None:
        pending, self._pending = self._pending, None
        self._meter.set_depth(0)
        if pending is not None and pending.revision == self._revision:
            self._issue(pending)
