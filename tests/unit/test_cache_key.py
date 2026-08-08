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

import pytest
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    SourceRef,
    resolved_params,
)
from sieve.core.tool_base import (
    SPEC_CHANNELS,
    ArraySpec,
    CaptionPart,
    Channel,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
    WarmupKind,
)
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


class BlurParams(ParamsBase):
    """Two fields so a test can move one and leave the other inherited."""

    radius: int = 3
    sigma: float = 1.0


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
        },
    }
    fields.update(overrides)
    return ToolSpec(**fields)  # pyright: ignore[reportArgumentType]


SPEC = make_spec()

CROP_SPEC = make_spec(
    tool_id="crop",
    summary="Cuts a region out of the frame.",
    params_model=CropParams,
    param_stereotypes={"region": ParamStereotype.REGION},
)

#: A stand-in for whatever the walk hands a root. Every key in this file is
#: derived from something, because in schema v1 a root's upstream is the source
#: key and there is no node with no input at all.
ROOT = "root-key"


def make_node(node_id: str, **params: object) -> Node:
    return Node(node_id=node_id, tool_id="blur", version="1.0.0", params=dict(params))


def make_project(*replicates: Replicate) -> Project:
    """One root feeding two siblings — the smallest graph the isolation claim needs.

    a ─┬─> b
       └─> c
    """
    return Project(
        source=SourceRef(path="arena.mp4"),
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

    def key(node_id: str, upstream: str) -> str:
        return node_key(
            project.pipeline.node(node_id), spec=SPEC, upstream=upstream, replicate=replicate
        )

    keys = {"a": key("a", ROOT)}
    keys["b"] = key("b", keys["a"])
    keys["c"] = key("c", keys["a"])
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
                "sigma": ParamStereotype.ENUM,
            },
            "primary_params": ("radius",),
            "summary": "Blurs, described differently.",
            "guidance": "Turn the radius up until the speckle stops moving.",
        }
        presentation = {n for n, c in SPEC_CHANNELS.items() if c is Channel.PRESENTATION}
        assert set(substitutes) == presentation

        for name, value in substitutes.items():
            edited = dataclasses.replace(SPEC, **{name: value})
            assert getattr(edited, name) != getattr(SPEC, name)
            assert node_key(node, spec=edited, upstream=ROOT) == keyed


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
