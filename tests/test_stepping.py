"""The step facet: the registry lists it and reports who offers it without calling a tool,
tests/stepping.py's oracle passes a tool whose step agrees with its run and names the row where a
peeking one diverges, the plan says of each chain node whether the walk steps it or runs it whole
and which node ended the prefix, and the walk steps the prefix once a row, a served head's rows
included, runs the suffix per emit, restarts a changed node from the window's first row, and
emits at one cadence over both ranges."""
import os
import time
from dataclasses import fields
from types import SimpleNamespace

import numpy as np
import pytest

from sieve_player import document as D
from sieve_player import registry
from sieve_player.graph import Graph, nbytes
from sieve_player.plan import base_key, plan
from sieve_player.worker import run_chain
from sieve_player.registry.__main__ import check, report
from tests import stepping
from tools import bake, blobs, gray, kinematics, smooth, track, tracks_filter, transitions

TOOLS = {t.NAME: t for t in (bake, blobs, gray, kinematics, smooth, track, tracks_filter, transitions)}
BASE = base_key("fake.mp4", "bgr")

SUMMING = SimpleNamespace(NAME="summing",
                          run=lambda s, p: {"signal": np.cumsum(np.asarray(s.data, np.float32)).astype(np.float32)},
                          step=lambda st, row, i, p: (np.float32((st or 0) + row), {"signal": np.float32((st or 0) + row)}))
PEEKING = SimpleNamespace(NAME="peeking",
                          run=lambda s, p: {"signal": np.array([max(s.data[i:]) for i in range(len(s.data))], np.float32)},
                          step=lambda st, row, i, p: (None, {"signal": np.float32(row)}))


def test_registry_lists_step_and_reports_it_without_calling_a_tool(capsys, monkeypatch):
    assert "step" in registry.FACETS and registry.hint("step").startswith("def step(state, row, i, params)")
    assert callable(registry.probe(track, "step")) and registry.probe(smooth, "step") is None
    for tool in (track, smooth):
        for facet in ("run", "step"):
            monkeypatch.setattr(tool, facet, lambda *a: pytest.fail("the registry called a tool"), raising=False)
    monkeypatch.setattr(smooth, "step", None)
    report(["tools"])
    lines = capsys.readouterr().out.splitlines()
    said = {name: next(l.split()[1] for l in lines[lines.index(next(l for l in lines if l.startswith(f"{name}  ("))):] if l.split()[0] == "step")
            for name in ("track", "smooth")}
    assert said == {"track": "defined", "smooth": "unsaid"}
    assert check() == 0


def test_the_oracle_passes_a_tool_that_steps_and_names_where_a_peeking_one_diverges():
    assert stepping.hold(SUMMING, [1.0, 3.0, 2.0], {})["signal"].tolist() == [1.0, 4.0, 6.0]
    with pytest.raises(AssertionError, match="over the whole at row 1"):
        stepping.hold(PEEKING, [3.0, 1.0, 2.0], {})
    assert stepping.same(np.float32(1), np.float32(1)) and not stepping.same(np.float32(1), np.float64(1))
    assert stepping.same(np.array([np.nan]), np.array([np.nan])) and not stepping.same(np.zeros(1), np.zeros((1, 1)))


def verdicts(p):
    return {nid: (p.entries[nid].steps, p.entries[nid].whole_by) for nid in p.chain}


def test_the_plan_names_where_stepping_ends_and_the_node_that_ended_it():
    """A stepping tool under a tool that runs whole runs whole, and so does every node after it,
    each naming the node that ended the prefix; a tool that does not step names nothing; the
    standing of a whole-run node stays empty since it runs."""
    p = plan(D.from_tools([gray, blobs, track, tracks_filter, kinematics, transitions]), TOOLS, BASE)
    assert p.chain == ["track", "tracks-filter", "kinematics", "transitions"]
    assert verdicts(p) == {"track": (True, None), "tracks-filter": (False, None),
                           "kinematics": (False, "tracks-filter"), "transitions": (False, "tracks-filter")}
    assert all(p.entries[nid].standing == "" for nid in p.chain)
    p = plan(D.from_tools([gray, blobs, track, kinematics, transitions]), TOOLS, BASE)
    assert p.chain == ["track", "kinematics", "transitions"] and verdicts(p) == {nid: (True, None) for nid in p.chain}
    assert not any(e.steps or e.whole_by for nid, e in p.entries.items() if nid not in p.chain)


