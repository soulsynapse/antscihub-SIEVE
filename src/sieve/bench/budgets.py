"""The latency budget table from ``ARCHITECTURE.md`` section 1, as data.

[INTENT] One transcription of the table, in one place, that every measurement
reads. The alternative -- a threshold written into each benchmark that checks
it -- puts the same number in several files and lets them drift apart silently.
A budget that disagrees with the architecture document is a bug this module
exists to make findable: it is the only place to look.

[STALE WHEN] ``ARCHITECTURE.md`` section 1's table changes. The source wins;
this is a derived copy and ``tests/bench/test_budget_table.py`` is what keeps
the two honest about diverging.

Deliberately dependency-free. ``bench/`` is imported by headless and CLI runs
(``.importlinter``: ``qt-free-below-gui``), and the budget table in particular
is read by tooling that has no reason to pay for numpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

__all__ = [
    "BUDGETS",
    "REGRESSION_MARGIN",
    "Budget",
    "Regime",
    "Verdict",
    "budget",
    "verdict_for",
]


class Regime(StrEnum):
    """The two speed regimes section 1 names, both load-bearing.

    Kept distinct because a change that helps one at measurable cost to the
    other is a regression rather than a tradeoff, and a report that pools them
    cannot show that.
    """

    PRE_PIPELINE = "pre-pipeline"
    IN_PIPELINE = "in-pipeline"


class Verdict(StrEnum):
    """How a measurement stands against its budget.

    ``REGRESSED`` is separated from ``OVER`` because section 1 treats them
    differently: over budget is a bug to fix, while over budget *by more than
    the margin* is the thing a PR has to justify explicitly.
    """

    WITHIN = "within"
    OVER = "over"
    REGRESSED = "regressed"


@dataclass(frozen=True, slots=True)
class Budget:
    """One row of the section 1 table.

    ``key`` is the stable identifier a measurement cites. It is not derived
    from ``interaction``: the prose wording is expected to be edited by the
    voice rewrite, and a key that moves when prose moves would silently
    orphan every measurement citing it.
    """

    key: str
    interaction: str
    milliseconds: float
    regime: Regime

    @property
    def regression_threshold_ms(self) -> float:
        """The point past which section 1 requires explicit justification."""
        return self.milliseconds * (1.0 + REGRESSION_MARGIN)


# ARCHITECTURE.md section 1: "a PR that regresses any budget by more than 20%
# requires explicit justification".
REGRESSION_MARGIN: Final = 0.20

_TABLE: Final = (
    Budget("file-open", "File open -> first frame visible", 500, Regime.PRE_PIPELINE),
    Budget("scrub-seek", "Scrub / seek -> frame repainted", 50, Regime.PRE_PIPELINE),
    Budget(
        "replicate-cut",
        "Replicate cut confirmed -> ready to add filter",
        200,
        Regime.PRE_PIPELINE,
    ),
    Budget(
        "first-filter-tick",
        "First filter added -> first graph tick on screen",
        2000,
        Regime.IN_PIPELINE,
    ),
    Budget("slider-preview", "Slider drag -> preview clip repainted", 100, Regime.IN_PIPELINE),
    Budget("slider-graph", "Slider drag -> dependent graph updated", 200, Regime.IN_PIPELINE),
    Budget(
        "clip-render",
        "Full-clip preview render (5-10 s clip, typical pipeline)",
        3000,
        Regime.IN_PIPELINE,
    ),
)

BUDGETS: Final = MappingProxyType({entry.key: entry for entry in _TABLE})


def budget(key: str) -> Budget:
    """Look up a budget, failing loudly on an unknown key.

    A benchmark citing a key that no longer exists has lost its reason to run.
    Returning ``None`` would let it keep passing while measuring nothing.
    """
    try:
        return BUDGETS[key]
    except KeyError:
        known = ", ".join(sorted(BUDGETS))
        raise KeyError(
            f"No budget named {key!r}. ARCHITECTURE.md section 1 defines: {known}"
        ) from None


def verdict_for(key: str, measured_ms: float, *, share: float = 1.0) -> Verdict:
    """Classify a measurement against its budget.

    ``share`` is the fraction of the end-to-end budget this measurement is
    allotted, for the common case where what is measurable is one component of
    an interaction the budget describes whole. A decode call is not a repaint;
    charging a decode the full scrub budget would report a pass that the
    assembled interaction does not have.

    [ASSUMPTION] Shares are judgement, not measurement. Each caller states its
    own and says why at the call site. They become measurements once the
    interaction they decompose exists end to end.
    """
    if not 0.0 < share <= 1.0:
        raise ValueError(f"share must fall in (0, 1]; got {share}")
    allotted = budget(key).milliseconds * share
    if measured_ms <= allotted:
        return Verdict.WITHIN
    if measured_ms <= allotted * (1.0 + REGRESSION_MARGIN):
        return Verdict.OVER
    return Verdict.REGRESSED
