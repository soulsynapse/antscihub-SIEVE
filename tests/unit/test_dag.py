









from __future__ import annotations

from fractions import Fraction

import pytest

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementKind,
    ElementRelation,
    ParamsBase,
    TableSpec,
)
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.pipeline.cache_key import node_key, source_key
from sieve.pipeline.dag import (
    CycleError,
    Dag,
    EdgeTypeError,
    PortWiringError,
    UnresolvedFilterError,
)

COST = CostEstimate(seconds_per_megapixel=0.001)
SOURCE = "footage|1|2"
ARENA = ROI(x=0, y=0, width=64, height=64)




SHELF = FilterRegistry()


@register_filter(
    filter_id="blur",
    version="1.0.0",
    summary="Frames in, frames out.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class BlurParams(ParamsBase):
    radius: int = 3


@register_filter(
    filter_id="detect",
    version="1.0.0",
    summary="Frames in, rows out.",
    accepts=ArraySpec(),
    emits=TableSpec(columns=("x", "y")),
    cost=COST,
    registry=SHELF,
)
class DetectParams(ParamsBase):
    pass


@register_filter(
    filter_id="minus",
    version="1.0.0",
    summary="Left minus right, so which port is which matters.",
    accepts={"left": ArraySpec(), "right": ArraySpec()},
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class MinusParams(ParamsBase):
    pass


@register_filter(
    filter_id="jitter",
    version="1.0.0",
    summary="Frames in, frames out, never the same ones twice.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    deterministic=False,
    registry=SHELF,
)
class JitterParams(ParamsBase):
    pass


@register_filter(
    filter_id="gridify",
    version="1.0.0",
    summary="Redefines the element: pixels in, blocks out.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementKind.BLOCK,
    cost=COST,
    registry=SHELF,
)
class GridifyParams(ParamsBase):
    pass


@register_filter(
    filter_id="shrink",
    version="1.0.0",
    summary="Many elements in, one out — `downsample`'s relation.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.AGGREGATED,
    cost=COST,
    registry=SHELF,
)
class ShrinkParams(ParamsBase):
    pass


@register_filter(
    filter_id="decimate",
    version="1.0.0",
    summary="Keeps one frame in ten, so a row stops being a source frame.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    rate_changing=True,
    registry=SHELF,
)
class DecimateParams(ParamsBase):
    def output_rate(self) -> Fraction:
        return Fraction(1, 10)


def node(node_id: str, filter_id: str = "blur", version: str = "1.0.0", **params: object) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version=version, params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:

    built: list[Edge] = []
    for pair in pairs:
        upstream, target = pair.split(">")
        downstream, _, port = target.partition(":")
        built.append(
            Edge(upstream=upstream, downstream=downstream, port=port)
            if port
            else Edge(upstream=upstream, downstream=downstream)
        )
    return tuple(built)


def diamond(**overrides: str) -> Pipeline:









    return Pipeline(
        nodes=tuple(
            node(node_id, overrides.get(node_id, default))
            for node_id, default in (("a", "blur"), ("b", "blur"), ("c", "blur"), ("d", "minus"))
        ),
        edges=edges("a>b", "a>c", "b>d:left", "c>d:right"),
    )


class TestRejections:
    def test_a_cycle_names_every_node_that_could_not_be_ordered(self) -> None:




        cyclic = Pipeline(
            nodes=tuple(node(node_id) for node_id in ("a", "b", "c", "d")),
            edges=edges("a>b", "b>c", "c>a", "c>d"),
        )

        with pytest.raises(CycleError) as raised:
            Dag.build(cyclic, SHELF)



        assert raised.value.nodes == ("a", "b", "c", "d")

    def test_a_missing_filter_is_named_by_id_and_version_all_at_once(self) -> None:





        unresolvable = Pipeline(
            nodes=(
                node("a", "wavelet_bands", "2.1.0"),
                node("b", "wavelet_bands", "2.1.0"),
                node("c", "blur", "9.0.0"),
            ),
            edges=edges("a>b", "b>c"),
        )

        with pytest.raises(UnresolvedFilterError) as raised:
            Dag.build(unresolvable, SHELF)

        assert raised.value.missing == (("wavelet_bands", "2.1.0"), ("blur", "9.0.0"))
        assert "wavelet_bands 2.1.0" in str(raised.value)
        assert "blur 9.0.0" in str(raised.value)

    def test_rows_may_not_feed_an_input_that_wants_frames(self) -> None:





        with pytest.raises(EdgeTypeError) as raised:
            Dag.build(diamond(b="detect"), SHELF)

        assert (raised.value.upstream, raised.value.downstream) == ("b", "d")
        assert raised.value.port == "left"

    def test_an_edge_into_a_port_the_filter_does_not_declare_is_refused(self) -> None:


        graph = Pipeline(
            nodes=(node("a"), node("b"), node("d", "minus")),
            edges=edges("a>d:left", "b>d:rigth"),
        )

        with pytest.raises(PortWiringError, match="rigth"):
            Dag.build(graph, SHELF)

    def test_a_declared_port_left_unfilled_is_refused(self) -> None:


        graph = Pipeline(
            nodes=(node("a"), node("d", "minus")),
            edges=edges("a>d:left"),
        )

        with pytest.raises(PortWiringError, match=r"\['right'\] unfilled"):
            Dag.build(graph, SHELF)

    def test_a_merging_filter_cannot_sit_at_a_root(self) -> None:


        graph = Pipeline(nodes=(node("d", "minus"),))

        with pytest.raises(PortWiringError, match="cannot be a root"):
            Dag.build(graph, SHELF)


class TestOrder:
    def test_the_order_follows_the_document_and_not_when_a_node_was_freed(self) -> None:





        pipeline = Pipeline(
            nodes=(node("first"), node("late"), node("second")),
            edges=edges("first>late"),
        )

        assert tuple(each.node_id for each in Dag.build(pipeline, SHELF).order) == (
            "first",
            "late",
            "second",
        )

    def test_every_node_comes_after_its_upstreams(self) -> None:
        dag = Dag.build(diamond(), SHELF)
        position = {each.node_id: index for index, each in enumerate(dag.order)}

        for each in dag.order:
            for upstream in dag.upstreams[each.node_id]:
                assert position[upstream] < position[each.node_id]
        assert tuple(each.node_id for each in dag.roots) == ("a",)
        assert tuple(each.node_id for each in dag.leaves) == ("d",)


class TestKeyWalk:
    def test_the_walk_is_the_hand_walk(self) -> None:






        dag = Dag.build(diamond(), SHELF)
        arena = Replicate(roi=ARENA, name="Replicate 1")

        keys = dag.node_keys(source=SOURCE, backend=Backend.CPU, replicate=arena)

        def by_hand(node_id: str, upstream: dict[str, str]) -> str:
            return node_key(
                dag.pipeline.node(node_id),
                spec=dag.spec(node_id),
                upstream=upstream,
                backend=Backend.CPU,
                replicate=arena,
            )





        root = source_key(SOURCE, ARENA, luma=not dag.needs_chroma)
        expected = {"a": by_hand("a", {"in": root})}
        expected["b"] = by_hand("b", {"in": expected["a"]})
        expected["c"] = by_hand("c", {"in": expected["a"]})
        expected["d"] = by_hand("d", {"left": expected["b"], "right": expected["c"]})
        assert keys == expected

    def test_swapping_a_merges_ports_moves_its_key_and_only_its_key(self) -> None:












        nodes = (node("a"), node("b", radius=5), node("c", radius=7), node("d", "minus"))
        forward_graph = Pipeline(nodes=nodes, edges=edges("a>b", "a>c", "b>d:left", "c>d:right"))
        swapped_graph = Pipeline(nodes=nodes, edges=edges("a>b", "a>c", "b>d:right", "c>d:left"))
        forward = Dag.build(forward_graph, SHELF).node_keys(source=SOURCE, backend=Backend.CPU)
        swapped = Dag.build(swapped_graph, SHELF).node_keys(source=SOURCE, backend=Backend.CPU)

        assert swapped["d"] != forward["d"]
        assert {k: v for k, v in swapped.items() if k != "d"} == {
            k: v for k, v in forward.items() if k != "d"
        }

    def test_an_uncacheable_node_takes_its_descendants_and_nobody_else(self) -> None:






        keys = Dag.build(diamond(b="jitter"), SHELF).node_keys(source=SOURCE, backend=Backend.CPU)

        assert set(keys) == {"a", "c"}


class TestElementMeaning:








    def test_the_source_is_pixels_and_a_preserving_root_says_so(self) -> None:




        graph = Pipeline(nodes=(node("a"),))

        assert Dag.build(graph, SHELF).elements == {"a": ElementKind.PIXEL}

    def test_meaning_carries_through_every_preserving_node_after_a_redefinition(self) -> None:





        graph = Pipeline(
            nodes=(node("a"), node("b", "gridify"), node("c"), node("d")),
            edges=edges("a>b", "b>c", "c>d"),
        )

        assert Dag.build(graph, SHELF).elements == {
            "a": ElementKind.PIXEL,
            "b": ElementKind.BLOCK,
            "c": ElementKind.BLOCK,
            "d": ElementKind.BLOCK,
        }

    def test_aggregating_blocks_loses_the_meaning_and_it_never_returns(self) -> None:




        graph = Pipeline(
            nodes=(node("a", "shrink"), node("b", "gridify"), node("c", "shrink"), node("d")),
            edges=edges("a>b", "b>c", "c>d"),
        )

        assert Dag.build(graph, SHELF).elements == {
            "a": ElementKind.PIXEL,
            "b": ElementKind.BLOCK,
            "c": None,
            "d": None,
        }

    def test_a_merge_of_two_meanings_resolves_to_neither(self) -> None:



        graph = Pipeline(
            nodes=(node("a"), node("b", "gridify"), node("c"), node("d", "minus")),
            edges=edges("a>b", "a>c", "b>d:left", "c>d:right"),
        )

        assert Dag.build(graph, SHELF).elements["d"] is None

    def test_a_table_emitter_has_no_element_at_all(self) -> None:
        graph = Pipeline(nodes=(node("a"), node("b", "detect")), edges=edges("a>b"))

        assert Dag.build(graph, SHELF).elements["b"] is None


class TestSourceIndexing:
    def test_a_rate_change_unindexes_itself_and_everything_after_it(self) -> None:



        graph = Pipeline(
            nodes=(node("a"), node("b", "decimate"), node("c")),
            edges=edges("a>b", "b>c"),
        )

        assert Dag.build(graph, SHELF).source_indexed == {"a": True, "b": False, "c": False}

    def test_a_graph_with_no_rate_change_is_indexed_throughout(self) -> None:
        assert all(Dag.build(diamond(), SHELF).source_indexed.values())


class TestWhereMeaningWasLost:
    def test_it_names_the_node_that_lost_it_not_the_one_that_asked(self) -> None:





        graph = Pipeline(
            nodes=(node("a"), node("b", "gridify"), node("c", "shrink"), node("d")),
            edges=edges("a>b", "b>c", "c>d"),
        )

        assert Dag.build(graph, SHELF).element_lost_at("d") == "c"

    def test_the_earliest_loss_wins_when_a_chain_loses_it_twice(self) -> None:


        graph = Pipeline(
            nodes=(
                node("a"),
                node("b", "gridify"),
                node("c", "shrink"),
                node("d", "shrink"),
            ),
            edges=edges("a>b", "b>c", "c>d"),
        )

        assert Dag.build(graph, SHELF).element_lost_at("d") == "c"

    def test_a_sibling_that_kept_its_meaning_is_not_blamed(self) -> None:




        graph = Pipeline(
            nodes=(
                node("a"),
                node("b", "gridify"),
                node("lost", "shrink"),
                node("d", "minus"),
            ),
            edges=edges("a>b", "b>lost", "b>d:left", "lost>d:right"),
        )

        assert Dag.build(graph, SHELF).element_lost_at("d") == "lost"

    def test_asking_about_a_node_that_has_a_meaning_is_refused(self) -> None:



        with pytest.raises(ValueError, match="so nothing was lost"):
            Dag.build(diamond(), SHELF).element_lost_at("d")
