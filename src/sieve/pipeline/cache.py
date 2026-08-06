"""Where a computed frame is kept so it is not computed twice.

**Keyed by `(node key, source frame index)`, not by node key alone.** A node's
key identifies a computation; one run of that computation produces a frame per
source frame, and the span they cover is a property of the run rather than of
the key — a preview over a five-second clip and a batch over the whole video
share every key and cover different frames. Keying by the pair means a partial
entry is an ordinary state rather than a corrupt one: a lookup that misses is
answered by computing that frame, and nothing has to record what an entry
covers or reason about whether it covers enough.

The index is the *source* frame index throughout, which is why `Frame.index`
being authoritative matters here as much as it does in `cache_key.py`. Two runs
of one computation number their outputs the same way or they are not one
computation.

**No eviction, and that is a deferral rather than a decision.** `SCAFFOLD`
calls this memory-resident during tuning, and what a tuning session actually
holds is a measurement nobody has taken — a bound picked now would be picked
from nothing, and `pipeline/materialize.py` is where spilling to Zarr belongs
anyway. What exists now is the protocol, so the executor is written against the
thing that will grow the policy rather than against a `dict` it would have to be
rewritten off.

**The protocol is the point of this module.** The executor takes a `FrameStore`
and never a concrete class, so a GUI holding a bounded store, a CLI holding an
unbounded one, and a test holding a recording one are the same execution path
with a different argument. That is what keeps "one executor" true against the
pressure that would otherwise produce a second one.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sieve.core.types import Frame, FrameIndex


@runtime_checkable
class FrameStore(Protocol):
    """Somewhere a computed frame can be put and later found.

    Deliberately two methods. A `Mapping`-shaped interface would drag in
    iteration and length, and both are questions a store that spills to disk
    cannot answer cheaply — nor does anything need to ask them, because a
    lookup is always for a key the caller already computed.
    """

    def get(self, key: str, index: int | FrameIndex) -> Frame | None:
        """The stored output of `key` at source frame `index`, or `None`.

        `None` rather than a raise: a miss is the ordinary case on the first
        run of anything, and an exception for it would make the executor's hot
        path a `try` block.
        """
        ...

    def put(self, key: str, index: int | FrameIndex, frame: Frame) -> None:
        """Store `frame` as the output of `key` at source frame `index`.

        Overwriting is legal and means nothing changed: the same key at the
        same index is by construction the same computation over the same input,
        so a store may keep the first, keep the last, or refuse to grow. What it
        may not do is raise, because a caller cannot avoid the case — two
        replicates in one equivalence group compute identical entries.
        """
        ...


class MemoryFrameStore:
    """The whole cache in a dict, for one process, for as long as it lives.

    Sufficient for tuning, which is the only thing that exists to use it, and
    honest about what it is not: nothing here is bounded, shared between
    processes, or persistent. A run over a full-length video with a checkpoint
    on every node will exhaust memory, and the answer to that is
    `materialize.py` rather than a heuristic here.
    """

    def __init__(self) -> None:
        self._frames: dict[tuple[str, FrameIndex], Frame] = {}

    def __len__(self) -> int:
        """Entries held. For tests and for a HUD, not for the executor."""
        return len(self._frames)

    def get(self, key: str, index: int | FrameIndex) -> Frame | None:
        """The stored output of `key` at source frame `index`, or `None`."""
        return self._frames.get((key, FrameIndex.of(index)))

    def put(self, key: str, index: int | FrameIndex, frame: Frame) -> None:
        """Store `frame` as the output of `key` at source frame `index`."""
        self._frames[(key, FrameIndex.of(index))] = frame

    def clear(self) -> None:
        """Drop everything. What "clear the cache" in the GUI will call."""
        self._frames.clear()


class NullFrameStore:
    """A store that keeps nothing, so every lookup misses.

    Not a test double — it is what a run with caching disabled uses, and it is
    also what makes "no cache" not a branch in the executor. An `if store is
    not None` around every lookup would be a second execution path through the
    one function that may not have one.
    """

    def get(self, key: str, index: int | FrameIndex) -> Frame | None:
        """Always `None`."""
        return None

    def put(self, key: str, index: int | FrameIndex, frame: Frame) -> None:
        """Discards `frame`."""
