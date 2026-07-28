"""What a graph has to be rejected for, and what the one walk has to agree with.

Three of these are rejections the artifact layer deliberately cannot make —
`Pipeline` validates structure and stops, so a cycle, a filter that is not
installed, and an edge whose ends cannot be connected all reach this module
unchallenged. The other three are about the traversal: that its order is the
document's rather than a dict's, that it produces the same keys a hand-walk
does, and that a node with no key takes its descendants with it and nobody else.
"""

from __future__ import annotations

import pytest

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ArraySpec, CostEstimate, ParamsBase, TableSpec
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

#: A scratch shelf, not `REGISTRY`. The process-wide one is populated by
#: `sieve.filters.discover()` and a test that registered into it would make the
#: suite's behaviour depend on whether a discovery had already run.
SHELF = FilterRegistry()


@register_filter(
    filter_id="blur",
    version="1.0.0",
    summary="Frames in, frames out.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
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
    cost=COST,
    deterministic=False,
    registry=SHELF,
)
class JitterParams(ParamsBase):
    pass


def node(node_id: str, filter_id: str = "blur", version: str = "1.0.0", **params: object) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version=version, params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:
    """`"a>b"` for each edge, or `"a>b:left"` to name the port it feeds."""
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
    """a ─┬─> b ─┬─> d, the smallest graph with a node that has two upstreams.
           └─> c ─┘

    `d` is a `minus`, taking `b` on `left` and `c` on `right` — a two-upstream
    node has to declare two ports now, and making the merge non-commutative is
    what lets the key tests below say the ports are load-bearing. `overrides`
    swaps one node's filter id, which is how the type-mismatch and
    non-determinism tests differ from the baseline by exactly one thing.
    """
    return Pipeline(
        nodes=tuple(
            node(node_id, overrides.get(node_id, default))
            for node_id, default in (("a", "blur"), ("b", "blur"), ("c", "blur"), ("d", "minus"))
        ),
        edges=edges("a>b", "a>c", "b>d:left", "c>d:right"),
    )


class TestRejections:
    def test_a_cycle_names_every_node_that_could_not_be_ordered(self) -> None:
        # `Pipeline` accepts this: the ids are unique, both endpoints of every
        # edge exist, and no edge is a self-loop. Nothing below this module
        # would notice before an executor walked it, which is a hang rather than
        # a message.
        cyclic = Pipeline(
            nodes=tuple(node(node_id) for node_id in ("a", "b", "c", "d")),
            edges=edges("a>b", "b>c", "c>a", "c>d"),
        )

        with pytest.raises(CycleError) as raised:
            Dag.build(cyclic, SHELF)

        # `d` is not in the cycle but cannot be ordered either, and saying so is
        # more useful than a minimal cycle would be: it is the set to look at.
        assert raised.value.nodes == ("a", "b", "c", "d")

    def test_a_missing_filter_is_named_by_id_and_version_all_at_once(self) -> None:
        # The reason `pipeline_model` is not registry-aware: a project from
        # another machine opens, and what the user gets is the list to install
        # rather than a parse error naming nothing. Two nodes of one missing
        # filter is one entry — twelve arenas of a missing detector is not
        # twelve things to install.
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
        # The whole point of declaring I/O: rejected statically, with no codec,
        # no frame, and no backend. `b` emits a table into `d`'s `left`, which
        # accepts arrays — provably disjoint under every parameterization of
        # both. The rejection names the port, because a merging filter's other
        # input may be fine and "which of the two" is the fix.
        with pytest.raises(EdgeTypeError) as raised:
            Dag.build(diamond(b="detect"), SHELF)

        assert (raised.value.upstream, raised.value.downstream) == ("b", "d")
        assert raised.value.port == "left"

    def test_an_edge_into_a_port_the_filter_does_not_declare_is_refused(self) -> None:
        # Silent at run time otherwise: the kernel reads the ports it declared,
        # so a stream wired to a misspelled name would simply never be read.
        graph = Pipeline(
            nodes=(node("a"), node("b"), node("d", "minus")),
            edges=edges("a>d:left", "b>d:rigth"),
        )

        with pytest.raises(PortWiringError, match="rigth"):
            Dag.build(graph, SHELF)

    def test_a_declared_port_left_unfilled_is_refused(self) -> None:
        # The kernel is called with every declared port, so an unfilled one is
        # an argument the executor would have nothing to pass.
        graph = Pipeline(
            nodes=(node("a"), node("d", "minus")),
            edges=edges("a>d:left"),
        )

        with pytest.raises(PortWiringError, match=r"\['right'\] unfilled"):
            Dag.build(graph, SHELF)

    def test_a_merging_filter_cannot_sit_at_a_root(self) -> None:
        # The source is one stream; which of `minus`'s two ports would receive
        # it is not this module's guess to make.
        graph = Pipeline(nodes=(node("d", "minus"),))

        with pytest.raises(PortWiringError, match="cannot be a root"):
            Dag.build(graph, SHELF)


class TestOrder:
    def test_the_order_follows_the_document_and_not_when_a_node_was_freed(self) -> None:
        # `late` becomes ready when `first` is processed, and `second` was ready
        # from the start. Appending the newly-freed node would order it after
        # `second`; re-sorting the ready set by declaration position puts it
        # where the document put it. The difference is invisible until two runs
        # of one project produce reports in different orders.
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
        # There is to be one answer to what a node's key is. The hand-walk here
        # is the same one `tests/unit/test_cache_key.py` writes out, so if the
        # traversal ever grew its own idea — folding in the graph, keying a root
        # against something other than `source_key`, passing upstreams in a
        # different shape — the two files would disagree rather than both being
        # internally consistent.
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

        # The root key carries the decode format, and the hand walk has to say
        # which — `needs_chroma` rather than a literal, because hard-coding
        # `luma=True` here would pass for this shelf of wildcard filters and
        # stop testing the thing that matters: that the walk asks the graph.
        root = source_key(SOURCE, ARENA, luma=not dag.needs_chroma)
        expected = {"a": by_hand("a", {"in": root})}
        expected["b"] = by_hand("b", {"in": expected["a"]})
        expected["c"] = by_hand("c", {"in": expected["a"]})
        expected["d"] = by_hand("d", {"left": expected["b"], "right": expected["c"]})
        assert keys == expected

    def test_swapping_a_merges_ports_moves_its_key_and_only_its_key(self) -> None:
        # The reason the fold is `[port, key]` pairs rather than a sorted list
        # of keys: `b - c` and `c - b` are fed by the same two upstream keys
        # and are not the same computation. A sorted-keys fold would give the
        # two wirings one key and serve one's frames as the other's — the
        # silent direction of `cache_key.py`'s asymmetry rule. Everything
        # *above* the merge is untouched, because a wiring edit below a node
        # has no path into its ancestry.
        #
        # `b` and `c` carry different radii on purpose. Two identical blurs of
        # one upstream share a key *by design* — same computation, same bytes —
        # and swapping the ports of two equal keys genuinely is the same
        # computation, so the baseline diamond would pass this test vacuously.
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
        # `b` cannot be keyed, so `d` — which consumes it — cannot be either,
        # and neither can be looked up in a cache. `a` and `c` are untouched.
        # Raising out of the walk instead would cost the whole graph its
        # entries for one non-deterministic node, and returning a key for `d`
        # would be worse: an entry claiming to stand for a computation nothing
        # can reproduce.
        keys = Dag.build(diamond(b="jitter"), SHELF).node_keys(source=SOURCE, backend=Backend.CPU)

        assert set(keys) == {"a", "c"}
