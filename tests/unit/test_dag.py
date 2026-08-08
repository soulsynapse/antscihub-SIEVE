"""What a graph has to be rejected for, and what the walks have to agree with.

The rejections are the ones the document deliberately cannot make — `Pipeline`
validates structure and stops, so a cycle, a tool that is not installed, and an
edge whose ends cannot be connected all reach this module unchallenged. The
rest are about traversal: that the order is the document's rather than a dict's,
that a meaning folded forward from the source is the graph's answer and not one
spec's, that the format a reader is opened in is derived from the graph, and
that `linear_order` refuses precisely what `Dag.order` accepts.

Schema v1 has one input per node, so the port cases v2 wrote here have no
subject and the wiring rejection they covered is `Pipeline`'s own — two edges
into one node is refused before this module sees the graph
(`tests/unit/test_pipeline_model.py`).
"""

from __future__ import annotations

from fractions import Fraction
from typing import ClassVar

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Replicate
from sieve.core.tool_base import (
    ArraySpec,
    ElementKind,
    ElementNames,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    TableSpec,
)
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import ChannelSpec
from sieve.pipeline.cache_key import node_key, source_key
from sieve.pipeline.dag import (
    CycleError,
    Dag,
    EdgeTypeError,
    GraphError,
    UnresolvedToolError,
    graph_needs_chroma,
    linear_order,
)

#: A scratch shelf, not `REGISTRY`. The process-wide one is populated by tool
#: modules at import, and a test that registered into it would make the suite's
#: behaviour depend on whether such an import had already happened.
SHELF = ToolRegistry()


