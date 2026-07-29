








from __future__ import annotations

import pytest

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, FilterSpec, ParamsBase
from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceRef
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.pipeline import cache_key
from sieve.pipeline.cache_key import NotCacheableError, node_key, source_key

COST = CostEstimate(seconds_per_megapixel=0.001)


class BlurParams(ParamsBase):


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
    return FilterSpec(**fields)


SPEC = make_spec()

ARENA = ROI(x=0, y=0, width=64, height=64)


def make_node(node_id: str, **params: object) -> Node:
    return Node(node_id=node_id, filter_id="blur", version="1.0.0", params=dict(params))


def make_project(*replicates: Replicate) -> Project:





    return Project(
        source=SourceRef(path="clip.mp4"),
        replicates=replicates,
        pipeline=Pipeline(
            nodes=(make_node("a", radius=3), make_node("b", radius=5), make_node("c", radius=7)),
            edges=(Edge(upstream="a", downstream="b"), Edge(upstream="a", downstream="c")),
        ),
    )


def keys_for(project: Project, replicate: Replicate | None) -> dict[str, str]:








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






        arena = Replicate(roi=ARENA, name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        edited = project.with_param_edit("b", arena.replicate_id, {"radius": 11})
        after = keys_for(edited, edited.replicate(arena.replicate_id))

        assert after["b"] != before["b"]
        assert after["a"] == before["a"]
        assert after["c"] == before["c"]

    def test_a_pinned_replicate_ignores_the_default_moving_under_it(self) -> None:






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




        left = Replicate(roi=ROI(x=0, y=0, width=64, height=64), name="Replicate 1")
        right = Replicate(roi=ROI(x=64, y=0, width=64, height=64), name="Replicate 2")
        project = make_project(left, right)

        assert keys_for(project, left)["a"] != keys_for(project, right)["a"]
        assert keys_for(project, left)["a"] != keys_for(project, None)["a"]

    def test_locking_a_replicate_moves_no_key(self) -> None:







        arena = Replicate(roi=ARENA, name="Replicate 1")
        project = make_project(arena)
        before = keys_for(project, arena)

        locked = project.with_visited([arena.replicate_id])

        assert locked.visited == (arena.replicate_id,)
        assert keys_for(locked, locked.replicate(arena.replicate_id)) == before


class TestInputs:
    def test_backend_identity_leaves_the_key_only_when_the_filter_claims_agreement(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:





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





        spelled_out = make_node("a", radius=3, sigma=1.0)
        implied = make_node("a")

        assert node_key(spelled_out, spec=SPEC, upstream={}, backend=Backend.CPU) == node_key(
            implied, spec=SPEC, upstream={}, backend=Backend.CPU
        )

    def test_refuses_a_key_it_cannot_stand_behind(self) -> None:
        node = make_node("a")



        with pytest.raises(NotCacheableError, match="not deterministic"):
            node_key(node, spec=make_spec(deterministic=False), upstream={}, backend=Backend.CPU)



        with pytest.raises(ValueError, match="node names"):
            node_key(node, spec=make_spec(version="2.0.0"), upstream={}, backend=Backend.CPU)
