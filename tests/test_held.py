"""What a later session reads back of the held file and what it refuses, that a write's cost is
the runs the file has not had, which run a range is served from and which goes at the limit, and
which nodes are said stale by the code their held results were made under."""
import os
import pickle

import numpy as np

from sieve_player import cut, held, theme


def test_a_held_file_reads_back_by_the_form_of_its_records_alone_and_is_let_go_by_a_write_of_no_runs(tmp_path):
    path = held.path_for(str(tmp_path / "doc.json"))
    read = lambda: held.File(path).load()
    result = {"signal": np.arange(4, dtype=np.float32), "key": "k", "said": (0, 1, 2, 3), "code": {"count": "d"}}      # a tuple as long as the run is no row of it
    held.File(path).write([(10, 4, {"count": result}, 16)])
    (start, rows, results, *_), = read()
    assert (start, rows) == (10, 4) and held.rows_of(results["count"], rows, 1, 2)["signal"].tolist() == [1.0, 2.0]
    assert held.rows_of(results["count"], rows, 1, 2)["key"] == "k"
    assert held.rows_of(results["count"], rows, 1, 2)["said"] == (0, 1, 2, 3)
    assert held.rows_of(results["count"], rows, 1, 2)["code"] == {"count": "d"}
    with open(path, "rb") as f:
        assert pickle.load(f) == (held.VERSION,)        # nothing of the tools' code: an edited tool leaves the runs serving
        records = f.read()

    def begun_with(stamp):
        with open(path, "wb") as f:
            pickle.dump(stamp, f)
            f.write(records)
        return read()
    assert len(begun_with((held.VERSION, "a digest of the tools' folder"))) == 1       # as a file written before the stamp lost it
    assert begun_with((held.VERSION + 1,)) == [] and begun_with(held.VERSION) == []
    file = held.File(path)
    file.write(begun_with((held.VERSION,)))
    file.write([])
    assert read() == []
    with open(path, "wb") as f:
        f.write(b"not a pickle")
    assert read() == [] and held.File(str(tmp_path / "absent")).load() == []


def test_a_run_is_pickled_once_however_the_file_is_written_after(tmp_path):
    file = held.File(str(tmp_path / "doc.json.series"))
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
    never = run(40, fn=lambda: None)
    assert file.write([a, c, d, never]) == [never] and file.write([a, c, d, never]) == []     # left out once, the others' records standing
    back = held.File(file.path)
    kept = back.load()
    assert [(s, r["track"]["signal"].tolist()) for s, _, r, *_ in kept] == [(0, [0.0] * 3), (20, [20.0] * 3), (30, [30.0] * 3)]
    first = kept[0][2]["track"]["rows"]
    assert [len(t) for t in first] == [2, 0, 1] and first[0].dtype == tables[0].dtype
    assert [float(x) for x in kept[0][2]["track"]["scalars"]] == [0.0, 1.0, 2.0]
    with open(file.path, "r+b") as f:
        f.truncate(os.path.getsize(file.path) - 4)          # a write cut short in its last record
    kept = back.load()
    back.write([*kept, d])
    assert [s for s, *_ in held.File(file.path).load()] == [0, 20, 30]


def test_bytes_are_said_in_the_first_unit_that_holds_them_under_1024_and_a_badge_has_a_colour_for_no_other():
    assert [held.in_units(n) for n in (0, 1536, 3 << 30, 1 << 50)] == [("0", "B"), ("1.5", "KB"), ("3.0", "GB"), ("1024.0", "TB")]
    assert set(theme.HELD) <= set(held.UNITS)


