









from __future__ import annotations

import numpy as np

from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.cache import FrameStore, MemoryFrameStore, NullFrameStore


def frame(index: int) -> Frame:
    return Frame(
        data=np.full((4, 4), index, dtype=np.uint8), index=index, channels=ChannelSpec.GRAY
    )


def test_one_key_holds_a_frame_per_index() -> None:






    store = MemoryFrameStore()
    store.put("k", 10, frame(10))
    store.put("k", 11, frame(11))

    assert len(store) == 2
    assert store.get("k", 10) is not None
    assert store.get("k", 10).index == 10
    assert store.get("k", 12) is None
    assert store.get("other", 10) is None


def test_the_null_store_satisfies_the_protocol_and_keeps_nothing() -> None:

    null = NullFrameStore()
    null.put("k", 10, frame(10))

    assert null.get("k", 10) is None
    assert isinstance(null, FrameStore)
    assert isinstance(MemoryFrameStore(), FrameStore)


def test_rewriting_an_entry_is_legal() -> None:







    store = MemoryFrameStore()
    store.put("k", 10, frame(10))
    store.put("k", 10, frame(10))

    assert len(store) == 1
    store.clear()
    assert len(store) == 0 and store.get("k", 10) is None


def test_a_bare_object_is_not_a_frame_store() -> None:

    assert not isinstance(object(), FrameStore)
