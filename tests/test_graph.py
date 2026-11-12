"""The runtime: wiring, fan-out, keys, rewiring under a worker, and the series node."""
import threading
import time
from contextlib import nullcontext
from dataclasses import fields
from types import SimpleNamespace as Tool

import numpy as np
import pytest

from sieve_player import document as D
from sieve_player.decoder import EndOfStream
from sieve_player.graph import Event, Graph, Stats, gated, nbytes
from sieve_player.plan import base_key, plan


class Dec:
    path, fps, count = "fake.mp4", 30.0, 10
    decodes = seeks = reads = cache_hits = cache_bytes = 0
    step_ms = seek_ms = None
    output, scale = "bgr", 1.0

    def read(self, row):
        if row >= self.count:
            raise EndOfStream(row)
        self.decodes += 1
        return np.full((4, 6, 3) if self.output == "bgr" else (4, 6), row, np.uint8)

    def cached(self, row):
        return None

    scrub = staticmethod(nullcontext)


def tool(name, expects="gray", produces="gray", fn=None, kind="frame"):
    t = Tool(NAME=name, KIND=kind, EXPECTS=expects, PRODUCES=produces, DEFAULTS={"k": 1}, runs=0)

    def run(frames, row, params):
        t.runs += 1
        return (fn or (lambda f, p: f))(frames(row), params)
    t.run = run
    return t


gray = tool("gray", "bgr", "gray", lambda f, p: f[..., 0] + p["k"])
add = tool("add", fn=lambda f, p: f + p["k"])
same = tool("same", fn=lambda f, p: f)
TOOLS = {t.NAME: t for t in (gray, add, same)}


def fan_out():
    """video -> gray -> {add, same}"""
    doc = D.from_tools([gray, add])
    doc.add_node("same", (0, 300))
    doc.connect("gray", "same")
    return doc


def test_built_from_document_and_decoder():
    dec, doc = Dec(), fan_out()
    g = Graph(doc, dec, TOOLS)
    assert g.shown == "add" and g.walk == "add" and g.over is None
    dec.count = 7                                                      # the decoder found the header lied
    assert g.count == 7
    k = g.key("gray")
    doc.video_node().params["output"] = "gray"                        # the video hands out gray: the decoder is told, every key moves
    g.sync()
    assert dec.output == "gray" and g.key("gray") != k and not g.fed("gray") and g.compute("video", 0).shape == (4, 6)
    assert g.key("video") == base_key("fake.mp4", "gray") and "scale" not in doc.video_node().params


def test_a_document_with_a_scaled_video_node_reads_the_rescaled_plane_through_the_inserted_node():
    from tools import rescale
    doc = D.from_tools([gray, add])
    d = doc.to_dict()
    d["version"], d["nodes"][0]["params"] = 1, {"scale": 0.5}
    g = Graph(D.Document.from_dict(d), Dec(), {**TOOLS, "rescale": rescale})
    assert g.source("gray") == "rescale" and g.compute("rescale", 0).shape == (2, 3, 3) and g.compute("add", 0).shape == (2, 3)


def test_a_band_zeroes_the_plane_outside_it_after_run_and_keys_the_node():
    doc = fan_out()
    g = Graph(doc, Dec(), TOOLS)
    kg, k = g.key("gray"), g.key("add")
    g.compute("gray", 6)
    runs = gray.runs
    doc.node("gray").band = (3.0, 5.0)        # gray is row + 1
    g.sync()
    assert g.key("gray") != kg and g.key("add") != k
    assert (g.compute("gray", 6) == 0).all() and (g.compute("gray", 2) == 3).all()   # zeroed, kept
    runs += 1                                                                          # row 2 is new; row 6 was not rerun
    assert (g.compute("gray", 6, raw=True) == 7).all() and gray.runs == runs         # the memo holds the raw plane; the band is on read
    assert (g.compute("add", 6) == 1).all()                                           # downstream reads the banded plane
    assert (g.peek(6, "gray") == 0).all()
    doc.node("gray").band = (5.0, 3.0)        # inside out: the middle goes
    g.sync()
    assert (g.compute("gray", 3) == 0).all() and (g.compute("gray", 6) == 7).all()


def test_overlay_is_a_one_plane_node_the_display_peeks_beside_the_shown():
    doc = fan_out()
    doc.overlay = "same"
    g = Graph(doc, Dec(), TOOLS)
    assert g.over == "same" and g.peek(3, "same") is None
    g.compute("same", 3)
    assert (g.peek(3, "same") == 4).all()
    doc.overlay = "video"      # bgr: not a plane the frame can be heated with
    g.sync()
    assert g.over is None


def test_reads_the_video_node():
    g = Graph(fan_out(), Dec(), TOOLS)
    assert g.compute("video", 3).shape == (4, 6, 3)
    assert (g.compute("gray", 3) == 4).all()


def test_fan_out_computes_once():
    g, before = Graph(fan_out(), Dec(), TOOLS), gray.runs
    g.compute("add", 0), g.compute("same", 0)
    assert gray.runs == before + 1 and (g.compute("add", 0) == g.compute("same", 0) + 1).all()


def test_unwired_computes_none_downstream():
    doc = fan_out()
    doc.disconnect("gray")
    g = Graph(doc, Dec(), TOOLS)
    assert g.compute("gray", 0) is None and g.compute("add", 0) is None and g.compute("same", 0) is None


