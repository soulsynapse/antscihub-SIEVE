







from __future__ import annotations

import numpy as np
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.gui.series_collector import SeriesCollector
from sieve.pipeline.executor import FrameResult


def result_at(index: int, node_id: str = "sig", fill: float = 0.0) -> FrameResult:
    frame = Frame(data=np.full((2, 3), fill, np.float32), index=index, channels=ChannelSpec.GRAY)
    return FrameResult(index=index, outputs={node_id: frame}, from_cache=frozenset())


def test_superseded_revision_never_contributes_rows() -> None:
    collector = SeriesCollector("sig")
    collector.start(1)
    collector.add(1, result_at(10, fill=1.0))

    collector.start(2)
    collector.add(1, result_at(11, fill=1.0))
    collector.add(2, result_at(10, fill=2.0))
    collector.add(2, result_at(11, fill=2.0))

    series = collector.take(2)
    assert series is not None
    assert series.data.shape == (2, 2, 3)
    np.testing.assert_array_equal(series.data, 2.0)

    assert collector.take(1) is None


def test_axis_starts_at_the_spans_first_frame_and_gaps_refuse() -> None:
    collector = SeriesCollector("sig")
    collector.start(1)
    collector.add(1, result_at(240))
    collector.add(1, result_at(241))
    series = collector.take(1)
    assert series is not None
    assert series.start_index == 240
    assert series.data.shape[0] == 2

    collector.start(2)
    collector.add(2, result_at(240))
    with pytest.raises(ValueError, match="expected frame 241"):
        collector.add(2, result_at(243))


def test_a_result_without_the_watched_node_is_ignored_not_fatal() -> None:


    collector = SeriesCollector("sig")
    collector.start(1)
    collector.add(1, result_at(0, node_id="someone_else"))
    assert collector.take(1) is None
