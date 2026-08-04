"""`bench/budgets.py` must agree with the budget table in ARCHITECTURE.md.

Prose and code drift apart silently, and the budgets are the operational
definition of the product requirement — a document claiming 50 ms while the
code enforces 500 ms is worse than having no document. This parses the source
of truth and compares both directions, so neither side can be edited alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sieve.bench.budgets import BUDGETS, Budget, BudgetMissError, Regime, check

ARCHITECTURE = Path(__file__).resolve().parents[2] / "docs" / "ARCHITECTURE.md"

_REGIME_HEADERS = {
    "PRE-PIPELINE": Regime.PRE_PIPELINE,
    "IN-PIPELINE": Regime.IN_PIPELINE,
}
_REGIME_LINE = re.compile(r"^(PRE-PIPELINE|IN-PIPELINE)\b")
_BUDGET_LINE = re.compile(r"^\s+(?P<label>\S.*?):\s*<\s*(?P<value>[\d.]+)\s*(?P<unit>ms|s)\s*$")


def parse_architecture_budgets() -> dict[str, tuple[Regime, float]]:
    """Extract `label -> (regime, limit in ms)` from the architecture document."""
    found: dict[str, tuple[Regime, float]] = {}
    regime: Regime | None = None

    for line in ARCHITECTURE.read_text(encoding="utf-8").splitlines():
        header = _REGIME_LINE.match(line)
        if header is not None:
            regime = _REGIME_HEADERS[header.group(1)]
            continue
        entry = _BUDGET_LINE.match(line)
        if entry is None or regime is None:
            continue
        value = float(entry.group("value"))
        limit_ms = value if entry.group("unit") == "ms" else value * 1000.0
        found[entry.group("label")] = (regime, limit_ms)

    return found


@pytest.fixture(scope="module")
def documented() -> dict[str, tuple[Regime, float]]:
    parsed = parse_architecture_budgets()
    assert parsed, f"Parsed no budgets from {ARCHITECTURE} — the table format changed"
    return parsed


def test_every_documented_budget_is_implemented(
    documented: dict[str, tuple[Regime, float]],
) -> None:
    implemented = {budget.label for budget in BUDGETS.values()}
    assert set(documented) - implemented == set()


def test_every_implemented_budget_is_documented(
    documented: dict[str, tuple[Regime, float]],
) -> None:
    implemented = {budget.label for budget in BUDGETS.values()}
    assert implemented - set(documented) == set()


def test_limits_and_regimes_match(documented: dict[str, tuple[Regime, float]]) -> None:
    for budget in BUDGETS.values():
        regime, limit_ms = documented[budget.label]
        assert budget.regime is regime, f"{budget.label} regime disagrees"
        assert budget.limit_ms == pytest.approx(limit_ms), f"{budget.label} limit disagrees"


def test_keys_are_unique_and_match_their_entries() -> None:
    for key, budget in BUDGETS.items():
        assert budget.key == key


class TestCheck:
    def test_within_budget_passes(self) -> None:
        check("scrub_to_repaint", 99.0)

    def test_exactly_at_budget_passes(self) -> None:
        check("scrub_to_repaint", 100.0)

    def test_over_budget_raises_with_the_overage(self) -> None:
        with pytest.raises(BudgetMissError, match="exceeds"):
            check("scrub_to_repaint", 101.0)

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(KeyError):
            check("not_a_budget", 1.0)

    def test_exceeded_by_reports_signed_headroom(self) -> None:
        budget = Budget(key="k", label="l", regime=Regime.PRE_PIPELINE, limit_ms=100.0)
        assert budget.exceeded_by(120.0) == pytest.approx(20.0)
        assert budget.exceeded_by(80.0) == pytest.approx(-20.0)
