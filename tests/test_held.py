"""The held file's side of staleness, what a later session reads back and what it refuses, that
a write's cost is the runs the file has not had, and which run a range is served from and which
goes at the limit."""
import os

import numpy as np

from sieve_player import held


def test_a_held_file_reads_back_under_its_stamp_and_as_nothing_under_any_other(tmp_path):
    video, tool = tmp_path / "clip.mp4", tmp_path / "tools" / "t.py"
    tool.parent.mkdir()
    video.write_bytes(b"footage")
    tool.write_text("A = 1\n", encoding="utf-8", newline="\n")
    tools = {"t": type("M", (), {"__file__": str(tool)})}
    stamp = held.stamp(video, held.tools_print(tools))
    path = held.path_for(str(tmp_path / "doc.json"))
    read = lambda: held.File(path, held.stamp(video, held.tools_print(tools))).load()
    result = {"signal": np.arange(4, dtype=np.float32), "key": "k", "plate": (0, 1, 2, 3)}     # a tuple as long as the run
    held.File(path, stamp).write([(10, 4, {"count": result}, 16)])
    (start, rows, results, _), = read()
    assert (start, rows) == (10, 4) and held.rows_of(results["count"], rows, 1, 2)["signal"].tolist() == [1.0, 2.0]
    assert held.rows_of(results["count"], rows, 1, 2)["key"] == "k"
    assert held.rows_of(results["count"], rows, 1, 2)["plate"] == (0, 1, 2, 3)
    tool.write_text("A = 2\n", encoding="utf-8", newline="\n")
    assert read() == []
    tool.write_text("A = 1\n", encoding="utf-8", newline="\n")
    assert read() != []
    video.write_bytes(b"other footage")
    assert read() == []
    with open(path, "wb") as f:
        f.write(b"not a pickle")
    assert held.File(path, stamp).load() == [] and held.File(str(tmp_path / "absent"), stamp).load() == []


def test_a_run_is_pickled_once_however_the_file_is_written_after(tmp_path):
    file = held.File(str(tmp_path / "doc.json.series"), ("stamp",))
    tables = np.empty(3, object)
    tables[:] = [np.zeros(n, [("id", "<i4")]) for n in (2, 0, 1)]
    run = lambda start, **more: (start, 3, {"track": {"signal": np.full(3, start, np.float32), **more}}, 0)
    scalars = np.empty(3, object)
    scalars[:] = [np.array(float(n)) for n in range(3)]     # arrays with no rows to concatenate
    a, b, c, d = run(0, rows=tables, scalars=scalars), run(10), run(20), run(30)
    file.write([a, b])
    for was in (a, b):
        was[2]["track"]["unpicklable"] = lambda: None       # a second pickling of a run the file has would raise
    file.write([a, b, c])                                   # added behind
    file.write([a, c, d])                                   # b let go: the file made again
    back = held.File(file.path, ("stamp",))
    kept = back.load()
    assert [(s, r["track"]["signal"].tolist()) for s, _, r, _ in kept] == [(0, [0.0] * 3), (20, [20.0] * 3), (30, [30.0] * 3)]
    first = kept[0][2]["track"]["rows"]
    assert [len(t) for t in first] == [2, 0, 1] and first[0].dtype == tables[0].dtype
    assert [float(x) for x in kept[0][2]["track"]["scalars"]] == [0.0, 1.0, 2.0]
    with open(file.path, "r+b") as f:
        f.truncate(os.path.getsize(file.path) - 4)          # a write cut short in its last record
    kept = back.load()
    back.write([*kept, d])
    assert [s for s, *_ in held.File(file.path, ("stamp",)).load()] == [0, 20, 30]


def test_a_range_is_served_from_the_run_that_covers_it_under_the_chains_keys_and_the_limit_lets_go_of_left_keys_first():
    now, moved = held.Chain({"a": "ka", "b": "kb"}, frozenset({"a"}), None), held.Chain({"a": "ka", "b": "kb2"}, frozenset({"a"}), None)
    runs = held.Runs(18, lambda v: 1)       # a run of two nodes of three values counts six
    of = lambda start, rows, chain: {nid: {"signal": np.arange(start, start + rows, dtype=np.float32), "key": k, "plate": None}
                                     for nid, k in chain.keys.items()}
    hold = lambda start, rows, chain: runs.hold(start, rows, of(start, rows, chain), chain)
    assert hold(10, 4, now) and not hold(10, 4, now) and not runs.hold(10, 5, of(10, 4, now), now)
    assert hold(0, 20, now) and [run[:2] for run in runs] == [(0, 20)]      # the window's run, covered, went
    assert runs.over(12, 3, now)["b"]["signal"].tolist() == [12.0, 13.0, 14.0] and runs.over(18, 5, now) is None
    assert runs.over(12, 3, moved) is None and runs.spans(moved) == [] and runs.spans(now) == [(0, 20)]
    part = runs.part(12, 3, moved)
    assert list(part) == ["a"] and part["a"]["signal"].tolist() == [12.0, 13.0, 14.0]       # b is not stepped, nor under its key
    assert hold(30, 4, moved) and hold(40, 4, now) and len(runs) == 3
    assert runs.from_first_row("a", "ka", None)[:2] == (0, 20) and runs.from_first_row("b", "kb2", None) is None
    assert hold(50, 4, moved) and [run[0] for run in runs] == [30, 40, 50]      # 0's keys are left: the longest kept is one the chain is served by
    assert [(at, signal.tolist()) for signal, at, _ in runs.beside("b", "kb2", None, 31, 2)] == [(30, [30.0]), (33, [33.0]), (50, [50.0, 51.0, 52.0, 53.0])]
    twice = held.Runs(18, lambda v: 1)
    again = lambda start, chain: twice.hold(start, 4, of(start, 4, chain), chain)
    assert again(10, now) and again(10, moved) and again(30, now) and again(50, now)    # two runs over the same rows: one goes as itself, its arrays never compared
    assert [(run.start, run.results["b"]["key"]) for run in twice] == [(10, "kb"), (30, "kb"), (50, "kb")]
    full = held.Runs(6, lambda v: 1)        # room for one run
    assert full.hold(0, 4, of(0, 4, now), now) and full.hold(0, 4, of(0, 4, moved), moved)     # as long as the run of keys left, which goes
    assert not full.hold(0, 4, of(0, 4, now), moved) and [run.results["b"]["key"] for run in full] == ["kb2"]      # let go at once: nothing held changed
    plated = held.Chain(moved.keys, moved.steps, "plate")
    assert full.hold(0, 4, {nid: {**r, "plate": "plate"} for nid, r in of(0, 4, moved).items()}, plated)       # the same keys in another plate are not covered
    assert full.over(0, 4, plated) is not None and full.over(0, 4, moved) is None
