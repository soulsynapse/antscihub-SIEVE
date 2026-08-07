"""Budget debt is a loan against a live repayment plan, not a mute button.

Three failure modes this pins, each fatal to the mechanism in a different way:
a debt naming a budget that does not exist silences nothing and checks
nothing; a debt whose `docs/todo/` item has been completed or deleted is
tolerance that outlived its justification; and `check(honor_debt=True)`
returning a debt for a *within*-budget interval, or honoring debt when the
caller did not ask, would let a gate's policy leak into runtime callers.

`IN_DEBT` is empty here and the first two classes of check therefore hold
vacuously — nothing has been measured yet, so nothing can be behind. The
mechanism lands before the first reading on purpose: a tolerance invented in
the session that discovers a miss is indistinguishable from moving the
ceiling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.bench.budgets import BUDGETS, IN_DEBT, BudgetMissError, Debt, check

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestDeclaredDebts:
    def test_every_debt_names_a_real_budget_under_its_own_key(self) -> None:
        for key, debt in IN_DEBT.items():
            assert key in BUDGETS, f"debt {key!r} names no budget"
            assert debt.key == key, f"debt filed under {key!r} claims to be {debt.key!r}"

    def test_every_debt_is_repaid_by_a_live_todo_item(self) -> None:
        for key, debt in IN_DEBT.items():
            item = REPO_ROOT / debt.item
            assert debt.item.replace("\\", "/").startswith("docs/todo/"), (
                f"{key}: a debt is repaid by an item, not by {debt.item!r}"
            )
            assert item.exists(), (
                f"{key}: repaying item {debt.item} is gone — the debt was either "
                "repaid (remove it) or orphaned (re-point it); neither may stand"
            )


class TestCheckHonorsDebtOnlyWhenAsked:
    @pytest.fixture()
    def indebted(self, monkeypatch: pytest.MonkeyPatch) -> Debt:
        debt = Debt(
            key="scrub_to_repaint",
            item="docs/todo/some-item.md",
            why="testing",
        )
        monkeypatch.setitem(IN_DEBT, "scrub_to_repaint", debt)
        return debt

    def test_a_miss_in_debt_is_returned_not_raised(self, indebted: Debt) -> None:
        assert check("scrub_to_repaint", 101.0, honor_debt=True) is indebted

    def test_the_default_is_the_runtime_policy_debt_changes_nothing(self, indebted: Debt) -> None:
        with pytest.raises(BudgetMissError):
            check("scrub_to_repaint", 101.0)

    def test_within_budget_returns_none_even_in_debt(self, indebted: Debt) -> None:
        assert check("scrub_to_repaint", 99.0, honor_debt=True) is None
