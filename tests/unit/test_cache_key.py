"""What a cache key is required to separate, and what it is required to conflate.

Every test here is a way a key stops meaning "this exact result has been
produced before". Two of them cover the direction that is silent when it fails:
a key that conflates two computations serves a wrong frame and the run still
completes. The rest cover the direction that merely costs time — a key that
separates two things that are the same recomputes work it had.
"""

from __future__ import annotations

import dataclasses

import pytest

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import (
    SPEC_CHANNELS,
    ArraySpec,
    CaptionPart,
    Channel,
    CostEstimate,
    ElementRelation,
    FilterSpec,
    Mode,
    ParamsBase,
)
from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceRef
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, WorkUnits
from sieve.pipeline import cache_key
from sieve.pipeline.cache_key import NotCacheableError, is_cacheable, node_key, source_key

COST = CostEstimate(work_per_megapixel=WorkUnits(1.0))


class BlurParams(ParamsBase):
    """Two fields so a test can move one and leave the other inherited."""

    radius: int = 3
    sigma: float = 1.0


def make_spec(**overrides: object) -> FilterSpec:
    fields: dict[str, object] = {
        "filter_id": "blur",
        "version": "1.0.0",
        "summary": "Blur.",
        "params_model": BlurParams,
        "accepts": ArraySpec(),
        "emits": ArraySpec(),
        "element": ElementRelation.PRESERVED,
        "cost": COST,
    }
    fields.update(overrides)
    return FilterSpec(**fields)  # pyright: ignore[reportArgumentType]


SPEC = make_spec()

ARENA = ROI(x=0, y=0, width=64, height=64)


def make_node(node_id: str, **params: object) -> Node:
    return Node(node_id=node_id, filter_id="blur", version="1.0.0", params=dict(params))


def make_project(*replicates: Replicate) -> Project:
    """One root feeding two siblings — the smallest graph guardrail §5 needs.

    a ─┬─> b
       └─> c
    """
    return Project(
        source=SourceRef(path="clip.mp4"),
        replicates=replicates,
        pipeline=Pipeline(
            nodes=(make_node("a", radius=3), make_node("b", radius=5), make_node("c", radius=7)),
            edges=(Edge(upstream="a", downstream="b"), Edge(upstream="a", downstream="c")),
        ),
    )


def keys_for(project: Project, replicate: Replicate | None) -> dict[str, str]:
    """Every node's key, walked by hand.

    The walk is written out here rather than imported because there is nothing
    to import yet: ordering a graph is `dag.py`'s, and `cache_key` deliberately
    does not carry a second traversal. Three nodes in a known shape make the
    hand-walk shorter than the fixture that would replace it.
    """

    def key(node_id: str, upstream: str) -> str:
        return node_key(
            project.pipeline.node(node_id),
            spec=SPEC,
            upstream={"in": upstream},
            backend=Backend.CPU,
            replicate=replicate,
        )

    root = source_key("footage", replicate.roi if replicate is not None else None)
    keys = {"a": key("a", root)}
    keys["b"] = key("b", keys["a"])
    keys["c"] = key("c", keys["a"])
    return keys