def test_a_served_series_head_is_stepped_into_the_chain_under_it():
    """A baked blobs node served in place of the walked head hands its rows one at a time, so the
    plan steps it and the stepping chain under it as it would a walked head's."""
    doc = D.from_tools([gray, blobs, bake, track, kinematics])
    assert doc.source("track").src == "bake"
    live = plan(doc, TOOLS, BASE)
    assert live.chain == ["track", "kinematics"] and verdicts(live) == {"track": (True, None), "kinematics": (True, None)}
    D.land(doc.node("bake"), D.Bake("k", "blobs", True, (0, 9), 1, 30.0, 30.0, (), 10))
    served = plan(doc, TOOLS, BASE)
    assert served.heads == ["bake"] and served.chain == ["bake", "track", "kinematics"]
    assert verdicts(served) == {nid: (True, None) for nid in served.chain}
    assert all(served.entries[nid].standing == "" for nid in served.chain)


# -- the walk steps ------------------------------------------------------
BLOBS = np.dtype([("cx", "<f4"), ("cy", "<f4"), ("area", "<f4")])


def blobs_at(f, p):
    """A blobs table from a gray frame whose value is the row plus one: one to three records a row, drifting right."""
    row = int(f.flat[0]) - 1
    return np.array([(10.0 * j + 0.5 * row, 0.0, 5.0) for j in range(row % 3 + 1)], dtype=BLOBS)


def frame_tool(name, expects, produces, fn):
    t = SimpleNamespace(NAME=name, KIND="frame", EXPECTS=expects, PRODUCES=produces, DEFAULTS={})
    t.run = lambda frames, row, params: fn(frames(row), params)
    return t


def equal(a, b):
    """Two chain results, {node: result}, equal field for field, arrays by `stepping.same`."""
    if a.keys() != b.keys():
        return False
    for nid in a:
        if a[nid].keys() != b[nid].keys():
            return False
        for f in a[nid]:
            x, y = a[nid][f], b[nid][f]
            if not (stepping.same(x, y) if isinstance(x, np.ndarray) or isinstance(y, np.ndarray) else x == y):
                return False
    return True


def wait_for(cond, timeout=10.0):
    from PySide6.QtWidgets import QApplication
    t = time.perf_counter()
    while time.perf_counter() - t < timeout:
        QApplication.processEvents()
        if cond():
            return
        time.sleep(0.005)
    pytest.fail(f"not within {timeout} s")


def stepping_worker(g, every, start, length):
    """A worker started on the window, with the lists its seriesReady results and the probe's events land in."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])
    events, got = [], []
    g.on_event = events.append
    w = Worker(g, every=every)
    w.seriesReady.connect(lambda r, s, fps: got.append(r))
    w.set_window(start, length)
    w.start()
    return w, events, got


def steps_and_runs(events, chain):
    steps = [(ev.node, ev.row) for ev in events if ev.kind == "step"]
    runs = [(ev.node, ev.row) for ev in events if ev.kind == "run" and ev.node in chain]
    return steps, runs


def test_the_walk_steps_the_prefix_once_a_row_runs_the_suffix_per_emit_and_matches_the_whole_chain():
    """track and kinematics step, tracks-filter runs whole: each stepping node is stepped at each row
    exactly once and never run, the suffix runs once per cadence row and at the window's end, and
    every emitted result equals the whole-stack chain's over the same rows. A rewalk off the memo
    steps each row once again and runs nothing of the prefix; the stepped state is dropped with the
    walk, nothing lands in the memo under the stepped node's key, and the results' bytes count
    toward the walk's with the stack's. A change on the prefix's head steps it and the node under
    it again from the window's first row; a change after the prefix reruns the suffix alone."""
    from tests.test_graph import Dec, TOOLS as FRAME, gray as fgray
    table = frame_tool("table", "gray", "blobs", blobs_at)
    tools = {**FRAME, "table": table, "track": track, "kinematics": kinematics, "tracks-filter": tracks_filter}
    doc = D.from_tools([fgray, table, track, kinematics, tracks_filter])
    doc.node("track").band = (1.0, 2.0)      # rows with three tracks are gated out, so kinematics is fed emptied rows there
    g = Graph(doc, Dec(), tools)
    assert g.chain == ["track", "kinematics", "tracks-filter"] and [g.entry(n).steps for n in g.chain] == [True, True, False]
    w, events, got = stepping_worker(g, 3, 0, 7)
    wait_for(lambda: got and len(got[-1]["tracks-filter"]["signal"]) == 7)
    steps, runs = steps_and_runs(events, g.chain)
    assert sorted(steps) == sorted([(n, r) for n in ("track", "kinematics") for r in range(7)])
    assert runs == [("tracks-filter", 2), ("tracks-filter", 5), ("tracks-filter", 6)]
    assert [len(r["track"]["signal"]) for r in got] == [3, 6, 7]
    for r in got:
        n = len(r["track"]["signal"])
        assert equal(r, run_chain(w.graph, w._win.stack[:n], 0, n, {}))
    raw = g.entry("track").raw_key
    assert not [k for d in (g.memo._big, g.memo._small, g.memo._pinned) for k in d if k[0] == raw]
    stack_bytes = sum(nbytes(row) for row in w._win.stack)
    assert w._win.bytes == stack_bytes + sum(ev.bytes for ev in events if ev.kind == "step") and w._win.bytes > stack_bytes
    held = {n: w._win.stepped[n] for n in ("track", "kinematics")}      # the objects, since a freed one's id comes back
    events.clear()
    got.clear()
    w.invalidate()
    wait_for(lambda: got and len(got[-1]["tracks-filter"]["signal"]) == 7)
    steps, runs = steps_and_runs(events, g.chain)
    assert sorted(steps) == sorted([(n, r) for n in ("track", "kinematics") for r in range(7)]) and not [r for r in runs if r[0] != "tracks-filter"]
    assert not [ev for ev in events if ev.kind == "run" and ev.node in ("gray", "table")]        # the memo held the frames
    assert not [n for n in held if w._win.stepped[n] is held[n]]
    events.clear()
    got.clear()
    doc.node("track").params["max_step"] = 9.0
    g.sync()
    w.rerun_series()
    wait_for(lambda: got)
    steps, runs = steps_and_runs(events, g.chain)
    assert [r for n, r in steps if n == "track"] == list(range(7)) and [r for n, r in steps if n == "kinematics"] == list(range(7))
    assert runs == [("tracks-filter", 6)] and equal(got[-1], run_chain(w.graph, w._win.stack, 0, 7, {}))
    events.clear()
    got.clear()
    doc.node("tracks-filter").params["lo"] = "2"
    g.sync()
    w.rerun_series()
    wait_for(lambda: got)
    steps, runs = steps_and_runs(events, g.chain)
    assert steps == [] and runs == [("tracks-filter", 6)] and equal(got[-1], run_chain(w.graph, w._win.stack, 0, 7, {}))
    w.stop()