def test_a_second_input_is_read_by_name_keyed_and_required():
    diff = tool("diff", fn=lambda f, p: f)
    diff.INPUTS = {"bg": "gray"}
    diff.run = lambda frames, row, params: frames(row) - frames(row, "bg")
    doc = fan_out()                                  # video -> gray -> {add, same}
    doc.add_node("diff", (0, 400))
    doc.connect("add", "diff")
    g = Graph(doc, Dec(), {**TOOLS, "diff": diff})
    assert g.compute("diff", 2) is None and not g.fed("diff")                 # bg unwired: unfed, as a missing first input is
    assert [p.where for p in D.validate(doc, {**TOOLS, "diff": diff}) if p.kind == "unfed"] == ["diff"]
    diff.OPTIONAL = ("bg",)
    diff.run = lambda frames, row, params: frames(row) if frames(row, "bg") is None else frames(row) - frames(row, "bg")
    g.sync()
    assert g.fed("diff") and (g.compute("diff", 2) == 4).all()                # optional and unwired: read as None; add alone
    assert not [p for p in D.validate(doc, {**TOOLS, "diff": diff}) if p.kind == "unfed"]
    doc.connect("same", "diff", "bg")
    g.sync()
    k = g.key("diff")
    assert (g.compute("diff", 2) == 1).all()                                  # add is gray + 1, same is gray
    doc.node("same").params["k"] = 2                                          # no effect on same's output, but behind bg
    g.sync()
    assert g.key("diff") != k and D.inputs_of(doc, {**TOOLS, "diff": diff}, "diff") == [("in", ("gray",)), ("bg", ("gray",))]


def test_a_read_after_the_node_moved_on_or_a_halt_is_cancelled():
    from sieve_player.graph import Cancelled
    doc = fan_out()
    g = Graph(doc, Dec(), TOOLS)
    seen = []

    def many(frames, row, params):      # a composite: many reads in one run
        for r in range(8):
            seen.append(r)
            frames(r)
            if r == 2:
                doc.node("gray").params["k"] = 5        # the user moves a knob upstream mid-build
                g.sync()
        return frames(0)

    add.run, keep = many, add.run
    try:
        kinds = []
        g.on_event = lambda ev: kinds.append(ev.kind) if ev.node == "add" else None
        with pytest.raises(Cancelled):
            g.compute("add", 0)
        assert seen == [0, 1, 2, 3] and kinds[-1] == "cancel" and g.memo.get((g.key("add"), 0)) is None
        g.halt = True
        with pytest.raises(Cancelled):
            g.compute("same", 1)
    finally:
        add.run, g.halt = keep, False


def test_a_static_node_is_computed_once_held_once_and_peeked_at_any_row():
    const = tool("const", fn=lambda f, p: np.full_like(f, p["k"]))
    const.STATIC = True
    doc = fan_out()
    doc.add_node("const", (0, 400), {"k": 1})
    doc.connect("gray", "const")
    g = Graph(doc, Dec(), {**TOOLS, "const": const}, memo_bytes=200)
    runs, held = const.runs, g.memo.bytes
    assert (g.compute("const", 0) == 1).all() and (g.compute("const", 7) == 1).all() and const.runs == runs + 1
    assert g.memo.bytes == held + 4 * 6 + 4 * 6                       # the plane once, and gray at row 0 once
    assert g.peek(9, "const") is not None and g.density("const", 3) is g.density("const", 8)
    for row in range(10):                                                 # a walk past the memo's limit evicts every plane but the static one
        g.compute("add", row)
    assert g.memo.evictions and g.peek(9, "const") is not None and g.compute("const", 5) is not None and const.runs == runs + 1
    old, fold = (g._plan["const"].raw_key, None), g.density("const", 3)
    g.sync()
    assert g.memo.get(old) is not None and g.density("const", 3) is fold   # a sync that leaves the node alone keeps both pins
    doc.node("const").params["k"] = 2
    g.sync()
    assert g.memo.get(old) is None and g.density("const", 3) is not fold   # the plan they were pinned under is gone
    assert (g.compute("const", 7) == 2).all() and const.runs == runs + 2


def test_key_follows_params_and_wiring():
    doc = fan_out()
    g = Graph(doc, Dec(), TOOLS)
    k_add, k_same = g.key("add"), g.key("same")
    doc.node("add").params["k"] = 2
    g.sync()
    assert g.key("add") != k_add and g.key("same") == k_same         # own change; an unrelated node's change
    k_add = g.key("add")
    doc.node("gray").params["k"] = 2
    g.sync()
    assert g.key("add") != k_add                                      # upstream change
    k_add = g.key("add")
    doc.connect("video", "add")
    g.sync()
    assert g.key("add") != k_add                                      # rewired


def test_rewire_during_walk():
    slow = tool("slow", fn=lambda f, p: time.sleep(0.001) or f + 100)
    doc = fan_out()
    doc.add_node("slow", (0, 400))
    doc.connect("add", "slow")
    tools = {**TOOLS, "slow": slow}
    g = Graph(doc, Dec(), tools)
    errors = []

    def walk():
        try:
            for r in range(300):
                g.compute("slow", r % 10)
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=walk)
    t.start()
    time.sleep(0.02)
    doc.connect("gray", "slow")
    g.sync()
    t.join()
    assert not errors and (g.compute("slow", 0) == g.compute("gray", 0) + 100).all()


