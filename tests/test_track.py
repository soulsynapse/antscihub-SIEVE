"""track and travel: two animals walking keep their ids across a gap and a swap of table order; one that
vanishes past lost_rows comes back as a new id; travel reads their steps."""
import numpy as np

from sieve_player.graph import Series, gated
from tests.stepping import hold
from tools import blobs, track, travel


def table(points):
    t = np.zeros(len(points), blobs.DTYPE)
    for i, (x, y) in enumerate(points):
        t["cx"][i], t["cy"][i], t["x"][i], t["y"][i], t["w"][i], t["h"][i], t["area"][i] = x, y, x - 2, y - 2, 4, 4, 16
    return t


def test_ids_follow_the_animals_and_a_long_absence_ends_a_track():
    a = [(10 + 2 * r, 50) for r in range(12)]                    # walks right, 2 px a row
    b = [(90, 10 + 3 * r) for r in range(12)]                    # walks down, 3 px a row
    tables = [table([a[r], b[r]]) if r % 2 else table([b[r], a[r]]) for r in range(12)]   # order swaps each row
    tables[5] = table([b[5]])                                     # a misses a row
    tables[8:11] = [table([b[r]]) for r in range(8, 11)]          # then three in a row, past lost_rows
    params = {"max_step": 5.0, "lost_rows": 2, "min_rows": 3, "min_p": 0.1}
    out = hold(track, tables, params)
    rows, signal = out["rows"], out["signal"]
    ids = lambda r, x: int(rows[r][rows[r]["cx"] == x]["id"][0])  # noqa: E731
    assert rows.dtype == object and rows[0].dtype == track.DTYPE and signal.shape == (12,)
    assert all(ids(r, 90) == ids(0, 90) for r in range(12))       # b keeps its id throughout
    assert ids(4, a[4][0]) == ids(0, 10) == ids(6, a[6][0])       # a bridges the one-row gap
    assert ids(11, a[11][0]) != ids(0, 10)                        # and is new after three rows away
    assert signal.tolist() == [0, 0, 2, 2, 2, 1, 2, 2, 1, 1, 1, 1]


def test_travel_reads_the_steps_under_the_gate():
    rows = track.run(Series([table([(0, 0), (50, 50)]), table([(3, 4), (50, 50)]), table([(6, 8)])], "k", 0, 30.0),
                     {"max_step": 10.0, "lost_rows": 5, "min_rows": 1, "min_p": 0.1})["rows"]
    assert hold(travel, rows, {"method": "mean", "moving": 1.0})["signal"].tolist() == [0, 2.5, 5]
    assert hold(travel, rows, {"method": "count", "moving": 1.0})["signal"].tolist() == [0, 1, 1]
    _, fed = gated({"rows": rows, "signal": np.array([2.0, 2.0, 1.0])}, (2.0, 2.0))
    assert [len(t) for t in fed] == [2, 2, 0]                     # a gated-out row feeds an empty table
    assert hold(travel, fed, {"method": "sum", "moving": 1.0})["signal"].tolist() == [0, 5, 0]
