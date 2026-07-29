







from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    SCHEMA_VERSION,
    ClipRange,
    Edge,
    Node,
    Pipeline,
    Project,
    Sink,
    SourceRef,
    project_path_for,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI


def make_project() -> Project:

    downsample = Node(node_id="n1", filter_id="downsample", version="1.0.0", params={"factor": 4})
    threshold = Node(node_id="n2", filter_id="threshold", version="2.1.0", params={"level": 0.25})
    return Project(
        source=SourceRef(path="../footage/arena.MP4"),
        replicates=(
            Replicate(
                roi=ROI(0, 0, 64, 64),
                name="Replicate 1",
                replicate_id="r1",
                overrides={"n2": {"level": 0.4}},
            ),
            Replicate(roi=ROI(64, 0, 64, 64), name="Replicate 2", replicate_id="r2"),
        ),
        clip=ClipRange(start=120, end=420),
        pipeline=Pipeline(
            nodes=(downsample, threshold),
            edges=(Edge(upstream="n1", downstream="n2"),),
        ),
        checkpoints=("n1",),
        outputs=(
            Sink(sink_id="s1", node_id="n2", format="csv", path="detections", params={"fps": 30}),
        ),
    )


class TestRoundTrip:
    def test_yaml_round_trip_preserves_the_document(self, tmp_path: Path) -> None:




        original = make_project()
        path = tmp_path / "arena.sieve.yaml"
        original.save(path)

        assert Project.load(path) == original

    def test_saving_twice_writes_identical_bytes(self, tmp_path: Path) -> None:



        project = make_project()
        first = tmp_path / "a.sieve.yaml"
        second = tmp_path / "b.sieve.yaml"
        project.save(first)
        Project.load(first).save(second)

        assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")

    def test_relocating_rebases_every_stored_path(self, tmp_path: Path) -> None:




        old_dir = tmp_path / "old"
        new_dir = tmp_path / "nested" / "new"
        project = make_project()

        moved = project.relocated(old_dir, new_dir)

        assert moved.source.resolve(new_dir) == project.source.resolve(old_dir)
        assert moved.outputs[0].resolve(new_dir) == project.outputs[0].resolve(old_dir)


class TestIndependenceFromTheRegistry:
    def test_a_project_naming_an_unknown_filter_still_loads(self) -> None:





        text = """
schema_version: 1
source: {path: arena.MP4}
pipeline:
  nodes:
    - {node_id: n1, filter_id: wavelet_bands, version: 2.1.0, params: {bands: 6}}
  edges: []
"""
        project = Project.from_yaml(text)

        assert project.pipeline.node("n1").filter_id == "wavelet_bands"
        assert project.pipeline.node("n1").params == {"bands": 6}

    def test_a_filter_id_that_cannot_key_a_cache_is_refused(self) -> None:




        with pytest.raises(ValidationError, match="filter_id must match"):
            Node(filter_id="Downsample", version="1.0.0")
        with pytest.raises(ValidationError, match=re.escape("version must be MAJOR.MINOR.PATCH")):
            Node(filter_id="downsample", version="1.0")


class TestPurity:
    def test_gui_state_cannot_be_stashed_in_the_artifact(self) -> None:





        with pytest.raises(ValidationError):
            Project.from_yaml("source: {path: arena.MP4}\nzoom: 2.5\n")
        with pytest.raises(ValidationError):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                "  nodes: [{filter_id: downsample, version: 1.0.0, scroll_x: 40}]\n"
            )

    def test_node_carries_identity_and_nothing_else(self) -> None:






        assert set(Node.model_fields) == {"node_id", "filter_id", "version", "params"}

    def test_a_document_from_a_newer_build_is_refused(self) -> None:



        with pytest.raises(ValidationError, match="schema version"):
            Project.from_yaml(f"schema_version: {SCHEMA_VERSION + 1}\nsource: {{path: a.MP4}}\n")


class TestPorts:
    def test_a_version_1_document_loads_with_every_edge_on_the_default_port(self) -> None:





        text = """
schema_version: 1
source: {path: arena.MP4}
pipeline:
  nodes:
    - {node_id: n1, filter_id: blur, version: 1.0.0}
    - {node_id: n2, filter_id: blur, version: 1.0.0}
  edges:
    - {upstream: n1, downstream: n2}
"""
        project = Project.from_yaml(text)

        assert project.pipeline.edges[0].port == "in"

        assert "port: in" in project.to_yaml()

    def test_two_edges_may_not_feed_one_port(self) -> None:



        nodes = tuple(
            Node(node_id=node_id, filter_id="blur", version="1.0.0") for node_id in ("a", "b", "c")
        )
        with pytest.raises(ValidationError, match="two edges feed"):
            Pipeline(
                nodes=nodes,
                edges=(
                    Edge(upstream="a", downstream="c"),
                    Edge(upstream="b", downstream="c"),
                ),
            )

    def test_one_upstream_may_feed_two_ports_of_one_downstream(self) -> None:




        nodes = tuple(
            Node(node_id=node_id, filter_id="blur", version="1.0.0") for node_id in ("a", "d")
        )
        pipeline = Pipeline(
            nodes=nodes,
            edges=(
                Edge(upstream="a", downstream="d", port="left"),
                Edge(upstream="a", downstream="d", port="right"),
            ),
        )

        assert len(pipeline.edges) == 2

    def test_a_port_that_cannot_survive_yaml_and_shells_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="port must match"):
            Edge(upstream="a", downstream="b", port="Left Channel")