def test_series_nodes_reading_the_walked_node_are_all_heads():
    """Two series nodes on gray both run; one on a different frame node is unrun; the fold is shared
    only when the heads agree on it."""
    s1, s2, s3 = (tool(n, kind="series", produces=None) for n in ("s1", "s2", "s3"))
    s1.fold = s2.fold = lambda frame: np.asarray([frame.sum()])
    doc = D.from_tools([gray, s1, s2])
    doc.add_node("add", (0, 300)); doc.connect("gray", "add")
    doc.add_node("s3", (0, 400)); doc.connect("add", "s3")
    g = Graph(doc, Dec(), {**TOOLS, "s1": s1, "s2": s2, "s3": s3})
    assert g.series == "s1" and g.heads == g.chain == ["s1", "s2"] and g.unrun_series == ["s3"] and g.walk == "gray"
    assert g.fold is s1.fold and g.walk_row(2).tolist() == [24 * 3]
    s2.fold = lambda frame: np.asarray([frame.max()])
    g.sync()
    assert g.fold is None and g.walk_row(2).shape == (4, 6)
    doc.connect("video", "s1")                  # "bgr" into a series node that expects "gray"
    g.sync()
    assert g.walk is None


def test_series_chain_runs_on_from_the_head():
    """A series node producing a signal feeds one expecting it; the chain is in run order, and a
    wire whose types do not fit ends it."""
    head = tool("head", kind="series", produces="signal")
    s1, s2 = tool("s1", kind="series", expects="signal", produces="signal"), tool("s2", kind="series", expects="signal", produces="signal")
    doc = D.from_tools([gray, head, s1, s2])
    doc.node("s1").band = (1.0, 2.0)
    tools = {**TOOLS, "head": head, "s1": s1, "s2": s2}
    g = Graph(doc, Dec(), tools)
    assert g.chain == ["head", "s1", "s2"] and g.walk == "gray" and not g.unrun_series
    assert [(nid, band, src) for nid, _, _, band, src in g.series_chain()] == [("head", None, "gray"), ("s1", (1.0, 2.0), "head"), ("s2", None, "s1")]
    doc.connect("gray", "s2")                   # "gray" into a node that expects "signal": off the chain, unrun
    g.sync()
    assert g.chain == ["head", "s1"] and g.unrun_series == ["s2"]


def test_a_series_band_gates_the_signal_and_zeroes_what_the_next_reads():
    """The gate is the player's, not the tool's: the result keeps the tool's signal whole and gains
    the gate; the feed downstream is zeroed outside the band, inside it once lo is above hi; no
    band keeps every row; a result without a signal feeds nothing."""
    sig = np.array([0.0, 2.0, 5.0, 9.0, 20.0], np.float32)
    r, feed = gated({"signal": sig}, (1.0, 10.0))
    assert r["gate"].tolist() == [False, True, True, True, False] and r["signal"] is sig
    assert feed.tolist() == [0.0, 2.0, 5.0, 9.0, 0.0]
    r, feed = gated({"signal": sig}, (10.0, 1.0))
    assert r["gate"].tolist() == [True, False, False, False, True] and feed.tolist() == [0.0, 0.0, 0.0, 0.0, 20.0]
    r, feed = gated({"signal": sig}, None)
    assert r["gate"].all() and feed.tolist() == sig.tolist()
    r, feed = gated({"signal": np.array([-3.0, 0.0, 4.0])}, None)         # no band gates nothing, a negative row included
    assert r["gate"].all() and feed.tolist() == [-3.0, 0.0, 4.0]
    assert gated({"other": 1}, (0.0, 1.0)) == ({"other": 1}, None)


def test_one_compute_sees_one_plan():
    """A sync between a node's run() starting and its frames(row) call that leaves the node's key
    alone: the run reads through the plan it began in, finishes, and is memoized under that key. A
    sync that changes the key cancels the read instead; see the cancellation test."""
    doc = fan_out()
    g = Graph(doc, Dec(), TOOLS)

    def run(frames, row, params):
        doc.node("same").params["k"] = 50       # a sibling changes while this node is mid-run
        g.sync()
        return frames(row) + params["k"]
    add.run, old = run, add.run
    try:
        k_old = g.key("add")
        v = g.compute("add", 0)
        assert (v == 0 + 1 + 1).all()
        assert g.key("add") == k_old and g.compute("add", 0) is v        # served from the memo, not recomputed
    finally:
        add.run = old


def test_walk_row_is_the_walked_node_through_the_heads_fold():
    """The worker stacks what the series tool asked for: the row through fold() when it has one, the
    frame itself when it has not, and None where nothing reaches the walked node."""
    head = tool("head", kind="series", produces="signal")
    head.fold = lambda f: np.array([f.sum(), f.size])
    doc = D.from_tools([gray, head])
    g = Graph(doc, Dec(), {**TOOLS, "head": head})
    assert g.walk_row(3).tolist() == [(3 + 1) * 24, 24]
    del head.fold
    assert (g.walk_row(3) == g.compute("gray", 3)).all()
    doc.connect("video", "head")
    g.sync()
    assert g.walk_row(3) is None


