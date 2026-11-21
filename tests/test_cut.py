"""A cut's record: one extent however the cuts nest, a place lifted to the footage, and the record a
tool is told against the plan's own."""
from types import SimpleNamespace as Tool

import pytest

from sieve_player import document as D
from sieve_player.cut import Extent, Record, holding, place_in
from sieve_player.graph import Graph
from sieve_player.plan import plan
from tests.test_graph import Dec, gray

RECT, ROWS = (10, 30, 20, 50), (3, 9)


def test_a_region_within_a_period_and_a_period_within_a_region_have_one_extent_and_a_place_lifts_to_the_footage():
    footage = Record("print")
    within, around = footage.cut(rows=ROWS).cut(rect=RECT), footage.cut(rect=RECT).cut(rows=ROWS)
    assert within.extent == around.extent == Extent(ROWS, RECT) and within != around
    assert within.lift((2, 3)) == around.lift((2, 3)) == (22, 13) and footage.lift((2, 3)) == (2, 3)
    assert (footage.cut(rect=RECT) & footage.cut(rows=ROWS)).extent == within.extent
    inner = within.cut(rect=(5, 40, 5, 10), rows=(0, 5))       # said in the cut's pixels, kept inside it
    assert inner.extent == Extent((3, 5), (15, 30, 25, 30)) and inner.lift((0, 0)) == (25, 15)
    assert within.cut(rows=(20, 30)).extent.rows == (20, 20)
    with pytest.raises(ValueError):
        footage & Record("another print")

    a_row = footage.cut(rows=(4, 8), rects=[(r, r + 4, 0, 6) for r in range(4)])
    met = a_row & footage.cut(rows=ROWS).cut(rows=(6, 20))
    assert met.extent == Extent((6, 8), None, ((2, 6, 0, 6), (3, 7, 0, 6))) and met.lift((1, 1), 7) == (1, 4)
    assert a_row.cut(rect=(1, 3, 2, 4)).extent.at(5) == (2, 4, 2, 4)
    with pytest.raises(ValueError):
        footage.cut(rows=(0, 3), rects=[(0, 1, 0, 1)])

    served = footage.cut(rect=RECT, file=("clip.mp4", "clip print"))
    assert served.cut(rows=ROWS).served() == ("clip.mp4", "clip print") and around.served() is None
    assert (served & footage.cut(rows=ROWS)).served() is None and served == footage.cut(rect=RECT)
    assert holding((footage.cut(rows=(0, 3)), within), 4) is within and holding((within,), 9) is None
    assert place_in(footage, within, 4, (20, 30), (48, 64)) == (-20, -10) and place_in(within, footage, 4, (48, 64), (48, 64)) == (20, 10)
    assert place_in(within, around, 4, (7, 7), (48, 64)) == (0, 0) and place_in(footage, within, 4, (10, 15), (48, 64)) is None


