"""Proof for session/frames.py's secret: the frame at index N reflects
exactly the first N+1 steps, and index -1 is the bound source untouched.
"""

from __future__ import annotations

import numpy as np

from proto_sieve.src.sieve.executor import cache_stats, clear_cache
from proto_sieve.src.sieve.pipeline import Pipeline, Step
from proto_sieve.src.sieve.session.frames import frame_for


def _pipeline() -> Pipeline:
    return Pipeline(
        source="src",
        steps=(
            Step(tool="crop", params={"y0": 0, "y1": 8, "x0": 0, "x1": 8}),
            Step(tool="crop", params={"y0": 0, "y1": 4, "x0": 0, "x1": 4}),
        ),
    )


def _bound() -> dict[str, np.ndarray]:
    return {"src": np.arange(16 * 16, dtype=np.uint8).reshape(16, 16)}


def test_index_minus_one_is_the_untouched_source():
    frame = frame_for(_pipeline(), -1, _bound())
    assert frame.shape == (16, 16)
    assert np.array_equal(frame, _bound()["src"])


def test_each_index_reflects_only_the_steps_up_to_it():
    bound = _bound()
    after_first = frame_for(_pipeline(), 0, bound)
    after_second = frame_for(_pipeline(), 1, bound)

    assert after_first.shape == (8, 8)
    assert after_second.shape == (4, 4)


def test_stepping_reuses_the_executors_cache_for_the_shared_prefix():
    clear_cache()
    bound = _bound()
    frame_for(_pipeline(), 0, bound)
    misses_after_first = cache_stats()["misses"]

    frame_for(_pipeline(), 1, bound)
    stats = cache_stats()

    # Only the second crop node is new work; the source and first crop were
    # already in cache from the prior call.
    assert stats["misses"] == misses_after_first + 1
