"""The latency budget table. Source of truth in code for both speed regimes.

A budget miss is a defect, not a tradeoff (ARCHITECTURE.md non-negotiable #4).
The labels below are copied verbatim from the budget block in
`docs/ARCHITECTURE.md`, and `tests/bench/test_budget_table.py` parses that
document and fails if the two ever disagree — so the prose cannot drift away
from what the code enforces, in either direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Regime(StrEnum):
    """The two speed regimes. Improving one at the cost of the other is a defect."""

    PRE_PIPELINE = "pre-pipeline"
    IN_PIPELINE = "in-pipeline"


@dataclass(frozen=True, slots=True)
class Budget:
    """One latency ceiling."""

    key: str
    label: str
    regime: Regime
    limit_ms: float

    def exceeded_by(self, elapsed_ms: float) -> float:
        """Milliseconds over budget; zero or negative when within it."""
        return elapsed_ms - self.limit_ms


class BudgetMissError(AssertionError):
    """Raised when a measured interval exceeds its budget."""


def _table(*budgets: Budget) -> dict[str, Budget]:
    return {budget.key: budget for budget in budgets}


#: Keyed by a stable identifier that call sites reference; the label is what
#: humans read and what the architecture document is checked against.
BUDGETS: dict[str, Budget] = _table(
    Budget(
        key="open_to_first_frame",
        label="Open file → first frame",
        regime=Regime.PRE_PIPELINE,
        limit_ms=500.0,
    ),
    Budget(
        key="scrub_to_repaint",
        label="Scrub/seek → frame repaint",
        regime=Regime.PRE_PIPELINE,
        limit_ms=50.0,
    ),
    Budget(
        key="cut_to_ready",
        label="Cut confirmed → ready",
        regime=Regime.PRE_PIPELINE,
        limit_ms=200.0,
    ),
    Budget(
        key="filter_to_first_tick",
        label="First filter → first graph tick",
        regime=Regime.IN_PIPELINE,
        limit_ms=2000.0,
    ),
    Budget(
        key="slider_to_preview",
        label="Slider drag → preview repaint",
        regime=Regime.IN_PIPELINE,
        limit_ms=100.0,
    ),
    Budget(
        key="slider_to_graph",
        label="Slider drag → graph update",
        regime=Regime.IN_PIPELINE,
        limit_ms=200.0,
    ),
    Budget(
        key="full_preview_render",
        label="Full preview render (5–10s clip)",
        regime=Regime.IN_PIPELINE,
        limit_ms=3000.0,
    ),
)


def check(key: str, elapsed_ms: float) -> None:
    """Assert a measured interval is within its budget.

    Raises:
        KeyError: if `key` is not a known budget.
        BudgetMiss: if the interval exceeds the budget.
    """
    budget = BUDGETS[key]
    over = budget.exceeded_by(elapsed_ms)
    if over > 0.0:
        raise BudgetMissError(
            f"{budget.label}: {elapsed_ms:.1f} ms exceeds the "
            f"{budget.limit_ms:.0f} ms {budget.regime} budget by {over:.1f} ms"
        )