def test_a_range_is_served_from_the_run_that_covers_it_under_the_chains_keys_and_the_limit_lets_go_of_left_keys_first():
    own = {"a": (0, 0), "b": (0, 0)}       # each reads its own row alone, so a run serves whatever walk asks
    now, moved = held.Chain({"a": "ka", "b": "kb"}, frozenset({"a"}), own), held.Chain({"a": "ka", "b": "kb2"}, frozenset({"a"}), own)
    walk = (0, 100)
    runs = held.Runs(18, lambda nid, r: len(r))       # a run of two nodes of three values counts six
    of = lambda start, rows, chain: {nid: {"signal": np.arange(start, start + rows, dtype=np.float32), "key": k, "gate": None}
                                     for nid, k in chain.keys.items()}
    hold = lambda start, rows, chain: runs.hold(start, rows, of(start, rows, chain), chain)
    assert hold(10, 4, now) and not hold(10, 4, now) and not runs.hold(10, 5, of(10, 4, now), now)
    assert hold(0, 20, now) and [run[:2] for run in runs] == [(0, 20)]      # the window's run, covered, went
    assert runs.over(12, 3, now, walk)["b"]["signal"].tolist() == [12.0, 13.0, 14.0] and runs.over(18, 5, now, walk) is None
    assert runs.over(12, 3, moved, walk) is None and runs.spans(moved) == [] and runs.spans(now) == [(0, 20)]
    part = runs.part(12, 3, moved, walk)
    assert list(part) == ["a"] and part["a"]["signal"].tolist() == [12.0, 13.0, 14.0]       # b is not stepped, nor under its key
    assert hold(30, 4, moved) and hold(40, 4, now) and len(runs) == 3
    assert runs.from_first_row("a", "ka")[:2] == (0, 20) and runs.from_first_row("b", "kb2") is None
    assert hold(50, 4, moved) and [run[0] for run in runs] == [0, 40, 50]       # 0 has the most rows of a under its key, what part hands a walk: the oldest other goes
    assert [(at, signal.tolist()) for signal, at, _ in runs.beside("a", "ka", 41, 2)] == [
        (0, [float(i) for i in range(20)]), (40, [40.0]), (43, [43.0]), (50, [50.0, 51.0, 52.0, 53.0])]
    gone = held.Chain({"a": "ka2", "b": "kb3"}, frozenset({"a"}), own)
    assert hold(60, 4, gone) and [run[0] for run in runs] == [40, 50, 60]       # no node of 0 is under a key the chain has: it goes first, however long
    assert not runs.hold(70, 4, {nid: {**r, "key": None} for nid, r in of(70, 4, gone).items()}, gone)      # under no key, good to no reader
    twice = held.Runs(18, lambda nid, r: len(r))
    again = lambda start, chain: twice.hold(start, 4, of(start, 4, chain), chain)
    assert again(10, now) and again(10, gone) and again(30, now) and again(50, now)     # two runs over the same rows: the later goes as itself, its arrays never compared
    assert [(run.start, run.results["b"]["key"]) for run in twice] == [(10, "kb"), (30, "kb"), (50, "kb")]
    full = held.Runs(6, lambda nid, r: len(r))        # room for one run
    assert full.hold(0, 4, of(0, 4, now), now) and full.hold(0, 4, of(0, 4, moved), moved)     # as long as the run of keys left, which goes
    assert not full.hold(0, 4, of(0, 4, now), moved) and [run.results["b"]["key"] for run in full] == ["kb2"]      # let go at once: nothing held changed
    assert full.hold(10, 4, of(10, 4, moved), moved)
    assert [run.start for run in full] == [10]      # of two the chain has as much of, as long, the one held last stays
    touching = held.Runs(100, lambda nid, r: len(r))
    assert touching.hold(0, 4, of(0, 4, now), now) and touching.hold(4, 4, of(4, 4, now), now)
    assert touching.spans(now) == [(0, 8)] and touching.over(2, 4, now, walk) is None       # held across two runs, served from neither


