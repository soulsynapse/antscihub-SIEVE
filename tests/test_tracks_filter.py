"""tracks-filter: ids kept by rows seen, displacement, path length or a column's mean within blank-is-none
bounds; ids are not renumbered and a dropped id leaves every row."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import track, tracks_filter
from tools import _table

DTYPE = _table.plane_dtype((20, 100), track.DTYPE)


def table(records):
    """A tracks table of (id, cx, cy, area)."""
    t = np.zeros(len(records), DTYPE)
    for i, (id, cx, cy, area) in enumerate(records):
        t["id"][i], t["cx"][i], t["cy"][i], t["area"][i] = id, cx, cy, area
    return t


ROWS = [table([(1, 0, 0, 10), (2, 50, 50, 30), (3, 10, 10, 20)]),
        table([(1, 10, 0, 10), (2, 51, 50, 30), (3, 10, 20, 20)]),
        table([(1, 20, 0, 10), (2, 50, 50, 30)]),                     # 3 ends after two rows
        table([(1, 30, 0, 10)]),                                       # 2 is lost a row
        table([(1, 40, 0, 10), (2, 51, 50, 30)])]                      # 1 walks 40 px; 2 wanders 3 and nets 1
SERIES = Series(ROWS, "k", 0, 30.0)


def ids(rows):
    return [sorted(int(i) for i in t["id"]) for t in rows]


def test_tracks_kept_by_their_properties_leave_every_row_with_ids_intact():
    assert tracks_filter.properties(ROWS, "rows") == {1: 5, 2: 4, 3: 2}
    assert tracks_filter.properties(ROWS, "displacement") == {1: 40.0, 2: 1.0, 3: 10.0}
    assert tracks_filter.properties(ROWS, "path") == {1: 40.0, 2: 3.0, 3: 10.0}
    assert tracks_filter.properties(ROWS, "mean", "area") == {1: 10.0, 2: 30.0, 3: 20.0}
    out = tracks_filter.run(SERIES, {"property": "rows", "column": "area", "lo": "3", "hi": ""})
    assert ids(out["rows"]) == [[1, 2], [1, 2], [1, 2], [1], [1, 2]] and out["signal"].tolist() == [2, 2, 2, 1, 2]
    assert out["rows"][0].dtype == DTYPE and _table.plane(out["rows"][0]) == (20, 100)
    assert ids(tracks_filter.keep(ROWS, "displacement", "", "", "20"))[0] == [2, 3]
    assert ids(tracks_filter.keep(ROWS, "path", "", "5", ""))[0] == [1, 3]
    assert ids(tracks_filter.keep(ROWS, "mean", "area", "15", "25"))[0] == [3]
    with pytest.raises(ValueError):
        tracks_filter.keep(ROWS, "mean", "hue", "", "")
    with pytest.raises(ValueError):
        tracks_filter.keep(ROWS, "speed", "area", "", "")
