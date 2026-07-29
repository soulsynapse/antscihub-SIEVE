
























from __future__ import annotations

from collections import OrderedDict

from PySide6.QtGui import QImage



DEFAULT_CAPACITY_BYTES = 96 * 1024 * 1024


class ProxyFrameCache:


    def __init__(self, capacity_bytes: int = DEFAULT_CAPACITY_BYTES) -> None:
        self._capacity_bytes = capacity_bytes
        self._entries: OrderedDict[int, QImage] = OrderedDict()
        self._bytes = 0

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def bytes_used(self) -> int:

        return self._bytes

    def get(self, index: int) -> QImage | None:

        image = self._entries.get(index)
        if image is None:
            return None
        self._entries.move_to_end(index)
        return image

    def put(self, index: int, image: QImage) -> None:






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

        self._entries.clear()
        self._bytes = 0

    def _evict_to_capacity(self) -> None:
        while self._bytes > self._capacity_bytes and self._entries:
            _, evicted = self._entries.popitem(last=False)
            self._bytes -= evicted.sizeInBytes()
