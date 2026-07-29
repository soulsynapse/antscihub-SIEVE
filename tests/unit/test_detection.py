

from __future__ import annotations

import math

import numpy as np

from sieve.core.detection import (
    count_band_to_counts,
    detect_gate,
    gate_intervals,
    inband_count,
    windowed_mean,
)


def test_windowed_mean_edges_divide_by_true_window_length() -> None:






    count = np.full(50, 3.0, np.float32)
    for centered in (True, False):
        out = windowed_mean(count, 15, centered)
        np.testing.assert_allclose(out, 3.0, rtol=1e-6)


def test_count_band_denominates_once_and_inf_passes_through() -> None:






    lo, hi = count_band_to_counts(0.25, math.inf, 40)
    assert (lo, hi) == (10.0, math.inf)
    assert count_band_to_counts(0.0, 1.0, 40) == (0.0, 40.0)


def test_chain_end_to_end_with_nan_blocks_and_intervals() -> None:







    n_frames, n_blocks = 60, 10
    m = np.zeros((n_frames, n_blocks), np.float32)
    m[20:30, :8] = 5.0
    m[5, :] = 5.0
    m[:, 9] = np.nan
    count = inband_count(m, 1.0, 10.0)
    assert count[5] == 9.0
    windowed = windowed_mean(count, 10, centered=True)
    lo, hi = count_band_to_counts(0.5, math.inf, n_blocks)
    gate = detect_gate(windowed, lo, hi)
    intervals = gate_intervals(gate, start=100)
    assert len(intervals) == 1
    start, end = intervals[0]


    assert 100 + 15 <= start <= 100 + 25
    assert 100 + 25 <= end <= 100 + 35
    assert not gate[5]
