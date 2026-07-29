

from __future__ import annotations

import pytest
from PySide6.QtGui import QImage

from sieve.core.shares import PROXY_CACHE_SHARE
from sieve.gui.proxy_cache import DEFAULT_CAPACITY_BYTES, ProxyFrameCache

pytestmark = pytest.mark.gui


def test_the_default_capacity_is_the_ledger_floor() -> None:






    assert PROXY_CACHE_SHARE.floor_bytes == DEFAULT_CAPACITY_BYTES


def image(width: int = 100, height: int = 100) -> QImage:

    return QImage(width, height, QImage.Format.Format_BGR888)


@pytest.fixture
def frame_bytes(qapp: object) -> int:
    del qapp
    return image().sizeInBytes()


class TestBasics:
    def test_a_miss_returns_none(self, qapp: object) -> None:
        del qapp
        assert ProxyFrameCache().get(7) is None

    def test_a_stored_frame_comes_back(self, qapp: object) -> None:
        del qapp
        cache = ProxyFrameCache()
        stored = image()
        cache.put(7, stored)
        assert cache.get(7) is stored

    def test_clear_empties_it(self, qapp: object) -> None:
        del qapp
        cache = ProxyFrameCache()
        cache.put(1, image())
        cache.clear()
        assert len(cache) == 0
        assert cache.bytes_used == 0
        assert cache.get(1) is None

    def test_re_putting_an_index_does_not_double_count(self, frame_bytes: int) -> None:
        cache = ProxyFrameCache()
        cache.put(1, image())
        cache.put(1, image())
        assert len(cache) == 1
        assert cache.bytes_used == frame_bytes


class TestEviction:
    def test_it_evicts_to_stay_within_capacity(self, frame_bytes: int) -> None:
        cache = ProxyFrameCache(capacity_bytes=frame_bytes * 3)
        for index in range(5):
            cache.put(index, image())
        assert len(cache) == 3
        assert cache.bytes_used <= frame_bytes * 3

    def test_it_evicts_the_least_recently_used(self, frame_bytes: int) -> None:
        cache = ProxyFrameCache(capacity_bytes=frame_bytes * 2)
        cache.put(1, image())
        cache.put(2, image())
        cache.get(1)
        cache.put(3, image())
        assert cache.get(1) is not None
        assert cache.get(2) is None
        assert cache.get(3) is not None

    def test_an_oversized_frame_is_dropped_rather_than_emptying_the_cache(
        self, frame_bytes: int
    ) -> None:
        cache = ProxyFrameCache(capacity_bytes=frame_bytes * 2)
        cache.put(1, image())
        cache.put(2, image(1000, 1000))
        assert cache.get(2) is None
        assert cache.get(1) is not None
