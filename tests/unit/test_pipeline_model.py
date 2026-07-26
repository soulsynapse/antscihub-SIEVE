"""The pipeline artifact: what it must carry, and what it must refuse to.

Each test here stands in for a way the artifact stops being the thing a run is
reproducible from — a document that reads back as something else, one that
needs the filters installed to open, one that lets presentation state in, or one
whose node references have gone stale under an edit.
"""

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
    """A project exercising every field, so a round trip can lose one."""
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
        # The load-bearing claim of the whole module: what comes back is what
        # went in. Every field is populated in the fixture so that a field that
        # silently stops serializing fails here rather than at run time, when
        # the symptom is a run that completes and is wrong.
        original = make_project()
        path = tmp_path / "arena.sieve.yaml"
        original.save(path)

        assert Project.load(path) == original

    def test_saving_twice_writes_identical_bytes(self, tmp_path: Path) -> None:
        # Stability, not merely correctness. A project whose YAML churned on
        # every save would make version control useless for the one file a user
        # most wants a history of, and would do it invisibly.
        project = make_project()
        first = tmp_path / "a.sieve.yaml"
        second = tmp_path / "b.sieve.yaml"
        project.save(first)
        Project.load(first).save(second)

        assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")

    def test_relocating_rebases_every_stored_path(self, tmp_path: Path) -> None:
        # Moving a project folder is how footage reaches a cluster. Both the
        # source and the sink directories have to follow, and a rebase that
        # handled only the source would be found by a run that wrote its
        # outputs into whatever happened to sit beside the new location.
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "nested" / "new"
        project = make_project()

        moved = project.relocated(old_dir, new_dir)

        assert moved.source.resolve(new_dir) == project.source.resolve(old_dir)
        assert moved.outputs[0].resolve(new_dir) == project.outputs[0].resolve(old_dir)


class TestIndependenceFromTheRegistry:
    def test_a_project_naming_an_unknown_filter_still_loads(self) -> None:
        # The reason `filter_id` resolution lives in `pipeline/dag.py` and not
        # here. A project that referenced a filter this build lacks must open —
        # so the user can be told *which* filter to install, and so the GUI can
        # draw a graph it cannot execute. Registry awareness in this layer would
        # turn that into a parse failure naming nothing.
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
        # Not registry awareness — it never asks whether the filter exists —
        # but the same syntactic contract `FilterSpec` applies. An id that
        # depends on case folding to stay itself is one that stops being itself
        # somewhere between a YAML file, a cache key, and a shell argument.
        with pytest.raises(ValidationError, match="filter_id must match"):
            Node(filter_id="Downsample", version="1.0.0")
        with pytest.raises(ValidationError, match=re.escape("version must be MAJOR.MINOR.PATCH")):
            Node(filter_id="downsample", version="1.0")


class TestPurity:
    def test_gui_state_cannot_be_stashed_in_the_artifact(self) -> None:
        # AUTO-GUARDRAILS §2, machine-checked. `extra="forbid"` is what makes
        # the rule cost something to break: a GUI wanting to persist zoom or
        # panel layout has to edit `core/pipeline_model.py` to do it, which is
        # the review the guardrail exists to force. Without this, an unknown key
        # would round-trip out and the artifact would quietly stop being the
        # thing two machines agree about.
        with pytest.raises(ValidationError):
            Project.from_yaml("source: {path: arena.MP4}\nzoom: 2.5\n")
        with pytest.raises(ValidationError):
            Project.from_yaml(
                "source: {path: arena.MP4}\n"
                "pipeline:\n"
                "  nodes: [{filter_id: downsample, version: 1.0.0, scroll_x: 40}]\n"
            )

    def test_node_carries_identity_and_nothing_else(self) -> None:
        # The cache-key line, pinned. Everything on `Node` feeds the key, so a
        # field that does not change the node's output must not appear here —
        # `checkpoints` and `outputs` live on `Project`, keyed by node id, for
        # exactly this reason. This test exists to fail when someone moves one
        # of them onto the node for convenience, because the alternative way to
        # discover it is a cache that misses whenever an output path changes.
        assert set(Node.model_fields) == {"node_id", "filter_id", "version", "params"}

    def test_a_document_from_a_newer_build_is_refused(self) -> None:
        # Refusing beats guessing: a forward-compatible reader that ignored
        # fields it did not understand would run a pipeline that is not the one
        # the document describes, and would report success.
        with pytest.raises(ValidationError, match="schema version"):
            Project.from_yaml(f"schema_version: {SCHEMA_VERSION + 1}\nsource: {{path: a.MP4}}\n")


