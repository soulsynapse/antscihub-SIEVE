"""The counters a worker pool exposes so its utilisation stops being a guess.

`mutual/shares.py` declares three worker pools, and until this module not one
of them could report whether its declared share fits the machine it is running
on — `DETECTOR_WORKERS`' own docstring calls itself "a judgement, not a
measurement", and the day someone profiles the pools competing is the day it
should change. This is the instrument that day needs: each pool accumulates the
time its workers spent working, and a sampler that reads the counter twice can
say what fraction of the interval the pool was busy.

**A counter, not a span — which is why this is not `bench/metrics.py`.** The
bus publishes one duration against one budget key, judged at publish; a pool's
busy time is a monotonic total that only a *difference* of two readings turns
into a number meaning anything, and the reader who differences it
(`gui/resource_probe.py`) also chooses the interval. The other reason is
layering: `decode/prefetch.py` sits below `bench` and may not import it, and a
pool that cannot name its own meter class would be back to duck-typed
callbacks.

**A raise still counts as busy**, which is the opposite of the bus's rule and
deliberate: `MetricBus.measure` publishes nothing for a block that raises,
because a truncated interval is not the interval the budget describes. Here the
quantity is occupancy, not achievement — a decode that failed after 20 ms held
a worker for 20 ms, and a pool that looked idle while its workers raised would
read as headroom that does not exist.

Thread contract: every method is safe from any thread. Workers add busy time
from their own threads, the depth gauge is written by whoever owns the queue,
and the sampler reads both from wherever it lives. One lock, held for
arithmetic only.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from threading import Lock
from time import perf_counter_ns

#: How the clock is read, injectable for `bench/metrics.py`'s reason: the
#: accumulation property worth testing cannot be stated against a real clock
#: without asserting on wall-clock timings, which is how a test becomes flaky.
Clock = Callable[[], int]


class PoolMeter:
    """Busy time and queue depth for one worker pool, read by a sampler.

    Owned by whoever outlives the pool, not by the pool itself: the preview's
    prefetch source is rebuilt per footage while its meter belongs to the
    runner, so the busy total stays monotonic across rebuilds and a sampler
    differencing two readings never sees the counter jump backwards.
    """

    def __init__(self, *, clock: Clock = perf_counter_ns) -> None:
        self._clock = clock
        self._lock = Lock()
        self._busy_ns = 0
        self._depth = 0

    @contextmanager
    def working(self) -> Generator[None]:
        """Account the block's duration as busy time, raise or return alike."""
        started = self._clock()
        try:
            yield
        finally:
            self.add_busy_ns(self._clock() - started)

    def add_busy_ns(self, ns: int) -> None:
        """Add an already-measured duration. `working` is the usual caller."""
        with self._lock:
            self._busy_ns += ns

    @property
    def busy_ns(self) -> int:
        """Total nanoseconds any worker spent working, since construction."""
        with self._lock:
            return self._busy_ns

    def set_depth(self, depth: int) -> None:
        """Declare how much work is currently waiting on the pool."""
        with self._lock:
            self._depth = depth

    @property
    def depth(self) -> int:
        """The queue as last declared — an instantaneous gauge, not a total."""
        with self._lock:
            return self._depth
