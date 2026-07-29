








from __future__ import annotations

import numpy as np
import pytest

from sieve.backend.dispatch import Backend, KernelRegistry, kernel
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase, TableSpec
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.cache_key import source_key
from sieve.pipeline.dag import Dag, graph_needs_chroma
from sieve.pipeline.executor import FormatMismatchError, execute
from sieve.pipeline.plan import ExecutionPlan

COST = CostEstimate(seconds_per_megapixel=0.001, peak_bytes_per_input_byte=2.0)

SHELF = FilterRegistry()


@register_filter(
    filter_id="agnostic",
    version="1.0.0",
    summary="Says nothing about channels, so it accepts any.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class AgnosticParams(ParamsBase):
    pass


@register_filter(
    filter_id="gray_only",
    version="1.0.0",
    summary="Single channel in, single channel out — the extraction shape.",
    accepts=ArraySpec(channels=(ChannelSpec.GRAY,)),
    emits=ArraySpec(channels=(ChannelSpec.GRAY,)),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class GrayOnlyParams(ParamsBase):
    pass


@register_filter(
    filter_id="hue",
    version="1.0.0",
    summary="Colour only. The filter that does not yet exist.",
    accepts=ArraySpec(channels=(ChannelSpec.BGR,)),
    emits=ArraySpec(channels=(ChannelSpec.GRAY,)),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class HueParams(ParamsBase):
    pass


@register_filter(
    filter_id="either",
    version="1.0.0",
    summary="Names colour but tolerates gray, so it demands nothing.",
    accepts=ArraySpec(channels=(ChannelSpec.BGR, ChannelSpec.GRAY)),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class EitherParams(ParamsBase):
    pass


@register_filter(
    filter_id="rows",
    version="1.0.0",
    summary="Consumes rows, so it reads no pixels at all.",
    accepts=TableSpec(columns=("x",)),
    emits=TableSpec(columns=("x",)),
    cost=COST,
    registry=SHELF,
)
class RowsParams(ParamsBase):
    pass


def graph(*filter_ids: str) -> Pipeline:

    nodes = tuple(
        Node(node_id=f"n{i}", filter_id=filter_id, version="1.0.0", params={})
        for i, filter_id in enumerate(filter_ids)
    )
    edges = tuple(
        Edge(upstream=f"n{i}", downstream=f"n{i + 1}") for i in range(len(filter_ids) - 1)
    )
    return Pipeline(nodes=nodes, edges=edges)


class TestNeedsChroma:
    def test_a_chain_that_never_mentions_colour_takes_the_luma_path(self) -> None:







        dag = Dag.build(graph("agnostic", "agnostic", "gray_only"), SHELF)
        assert dag.needs_chroma is False

    def test_one_colour_only_node_anywhere_forces_colour(self) -> None:
        dag = Dag.build(graph("agnostic", "hue", "gray_only"), SHELF)
        assert dag.needs_chroma is True

    def test_naming_colour_beside_gray_is_not_a_demand_for_it(self) -> None:






        assert Dag.build(graph("either", "gray_only"), SHELF).needs_chroma is False

    def test_a_table_input_reads_no_pixels_and_so_demands_none(self) -> None:






        assert Dag.build(graph("rows"), SHELF).needs_chroma is False

    def test_an_unresolvable_graph_falls_back_to_colour(self) -> None:






        assert graph_needs_chroma(graph("no_such_filter"), SHELF) is True


class TestSourceKey:
    def test_the_format_changes_the_key(self) -> None:






        assert source_key("footage", luma=True) != source_key("footage", luma=False)

    def test_colour_is_what_a_caller_gets_without_asking(self) -> None:




        assert source_key("footage") == source_key("footage", luma=False)





SHELF_KERNELS = KernelRegistry()


@kernel(GrayOnlyParams, Backend.CPU, registry=SHELF_KERNELS)
def gray_only_cpu(frame: Frame, params: GrayOnlyParams) -> Frame:
    return frame


@kernel(HueParams, Backend.CPU, registry=SHELF_KERNELS)
def hue_cpu(frame: Frame, params: HueParams) -> Frame:
    return frame


class TestTheExecutorRefusesADisagreement:









    def _plan(self, *, luma: bool) -> ExecutionPlan:

        return ExecutionPlan.build(
            Dag.build(graph("gray_only" if luma else "hue"), SHELF),
            source="footage",
            span=ClipRange(start=0, end=1),
            backend=Backend.CPU,
        )

    def test_a_colour_reader_under_a_luma_plan_is_refused(self) -> None:
        plan = self._plan(luma=True)
        assert plan.luma is True
        with pytest.raises(FormatMismatchError, match="keyed for luma"):
            list(execute(plan, _OneFrame(ChannelSpec.BGR), kernels=SHELF_KERNELS))

    def test_a_luma_reader_under_a_colour_plan_is_refused(self) -> None:






        plan = self._plan(luma=False)
        assert plan.luma is False
        with pytest.raises(FormatMismatchError, match="keyed for colour"):
            list(execute(plan, _OneFrame(ChannelSpec.GRAY), kernels=SHELF_KERNELS))


class _OneFrame:


    def __init__(self, channels: ChannelSpec) -> None:
        self._channels = channels

    def read(self, index: int) -> Frame:
        shape = (4, 4) if self._channels is ChannelSpec.GRAY else (4, 4, 3)
        return Frame(data=np.zeros(shape, dtype=np.uint8), index=index, channels=self._channels)
