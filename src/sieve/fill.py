"""The landing sequence: fill a window into RAM so a seek inside it is free.

A fill opens its own source — sharing the foreground's would stall the drawing
thread behind the frontier's decode. Chunks are filled anchor-first (playhead's
chunk, then wrapping), so what the user sees lands before the rest. Persisted
chunks refill at cut speed; only complete chunks are written. A landing-stop is
fire-and-forget; a form-change stop must join, because old-form frames arriving
after the cache rebuilds are wrong pixels under a right key. The callback runs
on the fill thread; callers that draw must dispatch it themselves.
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

#: At most two fills read concurrently (dying + replacement); an open is expensive.
_READERS = 2


class Readers:
    """Opened sources a fill borrows, so a landing never pays an open."""

    def __init__(self, tool: Tool, address: str) -> None:
        self.tool = tool
        self.address = address
        self._free: list[Store] = []
        self._lock = threading.Lock()

    def borrow(self) -> Store:
        """A free reader, or a newly opened one. Blocks; call from the fill thread."""
        with self._lock:
            if self._free:
                return self._free.pop()
        store = opened(self.tool, self.address)
        # One, not the default: fill's frames go into the shared cache.
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
    """The encoder thread: complete chunks to disk, behind whatever filled them."""

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
        """Discard pending writes. The in-flight encode is unreachable here;
        ``ChunkStore.wipe`` handles it."""
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                return


class WindowFill:
    """Fill ordinals [start, end) of one form into a shared cache."""

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
        #: The *store's* hole set; a fill finds holes first and `int.add` is atomic.
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
        """Signal stop; ``wait=False`` for landing changes (harmless stale frames),
        ``True`` for form changes (old-form frames would be wrong pixels)."""
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
        """Decode the span ascending (one seek + steps, not N seeks). Returns
        (delivered, refused)."""
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
                    # Only GONE — LATER and FORM are transient, not permanent holes.
                    self.holes.add(position)
                continue    # a hole, or not to us now; either way not a chunk
            self.cache.put(position, self.form, answered.frame)
            buffer.append(answered.frame)
            self.at = ordinal
            delivered += 1
        if len(buffer) == cend - cstart and self.form.pix == "gray":
            # Complete + gray only; generation captured now so a queued encode
            # lands in the form it was filled for, not a later one.
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
                    # Short chunk — the whole span re-derives, not the tail.
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
    """The chunk-grid superset of *span* positions centred on *anchor*.

    Snapped to the chunk grid so overlapping windows share chunks.
    """
    start = max(0, min(anchor, listed - span))
    end = min(start + span, listed)
    low = start - start % CHUNK_FRAMES
    high = min(-(-end // CHUNK_FRAMES) * CHUNK_FRAMES, listed)
    return low, high
