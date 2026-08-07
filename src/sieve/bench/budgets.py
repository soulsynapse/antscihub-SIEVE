"""The latency budget table. Source of truth in code for both speed regimes.

A budget miss is a defect, not a tradeoff. The labels below are copied verbatim
from the two-regime block in `docs/VISION.md`, and `tests/bench/test_budget_table.py`
parses that document and fails if the two ever disagree — so the prose cannot
drift away from what the code enforces, in either direction.

**A ceiling nothing publishes is a number, not a budget**, which is the half of
the claim this table cannot state by itself. It is stated by `WITHOUT_PRODUCER`
below and checked by `tests/bench/test_budget_producers.py`. Right now that set
holds every key: nothing in `src/` outside this package measures anything, and
the set is where that fact is written down rather than left to be inferred from
the absence of a call.

Every limit carries an **anchor** comment saying which perceptual band the
number came from (~100 ms reads as instantaneous, ~1 s holds the flow of
thought, ~10 s holds attention; Card, Moran & Newell — Nielsen's response-time
bands are the same numbers). A budget anchored to perception outlives the
hardware that first met it; one anchored to "what we achieved once" is history
wearing a rule's costume. The ceilings are promised for the *reference
workload* — the scope note under the table in VISION.md is the authority on
what that means and what is owed outside it.

A budget currently missed on purpose — temporary slowness bought for eventual
speed — is declared in `IN_DEBT` with the `docs/todo/` item that repays it. A
benchmark tolerates a key in debt visibly, by xfailing rather than passing;
`tests/bench/test_budget_debt.py` fails the suite if the item file is gone, so
debt cannot outlive its repayment plan. A runtime display never honors debt: a
slow session looks slow regardless.

The table lands before the first measurement (`docs/todo/`, 06.3) for the
reason the anchors exist: a ceiling written after the reading is a description
of the reading.
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
#: humans read and what VISION.md is checked against.
BUDGETS: dict[str, Budget] = _table(
    Budget(
        key="open_to_first_frame",
        label="Open file → first frame",
        regime=Regime.PRE_PIPELINE,
        # A "something is happening" latency: half the ~1 s flow-of-thought
        # band, because opening is a gesture with a visible consequence, not a
        # submitted job.
        limit_ms=500.0,
    ),
    Budget(
        key="scrub_to_repaint",
        label="Scrub/seek → frame repaint",
        regime=Regime.PRE_PIPELINE,
        # 100 ms is the classic threshold for a response reading as
        # instantaneous rather than as a delay (Miller 1968; Card, Moran &
        # Newell's ~0.1 s perceptual cycle). Unreachable by decoding faster: a
        # random seek into 5.3K H.264 measured ~68 ms in v2, of which ~47 ms
        # was the container seek itself. It is met by degrading during the drag
        # and landing exactly on release, which is why this and `scrub_settle`
        # are a pair rather than one number.
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
        # Confirming a cut is a click with a state change, not a render: two
        # perceptual beats, same band as slider_to_graph.
        limit_ms=200.0,
    ),
    Budget(
        key="tool_to_first_tick",
        label="First tool → first graph tick",
        regime=Regime.IN_PIPELINE,
        # First-run cost is real work (decode + warmup + one transform), so
        # this sits in the flow-of-thought band rather than the instantaneous
        # one — doubled, because the first tick follows a *decision* (adding a
        # tool), not a drag, and a decision tolerates a beat of setup.
        limit_ms=2000.0,
    ),
    Budget(
        key="slider_to_preview",
        label="Slider drag → preview repaint",
        regime=Regime.IN_PIPELINE,
        # The 100 ms instantaneous band: a drag is direct manipulation and the
        # preview is its hand.
        limit_ms=100.0,
    ),
    Budget(
        key="slider_to_graph",
        label="Slider drag → graph update",
        regime=Regime.IN_PIPELINE,
        # Two perceptual beats: the graph may trail the preview by one tick
        # without the pair reading as disconnected.
        limit_ms=200.0,
    ),
    Budget(
        key="full_preview_render",
        label="Full preview render (5–10s clip)",
        regime=Regime.IN_PIPELINE,
        # Attention-band latency, met by the preview store rather than by speed
        # after the first render. Not a per-gesture ceiling.
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
        key="density_rebuild",
        label="Band power arrives → density rebuilt",
        regime=Regime.IN_PIPELINE,
        # Binning the whole `(T, B)` band power into a density surface. 100 ms
        # is the instantaneous band: a partial pass lands repeatedly while a
        # window renders, and each rebuild must fit inside one perceived beat
        # rather than merely inside the 500 ms `knob_to_first_partial` it sits
        # within.
        #
        # An attribution, not a cap. v2 derived a block-count refusal from this
        # ceiling while the binning was on the GUI thread, and deleted the
        # derivation once it moved off: a limit justified by "the window
        # freezes" has no justification once the window does not freeze. What
        # survives the move is what the number says about where cost went.
        limit_ms=100.0,
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
        # and trustworthy". Two rows rather than one redefined row, because
        # redefining one would silently rewrite what a finding taken against it
        # had measured.
        #
        # 500 ms rather than the 100 ms perceptual threshold: the first partial
        # cannot precede the first frames plus one transform over them, and a
        # ceiling nothing can meet is not a budget. It is the same order as
        # `open_to_first_frame` and for the same reason — this is a "something
        # is happening" latency, not a per-gesture one.
        limit_ms=500.0,
    ),
)


#: Budgets that no module under `src/` names, and so that nothing can ever be
#: measured against at run time. A miss must be *visible*; a ceiling with no
#: publisher cannot be missed, which looks like compliance and is its absence.
#: Writing the gap down as a set makes it a list that only shrinks —
#: `tests/bench/test_budget_producers.py` fails both on a budget missing from
#: here that has no producer *and* on one listed here that has since grown one.
#:
#: It is currently the whole table, and that is the honest reading of a repo
#: with no preview session and no GUI: twelve ceilings, nothing measuring any
#: of them. The set is the ledger the next two items pay down — 06.2 gives the
#: in-pipeline keys a publisher, 06.3 gives two of them a clock — and each
#: payment is a deletion here rather than a silently truer tree. Spelled out
#: rather than derived from `BUDGETS` for that reason: a set that says "all of
#: them" stays true through the first publisher and names nothing to delete.
WITHOUT_PRODUCER: frozenset[str] = frozenset(
    {
        "open_to_first_frame",
        "scrub_to_repaint",
        "scrub_settle",
        "cut_to_ready",
        "tool_to_first_tick",
        "slider_to_preview",
        "slider_to_graph",
        "full_preview_render",
        "band_drag_repaint",
        "knob_to_graphs",
        "density_rebuild",
        "knob_to_first_partial",
    }
)


#: Timed and published are independent gaps, and this is the wider one: a
#: published budget shows a session it was missed, a timed one catches the
#: miss before it ships.
#:
#: Declared, not derived, because `src/` may not read `tests/`.
#: `tests/bench/test_budget_producers.py` scans every `within_budget("...")`
#: call site and fails in both directions.
#:
#: Empty until 06.3, which is the first thing in this repo that measures rather
#: than declares.
TIMED: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Debt:
    """A budget miss that is declared, scheduled for repayment, and tolerated
    by a benchmark — never by the runtime display."""

    key: str
    #: The `docs/todo/` item that repays it, as a repo-relative path. A debt
    #: whose item file no longer exists fails `tests/bench/test_budget_debt.py`
    #: — completing the item without restoring the budget invalidates the debt
    #: rather than laundering it.
    item: str
    #: One line: what is temporarily slower and what it is buying.
    why: str


#: Budgets currently missed on purpose. Empty is the normal state and is also
#: the only state available before anything has been measured: an entry is a
#: loan against a named `docs/todo/` item, and the honest response to a
#: benchmark xfail here is to go read that item, not to relax anything.
IN_DEBT: dict[str, Debt] = {}


def check(key: str, elapsed_ms: float, *, honor_debt: bool = False) -> Debt | None:
    """Assert a measured interval is within its budget.

    With `honor_debt`, a miss on a key declared in `IN_DEBT` returns the debt
    instead of raising — the caller (a benchmark) is expected to xfail with the
    debt's item, which keeps the miss visible in the report. Runtime callers
    must not pass it: a session's slowness is never excused on screen.

    Raises:
        KeyError: if `key` is not a known budget.
        BudgetMissError: if the interval exceeds the budget and no debt applies.
    """
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