def test_probe_emits_once_per_run_exclusive_of_what_the_run_reads():
    """gray and add each wait; add reads gray. The figure add gets is its own wait, not the pair's."""
    slow_gray = tool("gray", "bgr", "gray", lambda f, p: (time.sleep(0.01), f[..., 0])[1])
    slow_add = tool("add", fn=lambda f, p: (time.sleep(0.01), f + 1)[1])
    g = Graph(D.from_tools([slow_gray, slow_add]), Dec(), {t.NAME: t for t in (slow_gray, slow_add)})
    events = []
    g.on_event = events.append
    for r in range(3):
        g.compute("add", r)
    assert sorted((ev.node, ev.row) for ev in events) == sorted((n, r) for n in ("video", "gray", "add") for r in range(3))
    ms = {ev.node: ev.ms for ev in events if ev.row == 0}
    assert ms["add"] < ms["gray"] + ms["add"] and ms["add"] < 15
    assert {(ev.kind, ev.bytes) for ev in events if ev.node == "add"} == {("run", 4 * 6)} and events[0].key == g.key("video")
    g.compute("add", 0)
    g.compute("video", 0)
    assert [(ev.node, ev.kind) for ev in events[9:]] == [("video", "decode")]   # a memo hit is not a run; the video's read is a read
    g.sync()
    assert events[-1].kind == "sync" and len(events) == 11                     # a boundary, between the runs either side
    g.doc.node("add").params["k"] = 2
    g.sync()
    before, after = (ev.keys for ev in events if ev.kind == "sync")
    assert [n for n in after if after[n] != before[n]] == ["add"]              # what the drag changed, derived from two boundaries
    stats = Stats(g)                                                           # chains onto the list
    with pytest.raises(IndexError):
        g.compute("add", 10)                                                   # past the fake stream's end: the video read raises
    assert [(ev.node, ev.kind, ev.bytes) for ev in events[-3:]] == [("video", "error", 0), ("gray", "error", 0), ("add", "error", 0)]
    assert "video" not in stats.snapshot()["nodes"]                            # a failed run is in the stream, not in the means


def test_an_event_is_read_by_name_and_refused_short():
    full = {f.name: None for f in fields(Event)} | {"node": "add", "kind": "run", "ms": 1.0}
    with pytest.raises(TypeError):
        Event(**{k: v for k, v in full.items() if k != "ms"})       # a field missing: no default fills it in
    stats = Stats(Graph(fan_out(), Dec(), TOOLS))
    with pytest.raises(AttributeError):
        stats.event(tuple(full.values()))                           # a tuple is not an event; nothing is read by position
    stats.event(Event(**full))
    assert stats.snapshot()["nodes"]["add"]["n"] == 1


def test_events_carry_start_thread_and_cpu_so_a_reader_sees_overlap_and_waiting():
    """Two threads each run a tool that sleeps; the events' starts and durations alone show the
    runs overlapped, the thread names say which was whose, and a sleep is wall time with no CPU."""
    nap = tool("add", fn=lambda f, p: (time.sleep(0.03), f + 1)[1])
    g = Graph(D.from_tools([gray, nap]), Dec(), {**TOOLS, "add": nap})
    events = []
    g.on_event = events.append
    ts = [threading.Thread(target=g.compute, args=("add", r), name=f"t{r}") for r in range(2)]
    [t.start() for t in ts], [t.join() for t in ts]
    a, b = sorted((ev for ev in events if ev.node == "add"), key=lambda ev: ev.t)
    assert {a.thread, b.thread} == {"t0", "t1"} and b.t < a.t + a.ms / 1000       # b began before a ended
    assert a.cpu_ms < a.ms / 3 and 25 < a.ms < 100
    assert all(ev.t >= a.t for ev in events if ev.thread == a.thread and ev.node != "add")   # its reads started inside it, not before


