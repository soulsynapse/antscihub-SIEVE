"""The runtime: wiring, fan-out, keys, rewiring under a worker, and the series node."""
import threading
import time
from types import SimpleNamespace as Tool

import numpy as np

from sieve_player import document as D
from sieve_player.graph import Graph, gated


class Dec:
    path, fps, count = "fake.mp4", 30.0, 10

    def read(self, row):
        return np.full((4, 6, 3), row, np.uint8)

    def cached(self, row):
        return None


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
    g = Graph(fan_out(), Dec(), TOOLS)
    assert g.shown == "add" and g.walk == "add" and g.over is None


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


def test_two_series_nodes_one_runs():
    s1, s2 = tool("s1", kind="series", produces=None), tool("s2", kind="series", produces=None)
    doc = D.from_tools([gray, s1, s2])
    g = Graph(doc, Dec(), {**TOOLS, "s1": s1, "s2": s2})
    assert g.series == "s1" and g.chain == ["s1"] and g.unrun_series == ["s2"] and g.walk == "gray"
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
    assert gated({"other": 1}, (0.0, 1.0)) == ({"other": 1}, None)


def test_one_compute_sees_one_plan():
    """A sync between a node's run() starting and its frames(row) call: the value memoized under the
    old key is the old graph's, so flipping the param back serves the right frame."""
    doc = fan_out()
    g = Graph(doc, Dec(), TOOLS)

    def run(frames, row, params):
        doc.node("gray").params["k"] = 50       # upstream changes while this node is mid-run
        g.sync()
        return frames(row) + params["k"]
    add.run, old = run, add.run
    try:
        k_old = g.key("add")
        v = g.compute("add", 0)
        assert (v == 0 + 1 + 1).all()                            # gray's k was 1 when this compute began
        doc.node("gray").params["k"] = 1
        g.sync()
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
