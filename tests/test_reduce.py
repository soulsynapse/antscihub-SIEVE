"""reduce: each method over a row's pixels, one float per row."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import reduce


def test_each_method_over_the_rows_pixels():
    d = np.zeros((2, 4, 4), np.uint8)
    d[1, :2, :2] = 200                                     # row 1: four of sixteen pixels at 200
    s = Series(d, "k", 0, 30.0)
    expect = {"mean": [0.0, 50.0], "sum": [0.0, 800.0], "max": [0.0, 200.0], "count": [0.0, 4.0], "fraction": [0.0, 0.25]}
    for m, want in expect.items():
        out = reduce.run(s, {"method": m})["signal"]
        assert out.dtype == np.float32 and out.tolist() == want, m
    with pytest.raises(ValueError):
        reduce.run(s, {"method": "median"})
