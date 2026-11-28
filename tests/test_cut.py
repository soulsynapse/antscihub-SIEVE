"""A cut's record: one extent however the cuts nest, a place lifted to the footage, and the record a
tool is told against the plan's own."""
from types import SimpleNamespace as Tool

import pytest

from sieve_player import document as D
from sieve_player import registry
from sieve_player.cut import Extent, Record, holding, place_in
from sieve_player.graph import Graph
from sieve_player.plan import Provisional, _all_held_or_seen, plan
from sieve_player.walk import window_legs
from sieve_player.worker import _clip_legs
from tests.cutting import cuts, hold
from tests.test_graph import Dec, gray

RECT, ROWS = (10, 30, 20, 50), (3, 9)


def test_every_tool_that_says_it_is_cut_by_a_part_cuts_a_part_as_the_whole():
    gate = [0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1]
    said = [e.module for e in registry.discover("tools") if e.ok and registry.cut_by_a_part(e.module)]
    assert said
    for tool in said:
        hold(tool, registry.defaults(tool), gate)
    padded = Tool(NAME="padded", cut_extents=lambda params, result, count: [{"rows": (max(0, a - 1), b + 1)} for a, b in cuts(said[0], params, result["gate"])])
    with pytest.raises(AssertionError):
        hold(padded, registry.defaults(said[0]), gate)


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

    period = runs("period", PARAMS={"rows": {"default": list(ROWS)}}, cut_extents=lambda params, result, count: [{"rows": params["rows"]}])
    region = runs("region", cut_extents=lambda params, result, count: [{"rect": (1, 3, 2, 6)}])
    found = runs("found", cut_extents=lambda params, result, count: [{"rows": r} for r in result])
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

    sig = Tool(NAME="sig", KIND="series", EXPECTS="gray", PRODUCES="signal", run=lambda series, params: None, reach_in_rows=lambda params: (0, 0))
    pick = Tool(NAME="pick", PRODUCES="path", select=lambda folder, params: None)
    gated = runs("gated", PATHS={"periods": lambda path: {}}, CUT_BY={"gate": "signal"}, CUT_BY_A_PART=True, cut_extents=lambda params, result, count: [{"rows": r} for r in result])
    own_row = Tool(**{**vars(gray), "reach_in_rows": lambda params: (0, 0)})     # a tool that says no reach reads without bound, and a gate below it is none a part cuts by
    tools = {t.NAME: t for t in (own_row, sig, pick, gated, tools["below"])}
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
    doc.add_node("sig", (0, 0), None, "under")
    doc.connect("below", "under")
    seen = lambda answer: plan(doc, tools, "base", cut_result=lambda nid, key, within: answer, footage="print", count=20)
    p = seen(Provisional([(0, 2), (3, 5)], (3, 9)))     # the window's walk of the gate over rows 3 to 9, nothing held
    cuts = p.entries["below"].cuts
    assert [(c.extent.rows, c.provisional, c.cut_off) for c in cuts] == [((3, 5), True, True), ((6, 8), True, False)]
    assert p.entries["below"].fed and p.unheld == {"gated"} and p.entries["gated"].standing.startswith("gate waits on sig's walk")
    assert _clip_legs(p) == [] and [leg.best for leg in window_legs(p, 3, 6)] == [{"under"}, set()]
    assert seen(Provisional([], (3, 9))).entries["under"].standing == "reads below, which cuts no rows of those the window walked; gated waits on its gate's walk"
    held = seen([(3, 5), (6, 8)])
    assert held.unheld == set() and not any(c.provisional for c in held.entries["below"].cuts) and len(_clip_legs(held)) == 2
    both = seen(Provisional([(0, 2)], (3, 9), [(3, 5), (6, 8)]))       # walked by the window and held: cut by the held
    assert both.unheld == set() and [c.extent.rows for c in both.entries["below"].cuts] == [(3, 5), (6, 8)]
    a, b, lacking = Record("print").cut(rows=(0, 4)), Record("print").cut(rows=(4, 8)), {}
    walked = Provisional("seen", (0, 2))       # one cut held and one not: cut by what the window walked alone, the held one left out
    assert _all_held_or_seen("n", (a, b), [walked, "held"], lacking) == [walked, None] and lacking == {"n": {(0, 4)}}
    del gated.CUT_BY_A_PART        # a tool that does not say its cuts of a part stand waits for the walk
    p = seen(Provisional([(0, 2), (3, 5)], (3, 9)))
    assert p.entries["gated"].cuts == () and p.entries["gated"].standing == "gate waits on sig's walk" and p.unheld == {"gated"}
    gated.CUT_BY_A_PART = True
    reach, sig.reach_in_rows = sig.reach_in_rows, lambda params: (None, 0)      # a gate whose result at a row reads every row before it: over a part it is not its result over the whole
    p = seen(Provisional([(0, 2), (3, 5)], (3, 9)))
    assert p.entries["gated"].cuts == () and p.entries["gated"].standing == "gate waits on sig's walk"
    sig.reach_in_rows = reach
    doc.remove_node("under")
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
                  cut_extents=lambda params, result, count: [{"rows": r} for r in params["rows"]])
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