@register_tool(
    tool_id="blur",
    version="1.0.0",
    summary="Frames in, frames out.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    param_stereotypes={"radius": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class BlurParams(ParamsBase):
    radius: int = 3


@register_tool(
    tool_id="detect",
    version="1.0.0",
    summary="Frames in, rows out.",
    accepts=ArraySpec(),
    emits=TableSpec(columns=("x", "y")),
    emissions=(Emission("out"),),
    registry=SHELF,
)
class DetectParams(ParamsBase):
    pass


@register_tool(
    tool_id="summarize",
    version="1.0.0",
    summary="Rows in, rows out — a node that never reads a pixel.",
    accepts=TableSpec(),
    emits=TableSpec(columns=("count",)),
    emissions=(Emission("out"),),
    registry=SHELF,
)
class SummarizeParams(ParamsBase):
    pass


@register_tool(
    tool_id="gridify",
    version="1.0.0",
    summary="Redefines the element: pixels in, blocks out.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementKind.BLOCK,
    element_names=ElementNames("block", "blocks"),
    registry=SHELF,
)
class GridifyParams(ParamsBase):
    pass


@register_tool(
    tool_id="shrink",
    version="1.0.0",
    summary="Many elements in, one out — `downsample`'s relation.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.AGGREGATED,
    registry=SHELF,
)
class ShrinkParams(ParamsBase):
    pass


@register_tool(
    tool_id="decimate",
    version="1.0.0",
    summary="Keeps one frame in ten, so a row stops being a source frame.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    rate_changing=True,
    param_stereotypes={"stride": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class DecimateParams(ParamsBase):
    stride: int = 10

    def output_rate(self) -> Fraction:
        return Fraction(1, self.stride)


@register_tool(
    tool_id="hue_band",
    version="1.0.0",
    summary="Reads colour: names the packed layouts and omits GRAY.",
    accepts=ArraySpec(channels=(ChannelSpec.RGB, ChannelSpec.BGR)),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class HueBandParams(ParamsBase):
    pass


@register_tool(
    tool_id="either_way",
    version="1.0.0",
    summary="Names layouts but keeps GRAY among them, so it demands nothing.",
    accepts=ArraySpec(channels=(ChannelSpec.GRAY, ChannelSpec.RGB)),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class EitherWayParams(ParamsBase):
    pass


@register_tool(
    tool_id="jitter",
    version="1.0.0",
    summary="Does not claim determinism, so nothing downstream of it may be keyed.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    deterministic=False,
    registry=SHELF,
)
class JitterParams(ParamsBase):
    pass


def node(node_id: str, tool_id: str = "blur", version: str = "1.0.0", **params: object) -> Node:
    return Node(node_id=node_id, tool_id=tool_id, version=version, params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:
    """`"a>b"` for each edge."""
    built: list[Edge] = []
    for pair in pairs:
        upstream, downstream = pair.split(">")
        built.append(Edge(upstream=upstream, downstream=downstream))
    return tuple(built)


def fan_out(**overrides: str) -> Pipeline:
    """a ─┬─> b, the smallest graph that is more than one path.
          └─> c ──> d

    v2's fixture here was a diamond, which schema v1 cannot express: `d` would
    need two producers and the document refuses that before this module runs.
    Fan-out is what survives of the shape and it is what the two walks disagree
    about — `Dag.order` accepts it, `linear_order` refuses it. `overrides` swaps
    one node's tool id, which is how the type-mismatch and colour tests differ
    from the baseline by exactly one thing.
    """
    return Pipeline(
        nodes=tuple(
            node(node_id, overrides.get(node_id, "blur")) for node_id in ("a", "b", "c", "d")
        ),
        edges=edges("a>b", "a>c", "c>d"),
    )


class TestRejections:
    def test_a_cycle_names_every_node_that_could_not_be_ordered(self) -> None:
        # `Pipeline` accepts this: the ids are unique, both endpoints of every
        # edge exist, no edge is a self-loop, and no node has two producers.
        # Nothing below this module would notice before an executor walked it,
        # which is a hang rather than a message.
        cyclic = Pipeline(
            nodes=tuple(node(node_id) for node_id in ("a", "b", "c", "d")),
            edges=edges("a>b", "b>c", "c>a", "c>d"),
        )

        with pytest.raises(CycleError) as raised:
            Dag.build(cyclic, SHELF)

        # `d` is not in the cycle but cannot be ordered either, and saying so is
        # more useful than a minimal cycle would be: it is the set to look at.
        assert raised.value.nodes == ("a", "b", "c", "d")

    def test_a_missing_tool_is_named_by_id_and_version_all_at_once(self) -> None:
        # The reason `pipeline_model` is not registry-aware: a project from
        # another machine opens, and what the user gets is the list to install
        # rather than a parse error naming nothing. Two nodes of one missing
        # tool is one entry — twelve arenas of a missing detector is not twelve
        # things to install.
        unresolvable = Pipeline(
            nodes=(
                node("a", "wavelet_bands", "2.1.0"),
                node("b", "wavelet_bands", "2.1.0"),
                node("c", "blur", "9.0.0"),
            ),
            edges=edges("a>b", "b>c"),
        )

        with pytest.raises(UnresolvedToolError) as raised:
            Dag.build(unresolvable, SHELF)

        assert raised.value.missing == (("wavelet_bands", "2.1.0"), ("blur", "9.0.0"))
        assert "wavelet_bands 2.1.0" in str(raised.value)
        assert "blur 9.0.0" in str(raised.value)

    def test_rows_may_not_feed_an_input_that_wants_frames(self) -> None:
        # The whole point of declaring I/O: rejected statically, with no codec
        # and no frame. `c` emits a table into `d`, which accepts arrays —
        # provably disjoint under every parameterization of both.
        with pytest.raises(EdgeTypeError) as raised:
            Dag.build(fan_out(c="detect"), SHELF)

        assert (raised.value.upstream, raised.value.downstream) == ("c", "d")


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
        "edge type": fan_out(c="detect"),
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
        assert Dag.validate(fan_out(), SHELF) == ()
        Dag.build(fan_out(), SHELF)

    def test_two_independent_faults_are_both_reported(self) -> None:
        # The reason the mode exists. `build` names the first seam and stops, so
        # a stack drawing this graph would paint one card red, the user would
        # fix it, and the second fault would appear only then — which for a
        # loaded file that broke in three places is three round trips through a
        # rerun.
        #
        # Two *unrelated* faults on purpose, in disconnected halves of one
        # document: neither is derivable from the other, so a walk that stopped
        # at the first would be losing information rather than declining to
        # guess.
        graph = Pipeline(
            nodes=(
                node("a"),
                node("b", "detect"),
                node("c"),
                node("d"),
                node("e", "detect"),
                node("f"),
            ),
            edges=edges("a>b", "b>c", "d>e", "e>f"),
        )

        diagnostics = Dag.validate(graph, SHELF)

        assert [each.nodes for each in diagnostics] == [("b", "c"), ("e", "f")]
        assert all(isinstance(each.error, EdgeTypeError) for each in diagnostics)

    def test_an_unresolved_tool_reports_every_node_naming_it(self) -> None:
        # The information `UnresolvedToolError` alone cannot give, and the
        # reason a diagnostic carries nodes beside the error: the user installs
        # *one* tool and a renderer colours *three* cards. Deduplicating the
        # install list and enumerating the nodes are different questions with
        # different right answers, and the error only ever answered the first.
        graph = Pipeline(
            nodes=(node("a", "mystery"), node("b", "mystery"), node("c", "mystery")),
            edges=edges("a>b", "b>c"),
        )

        (diagnostic,) = Dag.validate(graph, SHELF)

        assert diagnostic.nodes == ("a", "b", "c")
        assert isinstance(diagnostic.error, UnresolvedToolError)
        assert diagnostic.error.missing == (("mystery", "1.0.0"),)

    def test_nothing_is_reported_that_a_missing_spec_would_have_to_be_guessed_from(self) -> None:
        # Collecting is only sound where the inputs survive. `b` names a tool
        # nobody has, so the edge into `c` has no `emits` to check — every
        # verdict past the unresolved one would be invented. `build` stops here
        # for the same reason and this is that reason made structural rather
        # than a second policy.
        graph = Pipeline(
            nodes=(node("a"), node("b", "mystery"), node("c")),
            edges=edges("a>b", "b>c"),
        )

        diagnostics = Dag.validate(graph, SHELF)

        assert len(diagnostics) == 1
        assert isinstance(diagnostics[0].error, UnresolvedToolError)

    def test_a_mistyped_edge_names_both_ends_it_could_be_repaired_from(self) -> None:
        # A renderer asking "which card" reads `error.downstream`; a renderer
        # drawing the *seam* wants both, and an edge is repairable by changing
        # either tool.
        (diagnostic,) = Dag.validate(fan_out(c="detect"), SHELF)

        assert diagnostic.nodes == ("c", "d")


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
        dag = Dag.build(fan_out(), SHELF)
        position = {each.node_id: index for index, each in enumerate(dag.order)}

        for each in dag.order:
            for upstream in dag.upstreams[each.node_id]:
                assert position[upstream] < position[each.node_id]
        assert tuple(each.node_id for each in dag.roots) == ("a",)
        assert tuple(each.node_id for each in dag.leaves) == ("b", "d")

    def test_an_empty_graph_builds_and_names_no_roots(self) -> None:
        # A project opens before anything is on its canvas, and the walks are
        # what the front end asks about it. Kahn's loop over no nodes and the
        # root query over no order are both total, and a graph nobody has
        # written yet must not be the one shape that raises.
        dag = Dag.build(Pipeline(), SHELF)

        assert (dag.order, dag.roots, dag.leaves) == ((), (), ())


class TestElementMeaning:
    """What one value of each node's output is a value of, folded from the source.

    The walk is the half `tool_base.node_element` deliberately cannot do: the
    conversion needs the upstream's answer, and only a graph has it. Each test
    here is a shape of chain where reading one spec in isolation gives the
    wrong answer.
    """

    def test_the_source_is_pixels_and_a_preserving_root_says_so(self) -> None:
        # Where `PIXEL` enters. A tool that preserves has no constant to
        # declare, so a root's element is a fact about the decoder, not about
        # the tool — and it has to be stated somewhere or every chain of
        # preserving tools resolves to nothing.
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
        # `--node` at `c` is the invocation that would write a pixel count under
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

    def test_a_table_emitter_has_no_element_at_all(self) -> None:
        graph = Pipeline(nodes=(node("a"), node("b", "detect")), edges=edges("a>b"))

        assert Dag.build(graph, SHELF).elements["b"] is None

    def test_a_second_upstream_is_refused_rather_than_folded_from_the_first(self) -> None:
        # The posture `node_keys` states and these two folds have to keep: a
        # node with two inputs is a graph neither knows how to answer for, and
        # answering from `fed[0]` would be the silent wrong meaning propagated
        # to every node after it. `Dag.build` cannot construct the mapping —
        # `Pipeline` refuses two edges into one node — so the folds are called
        # directly, which is the only place the difference is reachable.
        order = (node("a"), node("b", "gridify"), node("c"))
        specs = Dag.build(Pipeline(nodes=order), SHELF).specs
        upstreams = {"a": (), "b": (), "c": ("a", "b")}

        with pytest.raises(ValueError):
            Dag._elements(order, specs, upstreams)
        with pytest.raises(ValueError):
            Dag._element_names(order, specs, upstreams)


class TestSourceIndexing:
    def test_a_rate_change_unindexes_itself_and_everything_after_it(self) -> None:
        # The declaration a table writer needs and `rate_changing` alone does
        # not give: which *nodes* sit behind a rate change. `a` is still
        # source-indexed, and `frame = start + offset` is only true there.
        graph = Pipeline(
            nodes=(node("a"), node("b", "decimate"), node("c")),
            edges=edges("a>b", "b>c"),
        )

        assert Dag.build(graph, SHELF).source_indexed == {"a": True, "b": False, "c": False}

    def test_a_graph_with_no_rate_change_is_indexed_throughout(self) -> None:
        assert all(Dag.build(fan_out(), SHELF).source_indexed.values())


class TestWhereMeaningWasLost:
    def test_it_names_the_node_that_lost_it_not_the_one_that_asked(self) -> None:
        # The whole reason this is a graph query. `c` aggregates a block grid
        # and `d` merely preserves the nothing it was handed, so a message
        # about `d` would send a reader to a tool that is fine — and `c`'s own
        # declaration is fine too, which is why the answer is a *node* and not a
        # tool.
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

    def test_a_branch_that_does_not_feed_the_asker_is_not_blamed(self) -> None:
        # `sibling` loses its meaning too and is ordered *before* `c`, so a walk
        # that scanned the graph for the first undeclarable node would report a
        # branch `d` is not downstream of. The walk has to collect ancestors, or
        # the first unrelated loss anywhere is reported as the cause.
        graph = Pipeline(
            nodes=(
                node("a"),
                node("b", "gridify"),
                node("sibling", "shrink"),
                node("c", "shrink"),
                node("d"),
            ),
            edges=edges("a>b", "b>sibling", "b>c", "c>d"),
        )

        dag = Dag.build(graph, SHELF)

        assert dag.elements["sibling"] is None
        assert dag.element_lost_at("d") == "c"

    def test_asking_about_a_node_that_has_a_meaning_is_refused(self) -> None:
        # Returning `None` here would make every caller narrow an answer that
        # is total under its own precondition, and the narrowing is where an
        # `assert ... is not None` gets written.
        with pytest.raises(ValueError, match="so nothing was lost"):
            Dag.build(fan_out(), SHELF).element_lost_at("d")


class TestDecodeFormat:
    """Which format the reader is opened in, derived from the graph.

    v2 tested `needs_chroma` from the caller that consumed it rather than here.
    It is a graph query with a measured cost behind it — the luma plane is 2.4x
    cheaper to decode — so the cases that pin it belong beside the walk that
    answers it.
    """

    def test_a_graph_of_unconstrained_tools_is_decoded_from_luma(self) -> None:
        # Silence is never a demand: a tool that leaves `channels` empty means
        # "any", which includes GRAY. Today no tool on the shelf reads colour,
        # so this is the answer for every real graph.
        assert Dag.build(fan_out(), SHELF).needs_chroma is False
        assert graph_needs_chroma(fan_out(), SHELF) is False

    def test_one_node_demanding_colour_flips_the_whole_graph(self) -> None:
        # Over-inclusive on purpose, and the whole graph rather than the roots:
        # only roots touch the source frame, but layout propagates, and a
        # downstream node demanding colour is evidence the chain was meant to
        # carry it. An input wrongly included is a slower correct answer; one
        # wrongly omitted is a wrong one served from cache and never noticed.
        assert Dag.build(fan_out(d="hue_band"), SHELF).needs_chroma is True

    def test_a_layout_set_that_still_admits_gray_is_not_a_demand(self) -> None:
        # The question is whether GRAY is *excluded*, not whether colour is
        # named. A tool that accepts either would be handed luma and be right.
        assert Dag.build(fan_out(d="either_way"), SHELF).needs_chroma is False

    def test_a_node_that_consumes_rows_never_demands_pixels(self) -> None:
        graph = Pipeline(
            nodes=(node("a"), node("b", "detect"), node("c", "summarize")),
            edges=edges("a>b", "b>c"),
        )

        assert Dag.build(graph, SHELF).needs_chroma is False

    def test_a_graph_that_does_not_resolve_asks_for_colour(self) -> None:
        # "This tool is missing" is not a question about chroma, and the caller
        # is about to fail on it properly a moment later. Answering `True` keeps
        # the fallback the format that has always been the default.
        graph = Pipeline(nodes=(node("a", "mystery"),))

        assert graph_needs_chroma(graph, SHELF) is True


class TestKeyWalk:
    """The traversal `cache_key.py` names and declines to own.

    `test_cache_key.py` writes its own three-node walk by hand precisely because
    that module carries none; the claim here is that this one agrees with such a
    walk, which is what stops the graph growing a second idea of what a key is.
    Everything a key separates is asserted there — this class asserts only what
    the *walk* adds: the source key reaching the roots, the format coming from
    the graph, the replicate reaching every node, and a refusal propagating by
    absence.
    """

    #: What `cache_key.source_identity` would have produced. Taken as a string
    #: by the walk, so no file has to exist for the keys to be derivable.
    SOURCE = "arena.mp4|4096|17"

    def test_the_walk_is_the_hand_walk(self) -> None:
        # The anti-drift claim. A traversal that chained the keys in some other
        # order, or handed a root something other than the source key, would
        # still produce a stable dict of distinct-looking hashes — every
        # property short of this one survives getting the chaining wrong.
        dag = Dag.build(fan_out(), SHELF)
        root = source_key(self.SOURCE, decode_format="luma")

        def key(node_id: str, upstream: str) -> str:
            return node_key(dag.pipeline.node(node_id), spec=dag.spec(node_id), upstream=upstream)

        by_hand = {"a": key("a", root)}
        by_hand["b"] = key("b", by_hand["a"])
        by_hand["c"] = key("c", by_hand["a"])
        by_hand["d"] = key("d", by_hand["c"])

        assert dag.node_keys(source=self.SOURCE) == by_hand

    def test_the_format_the_reader_will_open_is_the_format_in_the_key(self) -> None:
        # `needs_chroma` is derived here rather than passed in so that the key
        # and the reader cannot disagree about what was decoded. `a` is upstream
        # of the node that demands colour and its own tool is unchanged, so its
        # key can only move through the source key — which is the position under
        # test. Getting this wrong serves a luma-decoded frame to a colour graph
        # from cache, and the run completes.
        luma = Dag.build(fan_out(), SHELF)
        colour = Dag.build(fan_out(d="hue_band"), SHELF)
        assert (luma.needs_chroma, colour.needs_chroma) == (False, True)

        assert colour.node_keys(source=self.SOURCE)["a"] != luma.node_keys(source=self.SOURCE)["a"]

    def test_an_uncacheable_node_takes_its_descendants_and_nobody_else(self) -> None:
        # A node absent from the result is a node that must be computed, and
        # neither cause is an error. `NotCacheableError` is swallowed at exactly
        # the node that raises it and then propagates for free — `d` has no
        # upstream key to fold in, so it drops without anything computing that
        # fact. Raising out of the walk instead would make one non-deterministic
        # node cost every other node in the graph its cache entries.
        dag = Dag.build(fan_out(c="jitter"), SHELF)

        keys = dag.node_keys(source=self.SOURCE)

        assert set(keys) == {"a", "b"}
        # And the survivors are unchanged by the refusal beside them, rather
        # than merely present.
        intact = Dag.build(fan_out(), SHELF).node_keys(source=self.SOURCE)
        assert {node_id: keys[node_id] for node_id in ("a", "b")} == {
            node_id: intact[node_id] for node_id in ("a", "b")
        }

    def test_a_replicate_deviation_reaches_the_node_it_names_and_its_descendants(self) -> None:
        # The walk threads `replicate` into every `node_key` call, and a walk
        # that dropped it would pass both cases above: the hand walk keys the
        # baseline, and a refusal propagates regardless. What would then break
        # is silent and total — twelve arenas sharing one set of keys, each
        # served the frames of whichever ran first.
        dag = Dag.build(fan_out(), SHELF)
        baseline = dag.node_keys(source=self.SOURCE)

        arena = Replicate(name="Replicate 1").with_override("c", {"radius": 11})
        deviated = dag.node_keys(source=self.SOURCE, replicate=arena)

        assert (deviated["c"], deviated["d"]) != (baseline["c"], baseline["d"])
        assert (deviated["a"], deviated["b"]) == (baseline["a"], baseline["b"])


class TestLookups:
    def test_an_id_this_graph_does_not_carry_is_a_key_error(self) -> None:
        # Both queries declare it, and a declared raise nothing proves is a
        # sentence in a docstring rather than a contract.
        dag = Dag.build(fan_out(), SHELF)

        with pytest.raises(KeyError):
            dag.spec("nope")
        with pytest.raises(KeyError):
            dag.element_lost_at("nope")


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

    def test_a_chain_of_tools_nobody_has_installed_still_orders(self) -> None:
        # No registry and no `Dag`: shape is answerable without resolution, and
        # this is what lets the stack rebuild from a project opened on a machine
        # missing half its tools instead of failing to draw at all.
        graph = Pipeline(
            nodes=(node("a", "mystery"), node("b", "also_missing")),
            edges=edges("a>b"),
        )

        assert tuple(each.node_id for each in linear_order(graph)) == ("a", "b")

    def test_a_branch_is_refused_though_it_executes_fine(self) -> None:
        # The seam: `Dag.build` accepts this graph and the executor runs it.
        # Flattening it to a stack would draw seams claiming `b` feeds `c` in
        # sequence when the two are fed in parallel.
        Dag.build(fan_out(), SHELF)

        with pytest.raises(GraphError, match="branches"):
            linear_order(fan_out())

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

    def test_an_empty_graph_is_an_empty_chain(self) -> None:
        # The stack draws a project with nothing on it, and the root count check
        # below would refuse a graph that has no root because it has no nodes.
        assert linear_order(Pipeline()) == ()
