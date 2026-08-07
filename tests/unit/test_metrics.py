"""The four things the bus can get wrong that nothing downstream would notice.

Each of these fails for a distinct real reason. **Subscriber cost inside the
sample** makes every consumer measure itself, and the symptom is a budget that
gets harder to meet the more things are watching it — which reads as the code
being slow. **A miss the bus does not flag** pushes the budget lookup back out
to every call site, which is what having keys was for. **An unknown key
accepted** is a metric that exists and is never checked, indistinguishable from
one that is passing. **A raised block publishing anyway** puts truncated
intervals into the same series as the real ones and improves the median.

The clock is injected throughout. The ordering property above is about what is
*inside* an interval, and stating it against `perf_counter` would mean asserting
on wall-clock numbers — a test that fails on a loaded CI box and tells you
nothing about the ordering it was written for.
"""

from __future__ import annotations

import pytest

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import MetricBus, Recorder, Sample

#: Any real key does; this one is the tightest in-pipeline ceiling and so is
#: the one the ordering property actually matters for.
KEY = "slider_to_preview"
LIMIT_MS = BUDGETS[KEY].limit_ms


class FakeClock:
    """A clock that only moves when something moves it.

    Seconds, like `perf_counter`, because the bus multiplies by 1000 on the way
    out and a test that fed it milliseconds would agree with a broken bus.
    """

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_a_subscribers_own_cost_stays_out_of_the_sample() -> None:
    """The clock is read before dispatch, so watching does not charge the watched.

    The subscriber here advances the clock by ten times the budget, standing in
    for a HUD repaint or a lock. If `measure` read the clock after dispatching,
    the sample would be 1000 ms and this budget would be unmeetable by anything
    that anyone was looking at.
    """
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
    """A subscriber learns a budget was missed without consulting the table.

    Not decoration: the point of publishing against `BUDGETS` keys is that the
    comparison happens once, on the way past. A `Sample` that carried only a
    duration would put a second copy of the lookup in every consumer, and the
    copy that drifted would be the one nobody was reading.
    """
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
    """A typo is a metric that exists and is checked by nothing.

    The failure mode without this is entirely silent: `slider_to_preveiw`
    publishes happily, a subscriber records it under its own name, and the
    budget it was meant to report against stays at zero samples — which reads
    the same as a budget that is never exceeded.
    """
    bus = MetricBus(clock=FakeClock())

    with pytest.raises(KeyError):
        bus.publish("slider_to_preveiw", 1.0)

    with pytest.raises(KeyError), bus.measure("no_such_budget"):
        pass


def test_a_block_that_raised_publishes_nothing() -> None:
    """An interval that ended in an exception did not measure the budget's thing.

    Recording it would fold a truncated duration into the same series as the
    successful renders and quietly pull the median down — the one direction of
    error a latency gate cannot detect, because it looks like an improvement.
    """
    clock = FakeClock()
    bus = MetricBus(clock=clock)
    recorder = Recorder()
    bus.subscribe(recorder.record)

    with pytest.raises(ValueError, match="halfway"):  # noqa: SIM117 - the two are not one block
        with bus.measure(KEY):
            clock.advance(0.010)
            raise ValueError("halfway through a render")

    assert len(recorder) == 0
    with pytest.raises(KeyError):
        recorder.median_ms(KEY)


def test_unsubscribing_stops_delivery_and_is_idempotent() -> None:
    """The handle is what a GUI closing a HUD calls, possibly twice.

    Twice because a teardown and a `finally` are both correct places to call it
    and neither can see the other. A second call that raised would turn tidy
    shutdown code into a crash on the way out.
    """
    clock = FakeClock()
    bus = MetricBus(clock=clock)
    recorder = Recorder()
    unsubscribe = bus.subscribe(recorder.record)

    bus.publish(KEY, 1.0)
    unsubscribe()
    unsubscribe()
    bus.publish(KEY, 2.0)

    assert [sample.elapsed_ms for sample in recorder.samples(KEY)] == [1.0]
