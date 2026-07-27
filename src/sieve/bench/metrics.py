"""The metric collection bus: where a timed interval goes and who hears it.

`budgets.py` declares eleven latency ceilings. Until this module, none of them
could be checked by anything, because nothing in the repo emitted a timing — and
rule 4 says a budget miss is a defect, which a budget nothing can miss is not.
This is the one place a duration is published and the one place a consumer
subscribes, so that adding a check means adding a subscriber rather than
threading a callback through the executor.

Four of the eleven still have no publisher anywhere in `src/`. That gap is
declared in `budgets.WITHOUT_PRODUCER` and held to a list that only shrinks by
`tests/bench/test_budget_producers.py`, because a ceiling nothing measures reads
as a ceiling being met.

Qt-free, and the `headless` contract in `.importlinter` enforces it. The QObject
that re-emits these as signals is `gui/executor_adapter.py`, one layer up, and
it is the only thing in the repo that will know both this and Qt.

**A span, not a counter.** Every budget in the table is a duration between two
named events, so what is published is `(key, elapsed_ms)` and never a gauge a
consumer would have to difference. The arithmetic is `measure`'s, once, rather
than each call site's `perf_counter` bookkeeping — which is the arithmetic the
budget keys exist to standardise. It also means a miss is detectable *by the
bus*: `Sample.over_ms` is computed against `BUDGETS[key]` on the way past, so no
call site has to remember to ask whether the thing it just timed was allowed to
take that long.

**Keys are the budget table's keys, and an unknown one is refused.** The
alternative is a free-form string namespace in which `slider_to_preview` and
`slider__to_preview` are both valid and only one of them is ever checked. A
typo that silently produces an unwatched metric is the failure this costs one
dict lookup to close.

**Subscription may not cost the thing it measures.** The bus sits inside a
100 ms budget. `measure` therefore reads the clock as the *first* statement
after the block and dispatches to subscribers afterwards, so a subscriber that
formats a string, takes a lock, or repaints a HUD is charged to the caller's
wall clock but never to the sample. `tests/unit/test_metrics.py` pins that with
a subscriber that advances a fake clock: without the ordering, the sample would
carry the subscriber's own cost and every consumer would be measuring itself.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from statistics import median
from threading import Lock
from time import perf_counter

from sieve.bench.budgets import BUDGETS, Budget

#: What a consumer is handed. Called on the publishing thread — the executor's
#: worker, the GUI thread, a CLI's main — so a subscriber that needs to be
#: somewhere else is responsible for getting there. `executor_adapter` doing
#: exactly that (a queued signal emission) is why the bus does not try.
Subscriber = Callable[["Sample"], None]

#: How the clock is read. Injectable for one reason: the ordering property this
#: module is built around — subscriber cost outside the sample — cannot be
#: stated against a real clock without asserting on wall-clock timings, which is
#: how a test becomes flaky on a loaded machine.
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class Sample:
    """One measured interval, already judged against its budget.

    Carries the `Budget` rather than only its key so a subscriber can report
    the human label and the ceiling without importing the table and looking it
    up again — the lookup happened once, here, at publish.
    """

    budget: Budget
    elapsed_ms: float

    @property
    def key(self) -> str:
        """The budget key this interval was published under."""
        return self.budget.key

    @property
    def over_ms(self) -> float:
        """Milliseconds over the ceiling; zero or negative when within it."""
        return self.budget.exceeded_by(self.elapsed_ms)

    @property
    def within_budget(self) -> bool:
        """Whether this interval met its ceiling."""
        return self.over_ms <= 0.0


class MetricBus:
    """Publishers on one side, subscribers on the other, nothing in between.

    Deliberately not a registry of named timers a caller starts and stops. A
    timer object outlives the interval it measures and can be leaked, stopped
    twice, or stopped by the wrong thread; a context manager cannot. `measure`
    is therefore the only intended way to produce a sample, and `publish` exists
    for the case where the number was already computed for some other reason —
    `gui/player.py`'s scrub round trip, which `ScrubPolicy` needs anyway.
    """

    def __init__(self, *, clock: Clock = perf_counter) -> None:
        self._clock = clock
        self._subscribers: tuple[Subscriber, ...] = ()
        # Guards replacement of the tuple above, not iteration of it. Publishing
        # reads the attribute once and walks that snapshot, so a subscribe from
        # the GUI thread during an executor's publish cannot mutate a sequence
        # mid-iteration and cannot make the publisher wait on a lock inside a
        # measured interval.
        self._lock = Lock()

    # ---- consumers -------------------------------------------------------

    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:
        """Deliver every future sample to `subscriber`.

        Returns:
            A callable that unsubscribes. Returned rather than requiring the
            caller to keep the function around and pass it back, because the
            common subscriber is a bound method or a closure and comparing those
            for identity later is a footgun — `Recorder().record` is a different
            object every time it is accessed.
        """
        with self._lock:
            self._subscribers = (*self._subscribers, subscriber)
        return lambda: self._unsubscribe(subscriber)

    def _unsubscribe(self, subscriber: Subscriber) -> None:
        """Drop the first registration of `subscriber`, if it is still there.

        Idempotent: calling the handle twice is not an error, because the second
        call is what a `finally` and an explicit teardown both look like.
        """
        with self._lock:
            remaining = list(self._subscribers)
            if subscriber in remaining:
                remaining.remove(subscriber)
                self._subscribers = tuple(remaining)

    # ---- publishers ------------------------------------------------------

    def publish(self, key: str, elapsed_ms: float) -> Sample:
        """Announce that `key`'s interval took `elapsed_ms`.

        Returns the sample so a caller that wants the verdict — over budget or
        not — has it without subscribing to its own publication.

        Raises:
            KeyError: if `key` is not in `BUDGETS`. See the module docstring:
                an unrecognised key is a metric nothing will ever check.
        """
        sample = Sample(budget=BUDGETS[key], elapsed_ms=elapsed_ms)
        for subscriber in self._subscribers:
            subscriber(sample)
        return sample

    @contextmanager
    def measure(self, key: str) -> Generator[None]:
        """Time the block and publish it as `key`.

        The clock is read before the budget is looked up and before any
        subscriber runs, so what is published is the block and nothing else.
        Nesting is fine — the start time is a local, not bus state — which is
        what lets a `full_preview_render` span contain the `slider_to_preview`
        spans it is made of.

        A block that raises publishes nothing. An interval that ended in an
        exception did not measure the thing the budget is about; recording it
        would put a truncated duration into the same series as the successful
        ones and quietly improve the median.

        Raises:
            KeyError: if `key` is not in `BUDGETS`, raised on the way out
                alongside whatever the block did. Checking on the way in would
                be earlier — and would put a dict lookup inside the interval.
        """
        started = self._clock()
        yield
        elapsed = self._clock() - started
        self.publish(key, elapsed * 1000.0)


class Recorder:
    """A subscriber that keeps what it hears, grouped by key.

    What a benchmark and a `--timings` flag both want and what neither should
    write for itself: a run produces many samples per key and the number that
    means anything is a median over them, not the last one. Not thread-safe on
    purpose — a consumer collecting across threads wants a queue, and pretending
    a list is one would hide that.
    """

    def __init__(self) -> None:
        self._samples: dict[str, list[Sample]] = {}

    def record(self, sample: Sample) -> None:
        """Subscriber entry point. Pass this to `MetricBus.subscribe`."""
        self._samples.setdefault(sample.key, []).append(sample)

    def __len__(self) -> int:
        """Total samples held, across every key."""
        return sum(len(samples) for samples in self._samples.values())

    @property
    def keys(self) -> tuple[str, ...]:
        """Budget keys anything was recorded under, in first-seen order."""
        return tuple(self._samples)

    def samples(self, key: str) -> Sequence[Sample]:
        """Everything recorded under `key`, in arrival order. Empty if none."""
        return tuple(self._samples.get(key, ()))

    def median_ms(self, key: str) -> float:
        """Median interval recorded under `key`.

        Median rather than mean, matching `test_perf_regression.py`: one
        pathological sample — a page fault, a GC pause, a scheduler decision —
        should not be able to fail a gate, and the thing a budget describes is
        the typical interaction rather than the worst one ever observed.

        Raises:
            KeyError: if nothing was recorded under `key`. A gate asserting on
                an empty series would pass vacuously, which is the failure
                `noxfile.py`'s `benchmark` session already refuses at the
                collection level.
        """
        samples = self._samples.get(key)
        if not samples:
            raise KeyError(f"nothing was recorded under {key!r}")
        return median(sample.elapsed_ms for sample in samples)

    def worst(self, key: str) -> Sample:
        """The slowest sample recorded under `key`.

        Raises:
            KeyError: if nothing was recorded under `key`.
        """
        samples = self._samples.get(key)
        if not samples:
            raise KeyError(f"nothing was recorded under {key!r}")
        return max(samples, key=lambda sample: sample.elapsed_ms)

    def misses(self) -> tuple[Sample, ...]:
        """Every recorded sample that exceeded its budget, in arrival order.

        The whole reason the bus judges at publish rather than leaving it to
        each consumer: this is one filter over what arrived, not a second
        lookup of the table by a second piece of code that could disagree.
        """
        return tuple(
            sample
            for samples in self._samples.values()
            for sample in samples
            if not sample.within_budget
        )

    def clear(self) -> None:
        """Drop everything. What a per-run consumer calls between runs."""
        self._samples.clear()


#: The process-wide bus. A default rather than a requirement: every publisher
#: and every consumer takes a `MetricBus`, so a test — and a second concurrent
#: run — can hold its own and hear only itself. This exists so that the ordinary
#: case is not each front end constructing and threading one.
METRICS = MetricBus()