def test_events_say_whether_they_served_the_scrub_or_the_walk():
    """The worker marks what it is doing; a display row asked for mid-walk comes back marked the
    scrub's among the walk's rows, on a thread named for the worker. Off the worker, nothing is marked."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])
    slow = tool("add", fn=lambda f, p: (time.sleep(0.005), f + 1)[1])
    g = Graph(D.from_tools([gray, slow]), Dec(), {**TOOLS, "add": slow})
    events = []
    g.on_event = events.append
    g.compute("add", 0)
    w = Worker(g)
    w.set_window(0, 10)
    w.start()
    time.sleep(0.015)
    w.request_row(7)
    for _ in range(500):
        if any(ev.node == "add" and ev.row == 9 for ev in events):
            break
        time.sleep(0.01)
    w.stop()
    served = {(ev.row, ev.serves) for ev in events if ev.node == "add"}
    assert (0, None) in served and (7, "scrub") in served and (9, "walk") in served
    assert [(ev.row, ev.length) for ev in events if ev.kind == "progress"] == [(i, 10) for i in range(1, 11)]
    assert {ev.thread for ev in events if ev.serves} == {"worker"}


def test_stats_counts_everything_over_a_short_walk(tmp_path):
    import cv2
    from sieve_player.decoder import Decoder
    path = str(tmp_path / "v.avi")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for i in range(40):
        w.write(np.full((48, 64, 3), i, np.uint8))
    w.release()
    doc = D.from_tools([gray, add], path)
    g = Graph(doc, Decoder(path, cache_bytes=40 << 10), TOOLS, memo_bytes=40 << 10)   # room for a few rows, not the walk: both stores evict
    stats = Stats(g)
    events = []
    g.on_event = lambda ev: (events.append(ev), stats.event(ev))
    g.compute("add", 30)                      # a jump: one seek
    for r in range(8):
        g.compute("add", r)
        g.progress(r + 1, 8)
    g.compute("add", 7)                       # a memo hit: the last row walked is still held
    n = len(events)
    g.compute("video", 7)                     # a cache hit: the small cache still holds the last rows
    g.compute("video", 20)                    # a seek
    assert [ev.kind for ev in events[n:] if ev.kind != "uncache"] == ["cache", "seek"]
    held = sum(ev.bytes for ev in events if ev.kind == "run") - sum(ev.bytes for ev in events if ev.kind == "evict")
    assert held == g.memo.bytes and {(ev.node, ev.key) for ev in events if ev.kind == "evict"} == {(None, g.key("gray")), (None, g.key("add"))}
    assert {ev.key for ev in events if ev.kind == "uncache"} == {g.key("video")} and len(events) > n + 2
    assert sum(ev.bytes for ev in events if ev.kind == "uncache") == 9216 * (g.decoder.decodes - len(g.decoder._cache))
    s = stats.snapshot()
    assert {nid: v["n"] for nid, v in s["nodes"].items()} == {"video": 11, "gray": 9, "add": 9}
    assert s["walk_rows_s"] > 0 and s["step_ms"] > 0 and s["seek_ms"] > 0 and s["decodes"] and s["seeks"]
    assert s["memo_mb"] > 0 and s["cache_mb"] > 0 and 0 < s["memo_hit"] < 1 and 0 < s["cache_hit"] < 1
    assert s["series_ms"] is None and s["evictions"] > 0    # no chain in this document
    g.compute("add", 0)                       # neither store holds row 0 any longer
    from sieve_player.ledger import Ledger
    led = Ledger()
    for ev in events:
        led.event(ev)
    again, seeks = ({k: sum(getattr(b, name).get(k, 0) for b in led.view().buckets) for k in ("memo", "video", g.key("video"))}
                    for name in ("recomputed", "seeks"))
    assert again["memo"] == 2 and again[g.key("video")] == 1 and seeks["video"] == sum(ev.kind == "seek" for ev in events)
    g.decoder.close()


def test_a_density_is_folded_once_under_the_node_and_memoized_beside_its_plane():
    g = Graph(fan_out(), Dec(), TOOLS)
    seen = []
    g.on_event = seen.append
    counts = g.density("gray", 3)
    assert counts.shape == (256,) and counts.sum() == 4 * 6
    folds = [ev for ev in seen if ev.kind == "fold"]
    assert [(ev.node, ev.row) for ev in folds] == [("gray", 3)] and folds[0].bytes == counts.nbytes
    assert folds[0].key != g.key("gray") and folds[0].ms >= 0
    seen.clear()
    assert (g.density("gray", 3) == counts).all() and seen == []           # held: no run, no fold
    assert g.density("video", 3) is None and g.density("nowhere", 3) is None and seen == []


def test_events_name_the_demand_and_the_reader_and_memo_hits_leave_on_progress():
    """video -> gray -> {add, same}, add walked, and side reading the video off the walked path."""
    side = tool("side", "bgr", "gray", lambda f, p: f[..., 1])
    doc = fan_out()
    doc.add_node("side", (0, 400))
    doc.connect("video", "side")
    g = Graph(doc, Dec(), {**TOOLS, "side": side})
    events = []
    g.on_event = events.append
    for _ in range(2):
        for r in range(3):
            g.walk_row(r)
            g.compute("same", r)
            g.density("side", r)
            g.progress(r + 1, 3)
            assert events[-1].facts["memo"]["bytes"] == g.memo.bytes
    said = {(ev.node, ev.kind, ev.reader): (ev.demand, ev.asked) for ev in events if ev.row == 0 and ev.node}
    assert said == {("add", "run", None): ("walk", "add"), ("gray", "run", "add"): ("walk", "add"),     # gray names the reader that reached it first
                    ("video", "decode", "gray"): ("walk", "add"), ("same", "run", None): ("display", "same"),
                    ("side", "run", None): ("fold", "side"), ("video", "decode", "side"): ("fold", "side"),
                    ("side", "fold", None): ("fold", "side")}
    first, second = ([ev.facts for ev in events if ev.kind == "progress"][i:i + 3] for i in (0, 3))
    assert [(f["hits"], f["fold_hits"]) for f in first] == [({"gray": 1}, {})] * 3                      # same read gray, which add had run
    assert [(f["hits"], f["fold_hits"]) for f in second] == [({"add": 1, "same": 1}, {"side": 1})] * 3
    assert second[-1]["memo"]["hits"] == g.memo.hits and second[-1]["caches"][g.key("video")]["misses"] == 0   # the fake counts no read
    g.compute("same", 0)
    g.began(0, 3)                             # a hit before a walk begins is not the walk's
    g.progress(1, 3)
    assert events[-1].facts["hits"] == {}


def test_a_sync_event_carries_the_plan_it_began():
    from sieve_player.store import Sidecar
    doc = fan_out()
    D.land(doc.node("add"), Sidecar("k", "gray", "doc", "add", [0, 9], 1, 30.0, 30.0, [4, 6], "lossless").bake(10))
    doc.pin("same", TOOLS)
    g = Graph(doc, Dec(), TOOLS)
    events = []
    g.on_event = events.append
    g.sync()
    f = events[-1].facts
    reach, todo = set(), [f["walk"]]
    while todo:
        n = todo.pop()
        if n is not None and n not in reach:
            reach.add(n)
            todo += f["nodes"][n]["reads"].values()
    assert f["nodes"]["add"]["served"] and f["nodes"]["gray"]["fed"] and not f["nodes"]["gray"]["served"]
    assert reach == {"add"} and f["nodes"]["same"]["reads"] == {"in": "gray"}        # gray is fed, and nothing the walk reaches reads it
    assert (f["walk"], f["shown"], f["over"], f["pinned"], f["chain"]) == ("add", "add", None, ["same"], [])
    assert f["nodes"]["video"] == {"kind": "video", "fed": True, "static": False, "served": False, "steps": False,
                                   "whole_by": None, "reads": {"in": None}}


def test_the_clip_walk_runs_behind_the_window_and_a_frame_change_drops_it():
    """Asked for, the clip walk covers every row from the first once the window is walked, and the
    chain's result over it arrives as clipReady; a change to a frame tool abandons it and says so
    with an empty clipReady, while a series-only change reruns the chain on the clip's stack."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])
    head = tool("head", kind="series", produces="signal")
    head.run = lambda series, params: {"signal": np.asarray(series.data, np.float64).reshape(len(series.data), -1)[:, 0] + params["k"]}
    head.fold = lambda frame: np.asarray([float(frame.mean())])
    doc = D.from_tools([gray, head])
    g = Graph(doc, Dec(), {**TOOLS, "head": head})
    w = Worker(g, every=3)
    clips, walked, windows = [], [], []
    w.clipReady.connect(lambda r, s, fps: clips.append((r, s)))
    w.clipWalked.connect(lambda d, n: walked.append((d, n)))
    w.seriesReady.connect(lambda r, s, fps: windows.append((r, s)))
    w.set_window(4, 3)
    w.walk_clip()
    w.start()
    for _ in range(500):
        QApplication.processEvents()
        if clips and len(clips[-1][0].get("head", {}).get("signal", ())) == 10:
            break
        time.sleep(0.01)
    assert walked[-1] == (10, 10) and clips[-1][1] == 0
    assert clips[-1][0]["head"]["signal"].tolist() == [r + 1 + 1 for r in range(10)]   # gray adds k=1, head adds k=1
    assert windows and len(windows[-1][0]["head"]["signal"]) == 3 and windows[-1][1] == 4
    assert windows[0][1] == 4 and clips[0][1] == 0 and walked[0][0] == 0            # the window's result came first
    doc.node("head").params["k"] = 5
    g.sync()
    w.request_row(2)                            # a row request pending beside the rerun must not swallow it
    w.rerun_series()
    for _ in range(500):
        QApplication.processEvents()
        if clips[-1][0]["head"]["signal"][0] == 6:
            break
        time.sleep(0.01)
    assert clips[-1][0]["head"]["signal"].tolist() == [r + 1 + 5 for r in range(10)]
    w.invalidate()
    for _ in range(500):
        QApplication.processEvents()
        if clips[-1][0] == {}:
            break
        time.sleep(0.01)
    w.stop()
    assert clips[-1] == ({}, 0) and walked[-1] == (0, 0)


