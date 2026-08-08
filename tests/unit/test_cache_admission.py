"""The gate `adr/cache-admission-is-bounded-warmup.md` admits tools against.

The rule the ADR replaced was checkable by reading a spec: a stateful node got
no key, and `test_stateful_execution.py` proved the exclusion held. The rule
that replaced it is not — `WarmupKind.BOUNDED` is a claim about how far back a
tool's output depends, and a tool making it falsely is keyed, served, and wrong
with no symptom anywhere. So the declaration is checked by running it:

> a range served from the store equals the same range computed cold, exactly.

Exactly, not approximately. `np.array_equal` and not `allclose`, because the
whole content of `BOUNDED` is that the residual is zero — a tool whose two runs
agree to a tolerance is `EPSILON`, and the ADR refuses it.

**The served range is deliberately partial**, which is the only shape that
tests anything. A store filled by an identical run answers every frame and the
tools are never called; a store filled by a *narrower* run answers a prefix and
then stops, which is the state the executor has to survive — a state that
stopped where the hits began, a window holding frames nobody fed it, and a
frontier that has to keep going.

The two nodes fail differently, and only one of them fails quietly.
`block_signal` keeps state that the store's answers walk past, so a loop with no
re-settle computes the frame after the last hit from a state that stopped
twenty frames earlier — a plausible float32 grid, caught here and nowhere else.
`detect` keeps none; what it has is a lookahead, so the input range it needs is
wider on the far side than the range it emits and a hit that satisfies the frame
being emitted can still leave the window behind it unfed. That one turns out to
be loud rather than silent: the frames the loop *did* feed sit either side of the
served range, so the window it assembles is not consecutive and `FrameSpan`
refuses it outright. Both are held here anyway. Which of two failures announces
itself is a property of a type in `core/types.py`, and a gate that only covered
the quiet one would be relying on that type to stay the way it is.

**A second graph, for the half a shared `span.start` cannot reach.** Every case
built on the pair above fills the store from a run beginning where the served run
begins, so both runs' lead-in frames are under-warmed by the same amount and
agree with each other. What that hides is the boundary the entries are written
at: an entry is settled once the lead-in *behind* the node has elapsed, which is
its own warmup plus its ancestors', and a guard reading only the node's own is
wrong by exactly the difference. `under_a_warmed_node` is where that difference
is nonzero and visible.

Real tools rather than fixtures, unlike every other file in `tests/unit/`: what
is under test is a declaration two shipped tools make, and a fixture declaring
`BOUNDED` would be testing that this file's author can write one.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, SourceSpan
from sieve.core.tool_base import WarmupKind, node_warmup_frames
from sieve.core.tool_registry import REGISTRY
from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FrameResult, execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.tools import discover

SOURCE = "footage|1|2"

BLOCKS, DETECTOR, NORMALIZED = "blocks", "detector", "norm"

#: Big enough that `block_signal`'s grid has several cells and small enough that
#: two hundred frames of it cost nothing.
WIDTH, HEIGHT = 64, 48

#: The whole range asked for, and a prefix of it. The second run is over the
#: first: the frames `NARROW` reached are answered from the store and the ones
#: after them are not, so the transition sits inside the span rather than at its
#: edge. Starting well past frame zero keeps `lead_in_shortfall` at zero, so the
#: cold run is a fully warmed one and the comparison is against the real answer.
#:
#: `WIDE` is four times `NARROW` and not merely longer, because what a run
#: leaves in the store is its *decode* range: the narrow run reads twenty-two
#: frames past its own span for `detect`'s lookahead, and `block_signal` answers
#: for every one of them. A `WIDE` short enough to sit inside that overshoot
#: would find the upper node entirely served and would test the transition on
#: one of the two tools.
WIDE = SourceSpan(start=60, end=140)
NARROW = SourceSpan(start=60, end=80)

#: A span that begins *before* `WIDE` does, which the two above cannot express
#: between them: sharing a `span.start` means sharing a `decode_start`, so both
#: runs' lead-in frames are under-warmed by the same amount and agree with each
#: other. A run starting here decodes from 39 and is fully settled by 60, so
#: every frame it is served from a `WIDE` store is one it can check.
EARLIER = SourceSpan(start=40, end=100)


class NoiseSource:
    """Frame `n` is noise seeded on `n`, so no two frames are alike.

    Noise rather than a ramp, and it is load-bearing here where it is not in
    `test_executor.py`: a ramp differences to a constant, so `block_signal`
    would emit the same grid for every frame and a window of the wrong frames
    would equal a window of the right ones. What this file is looking for is
    exactly that substitution.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        data = np.random.default_rng(index).integers(0, 256, (HEIGHT, WIDTH), dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def graph() -> Pipeline:
    """`block_signal -> detect`: the two tools this rule admits, chained.

    Without a `crop` above them, unlike the oracle's graph — the region is not
    what is under test and a root that is itself keyed and stateless would hand
    the two below it their input from the store on every frame, which is the
    easy half of what the executor has to get right.
    """
    return Pipeline(
        nodes=(
            Node(
                node_id=BLOCKS,
                tool_id="block_signal",
                version="1.0.0",
                params={"signal": "change_energy", "block": 8, "scale": 1.0, "fps": 30.0},
            ),
            Node(
                node_id=DETECTOR,
                tool_id="detect",
                version="1.0.0",
                params={
                    "freq_band": (5.0, math.inf),
                    "value_band": (0.0, math.inf),
                    "count_frac": (0.1, math.inf),
                    "window_frames": 9,
                    "centered": True,
                    "fps": 30.0,
                },
            ),
        ),
        edges=(Edge(upstream=BLOCKS, downstream=DETECTOR),),
    )


def under_a_warmed_node() -> Pipeline:
    """`block_signal -> normalize`: a node with no warmup of its own beneath one.

    `detect` cannot show this. It over-declares — `node_warmup_frames` returns 22
    for the configuration above while its arithmetic reaches `window_frames`
    back — so an entry it files one frame too early is right by a margin nobody
    declared, and the graph agrees with itself for the wrong reason. `normalize`
    declares nothing and reaches nowhere: every frame of lead-in behind it is
    its parent's, which is the whole quantity under test here.
    """
    return Pipeline(
        nodes=(
            Node(
                node_id=BLOCKS,
                tool_id="block_signal",
                version="1.0.0",
                params={"signal": "change_energy", "block": 8, "scale": 1.0, "fps": 30.0},
            ),
            Node(
                node_id=NORMALIZED,
                tool_id="normalize",
                version="1.0.0",
                params={"mode": "zscore"},
            ),
        ),
        edges=(Edge(upstream=BLOCKS, downstream=NORMALIZED),),
    )


@pytest.fixture(scope="module", autouse=True)
def shelf() -> None:
    """The process-wide registry, populated. These are the real tools."""
    discover()


def plan_over(span: SourceSpan, pipeline: Pipeline | None = None) -> ExecutionPlan:
    return ExecutionPlan.build(
        Dag.build(graph() if pipeline is None else pipeline), source=SOURCE, span=span
    )


def outputs(plan: ExecutionPlan, store: MemoryFrameStore | None = None) -> list[FrameResult]:
    return list(execute(plan, NoiseSource(), store=store))


def served_over_a_narrower_run() -> list[FrameResult]:
    """`WIDE`, against a store that only ever saw `NARROW`."""
    store = MemoryFrameStore()
    outputs(plan_over(NARROW), store)
    return outputs(plan_over(WIDE), store)


def test_a_bounded_warmup_tool_served_from_the_store_equals_its_cold_run() -> None:
    """The ADR's gate, and the whole reason `block_signal` and `detect` are keyed.

    Both nodes at once rather than one test each: a served result is one
    `FrameResult` carrying both, and splitting it would run the same two renders
    twice to make two halves of one claim.
    """
    cold = outputs(plan_over(WIDE))
    served = served_over_a_narrower_run()

    assert [result.index for result in served] == [result.index for result in cold]
    for from_store, from_scratch in zip(served, cold, strict=True):
        for node_id in (BLOCKS, DETECTOR):
            assert np.array_equal(from_store[node_id].data, from_scratch[node_id].data), (
                f"{node_id} at frame {from_store.index} differs from its cold run"
            )
            assert from_store[node_id].dtype == from_scratch[node_id].dtype


def test_the_served_range_stops_inside_the_span_and_both_tools_carry_on() -> None:
    """What makes the case above a case: a hit prefix, then a miss, per node.

    A store filled by an identical run answers every frame and calls neither
    tool, so the equality would hold over a loop that had no re-settle in it at
    all. Both halves are asserted per node, because the two nodes fail
    differently — `block_signal`'s state stops advancing, `detect`'s window
    fills with frames it was never handed.
    """
    served = served_over_a_narrower_run()

    for node_id in (BLOCKS, DETECTOR):
        cached = {int(r.index) for r in served if node_id in r.from_cache}
        computed = {int(r.index) for r in served if node_id not in r.from_cache}
        assert cached and computed, f"{node_id} was entirely {'served' if cached else 'computed'}"
        # And in that order: the store holds a prefix, so every computed frame
        # follows every served one. A miss in the middle would be a different
        # case and would make the boundary above ambiguous.
        assert max(cached) < min(computed)
        assert max(computed) == WIDE.end - 1


def test_a_run_that_was_served_nothing_computes_what_the_served_run_computed() -> None:
    """The comparison the gate rests on, stated as the thing that could be vacuous.

    If a served run and a cold run both produced the wrong answer in the same
    way — a window short at the same edge, a state cold at the same frame — the
    equality above would hold and mean nothing. So the cold run is checked
    against a *third* reading: the same frames answered by a run that was never
    narrowed, over a span wide enough that the whole of `WIDE` is settled inside
    it. Three runs, three entry points, one set of numbers.
    """
    wider = plan_over(SourceSpan(start=WIDE.start - 20, end=WIDE.end))
    from_further_back = {int(r.index): r for r in outputs(wider)}
    cold = outputs(plan_over(WIDE))

    assert plan_over(WIDE).lead_in_shortfall.frames == 0
    for result in cold:
        earlier = from_further_back[int(result.index)]
        for node_id in (BLOCKS, DETECTOR):
            assert np.array_equal(result[node_id].data, earlier[node_id].data)


def test_the_store_is_never_written_before_the_lead_in_behind_a_node_elapsed() -> None:
    """A lead-in frame is not what that node computes cold, so no key holds it.

    `detect` needs eleven frames behind its target here and the run decodes them,
    but the frames it answers for while that history is still filling are
    computed from a short window. An entry for one of them would be served to a
    later run that had decoded further back, in place of the settled answer —
    and the entry carries nothing that says which it is.

    The boundary is the *accumulated* warmup and not the node's own: `detect` is
    fed `block_signal`'s output, so the frame at which its answer stops carrying
    where the run began is one frame later than its own declaration would put it.
    Summed by hand over the two nodes rather than folded, because a walk written
    here would be the executor's walk asserted against itself.
    """
    plan = plan_over(WIDE)
    store = MemoryFrameStore()

    outputs(plan, store)

    first = int(plan.decode_start)
    # This configuration's numbers, not the specs' bounds: `detect` refines 1972
    # down to what its bands and window actually reach.
    warmups = {
        node_id: node_warmup_frames((plan.dag.spec(node_id), plan.params[node_id])).frames
        for node_id in (BLOCKS, DETECTOR)
    }
    settled = {BLOCKS: warmups[BLOCKS], DETECTOR: warmups[BLOCKS] + warmups[DETECTOR]}
    for node_id in (BLOCKS, DETECTOR):
        assert warmups[node_id] > 0
        held = {
            index for index in plan.decode_range if store.get(plan.keys[node_id], index) is not None
        }
        assert min(held) == first + settled[node_id]

    # The upper node keys frames the span does not contain, which is what makes
    # this a boundary inside the decode range rather than the span's own edge.
    # The lower one cannot: it is the node `plan.lead_in` was folded from, so
    # the first frame it may key is the first frame asked for.
    assert first + settled[BLOCKS] < WIDE.start
    assert first + settled[DETECTOR] == WIDE.start == first + plan.lead_in.frames


def test_an_entry_is_never_a_lead_in_frames_under_warmed_output() -> None:
    """`executor.py`'s first bullet, run against a store filled by another span.

    Every other case here fills the store from a run sharing this one's
    `span.start`, so both runs' lead-in frames are equally under-warmed and the
    comparison is of a mistake with itself. Here the filling run starts at 60 and
    the served run at 40: it decodes from 39, is settled well before the first
    frame it can be served, and so is in a position to notice an entry the first
    run filed out of its own lead-in.

    What that costs when the guard reads a node's own warmup: `normalize` has
    none, so the filling run keys its very first decoded frame — computed from a
    `block_signal` that had seen one frame rather than two — and hands it back
    here as the settled answer.
    """
    store = MemoryFrameStore()
    outputs(plan_over(WIDE, under_a_warmed_node()), store)

    plan = plan_over(EARLIER, under_a_warmed_node())
    served = outputs(plan, store)
    cold = outputs(plan)

    assert plan.lead_in_shortfall.frames == 0
    for node_id in (BLOCKS, NORMALIZED):
        assert {int(r.index) for r in served if node_id in r.from_cache}, (
            f"{node_id} was served nothing, so this compares two cold runs"
        )
    for from_store, from_scratch in zip(served, cold, strict=True):
        for node_id in (BLOCKS, NORMALIZED):
            assert np.array_equal(from_store[node_id].data, from_scratch[node_id].data), (
                f"{node_id} at frame {from_store.index} differs from its cold run"
            )


def test_the_two_epsilon_warmup_tools_are_still_refused() -> None:
    """The ADR admits a bounded warmup and leaves the other kind where it was.

    Named rather than derived from the shelf, because what this asserts is that
    a *measurement* nobody has taken has not quietly been assumed: whether
    `background_ema`'s difference under its declared epsilon survives into a
    detection flip is open, and until it is answered these two recompute.
    """
    for tool_id in ("background_ema", "temporal_baseline", "motion_history"):
        spec = REGISTRY.latest(tool_id)
        assert spec.warmup_kind is WarmupKind.EPSILON

    for tool_id in ("block_signal", "detect"):
        assert REGISTRY.latest(tool_id).warmup_kind is WarmupKind.BOUNDED
