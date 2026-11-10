"""csv: what it reads passes through; the file is the key line with the kind, the columns, one line per
row of a signal or per record of a table, `id` for tracks alone and no non-numeric column; the key
reads back; tracks-csv is no longer a tool."""
import numpy as np
import pytest

from sieve_player.graph import Series
from sieve_player.registry import discover
from tests.test_track import table
from tools import _csvfile, _table, csv, track


def test_signal_passes_through_and_the_file_reads_back(tmp_path):
    sig = np.array([0.5, 0.0, 2.0], np.float32)
    assert csv.run(Series(sig, "k", 7, 30.0), csv.DEFAULTS)["signal"].tolist() == sig.tolist()
    result = {"signal": sig, "gate": np.array([True, False, True]), "key": "abc123"}
    p = tmp_path / csv.default_name(tmp_path / "ants.mp4", 7, 3, result)
    assert p.name == "ants_7-9.csv"
    csv.write(p, result, 7, 30.0, "ants.mp4")
    assert p.read_text(encoding="utf-8") == ("# sieve key=abc123 rows=7-9 footage=ants.mp4 kind=signal\nrow,time,signal,gate\n"
                                            "7,0.233333,0.5,1\n8,0.266667,0,0\n9,0.300000,2,1\n")
    assert _csvfile.written_key(p) == "abc123" and _csvfile.written_key(tmp_path / "none.csv") is None
    key, start, n, header, lines, kind = _csvfile.read(p)
    assert (key, start, n, header, kind) == ("# sieve key=abc123 rows=7-9 footage=ants.mp4 kind=signal", 7, 3, list(csv.COLUMNS), "signal")
    (tmp_path / "plain.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _csvfile.read(tmp_path / "plain.csv")


def test_tables_pass_through_with_their_count_and_write_one_line_per_record(tmp_path):
    blobs = [_table.with_column(t, "name", np.array(["nest"] * len(t), "<U8")) for t in (table([(10, 20), (50, 60)]), table([]), table([(12, 22)]))]
    tracks = track.run(Series(blobs, "k", 0, 30.0), {**track.DEFAULTS, "max_step": 5.0, "min_rows": 1})["rows"]
    for rows, kind, id, col in ((blobs, "blobs", "", ""), (tracks, "tracks", "0,", "id,")):
        out = csv.run(Series(rows, "k", 7, 30.0), csv.DEFAULTS)
        assert out["signal"].tolist() == [2, 0, 1] and all(np.array_equal(a, b) for a, b in zip(out["rows"], rows))
        result = {**out, "gate": np.array([True, True, False]), "key": "abc123"}
        p = tmp_path / csv.default_name(tmp_path / "ants.mp4", 7, 3, result)
        assert p.name == f"ants_7-9_{kind}.csv"
        csv.write(p, result, 7, 30.0, "ants.mp4")
        lines = p.read_text(encoding="utf-8").splitlines()
        assert lines[0] == f"# sieve key=abc123 rows=7-9 footage=ants.mp4 kind={kind}" and _csvfile.read(p)[5] == kind
        assert lines[1] == ",".join(csv.columns(rows[0].dtype)) == f"row,time,{col}" + ",".join(csv.fields(rows[0].dtype)) + ",gate"
        assert ("id" in lines[1].split(",")) == (kind == "tracks") and "name" not in lines[1] and "contour" not in lines[1]
        assert len(lines) == 5 and lines[2].startswith(f"7,0.233333,{id}8,18,4,4,16,10,20,") and lines[4].startswith(f"9,0.300000,{id}")
        assert lines[2].endswith(",1") and lines[4].endswith(",0")


def test_tracks_csv_is_no_longer_a_tool():
    assert "tracks-csv" not in {e.name for e in discover("tools")}
