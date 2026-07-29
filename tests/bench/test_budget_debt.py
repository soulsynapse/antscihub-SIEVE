"""Declared budget debt remains visible and only affects benchmark gates."""

import pytest

from sieve.bench.budgets import BUDGETS, IN_DEBT, BudgetMissError, Debt, check


def test_every_debt_names_a_real_budget_under_its_own_key() -> None:
    for key, debt in IN_DEBT.items():
        assert key in BUDGETS
        assert debt.key == key


@pytest.fixture()
def indebted(monkeypatch: pytest.MonkeyPatch) -> Debt:
    debt = Debt(key="scrub_to_repaint", why="testing")
    monkeypatch.setitem(IN_DEBT, "scrub_to_repaint", debt)
    return debt


def test_a_miss_in_debt_is_returned_when_requested(indebted: Debt) -> None:
    assert check("scrub_to_repaint", 101.0, honor_debt=True) is indebted


def test_runtime_policy_does_not_honor_debt(indebted: Debt) -> None:
    with pytest.raises(BudgetMissError):
        check("scrub_to_repaint", 101.0)


def test_within_budget_returns_none_even_in_debt(indebted: Debt) -> None:
    assert check("scrub_to_repaint", 99.0, honor_debt=True) is None
