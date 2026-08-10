"""What a cache key is required to separate, and what it is required to conflate.

Every test here is a way a key stops meaning "this exact result has been
produced before". Some cover the direction that is silent when it fails: a key
that conflates two computations serves a wrong frame and the run still
completes. The rest cover the direction that merely costs time — a key that
separates two things that are the same recomputes work it had.

Isolation and propagation are asserted as a pair, and the pair is the point.
"An edit here does not reach there" is three equalities over keys that did not
move, and a `node_key` that ignored its `upstream` argument satisfies all three
— which is how it was found (`findings/loop/`,
`2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md`).

Schema v1 moved one of v2's cases without weakening it. A replicate's geometry
is a per-replicate override on the crop node's region parameter
(`adr/detector-is-a-node.md`), so two replicates over different pixels are
separated through `resolved_params` like any other deviation rather than
through a field the source key had to be taught.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    resolved_params,
)
from sieve.core.tool_base import (
    SOLE_PORT,
    SOURCE_ELEMENT_NAMES,
    SPEC_CHANNELS,
    ArraySpec,
    AxisRelation,
    CaptionPart,
    Channel,
    DisplaySurface,
    ElementKind,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
    ValueAxis,
    WarmupKind,
)
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import FrameCount
from sieve.pipeline import cache_key
from sieve.pipeline.cache_key import (
    NODE_KEY_POSITIONS,
    SOURCE_KEY_POSITIONS,
    NotCacheableError,
    is_cacheable,
    node_key,
    source_key,
)
from sieve.pipeline.dag import Dag
from sieve.pipeline.resolve_source import anchored


class BlurParams(ParamsBase):
    """Two fields so a test can move one and leave the other inherited.

    `separable` is neither of those two. It is here because a stereotype map is
    checked against the annotations it stands over, and `enum` on a number is
    refused — so a model of numbers alone admits exactly one legal map and the
    presentation substitute below would have nothing to differ by.
    """

    radius: int = 3
    sigma: float = 1.0
    separable: bool = True


class CropParams(ParamsBase):
    """A region as an ordinary parameter — what schema v1 made the geometry."""

    region: tuple[int, int, int, int] = (0, 0, 64, 64)


def make_spec(**overrides: object) -> ToolSpec:
    fields: dict[str, object] = {
        "tool_id": "blur",
        "version": "1.0.0",
        "summary": "Blur.",
        "params_model": BlurParams,
        "accepts": ArraySpec(),
        "emits": ArraySpec(),
        "emissions": (Emission("out"),),
        "element": ElementRelation.PRESERVED,
        "param_stereotypes": {
            "radius": ParamStereotype.SCALAR_RANGE,
            "sigma": ParamStereotype.SCALAR_RANGE,
            "separable": ParamStereotype.SCALAR_RANGE,
        },
    }
    fields.update(overrides)
    return ToolSpec(**fields)  # pyright: ignore[reportArgumentType]


SPEC = make_spec()


class BandedBlurParams(BlurParams):
    """`BlurParams` with a band, which is the only thing an axis may stand over.

    A subclass rather than a fourth field on `BlurParams`, because the params
    model is the *identity* channel: every key in this file is derived from it,
    and giving the shared model a band would move them all.
    """

    band: tuple[float, float] = (0.0, 1.0)


def _fills_nothing(params: BandedBlurParams, window: object, /) -> dict[object, object]:
    """A filler, so the surface below is not a declaration nothing draws."""
    del params, window
    return {}


#: The spec the `param_axes` substitution is made against. It cannot be `SPEC`:
#: an axis is legal only on a band, a band needs a params model with one, and
#: that model is the one thing this test holds fixed.
BANDED_SPEC = make_spec(
    params_model=BandedBlurParams,
    param_stereotypes={
        "radius": ParamStereotype.SCALAR_RANGE,
        "sigma": ParamStereotype.SCALAR_RANGE,
        "separable": ParamStereotype.SCALAR_RANGE,
        "band": ParamStereotype.BAND,
    },
    param_surfaces={"band": DisplaySurface.TRACE},
    param_axes={"band": ValueAxis()},
    display=_fills_nothing,
)

#: The first spec here with more than one input. Two array ports rather than one
#: of each kind, so that what separates them is the wiring and nothing else —
#: the crossing has to move the key on the labels alone.
MERGE_SPEC = make_spec(
    tool_id="merge",
    summary="Reads two streams.",
    accepts={"left": ArraySpec(), "right": ArraySpec()},
)

CROP_SPEC = make_spec(
    tool_id="crop",
    summary="Cuts a region out of the frame.",
    params_model=CropParams,
    param_stereotypes={"region": ParamStereotype.REGION},
)

#: A scratch shelf, for `test_preview.py`'s reason: the process-wide one is
#: populated by tool modules at import, so registering into it would make this
#: file's behaviour depend on whether such an import had already happened. Two
#: tools rather than one, because the claim below is about the keys *under* a
#: source and a source alone has nothing under it.
SHELF = ToolRegistry()


class _NothingRead:
    """A `ToolSource` that resolves its parameter and reads no file.

    `TestPortability`'s case never runs the graph and never stats anything — it
    hands `node_keys` an identity directly, which is what isolates the spelling
    of the path from what the path resolves to.
    """

    #: Own code rather than `decode/`, so this root folds `picked_key`
    #: (`adr/a-root-keys-by-its-reader.md`). The claim holds for either flavour;
    #: this is the one whose ancestor is the picked file and nothing else.
    decoded = False

    def files(self, params: PlateParams, /) -> tuple[Path, ...]:
        return (Path(params.pattern),)

    def file(self, params: PlateParams, /) -> Path:
        return Path(params.pattern)

    def read(self, params: PlateParams, index: object, /, *, luma: bool) -> object:
        raise AssertionError("no case here reads a frame")


@register_tool(
    tool_id="plate",
    version="1.0.0",
    summary="Reads the file its own path parameter names.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("plate"),),
    source=_NothingRead(),
    element=ElementKind.PIXEL,
    element_names=SOURCE_ELEMENT_NAMES,
    param_stereotypes={"pattern": ParamStereotype.PATH},
    registry=SHELF,
)
class PlateParams(ParamsBase):
    pattern: str = ""


@register_tool(
    tool_id="shade",
    version="1.0.0",
    summary="Whatever a source root feeds.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    param_stereotypes={"radius": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class ShadeParams(ParamsBase):
    radius: int = 3


def sole(key: str) -> tuple[tuple[str | None, str], ...]:
    """`key` as the one input of a single-input node.

    `node_key` takes `(port, key)` pairs, and most of this file is about a node
    with one input, whose port is `SOLE_PORT`. Written once here so the cases
    that are not about ports do not each spell the pairing out.
    """
    return ((SOLE_PORT, key),)


#: A stand-in for whatever the walk hands a root. Every key in this file is
#: derived from something, because a root's upstream is the source key and
#: there is no node with no input at all.
ROOT = sole("root-key")


def make_node(node_id: str, **params: object) -> Node:
    return Node(node_id=node_id, tool_id="blur", version="1.0.0", params=dict(params))


def make_project(*replicates: Replicate) -> Project:
    """One root feeding two siblings — the smallest graph the isolation claim needs.

    a ─┬─> b
       └─> c
    """
    return Project(
        replicates=replicates,
        pipeline=Pipeline(
            nodes=(make_node("a", radius=3), make_node("b", radius=5), make_node("c", radius=7)),
            edges=(Edge(upstream="a", downstream="b"), Edge(upstream="a", downstream="c")),
        ),
    )


def keys_for(project: Project, replicate: Replicate | None) -> dict[str, str]:
    """Every node's key, walked by hand.

    The walk is written out here rather than imported because `cache_key`
    deliberately carries no traversal: ordering a graph is `dag.py`'s, and
    `Dag.node_keys` is a step of its own. Three nodes in a known shape make the
    hand-walk shorter than the fixture that would replace it.
    """

    def key(node_id: str, upstream: tuple[tuple[str | None, str], ...]) -> str:
        return node_key(
            project.pipeline.node(node_id), spec=SPEC, upstream=upstream, replicate=replicate
        )

    keys = {"a": key("a", ROOT)}
    keys["b"] = key("b", sole(keys["a"]))
    keys["c"] = key("c", sole(keys["a"]))
    return keys


class TestIsolation:
    def test_editing_one_branch_leaves_its_sibling_valid(self) -> None:
        # The reason the key is per node rather than per graph: `b` and `c`
        # share `a`'s key and nothing else, so a parameter edit on `b` has no
        # path to `c`. A key that folded in anything project-wide — the graph's
        # whole parameter set, a document revision — would pass every other test
        # in this file and fail this one by invalidating the eleven arenas
        # nobody touched.
        arena = Replicate(name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        edited = project.with_param_edit("b", arena.replicate_id, {"radius": 11})
        after = keys_for(edited, edited.replicate(arena.replicate_id))

        assert after["b"] != before["b"]
        assert after["a"] == before["a"]
        assert after["c"] == before["c"]

    def test_an_edit_to_an_ancestor_moves_every_key_below_it(self) -> None:
        # The complement of the case above, and the direction that fails
        # silently: `b` and `c` are computed from `a`'s output, so an edit to
        # `a` that left their keys standing would serve frames blurred at the
        # old radius for the rest of the store's life. Isolation alone does not
        # get this — a `node_key` that ignored its `upstream` argument passes
        # every equality the sibling case asserts
        # (`findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md`),
        # and so does the layout pin, which certifies that a position named
        # `upstream` exists and never what fills it.
        arena = Replicate(name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        edited = project.with_param_edit("a", arena.replicate_id, {"radius": 11})
        after = keys_for(edited, edited.replicate(arena.replicate_id))

        assert after["a"] != before["a"]
        assert after["b"] != before["b"]
        assert after["c"] != before["c"]

    def test_a_pinned_replicate_ignores_the_default_moving_under_it(self) -> None:
        # The failure this closes is silent. `with_param_edit` moves
        # `Node.params` to the last configured value on *every* edit, so a key
        # built from the node's own dict would change for all twelve arenas
        # each time one of them was adjusted — including for an arena that pins
        # the parameter and never reads the default. Hashing `resolved_params`
        # is what makes the second edit below invisible to the first arena.
        pinned = Replicate(name="Replicate 1")
        following = Replicate(name="Replicate 2")
        project = make_project(pinned, following).with_param_edit(
            "a", pinned.replicate_id, {"radius": 9}
        )
        before = keys_for(project, project.replicate(pinned.replicate_id))

        moved = project.with_param_edit("a", following.replicate_id, {"radius": 5})

        assert keys_for(moved, moved.replicate(pinned.replicate_id))["a"] == before["a"]
        assert keys_for(moved, moved.replicate(following.replicate_id))["a"] != before["a"]

    def test_the_region_separates_two_otherwise_identical_replicates(self) -> None:
        # Two arenas with the same settings are the same computation over
        # different pixels, and in schema v1 nothing special says so: the
        # geometry is the crop node's `region` parameter, deviated per replicate
        # like a threshold or a radius, so it reaches the digest through
        # `resolved_params` (`adr/detector-is-a-node.md`). v2 carried the box on
        # the replicate and folded it into the source key instead, which is the
        # special case this arrangement removed.
        node = Node(node_id="a", tool_id="crop", version="1.0.0", params={"region": (0, 0, 96, 96)})
        left = Replicate(name="Replicate 1").with_override("a", {"region": (0, 0, 64, 64)})
        right = Replicate(name="Replicate 2").with_override("a", {"region": (64, 0, 64, 64)})

        def key(replicate: Replicate | None) -> str:
            return node_key(node, spec=CROP_SPEC, upstream=ROOT, replicate=replicate)

        assert resolved_params(node, left) != resolved_params(node, right)
        assert key(left) != key(right)
        # The baseline is a third computation, not a synonym for the first: a
        # project with no fan-out runs the node's own parameters, which here is
        # the whole frame rather than either arena.
        assert key(None) != key(left)

    def test_turning_a_checkpoint_off_moves_no_key(self) -> None:
        # `checkpoints` is on `Project` precisely so this holds: whether a
        # node's output is also written to the project folder changes where a
        # result lives and never what it is, so an HPC handoff that empties the
        # list must not invalidate a single entry. The failure this closes is
        # not a wrong frame but a silent one — every node recomputing from
        # scratch on the cluster, which reads as the store being cold rather
        # than as the field being hashed.
        arena = Replicate(name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        checkpointed = project.model_copy(update={"checkpoints": ("b",)})

        assert checkpointed.checkpoints == ("b",)
        assert keys_for(checkpointed, checkpointed.replicate(arena.replicate_id)) == before

    def test_a_replicate_rename_moves_no_key(self) -> None:
        # What separates two replicates is what they resolve their parameters
        # to, so neither the display name nor `replicate_id` may reach the
        # digest — `Replicate` carries a generated id exactly so that "a rename
        # must not invalidate an entry keyed on it", and twelve arenas retyped
        # after a run is the cost of getting this wrong. The layout pin cannot
        # state it: it says `upstream` is the second position and not that the
        # position holds an upstream key and nothing else, which is why
        # `f"{upstream}{replicate.name}"` passed every other case in this file.
        arena = Replicate(name="Replicate 1")
        project = make_project(arena).with_param_edit("a", arena.replicate_id, {"radius": 9})
        configured = project.replicate(arena.replicate_id)
        before = keys_for(project, configured)

        assert keys_for(project, configured.renamed("Dish B")) == before
        # And identity itself is out, not merely stable under renaming: a second
        # replicate with its own `replicate_id` that resolves to the same
        # parameters over the same pixels *is* the same computation.
        twin = Replicate(name="Replicate 2", overrides=dict(configured.overrides))
        assert twin.replicate_id != configured.replicate_id
        assert keys_for(project, twin) == before

    def test_a_presentation_edit_moves_no_key(self) -> None:
        # Nothing else asserts that the non-identity side of the *spec* stays
        # out of the digest. It passes on day one for a structural reason —
        # `node_key` never reaches `caption`, `primary_params`, or `summary` —
        # so this is a tripwire on a whole `ToolSpec` being handed to a key
        # function, against the day somebody keys on a caption. Not a discovery.
        #
        # Scoped to presentation and not to every unhashed field, deliberately.
        # `deterministic`, `stateful` and `mode` are execution, they feed cache
        # policy, and moving any of them makes the call raise rather than return
        # an unchanged key — a sweep over all non-identity fields would fail on
        # those three and the repair would be to weaken the assertion.
        node = make_node("a", radius=3)
        keyed = node_key(node, spec=SPEC, upstream=ROOT)
        # The next presentation field is covered by the row that declares it:
        # the substitutes are checked against `SPEC_CHANNELS` rather than
        # against a typed list of names, so declaring one without a value here
        # fails instead of silently going untested. Values stay legal —
        # `primary_params` and `param_stereotypes` are both checked against
        # `params_model`, and the stereotype map has to stay total.
        substitutes: dict[str, object] = {
            "caption": (CaptionPart(label="radius", param="radius"),),
            "param_value_labels": {"radius": {"3": "three pixels"}},
            "param_stereotypes": {
                "radius": ParamStereotype.SCALAR_RANGE,
                "sigma": ParamStereotype.SCALAR_RANGE,
                "separable": ParamStereotype.ENUM,
            },
            "primary_params": ("radius",),
            "summary": "Blurs, described differently.",
            "guidance": "Turn the radius up until the speckle stops moving.",
            "param_axes": {"band": AxisRelation.INPUT_VALUES},
        }
        presentation = {n for n, c in SPEC_CHANNELS.items() if c is Channel.PRESENTATION}
        assert set(substitutes) == presentation

        # `param_axes` is the one row that cannot be substituted onto `SPEC` —
        # see `BANDED_SPEC` — so it is asserted against that spec and that
        # spec's own key.
        against = dict.fromkeys(substitutes, SPEC) | {"param_axes": BANDED_SPEC}
        banded_key = node_key(node, spec=BANDED_SPEC, upstream=ROOT)

        for name, value in substitutes.items():
            base = against[name]
            edited = dataclasses.replace(base, **{name: value})
            assert getattr(edited, name) != getattr(base, name)
            expected = keyed if base is SPEC else banded_key
            assert node_key(node, spec=edited, upstream=ROOT) == expected


class TestWiring:
    """What the `upstream` position has to separate now that it is pairs.

    v2 asserted this and 03.3 dropped it for want of a subject — an edge carried
    no port, so `a - b` and `b - a` were not two graphs to tell apart
    (`todo/a-merge-keys-its-inputs-by-port.md`). The subject arrived with the
    port-keyed form of `accepts`, and the claim is unchanged: crossing two
    inputs over is a different computation at that node and the same one
    everywhere else.
    """

    def test_swapping_two_ports_moves_one_key(self) -> None:
        # Walked by hand for `keys_for`'s reason, over the smallest graph the
        # claim needs: one root, two branches off it, and a merge reading both.
        # The branches must key differently — crossing two edges carrying one
        # key would prove nothing, since the pairs would be equal either way.
        def walk(left: str, right: str) -> dict[str, str]:
            keys = {
                "p": node_key(make_node("p", radius=5), spec=SPEC, upstream=ROOT),
                "q": node_key(make_node("q", radius=7), spec=SPEC, upstream=ROOT),
            }
            keys["m"] = node_key(
                Node(node_id="m", tool_id="merge", version="1.0.0"),
                spec=MERGE_SPEC,
                upstream=(("left", keys[left]), ("right", keys[right])),
            )
            return keys

        straight = walk("p", "q")
        crossed = walk("q", "p")

        assert straight["m"] != crossed["m"]
        assert {name: key for name, key in straight.items() if name != "m"} == {
            name: key for name, key in crossed.items() if name != "m"
        }


class TestInputs:
    def test_a_luma_read_and_a_colour_read_of_one_file_are_two_computations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The two are not the same array — a graph that reads no chroma is
        # decoded from the Y plane rather than from a colour conversion of it
        # (`decode/reader.py`) — so a key that carried only the file would serve
        # one to the other. Both facts about the decoder enter here and only
        # here, at the ancestor of every root: which format this run asked for,
        # and who decoded it. The second is patched rather than compared across
        # builds, since there is one decoder on any given machine.
        colour = source_key("footage", decode_format="bgr")

        assert source_key("footage", decode_format="luma") != colour
        assert source_key("other footage", decode_format="bgr") != colour

        monkeypatch.setattr(cache_key, "decoder_identity", lambda: "pretend-decoder")

        assert source_key("footage", decode_format="bgr") != colour

    def test_an_omitted_parameter_and_its_default_are_one_computation(self) -> None:
        # Canonical, not merely deterministic. The params are validated before
        # they are hashed, so the document that spells out every field and the
        # one that relies on defaults key alike — otherwise a project saved by a
        # build that gained a field would recompute everything the previous
        # build had already cached.
        spelled_out = make_node("a", radius=3, sigma=1.0)
        implied = make_node("a")

        assert node_key(spelled_out, spec=SPEC, upstream=ROOT) == node_key(
            implied, spec=SPEC, upstream=ROOT
        )

    def test_invalid_params_never_reach_the_digest(self) -> None:
        # The declared raise. It is the last statement before the hash and it is
        # reachable from a document `Dag.build` accepted, which checks edges and
        # elements and not values. A misspelled key is the case worth pinning:
        # `ParamsBase` forbids extras precisely so it cannot validate, run with
        # the default, and key identically to the run the user meant to vary.
        with pytest.raises(ValidationError, match="radiuz"):
            node_key(make_node("a", radiuz=5), spec=SPEC, upstream=ROOT)
        with pytest.raises(ValidationError, match="radius"):
            node_key(make_node("a", radius="wide"), spec=SPEC, upstream=ROOT)

    def test_refuses_a_key_it_cannot_stand_behind(self) -> None:
        node = make_node("a")
        # No key for a tool that cannot reproduce itself, and the refusal is
        # what propagates: the downstream gets no upstream hash to fold in, so
        # the whole subtree is uncacheable without anything computing that.
        with pytest.raises(NotCacheableError, match="not deterministic"):
            node_key(node, spec=make_spec(deterministic=False), upstream=ROOT)
        with pytest.raises(NotCacheableError, match="epsilon warmup"):
            node_key(
                node,
                spec=make_spec(
                    stateful=True, warmup_kind=WarmupKind.EPSILON, settling_epsilon=0.25
                ),
                upstream=ROOT,
            )
        with pytest.raises(NotCacheableError, match="replaying frames rather than windows"):
            node_key(
                node,
                spec=make_spec(mode=Mode.WINDOWED, stateful=True, warmup_kind=WarmupKind.BOUNDED),
                upstream=ROOT,
            )
        assert is_cacheable(SPEC)
        # And the two the rule now admits, which is 06.5's whole subject: a
        # bounded warmup is keyed whether the tool keeps state
        # (`block_signal`) or a window (`detect`).
        assert is_cacheable(make_spec(stateful=True, warmup_kind=WarmupKind.BOUNDED))
        assert is_cacheable(
            make_spec(
                mode=Mode.WINDOWED,
                warmup_frames=FrameCount(4),
                settling_epsilon=0.0,
                warmup_kind=WarmupKind.BOUNDED,
            )
        )
        # A spec for the wrong tool would key this node's output under another
        # tool's identity, which is the one mistake that produces a confidently
        # wrong cache hit rather than a miss.
        with pytest.raises(ValueError, match="node names"):
            node_key(node, spec=make_spec(version="2.0.0"), upstream=ROOT)


class TestPortability:
    """What a key may not be derived from: where the project file happens to sit.

    `adr/a-users-file-wires-in-like-any-other-input.md`'s exclusion clause, which
    is the half of it nothing asserted — "what is hashed is the resolved file's
    identity, never the rule that found it — neither 'this exact path' nor 'the
    folder of this name beside the project'". Its ordering clause was checked
    when the anchoring landed and this one was not, so a source node's path
    parameter reached the digest as the absolute string `resolve_source.anchored`
    had just made of it
    (`findings/2026.08.10-anchoring-puts-the-project-directory-into-the-node-key.md`).

    Walked through `anchored` and `Dag.build` rather than by hand, unlike the
    rest of this file: the rule being excluded is not something `node_key`'s
    caller passes in, it is a rewrite of the graph one layer up, and a case that
    spelt the two absolute paths itself would assert that `node_key` ignores a
    parameter without asserting that the parameter is the one anchoring writes.

    What this does *not* buy is a project that keeps its cache across a move.
    `source_identity` is `abspath|size|mtime_ns`, so footage carried to a new
    folder is a new identity by design, and it is the identity that the key
    below a source is derived from — the same finding's 2026-08-10 amendment.
    """

    def test_a_projects_location_and_the_key_below_its_source_are_independent(self) -> None:
        # Three spellings of one document, all naming one file: as it is held,
        # anchored on one project directory, anchored on another. The identity is
        # handed over rather than statted, and is the same string in all three,
        # so the only thing varying is where the project file sits — which is the
        # variable the ADR says a key may not see. The failure this names is the
        # one the ADR names: two projects naming one file disagree about it, so
        # the second reviewer to open a shared background recomputes a chain the
        # first already has entries for.
        graph = Pipeline(
            nodes=(
                Node(
                    node_id="s",
                    tool_id="plate",
                    version="1.0.0",
                    params={"pattern": "plate_bg.png"},
                ),
                Node(node_id="b", tool_id="shade", version="1.0.0", params={"radius": 5}),
            ),
            edges=(Edge(upstream="s", downstream="b"),),
        )

        def keys(pipeline: Pipeline) -> dict[str, str]:
            return Dag.build(pipeline, SHELF).node_keys(
                source="footage|1|2", picked={"s": "one file, one identity"}
            )

        held = keys(graph)
        here = keys(anchored(graph, Path("/one/proj"), SHELF))
        there = keys(anchored(graph, Path("/two/elsewhere"), SHELF))

        # Both nodes, before the equality: a source root whose identity the walk
        # cannot find is left unkeyed and takes everything below it with it, and
        # three empty dicts are equal.
        assert set(held) == {"s", "b"}
        assert held == here == there


class TestLayout:
    def test_the_positions_that_enter_a_key_are_pinned(self) -> None:
        # Character-exact, so that adding or reordering a position is visible in
        # a diff rather than in a cache that silently misses. The arity check
        # inside `_digest` is what makes the declaration load-bearing rather
        # than a comment: a sixth part handed to a node digest fails here, at
        # the edit, instead of turning over every entry in the store.
        assert NODE_KEY_POSITIONS == ("flavour", "upstream", "tool_id", "version", "params")
        assert SOURCE_KEY_POSITIONS == ("flavour", "source", "decoder", "format")

        with pytest.raises(AssertionError, match="5 positions"):
            cache_key._digest(NODE_KEY_POSITIONS, "node", "upstream", "blur")
