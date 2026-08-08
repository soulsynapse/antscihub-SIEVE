"""A bounded LRU of decoded display proxies, keyed by frame index.

Named for the proxy rather than for the frame because `pipeline/cache.py` is
also a frame cache and the two are unrelated objects. This one holds what the
viewport is currently showing, keyed by *where in the video* it came from, and
is discarded when the source closes; that one holds what a tool computed, keyed
by *what computation produced it*, and is the thing that makes a rerun cheap. A
name that said only "frame cache" would leave the difference to be rediscovered
at every call site.

This exists to make coarse scrubbing cost nothing. Snapping drag targets to a
grid is only a win if the grid points stop being decoded after the first pass,
and that is what this provides: the expensive part of showing a frame is the
container seek, and a cache hit does not seek.

Bounded by bytes rather than by count, and sized from the ledger rather than
from a number here — `mutual/shares.PROXY_CACHE_SHARE` is this cache's row, and
its floor is the default below. A count-based cap would be a memory ceiling
that moves when the user changes the proxy width.

Playback frames are deliberately *not* cached by the player. Playback walks the
whole timeline and would evict everything a scrub had warmed, which is exactly
backwards — the frames worth keeping are the ones the user returned to.
"""

from __future__ import annotations

from collections import OrderedDict

from PySide6.QtGui import QImage

#: Ceiling on retained frames. ~35 proxy frames at 1280x720, which covers a
#: coarse grid over several minutes of source without being a memory footgun.
#: Equal to `PROXY_CACHE_SHARE.floor_bytes` by construction.
DEFAULT_CAPACITY_BYTES = 96 * 1024 * 1024


class ProxyFrameCache:
    """Least-recently-used cache of display-proxy `QImage` by frame index."""

    def __init__(self, capacity_bytes: int = DEFAULT_CAPACITY_BYTES) -> None:
        self._capacity_bytes = capacity_bytes
        self._entries: OrderedDict[int, QImage] = OrderedDict()
        self._bytes = 0

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def bytes_used(self) -> int:
        """Total size of the retained images."""
        return self._bytes

    def get(self, index: int) -> QImage | None:
        """Return the cached frame at `index`, marking it most recently used."""
        image = self._entries.get(index)
        if image is None:
            return None
        self._entries.move_to_end(index)
        return image

    def put(self, index: int, image: QImage) -> None:
        """Cache `image` under `index`, evicting the oldest frames if needed.

        An image larger than the whole capacity is dropped rather than stored
        and immediately evicted, which would empty the cache to hold one frame
        nobody asked to keep.
        """
        size = image.sizeInBytes()
        if size > self._capacity_bytes:
            return

        if index in self._entries:
            self._bytes -= self._entries[index].sizeInBytes()
            del self._entries[index]

        self._entries[index] = image
        self._bytes += size
        self._evict_to_capacity()

    def clear(self) -> None:
        """Drop everything. Called when the source changes."""
        self._entries.clear()
        self._bytes = 0

    def _evict_to_capacity(self) -> None:
        while self._bytes > self._capacity_bytes and self._entries:
            _, evicted = self._entries.popitem(last=False)
            self._bytes -= evicted.sizeInBytes()
