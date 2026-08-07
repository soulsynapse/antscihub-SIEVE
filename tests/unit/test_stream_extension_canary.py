"""A third stream-family canary for the filter contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol, cast

import pytest

from sieve.backend.dispatch import unrunnable_reason
from sieve.cli import inspect_cmd
from sieve.core.filter_base import (
    DEFAULT_PORT,
    ArraySpec,
    AuthoringGroup,
    CostEstimate,
    ElementKind,
    ElementNames,
    FilterSpec,
    ParamsBase,
    StreamSpec,
)
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.core.types import WorkUnits
from sieve.gui.wizard_model import catalog, chain_from_pipeline
from sieve.pipeline.dag import Dag, EdgeTypeError

COST = CostEstimate(work_per_megapixel=WorkUnits(1.0))
MASK = "ant"
OTHER_MASK = "larva"


@dataclass(frozen=True, slots=True)
class MaskSpec:
    """Test-only stream family that is neither `ArraySpec` nor `TableSpec`."""

    kind: ClassVar[str] = "mask"
    labels: tuple[str, ...] = ()

    def admits(self, produced: object) -> bool:
        if not isinstance(produced, MaskSpec):
            return False
        if not self.labels or not produced.labels:
            return True
        return bool(set(self.labels) & set(produced.labels))


class DescribeFilter(Protocol):
    def __call__(self, spec: FilterSpec, *, guidance: bool) -> str: ...


def _stream(spec: MaskSpec) -> StreamSpec:
    return cast("StreamSpec", spec)


def _inspect_text(spec: FilterSpec) -> str:
    describe = cast(DescribeFilter, inspect_cmd._describe)  # pyright: ignore[reportPrivateUsage]
    return describe(spec, guidance=False)


def _node(node_id: str, filter_id: str) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version="1.0.0", params={})


def _registry_with_mask_family() -> FilterRegistry:
    registry = FilterRegistry()

    @register_filter(
        filter_id="mask_source",
        version="1.0.0",
        summary="Produces a test-only mask stream.",
        accepts=ArraySpec(),
        emits=_stream(MaskSpec(labels=(MASK,))),
        cost=COST,
        authoring_group=AuthoringGroup.SIGNAL_EXTRACTION,
        registry=registry,
    )
    class MaskSourceParams(ParamsBase):
        pass

    @register_filter(
        filter_id="mask_refine",
        version="1.0.0",
        summary="Consumes and produces the test-only mask stream.",
        accepts=_stream(MaskSpec(labels=(MASK,))),
        emits=_stream(MaskSpec(labels=(MASK,))),
        cost=COST,
        authoring_group=AuthoringGroup.TEMPORAL_FILTER,
        registry=registry,
    )
    class MaskRefineParams(ParamsBase):
        pass

    @register_filter(
        filter_id="mask_to_frame",
        version="1.0.0",
        summary="Turns a test-only mask stream back into image frames.",
        accepts=_stream(MaskSpec(labels=(MASK,))),
        emits=ArraySpec(),
        element=ElementKind.PIXEL,
        element_names=ElementNames("pixel", "pixels"),
        cost=COST,
        authoring_group=AuthoringGroup.SPATIAL_PREP,
        registry=registry,
    )
    class MaskToFrameParams(ParamsBase):
        pass

    @register_filter(
        filter_id="wrong_mask_reader",
        version="1.0.0",
        summary="Consumes a different mask label.",
        accepts=_stream(MaskSpec(labels=(OTHER_MASK,))),
        emits=ArraySpec(),
        element=ElementKind.PIXEL,
        element_names=ElementNames("pixel", "pixels"),
        cost=COST,
        authoring_group=AuthoringGroup.SPATIAL_PREP,
        registry=registry,
    )
    class WrongMaskReaderParams(ParamsBase):
        pass

    assert MaskSourceParams.spec().filter_id == "mask_source"
    assert MaskRefineParams.spec().filter_id == "mask_refine"
    assert MaskToFrameParams.spec().filter_id == "mask_to_frame"
    assert WrongMaskReaderParams.spec().filter_id == "wrong_mask_reader"
    return registry


def test_a_third_stream_family_registers_and_checks_edges_through_admits() -> None:
    registry = _registry_with_mask_family()
    graph = Pipeline(
        nodes=(_node("source", "mask_source"), _node("overlay", "mask_to_frame")),
        edges=(Edge(upstream="source", downstream="overlay"),),
    )

    dag = Dag.build(graph, registry)

    assert dag.spec("source").emits == MaskSpec(labels=(MASK,))
    assert dag.elements == {"source": None, "overlay": ElementKind.PIXEL}

    wrong_label = Pipeline(
        nodes=(_node("source", "mask_source"), _node("wrong", "wrong_mask_reader")),
        edges=(Edge(upstream="source", downstream="wrong"),),
    )
    with pytest.raises(EdgeTypeError) as raised:
        Dag.build(wrong_label, registry)
    assert raised.value.upstream == "source"
    assert raised.value.downstream == "wrong"


def test_attachable_operations_reads_the_third_family_through_the_same_query() -> None:
    registry = _registry_with_mask_family()

    offers = Dag.attachable_operations(_stream(MaskSpec(labels=(MASK,))), registry=registry)
    named = {(offer.spec.filter_id, offer.port) for offer in offers}

    assert ("mask_refine", DEFAULT_PORT) in named
    assert ("mask_to_frame", DEFAULT_PORT) in named
    assert ("wrong_mask_reader", DEFAULT_PORT) not in named

    to_frame = Dag.attachable_operations(
        _stream(MaskSpec(labels=(MASK,))),
        downstream_port=ArraySpec(),
        registry=registry,
    )
    assert [offer.spec.filter_id for offer in to_frame] == ["mask_to_frame"]


def test_dispatch_refuses_the_third_family_by_the_declared_field() -> None:
    registry = _registry_with_mask_family()

    accepts_reason = unrunnable_reason(registry.latest("mask_to_frame"))
    emits_reason = unrunnable_reason(registry.latest("mask_source"))

    assert accepts_reason is not None
    assert "accepts mask on port 'in'" in accepts_reason
    assert emits_reason is not None
    assert "emits mask" in emits_reason


def test_current_stack_refuses_the_third_family_by_the_declared_field() -> None:
    registry = _registry_with_mask_family()
    entries = {entry.entry_id for entry in catalog(registry=registry)}

    assert "mask_source" not in entries
    assert "mask_to_frame" not in entries

    with pytest.raises(ValueError, match="emits=mask"):
        chain_from_pipeline(
            Pipeline(nodes=(_node("source", "mask_source"),)),
            30.0,
            registry=registry,
        )
    with pytest.raises(ValueError, match="accepts=mask"):
        chain_from_pipeline(
            Pipeline(nodes=(_node("overlay", "mask_to_frame"),)),
            30.0,
            registry=registry,
        )


def test_inspect_describes_the_third_family_without_a_catalog_case() -> None:
    registry = _registry_with_mask_family()

    text = _inspect_text(registry.latest("mask_source"))

    assert "accepts           ArraySpec" in text
    assert "emits             MaskSpec(labels=('ant',))" in text
