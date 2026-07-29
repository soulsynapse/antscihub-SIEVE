from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Regime(StrEnum):
    PRE_PIPELINE = "pre-pipeline"
    IN_PIPELINE = "in-pipeline"


@dataclass(frozen=True, slots=True)
class Budget:
    key: str
    label: str
    regime: Regime
    limit_ms: float

    def exceeded_by(self, elapsed_ms: float) -> float:
        return elapsed_ms - self.limit_ms


class BudgetMissError(AssertionError):
    pass


def _table(*budgets: Budget) -> dict[str, Budget]:
    return {budget.key: budget for budget in budgets}


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
        limit_ms=100.0,
    ),
    Budget(
        key="scrub_settle",
        label="Scrub release → exact frame",
        regime=Regime.PRE_PIPELINE,
        limit_ms=250.0,
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
    Budget(
        key="band_drag_repaint",
        label="Band drag → graphs repaint",
        regime=Regime.IN_PIPELINE,
        limit_ms=50.0,
    ),
    Budget(
        key="knob_to_graphs",
        label="Knob settle → graphs rebuilt",
        regime=Regime.IN_PIPELINE,
        limit_ms=3000.0,
    ),
    Budget(
        key="density_rebuild",
        label="Band power arrives → density rebuilt",
        regime=Regime.IN_PIPELINE,
        limit_ms=100.0,
    ),
    Budget(
        key="knob_to_first_partial",
        label="Knob settle → graphs start filling",
        regime=Regime.IN_PIPELINE,
        limit_ms=500.0,
    ),
)


WITHOUT_PRODUCER: frozenset[str] = frozenset(
    {
        "open_to_first_frame",
        "scrub_settle",
        "cut_to_ready",
        "slider_to_graph",
    }
)


TIMED: frozenset[str] = frozenset(
    {
        "open_to_first_frame",
        "scrub_settle",
        "density_rebuild",
    }
)


@dataclass(frozen=True, slots=True)
class Debt:
    key: str

    why: str


IN_DEBT: dict[str, Debt] = {
    "density_rebuild": Debt(
        key="density_rebuild",
        why=(
            "the cap half of this debt is repaid — the binning moved to the detector "
            "thread and the block-count refusal is gone, so the number attributes rather "
            "than forbids. What is left is the timing: B = 16,384 reads 98-140 ms against "
            "a 100 ms ceiling on the reference workstation, headroom under the machine's "
            "own variation. The open question is whether 100 ms is still the right ceiling "
            "at all now that a miss means a graph filling late rather than a frozen window"
        ),
    )
}


def check(key: str, elapsed_ms: float, *, honor_debt: bool = False) -> Debt | None:
    budget = BUDGETS[key]
    over = budget.exceeded_by(elapsed_ms)
    if over <= 0.0:
        return None
    debt = IN_DEBT.get(key)
    if honor_debt and debt is not None:
        return debt
    raise BudgetMissError(
        f"{budget.label}: {elapsed_ms:.1f} ms exceeds the "
        f"{budget.limit_ms:.0f} ms {budget.regime} budget by {over:.1f} ms"
    )
