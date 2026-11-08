"""The step facet: the registry lists it and reports who offers it without calling a tool, and
tests/stepping.py's oracle passes a tool whose step agrees with its run and names the row where a
peeking one diverges."""
from types import SimpleNamespace

import numpy as np
import pytest

from sieve_player import registry
from sieve_player.registry.__main__ import check, report
from tests import stepping
from tools import smooth, track

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
