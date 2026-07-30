"""What the store has to be, given how the executor uses it.

Two claims. The pair `(key, index)` is the unit, so one computation's frames do
not collide and a partially-filled entry is an ordinary state rather than a
corrupt one — that is what lets a preview over a clip and a batch over the whole
video share keys. And `NullFrameStore` is a real store rather than a test
double: it is what "caching off" is, and it exists so the executor has no
`if store is not None` in it.
"""

from __future__ import annotations

import numpy as np

from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.cache import FrameStore, MemoryFrameStore, NullFrameStore


def frame(index: int) -> Frame:
    return Frame(
        data=np.full((4, 4), index, dtype=np.uint8), index=index, channels=ChannelSpec.GRAY
    )


def test_one_key_holds_a_frame_per_index() -> None:
    """Two frames of one computation are two entries, not one overwriting one.

    Keying by node key alone was the alternative, and it fails silently: the
    second frame of a run would replace the first, every lookup would hit, and
    every frame of a cached clip would be frame zero.
    """
    store = MemoryFrameStore()
    store.put("k", 10, frame(10))
    store.put("k", 11, frame(11))

    assert len(store) == 2
    assert store.get("k", 10) is not None
    assert store.get("k", 10).index == 10  # pyright: ignore[reportOptionalMemberAccess]
    assert store.get("k", 12) is None
    assert store.get("other", 10) is None


def test_the_null_store_satisfies_the_protocol_and_keeps_nothing() -> None:
    """ "No cache" is a store, so it is not a branch in the executor."""
    null = NullFrameStore()
    null.put("k", 10, frame(10))

    assert null.get("k", 10) is None
    assert isinstance(null, FrameStore)
    assert isinstance(MemoryFrameStore(), FrameStore)


def test_rewriting_an_entry_is_legal() -> None:
    """A caller cannot avoid it, so a store may not raise on it.

    Two replicates in one equivalence group resolve to identical parameters and
    identical ROIs, so they produce the same key and recompute the same entry.
    That is correct — they *are* one computation — and a store that treated the
    second write as a conflict would make the fan-out unrunnable.
    """
    store = MemoryFrameStore()
    store.put("k", 10, frame(10))
    store.put("k", 10, frame(10))

    assert len(store) == 1
    store.clear()
    assert len(store) == 0 and store.get("k", 10) is None


def test_a_bare_object_is_not_a_frame_store() -> None:
    """The protocol is runtime-checkable, so the check has to mean something."""
    assert not isinstance(object(), FrameStore)
