"""Every registered tool's declared reach against what a window's walk gives: a row whose reach summed
along its chain lies inside the window is the full walk's row, and a series tool's bounded reach is
no larger than the rows that do differ. Driven by tests/windowing.py."""
import os

import pytest

from sieve_player.registry import discover, kind, probe
from tests.windowing import PROBE, against_full, offsets

TOOLS = {e.name: e.module for e in discover(os.path.join(os.path.dirname(__file__), "..", "tools")) if e.ok}
UNDRIVEN = {"file": "a selector: hands out no rows"}


def outermost_reached(a, b, own, reach, ends):
    """The rows of a..b at its edges a series node's own reach must make differ: on each side its own
    bounded reach is all of the summed one and the window's edge is not the end its rows are of."""
    rows = []
    if own[0] and reach[0] == own[0] and a > ends[0]:
        rows.append(a + own[0] - 1)
    if own[1] and reach[1] == own[1] and b < ends[1]:
        rows.append(b - own[1])
    return rows


@pytest.mark.parametrize("name", sorted(TOOLS))
def test_a_window_differs_from_the_full_walk_only_within_the_summed_reach(name, tmp_path):
    said, why, nid, found = against_full(name, {**TOOLS, "probe": PROBE}, str(tmp_path))
    if name in UNDRIVEN:
        assert why is not None, f"{name} is driven now: take it out of UNDRIVEN"
        return
    assert why is None, f"{name} could not be driven: {why}"
    t, problems = TOOLS[name], []
    for a, b, node, reach, planned, bad, over, ends in found:
        if reach != planned:
            problems.append(f"{node} summed {reach}, the plan says {planned}")
        if over:
            problems.append(f"[{a},{b}) {node}, reach summed {reach}, differs past it at {offsets(over, a, b)} (all differing: {offsets(bad, a, b)})")
        if node == nid and kind(t) == "series":
            short = [r for r in outermost_reached(a, b, said, reach, ends) if r not in bad]
            if short:
                problems.append(f"[{a},{b}) {node}, reach summed {reach}, does not differ at {offsets(short, a, b)}: the reach declared is larger than the one read")
    assert not problems, f"{name} declares {said}: " + "; ".join(problems)


def test_every_tool_declares_its_reach():
    undeclared = sorted(n for n, t in TOOLS.items() if probe(t, "reach_in_rows") is None)
    assert not undeclared, f"declare no reach_in_rows: {undeclared}"
