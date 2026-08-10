"""What a position produces, resolved along the walk rather than read off a tool.

`crop` emits an `ArraySpec` stating neither field because it emits what it was
handed, so the declaration alone proves nothing and the offer under it was empty
(`findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md`).
The cases here are the two that fold exists for — the offer under a source
resolved to one video, and the offer under a `crop` reading that source — and
they are asserted over the real shelf rather than a scratch one, because the
claim is about what the tools this install ships actually declare.

The element meaning is passed in rather than folded: `element_kinds` is the
other half of the same walk and lives beside the widget that reads it, so
importing it here would pull Qt into a test whose subject is a stream.
"""

from __future__ import annotations

from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.core.tool_base import ArraySpec, ElementKind, ToolSpec
from sieve.core.tool_registry import ToolRegistry, offered_tools
from sieve.gui.streams import stream_specs
from sieve.gui.walk import node_order
from sieve.pipeline.shelf import loaded_shelf


def _shelf(registry: ToolRegistry) -> tuple[ToolSpec, ...]:
    """One version of each tool, which is the shelf a position is offered from."""
    return tuple(registry.latest(tool_id) for tool_id in registry.ids())


def _chain(*tools: str) -> Pipeline:
    return Pipeline(
        nodes=tuple(
            Node(node_id=f"n{i}", tool_id=tool, version="1.0.0") for i, tool in enumerate(tools)
        ),
        edges=tuple(Edge(upstream=f"n{i}", downstream=f"n{i + 1}") for i in range(len(tools) - 1)),
    )


def _resolved(pipeline: Pipeline, registry: ToolRegistry) -> dict[str, object]:
    specs = {node.node_id: registry.get(node.tool_id, node.version) for node in pipeline.nodes}
    return dict(stream_specs(node_order(pipeline), pipeline, specs))


def test_offering_from_a_resolved_source_carries_the_source_through_the_preserving_tool() -> None:
    registry = loaded_shelf()
    pipeline = _chain("footage", "crop")
    footage = registry.latest("footage")

    resolved = _resolved(pipeline, registry)

    # The root's seed is the source as the document names it, not a decode
    # format the graph would settle: `footage` states what it emits and the
    # walk starts there.
    assert resolved["n0"] == footage.emits
    # And `crop` declares neither field because it emits what it was handed,
    # which is the claim the fold reads rather than a second one it adds.
    assert resolved["n1"] == footage.emits


def test_offering_from_a_resolved_source_is_what_takes_a_single_video() -> None:
    registry = loaded_shelf()
    pipeline = _chain("footage", "crop")
    resolved = _resolved(pipeline, registry)
    shelf = _shelf(registry)

    under_source = offered_tools(resolved["n0"], ElementKind.PIXEL, shelf)
    under_crop = offered_tools(resolved["n1"], ElementKind.PIXEL, shelf)

    # VISION offers "crop, downsample, and the rest of what takes a single
    # video", so the target is most of the shelf and not the two-entry
    # shortlist an unresolved position produced.
    named = [spec.tool_id for spec in under_source]
    assert "crop" in named
    assert "downsample" in named
    assert len(named) > len(shelf) // 2
    # The gap under the crop is the same position asked again — crop changes
    # neither dtype nor layout, so nothing about the offer may move.
    assert [spec.tool_id for spec in under_crop] == named


def test_offering_from_a_resolved_source_still_refuses_what_the_dtype_rules_out() -> None:
    registry = loaded_shelf()
    resolved = _resolved(_chain("footage", "crop"), registry)

    named = [
        spec.tool_id for spec in offered_tools(resolved["n1"], ElementKind.PIXEL, _shelf(registry))
    ]

    # Resolution is not permission: `detect` takes float32 and the source is
    # uint8 all the way down to the first conversion.
    assert "detect" not in named
    assert "motion_history" not in named


def test_offering_from_a_resolved_source_offers_no_tool_that_reads_a_file() -> None:
    registry = loaded_shelf()
    resolved = _resolved(_chain("footage", "crop"), registry)

    offered = offered_tools(resolved["n1"], ElementKind.PIXEL, _shelf(registry))

    # A source root has no input, so "what could go after this" can never be
    # one however completely the position is resolved — the wildcard `accepts`
    # a source carries is a statement about a position that does not exist
    # (`tools/pick.py`).
    assert [spec.tool_id for spec in offered if spec.source is not None] == []


def test_offering_from_a_resolved_source_is_empty_where_the_root_declares_nothing() -> None:
    registry = loaded_shelf()
    # `checkpoint` states neither field and has nothing upstream to preserve
    # from, so a chain rooted on one resolves to nothing and offers nothing —
    # which is ADR 32's "a claim while it has an upstream and nothing at all
    # without one" measured.
    resolved = _resolved(_chain("checkpoint", "crop"), registry)

    assert resolved["n1"] == ArraySpec()
    assert offered_tools(resolved["n1"], ElementKind.PIXEL, _shelf(registry)) == ()
