"""transitions: ids whose column moved from one value to another between consecutive rows, either
blank for any; an id absent the row before, or reading NaN, counts nothing; a missing column raises."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import track, transitions

DTYPE = np.dtype(track.DTYPE.descr + [("nest", np.float64)])


def table(members):
    """A tracks table of (id, nest) pairs."""
    t = np.zeros(len(members), DTYPE)
    for i, (id, nest) in enumerate(members):
        t["id"][i], t["nest"][i] = id, nest
    return t


ROWS = [table([(1, 0), (2, 1)]),
        table([(1, 0), (2, 1)]),
        table([(1, 1), (2, 1), (3, 1)]),           # 1 enters; 3 appears inside, which is no crossing
        table([(1, 1), (2, 0), (3, np.nan)]),      # 2 exits; 3 loses its value
        table([(1, 0), (2, 0), (3, 2)]),           # 1 exits; 3 reads 2 from nothing
        table([(2, 2)])]                           # 2 goes to 2, an entry under neither bound
SERIES = Series(ROWS, "k", 0, 30.0)


def signal(column="nest", lo="", hi=""):
    return transitions.run(SERIES, {"column": column, "from": lo, "to": hi})["signal"].tolist()


def test_entries_exits_and_any_change_between_consecutive_rows():
    assert signal(lo="0", hi="1") == [0, 0, 1, 0, 0, 0]
    assert signal(lo="1", hi="0") == [0, 0, 0, 1, 1, 0]
    assert signal() == [0, 0, 1, 1, 1, 1]
    assert signal(lo="0") == [0, 0, 1, 0, 0, 1] and signal(hi="2") == [0, 0, 0, 0, 0, 1]
    assert transitions.changed(ROWS[0], table([]), "nest") == 0
    with pytest.raises(ValueError):
        signal(column="burrow")
