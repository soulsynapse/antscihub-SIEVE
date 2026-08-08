"""The scrub cache's bookkeeping, and the equality the ledger's row cites.

`shares.PROXY_CACHE_SHARE` says its floor is this cache's own default, and the
player sizes the cache from `resolved_bytes` of that row rather than from the
default — so the two numbers being equal is arithmetic the ledger depends on
and code alone does not state. It is the first case below.

The rest is the cache's own bookkeeping, which the player exercises only
incidentally: a wrong eviction order or a byte count that drifts reads there as
a scrub that got slower, never as a red test.

Qt is imported inside the tests, for the reason `conftest.py` gives. `QImage`
needs no `QApplication`, so these do not take the `qapp` fixture.
"""

from __future__ import annotations

from typing import Any

#: Grayscale, and a width that is a multiple of four, so `sizeInBytes` is
#: `WIDTH * HEIGHT` exactly rather than that plus Qt's per-row padding — the
#: capacities below are written as whole multiples of a frame.
FRAME_WIDTH = 100
FRAME_HEIGHT = 100
FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT


def frame(width: int = FRAME_WIDTH, height: int = FRAME_HEIGHT) -> Any:
    from PySide6.QtGui import QImage

    image = QImage(width, height, QImage.Format.Format_Grayscale8)
    assert image.sizeInBytes() == width * height
    return image


def test_the_ledger_row_and_the_caches_default_are_the_same_number() -> None:
    """The claim `shares.py`'s comment makes about this file.

    `VideoPlayer` never passes `DEFAULT_CAPACITY_BYTES`; it passes
    `resolved_bytes(PROXY_CACHE_SHARE)`, whose floor is what a small machine
    gets. If the two drift, the default becomes a number no session ever uses
    and the comment beside it becomes false, both silently.
    """
    from sieve.gui.transport.proxy_cache import DEFAULT_CAPACITY_BYTES
    from sieve.mutual.shares import PROXY_CACHE_SHARE

    assert DEFAULT_CAPACITY_BYTES == PROXY_CACHE_SHARE.floor_bytes


def test_a_hit_spares_the_frame_it_hit_and_the_untouched_one_is_evicted() -> None:
    """Least-recently-*used*, not least-recently-inserted.

    This is the whole point of the cache: the frames worth keeping are the grid
    points the user keeps returning to, and insertion order alone would evict
    exactly those on a long drag.
    """
    from sieve.gui.transport.proxy_cache import ProxyFrameCache

    cache = ProxyFrameCache(capacity_bytes=2 * FRAME_BYTES)
    cache.put(0, frame())
    cache.put(1, frame())

    assert cache.get(0) is not None
    cache.put(2, frame())

    assert cache.get(1) is None
    assert cache.get(0) is not None
    assert cache.get(2) is not None


def test_one_admission_evicts_as_many_frames_as_it_takes_to_fit() -> None:
    """The eviction loop, which a single-eviction step would pass three of four.

    A proxy is sized by the display, so a viewport resize can put an image
    worth several of the frames already held; stopping after one eviction
    leaves the cache over its bound rather than under it.
    """
    from sieve.gui.transport.proxy_cache import ProxyFrameCache

    cache = ProxyFrameCache(capacity_bytes=3 * FRAME_BYTES)
    for index in range(3):
        cache.put(index, frame())

    cache.put(3, frame(height=2 * FRAME_HEIGHT))

    assert cache.bytes_used == 3 * FRAME_BYTES
    assert len(cache) == 2
    assert cache.get(0) is None
    assert cache.get(1) is None


def test_recaching_an_index_replaces_its_bytes_rather_than_adding_them() -> None:
    """The same frame index arrives again whenever a source is re-scrubbed.

    Counting the second copy on top of the first would make `bytes_used` climb
    without the cache holding anything more, and the cache would evict live
    frames to satisfy a number that was wrong.
    """
    from sieve.gui.transport.proxy_cache import ProxyFrameCache

    cache = ProxyFrameCache(capacity_bytes=4 * FRAME_BYTES)
    cache.put(7, frame())
    cache.put(7, frame())

    assert len(cache) == 1
    assert cache.bytes_used == FRAME_BYTES

    cache.clear()
    assert len(cache) == 0
    assert cache.bytes_used == 0


def test_a_recache_promotes_the_frame_the_way_a_hit_does() -> None:
    """Re-scrubbing warmed ground arrives as `put`, not as `get`.

    An `OrderedDict` assignment to a key already present keeps that key's
    position, so without the delete in `put` the frames the grid keeps
    returning to are the ones that lose their recency — the failure the LRU
    exists to prevent, on the path that triggers it most.
    """
    from sieve.gui.transport.proxy_cache import ProxyFrameCache

    cache = ProxyFrameCache(capacity_bytes=2 * FRAME_BYTES)
    cache.put(0, frame())
    cache.put(1, frame())

    cache.put(0, frame())
    cache.put(2, frame())

    assert cache.get(1) is None
    assert cache.get(0) is not None
    assert cache.get(2) is not None


def test_an_image_larger_than_the_whole_capacity_is_dropped_and_nothing_else_is() -> None:
    """Storing it would evict everything to hold one frame nobody asked to keep.

    Asserted on what survives, not on what was refused: the refusal is only
    worth having because the frames already warmed are still there afterwards.
    """
    from sieve.gui.transport.proxy_cache import ProxyFrameCache

    cache = ProxyFrameCache(capacity_bytes=2 * FRAME_BYTES)
    cache.put(0, frame())

    cache.put(1, frame(height=3 * FRAME_HEIGHT))

    assert cache.get(1) is None
    assert cache.get(0) is not None
    assert cache.bytes_used == FRAME_BYTES
