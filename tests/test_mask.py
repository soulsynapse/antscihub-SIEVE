"""mask: a frame let through a mask, zero where the mask is and as it was elsewhere, on BGR and gray; two shapes are said on the node."""
import numpy as np
import pytest

from sieve_player import document as D
from sieve_player.graph import Graph
from tests.test_combine import fed
from tests.test_graph import Dec, tool
from tools import mask

HOLE = np.full((4, 6), 255, np.uint8)
HOLE[1:3, 2:4] = 0


def test_the_hole_is_zero_and_the_rest_as_it_was_on_bgr_and_gray():
    bgr = np.random.default_rng(0).integers(1, 255, (4, 6, 3), np.uint8)
    out = mask.run(fed(bgr, HOLE), 0, {})
    assert out.shape == bgr.shape and out.dtype == bgr.dtype and (out[1:3, 2:4] == 0).all()
    assert np.array_equal(out[HOLE != 0], bgr[HOLE != 0])
    gray = bgr[..., 0]
    out = mask.run(fed(gray, HOLE), 0, {})
    assert out.shape == gray.shape and (out[1:3, 2:4] == 0).all() and np.array_equal(out[HOLE != 0], gray[HOLE != 0])
    flow = np.ones((4, 6, 2), np.float32)
    assert mask.masked(flow, HOLE)[1, 2].tolist() == [0.0, 0.0] and mask.masked(flow, HOLE)[0, 0].tolist() == [1.0, 1.0]
    with pytest.raises(ValueError):
        mask.masked(gray, HOLE[:2])


def test_a_mask_of_another_shape_is_reported_on_the_node():
    full = tool("full", "bgr", "mask", lambda f, p: np.full(f.shape[:2], 255, np.uint8))
    half = tool("half", "bgr", "mask", lambda f, p: np.full((f.shape[0] // 2, f.shape[1]), 255, np.uint8))
    tools = {t.NAME: t for t in (full, half, mask)}
    doc = D.from_tools([full, mask])
    doc.connect("video", "mask")
    doc.add_node("half", (0, 500))
    doc.connect("video", "half")
    doc.connect("half", "mask", "mask")
    g = Graph(doc, Dec(), tools)
    with pytest.raises(ValueError):
        g.compute("mask", 1)
    assert g.standing("mask").startswith("raised at row 1: ValueError: the frame is 6x4 and the mask 6x2")
    doc.connect("full", "mask", "mask")
    g.sync()
    assert g.standing("mask") == "" and g.compute("mask", 1).shape == (4, 6, 3)