def test_a_tool_cuts_by_its_declaration_alone_and_a_tool_below_two_cuts_is_told_their_record():
    told = []

    def runs(name, **more):
        return Tool(NAME=name, KIND="frame", EXPECTS="gray", PRODUCES="gray", run=lambda frames, row, params: told.append((name, frames.cut)) or frames(row), **more)

    period = runs("period", PARAMS={"rows": {"default": list(ROWS)}}, cut_extents=lambda params, result: [{"rows": params["rows"]}])
    region = runs("region", cut_extents=lambda params, result: [{"rect": (1, 3, 2, 6)}])
    found = runs("found", cut_extents=lambda params, result: [{"rows": r} for r in result])
    tools = {t.NAME: t for t in (gray, period, region, found, runs("below"))}
    doc = D.from_tools([gray, period, region, tools["below"]])
    g = Graph(doc, Dec(), tools)
    g.compute("below", 4)
    e, footage = g.snapshot().entries, Record(Dec.footage_print)
    assert e["gray"].cuts == e["period"].reads == (footage,) and e["below"].reads == e["below"].cuts == e["region"].cuts
    (cut,) = e["below"].cuts
    assert cut.extent == Extent(ROWS, (1, 3, 2, 6)) and cut.made_from == e["period"].cuts and cut.served() is None
    assert dict(told) == {"period": footage, "region": footage.cut(rows=ROWS), "below": cut}

    doc = D.from_tools([gray, found, tools["below"]])
    asked = []
    p = plan(doc, tools, "base", cut_file=lambda nid, up: asked.append(nid), cut_result=lambda nid, key, within: [(0, 2), (5, 7)], footage="print")
    assert [c.extent.rows for c in p.entries["below"].cuts] == [(0, 2), (5, 7)] and not asked and p.entries["found"].file is None
    assert plan(doc, tools, "base", footage="print").entries["below"].cuts == (Record("print"),)        # a declaration that raises cuts nothing

    sig = Tool(NAME="sig", KIND="series", EXPECTS="gray", PRODUCES="signal", run=lambda series, params: None)
    pick = Tool(NAME="pick", PRODUCES="path", select=lambda folder, params: None)
    gated = runs("gated", PATHS={"periods": lambda path: {}}, CUT_BY={"gate": "signal"}, cut_extents=lambda params, result: [{"rows": r} for r in result])
    tools = {t.NAME: t for t in (gray, sig, pick, gated, tools["below"])}
    doc = D.from_tools([gray, gated, tools["below"]])
    doc.add_node("sig")
    doc.connect("gray", "sig")
    doc.connect("sig", "gated", "gate")
    asked = []
    of = lambda held: plan(doc, tools, "base", cut_result=lambda nid, key, within: asked.append((nid, key)) or held, footage="print").entries
    e = of([(0, 2)])
    assert [c.extent.rows for c in e["below"].cuts] == [(0, 2)] and asked == [("gated", e["sig"].key)]       # asked under the key the node wired there has
    e = of(None)
    assert e["gated"].cuts == () and not e["below"].fed and e["gated"].standing == "gate waits on sig's walk"
    doc.add_node("pick")
    doc.connect("pick", "gated", "periods")
    assert of([(0, 2)])["gated"].standing == "fed both: periods by a file and gate by sig; one cuts it"
    doc.disconnect("gated", "periods")
    doc.connect("below", "sig")         # the gate's node now reads the node it cuts
    e = of([(0, 2)])
    assert e["gated"].standing == "in a cycle: gate is fed by sig, which reads gated" and not e["below"].fed
    doc.disconnect("gated", "gate")
    assert of([(0, 2)])["gated"].standing == "neither periods nor gate is wired"


def test_a_value_is_one_in_every_period_holding_its_row_but_where_it_read_an_edge():
    runs = []

    def reads(name, before, after, at=lambda row: row):
        def run(frames, row, params):
            runs.append((name, row, frames.cut.extent.rows))
            return frames(at(row))
        return Tool(NAME=name, KIND="frame", EXPECTS="gray", PRODUCES="gray", run=run, reach_in_rows=lambda params: (before, after))

    period = Tool(NAME="period", KIND="frame", EXPECTS="gray", PRODUCES="gray", PARAMS={"rows": {"default": [[2, 8], [5, 10]]}},
                  run=lambda frames, row, params: frames(row), key_params=lambda params: {}, reach_in_rows=lambda params: (0, 0),
                  cut_extents=lambda params, result: [{"rows": r} for r in params["rows"]])
    own, back, walk, ahead = reads("own", 0, 0), reads("back", 1, 0, lambda row: row - 1), reads("walk", None, 0), reads("ahead", 0, 1)
    gray_own_row = Tool(**{**vars(gray), "reach_in_rows": lambda params: (0, 0)})         # a tool that says nothing reads both edges
    tools = {t.NAME: t for t in (gray_own_row, period, own, back, walk, ahead)}
    doc = D.from_tools([gray_own_row, period, own])
    for t in (back, walk, ahead):
        n = doc.add_node(t.NAME)
        doc.connect("own", n.id)
    g = Graph(doc, Dec(), tools)

    def ran(name, row, period):
        e = g.snapshot().entries[name]
        g.compute(name, row, cut=next(c for c in e.cuts if c.extent.rows == period))
        return [(n, r) for n, r, _ in runs].count((name, row))

    assert ran("own", 6, (2, 8)) == ran("own", 6, (5, 10)) == 1 and ran("own", 5, (5, 10)) == 1
    assert ran("back", 6, (2, 8)) == ran("back", 6, (5, 10)) == 1
    assert ran("back", 5, (2, 8)) == 1 and ran("back", 5, (5, 10)) == 2         # one read that the period begins at 5
    assert ran("walk", 6, (2, 8)) == 1 and ran("walk", 6, (5, 10)) == 2         # of each period's first row at every row
    assert ran("ahead", 6, (2, 8)) == ran("ahead", 7, (2, 8)) == 1
    assert ("own", 6, (2, 8)) in runs and ("own", 6, (5, 10)) not in runs        # told the cut it was computed in

    doc.node("period").params["rows"] = [[2, 9], [5, 10]]                     # the first period's last row later: no key moves
    g.sync()
    before = len(runs)
    for name, row in (("own", 6), ("walk", 6), ("ahead", 6), ("ahead", 7)):
        ran(name, row, (2, 9))
    assert runs[before:] == [("ahead", 7, (2, 9))]                              # within reach of the old last row, it read it


