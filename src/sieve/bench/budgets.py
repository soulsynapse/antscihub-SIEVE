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
        # 100 ms is the classic threshold for a response reading as
        # instantaneous rather than as a delay (Miller 1968; Card, Moran &
        # Newell's ~0.1 s perceptual cycle). It is also the trigger: sustained
        # scrub latency above this is what flips the player into coarse mode,
        # so this number is enforced by degradation, not by hope. See
        # `gui/scrub_policy.py` and the note under the table in ARCHITECTURE.md.
        limit_ms=100.0,
    ),
    Budget(
        key="scrub_settle",
        label="Scrub release → exact frame",
        regime=Regime.PRE_PIPELINE,
        # Releasing the slider must land on the exact frame under the cursor,
        # however coarse the drag was. Worst case is one in-flight decode we
        # cannot cancel plus the exact one: two seeks on the reference source.
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
        # The cheap tier of the two-tier drag discipline: re-derive from the
        # retained band power, re-count, repaint. Half the 100 ms perceptual
        # threshold, because a drag emits continuously and two consecutive
        # ticks must both land inside one perceived beat.
        limit_ms=50.0,
    ),
    Budget(
        key="knob_to_graphs",
        label="Knob settle → graphs rebuilt",
        regime=Regime.IN_PIPELINE,
        # An upstream parameter edit re-runs extraction over the working
        # window and re-derives the detector. Bounded by the same ceiling as
        # the full preview render it contains — the store, not speed, is what
        # meets it after the first render.
        limit_ms=3000.0,
    ),
    Budget(
        key="knob_to_first_partial",
        label="Knob settle → graphs start filling",
        regime=Regime.IN_PIPELINE,
        # `knob_to_graphs` above is the *complete* graph, and once the detector
        # derives partial passes that is no longer the interval a user waits
        # through — they are reading a filling graph long before the window is
        # rendered. Both are real and they answer different questions: this one
        # is "when could I start reading it", that one is "when is it complete
        # and trustworthy". Kept as two rows rather than one redefined row,
        # because redefining it would silently rewrite what the findings
        # already written against `knob_to_graphs` measured.
        #
        # 500 ms rather than the 100 ms perceptual threshold: the first partial
        # cannot precede the first frames plus one transform over them, and a
        # ceiling nothing can meet is not a budget. It is the same order as
        # `open_to_first_frame` and for the same reason — this is a "something
        # is happening" latency, not a per-gesture one.
        limit_ms=500.0,
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
