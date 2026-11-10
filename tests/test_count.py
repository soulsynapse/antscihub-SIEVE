"""count: a row's table folds to its length, and the signal is that per row; fed tables, tracks say, read the same."""
import numpy as np

from sieve_player.graph import Series
from tests.test_track import table
from tools import blobs, count, size, track


def test_folds_a_table_to_its_length_and_signals_it():
    tables = [np.empty(n, blobs.DTYPE) for n in (0, 3, 1)]
    stack = np.stack([count.fold(t) for t in tables])
    assert stack.shape == (3, 1) and stack.dtype == np.float64
    out = count.run(Series(stack, "k", 0, 30.0), {})
    assert out["signal"].tolist() == [0.0, 3.0, 1.0] and out["signal"].dtype == np.float32


def test_a_tracks_series_counts_and_sizes_as_the_blobs_it_was_tracked_from():
    blobs_rows = [table([(10, 20), (50, 60)]), table([]), table([(12, 22), (52, 62), (90, 90)])]
    tracks = track.run(Series(blobs_rows, "k", 0, 30.0), {**track.DEFAULTS, "max_step": 5.0, "min_rows": 1})["rows"]
    folded = np.stack([count.fold(t) for t in blobs_rows])
    assert count.run(Series(tracks, "k", 0, 30.0), {})["signal"].tolist() == count.run(Series(folded, "k", 0, 30.0), {})["signal"].tolist() == [2, 0, 3]
    for method in size.METHODS:
        params = {"field": "area", "method": method}
        assert size.run(Series(tracks, "k", 0, 30.0), params)["signal"].tolist() == size.run(Series(blobs_rows, "k", 0, 30.0), params)["signal"].tolist()
