"""hsv: inrange reads the same mask from bgr and from hsv of it, told which by frames.type(); several
inrange readers of one hsv node cost one conversion a row."""
import numpy as np

from sieve_player import document as D
from sieve_player.graph import Graph
from tools import hsv, inrange

TOOLS = [hsv, inrange]
BOUNDS = {**inrange.DEFAULTS, "h_lo": 100, "h_hi": 130, "s_lo": 100, "v_lo": 100}   # blues


class Dec:
    path, fps, count = "fake.mp4", 30.0, 4
    decodes = seeks = reads = cache_hits = cache_bytes = 0
    step_ms = seek_ms = None
    output, scale = "bgr", 1.0

    def read(self, row):
        rng = np.random.default_rng(row)
        frame = rng.integers(0, 256, (8, 10, 3), np.uint8)
        frame[2:5, 3:7] = (255, 40, 40)        # a blue patch
        return frame

    def cached(self, row):
        return None


def test_inrange_reads_bgr_or_hsv_alike_and_knows_which():
    direct = D.from_tools([inrange])
    direct.node("inrange").params.update(BOUNDS)
    via = D.from_tools(TOOLS)
    via.node("inrange").params.update(BOUNDS)
    a, b = Graph(direct, Dec(), TOOLS), Graph(via, Dec(), TOOLS)
    for row in range(3):
        m = a.compute("inrange", row)
        assert np.array_equal(m, b.compute("inrange", row)) and m[3, 4] == 255 and m.shape == (8, 10)
    seen = []
    orig = inrange.run
    inrange.run = lambda frames, row, params: (seen.append(frames.type()), orig(frames, row, params))[1]
    try:
        a.compute("inrange", 3), b.compute("inrange", 3)
    finally:
        inrange.run = orig
    assert seen == ["bgr", "hsv"]


def test_three_readers_of_one_hsv_cost_one_conversion_a_row():
    doc = D.from_tools(TOOLS)
    for name in ("two", "three"):
        doc.add_node("inrange", (0, 300), dict(inrange.DEFAULTS), id=name)
        doc.connect("hsv", name)
    runs = []
    orig = hsv.run
    hsv.run = lambda frames, row, params: (runs.append(row), orig(frames, row, params))[1]
    try:
        g = Graph(doc, Dec(), TOOLS)
        for row in range(2):
            for node in ("inrange", "two", "three"):
                g.compute(node, row)
    finally:
        hsv.run = orig
    assert runs == [0, 1]
