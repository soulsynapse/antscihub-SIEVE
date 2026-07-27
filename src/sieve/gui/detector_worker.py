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
provisional (`core.wavelet.settled_frames`); a centered detection window near
the cut averages frames that have not arrived (`core.detection.settled_frames`).
`DetectorResult.settled` is where they meet, and it is the whole record once
`final` is set — a render that is over has no moving frontier, and its edges
mean what the clip means.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QObject, QThread, Signal, Slot

from sieve.core.detection import gate_intervals
from sieve.core.detection import settled_frames as settled_after_window
from sieve.core.wavelet import band_indices, default_freqs, morlet_power
from sieve.core.wavelet import settled_frames as settled_after_coi
from sieve.gui.chain_model import DetectorState, DetectorUpdate, recompute
from sieve.gui.concurrency import DETECTOR_WORKERS

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
    #: `(T, ny, nx)` block grids as the collector assembled them, `T` frames of
    #: the window so far. Flattened to columns inside `derive` rather than by
    #: the caller, so the reshape and the grid it implies are stated once.
    series: NDArray[np.float32]
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
    final: bool


def settled_for(frames: int, fps: float, state: DetectorState, *, final: bool) -> int:
    """Where a record of `frames` stops being provisional, under `state`.

    Two frontiers and the smaller wins: the transform's cone of influence at
    the cut, and a centered detection window reaching past it. A final pass
    claims the whole record — a render that is over has no moving frontier, and
    its edges mean what the clip's edges mean.

    Shared with `FilterTab`'s cheap tier rather than living only in `derive`,
    because a D drag over a partial series *moves* this frontier: widening a
    centered window pulls it back, and a tab that kept the frontier the worker
    last reported would go on painting a gate over frames the wider window no
    longer settles.
    """
    if final:
        return frames
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, state.freq_band[0], state.freq_band[1])
    return min(
        settled_after_coi(frames, fps, freqs[i:j]),
        settled_after_window(frames, state.window_frames, state.centered),
    )


def derive(request: DetectorRequest) -> DetectorResult:
    """The whole derivation, as a pure function. Qt-free and thread-free.

    Separate from the worker because everything worth pinning about a partial
    pass — which frontier wins, that a final pass claims the record, that the
    gate stops where the window stops being honest — is arithmetic, and a test
    of it should not need an event loop or a thread to reach it.
    """
    grids = request.series
    frames = int(grids.shape[0])
    grid = (int(grids.shape[1]), int(grids.shape[2]))
    series2d = grids.reshape(frames, -1)
    fps = request.fps
    freqs = default_freqs(fps)
    update = recompute(
        series2d, fps, request.state, start_index=request.start_index, workers=DETECTOR_WORKERS
    )
    pooled = morlet_power(series2d.mean(axis=1), fps, freqs, workers=DETECTOR_WORKERS)

    settled = settled_for(frames, fps, request.state, final=request.final)

    return DetectorResult(
        revision=request.revision,
        update=gate_to(update, settled, request.start_index),
        start_index=request.start_index,
        series2d=series2d,
        grid=grid,
        frames=frames,
        settled=settled,
        pooled_power=pooled,
        final=request.final,
    )


def gate_to(update: DetectorUpdate, settled: int, start_index: int) -> DetectorUpdate:
    """Truncate the gate and its intervals to the settled frontier.

    The curves are published in full and drawn faded past the frontier, because
    a provisional *value* reads as one. A provisional *detection* does not: the
    seeker's ticks and the prev/next jumps are navigation, and an interval that
    appears and then vanishes as the record grows is a worse lie than a graph
    that has not got there yet. So the gate stops where the arithmetic stops
    being final, and the summary's count only ever grows.
    """
    gate = update.gate
    if gate is None or settled >= gate.shape[0]:
        return update
    clipped = gate[:settled]
    return DetectorUpdate(
        band_power=update.band_power,
        count=update.count,
        windowed=update.windowed,
        gate=clipped,
        intervals=tuple(gate_intervals(clipped, start=start_index)),
        band_rows=update.band_rows,
    )


class _DetectorWorker(QObject):
    """Lives on the detector thread. Its one slot runs off the GUI thread."""

    computed = Signal(object)

    @Slot(DetectorRequest)
    def compute(self, request: DetectorRequest) -> None:
        """Derive and report. Nothing here touches Qt beyond the emit.

        A derivation that raises is dropped rather than reported: every input
        was validated by the chain that produced it, so a failure here is a
        defect in this module and not something a user can act on — and a
        partial pass that reported an error would replace a graph that is
        merely incomplete with one that says it is broken.
        """
        try:
            result = derive(request)
        except (ValueError, FloatingPointError):
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

    _requested = Signal(DetectorRequest)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._revision = 0
        self._busy = False
        self._pending: DetectorRequest | None = None

        self._thread = QThread()
        self._thread.setObjectName("sieve-detector")
        self._worker = _DetectorWorker()
        self._worker.moveToThread(self._thread)
        self._requested.connect(self._worker.compute)
        self._worker.computed.connect(self._on_computed)
        self._thread.start()

    @property
    def busy(self) -> bool:
        """Whether a pass is in flight. The tab's idle gate reads this."""
        return self._busy

    def set_revision(self, revision: int) -> None:
        """Declare `revision` the only one still worth painting.

        Called when a render starts. Anything the worker is still deriving for
        an older revision is finished — it is one FFT and abandoning it buys
        nothing — but its result is dropped on arrival rather than painted over
        a chain the user has already changed.
        """
        self._revision = revision
        self._pending = None

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
        pending, self._pending = self._pending, None
        if pending is not None and pending.revision == self._revision:
            self._issue(pending)
        if result.revision == self._revision:
            self.ready.emit(result)
