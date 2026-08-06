"""What a graph has to be rejected for, and what the walks have to agree with.

The rejections are the ones the artifact layer deliberately cannot make —
`Pipeline` validates structure and stops, so a cycle, a filter that is not
installed, and an edge whose ends cannot be connected all reach this module
unchallenged. The rest are about traversal: that the order is the document's
rather than a dict's, that it produces the same keys a hand-walk does, that a
node with no key takes its descendants with it and nobody else, and that
`linear_order` refuses precisely what `Dag.order` accepts.
"""

from __future__ import annotations

from fractions import Fraction
from typing import ClassVar

import pytest

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementKind,
    ElementNames,
    ElementRelation,
    ParamsBase,
    TableSpec,
)
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, WorkUnits
from sieve.pipeline.cache_key import node_key, source_key
from sieve.pipeline.dag import (
    CycleError,
    Dag,
    EdgeTypeError,
    GraphError,
    PortWiringError,
    UnresolvedFilterError,
    linear_order,
)

COST = CostEstimate(work_per_megapixel=WorkUnits(1.0))
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
    element_names=ElementNames("block", "blocks"),
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


class TestValidate:
    """The collect-all mode, and that it is the same definition as the raise.

    The thing worth pinning is not that `validate` finds faults — `build`
    already did — but that the two modes cannot drift: one walk, one order, one
    sentence. A second spelling of edge legality that agreed on the examples
    somebody thought to write is exactly what this replaces.
    """

    #: Every graph `TestRejections` rejects, by the fault it carries. Reused
    #: rather than rewritten so that a rejection added there is one this class
    #: checks the collect-all mode against too.
    BROKEN: ClassVar[dict[str, Pipeline]] = {
        "cycle": Pipeline(
            nodes=tuple(node(node_id) for node_id in ("a", "b", "c", "d")),
            edges=edges("a>b", "b>c", "c>a", "c>d"),
        ),
        "unresolved": Pipeline(
            nodes=(node("a", "wavelet_bands", "2.1.0"), node("b", "blur", "9.0.0")),
            edges=edges("a>b"),
        ),
        "edge type": diamond(b="detect"),
        "unknown port": Pipeline(
            nodes=(node("a"), node("b"), node("d", "minus")),
            edges=edges("a>d:left", "b>d:rigth"),
        ),
        "unfilled port": Pipeline(
            nodes=(node("a"), node("d", "minus")),
            edges=edges("a>d:left"),
        ),
        "merging root": Pipeline(nodes=(node("d", "minus"),)),
    }

    @pytest.mark.parametrize("broken", BROKEN.values(), ids=list(BROKEN))
    def test_the_first_diagnostic_is_the_error_build_raises(self, broken: Pipeline) -> None:
        # The anti-drift claim, and the whole reason `Diagnostic` carries the
        # error rather than a message assembled beside it. A renderer and the
        # executor that refuses to run the same graph say one thing about it, in
        # one wording, and no reviewer has to keep two sentences in step.
        with pytest.raises(GraphError) as raised:
            Dag.build(broken, SHELF)

        first = Dag.validate(broken, SHELF)[0]
        assert type(first.error) is type(raised.value)
        assert first.message == str(raised.value)

    def test_a_graph_that_validates_clean_is_one_build_accepts(self) -> None:
        # The other direction, which is what makes an empty list worth acting
        # on: a caller that renders no fault must not then watch the run refuse.
        assert Dag.validate(diamond(), SHELF) == ()
        Dag.build(diamond(), SHELF)

    def test_two_independent_faults_are_both_reported(self) -> None:
        # The reason the mode exists. `build` names `b` and stops, so a stack
        # drawing this chain would paint one card red, the user would fix it,
        # and the second fault would appear only then — which for a loaded file
        # that broke in three places is three round trips through a rerun.
        #
        # Two *unrelated* faults on purpose: `b` leaves a port unfilled and `e`
        # is a merging filter at a root. Neither is derivable from the other, so
        # a walk that stopped at the first would be losing information rather
        # than declining to guess.
        graph = Pipeline(
            nodes=(node("a"), node("b", "minus"), node("e", "minus")),
            edges=edges("a>b:left"),
        )

        diagnostics = Dag.validate(graph, SHELF)

        assert [each.nodes for each in diagnostics] == [("b",), ("e",)]
        assert all(isinstance(each.error, PortWiringError) for each in diagnostics)

    def test_an_unresolved_filter_reports_every_node_naming_it(self) -> None:
        # The information `UnresolvedFilterError` alone cannot give, and the
        # reason a diagnostic carries nodes beside the error: the user installs
        # *one* filter and a renderer colours *three* cards. Deduplicating the
        # install list and enumerating the nodes are different questions with
        # different right answers, and the error only ever answered the first.
        graph = Pipeline(
            nodes=(node("a", "mystery"), node("b", "mystery"), node("c", "mystery")),
            edges=edges("a>b", "b>c"),
        )

        (diagnostic,) = Dag.validate(graph, SHELF)

        assert diagnostic.nodes == ("a", "b", "c")
        assert isinstance(diagnostic.error, UnresolvedFilterError)
        assert diagnostic.error.missing == (("mystery", "1.0.0"),)

    def test_nothing_is_reported_that_a_missing_spec_would_have_to_be_guessed_from(self) -> None:
        # Collecting is only sound where the inputs survive. `b` names a filter
        # nobody has, so its ports are unknown and the edge into `c` has no
        # `emits` to check — every verdict past the unresolved one would be
        # invented. `build` stops here for the same reason and this is that
        # reason made structural rather than a second policy.
        graph = Pipeline(
            nodes=(node("a"), node("b", "mystery"), node("c", "minus")),
            edges=edges("a>c:left", "b>c:right"),
        )

        diagnostics = Dag.validate(graph, SHELF)

        assert len(diagnostics) == 1
        assert isinstance(diagnostics[0].error, UnresolvedFilterError)

    def test_a_node_whose_wiring_is_broken_gets_no_second_verdict_about_its_types(self) -> None:
        # `d` has an edge into `rigth`, which `minus` does not declare — so
        # there is no `accepts` for that port to check `b`'s `emits` against,
        # and `left` being genuinely mistyped is a fault about a chain the user
        # cannot see until the port name is fixed. One card, one repair.
        graph = Pipeline(
            nodes=(node("a"), node("b", "detect"), node("d", "minus")),
            edges=edges("a>b", "b>d:left", "a>d:rigth"),
        )

        (diagnostic,) = Dag.validate(graph, SHELF)

        assert isinstance(diagnostic.error, PortWiringError)
        assert diagnostic.nodes == ("d",)

    def test_a_mistyped_edge_names_both_ends_it_could_be_repaired_from(self) -> None:
        # A renderer asking "which card" reads `error.downstream`; a renderer
        # drawing the *seam* wants both, and an edge is repairable by changing
        # either filter. The error class has carried both since before anything
        # collected them.
        (diagnostic,) = Dag.validate(diamond(b="detect"), SHELF)

        assert diagnostic.nodes == ("b", "d")


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


