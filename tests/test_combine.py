"""combine: and, or, difference and not of two masks; two shapes are a note on the node and None downstream."""
import numpy as np
import pytest

from sieve_player import document as D
from sieve_player.graph import Graph
from tests.test_graph import Dec, tool
from tools import combine

A = np.array([[255, 255, 0, 0]], np.uint8)
B = np.array([[255, 0, 255, 0]], np.uint8)


def fed(a, b=None):
    return lambda r, name="in": a if name == "in" else b


def test_each_method_on_two_small_masks():
    out = {m: combine.run(fed(A, B), 0, {"method": m}).tolist()[0] for m in combine.METHODS}
    assert out["and"] == [255, 0, 0, 0] and out["or"] == [255, 255, 255, 0]
    assert out["difference"] == [0, 255, 0, 0] and out["not"] == [0, 0, 255, 255]
    assert combine.run(fed(A), 0, {"method": "not"}).tolist()[0] == [0, 0, 255, 255]
    with pytest.raises(ValueError):
        combine.run(fed(A), 0, {"method": "and"})


def test_two_shapes_are_reported_on_the_node_and_none_downstream():
    full = tool("full", "bgr", "mask", lambda f, p: np.full(f.shape[:2], 255, np.uint8))
    half = tool("half", "bgr", "mask", lambda f, p: np.full((f.shape[0] // 2, f.shape[1]), 255, np.uint8))
    after = tool("after", "mask", "mask")
    tools = {t.NAME: t for t in (full, half, after, combine)}
    doc = D.from_tools([full, combine, after])
    doc.add_node("half", (0, 500))
    doc.connect("video", "half")
    doc.connect("half", "combine", "with")
    g = Graph(doc, Dec(), tools)
    with pytest.raises(ValueError) as e:
        g.compute("after", 1)
    assert e.value.sieve_node == "combine" and g.standing("combine").startswith("raised at row 1: ValueError: masks of two shapes")
    assert g.standing("after") == ""
    doc.node("combine").params["method"] = "not"
    g.sync()
    assert g.standing("combine") == "" and g.compute("after", 1).shape == (4, 6) and g.compute("after", 1).max() == 0
