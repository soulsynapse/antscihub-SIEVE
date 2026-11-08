"""The bake node, live: the identity on every kind, a frame node on a frame wire and a series node on a series wire, its params changing nothing it hands out, and its mode live."""
import json
import os

import numpy as np

from sieve_player import document as D
from sieve_player.graph import Graph
from sieve_player.registry import discover, types
from sieve_player.registry.__main__ import VIDEO
from sieve_player.worker import Worker
from tests import stepping
from tests.test_graph import Dec
from tools import bake, blobs, gray, reduce, smooth, threshold

TOOLS = {t.NAME: t for t in (bake, blobs, gray, reduce, smooth, threshold)}
ROWS = 5


def chain(*names):
    """video -> gray -> threshold -> blobs, and reduce -> smooth off gray, with a bake spliced after each node named."""
    doc = D.from_tools([gray, threshold, blobs, reduce, smooth])
    doc.connect("gray", "reduce")
    for n in names:
        b = doc.add_node("bake")
        for w in [w for w in doc.wires if w.src == n]:
            doc.connect(b.id, w.dst, w.input)
        doc.connect(n, b.id)
    return doc


def series(g):
    stack = np.stack([g.walk_row(r) for r in range(ROWS)])
    return Worker(g)._run_chain(stack, 0, ROWS, {})


def test_the_identity_on_a_gray_a_blobs_and_a_signal_wire():
    plain = Graph(chain(), Dec(), TOOLS)
    doc = chain("gray", "blobs", "reduce")
    g = Graph(doc, Dec(), TOOLS)
    kinds = {n.id: D.kind_of(doc, TOOLS, n.id) for n in doc.nodes if n.tool == "bake"}
    assert kinds == {"bake": "frame", "bake_2": "frame", "bake_3": "series"} and g.chain == ["reduce", "bake_3", "smooth"]
    for r in range(ROWS):
        assert (g.compute("threshold", r) == plain.compute("threshold", r)).all()
        assert g.compute("bake", r).shape == (4, 6) and g.compute("bake_2", r).dtype == plain.compute("blobs", r).dtype
    assert series(g)["smooth"]["signal"].tolist() == series(plain)["smooth"]["signal"].tolist()
    assert D.mode_of(doc, TOOLS, "bake") == "live" and D.mode_of(doc, TOOLS, "gray") is None
    doc.node("bake").mode = "baked"
    back = D.Document.from_dict(json.loads(json.dumps(doc.to_dict())))
    assert back.node("bake").mode == "baked" and "mode" not in doc.to_dict()["nodes"][1]
    assert D.mode_of(doc, TOOLS, "bake") == "live"      # a mode with no bake behind it serves nothing
    assert bake.bake({"from": "2", "to": "9", "increment": 2}, 12) == (range(2, 10, 2), "lossless")
    assert bake.bake(bake.DEFAULTS, 12) == (range(0, 12), "lossless") and not bake.bake({"from": "20"}, 12)[0]
    assert bake.bake({"quality": "standard"}, 12)[1] == "standard"
    tables = np.empty(ROWS, object)
    tables[:] = [plain.compute("blobs", r) for r in range(ROWS)]
    for data in (tables, np.arange(ROWS, dtype=np.float32)):      # the identity steps on both series kinds, held to run by the oracle
        stepping.hold(bake, data, {})
    expected = {t for t, (p, ex) in types(discover("tools"), [VIDEO]).items()} - {D.PATH}
    assert set(bake.EXPECTS) == expected
    doc.disconnect("bake_3")
    assert D.kind_of(doc, TOOLS, "bake_3") == "frame"


def test_no_param_changes_what_a_live_node_hands_out():
    doc = chain("gray", "reduce")
    g = Graph(doc, Dec(), TOOLS)
    before = [g.compute("bake", r).copy() for r in range(ROWS)], series(g)["smooth"]["signal"].tolist()
    for name, value in (("from", "2"), ("to", "3"), ("increment", 2), ("quality", "standard")):
        for nid in ("bake", "bake_2"):
            doc.node(nid).params[name] = value
        g.sync()
        assert all((g.compute("bake", r) == before[0][r]).all() for r in range(ROWS))
        assert series(g)["smooth"]["signal"].tolist() == before[1]


def test_the_export_facets_are_retired_with_downsample():
    from sieve_player.registry import FACETS
    assert not {"output_name", "export_command", "describe_output"} & set(FACETS)
    assert not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "tools", "downsample.py"))
