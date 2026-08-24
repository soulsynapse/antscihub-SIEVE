"""Filling a window into memory, in the order attention actually wants it.

The same split as the proxy builder, for the same reason. **`fill_order` is a
pure function** returning the list of chunk starts to work through; **`Frontier`
is the thread** that works through it. In the explorer these are four lines
inside a thread body, and the difference between a frozen landing and a seamless
one is which way a list was rotated — observable only by decoding video and
watching a picture, which is how it was got wrong in the first place.

**Fill from the playhead's chunk, then wrap.** The finding is blunt about it:
the same decode work in a different order is the difference between a frozen
landing and a seamless one
(`docs/findings/2026.08.22-what-froze-the-felt-loop.md`). A window filled from
its start while the loop plays from where somebody clicked spends its first
seconds decoding ground nobody is looking at, and the picture sits still. Filled
from the click, the frontier stays ahead of the playhead and the landing has no
frozen beat at all.

**Chunks already on disk refill at cut speed.** A revisited window costs a read
rather than a re-derive from the original, and the schedule says which is which
before any of it runs, so a caller can price a landing without starting one.

**Pausing is a priority inversion, and it is deliberate.** When somebody changes
a signal while crops are still growing, the thing they are waiting on is the
signal. The frontier yields its decode bandwidth rather than competing for it —
which is what the plan calls for and what a fill that could not be paused would
make impossible.

**Stopping without waiting is safe here, and it was not obvious.** A dying
frontier's last frames land in the same store under the same form key, so they
are simply frames somebody may want. The explorer argues this in a comment; with
a form-keyed store it is true by construction, because a frame that arrives late
cannot be the wrong picture — it can only be a picture nobody asked for, which
is what eviction is for.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import numpy as np

from sieve.frame.form import Form, build
from sieve.session.ledger import Ledger
from sieve.store.chunks import ChunkStore
from sieve.store.resident import ResidentStore

#: How long a paused frontier sleeps between checks. Short enough that handing
#: the decoder over feels immediate, long enough not to spin.
PAUSE_POLL_S = 0.02


@dataclass(frozen=True)
class Piece:
    """One chunk of a window, and where its frames are coming from."""

    grid_start: int       #: where this chunk begins on the absolute grid
    start: int            #: where filling begins, clipped to the window
    end: int              #: exclusive, clipped to the window
    from_disk: bool       #: already persisted, so a read rather than a decode
    chunk_rows: int       #: what a whole chunk is, so `whole` can be honest

    @property
    def rows(self) -> int:
        return self.end - self.start

    @property
    def whole(self) -> bool:
        """Does this piece cover its chunk exactly?

        Only a whole chunk may be written. A window rarely begins on the grid,
        so its first and last pieces are partial — and a partial chunk is not
        a smaller chunk, it is one that is not finished. Recording it would
        leave the coverage record's spans no longer tiling, and every consumer
        below would gain a case.

        Both halves are needed. Alignment alone says the piece begins where a
        chunk begins, which the *last* piece of a window does while covering a
        handful of rows — a version of this checking only alignment called a
        sixteen-row tail whole.
        """
        return (self.start == self.grid_start
                and self.rows == self.chunk_rows)


def fill_order(start: int, end: int, anchor: int, rows_per_chunk: int,
               held: list[tuple[int, int]] | None = None) -> list[Piece]:
    """Which pieces of `[start, end)` to fill, in the order to fill them.

    Anchored on the playhead and wrapping: the chunk containing `anchor`
    first, then forward to the end of the window, then round to the
    beginning. That rotation is the entire finding, and returning it as a list
    is what makes it something a check can hold to rather than something a
    person has to watch for.

    Pieces sit on the absolute chunk grid and are clipped to the window, so
    two windows overlapping the same ground share chunks instead of each
    writing its own copy of the overlap. `held` is the row ranges already on
    disk, so each piece says whether it is a read or a decode before any of it
    runs — which is what lets a caller price a landing without starting one.
    """
    if end <= start or rows_per_chunk <= 0:
        return []
    anchor = max(start, min(anchor, end - 1))
    ranges = held or []

    spans: list[tuple[int, int, int]] = []
    grid = start - start % rows_per_chunk
    while grid < end:
        low, high = max(grid, start), min(grid + rows_per_chunk, end)
        if high > low:
            spans.append((grid, low, high))
        grid += rows_per_chunk

    landed = next((index for index, (_, low, high) in enumerate(spans)
                   if low <= anchor < high), 0)
    rotated = spans[landed:] + spans[:landed]

    return [Piece(grid_start=grid, start=low, end=high,
                  chunk_rows=rows_per_chunk,
                  from_disk=any(a <= low and high <= b for a, b in ranges))
            for grid, low, high in rotated]


class Frontier:
    """The thread that walks a fill order and admits what it decodes."""

    def __init__(self, route, form: Form,
                 resident: ResidentStore, chunks: ChunkStore,
                 encode_queue: queue.Queue | None = None,
                 ledger: Ledger | None = None,
                 protected: set[tuple[int, str]] | None = None):
        self.route = route
        self.form = form
        self.resident = resident
        self.chunks = chunks
        self.encode_queue = encode_queue
        self.ledger = ledger
        self.protected = protected or set()
        self.pause = threading.Event()
        self.order: list[Piece] = []
        self.pos = -1
        self.from_disk = 0
        self.from_route = 0
        self.paused_s = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def launch(self, start: int, end: int, anchor: int) -> list[Piece]:
        """Start filling, and return the order it is going to work in."""
        self.order = fill_order(start, end, anchor, self.chunks.rows_per_chunk,
                                self.chunks.rows_held(self.form.key()))
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self.order

    def wait(self, timeout: float = 30.0) -> bool:
        """Block until the fill finishes on its own. True if it did.

        Distinct from `stop`, which asks it to give up. A caller that wants
        the whole window filled and reaches for `stop` gets whatever had been
        decoded by the time the request arrived, which is a race dressed up
        as an API.
        """
        if self._thread is None:
            return True
        self._thread.join(timeout=timeout)
        return not self._thread.is_alive()

    def stop(self, wait: bool = True, timeout: float = 15.0) -> None:
        self._stop.set()
        self.pause.clear()
        if self._thread is not None and wait:
            self._thread.join(timeout=timeout)
        self._thread = None

    def _wait_while_paused(self) -> None:
        if not self.pause.is_set():
            return
        start = time.perf_counter()
        while self.pause.is_set() and not self._stop.is_set():
            time.sleep(PAUSE_POLL_S)
        self.paused_s += time.perf_counter() - start

    def _run(self) -> None:
        activity = self.ledger.begin("fill", f"{len(self.order)} pieces") \
            if self.ledger else None
        try:
            for piece in self.order:
                if self._stop.is_set():
                    return
                if piece.from_disk and self._from_disk(piece):
                    continue
                self._from_route(piece)
        finally:
            if self.ledger and activity is not None:
                self.ledger.end(activity, f"{self.from_disk} read, "
                                          f"{self.from_route} decoded")

    def _from_disk(self, piece: Piece) -> bool:
        """Refill a piece from its chunk. False if the chunk let us down."""
        for row in range(piece.start, piece.end):
            if self._stop.is_set():
                return True
            self._wait_while_paused()
            frame = self.chunks.fetch(self.form.key(), row)
            if frame is None:
                return False        # vanished mid-read; re-derive it instead
            self.resident.put(self.form.key(), row, frame,
                              protected=self.protected)
            self.pos = row
            self.from_disk += 1
        return True

    def _from_route(self, piece: Piece) -> None:
        """Decode a piece from the source, admitting and buffering as it goes."""
        buffered: list[np.ndarray] = []
        for row in range(piece.start, piece.end):
            if self._stop.is_set():
                return
            self._wait_while_paused()
            answer = self.route.at(row)
            if answer is None:
                # a row that decodes to nothing breaks the run: a chunk is
                # written only when it is whole, and a chunk with a hole in it
                # would make the record's spans stop tiling
                return
            frame = build(answer[0], self.form)
            self.resident.put(self.form.key(), row, frame,
                              protected=self.protected)
            buffered.append(frame)
            self.pos = row
            self.from_route += 1
        if piece.whole and len(buffered) == piece.rows:
            if self.encode_queue is not None:
                self.encode_queue.put((self.form, piece.start, buffered))
            else:
                self.chunks.encode(self.form, piece.start, buffered)
