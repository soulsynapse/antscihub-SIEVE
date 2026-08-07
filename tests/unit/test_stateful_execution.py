"""Where a tool's state lives, and the three ways that could be wrong.

The arithmetic of any particular tool is that tool's test. What is here is the
machinery around it, and each of these fails for a reason nothing downstream
would report:

**State shared between runs.** Two replicates previewing one node concurrently
get one model fed by two arenas. Every frame that comes out is plausible.

**State surviving a run.** A second pass over the same span starts warm, so the
run is not reproducible and the lead-in the plan decoded was pointless.

**A stateful node given a cache key.** Its output at a frame depends on where the
run began. Whether that dependence has decayed to nothing by the time anything is
yielded is exactly what `warmup_frames` claims, and nothing that derives a key
can check the claim — so an entry served across spans would rest on an unverified
warmup derivation.

The last is the one worth spelling out, and two cases below do it from opposite
sides: the honest tool agrees across spans, the dishonest one does not, and they
are indistinguishable to everything that decides what may be cached.

The tools are declared here rather than reached for from `sieve.tools`, which is
`test_plan.py`'s reason and one more: the shelf is empty at this step, and a case
that named the first real tool would be asserting against that tool rather than
against the contract the executor reads.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from sieve.core.pipeline_model import Node, Pipeline, SourceSpan
from sieve.core.tool_base import ArraySpec, ElementRelation, ParamsBase, ParamStereotype
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import NO_FRAMES, ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import is_cacheable
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import _bind, execute
from sieve.pipeline.plan import ExecutionPlan

SOURCE = "footage|1|2"
WIDTH, HEIGHT = 8, 6

#: A scratch shelf, for `test_executor.py`'s reason.
SHELF = ToolRegistry()

#: Frames the exponential model below needs before two runs of it agree. Large
#: enough that the lead-in is visibly not the span, and declared as the bound so
#: the plan charges it.
SETTLES_IN = 90


def background_run(params: BackgroundParams, window: FrameSpan, state: list[Any]) -> Frame:
    """An exponential background model, which is the shape of the real hazard.

    Deterministic, stateful, and honest: its output at a frame depends on where
    the run began, and that dependence decays geometrically, so two runs that
    both saw `SETTLES_IN` frames agree at a shared frame to well inside a uint8.
    """
    frame = window.target
    incoming = frame.data.astype(np.float32)
    if not state:
        state.append(incoming)
    else:
        state[0] = state[0] + params.alpha * (incoming - state[0])
    return Frame(data=state[0].astype(np.uint8), index=frame.index, channels=frame.channels)


@register_tool(
    tool_id="background",
    version="1.0.0",
    summary="An exponential model of what does not move.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    run=background_run,
    element=ElementRelation.PRESERVED,
    settling_epsilon=1.0,
    stateful=True,
    state_factory=list,
    param_stereotypes={"alpha": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class BackgroundParams(ParamsBase):
    alpha: float = 0.5

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        return FrameCount(SETTLES_IN)


def accumulate_run(params: AccumulateParams, window: FrameSpan, state: list[int]) -> Frame:
    """A running sum declaring it needs no warmup, which is false."""
    del params
    frame = window.target
    state.append(int(frame.data.flat[0]))
    return Frame(
        data=np.full_like(frame.data, sum(state) % 251),
        index=frame.index,
        channels=frame.channels,
    )


@register_tool(
    tool_id="accumulate",
    version="1.0.0",
    summary="Running sum, declaring it needs no warmup, which is false.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    run=accumulate_run,
    element=ElementRelation.PRESERVED,
    stateful=True,
    state_factory=list,
    registry=SHELF,
)
class AccumulateParams(ParamsBase):
    pass


def plain_run(params: PlainParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    return window.target


@register_tool(
    tool_id="plain",
    version="1.0.0",
    summary="Keeps nothing, so there is nothing to mint for it.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    run=plain_run,
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class PlainParams(ParamsBase):
    pass


class RampSource:
    """Frame `n` is a flat field of intensity `n`, and reads are counted.

    A ramp rather than noise because the model of a ramp is a number a reader can
    predict, which is what lets an assertion below say *which* frame the model
    had seen rather than merely that it had seen some.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        data = np.full((HEIGHT, WIDTH), min(index, 255), dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def node(node_id: str, tool_id: str) -> Node:
    return Node(node_id=node_id, tool_id=tool_id, version="1.0.0")


def plan_over(span: SourceSpan, tool_id: str = "background", node_id: str = "bg") -> ExecutionPlan:
    return ExecutionPlan.build(
        Dag.build(Pipeline(nodes=(node(node_id, tool_id),)), SHELF), source=SOURCE, span=span
    )


def test_a_stateful_node_gets_no_cache_key_and_writes_no_entry() -> None:
    """The plan carries no key for it, so nothing is stored and nothing served.

    Not a performance choice, and not a claim that this tool's output varies —
    the next case shows it does not. The rule is on the category, because the two
    cases after this one are indistinguishable to `Dag.node_keys`. The plan is
    where that becomes visible, and the store is where it would have gone wrong.
    """
    plan = plan_over(SourceSpan(start=100, end=104))
    store = MemoryFrameStore()

    assert plan.key("bg") is None
    results = list(execute(plan, RampSource(), store=store))

    assert len(results) == 4
    assert not any(result.from_cache for result in results)
    assert len(store) == 0


def test_a_correct_warmup_is_what_makes_two_spans_agree() -> None:
    """Two runs starting 50 frames apart give the same answer at a shared frame.

    Worth stating explicitly because it is the opposite of what the exclusion
    from the cache looks like it is claiming. A stateful tool whose
    `warmup_frames` is *right* is span-independent: both runs reach frame 150
    having seen at least 90 frames, both models have converged to within the
    declared epsilon, and after the narrowing back to uint8 they are identical.

    So the reason a stateful node is not cached is not that its output varies. It
    is that this agreement is a consequence of a number the tool's author wrote
    down, nothing that derives a key can check it, and a key that does not carry
    the run's origin is a key resting on that unverified claim.
    """
    early = plan_over(SourceSpan(start=100, end=151))
    late = plan_over(SourceSpan(start=150, end=151))
    assert early.decode_start != late.decode_start

    from_early = list(execute(early, RampSource()))[-1]
    from_late = list(execute(late, RampSource()))[-1]

    assert from_early.index == from_late.index == 150
    assert np.array_equal(from_early["bg"].data, from_late["bg"].data)


def test_a_tool_whose_warmup_is_a_lie_disagrees_with_itself_across_spans() -> None:
    """And nothing that derives a key can tell it from the honest one.

    An accumulator declaring zero warmup is the whole hazard in six lines: it is
    stateful, it is deterministic, its output at frame `i` is the sum of every
    frame from wherever the run began, and every static declaration it makes is
    identical in kind to the model's above. If `cache_policy` admitted stateful
    nodes on the strength of a declared warmup, this node would be keyed, the
    first run's entry for frame 12 would be served to the second, and the second
    run would report a number that no run of it ever computed.

    That failure is invisible in every way this repo cares about: the key is
    well-formed, the entry is present, the result is a plausible image, and only
    a machine that ran the other span disagrees.
    """
    spec = AccumulateParams.spec()
    assert spec.warmup_frames == NO_FRAMES

    early = plan_over(SourceSpan(start=5, end=13), "accumulate", "acc")
    late = plan_over(SourceSpan(start=10, end=13), "accumulate", "acc")

    from_five = list(execute(early, RampSource()))[-1]
    from_ten = list(execute(late, RampSource()))[-1]

    assert from_five.index == from_ten.index == 12
    assert not np.array_equal(from_five["acc"].data, from_ten["acc"].data)
    # The declaration a key would have been derived from is identical in kind to
    # the honest tool's, and this one is wrong. Neither gets a key.
    assert not is_cacheable(spec) and spec.deterministic


def test_the_lead_in_is_what_settles_the_model() -> None:
    """90 frames are decoded before the span, and the tool sees all of them.

    `test_plan.py` proves the lead-in *arithmetic*; this proves it has a
    consumer. A loop that skipped the lead-in would decode the same frames and
    hand the caller a model that had seen two.
    """
    plan = plan_over(SourceSpan(start=100, end=102))
    source = RampSource()

    results = list(execute(plan, source))

    assert plan.lead_in == BackgroundParams.spec().warmup_frames == FrameCount(SETTLES_IN)
    assert source.reads == list(range(10, 102))
    assert [result.index for result in results] == [100, 101]


def test_two_concurrent_runs_of_one_node_do_not_share_a_model() -> None:
    """Interleaved runs give each what it would have got alone.

    The constraint the whole design is shaped around: state belongs to the run,
    not to the tool. A tool closing over its own model would pass this file's
    other cases and fail only here — and in production only when two replicates
    previewed at once, producing a background fed by two arenas and frames that
    look entirely reasonable.

    Interleaved rather than run one-then-the-other, because generators make the
    sharing visible: the two `execute` calls are alive at the same time and each
    step of one lands between two steps of the other.
    """
    span = SourceSpan(start=95, end=99)
    alone = [result["bg"].data.copy() for result in execute(plan_over(span), RampSource())]

    left = execute(plan_over(span), RampSource())
    right = execute(plan_over(span), RampSource())
    interleaved = [
        (next(left)["bg"].data.copy(), next(right)["bg"].data.copy()) for _ in range(len(alone))
    ]

    for expected, (from_left, from_right) in zip(alone, interleaved, strict=True):
        assert np.array_equal(from_left, expected)
        assert np.array_equal(from_right, expected)


def test_a_second_run_starts_cold() -> None:
    """A run is reproducible, which means its state does not outlive it.

    The factory is called from `_bind`, which `execute` calls once per generator,
    so the model's lifetime is the generator's. A factory called at registration
    instead — the obvious place, and wrong — would make the second run of a
    tuning session differ from the first with nothing in the project changed.
    """
    plan = plan_over(SourceSpan(start=95, end=97))

    first = [result["bg"].data.copy() for result in execute(plan, RampSource())]
    second = [result["bg"].data.copy() for result in execute(plan, RampSource())]

    for before, after in zip(first, second, strict=True):
        assert np.array_equal(before, after)


def test_binding_mints_a_state_per_run_and_leaves_a_stateless_tool_alone() -> None:
    """The half of the claim `_bind` owns, without a loop in the way.

    Two bindings of one node must not share a state, and a stateless tool's
    binding must carry the very function that was registered and nothing to keep
    — a wrapper there would cost every tool an indirection and would break an
    equivalence test that names a `run` directly.
    """
    stateful = plan_over(SourceSpan(start=95, end=97))
    stateless = plan_over(SourceSpan(start=95, end=97), "plain", "p")

    one = _bind(stateful)["bg"]
    two = _bind(stateful)["bg"]
    bare = _bind(stateless)["p"]

    assert one.state is not two.state
    assert bare.state is None
    assert bare.run is plain_run

    params = BackgroundParams(alpha=0.5)
    bright = FrameSpan(
        (Frame(data=np.full((HEIGHT, WIDTH), 200, np.uint8), index=0, channels=ChannelSpec.GRAY),)
    )
    dark = FrameSpan(
        (Frame(data=np.zeros((HEIGHT, WIDTH), np.uint8), index=1, channels=ChannelSpec.GRAY),)
    )
    one.run(params, bright, one.state)  # seeds `one`'s model at 200 and not `two`'s

    assert one.run(params, dark, one.state).data.mean() > 0  # 100 away from a model at 200
    assert not two.run(params, dark, two.state).data.any()  # seeded by this very frame