def test_the_window_and_the_clip_are_one_walk_over_two_ranges():
    """Under the probe the clip walk runs each node as the window walk does: a frame node once per
    row the memo does not hold, the chain at each cadence row and at the range's end; the densities
    are the window's alone, each range's events and progress are in its own lane, and each range's
    beginning is an event."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])
    head = tool("head", kind="series", produces="signal")
    head.run = lambda series, params: {"signal": np.asarray(series.data, np.float64).reshape(len(series.data), -1)[:, 0]}
    head.fold = lambda frame: np.asarray([float(frame.mean())])
    doc = D.from_tools([gray, head])
    g = Graph(doc, Dec(), {**TOOLS, "head": head})
    events = []
    g.on_event = events.append
    w = Worker(g, every=3)
    clips = []
    w.clipReady.connect(lambda r, s, fps: clips.append(r))
    w.set_window(0, 6)
    w.walk_clip()
    w.start()
    for _ in range(500):
        QApplication.processEvents()
        if clips and len(clips[-1].get("head", {}).get("signal", ())) == 10:
            break
        time.sleep(0.01)
    w.stop()
    runs = [(ev.node, ev.row) for ev in events if ev.kind == "run" and ev.serves == "walk"]
    assert [r for n, r in runs if n == "gray"] == list(range(10))              # the window's six, then the clip's four the memo lacks
    assert [r for n, r in runs if n == "head"] == [2, 5, 2, 5, 8, 9]
    assert [ev.row for ev in events if ev.kind == "fold"] == list(range(6))
    assert {ev.lane for ev in events} == {"window", "clip"}                    # each range's rows are its own lane
    for lane, n in (("window", 6), ("clip", 10)):
        assert [(ev.row, ev.length) for ev in events if ev.kind == "progress" and ev.lane == lane] == [(i, n) for i in range(1, n + 1)]
    assert {ev.lane for ev in events if ev.kind == "fold" or ev.node == "gray" and ev.row < 6} == {"window"}
    assert {ev.lane for ev in events if ev.node == "gray" and ev.row >= 6} == {"clip"}
    assert [(ev.lane, ev.row, ev.length) for ev in events if ev.kind == "begin"] == [("window", 0, 6), ("clip", 0, 10)]
    from sieve_player.ledger import Ledger
    led = Ledger()
    for ev in events:
        led.event(ev)
    window, clip = led.view().walks       # head's run after a range's last row is that range's, by the begin between them
    assert [sum(r[0] for r in walk.nodes["head"].runs.values()) for walk in (window, clip)] == [2, 4]


def test_a_tool_raising_indexerror_fails_the_walk_and_only_the_stream_end_closes_it():
    """A tool's own IndexError is a failure said on the node, never a shorter clip with a clean
    trace: the walk closes at the rows it has, as a refused one does, and only EndOfStream closes
    it with no node blamed."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])
    bad = tool("bad", fn=lambda f, p: f[99] if int(f.flat[0]) == 3 else f)
    always = tool("always", kind="series", produces="signal")      # a series tool raising at every run, wired in below
    always.run = lambda series, params: 1 / 0
    doc = D.from_tools([gray, bad])
    g = Graph(doc, Dec(), {**TOOLS, "bad": bad, "always": always})
    w = Worker(g)
    failed, walked = [], []
    w.failed.connect(lambda r, n: failed.append((r, n)))
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.set_window(0, 8)
    w.start()
    for _ in range(300):
        QApplication.processEvents()
        if failed:
            break
        time.sleep(0.01)
    assert failed == [(2, "bad")] and walked[-1] == (2, 2) and g.standing("bad").startswith("raised at row 2: IndexError")
    w.request_row(2)                            # the display asking for the row fails the same way, and says so
    for _ in range(300):
        QApplication.processEvents()
        if len(failed) == 2:
            break
        time.sleep(0.01)
    assert failed[-1] == (2, "bad")
    w.set_window(8, 5)                          # past the fake stream's ten rows: the window closes where the stream ends
    for _ in range(300):
        QApplication.processEvents()
        if walked[-1] == (2, 2):
            break
        time.sleep(0.01)
    assert walked[-1] == (2, 2) and len(failed) == 2
    doc.add_node("always", (0, 300))            # the close's own chain run now raises too, and the thread must survive it
    doc.connect("bad", "always")
    g.sync()
    w.invalidate()
    w.set_window(0, 4)
    for _ in range(300):
        QApplication.processEvents()
        if len(failed) == 3:
            break
        time.sleep(0.01)
    assert failed[-1] == (2, "always") and walked[-1] == (2, 2) and w.isRunning()
    rows = []
    w.rowReady.connect(rows.append)
    w.request_row(1)                            # the thread survived the double raise and still serves
    for _ in range(300):
        QApplication.processEvents()
        if rows:
            break
        time.sleep(0.01)
    w.stop()
    assert rows == [1] and len(failed) == 3