class TestElementMeaning:
    """What one value of each node's output is a value of, folded from the source.

    The walk is the half `filter_base.node_element` deliberately cannot do: the
    conversion needs the upstream's answer, and only a graph has it. Each test
    here is a shape of chain where reading one spec in isolation gives the
    wrong answer.
    """

    def test_the_source_is_pixels_and_a_preserving_root_says_so(self) -> None:
        # Where `PIXEL` enters. A filter that preserves has no constant to
        # declare, so a root's element is a fact about the decoder, not about
        # the filter — and it has to be stated somewhere or every chain of
        # preserving filters resolves to nothing.
        graph = Pipeline(nodes=(node("a"),))

        dag = Dag.build(graph, SHELF)
        assert dag.elements == {"a": ElementKind.PIXEL}
        assert dag.element_names == {"a": ElementNames("pixel", "pixels")}

    def test_meaning_carries_through_every_preserving_node_after_a_redefinition(self) -> None:
        # The real chain, and the reason `PRESERVED` exists at all:
        # `temporal_baseline` accepts any array, so it cannot declare a
        # constant, and a detection over it is the normal case rather than an
        # exotic one. Reading its spec alone says nothing; reading the graph
        # says blocks.
        graph = Pipeline(
            nodes=(node("a"), node("b", "gridify"), node("c"), node("d")),
            edges=edges("a>b", "b>c", "c>d"),
        )

        dag = Dag.build(graph, SHELF)
        assert dag.elements == {
            "a": ElementKind.PIXEL,
            "b": ElementKind.BLOCK,
            "c": ElementKind.BLOCK,
            "d": ElementKind.BLOCK,
        }
        assert dag.element_names == {
            "a": ElementNames("pixel", "pixels"),
            "b": ElementNames("block", "blocks"),
            "c": ElementNames("block", "blocks"),
            "d": ElementNames("block", "blocks"),
        }

    def test_aggregating_blocks_loses_the_meaning_and_it_never_returns(self) -> None:
        # `--node` at `c` is the invocation that wrote a pixel count under
        # `blocks_in_band`. Aggregating pixels is fine and stays pixels;
        # aggregating blocks is not a block, and `d` preserving that cannot
        # invent the meaning back.
        graph = Pipeline(
            nodes=(node("a", "shrink"), node("b", "gridify"), node("c", "shrink"), node("d")),
            edges=edges("a>b", "b>c", "c>d"),
        )

        dag = Dag.build(graph, SHELF)
        assert dag.elements == {
            "a": ElementKind.PIXEL,
            "b": ElementKind.BLOCK,
            "c": None,
            "d": None,
        }
        assert dag.element_names == {
            "a": ElementNames("pixel", "pixels"),
            "b": ElementNames("block", "blocks"),
            "c": None,
            "d": None,
        }

    def test_a_merge_of_two_meanings_resolves_to_neither(self) -> None:
        # `d` subtracts a block grid from a pixel frame. Nothing it emits has
        # one meaning, and picking an upstream's would be the invented noun
        # under a different name.
        graph = Pipeline(
            nodes=(node("a"), node("b", "gridify"), node("c"), node("d", "minus")),
            edges=edges("a>b", "a>c", "b>d:left", "c>d:right"),
        )

        dag = Dag.build(graph, SHELF)
        assert dag.elements["d"] is None
        assert dag.element_names["d"] is None

    def test_a_table_emitter_has_no_element_at_all(self) -> None:
        graph = Pipeline(nodes=(node("a"), node("b", "detect")), edges=edges("a>b"))

        assert Dag.build(graph, SHELF).elements["b"] is None