class TestIsolation:
    def test_editing_one_branch_leaves_its_sibling_valid(self) -> None:
        # AUTO-GUARDRAILS §5, and the reason the key is per node rather than per
        # graph: `b` and `c` share `a`'s key and nothing else, so a parameter
        # edit on `b` has no path to `c`. A key that folded in anything
        # project-wide — the graph's whole parameter set, a document revision —
        # would pass every other test in this file and fail this one by
        # invalidating the eleven arenas nobody touched.
        arena = Replicate(roi=ARENA, name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        edited = project.with_param_edit("b", arena.replicate_id, {"radius": 11})
        after = keys_for(edited, edited.replicate(arena.replicate_id))

        assert after["b"] != before["b"]
        assert after["a"] == before["a"]
        assert after["c"] == before["c"]

    def test_a_pinned_replicate_ignores_the_default_moving_under_it(self) -> None:
        # The failure this closes is silent. `with_param_edit` moves
        # `Node.params` to the last configured value on *every* edit, so a key
        # built from the node's own dict would change for all twelve arenas
        # each time one of them was adjusted — including for an arena that pins
        # the parameter and never reads the default. Hashing `resolved_params`
        # is what makes the second edit below invisible to the first arena.
        pinned = Replicate(roi=ARENA, name="Replicate 1")
        following = Replicate(roi=ARENA, name="Replicate 2")
        project = make_project(pinned, following).with_param_edit(
            "a", pinned.replicate_id, {"radius": 9}
        )
        before = keys_for(project, project.replicate(pinned.replicate_id))

        moved = project.with_param_edit("a", following.replicate_id, {"radius": 5})

        assert keys_for(moved, moved.replicate(pinned.replicate_id))["a"] == before["a"]
        assert keys_for(moved, moved.replicate(following.replicate_id))["a"] != before["a"]

    def test_the_crop_separates_two_otherwise_identical_replicates(self) -> None:
        # Two arenas with the same parameters are the same computation over
        # different pixels. Nothing on the node says so — the geometry enters at
        # the root, through `source_key`, and reaches `a` only because the
        # source key is its upstream.
        left = Replicate(roi=ROI(x=0, y=0, width=64, height=64), name="Replicate 1")
        right = Replicate(roi=ROI(x=64, y=0, width=64, height=64), name="Replicate 2")
        project = make_project(left, right)

        assert keys_for(project, left)["a"] != keys_for(project, right)["a"]
        assert keys_for(project, left)["a"] != keys_for(project, None)["a"]

    def test_locking_a_replicate_moves_no_key(self) -> None:
        # Rule 7's test applied to `Project.visited`: whether the GUI interposes
        # a dialog in front of a geometry drag changes nothing about what a
        # result *is*, so recording that an arena has been tuned must not cost
        # a single cache entry. The failure this closes is not a wrong frame but
        # a silent one — every arena recomputing from scratch the first time
        # anybody opened it, which reads as the store being cold rather than as
        # the lock being hashed.
        arena = Replicate(roi=ARENA, name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        locked = project.with_visited([arena.replicate_id])

        assert locked.visited == (arena.replicate_id,)
        assert keys_for(locked, locked.replicate(arena.replicate_id)) == before

    def test_a_presentation_edit_moves_no_key(self) -> None:
        # Rule 7's own named gap, generalized: nothing else asserts that the
        # non-identity side of the *spec* stays out of the digest. It passes on
        # day one for a structural reason — `node_key` never reaches `cost`,
        # `primary_params`, or `summary` — so this is a tripwire on a whole
        # `FilterSpec` being handed to a key function, against the day somebody
        # keys on cost. Not a discovery.
        #
        # Scoped to presentation and not to every unhashed field, deliberately.
        # `deterministic` and `stateful` are execution, they feed
        # cache policy, and flipping either makes the call raise rather than
        # return an unchanged key — a sweep over all non-identity fields would
        # fail on those two and the repair would be to weaken the assertion.
        node = make_node("a", radius=3)
        keyed = node_key(node, spec=SPEC, upstream={}, backend=Backend.CPU)
        # The next presentation field is covered by the row that declares it:
        # the substitutes are checked against `SPEC_CHANNELS` rather than
        # against a typed list of names, so declaring one without a value
        # here fails instead of silently going untested. Values stay legal —
        # `primary_params` names are checked against `params_model`.
        substitutes: dict[str, object] = {
            "caption": (CaptionPart(label="radius", param="radius"),),
            "cost": CostEstimate(work_per_megapixel=WorkUnits(2.0)),
            "param_value_labels": {"radius": {"3": "three pixels"}},
            "primary_params": ("radius",),
            "summary": "Blurs, described differently.",
        }
        presentation = {n for n, c in SPEC_CHANNELS.items() if c is Channel.PRESENTATION}
        assert set(substitutes) == presentation

        for name, value in substitutes.items():
            edited = dataclasses.replace(SPEC, **{name: value})
            assert getattr(edited, name) != getattr(SPEC, name)
            assert node_key(node, spec=edited, upstream={}, backend=Backend.CPU) == keyed


class TestInputs:
    def test_backend_identity_leaves_the_key_only_when_the_filter_claims_agreement(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Patched rather than run on two backends: `backend_identity(GPU)`
        # raises without a cupy install, so a machine with no CUDA would skip
        # the assertion that matters. Moving the string under both specs asks
        # the same question — is it in the digest — and answers it on every
        # machine.
        node = make_node("a", radius=3)
        agnostic = make_spec(backend_agnostic=True)
        keyed = node_key(node, spec=SPEC, upstream={}, backend=Backend.CPU)
        unkeyed = node_key(node, spec=agnostic, upstream={}, backend=Backend.CPU)

        def pretend(backend: Backend) -> str:
            return f"pretend-{backend}"

        monkeypatch.setattr(cache_key, "backend_identity", pretend)

        assert node_key(node, spec=SPEC, upstream={}, backend=Backend.CPU) != keyed
        assert node_key(node, spec=agnostic, upstream={}, backend=Backend.CPU) == unkeyed

    def test_which_port_a_stream_arrives_on_is_part_of_the_computation(self) -> None:
        # The silent direction again: `a - b` and `b - a` are fed by the same
        # two upstream keys, and a fold that hashed the keys alone would give
        # the two wirings one entry — one served as the other, plausible frames,
        # no symptom. Binding key to port is what separates them; hashing the
        # pairs *sorted* is what keeps edge-declaration order from mattering,
        # which is the second assertion.
        node = make_node("a", radius=3)
        forward = node_key(
            node, spec=SPEC, upstream={"left": "k1", "right": "k2"}, backend=Backend.CPU
        )
        swapped = node_key(
            node, spec=SPEC, upstream={"left": "k2", "right": "k1"}, backend=Backend.CPU
        )
        reordered = node_key(
            node, spec=SPEC, upstream={"right": "k2", "left": "k1"}, backend=Backend.CPU
        )

        assert forward != swapped
        assert forward == reordered

    def test_an_omitted_parameter_and_its_default_are_one_computation(self) -> None:
        # Canonical, not merely deterministic. The params are validated before
        # they are hashed, so the document that spells out every field and the
        # one that relies on defaults key alike — otherwise a project saved by
        # a build that gained a field would recompute everything the previous
        # build had already cached.
        spelled_out = make_node("a", radius=3, sigma=1.0)
        implied = make_node("a")

        assert node_key(spelled_out, spec=SPEC, upstream={}, backend=Backend.CPU) == node_key(
            implied, spec=SPEC, upstream={}, backend=Backend.CPU
        )

    def test_refuses_a_key_it_cannot_stand_behind(self) -> None:
        node = make_node("a")
        # No key for a filter that cannot reproduce itself, and the refusal is
        # what propagates: the downstream gets no upstream hash to fold in, so
        # the whole subtree is uncacheable without anything computing that.
        with pytest.raises(NotCacheableError, match="not deterministic"):
            node_key(node, spec=make_spec(deterministic=False), upstream={}, backend=Backend.CPU)
        with pytest.raises(NotCacheableError, match="stateful"):
            node_key(node, spec=make_spec(stateful=True), upstream={}, backend=Backend.CPU)
        with pytest.raises(NotCacheableError, match="windowed output"):
            node_key(node, spec=make_spec(mode=Mode.WINDOWED), upstream={}, backend=Backend.CPU)
        assert is_cacheable(SPEC)
        # A spec for the wrong filter would key this node's output under
        # another filter's identity, which is the one mistake that produces a
        # confidently wrong cache hit rather than a miss.
        with pytest.raises(ValueError, match="node names"):
            node_key(node, spec=make_spec(version="2.0.0"), upstream={}, backend=Backend.CPU)