def test_a_clip_stack_of_tables_is_counted_through_its_object_columns():
    """nbytes reads the arrays behind an object field; the clip walk stops where the running total
    passes STACK_BYTES, the rows it has standing, where the first row's forecast let it start."""
    from PySide6.QtWidgets import QApplication
    from sieve_player import worker as W
    QApplication.instance() or QApplication([])
    t = np.empty(2, dtype=[("x", "<i4"), ("contour", object)])
    t["contour"] = [np.zeros((100, 2), np.int32), None]
    stack = np.empty(2, object)
    stack[:] = [t, t]
    assert t.nbytes == 24 and nbytes(t) == 24 + 800 and nbytes(stack) == 16 + 2 * 824 and nbytes({}) == 64
    table = tool("table", produces="blobs", fn=lambda f, p: np.array([(0, np.zeros((50 * int(f.flat[0]), 2), np.int32))], dtype=t.dtype))
    head = tool("head", kind="series", expects="blobs", produces="signal")
    head.run = lambda series, params: {"signal": np.array([len(r) for r in series.data], np.float32)}
    doc = D.from_tools([gray, table, head])
    g = Graph(doc, Dec(), {**TOOLS, "table": table, "head": head})
    w = W.Worker(g)
    W.STACK_BYTES = 10_000           # ten rows of row 0's 424 B pass the forecast; the contours grow 400 B a row
    refused, walked, clips = [], [], []
    w.clipRefused.connect(refused.append)
    w.clipWalked.connect(lambda d, n: walked.append((d, n)))
    w.clipReady.connect(lambda r, s, fps: clips.append(r))
    try:
        w.set_window(0, 2)
        w.walk_clip()
        w.start()
        for _ in range(500):
            QApplication.processEvents()
            if refused:
                break
            time.sleep(0.01)
        w.stop()
    finally:
        W.STACK_BYTES = 512 << 20
    assert refused and refused[0].startswith("the clip's stack reached") and walked[-1][0] == walked[-1][1] < 10
    assert len(clips[-1]["head"]["signal"]) == walked[-1][0]


def test_a_shown_table_walks_without_a_series_node():
    """blobs shown with nothing reading it: the walk is that node, each row a table of its own length,
    and the walk finishes instead of reading every row as a shape change and starting over."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])
    table = tool("table", produces="blobs", fn=lambda f, p: np.zeros(int(f.flat[0]) % 3, dtype=[("x", "<i4")]))
    doc = D.from_tools([gray, table])
    doc.display = "table"
    g = Graph(doc, Dec(), {**TOOLS, "table": table})
    w = Worker(g)
    walked = []
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.set_window(0, 6)
    w.start()
    for _ in range(300):
        QApplication.processEvents()
        if walked and walked[-1] == (6, 6):
            break
        time.sleep(0.01)
    w.stop()
    assert walked[-1] == (6, 6) and len(walked) <= 7 and w._win.stack is None     # nothing reads a stack, so none is held


def test_a_window_stack_stops_at_the_byte_limit_as_the_clip_stack_does():
    """The window's stack is forecast from the first row and summed as it fills; past STACK_BYTES the
    walk closes at the rows it has, the chain runs over them, and the transport is told why."""
    from PySide6.QtWidgets import QApplication
    from sieve_player import worker as W
    QApplication.instance() or QApplication([])
    t = np.dtype([("x", "<i4"), ("contour", object)])
    table = tool("table", produces="blobs", fn=lambda f, p: np.array([(0, np.zeros((50 * int(f.flat[0]), 2), np.int32))], dtype=t))
    head = tool("head", kind="series", expects="blobs", produces="signal")
    head.run = lambda series, params: {"signal": np.array([len(r) for r in series.data], np.float32)}
    doc = D.from_tools([gray, table, head])
    g = Graph(doc, Dec(), {**TOOLS, "table": table, "head": head})
    w = W.Worker(g)
    W.STACK_BYTES = 10_000
    refused, walked, got = [], [], []
    w.walkRefused.connect(refused.append)
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.seriesReady.connect(lambda r, s, fps: got.append(r))
    try:
        w.set_window(0, 20)
        w.start()
        for _ in range(500):
            QApplication.processEvents()
            if refused:
                break
            time.sleep(0.01)
        w.stop()
    finally:
        W.STACK_BYTES = 512 << 20
    assert refused[0].startswith("the window's stack reached") and walked[-1][0] == walked[-1][1] < 20
    assert len(got[-1]["head"]["signal"]) == walked[-1][0]


def test_two_heads_with_different_folds_each_run_on_their_own_folding():
    """count folds, size does not: both read the same table node and both hand out a signal."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    from tools import count, size
    QApplication.instance() or QApplication([])
    table = tool("table", produces="blobs", fn=lambda f, p: np.array([(a,) for a in range(1, int(f.flat[0]) + 1 + p["k"])], dtype=[("area", "<i4")]))
    doc = D.from_tools([gray, table, count])
    doc.add_node("size", (0, 400), size.DEFAULTS); doc.connect("table", "size")
    g = Graph(doc, Dec(), {**TOOLS, "table": table, "count": count, "size": size})
    assert g.chain == ["count", "size"] and g.fold is None
    w = Worker(g)
    got = []
    w.seriesReady.connect(lambda r, s, fps: got.append(r))
    w.set_window(0, 4)
    w.start()
    for _ in range(500):
        QApplication.processEvents()
        if got and len(got[-1].get("size", {}).get("signal", ())) == 4:
            break
        time.sleep(0.01)
    assert got[-1]["count"]["signal"].tolist() == [2, 3, 4, 5]          # gray is row + 1; the table has row + 1 + k records
    assert got[-1]["size"]["signal"].tolist() == [1.5, 2, 2.5, 3]       # mean area of 1..n
    doc.node("table").params["k"] = 2
    g.sync()
    w.invalidate()                              # a new stack of the same shape, likely at the freed one's address, folded afresh
    for _ in range(500):
        QApplication.processEvents()
        if got[-1]["count"]["signal"].tolist() == [3, 4, 5, 6]:
            break
        time.sleep(0.01)
    w.stop()
    assert got[-1]["count"]["signal"].tolist() == [3, 4, 5, 6]


