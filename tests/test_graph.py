"""One test per `Check: a test` line under "Graph runtime" in spec/graph.md."""
import threading
import time
from types import SimpleNamespace as Tool

import numpy as np

from sieve_player import document as D
from sieve_player.graph import Graph


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
    assert g.shown == "add" and g.walk == "add"


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
    s1, s2 = tool("s1", kind="series"), tool("s2", kind="series")
    doc = D.from_tools([gray, s1, s2])
    g = Graph(doc, Dec(), {**TOOLS, "s1": s1, "s2": s2})
    assert g.series == "s1" and g.unrun_series == ["s2"] and g.walk == "gray"