class TestSourceIndexing:
    def test_a_rate_change_unindexes_itself_and_everything_after_it(self) -> None:
        # The declaration `detect/tables.py` needs and `rate_changing` alone
        # does not give: which *nodes* sit behind a rate change. `a` is still
        # source-indexed, and `frame = start + offset` is only true there.
        graph = Pipeline(
            nodes=(node("a"), node("b", "decimate"), node("c")),
            edges=edges("a>b", "b>c"),
        )

        assert Dag.build(graph, SHELF).source_indexed == {"a": True, "b": False, "c": False}

    def test_a_graph_with_no_rate_change_is_indexed_throughout(self) -> None:
        assert all(Dag.build(diamond(), SHELF).source_indexed.values())


class TestWhereMeaningWasLost:
    def test_it_names_the_node_that_lost_it_not_the_one_that_asked(self) -> None:
        # The whole reason this is a graph query. `c` aggregates a block grid
        # and `d` merely preserves the nothing it was handed, so a message
        # about `d` would send a reader to a filter that is fine — and `c`'s
        # own declaration is fine too, which is why the answer is a *node* and
        # not a filter.
        graph = Pipeline(
            nodes=(node("a"), node("b", "gridify"), node("c", "shrink"), node("d")),
            edges=edges("a>b", "b>c", "c>d"),
        )

        assert Dag.build(graph, SHELF).element_lost_at("d") == "c"

    def test_the_earliest_loss_wins_when_a_chain_loses_it_twice(self) -> None:
        # Every `None` after the first is that one propagating, and the
        # earliest is the only one where detecting upstream still helps.
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
        # `b` is upstream of nothing that reaches `d` through a loss; the walk
        # has to collect ancestors rather than scan the whole graph for a
        # `None`, or the first unrelated undeclarable node anywhere would be
        # reported as the cause.
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
        # Returning `None` here would make every caller narrow an answer that
        # is total under its own precondition, and the narrowing is where an
        # `assert ... is not None` gets written.
        with pytest.raises(ValueError, match="so nothing was lost"):
            Dag.build(diamond(), SHELF).element_lost_at("d")


class TestLinearOrder:
    """`linear_order` refuses every graph `Dag.order` tolerates but one path.

    The two walks answer different questions over the same structure, so what
    is worth pinning is the gap between them, not that either one sorts.
    """

    def test_the_order_is_the_edges_and_not_the_declaration(self) -> None:
        # Reversed in the tuple, so a walk that iterated `pipeline.nodes` and
        # called it an order would pass every branch check and still hand the
        # stack a chain drawn upside down.
        graph = Pipeline(
            nodes=(node("c"), node("b"), node("a")),
            edges=edges("a>b", "b>c"),
        )

        assert tuple(each.node_id for each in linear_order(graph)) == ("a", "b", "c")

    def test_a_chain_of_filters_nobody_has_installed_still_orders(self) -> None:
        # No registry and no `Dag`: shape is answerable without resolution, and
        # this is what lets the stack rebuild from a project opened on a machine
        # missing half its filters instead of failing to draw at all.
        graph = Pipeline(
            nodes=(node("a", "mystery"), node("b", "also_missing")),
            edges=edges("a>b"),
        )

        assert tuple(each.node_id for each in linear_order(graph)) == ("a", "b")

    def test_a_diamond_is_refused_though_it_executes_fine(self) -> None:
        # The seam: `Dag.build` accepts this graph and the executor runs it.
        # Flattening it to a stack would draw seams claiming `c` feeds `d` in
        # sequence when it feeds it in parallel with `b`.
        Dag.build(diamond(), SHELF)

        with pytest.raises(GraphError, match="branches"):
            linear_order(diamond())

    def test_a_cycle_off_the_root_is_refused_as_disconnected(self) -> None:
        # One root, no node with two edges out — so the branch and root checks
        # both pass and only the reachability count catches it. `linear_order`
        # resolves nothing and so never gets a `CycleError` to report.
        graph = Pipeline(
            nodes=tuple(node(node_id) for node_id in ("a", "b", "c", "d")),
            edges=edges("a>b", "c>d", "d>c"),
        )

        with pytest.raises(GraphError, match="disconnected"):
            linear_order(graph)