def test_a_node_below_a_period_is_keyed_as_beside_it_and_neither_computes_at_nor_reads_a_row_outside_it():
    import numpy as np

    from tools import motion

    runs = []

    def counted(name, run, reach):
        return Tool(NAME=name, KIND="frame", EXPECTS="gray", PRODUCES="gray", reach_in_rows=reach,
                    run=lambda frames, row, params: runs.append((name, row)) or run(frames, row, params))

    detect = counted("detect", lambda frames, row, params: frames(row), lambda params: (0, 0))
    moved = counted("motion", motion.run, motion.reach_in_rows)
    period = Tool(NAME="period", KIND="frame", EXPECTS="gray", PRODUCES="gray", PARAMS={"rows": {"default": [[2, 6], [5, 9]]}},
                  key_params=lambda params: {}, reach_in_rows=lambda params: (0, 0),
                  cut_extents=lambda params, result, count: [{"rows": r} for r in params["rows"]])
    gray_own_row = Tool(**{**vars(gray), "reach_in_rows": lambda params: (0, 0)})
    tools = {t.NAME: t for t in (gray_own_row, period, detect, moved)}
    doc = D.from_tools([gray_own_row, period])
    nodes = {}
    for where in ("below", "beside"):
        for t in ("detect", "motion"):
            nodes[t, where] = n = doc.add_node(t).id
            doc.connect("period" if where == "below" else "gray", n)
    g = Graph(doc, Dec(), tools)

    def at(t, where, row, period=None):
        nid = nodes[t, where]
        cut = None if period is None else next(c for c in g.snapshot().entries[nid].cuts if c.extent.rows == period)
        before = len(runs)
        return g.compute(nid, row, cut=cut), len(runs) - before

    e = g.snapshot().entries
    assert all(e[nodes[t, "below"]].key == e[nodes[t, "beside"]].key for t in ("detect", "motion"))
    assert at("detect", "below", 1) == at("detect", "below", 7, (2, 6)) == (None, 0)
    at("detect", "beside", 1), g.density(nodes["detect", "beside"], 1)
    assert g.peek(1, nodes["detect", "below"]) is None and g.density(nodes["detect", "below"], 1) is None    # not the one beside's
    assert at("detect", "beside", 5)[1] == 1 and at("detect", "below", 5, (2, 6))[1] == at("detect", "below", 5, (5, 9))[1] == 0
    first, ran = at("motion", "below", 2, (2, 6))
    assert ran == 1 and not first.any() and at("motion", "beside", 0)[0].tolist() == first.tolist()      # the row before absent, as before row 0
    beside, ran = at("motion", "beside", 2)
    assert ran == 1 and (beside == 1).all()                                       # above the period, the difference: held apart
    for row in (3, 4, 5):
        at("motion", "below", row, (2, 6)), at("detect", "below", row, (2, 6))
    for row in (5, 6, 7):
        at("motion", "below", row, (5, 9))

    doc.node("period").params["rows"] = [[3, 6], [5, 9]]                         # the first period begins a row later
    g.sync()
    assert [at("detect", "below", row, (3, 6))[1] for row in (3, 4, 5)] == [0, 0, 0]
    again, ran = at("motion", "below", 3, (3, 6))
    assert ran == 1 and not again.any() and at("motion", "below", 4, (3, 6))[1] == 0
    assert [at("motion", "below", row, (5, 9))[1] for row in (5, 6, 7)] == [0, 0, 0]

    from sieve_player.bare import _Told
    from sieve_player.walk import _Walk
    g.watch([nodes["detect", "below"]])
    dens = _Told()
    w = _Walk(g, name="window", every=1 << 62, progress=_Told(), ready=_Told(), refused=_Told(), failed=_Told(), densities=dens, plan=g.snapshot())
    w.begin(0, Dec.count)
    before = len(runs)
    while w.i < w.length or w.behind():
        w.turn() if w.i < w.length else w.refold()
    folded = dens.last[0][nodes["detect", "below"]].sum(axis=1)
    assert [r for r in range(Dec.count) if folded[r]] == list(range(3, 9))       # a row outside the periods is absent, and the fold goes on past it
    assert not [row for name, row in runs[before:] if name == "detect" and not 3 <= row < 9]


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
                  cut_extents=lambda params, result, count: [{"rows": r} for r in params["rows"]])
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

    from sieve_player.worker import Worker
    doc.node("period").params["rows"] = [[2, 5], [4, 8]]
    doc.remove_node("sig")                                                    # every series node below the period: no chain above it
    g.sync()
    assert not g.snapshot().chain and g.snapshot().walk == "gray"
    w, stepped, periods, told = Worker(g), [], [], []
    g.on_event = lambda ev: stepped.append((ev.node, ev.row)) if ev.lane == "clip" and ev.kind in ("run", "step") else None
    w.periodReady.connect(lambda r, s, of, fps: periods.append(s))
    w.periodWalked.connect(lambda *t: told.append(t))

    def turned(until=lambda: False):
        while not until():
            with w._cv:
                turn = w._turn()
            if turn is None:
                return
            for job, act in turn[1]:
                g.serving(turn[0], job.name)
                act()

    asks, ask = [], w._clip_legs._ask
    w._clip_legs._ask = lambda leg: asks.append(leg) or ask(leg)
    w.walk_clip()
    turned()
    w._clip_legs._ask = ask
    assert len(asks) == 3      # each leg as it is begun, and the one behind the first counted once for all the first's rows told: no telling costs the cuts
    assert w._clip.length == 0 and periods == [2, 4]                         # the clip's own range walks no shown node for no one
    assert sorted(row for nid, row in stepped if nid == below) == [2, 3, 4, 4, 5, 6, 7] and {nid for nid, _ in stepped} == {below}

    from sieve_player.walk import HeldCut, period_keys
    periods.clear()
    w.walk_clip()
    turned(lambda: w._clip_legs.walk.i == 1)
    doc.node("period").params["rows"] = [[4, 8], [9, 10]]                     # the period under way leaves the plan as the clip walk begins again
    g.sync()
    q = g.snapshot()
    (timed,) = q.timed
    w.give_periods({("period", (9, 10)): HeldCut(period_keys(q.of(timed)), True, {}, None)})
    w.walk_clip()
    turned()
    assert periods == [4] and told[-1] == (4, 4, 0)                         # the new legs walked, the held one passed over and the end told

    periods.clear()
    doc.node("period").params["rows"] = [[4, 8], [9, 10], [0, 2]]
    g.sync()
    q = g.snapshot()
    (timed,) = q.timed
    w.give_periods({("period", r): HeldCut(period_keys(q.of(timed)), True, {}, None) for r in ((4, 8), (9, 10))})
    w.recut()
    turned()
    assert periods == [0] and not w._clip.asked and not w._win.asked         # a period added walked alone, neither own range begun again


