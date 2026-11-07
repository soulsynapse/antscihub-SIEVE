"""csv: the signal passes through; the file is the key line, the columns, one line per row of the window; the key reads back."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import _csvfile, csv


def test_signal_passes_through_and_the_file_reads_back(tmp_path):
    sig = np.array([0.5, 0.0, 2.0], np.float32)
    assert csv.run(Series(sig, "k", 7, 30.0), csv.DEFAULTS)["signal"].tolist() == sig.tolist()
    result = {"signal": sig, "gate": np.array([True, False, True]), "key": "abc123"}
    p = tmp_path / csv.default_name(tmp_path / "ants.mp4", 7, 3)
    assert p.name == "ants_7-9.csv"
    csv.write(p, result, 7, 30.0, "ants.mp4")
    assert p.read_text(encoding="utf-8") == ("# sieve key=abc123 rows=7-9 footage=ants.mp4\nrow,time,signal,gate\n"
                                            "7,0.233333,0.5,1\n8,0.266667,0,0\n9,0.300000,2,1\n")
    assert _csvfile.written_key(p) == "abc123" and _csvfile.written_key(tmp_path / "none.csv") is None
    assert _csvfile.read(p)[:3] == ("# sieve key=abc123 rows=7-9 footage=ants.mp4", 7, 3) and _csvfile.read(p)[3] == list(csv.COLUMNS)
    (tmp_path / "plain.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _csvfile.read(tmp_path / "plain.csv")
