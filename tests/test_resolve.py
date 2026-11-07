"""resolve: one read labels a tracklet back to its first row once enough agree; two identities or an
overlapping holder flag it; a merge and split label the unread piece by elimination; a labels file
comes through a path input; the same pass rewrites a tracks csv under its key line."""
import os

import numpy as np
import pytest

from sieve_player import document as D
from sieve_player.graph import Series
from tests.test_selector import open_window, tree
from tools import blobs, resolve, track, tracks_csv
from tools import _table

DTYPE = _table.plane_dtype((100, 100), np.dtype(track.DTYPE.descr + [("tag", np.float64)]))


def table(records):
    """A tracks table of (id, cx, cy, tag), each a 10 px box about its centroid."""
    t = np.zeros(len(records), DTYPE)
    for i, (id, cx, cy, tag) in enumerate(records):
        t["id"][i], t["cx"][i], t["cy"][i], t["tag"][i] = id, cx, cy, tag
        t["x"][i], t["y"][i], t["w"][i], t["h"][i], t["area"][i] = cx - 5, cy - 5, 10, 10, 50
    return t


def run(rows, start=0, **params):
    return resolve.run(Series(rows, "k", start, 30.0), {**resolve.DEFAULTS, "columns": "tag", **params})


def column(rows, name):
    return [{int(b["id"]): (None if np.isnan(b[name]) else float(b[name])) for b in t} for t in rows]


def test_enough_agreeing_reads_label_the_whole_tracklet_and_disagreement_flags_it():
    rows = [table([(1, 10, 10, np.nan), (2, 50, 50, np.nan), (3, 80, 80, 5 if r < 2 else np.nan)]) for r in range(10)]
    rows[6]["tag"][0] = rows[7]["tag"][0] = 5
    rows[3]["tag"][1] = 9
    rows[5]["tag"][2] = rows[6]["tag"][2] = 8
    out = run(rows)
    assert out["rows"][0].dtype.names[-2:] == ("identity", "conflict") and _table.plane(out["rows"][0]) == (100, 100)
    assert column(out["rows"], "identity")[0] == {1: 5.0, 2: None, 3: None}
    assert column(out["rows"], "conflict")[0] == {1: 0, 2: 0, 3: 1}
    assert out["signal"].tolist() == [1] * 10
    assert run(rows, signal="conflicts")["signal"].tolist() == [1] * 10
    assert column(run(rows, min_reads=3)["rows"], "identity")[0][1] is None
    with pytest.raises(ValueError):
        run(rows, columns="hue")
    with pytest.raises(ValueError):
        run(rows, signal="reads")


def test_an_identity_is_exclusive_in_time():
    rows = [table([(1, 10, 10, 4 if r < 3 else np.nan), (2, 50, 50, 4 if r in (5, 6) else np.nan)]) for r in range(8)]
    out = run(rows)["rows"]
    assert column(out, "identity")[7] == {1: 4.0, 2: None} and column(out, "conflict")[7] == {1: 0, 2: 1}
    apart = run([table([(1, 10, 10, 4)]) for _ in range(3)] + [table([(2, 50, 50, 4)]) for _ in range(2)])["rows"]
    assert column(apart, "identity")[0] == {1: 4.0} and column(apart, "identity")[4] == {2: 4.0}


def test_a_merge_and_a_split_label_the_unread_piece_by_elimination():
    rows = [table([(1, 10 + 8 * r, 50, 1 if r < 2 else np.nan), (2, 90 - 8 * r, 50, np.nan)]) for r in range(5)]
    rows += [table([(3, 50, 50, np.nan)]) for _ in range(3)]
    for t in rows[5:8]:
        t["x"][0], t["w"][0] = 40, 20
    rows += [table([(4, 50 - 8 * (r - 7), 50, 2 if r > 10 else np.nan), (5, 50 + 8 * (r - 7), 50, np.nan)]) for r in range(8, 13)]
    assert resolve.contacts(rows) == [([1, 2], [4, 5])]
    out = run(rows)["rows"]
    assert column(out, "identity")[0] == {1: 1.0, 2: 2.0} and column(out, "identity")[8] == {4: 2.0, 5: 1.0}
    assert column(out, "identity")[5] == {3: None} and not any(column(out, "conflict")[8].values())


def test_a_labels_file_is_reads_and_comes_through_a_path_input(tmp_path):
    labels = tmp_path / "labels.csv"
    labels.write_text("first,last,id,identity\n# a comment\n3,6,2,7\n", encoding="utf-8")
    assert resolve.load_labels(labels) == [[3, 6, 2, 7.0]]
    rows = [table([(2, 50, 50, np.nan)]) for _ in range(10)]
    assert column(run(rows, labels=resolve.load_labels(labels))["rows"], "identity")[0] == {2: 7.0}
    assert column(run(rows, start=5, labels=[[3, 6, 2, 7]])["rows"], "identity")[0] == {2: 7.0}
    assert column(run(rows, start=7, labels=[[3, 6, 2, 7]])["rows"], "identity")[0] == {2: None}
    (tmp_path / "bad.csv").write_text("1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        resolve.load_labels(tmp_path / "bad.csv")
    from tools import file, gray, threshold

    tree(tmp_path)
    tools = [file, gray, threshold, blobs, track, resolve]
    doc = D.from_tools(tools[1:])
    doc.add_node("file", params={**file.DEFAULTS, "pattern": "labels.csv"})
    doc.connect("file", "resolve", "labels")
    D.save(doc, tmp_path / "doc.json")
    win = open_window(tmp_path, tools)
    assert win.doc.node("resolve").params["labels"] == [[3, 6, 2, 7.0]] and "labels.csv" in win.pane.notes["resolve"].text()
    win.close()


def test_the_same_pass_rewrites_a_tracks_csv_under_its_key_line(tmp_path):
    rows = [table([(1, 10, 10, 5 if r in (6, 7) else np.nan), (2, 50, 50, np.nan)]) for r in range(10)]
    p = tmp_path / "ants_20-29_tracks.csv"
    stack = np.empty(10, object)
    stack[:] = rows
    tracks_csv.write(p, {"rows": stack, "signal": np.full(10, 2.0), "key": "k1"}, 20, 30.0, "ants.mp4")
    before = p.read_text(encoding="utf-8").splitlines()
    assert resolve.main([str(p), "--columns", "tag"]) == 0
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines[0] == before[0] == "# sieve key=k1 rows=20-29 footage=ants.mp4"
    assert lines[1] == before[1].replace(",gate", ",identity,conflict,gate") and len(lines) == len(before)
    assert lines[2].startswith("20,0.666667,1,") and lines[2].endswith(",5,0,1") and lines[3].endswith(",nan,0,1")
    (tmp_path / "l.csv").write_text("20,29,2,3\n", encoding="utf-8")
    resolve.main([str(p), "--columns", "tag", "--labels", str(tmp_path / "l.csv"), "--out", str(tmp_path / "o.csv")])
    out = (tmp_path / "o.csv").read_text(encoding="utf-8").splitlines()
    assert out[1] == lines[1] and out[3].endswith(",3,0,1") and os.path.exists(p)
