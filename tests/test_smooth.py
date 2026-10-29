"""smooth: a centred mean or median over 2 * reach + 1 rows, the edges over the rows that exist; a spike spreads under the mean and drops under the median."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import smooth


def sig(values):
    return Series(np.array(values, np.float32), "k", 0, 30.0)


def test_mean_spreads_a_spike_and_the_edges_average_fewer_rows():
    out = smooth.run(sig([0, 0, 6, 0, 0]), {"kernel": "mean", "reach": 1})["signal"]
    assert out.dtype == np.float32 and out.tolist() == [0.0, 2.0, 2.0, 2.0, 0.0]
    out = smooth.run(sig([3, 3, 3]), {"kernel": "mean", "reach": 5})["signal"]
    assert out.tolist() == [3.0, 3.0, 3.0]                 # a window wider than the series is the rows there are


def test_median_drops_a_spike_and_keeps_a_plateau():
    assert smooth.run(sig([0, 0, 6, 0, 0]), {"kernel": "median", "reach": 1})["signal"].tolist() == [0.0, 0.0, 0.0, 0.0, 0.0]
    assert smooth.run(sig([0, 5, 5, 5, 0]), {"kernel": "median", "reach": 1})["signal"].tolist() == [2.5, 5.0, 5.0, 5.0, 2.5]


def test_reach_zero_is_the_signal_and_a_kernel_it_lacks_raises():
    x = [1, 4, 1, 5]
    assert smooth.run(sig(x), {"kernel": "median", "reach": 0})["signal"].tolist() == x
    with pytest.raises(ValueError):
        smooth.run(sig(x), {"kernel": "gaussian", "reach": 1})