def test_standing_says_why_a_node_does_not_run_and_what_its_run_said():
    """The plan's reason per node, "" for one that runs; a tool raising leaves its line on the node
    until the node's key changes; a run that goes through clears a note."""
    s1, s3 = tool("s1", kind="series", produces=None), tool("s3", kind="series", produces=None)
    doc = fan_out()
    doc.add_node("s1", (0, 400)); doc.connect("gray", "s1")
    doc.add_node("s3", (0, 500)); doc.connect("add", "s3")
    g = Graph(doc, Dec(), {**TOOLS, "s1": s1, "s3": s3})
    assert g.standing("video") == g.standing("gray") == g.standing("add") == g.standing("s1") == ""
    assert g.standing("s3") == "unrun: reads add; the walk is gray, which s1 reads"
    doc.disconnect("gray")
    g.sync()
    assert g.standing("gray") == "in is unwired" and g.standing("add") == "in waits on gray"
    doc.connect("video", "add")
    g.sync()
    assert g.standing("add") == "in expects gray, video produces bgr"
    doc.disconnect("add"); doc.connect("video", "gray"); doc.connect("gray", "add")
    bad = tool("bad", fn=lambda f, p: f[99])
    doc.add_node("bad", (0, 600)); doc.connect("gray", "bad")
    g = Graph(doc, Dec(), {**TOOLS, "s1": s1, "s3": s3, "bad": bad})
    with pytest.raises(IndexError) as e:
        g.compute("bad", 2)
    assert e.value.sieve_node == "bad" and g.standing("bad").startswith("raised at row 2: IndexError") and g.standing("gray") == ""
    with pytest.raises(IndexError) as e:
        g.compute("add", 10)                    # the stream's end is the video node's, not the reader's
    assert e.value.sieve_node == "video" and g.standing("add") == ""
    doc.node("bad").params["k"] = 2
    g.sync()
    assert g.standing("bad") == ""
    g.note("bad", "said so")
    assert g.standing("bad") == "said so"
    g.note("bad", "")
    assert g.standing("bad") == ""


def test_the_plan_is_pure_in_the_document_and_the_tools():
    """plan() needs no decoder and says the same twice; the graph's sync holds nothing it does not."""
    doc = fan_out()
    base = base_key("fake.mp4", "bgr")
    p, q = plan(doc, TOOLS, base), plan(doc, TOOLS, base)
    assert p == q and p.shown == doc.display and p.entries["video"].key == base and not p.chain
    g = Graph(doc, Dec(), TOOLS)
    assert {nid: e.key for nid, e in p.entries.items()} == {n.id: g.key(n.id) for n in doc.nodes}


def test_a_scrub_past_the_end_says_the_count_and_leaves_the_walk_standing():
    """A header may claim rows the stream lacks. The walk closes where the stream ends and says the
    count; a display request past it says the count again and neither fails nor closes the walk."""
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    QApplication.instance() or QApplication([])

    class Lying(Dec):
        count = 12

        def read(self, row):
            if row >= 10:
                self.count = 10
            return super().read(row)
    g = Graph(D.from_tools([gray]), Lying(), TOOLS)
    w = Worker(g)
    failed, walked, short = [], [], []
    w.failed.connect(lambda r, n: failed.append((r, n)))
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.shortened.connect(short.append)
    w.set_window(0, 12)
    w.start()
    for _ in range(300):
        QApplication.processEvents()
        if short:
            break
        time.sleep(0.01)
    assert short == [10] and walked[-1] == (10, 10)
    w.request_row(11)
    for _ in range(300):
        QApplication.processEvents()
        if len(short) == 2:
            break
        time.sleep(0.01)
    w.stop()
    assert short == [10, 10] and walked[-1] == (10, 10) and not failed
