



















from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray
from typer.testing import CliRunner

from sieve.backend.dispatch import Backend
from sieve.cli import run_cmd
from sieve.cli.app import app
from sieve.core.pipeline_model import ClipRange, Node, Pipeline, Project
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoReader
from sieve.filters import discover
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import OffsetFrameSource, ResolvedSource, resolve

runner = CliRunner()

ARENA = ROI(x=16, y=8, width=64, height=48)


CLIP = ClipRange(start=10, end=16)
GRAPH = Pipeline(
    nodes=(Node(node_id="down", filter_id="downsample", version="1.0.0", params={"factor": 2}),)
)


def _project(video: Path, directory: Path, *, replicate: Replicate) -> Path:

    path = directory / "arena.sieve.yaml"
    (
        Project.for_video(video, directory)
        .with_pipeline(GRAPH)
        .with_clip(CLIP)
        .with_replicates((replicate,))
        .save(path)
    )
    return path


def _materialized(video: Path, directory: Path, replicate: Replicate) -> Path:

    project_path = _project(video, directory, replicate=replicate)
    result = runner.invoke(app, ["materialize", str(project_path), "--replicate", "Arena 1"])
    assert result.exit_code == 0, result.output
    return project_path


def _resolved(project: Project, project_dir: Path, replicate: Replicate) -> ResolvedSource:

    discover()
    video = project.source_path(project_dir / "arena.sieve.yaml")
    return resolve(
        project.crops,
        replicate,
        project_dir=project_dir,
        parent=video,
        parent_identity=source_identity(video),
        luma=not Dag.build(project.pipeline).needs_chroma,
        want=CLIP,
    )


def _outputs(project: Project, project_dir: Path, replicate: Replicate) -> list[NDArray[Any]]:






    discover()
    dag = Dag.build(project.pipeline)
    resolved = _resolved(project, project_dir, replicate)
    plan = ExecutionPlan.build(
        dag,
        source=resolved.identity,
        span=CLIP,
        backend=Backend.CPU,
        replicate=replicate,
        pre_cropped=resolved.pre_cropped,
        source_start=resolved.first_index,
    )
    with VideoReader(resolved.path, luma=not dag.needs_chroma) as reader:
        return [np.array(result["down"].data) for result in execute(plan, resolved.wrap(reader))]


class TestTheArtifactIsWhatGetsDecoded:
    def test_the_command_opens_the_crop_and_never_the_parent(
        self, synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:







        opened: list[Path] = []
        original = run_cmd.frame_source

        def recording(video: Path, workers: int | None, *, luma: bool) -> PrefetchFrameSource:
            opened.append(video)
            return original(video, workers, luma=luma)

        monkeypatch.setattr(run_cmd, "frame_source", recording)
        project_path = _materialized(
            synthetic_video, tmp_path, Replicate(replicate_id="a", name="Arena 1", roi=ARENA)
        )

        result = runner.invoke(app, ["run", str(project_path)])

        assert result.exit_code == 0, result.output
        assert opened == [Project.load(project_path).crops[0].resolve(tmp_path)]
        assert synthetic_video not in opened

    def test_a_dry_run_says_which_file_each_replicate_will_read(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:






        project_path = _materialized(
            synthetic_video, tmp_path, Replicate(replicate_id="a", name="Arena 1", roi=ARENA)
        )

        result = runner.invoke(app, ["run", str(project_path), "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "served by" in result.output


class TestTheServedFramesAreTheFramesTheParentWouldHaveGiven:
    def test_frame_for_frame_against_a_parent_served_run(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:








        replicate = Replicate(replicate_id="a", name="Arena 1", roi=ARENA)
        project_path = _project(synthetic_video, tmp_path, replicate=replicate)
        before = _outputs(Project.load(project_path), tmp_path, replicate)

        _materialized(synthetic_video, tmp_path, replicate)
        backed = Project.load(project_path)
        after = _outputs(backed, tmp_path, replicate)



        assert _resolved(backed, tmp_path, replicate).pre_cropped
        assert len(after) == CLIP.frame_count
        for index, (parent_frame, crop_frame) in enumerate(zip(before, after, strict=True)):
            assert np.array_equal(parent_frame, crop_frame), f"frame {CLIP.start + index}"

    def test_the_run_is_rooted_on_the_artifact_alone_and_says_so(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:











        replicate = Replicate(replicate_id="a", name="Arena 1", roi=ARENA)
        project_path = _materialized(synthetic_video, tmp_path, replicate)
        project = Project.load(project_path)
        crop = project.crops[0].resolve(tmp_path)
        discover()
        dag = Dag.build(project.pipeline)

        plan = ExecutionPlan.build(
            dag,
            source=source_identity(crop),
            span=CLIP,
            backend=Backend.CPU,
            replicate=replicate,
            pre_cropped=True,
            source_start=CLIP.start,
        )
        with VideoReader(crop, luma=not dag.needs_chroma) as reader:
            results = list(execute(plan, OffsetFrameSource(reader, CLIP.start)))

        assert [result.index for result in results] == list(range(CLIP.start, CLIP.end))
        assert all(result.source_cropped for result in results), "the honesty flag is set"


class TestAStaleRecordChangesNothing:
    def test_a_moved_box_reproduces_the_pre_artifact_run_keys_included(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:







        replicate = Replicate(replicate_id="a", name="Arena 1", roi=ARENA)
        project_path = _project(synthetic_video, tmp_path, replicate=replicate)
        clean = Project.load(project_path)
        moved = Replicate(replicate_id="a", name="Arena 1", roi=ROI(x=17, y=8, width=64, height=48))

        _materialized(synthetic_video, tmp_path, replicate)
        backed = Project.load(project_path)
        assert backed.crops, "the record was written"

        video = backed.source_path(project_path)
        discover()
        dag = Dag.build(backed.pipeline)
        stale = resolve(
            backed.crops,
            moved,
            project_dir=tmp_path,
            parent=video,
            parent_identity=source_identity(video),
            luma=not dag.needs_chroma,
            want=CLIP,
        )

        assert stale.path == video
        assert not stale.pre_cropped

        assert (
            ExecutionPlan.build(
                Dag.build(clean.pipeline),
                source=stale.identity,
                span=CLIP,
                backend=Backend.CPU,
                replicate=moved,
                pre_cropped=stale.pre_cropped,
                source_start=stale.first_index,
            ).keys
            == ExecutionPlan.build(
                Dag.build(clean.pipeline),
                source=source_identity(video),
                span=CLIP,
                backend=Backend.CPU,
                replicate=moved,
            ).keys
        )