class TestReferentialIntegrity:
    def test_an_edge_naming_no_node_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="edge names no such node"):
            Pipeline(
                nodes=(Node(node_id="n1", filter_id="downsample", version="1.0.0"),),
                edges=(Edge(upstream="n1", downstream="ghost"),),
            )

    def test_replacing_the_graph_catches_stale_checkpoints_and_sinks(self) -> None:
        # The case a constructor-only check misses. `checkpoints` and `outputs`
        # hold node ids, and swapping the pipeline out is precisely the moment
        # those go stale — a checkpoint on a node that no longer exists is a
        # materialization step the executor cannot schedule.
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
        """Two arenas and one node carrying two parameters."""
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
        # The whole workflow, and the reason for the second write. Configuring
        # arena 1 must leave arena 2 showing arena 1's settings, so twelve
        # arenas are configured once. A `with_param_edit` that stored the
        # override and left `Node.params` alone would pass every other test
        # here and make the user configure all twelve.
        project = self._project().with_param_edit("n1", "r1", {"level": 0.9, "blur": 3})

        assert project.params_for("n1", "r2") == {"level": 0.9, "blur": 3}
        assert project.pipeline.node("n1").params == {"level": 0.9, "blur": 3}

        moved = project.with_param_edit("n1", "r2", {"level": 0.2, "blur": 3})

        # Arena 1 pinned its level and does not follow; arena 2 is now the
        # default anything unconfigured inherits.
        assert moved.params_for("n1", "r1") == {"level": 0.9, "blur": 3}
        assert moved.params_for("n1", "r2") == {"level": 0.2, "blur": 3}

    def test_a_pinned_parameter_does_not_freeze_its_siblings(self) -> None:
        # Sparsity is per key, not per node, and this is what that buys: one
        # dim arena holds its own threshold while still picking up a later
        # change to a blur radius nobody varied. An override that stored the
        # whole submitted parameter set would leave arena 1 on blur 3 forever,
        # silently — the run completes and the arenas are no longer comparable.
        project = self._project().with_param_edit("n1", "r1", {"level": 0.9, "blur": 3})
        project = project.with_param_edit("n1", "r2", {"level": 0.5, "blur": 7})

        assert project.params_for("n1", "r1") == {"level": 0.9, "blur": 7}
        assert project.replicate("r1").overrides == {"n1": {"level": 0.9}}

    def test_resetting_returns_a_replicate_to_the_default(self) -> None:
        # The way back from a pin, and it must not move the default: resetting
        # is not an edit. Without this a parameter set once could only ever be
        # re-pinned, and the replicate would never rejoin its equivalence group.
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
        # Same staleness a checkpoint has, and it survives every save
        # otherwise — a deviation nothing reads, waiting for a new node to be
        # handed the dead id.
        with pytest.raises(ValidationError, match="overrides no such node"):
            Project(
                source=SourceRef(path="arena.MP4"),
                replicates=(
                    Replicate(roi=ROI(0, 0, 8, 8), name="one", overrides={"ghost": {"level": 0.5}}),
                ),
            )


class TestConventions:
    def test_the_project_file_sits_beside_its_video(self) -> None:
        # VISION step 1's folder layout: the project names the child folders its
        # derivatives live in, so it belongs at the root of that tree rather
        # than in a user-global application directory. Copying the folder is
        # then how a project reaches another machine.
        video = Path("/data/arena/stab_GX010050.MP4")

        assert project_path_for(video) == Path("/data/arena/stab_GX010050.sieve.yaml")

    def test_an_empty_clip_is_refused(self) -> None:
        # A zero-frame clip would make the executor's warmup request
        # `[start - warmup, start)`, which decodes a lead-in and discards all
        # of it — a preview that renders nothing and reports no error.
        with pytest.raises(ValidationError, match="at least one frame"):
            ClipRange(start=120, end=120)