def test_a_served_series_heads_rows_step_the_chain_under_it_one_at_a_time(in_store):
    """A baked blobs file served in place of the walked head is stepped a row at a time, through
    bake's own step, and track under it is stepped once per row and never handed the file's rows whole."""
    from sieve_player import store
    from sieve_player.writers import TablesWriter
    from tests.test_graph import Dec, TOOLS as FRAME, gray as fgray
    table = frame_tool("table", "gray", "blobs", blobs_at)
    tools = {**FRAME, "table": table, "bake": bake, "track": track}
    doc = D.from_tools([fgray, table, bake, track])
    os.makedirs(in_store)
    wr = TablesWriter(store.current().place("k", ".tables"), "blobs", 30.0, "lossless")
    for r in range(10):
        wr.write(blobs_at(np.full((4, 6), r + 1, np.uint8), {}))
    wr.close()
    side = store.current().write_sidecar(store.Sidecar("k", "blobs", "doc", "bake", [0, 9], 1, 30.0, 30.0, [], "lossless"))
    D.land(doc.node("bake"), side.bake(10))
    dec = Dec()
    dec.cache_limit = 0        # the reader takes the plate decoder's limit, which the fake has none of
    g = Graph(doc, dec, tools, open_bake=store.current().open_bake)
    assert g.heads == ["bake"] and g.chain == ["bake", "track"] and g.walk is None
    w, events, got = stepping_worker(g, 4, 0, 10)
    wait_for(lambda: got and len(got[-1]["track"]["signal"]) == 10)
    steps, runs = steps_and_runs(events, g.chain)
    assert sorted(steps) == sorted([(n, r) for n in ("bake", "track") for r in range(10)]) and runs == []
    assert not [ev for ev in events if ev.node in ("gray", "table") and ev.serves == "walk"]
    assert [len(r["track"]["signal"]) for r in got] == [4, 8, 10]
    assert equal(got[-1], run_chain(w.graph, None, 0, 10, {}))
    w.stop()
    g.close()


def test_the_cadence_is_one_setting_read_over_both_ranges_and_the_throttle_is_gone():
    from sieve_player import worker as W
    from tests.test_graph import Dec, TOOLS as FRAME, gray as fgray, tool
    assert not hasattr(W, "CHAIN_SHARE") and "share" not in {f.name for f in fields(W._Walk)}
    head = tool("head", kind="series", produces="signal")
    head.run = lambda series, params: {"signal": np.asarray(series.data, np.float64).reshape(len(series.data), -1)[:, 0]}
    head.fold = lambda frame: np.asarray([float(frame.mean())])
    for every, windows, clips in ((2, 3, 5), (5, 2, 2)):
        g = Graph(D.from_tools([fgray, head]), Dec(), {**FRAME, "head": head})
        w, events, got = stepping_worker(g, every, 0, 6)
        clip = []
        w.clipReady.connect(lambda r, s, fps: clip.append(r))
        w.walk_clip()
        wait_for(lambda: clip and len(clip[-1].get("head", {}).get("signal", ())) == 10)
        w.stop()
        assert (len(got), len(clip)) == (windows, clips), every
