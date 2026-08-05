"""Pins on `core/ops/detection.py` — honest edges, one denomination, real runs."""

from __future__ import annotations

import math

import numpy as np

from sieve.core.ops.detection import (
    count_band_to_counts,
    detect_gate,
    gate_intervals,
    inband_count,
    windowed_mean,
)


def test_windowed_mean_edges_divide_by_true_window_length() -> None:
    """A constant series stays constant through both clip edges.

    A zero-padded mean would dip at the edges by exactly the truncated
    fraction — a phantom event boundary at the start and end of every clip.
    Both centered and trailing, because they truncate on different sides.
    """
    count = np.full(50, 3.0, np.float32)
    for centered in (True, False):
        out = windowed_mean(count, 15, centered)
        np.testing.assert_allclose(out, 3.0, rtol=1e-6)


def test_count_band_denominates_once_and_inf_passes_through() -> None:
    """The fraction→counts conversion is the one denomination point.

    A band of [0.25, inf] over 40 blocks is [10, inf]: the finite endpoint
    scales, the unbounded one does not become a number, and zero would stay
    zero. This is the API that deletes v1's `rescale_count_band`.
    """
    lo, hi = count_band_to_counts(0.25, math.inf, 40)
    assert (lo, hi) == (10.0, math.inf)
    assert count_band_to_counts(0.0, 1.0, 40) == (0.0, 40.0)


def test_chain_end_to_end_with_nan_blocks_and_intervals() -> None:
    """The full chain on synthetic data: NaN never counts, the gate fires on
    the sustained event only, and intervals come back in absolute frames.

    Frames 20-29 put 8 of 10 blocks in band; one lone spike at frame 5 puts
    all 10 in band for a single frame. With D=10 the spike dilutes below a
    0.5-fraction threshold and only the sustained run gates.
    """
    n_frames, n_blocks = 60, 10
    m = np.zeros((n_frames, n_blocks), np.float32)
    m[20:30, :8] = 5.0  # sustained: 8 blocks in [1, 10]
    m[5, :] = 5.0  # 1-frame spike: all 10 blocks
    m[:, 9] = np.nan  # a dead block must never count
    count = inband_count(m, 1.0, 10.0)
    assert count[5] == 9.0  # 10 in band minus the NaN column
    windowed = windowed_mean(count, 10, centered=True)
    lo, hi = count_band_to_counts(0.5, math.inf, n_blocks)
    gate = detect_gate(windowed, lo, hi)
    intervals = gate_intervals(gate, start=100)
    assert len(intervals) == 1
    start, end = intervals[0]
    # The centered window smears the run's edges by up to D/2 either side;
    # what must hold is that it brackets the event and excludes the spike.
    assert 100 + 15 <= start <= 100 + 25
    assert 100 + 25 <= end <= 100 + 35
    assert not gate[5]
