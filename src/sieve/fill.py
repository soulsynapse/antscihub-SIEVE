"""The landing sequence: fill a window into RAM so a seek inside it is free.

Ported from `experiments/storage-experiments/session-explorer.py`, the oracle
for this shelf. What it buys is measured on the footage in `video-tests/`: a
sequential read through the contract costs about 10 ms, and *every seek* costs
220-320 ms — a backward step is 321. So forward playback was never the freeze;
landing, scrubbing and stepping back are, and a window already in RAM turns
each of them into a dict touch.

**A fill reads through its own opened source.** `nodes.py` calls an `Opened`
one per address and not thread-safe, and `store.py` says a fill tier brings
its own — the second is the one that holds, and the first now says so. Two
opened sources on one address, read concurrently, were measured here: the
foreground stayed at 7.6 ms mean and 15 ms worst while a fill ran at 87 fps
beside it. Sharing one instead would put the drawing thread behind the
frontier's decode, which is the freeze this file exists to prevent.

**Attention-first, and the ordering is the whole point.** The same decode
work in a different order is the difference between a frozen landing and a
seamless one: the loop starts at the chunk the playhead is in and wraps, so
what the user is looking at arrives first and the rest arrives while they
look at it. Filling from the window's head instead is the same total time and
a landing that stares back.

**Chunks the store already holds refill at cut speed; the rest decode.** A
revisited window costs its own chunks and not the original
(`docs/findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md`: 10.3 ms
against 315.5). Only complete chunks are handed to the writer, because a
partial one on disk is indistinguishable from a whole one.

**Stopping has two speeds and the difference is the form.** A landing stops
the old fill without waiting: its last frames land in the same cache at the
same form, which is harmless. A form change must wait, because frames of the
old form arriving after the cache was rebuilt are wrong pixels under a right
key.

Nothing here imports Qt. The callback runs on the fill thread; a caller that
draws is responsible for getting it back to whatever thread it draws on.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable

from sieve.chunks import CHUNK_FRAMES, ChunkStore
from sieve.contract import Tool
from sieve.contract.forms import Form
from sieve.contract.nodes import Refusal
from sieve.store import Frames, Store, opened

#: Opened sources kept for lending. Two, because only a dying fill and the
#: one that replaced it are ever reading at once, and an open costs the whole
#: frame table (785 ms on the footage in `video-tests/`) — paying that per
#: landing is the cost this pool exists to not pay.
_READERS = 2


class Readers:
    """Opened sources a fill borrows, so a landing never pays an open.

    The explorer built a fetcher per fill and threw it away, which is right
    when an open is a container and wrong when it is ADR-0004's whole demux
    pass. Same lifetime as the source, and closed with it.
    """

    def __init__(self, tool: Tool, address: str) -> None:
        self.tool = tool
        self.address = address
        self._free: list[Store] = []
        self._lock = threading.Lock()

    def borrow(self) -> Store:
        """A free reader, or a newly opened one. Blocks for an open; call it
        from the fill thread, which is what it is for."""
        with self._lock:
            if self._free:
                return self._free.pop()
        store = opened(self.tool, self.address)
        #: one, not the default: the shared cache is where a fill's frames go,
        #: and a reader holding a second copy of the same window is the
        #: budget being spent twice on one form.
        store.frames.set_budget(1)
        return store

    def give_back(self, store: Store) -> None:
        with self._lock:
            if len(self._free) < _READERS:
                self._free.append(store)
                return
        store.close()

    def close(self) -> None:
        with self._lock:
            free, self._free = self._free, []
        for store in free:
            store.close()


class WriteBehind:
    """The encoder thread: complete chunks to disk, behind whatever filled them.

    A thread and not the fill's own work, because encoding a chunk takes about
    as long as filling one and a frontier that stopped to write would be half
    the frontier. The queue is the seam, and it is drained oldest-first so a
    window that landed earlier finishes writing first.
    """

    def __init__(self, chunks: ChunkStore) -> None:
        self.chunks = chunks
        self.queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            start, frames, form, generation = self.queue.get()
            try:
                self.chunks.encode(start, frames, form, generation)
            except Exception:   # noqa: BLE001 — a failed chunk re-derives
                pass

    def pending(self) -> int:
        return self.queue.qsize()

    def drain(self) -> None:
        """Throw away what has not been written. What a form change calls.

        The chunk being written right now is not reachable from here and is
        wiped instead — which is why `ChunkStore.wipe` tolerates a file it
        cannot unlink.
        """
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                return


class WindowFill:
    """Fill ordinals [start, end) of one form into a shared cache.

    Ordinals and not positions, because a chunk is a span of the store's
    listing and a pts difference is not a frame count — ADR-0004 admits the
    ordinal exactly here, as a per-store coordinate with the listing as the
    table that says what it means.
    """

    def __init__(
        self,
        positions: tuple[int, ...],
        start: int,
        end: int,
        anchor: int,
        form: Form,
        cache: Frames,
        chunks: ChunkStore,
        writer: WriteBehind,
        readers: Readers,
        on_covered: Callable[..., None] | None = None,
        holes: set[int] | None = None,
    ) -> None:
        self.positions = positions
        self.start, self.end = start, end
        self.anchor = max(start, min(anchor, end - 1))
        self.form = form
        self.cache = cache
        self.chunks = chunks
        self.writer = writer
        self.readers = readers
        self.on_covered = on_covered
        #: the coverage record to write holes into — the *store's*, not this
        #: reader's. A hole is a fact about the recording and not about who
        #: found it, and a fill walking a cut-away prefix is usually who finds
        #: it first: twenty positions at ~273 ms apiece on the footage in
        #: `video-tests/`, which the drawing thread would otherwise re-pay one
        #: at a time. A set of ints is safe to share — `add` is one bytecode.
        self.holes = holes
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        #: how far it has got, for whoever draws a progress line
        self.at = start

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def launch(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        """`wait=False` signals and returns: the dying frontier's last frames
        land in the same cache at the same form, which is harmless. Only a
        form change must actually wait, because after one the same key means
        different pixels."""
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and wait:
            thread.join(timeout=15)

    # -- the frontier ------------------------------------------------------

    def _order(self) -> list[int]:
        """Chunk starts, the anchor's first, wrapping to the window's head."""
        starts = list(range(self.start, self.end, CHUNK_FRAMES))
        if not starts:
            return []
        first = min((self.anchor - self.start) // CHUNK_FRAMES, len(starts) - 1)
        return starts[first:] + starts[:first]

    def _from_chunks(self, cstart: int, cend: int) -> int:
        """Refill a persisted chunk. Returns how many landed; short means the
        chunk was not all there and the span re-derives below."""
        landed = 0
        for ordinal in range(cstart, cend):
            if self._stop.is_set():
                return landed
            array = self.chunks.fetch(ordinal)
            if array is None:
                return landed
            self.cache.put(self.positions[ordinal], self.form, array)
            self.at = ordinal
            landed += 1
        return landed

    def _from_source(self, reader: Store, cstart: int, cend: int) -> tuple[int, int]:
        """Decode the span. Returns (delivered, refused).

        Ascending, which is what makes it cheap: the source steps its decoder
        forward for a request within a GOP of its cursor and seeks otherwise,
        so a chunk costs one seek and ninety-five steps rather than
        ninety-six seeks (`docs/findings/2026.08.21-uncut-seek-costs-a-gop-\
not-a-frame.md`).
        """
        buffer: list[Any] = []
        delivered = refused = 0
        for ordinal in range(cstart, cend):
            if self._stop.is_set():
                break
            position = self.positions[ordinal]
            answered = reader.answer(position, self.form)
            if not answered.delivered:
                refused += 1
                if answered.refusal is Refusal.GONE and self.holes is not None:
                    # Only GONE. `LATER` is a moment and `FORM` is about the
                    # shape asked for; filing either would answer the same way
                    # forever on the strength of one instant — `store.py` keeps
                    # the same line and for the same reason.
                    self.holes.add(position)
                continue    # a hole, or not to us now; either way not a chunk
            self.cache.put(position, self.form, answered.frame)
            buffer.append(answered.frame)
            self.at = ordinal
            delivered += 1
        if len(buffer) == cend - cstart and self.form.pix == "gray":
            # complete chunks only: a short one on disk answers for positions
            # it never held. Gray only, because that is what a chunk is
            # written from — see `ChunkStore.encode`. The generation is taken
            # now and not at encode time: if the form changes while this sits
            # in the queue, it must land where the new form will not find it.
            self.writer.queue.put(
                (cstart, buffer, self.form, self.chunks.generation)
            )
        return delivered, refused

    def _run(self) -> None:
        began = time.perf_counter()
        persisted = self.chunks.persisted()
        from_chunks = from_source = refused = 0
        reader: Store | None = None
        try:
            for cstart in self._order():
                if self._stop.is_set():
                    return
                cend = min(cstart + CHUNK_FRAMES, self.end)
                if cstart in persisted:
                    landed = self._from_chunks(cstart, cend)
                    from_chunks += landed
                    if landed == cend - cstart:
                        continue
                    # The chunk was short — wiped under us, or never whole.
                    # The *whole* span re-derives, not the tail: a chunk is
                    # the unit of persistence, and one written from a partial
                    # span would sit on disk under a start no reader computes.
                if reader is None:
                    reader = self.readers.borrow()
                got, missed = self._from_source(reader, cstart, cend)
                from_source += got
                refused += missed
            if self._stop.is_set() or self.on_covered is None:
                return
            self.on_covered(
                self.start,
                time.perf_counter() - began,
                from_chunks,
                from_source,
                refused,
            )
        finally:
            if reader is not None:
                self.readers.give_back(reader)


def window_for(anchor: int, span: int, listed: int) -> tuple[int, int]:
    """The chunk-grid superset of *span* positions starting at *anchor*.

    The window the user asked for is exactly the span they clicked; the range
    that gets *filled* is snapped out to the chunk grid, because chunks live
    on the store's absolute ordinals and a window must not bend the grid to
    itself — two windows overlapping would otherwise write two chunk sets
    over the same positions and share neither.
    """
    start = max(0, min(anchor, listed - span))
    end = min(start + span, listed)
    low = start - start % CHUNK_FRAMES
    high = min(-(-end // CHUNK_FRAMES) * CHUNK_FRAMES, listed)
    return low, high
