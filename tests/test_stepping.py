"""The step facet: the registry lists it and reports who offers it without calling a tool,
tests/stepping.py's oracle passes a tool whose step agrees with its run and names the row where a
peeking one diverges, and the plan says of each chain node whether the walk steps it or runs it
whole and which node ended the prefix."""
from types import SimpleNamespace

import numpy as np
import pytest

from sieve_player import document as D
from sieve_player import registry
from sieve_player.plan import base_key, plan
from sieve_player.registry.__main__ import check, report
from tests import stepping
from tools import bake, blobs, gray, kinematics, smooth, track, tracks_filter, transitions

TOOLS = {t.NAME: t for t in (bake, blobs, gray, kinematics, smooth, track, tracks_filter, transitions)}
BASE = base_key("fake.mp4", "bgr")

SUMMING = SimpleNamespace(NAME="summing",
                          run=lambda s, p: {"signal": np.cumsum(np.asarray(s.data, np.float32)).astype(np.float32)},
                          step=lambda st, row, i, p: (np.float32((st or 0) + row), {"signal": np.float32((st or 0) + row)}))
PEEKING = SimpleNamespace(NAME="peeking",
                          run=lambda s, p: {"signal": np.array([max(s.data[i:]) for i in range(len(s.data))], np.float32)},
                          step=lambda st, row, i, p: (None, {"signal": np.float32(row)}))


def test_registry_lists_step_and_reports_it_without_calling_a_tool(capsys, monkeypatch):
    assert "step" in registry.FACETS and registry.hint("step").startswith("def step(state, row, i, params)")
    assert callable(registry.probe(track, "step")) and registry.probe(smooth, "step") is None
    for tool in (track, smooth):
        for facet in ("run", "step"):
            monkeypatch.setattr(tool, facet, lambda *a: pytest.fail("the registry called a tool"), raising=False)
    monkeypatch.setattr(smooth, "step", None)
    report(["tools"])
    lines = capsys.readouterr().out.splitlines()
    said = {name: next(l.split()[1] for l in lines[lines.index(next(l for l in lines if l.startswith(f"{name}  ("))):] if l.split()[0] == "step")
            for name in ("track", "smooth")}
    assert said == {"track": "defined", "smooth": "unsaid"}
    assert check() == 0


def test_the_oracle_passes_a_tool_that_steps_and_names_where_a_peeking_one_diverges():
    assert stepping.hold(SUMMING, [1.0, 3.0, 2.0], {})["signal"].tolist() == [1.0, 4.0, 6.0]
    with pytest.raises(AssertionError, match="over the whole at row 1"):
        stepping.hold(PEEKING, [3.0, 1.0, 2.0], {})
    assert stepping.same(np.float32(1), np.float32(1)) and not stepping.same(np.float32(1), np.float64(1))
    assert stepping.same(np.array([np.nan]), np.array([np.nan])) and not stepping.same(np.zeros(1), np.zeros((1, 1)))


def verdicts(p):
    return {nid: (p.entries[nid].steps, p.entries[nid].whole_by) for nid in p.chain}


def test_the_plan_names_where_stepping_ends_and_the_node_that_ended_it():
    """A stepping tool under a tool that runs whole runs whole, and so does every node after it,
    each naming the node that ended the prefix; a tool that does not step names nothing; the
    standing of a whole-run node stays empty since it runs."""
    p = plan(D.from_tools([gray, blobs, track, tracks_filter, kinematics, transitions]), TOOLS, BASE)
    assert p.chain == ["track", "tracks-filter", "kinematics", "transitions"]
    assert verdicts(p) == {"track": (True, None), "tracks-filter": (False, None),
                           "kinematics": (False, "tracks-filter"), "transitions": (False, "tracks-filter")}
    assert all(p.entries[nid].standing == "" for nid in p.chain)
    p = plan(D.from_tools([gray, blobs, track, kinematics, transitions]), TOOLS, BASE)
    assert p.chain == ["track", "kinematics", "transitions"] and verdicts(p) == {nid: (True, None) for nid in p.chain}
    assert not any(e.steps or e.whole_by for nid, e in p.entries.items() if nid not in p.chain)


def test_a_served_series_head_is_stepped_into_the_chain_under_it():
    """A baked blobs node served in place of the walked head hands its rows one at a time, so the
    plan steps it and the stepping chain under it as it would a walked head's."""
    doc = D.from_tools([gray, blobs, bake, track, kinematics])
    assert doc.source("track").src == "bake"
    live = plan(doc, TOOLS, BASE)
    assert live.chain == ["track", "kinematics"] and verdicts(live) == {"track": (True, None), "kinematics": (True, None)}
    D.land(doc.node("bake"), D.Bake("k", "blobs", True, (0, 9), 1, 30.0, 30.0, (), 10))
    served = plan(doc, TOOLS, BASE)
    assert served.heads == ["bake"] and served.chain == ["bake", "track", "kinematics"]
    assert verdicts(served) == {nid: (True, None) for nid in served.chain}
    assert all(served.entries[nid].standing == "" for nid in served.chain)
