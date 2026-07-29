
















from __future__ import annotations

import pytest

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import MetricBus, Recorder, Sample



KEY = "slider_to_preview"
LIMIT_MS = BUDGETS[KEY].limit_ms


class FakeClock:






    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_a_subscribers_own_cost_stays_out_of_the_sample() -> None:







    clock = FakeClock()
    bus = MetricBus(clock=clock)
    seen: list[Sample] = []

    def slow_subscriber(sample: Sample) -> None:
        clock.advance(1.0)
        seen.append(sample)

    bus.subscribe(slow_subscriber)

    with bus.measure(KEY):
        clock.advance(0.030)

    assert [sample.elapsed_ms for sample in seen] == [30.0]


def test_the_bus_judges_the_miss_rather_than_the_caller() -> None:







    clock = FakeClock()
    bus = MetricBus(clock=clock)
    recorder = Recorder()
    bus.subscribe(recorder.record)

    with bus.measure(KEY):
        clock.advance(LIMIT_MS / 1000.0 * 3)
    with bus.measure(KEY):
        clock.advance(0.001)

    assert len(recorder.samples(KEY)) == 2
    assert [sample.key for sample in recorder.misses()] == [KEY]
    assert recorder.misses()[0].over_ms == pytest.approx(LIMIT_MS * 2)
    assert recorder.worst(KEY).elapsed_ms == pytest.approx(LIMIT_MS * 3)


def test_a_key_no_budget_knows_is_refused() -> None:







    bus = MetricBus(clock=FakeClock())

    with pytest.raises(KeyError):
        bus.publish("slider_to_preveiw", 1.0)

    with pytest.raises(KeyError), bus.measure("no_such_budget"):
        pass


def test_a_block_that_raised_publishes_nothing() -> None:






    clock = FakeClock()
    bus = MetricBus(clock=clock)
    recorder = Recorder()
    bus.subscribe(recorder.record)

    with pytest.raises(ValueError, match="halfway"):
        with bus.measure(KEY):
            clock.advance(0.010)
            raise ValueError("halfway through a render")

    assert len(recorder) == 0
    with pytest.raises(KeyError):
        recorder.median_ms(KEY)


def test_unsubscribing_stops_delivery_and_is_idempotent() -> None:






    clock = FakeClock()
    bus = MetricBus(clock=clock)
    recorder = Recorder()
    unsubscribe = bus.subscribe(recorder.record)

    bus.publish(KEY, 1.0)
    unsubscribe()
    unsubscribe()
    bus.publish(KEY, 2.0)

    assert [sample.elapsed_ms for sample in recorder.samples(KEY)] == [1.0]
