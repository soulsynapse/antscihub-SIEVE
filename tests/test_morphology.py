"""morphology: open drops specks and protrusions and keeps holes, close fills holes and keeps specks;
between threshold and blobs the specks never become records."""
import numpy as np
import pytest

from sieve_player import document as D
from sieve_player.graph import Graph
from tests.test_hsv import Dec
from tools import blobs, morphology, threshold

MASK = np.zeros((12, 12), np.uint8)
MASK[2:9, 2:9] = 255          # a 7x7 square
MASK[5, 5] = 0                # with a one-pixel hole
MASK[5, 9] = 255              # and a one-pixel protrusion
MASK[10, 10] = 255            # beside a speck
BAR = np.zeros((9, 20), np.uint8)
BAR[3:6, 2:18] = 255          # three pixels tall


def test_open_and_close_cut_what_the_kernel_says():
    out = morphology.morph(MASK, "open", 1, 1)
    assert out[10, 10] == 0 and out[5, 9] == 0 and out[5, 5] == 0 and out.sum() == 255 * 48
    out = morphology.morph(MASK, "close", 1, 1)
    assert out[5, 5] == 255 and out[10, 10] == 255 and out[5, 9] == 255
    assert morphology.morph(BAR, "open", 1, 1).sum() == BAR.sum() and morphology.morph(BAR, "open", 1, 2).sum() == 0
    with pytest.raises(ValueError):
        morphology.morph(MASK, "erode", 1, 1)


def test_between_threshold_and_blobs_the_specks_are_never_records():
    class Specked(Dec):
        def read(self, row):
            f = np.full((16, 16), 255, np.uint8)
            f[4:12, 4:12] = 0
            f[1, 1] = f[14, 14] = 0
            return f

    tools = [threshold, morphology, blobs]
    bare, opened = D.from_tools([threshold, blobs]), D.from_tools(tools)
    for doc in (bare, opened):
        doc.video_node().params["output"] = "gray"
        doc.connect("video", "threshold")
        doc.node("threshold").params["invert"] = True
        doc.node("blobs").params["min_area"] = 1
    assert len(Graph(bare, Specked(), tools).compute("blobs", 0)) == 3
    rec = Graph(opened, Specked(), tools).compute("blobs", 0)
    assert len(rec) == 1 and rec["area"][0] == 64