def test_a_period_cut_by_a_gate_is_cut_by_the_gates_held_run_and_holding_its_periods_cuts_it_no_differently():
    """The window's loop: a held run re-plans, new cuts are walked, their runs are held. It ends only
    because a period's held run is never read as the gate's, and a run held again holds nothing."""
    import numpy as np

    from sieve_player import held
    from sieve_player.bare import _Told
    from sieve_player.heldwalks import gate_result, held_chain, held_periods, listed_cuts, period_run
    from sieve_player.walk import _Walk
    from tools import period

    def run(series, params):
        return {"signal": np.asarray([float(r[0, 0] % 4) for r in series.data])}

    sig = Tool(NAME="sig", KIND="series", EXPECTS="gray", PRODUCES="signal", run=run)
    tools = {t.NAME: t for t in (gray, sig, period)}
    doc = D.from_tools([gray, sig])
    doc.node("sig").band = (1, 2)       # gray is row + 1: the band keeps rows 0-1, 4-5 and 8-9
    doc.add_node("period", (0, 200), {"rows": 0, "periods": []})
    doc.connect("gray", "period")
    doc.connect("sig", "period", "gate")
    below = doc.add_node("sig").id
    doc.connect("period", below)
    runs = held.Runs(1 << 30, lambda nid, r: 0)
    g = Graph(doc, Dec(), tools, cut_result=lambda nid, key, within: gate_result(runs, "sig", key, within, Dec.count))

    def walked(p, cut=None, rows=(0, Dec.count)):
        ready = _Told()
        w = _Walk(g, name="clip", every=1 << 62, progress=_Told(), ready=ready, refused=_Told(), failed=_Told(), plan=p, cut=cut, keeps=True)
        w.begin(rows[0], rows[1] - rows[0])
        while w.i < w.length:
            w.turn()
        return ready.last[0]

    p = g.snapshot()
    assert p.entries["period"].cuts == () and p.entries["period"].standing == "gate waits on sig's walk"
    assert runs.hold(0, Dec.count, walked(p), held_chain(p, p.chain))
    g.sync()
    q = g.snapshot()
    cuts = q.entries["period"].cuts
    assert [c.extent.rows for c in cuts] == [(0, 2), (4, 6), (8, 10)]
    (w,) = q.timed
    worth = held_chain(q, [*q.chain, *w.chain])
    read = q.entries[w.heads[0]].src
    assert period_run(q, walked(q.of(w), cuts[1], (4, 5)), 4, (read, cuts[1])) is None      # a walk closed short of its cut is no cut's run, whatever rows another has
    told = lambda held, lists: ({of: (h.keys, h.spared, sorted(h.given), sorted(h.handed or ())) for of, h in held.items()},
                                [[(a, len(v["signal"])) for a, v in lst.parts] for lst in lists])
    was, lists = held_periods(q, runs), listed_cuts(runs, below, held_chain(q, w.chain), w.cuts, Dec.count)
    for c in w.cuts:
        start, rows, has, chain, cut, walked_rows = period_run(q, walked(q.of(w), c, c.extent.rows), c.extent.rows[0], (read, c))
        assert (moved := runs.hold(start, rows, has, chain, cut, worth=worth, walked=walked_rows)) == [cut]
        assert not runs.hold(start, rows, has, chain, cut, worth=worth, walked=walked_rows)
        was, lists = held_periods(q, runs, was, moved), listed_cuts(runs, below, chain, w.cuts, Dec.count, lists, moved)     # what one hold moved, and what stands of the rest
        assert told(was, lists) == told(held_periods(q, runs), listed_cuts(runs, below, chain, w.cuts, Dec.count)) and was[(read, cut)].spared
        g.sync()
        assert g.snapshot().entries["period"].cuts == cuts
    assert len(runs) == 4
    gates, of_gate = held.Runs(2, lambda nid, r: 1), held.Chain({"sig": "k"}, frozenset())
    leaf, sig = {"below": {"signal": np.zeros(2), "key": "b"}}, lambda: {"sig": {"signal": np.zeros(2), "key": "k"}}
    assert gates.hold(0, 2, leaf, held.Chain({"below": "b"}, frozenset())) and gates.hold(2, 2, sig(), of_gate, cut_by={"sig": "k"})
    assert gates.hold(4, 2, sig(), of_gate, cut_by={"sig": "k"}) == [(0, 2), (4, 6)]      # the run no node is cut by goes first
    assert not gates.hold(6, 2, sig(), of_gate, cut_by={"sig": "k"}) and [r.start for r in gates] == [2, 4]     # of runs a node is cut by, the one that came is refused: no run held moves, so nothing is walked again
    gone = lambda run: run.start == 4       # a run that serves nothing now goes before one that serves, though a node is cut by it and the other is older
    assert gates.hold(8, 2, leaf, held.Chain({"below": "b"}, frozenset()), serves_nothing=gone, cut_by={"sig": "k"}) == [(4, 6), (8, 10)]
    g.decoder.count = 9     # a count lowered under a period's end
    g.sync()
    lowered = g.snapshot()
    (w,), last = lowered.timed, lowered.entries["period"].cuts[-1]
    assert last.extent.rows == (8, 9)
    start, rows, has, chain, cut, walked_rows = period_run(lowered, walked(lowered.of(w), last, last.extent.rows), 8, (read, last))
    assert cut == (8, 9) and runs.hold(start, rows, has, chain, cut, worth=worth, walked=walked_rows)
    assert [(a, len(v["signal"])) for a, v in runs.listed(below, chain, last, 9).parts] == [(8, 1)]
