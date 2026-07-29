from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from threading import Lock
from time import perf_counter_ns


Clock = Callable[[], int]


class PoolMeter:
    def __init__(self, *, clock: Clock = perf_counter_ns) -> None:
        self._clock = clock
        self._lock = Lock()
        self._busy_ns = 0
        self._depth = 0

    @contextmanager
    def working(self) -> Generator[None]:
        started = self._clock()
        try:
            yield
        finally:
            self.add_busy_ns(self._clock() - started)

    def add_busy_ns(self, ns: int) -> None:
        with self._lock:
            self._busy_ns += ns

    @property
    def busy_ns(self) -> int:
        with self._lock:
            return self._busy_ns

    def set_depth(self, depth: int) -> None:
        with self._lock:
            self._depth = depth

    @property
    def depth(self) -> int:
        with self._lock:
            return self._depth