def test_a_node_above_a_period_is_walked_as_with_none_and_one_below_is_walked_over_each_period_alone():
    import numpy as np

    from sieve_player import held
    from sieve_player.bare import _Told
    from sieve_player.walk import _Walk

    def step(state, row, i, params):
        return state, {"signal": float(row[0, 0])}

    def run(series, params):
        return {"signal": np.asarray([float(r[0, 0]) for r in series.data])}

    sig = Tool(NAME="sig", KIND="series", EXPECTS="gray", PRODUCES="signal", run=run, step=step)
    period = Tool(NAME="period", KIND="frame", EXPECTS="gray", PRODUCES="gray", PARAMS={"rows": {"default": []}},
                  run=lambda frames, row, params: frames(row), key_params=lambda params: {}, reach_in_rows=lambda params: (0, 0),
                  cut_extents=lambda params, result: [{"rows": r} for r in params["rows"]])
    tools = {t.NAME: t for t in (gray, period, sig)}
    doc = D.from_tools([gray, sig])
    doc.add_node("period", (0, 200), {"rows": [[2, 5], [4, 8]]})
    doc.connect("gray", "period")
    below = doc.add_node("sig").id
    doc.connect("period", below)
    g = Graph(doc, Dec(), tools)

    def walked(p, cut=None, rows=(0, Dec.count)):
        ready = _Told()
        w = _Walk(g, name="clip", every=1 << 62, progress=_Told(), ready=ready, refused=_Told(), failed=_Told(), plan=p, cut=cut)
        w.begin(rows[0], rows[1] - rows[0])
        while w.i < w.length:
            w.turn()
        return ready.last[0]

    p = g.snapshot()
    (w,) = p.timed
    assert p.chain == ["sig"] and w.chain == [below] and [c.extent.rows for c in w.cuts] == [(2, 5), (4, 8)]
    for c in w.cuts:
        got = walked(p.of(w), c, c.extent.rows)[below]["signal"]
        assert got.tolist() == [r + 1.0 for r in range(*c.extent.rows)]         # gray is the row and its k, over the period's rows alone
    runs, key = held.Runs(1 << 30, lambda nid, r: 0), p.entries["sig"].key
    chain = held.Chain({"sig": key}, frozenset({"sig"}), {"sig": (0, 0)})
    above = walked(p)
    assert runs.hold(0, Dec.count, above, chain)
    for rows in ([[2, 6], [4, 8]], [[2, 5], [4, 8], [0, 3]], []):        # moved, added, gone
        doc.node("period").params["rows"] = rows
        g.sync()
        q = g.snapshot()
        assert q.chain == ["sig"] and q.entries["sig"].key == key and q.entries[below].key == p.entries[below].key
        assert runs.over(0, Dec.count, chain, (0, Dec.count))["sig"]["signal"].tolist() == above["sig"]["signal"].tolist()
        assert [c.extent.rows for w in q.timed for c in w.cuts] == [tuple(r) for r in rows]
    assert not q.timed and q.entries[below].standing == "reads period, which cuts no rows"
