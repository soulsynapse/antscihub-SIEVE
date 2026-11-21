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
    p = plan(doc, tools, "base", cut_file=lambda nid, up: asked.append(nid), cut_result=lambda nid: [(0, 2), (5, 7)], footage="print")
    assert [c.extent.rows for c in p.entries["below"].cuts] == [(0, 2), (5, 7)] and not asked and p.entries["found"].file is None
    assert plan(doc, tools, "base", footage="print").entries["below"].cuts == (Record("print"),)        # a declaration that raises cuts nothing