class TestReferentialIntegrity:
    def test_an_edge_naming_no_node_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="edge names no such node"):
            Pipeline(
                nodes=(Node(node_id="n1", filter_id="downsample", version="1.0.0"),),
                edges=(Edge(upstream="n1", downstream="ghost"),),
            )

    def test_replacing_the_graph_catches_stale_checkpoints_and_sinks(self) -> None:




        project = make_project()
        replacement = Pipeline(nodes=(Node(node_id="n9", filter_id="blur", version="1.0.0"),))

        with pytest.raises(ValidationError, match="overrides no such node"):
            project.with_pipeline(replacement)

        following = project.with_param_reset("n2", "r1")
        with pytest.raises(ValidationError, match="checkpoint names no such node"):
            following.with_pipeline(replacement)

        bare = following.model_copy(update={"checkpoints": (), "outputs": ()})
        assert bare.with_pipeline(replacement).pipeline == replacement


class TestPerReplicateDeviation:
    def _project(self) -> Project:

        node = Node(
            node_id="n1", filter_id="threshold", version="1.0.0", params={"level": 0.5, "blur": 3}
        )
        return Project(
            source=SourceRef(path="arena.MP4"),
            replicates=(
                Replicate(roi=ROI(0, 0, 64, 64), name="one", replicate_id="r1"),
                Replicate(roi=ROI(64, 0, 64, 64), name="two", replicate_id="r2"),
            ),
            pipeline=Pipeline(nodes=(node,)),
        )

    def test_untouched_replicates_follow_the_newest_edit(self) -> None:





        project = self._project().with_param_edit("n1", "r1", {"level": 0.9, "blur": 3})

        assert project.params_for("n1", "r2") == {"level": 0.9, "blur": 3}
        assert project.pipeline.node("n1").params == {"level": 0.9, "blur": 3}

        moved = project.with_param_edit("n1", "r2", {"level": 0.2, "blur": 3})



        assert moved.params_for("n1", "r1") == {"level": 0.9, "blur": 3}
        assert moved.params_for("n1", "r2") == {"level": 0.2, "blur": 3}

    def test_a_pinned_parameter_does_not_freeze_its_siblings(self) -> None:





        project = self._project().with_param_edit("n1", "r1", {"level": 0.9, "blur": 3})
        project = project.with_param_edit("n1", "r2", {"level": 0.5, "blur": 7})

        assert project.params_for("n1", "r1") == {"level": 0.9, "blur": 7}
        assert project.replicate("r1").overrides == {"n1": {"level": 0.9}}

    def test_resetting_returns_a_replicate_to_the_default(self) -> None:



        project = self._project().with_param_edit("n1", "r1", {"level": 0.9})
        project = project.with_param_edit("n1", "r2", {"level": 0.1})

        reset = project.with_param_reset("n1", "r1")

        assert reset.replicate("r1").overrides == {}
        assert (
            reset.params_for("n1", "r1")
            == reset.params_for("n1", "r2")
            == project.params_for("n1", "r2")
        )

    def test_an_override_naming_no_node_is_refused(self) -> None:



        with pytest.raises(ValidationError, match="overrides no such node"):
            Project(
                source=SourceRef(path="arena.MP4"),
                replicates=(
                    Replicate(roi=ROI(0, 0, 8, 8), name="one", overrides={"ghost": {"level": 0.5}}),
                ),
            )


class TestEquivalenceGroups:
    def _project(self, count: int = 4) -> Project:

        node = Node(
            node_id="n1", filter_id="threshold", version="1.0.0", params={"level": 0.5, "blur": 3}
        )
        return Project(
            source=SourceRef(path="arena.MP4"),
            replicates=tuple(
                Replicate(roi=ROI(64 * i, 0, 64, 64), name=f"r{i}", replicate_id=f"r{i}")
                for i in range(count)
            ),
            pipeline=Pipeline(nodes=(node,)),
        )

    def test_a_deviating_replicate_renumbers_every_group_below_it(self) -> None:








        project = self._project()
        assert project.equivalence_groups() == (1, 1, 1, 1)

        deviated = project.with_param_edit("n1", "r0", {"level": 0.9})
        assert deviated.equivalence_groups() == (1, 1, 1, 1)

        deviated = deviated.with_param_edit("n1", "r1", {"level": 0.5})




        assert deviated.equivalence_groups() == (1, 2, 2, 2)

    def test_a_deviation_anywhere_in_the_graph_splits_a_group(self) -> None:





        first = Node(node_id="n1", filter_id="downsample", version="1.0.0", params={"factor": 4})
        second = Node(node_id="n2", filter_id="blur", version="1.0.0", params={"radius": 3})
        project = Project(
            source=SourceRef(path="arena.MP4"),
            replicates=(
                Replicate(roi=ROI(0, 0, 64, 64), name="one", replicate_id="r0"),
                Replicate(
                    roi=ROI(64, 0, 64, 64),
                    name="two",
                    replicate_id="r1",
                    overrides={"n2": {"radius": 9}},
                ),
            ),
            pipeline=Pipeline(nodes=(first, second), edges=(Edge(upstream="n1", downstream="n2"),)),
        )

        assert project.equivalence_groups() == (1, 2)

    def test_geometry_and_naming_are_not_what_makes_a_group(self) -> None:





        groups = self._project(count=3).equivalence_groups()

        assert groups == (1, 1, 1)


class TestConventions:
    def test_the_project_file_sits_beside_its_video(self) -> None:




        video = Path("/data/arena/stab_GX010050.MP4")

        assert project_path_for(video) == Path("/data/arena/stab_GX010050.sieve.yaml")

    def test_an_empty_clip_is_refused(self) -> None:



        with pytest.raises(ValidationError, match="at least one frame"):
            ClipRange(start=120, end=120)
