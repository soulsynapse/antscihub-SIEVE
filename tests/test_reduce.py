"""reduce: each method over a row's pixels, one float per row, from the four numbers the fold keeps; no gate of its own."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import reduce


def test_each_method_over_the_rows_pixels():
    d = np.zeros((2, 4, 4), np.uint8)
    d[1, :2, :2] = 200                                     # row 1: four of sixteen pixels at 200
    folded = np.stack([reduce.fold(f) for f in d])
    assert folded.shape == (2, 4) and folded[1].tolist() == [800.0, 200.0, 4.0, 16.0]
    s = Series(folded, "k", 0, 30.0)
    expect = {"mean": [0.0, 50.0], "sum": [0.0, 800.0], "max": [0.0, 200.0], "count": [0.0, 4.0], "fraction": [0.0, 0.25]}
    for m, want in expect.items():
        out = reduce.run(s, {"method": m})
        assert out["signal"].dtype == np.float32 and out["signal"].tolist() == want and "gate" not in out, m
    with pytest.raises(ValueError):
        reduce.run(s, {"method": "median"})
