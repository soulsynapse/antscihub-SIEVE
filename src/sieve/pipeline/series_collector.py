"""Assemble one node's per-frame outputs into a (T, ny, nx) series.

A detector runs on a *series* — the Morlet transform needs the whole working
window of `block_signal` grids at once — and `execute` yields frames one at a
time. This is the bridge: a producer appends rows as they arrive, a consumer
takes the assembled array when the render finishes, and revisions are how the
two sides agree about staleness without sharing a flag.

It sits at this layer and not under `gui/` because the CLI assembles the same
series: `cli/detect_cmd._collect` stacks one node's outputs over a span, which
is this class with the revision fence removed because a batch run has nothing
to supersede. Two implementations of "what the detector was run on" is how the
GUI and the CLI drift into disagreeing about the same project, which is what
`tests/gui/test_gui_cli_parity.py` exists to catch.

Thread-safety is one lock around the row list, held across nothing slower than
an append: `add` runs on whichever thread `execute` is driven from, `start`
and `take` on the caller's.

The frame axis is the *span's*, not the decode's: `execute` yields only
frames at or after `plan.span.start` (the warmup lead-in is consumed and
discarded inside the executor), so the first `add` of a revision defines
`start_index` and everything after it must be contiguous. A gap means frames
were lost between the render thread and here, and the collector refuses to
hand out a series with a silent hole where a detection could have been.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import numpy as np
from numpy.typing import NDArray

from sieve.pipeline.executor import FrameResult


@dataclass(frozen=True, slots=True)
class CollectedSeries:
    """One revision's assembled series, aligned to source frame indices."""

    #: Source index of `data[0]` — the rendered span's start.
    start_index: int
    #: `(T, ny, nx)` float32.
    data: NDArray[np.float32]


@dataclass(frozen=True, slots=True)
class CollectedRows:
    """One revision's rows so far, unstacked — the cheap snapshot.

    `rows` are the collector's own arrays. A row is never written to after its
    append, so a consumer on another thread may stack them without a copy
    race; what it must not do is write into them.
    """

    #: Source index of `rows[0]` — the rendered span's start.
    start_index: int
    #: `len(rows)` frames, each `(ny, nx)` float32, contiguous from `start_index`.
    rows: tuple[NDArray[np.float32], ...]


class SeriesCollector:
    """Rows in on the render thread, one array out on the consumer's.

    One collector watches one node, and callers that render provisionally take
    their own instance rather than sharing one — a shared collector makes a
    speculative render's rows indistinguishable from the committed render's.
    """

    def __init__(self, node_id: str) -> None:
        self._node_id = node_id
        self._lock = Lock()
        self._revision: int | None = None
        self._start: int | None = None
        self._rows: list[NDArray[np.float32]] = []

    @property
    def node_id(self) -> str:
        """The node whose outputs this assembles."""
        return self._node_id

    def start(self, revision: int) -> None:
        """A new render is about to produce frames; everything older is dead.

        Rows a superseded render manages to deliver after this are discarded
        by the revision check in `add`, which is what makes the served series
        never contain them.
        """
        with self._lock:
            self._revision = revision
            self._start = None
            self._rows = []

    def add(self, revision: int, result: FrameResult) -> None:
        """One frame's outputs, on the render thread.

        A revision that is not the current one contributes nothing — not a
        partial row, not a stale tail. A result that does not carry this
        node's output is ignored rather than an error: a conflicted chain
        legitimately renders a prefix that stops above the watched node.
        """
        frame = result.outputs.get(self._node_id)
        if frame is None:
            return
        row = np.asarray(frame.data, np.float32)
        with self._lock:
            if revision != self._revision:
                return
            if self._start is None:
                self._start = result.index
            expected = self._start + len(self._rows)
            if result.index != expected:
                raise ValueError(
                    f"series for {self._node_id!r} expected frame {expected}, got "
                    f"{result.index}; a gap here would be a silent hole in the detector's input"
                )
            self._rows.append(row)

    def snapshot(self, revision: int) -> CollectedSeries | None:
        """Whatever `revision` has assembled *so far*, or None if superseded.

        The partial-detector path: the render thread is still appending, and
        this hands the GUI a contiguous prefix of the series to derive from
        while it does. The returned array is a fresh stack, so the rows the
        collector goes on appending are not aliased into a consumer that is
        about to FFT them on another thread.

        The prefix is contiguous by construction — `add` refuses a gap — so a
        snapshot is always a real record of `[start_index, start_index + T)`
        and never a series with a hole standing in for frames still in flight.
        What it is *not* is final: the trailing frames are inside the
        transform's cone of influence and change as the record grows, which is
        `core.ops.wavelet.settled_frames`' business to say and the caller's to
        render honestly.
        """
        with self._lock:
            if revision != self._revision or self._start is None or not self._rows:
                return None
            return CollectedSeries(
                start_index=self._start, data=np.stack(self._rows).astype(np.float32, copy=False)
            )

    def snapshot_rows(self, revision: int) -> CollectedRows | None:
        """`snapshot` without the stack: an O(rows) pointer copy.

        The stack itself is O(frames x blocks) — tens of megabytes at a small
        block size — and belongs on the thread that will transform the result,
        not on the one pacing the render. Called once per pacing kick on the
        GUI thread it was a per-kick stall the playback timer and every queued
        repaint sat behind.
        """
        with self._lock:
            if revision != self._revision or self._start is None or not self._rows:
                return None
            return CollectedRows(start_index=self._start, rows=tuple(self._rows))

    def take(self, revision: int) -> CollectedSeries | None:
        """The finished series for `revision`, or None if it was superseded.

        Returns None too for a render that produced no rows — a chain whose
        watched node was never reached — which the caller reports as "no
        reachable step", not as an empty detection.

        Identical to `snapshot` in what it computes and different in what it
        claims: this one is called when the render is over, so the record is
        the whole working window and nothing in it is provisional.
        """
        return self.snapshot(revision)