def test_a_run_serves_a_node_where_its_rows_read_the_same_of_the_run_as_of_the_walk_asking():
    chain = held.Chain({"travel": "kv", "track": "kt", "count": "kc"}, frozenset({"travel", "track", "count"}),
                       {"travel": (1, 0), "track": (None, 0), "count": (None, 0)})
    of = lambda start, rows: {nid: {"signal": np.arange(start, start + rows, dtype=np.float32) + (100 * (start > 0)), "key": k}
                              for nid, k in chain.keys.items()}       # a walk's values say where it began
    runs, window, clip = held.Runs(1 << 20, lambda nid, r: 0), (40, 50), (0, 100)
    assert runs.hold(40, 10, of(40, 10), chain) and runs.hold(0, 100, of(0, 100), chain) and len(runs) == 2     # neither stands in for the other
    assert not runs.hold(40, 10, of(40, 10), chain)
    seen = lambda got: {nid: r["signal"][0] for nid, r in got.items()}
    assert seen(runs.over(41, 5, chain, window)) == {"travel": 41.0, "track": 141.0, "count": 141.0}    # travel one past the window's first row from the clip's, as from either
    assert seen(runs.over(40, 5, chain, clip)) == {"travel": 40.0, "track": 40.0, "count": 40.0}
    assert seen(runs.over(40, 5, chain, window)) == {"travel": 140.0, "track": 140.0, "count": 140.0}
    only_clip = held.Runs(1 << 20, lambda nid, r: 0)
    only_clip.hold(0, 100, of(0, 100), chain)
    assert only_clip.over(40, 5, chain, window) is None and only_clip.part(40, 5, chain, window) == {}
    assert set(only_clip.part(41, 4, chain, window)) == {"travel"}       # track's rows of row 0 hand a walk from 40 nothing to step count from
    assert set(only_clip.over(41, 4, chain, clip)) == {"travel", "track", "count"}
    ends = held.Chain({"smooth": "ks"}, frozenset(), {"smooth": (2, 2)})
    short = held.Runs(1 << 20, lambda nid, r: 0)
    short.hold(0, 60, {"smooth": {"signal": np.zeros(60, np.float32), "key": "ks"}}, ends)        # a clip walk cut short at 60
    assert short.over(50, 7, ends, clip) is not None and short.over(50, 9, ends, clip) is None     # within its reach of 60, it read where the walk stopped
    assert short.over(50, 10, ends, (0, 60)) is not None
    inside = held.Runs(1 << 20, lambda nid, r: 0)
    inside.hold(20, 30, of(20, 30), chain, cut=(20, 50))         # a period's walk, from its first row
    assert seen(inside.over(30, 5, held.Chain({"track": "kt"}, frozenset({"track"}), {"track": (3, 0)}), (25, 60), (10, 60)))["track"] == 130.0
    assert inside.over(30, 5, chain, (20, 50), (20, 50)) is not None and inside.over(30, 5, chain, (20, 50)) is None
    whole = cut.Record("v")
    a, b = whole.cut(rows=(20, 50)), whole.cut(rows=(40, 70))      # two periods that overlap, under one key
    both = held.Chain({"detect": "kd", "track": "kt"}, frozenset({"track"}), {"detect": (0, 0), "track": (None, 0)})
    of_both = lambda start, rows: {"track": of(start, rows)["track"],
                                   "detect": {"signal": np.arange(start, start + rows, dtype=np.float32) + (100 * (start > 20)), "key": "kd"}}
    two = held.Runs(1 << 20, lambda nid, r: 0)
    assert two.hold(20, 30, of_both(20, 30), both, cut=(20, 50)) and two.hold(40, 30, of_both(40, 30), both, cut=(40, 70))
    spans = lambda nid, record: [(at, r["signal"][0], len(r["signal"])) for at, r in two.listed(nid, both, record, 100).parts]
    assert two.listed("detect", both, a, 100).record is a and two.listed("detect", both, b, 100).record is b
    assert spans("detect", a) == [(20, 20.0, 30)]
    assert spans("detect", b) == [(40, 40.0, 10), (50, 150.0, 20)]     # the rows they share, which read no edge, from the run that began earliest
    assert spans("track", a) == [(20, 120.0, 30)] and spans("track", b) == [(40, 140.0, 30)]    # read where each walk began
    assert spans("detect", whole) == [(20, 20.0, 30), (50, 150.0, 20)] and spans("track", whole) == []    # what read no edge is the footage's too


def test_a_node_is_marked_by_the_code_its_held_result_was_made_under_and_so_is_every_node_below_it():
    chain = held.Chain({"track": "kt", "count": "kc"}, frozenset({"track"}))
    above = {"video": [], "blobs": ["video"], "track": ["blobs"], "count": ["track"], "drawn": ["blobs"], "other": ["video"]}
    now = {"blobs": "b", "track": "t", "count": "c", "drawn": "d", "other": "o"}
    run = lambda code, keys=chain.keys: [(0, 2, {nid: {"signal": np.zeros(2), "key": k, **code} for nid, k in keys.items()}, 0)]
    marked = lambda code, now=now, **more: held.marked(run(code, **more), chain, now, above)
    made = {"blobs": "b", "track": "t", "count": "c"}
    assert marked({"code": made}) == set() and held.marked([], chain, now, above) == set()
    assert marked({"code": made}, {**now, "track": "t2"}) == {"track", "count"}        # blobs above it and other, of another tool, are not
    assert marked({"code": made}, {**now, "blobs": "b2"}) == {"blobs", "track", "count", "drawn"}
    assert marked({"code": made}, {**now, "other": "o2", "drawn": "d2"}) == set()      # neither is above a held result
    assert marked({}) == marked({"code": None}) == {"blobs", "track", "count", "drawn"}     # a result that says nothing of its code
    assert marked({}, keys={"track": "left", "count": "left"}) == set()                 # held under keys the chain has left
