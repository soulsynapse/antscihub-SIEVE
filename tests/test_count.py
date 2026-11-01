"""count: a row's blob table folds to its length, and the signal is that per row."""
import numpy as np

from sieve_player.graph import Series
from tools import blobs, count


def test_folds_a_table_to_its_length_and_signals_it():
    tables = [np.empty(n, blobs.DTYPE) for n in (0, 3, 1)]
    stack = np.stack([count.fold(t) for t in tables])
    assert stack.shape == (3, 1) and stack.dtype == np.float64
    out = count.run(Series(stack, "k", 0, 30.0), {})
    assert out["signal"].tolist() == [0.0, 3.0, 1.0] and out["signal"].dtype == np.float32
