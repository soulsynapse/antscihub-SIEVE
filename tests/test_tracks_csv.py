"""tracks-csv: the rows pass through with their count as the signal; the file is the key line, the columns,
one line per record, none for an empty row; the key reads back through csv."""
import numpy as np

from sieve_player.graph import Series
from tests.test_track import table
from tools import _csvfile, track, tracks_csv


def test_rows_pass_through_and_the_file_holds_one_line_per_record(tmp_path):
    rows = track.run(Series([table([(10, 20), (50, 60)]), table([]), table([(12, 22)])], "k", 0, 30.0),
                     {**track.DEFAULTS, "max_step": 5.0, "min_rows": 1})["rows"]
    out = tracks_csv.run(Series(rows, "k", 7, 30.0), tracks_csv.DEFAULTS)
    assert out["signal"].tolist() == [2, 0, 1] and all(np.array_equal(a, b) for a, b in zip(out["rows"], rows))
    result = {**out, "gate": np.array([True, True, False]), "key": "abc123"}
    p = tmp_path / tracks_csv.default_name(tmp_path / "ants.mp4", 7, 3)
    assert p.name == "ants_7-9_tracks.csv"
    tracks_csv.write(p, result, 7, 30.0, "ants.mp4")
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# sieve key=abc123 rows=7-9 footage=ants.mp4" and lines[1] == ",".join(tracks_csv.columns(rows[0].dtype))
    assert lines[1].startswith("row,time,id,x,y,w,h,area,") and lines[1].endswith(",core,gate")
    assert len(lines) == 5 and lines[2].startswith("7,0.233333,0,8,18,4,4,16,10,20,") and lines[4].startswith("9,0.300000,0,")
    assert lines[2].endswith(",1") and lines[4].endswith(",0")
    assert _csvfile.written_key(p) == "abc123"
