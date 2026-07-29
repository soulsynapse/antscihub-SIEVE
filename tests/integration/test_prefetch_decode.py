






























from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter, sleep

import numpy as np
import pytest

from sieve.decode.prefetch import (
    INFERRED_WORKER_CAP,
    LUMA_WORKER_CAP,
    PrefetchFrameSource,
    available_cpus,
)
from sieve.decode.reader import VideoDecodeError, VideoReader



SPAN = range(8, 32)


def test_every_frame_is_byte_identical_to_the_sequential_reader(synthetic_video: Path) -> None:







    with VideoReader(synthetic_video) as reader:
        expected = [reader.read(index) for index in SPAN]

    with PrefetchFrameSource(synthetic_video, workers=4) as source:
        got = [source.read(index) for index in SPAN]

    assert [frame.index for frame in got] == list(SPAN)
    for frame, reference in zip(got, expected, strict=True):
        assert frame.index == reference.index
        assert frame.channels == reference.channels
        assert np.array_equal(frame.data, reference.data)


    assert len({frame.data.tobytes() for frame in got}) == len(list(SPAN))


def test_an_inferred_count_follows_the_format_the_source_was_opened_in(
    synthetic_video: Path,
) -> None:












    if available_cpus() < INFERRED_WORKER_CAP:
        pytest.skip(f"{available_cpus()} cpus cannot distinguish the two caps")

    with PrefetchFrameSource(synthetic_video, luma=True) as source:
        assert source.luma
        assert source.workers == LUMA_WORKER_CAP

    with PrefetchFrameSource(synthetic_video) as source:
        assert not source.luma
        assert source.workers == INFERRED_WORKER_CAP


def test_the_window_never_runs_further_ahead_than_lookahead(synthetic_video: Path) -> None:



























    lookahead = 3
    with PrefetchFrameSource(synthetic_video, workers=2, lookahead=lookahead) as source:
        assert source.lookahead == lookahead
        source.read(0)



        def ahead() -> int:
            return source._claim - source._want

        settled = _quiesce(ahead)
        assert settled == lookahead, f"window settled {settled} ahead of a {lookahead} bound"


        assert [source.read(index).index for index in range(1, 16)] == list(range(1, 16))


def _quiesce(sample: Callable[[], int], *, timeout_s: float = 3.0) -> int:








    deadline = perf_counter() + timeout_s
    stable = 0
    last = sample()
    while perf_counter() < deadline:
        sleep(0.01)
        current = sample()
        stable = stable + 1 if current == last else 0
        last = current
        if stable >= 3:
            return current
    raise AssertionError(f"never settled within {timeout_s}s; last value {last}")


def test_reading_out_of_order_answers_the_index_asked_for(synthetic_video: Path) -> None:













    with VideoReader(synthetic_video) as reader:
        expected = {index: reader.read(index).data.copy() for index in (0, 30, 31, 5)}

    with PrefetchFrameSource(synthetic_video, workers=4) as source:
        assert np.array_equal(source.read(0).data, expected[0])

        assert np.array_equal(source.read(30).data, expected[30])

        assert np.array_equal(source.read(31).data, expected[31])

        assert np.array_equal(source.read(5).data, expected[5])


def test_a_frame_outside_the_video_is_refused_the_way_the_reader_refuses_it(
    synthetic_video: Path,
) -> None:







    with VideoReader(synthetic_video) as reader:
        frames = reader.metadata.frame_count
        with pytest.raises(VideoDecodeError) as sequential:
            reader.read(frames)

    with (
        PrefetchFrameSource(synthetic_video, workers=2) as source,
        pytest.raises(VideoDecodeError) as parallel,
    ):
        source.read(frames)

    assert str(parallel.value) == str(sequential.value)
