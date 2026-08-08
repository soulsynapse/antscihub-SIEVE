"""The handshake: the graph picks a decode format, and the run refuses any other.

Three modules answer one question here. `dag.py` derives the format from what
the tools accept, `cache_key.py` hashes it at the ancestor of every root, and
`executor.py` refuses a frame that disagrees with it. Each of those derivations
is pinned where it lives — `test_dag.py` for which graphs demand chroma,
`test_cache_key.py` for the format separating two keys, `test_plan.py` for
`luma` being the graph's answer rather than a caller's. What none of them can
say is that the three agree, and that a disagreement between any two of them is
loud rather than a cache full of frames labelled as something they are not.

So the claims below are joints, not behaviours: the format the reader is to be
opened in is the format the root key was built from, and a reader handing the
other one is refused before a tool is called. The second is the reason this file
exists — a silent conversion completes, produces correctly-shaped frames, and
looks plausible in a preview, which is the wrong-but-green result nothing
downstream detects.

A one-frame fake source rather than `synthetic_video`, and that is the point of
the test rather than a shortcut: the contract is about two derivations
disagreeing, and a real decode cannot be made to disagree with itself on demand.
"""

from __future__ import annotations

import numpy as np
import pytest

from sieve.core.pipeline_model import CropFormat, Edge, Node, Pipeline, SourceSpan
from sieve.core.tool_base import ArraySpec, ElementRelation, Emission, ParamsBase
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import ChannelSpec, Frame, FrameSpan
from sieve.pipeline.cache_key import node_key, source_key
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FormatMismatchError, execute
from sieve.pipeline.plan import ExecutionPlan

#: What `cache_key.source_identity` would have produced. A string, so no footage
#: has to exist for a key to be derivable.
SOURCE = "arena.mp4|4096|17"

SPAN = SourceSpan(start=0, end=1)

#: A scratch shelf, not `REGISTRY`: the process-wide one is populated by tool
#: modules at import, and registering into it would make this file's behaviour
#: depend on whether such an import had already happened.
SHELF = ToolRegistry()

#: Every frame index a tool was called for. The refusal cases assert this stayed
#: empty, which is the difference between refusing a mismatched frame and
#: converting it — a conversion also raises nothing and also yields nothing this
#: file looks at.
CALLS: list[int] = []


def _passthrough(params: ParamsBase, window: FrameSpan, state: None) -> Frame:
    del params, state
    CALLS.append(int(window.target.index))
    return window.target


@register_tool(
    tool_id="agnostic",
    version="1.0.0",
    summary="Says nothing about channels, so it accepts any and demands none.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_passthrough,
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class AgnosticParams(ParamsBase):
    pass


@register_tool(
    tool_id="hue_band",
    version="1.0.0",
    summary="Names the packed layouts and omits GRAY, so it demands colour.",
    accepts=ArraySpec(channels=(ChannelSpec.RGB, ChannelSpec.BGR)),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_passthrough,
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class HueBandParams(ParamsBase):
    pass


def chain(*tool_ids: str) -> Pipeline:
    """One node per id, wired head to tail. `n0` is the root every case reads."""
    nodes = tuple(
        Node(node_id=f"n{index}", tool_id=tool_id, version="1.0.0", params={})
        for index, tool_id in enumerate(tool_ids)
    )
    return Pipeline(
        nodes=nodes,
        edges=tuple(
            Edge(upstream=f"n{index}", downstream=f"n{index + 1}")
            for index in range(len(tool_ids) - 1)
        ),
    )


def plan_for(*tool_ids: str) -> ExecutionPlan:
    return ExecutionPlan.build(Dag.build(chain(*tool_ids), SHELF), source=SOURCE, span=SPAN)


@pytest.fixture(autouse=True)
def forget_calls() -> None:
    CALLS.clear()


class OneFrame:
    """A source handing back one frame in a declared format, however it is asked.

    Not `ListSource`: what these cases need is a reader whose format is chosen
    against the plan's, which is precisely the thing no real reader will do.
    """

    def __init__(self, channels: ChannelSpec) -> None:
        self._channels = channels

    def read(self, index: int) -> Frame:
        shape = (4, 4) if self._channels is ChannelSpec.GRAY else (4, 4, 3)
        return Frame(data=np.zeros(shape, dtype=np.uint8), index=index, channels=self._channels)


class TestTheGraphsAnswerIsTheKeysAnswer:
    """The format reaching the reader and the format in the key are one value.

    `test_dag.py` shows two graphs keyed apart by their formats; that is the
    separation. This is the equality behind it — the root's upstream hash is the
    source key for the very format `plan.luma` will have the reader opened in.
    A derivation that moved one of the two would still separate the two graphs
    and would serve every entry it wrote to the wrong reader.
    """

    def _root_key_for(self, plan: ExecutionPlan, decode_format: CropFormat) -> str:
        return node_key(
            plan.dag.pipeline.node("n0"),
            spec=plan.dag.spec("n0"),
            upstream=source_key(SOURCE, decode_format=decode_format),
        )

    def test_a_chain_that_never_reads_colour_is_keyed_for_the_plane_it_opens(self) -> None:
        plan = plan_for("agnostic", "agnostic")

        assert plan.luma is True
        assert plan.keys["n0"] == self._root_key_for(plan, "luma")

    def test_one_colour_node_moves_the_reader_and_the_key_together(self) -> None:
        # The demand is downstream of the root, so the root's own tool and
        # parameters are unchanged between the two cases and its key can only
        # move through the source key — which is the position under test.
        plan = plan_for("agnostic", "hue_band")

        assert plan.luma is False
        assert plan.keys["n0"] == self._root_key_for(plan, "bgr")


class TestTheExecutorRefusesADisagreement:
    """What happens when a reader and a plan hold different answers.

    The class above pins that the format reaches the key. What it cannot say is
    that a run whose reader was opened in the other format stops: the frames
    would be the right shape, every node would compute, and the store would fill
    with entries labelled as something they are not. Both directions are written
    out rather than parametrized — one comparison catches them today, and an
    implementation that only checked the expensive direction would leave the
    other silent.
    """

    def test_a_colour_reader_under_a_luma_plan_is_refused(self) -> None:
        plan = plan_for("agnostic")
        assert plan.luma is True

        with pytest.raises(FormatMismatchError, match="keyed for luma"):
            list(execute(plan, OneFrame(ChannelSpec.BGR)))

        assert CALLS == []

    def test_a_luma_reader_under_a_colour_plan_is_refused(self) -> None:
        plan = plan_for("hue_band")
        assert plan.luma is False

        with pytest.raises(FormatMismatchError, match="keyed for colour"):
            list(execute(plan, OneFrame(ChannelSpec.GRAY)))

        assert CALLS == []

    def test_the_reader_the_plan_asked_for_is_run_rather_than_refused(self) -> None:
        # The other side of the check, and the one that makes the two refusals
        # above evidence of anything: a guard comparing the wrong way round, or
        # one refusing every frame, passes both of them.
        plan = plan_for("hue_band")

        results = list(execute(plan, OneFrame(ChannelSpec.BGR)))

        assert CALLS == [0]
        assert [result.index for result in results] == [0]
