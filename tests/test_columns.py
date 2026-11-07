"""A table carries columns added downstream and the shape of the plane it was found in: an added column
reaches filter, size, track, travel and tracks-csv by the table's own names; a name the table has is
refused; the plane survives blobs, filter and track."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sieve_player.graph import Series
from tests.test_blobs import fed, m
from tests.test_track import table
from tools import blobs, filter, size, track, tracks_csv, travel
from tools import _table


def test_an_added_column_reaches_every_reader_by_the_tables_names(tmp_path):
    a, b = [(10 + 2 * r, 50) for r in range(4)], [(90, 10 + 3 * r) for r in range(4)]
    tables = [_table.with_column(table([a[r], b[r]]), "purple", np.array([r, 10 + r], np.float32)) for r in range(4)]
    assert tables[0].dtype.names[-1] == "purple" and tables[0]["purple"].tolist() == [0.0, 10.0]
    assert filter.keep(tables[3], "purple", "5", "")["purple"].tolist() == [13.0]
    assert filter.keep(tables[3], "aspect", "", "")["purple"].tolist() == []           # the ratios still are: minor 0 is NaN
    rows = np.empty(4, object)
    rows[:] = tables
    assert size.run(Series(rows, "k", 0, 30.0), {"field": "purple", "method": "max"})["signal"].tolist() == [10, 11, 12, 13]
    with pytest.raises(ValueError):
        size.run(Series(rows, "k", 0, 30.0), {"field": "contour", "method": "max"})
    tracked = track.run(Series(rows, "k", 0, 30.0), {**track.DEFAULTS, "max_step": 5.0, "min_rows": 1})
    out = tracked["rows"]
    assert out[0].dtype.names[-2:] == ("purple", "id") and out[3]["purple"].tolist() == [3.0, 13.0]
    assert len(set(out[r]["id"][out[r]["purple"] >= 10][0] for r in range(4))) == 1         # b keeps its id and its column
    assert travel.run(Series(out, "k", 0, 30.0), travel.DEFAULTS)["signal"].shape == (4,)
    text = tracks_csv.text({"rows": out}, 0, 30.0, "ants.mp4")
    header, first = text.splitlines()[1:3]
    assert header.endswith(",core,purple,gate") and first.endswith(",0,1") and first.split(",")[-2] in ("0", "10")
    with pytest.raises(ValueError):
        _table.with_column(tables[0], "area", np.zeros(2))
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    image = QImage(100, 60, QImage.Format_RGB32)
    painter = QPainter(image)
    _table.draw(painter, tables[3])
    track.draw(painter, 3, tracked, 0, track.DEFAULTS)
    painter.end()


def test_the_plane_a_table_was_found_in_survives_filter_and_track():
    found = blobs.run(fed(m), 0, {**blobs.DEFAULTS, "min_area": 2})
    assert _table.plane(found) == m.shape and found.dtype == blobs.DTYPE
    assert _table.plane(filter.keep(found, "area", "10", "")) == m.shape
    assert _table.plane(_table.with_column(found, "purple", np.zeros(len(found)))) == m.shape
    assert _table.plane(blobs.run(fed(m), 0, {**blobs.DEFAULTS, "min_area": 2, "max_area": 10})) == m.shape
    rows = np.empty(2, object)
    rows[:] = [found, found]
    assert _table.plane(track.run(Series(rows, "k", 0, 30.0), track.DEFAULTS)["rows"][1]) == m.shape
    assert _table.plane(table([(1, 1)])) is None
