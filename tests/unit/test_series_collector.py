"""The collector's two claims: the series has no holes, and the clock covers it.

Everything else here is arithmetic over a list. What is worth a test is the pair
of things a graph drawn from this would otherwise get wrong silently — a series
with a frame missing from the middle, which plots as a shifted trace rather than
as an error, and a `slider_to_graph` span that closed before the array existed,
which would be a number about rendering wearing the name of the graph.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import numpy as np
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.executor import FrameResult
from sieve.pipeline.series_collector import SERIES_BUDGET, CollectedSeries, SeriesCollector

NODE = "detector"


class MeasureWatchingTheSeries:
    """A `Measure` that records what had been assembled when each span closed.

    A recorder of keys alone could not fail the test that matters: the span
    opening around a refill is trivial, and the claim is that it closes *after*
    the stack.
    """

    def __init__(self, series: Callable[[], CollectedSeries | None]) -> None:
        self._series = series
        self.entered: list[str] = []
        self.at_close: list[CollectedSeries | None] = []

    @contextmanager
    def __call__(self, key: str) -> Iterator[None]:
        self.entered.append(key)
        yield
        self.at_close.append(self._series())


def result(index: int, value: float, node_id: str = NODE) -> FrameResult:
    """One frame of `node_id`'s output, as `execute` would hand it over."""
    return FrameResult(
        index=index,
        outputs={node_id: Frame(np.full((1, 1), value, np.float32), index, ChannelSpec.GRAY)},
        from_cache=frozenset(),
    )


def collector(measure: MeasureWatchingTheSeries | None = None) -> SeriesCollector:
    return SeriesCollector(NODE, measure=measure if measure is not None else _untimed)


@contextmanager
def _untimed(key: str) -> Iterator[None]:
    del key
    yield


def test_a_refill_assembles_the_rendered_span_into_one_array() -> None:
    """The whole job: rows in frame order, out as `(T, ...)` from a known start.

    `start_index` is the first frame the render delivered rather than zero,
    because a working window is a stretch of footage and a graph drawn as if it
    began at the file's first frame is a graph about the wrong footage.
    """
    watched = collector()
    with watched.refill() as consume:
        for offset, value in enumerate((1.0, 2.0, 3.0)):
            consume(result(5 + offset, value))

    series = watched.series
    assert series is not None
    assert series.start_index == 5
    assert series.data.shape == (3, 1, 1)
    assert series.data.dtype == np.float32
    assert series.data.reshape(-1).tolist() == [1.0, 2.0, 3.0]


def test_a_gap_in_the_rendered_span_is_refused() -> None:
    """A hole would plot as a shifted trace, which is a wrong graph, not an empty one."""
    watched = collector()
    with pytest.raises(ValueError, match="expected frame 6"), watched.refill() as consume:
        consume(result(5, 1.0))
        consume(result(7, 2.0))


def test_a_result_without_the_watched_nodes_output_is_refused() -> None:
    """`execute` carries every node on every frame, so an absence is a typo."""
    watched = collector()
    with pytest.raises(KeyError), watched.refill() as consume:
        consume(result(0, 1.0, node_id="blocks"))


def test_the_timed_span_closes_only_once_the_series_exists() -> None:
    """`slider_to_graph` ends where the graph could be drawn, not where the render ends."""
    measure = MeasureWatchingTheSeries(lambda: watched.series)
    watched = collector(measure)

    with watched.refill() as consume:
        consume(result(0, 1.0))
        consume(result(1, 2.0))

    assert measure.entered == [SERIES_BUDGET]
    assert [series.data.shape[0] for series in measure.at_close if series is not None] == [2]


def test_a_refill_that_produced_no_rows_has_no_series() -> None:
    """No reachable output is not the same claim as a flat one."""
    watched = collector()
    with watched.refill():
        pass
    assert watched.series is None


def test_a_refill_starts_from_nothing_rather_than_from_the_last_one() -> None:
    """The second drag's graph is the second drag's frames.

    A collector that appended across refills would pass every assertion above
    and hand a graph twice the window's length after the second edit.
    """
    watched = collector()
    with watched.refill() as consume:
        consume(result(5, 1.0))
    with watched.refill() as consume:
        consume(result(9, 4.0))

    series = watched.series
    assert series is not None
    assert (series.start_index, series.data.shape[0]) == (9, 1)
