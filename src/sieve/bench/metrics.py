









































from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from statistics import median
from threading import Lock
from time import perf_counter

from sieve.bench.budgets import BUDGETS, Budget





Subscriber = Callable[["Sample"], None]





Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class Sample:







    budget: Budget
    elapsed_ms: float






    detail: str = ""

    @property
    def key(self) -> str:

        return self.budget.key

    @property
    def over_ms(self) -> float:

        return self.budget.exceeded_by(self.elapsed_ms)

    @property
    def within_budget(self) -> bool:

        return self.over_ms <= 0.0


class MetricBus:










    def __init__(self, *, clock: Clock = perf_counter) -> None:
        self._clock = clock
        self._subscribers: tuple[Subscriber, ...] = ()





        self._lock = Lock()



    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:









        with self._lock:
            self._subscribers = (*self._subscribers, subscriber)
        return lambda: self._unsubscribe(subscriber)

    def _unsubscribe(self, subscriber: Subscriber) -> None:





        with self._lock:
            remaining = list(self._subscribers)
            if subscriber in remaining:
                remaining.remove(subscriber)
                self._subscribers = tuple(remaining)



    def publish(self, key: str, elapsed_ms: float, *, detail: str = "") -> Sample:











        sample = Sample(budget=BUDGETS[key], elapsed_ms=elapsed_ms, detail=detail)
        for subscriber in self._subscribers:
            subscriber(sample)
        return sample

    @contextmanager
    def measure(self, key: str) -> Generator[None]:


















        started = self._clock()
        yield
        elapsed = self._clock() - started
        self.publish(key, elapsed * 1000.0)


class Recorder:









    def __init__(self) -> None:
        self._samples: dict[str, list[Sample]] = {}

    def record(self, sample: Sample) -> None:

        self._samples.setdefault(sample.key, []).append(sample)

    def __len__(self) -> int:

        return sum(len(samples) for samples in self._samples.values())

    @property
    def keys(self) -> tuple[str, ...]:

        return tuple(self._samples)

    def samples(self, key: str) -> Sequence[Sample]:

        return tuple(self._samples.get(key, ()))

    def median_ms(self, key: str) -> float:













        samples = self._samples.get(key)
        if not samples:
            raise KeyError(f"nothing was recorded under {key!r}")
        return median(sample.elapsed_ms for sample in samples)

    def worst(self, key: str) -> Sample:





        samples = self._samples.get(key)
        if not samples:
            raise KeyError(f"nothing was recorded under {key!r}")
        return max(samples, key=lambda sample: sample.elapsed_ms)

    def misses(self) -> tuple[Sample, ...]:






        return tuple(
            sample
            for samples in self._samples.values()
            for sample in samples
            if not sample.within_budget
        )

    def clear(self) -> None:

        self._samples.clear()






METRICS = MetricBus()
