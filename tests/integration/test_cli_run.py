











from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import ClipRange, Node, Pipeline, Project, Sink
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

runner = CliRunner()




ARENA = ROI(x=16, y=8, width=64, height=48)


def _project(video: Path, directory: Path, *, replicates: tuple[Replicate, ...]) -> Path:

    project = (
        Project.for_video(video, directory)
        .with_pipeline(
            Pipeline(
                nodes=(
                    Node(
                        node_id="down",
                        filter_id="downsample",
                        version="1.0.0",
                        params={"factor": 2},
                    ),
                )
            )
        )
        .with_clip(ClipRange(start=10, end=14))
        .with_replicates(replicates)
    )
    path = directory / "arena.sieve.yaml"
    project.save(path)
    return path


def test_two_replicates_run_and_the_second_reuses_the_first(
    synthetic_video: Path, tmp_path: Path
) -> None:







    project = _project(
        synthetic_video,
        tmp_path,
        replicates=(
            Replicate(replicate_id="a", name="arena 1", roi=ARENA),
            Replicate(replicate_id="b", name="arena 2", roi=ARENA),
        ),
    )

    result = runner.invoke(app, ["run", str(project)])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "arena 1: 4 frames, 4 node outputs computed, 0 from cache"
    assert lines[1] == "arena 2: 4 frames, 0 node outputs computed, 4 from cache"


def test_a_dry_run_never_opens_the_video(
    synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:







    project = _project(
        synthetic_video,
        tmp_path,
        replicates=(Replicate(replicate_id="a", name="arena 1", roi=ARENA),),
    )

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError("--dry-run opened the video")





    monkeypatch.setattr("sieve.cli.run_cmd.frame_source", refuse)
    monkeypatch.setattr("sieve.cli.common.VideoReader", refuse)

    result = runner.invoke(app, ["run", str(project), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "frames 10:14" in result.output



    assert "key " in result.output




    Project.load(project).with_clip(None).save(project)
    unclipped = runner.invoke(app, ["run", str(project), "--dry-run"])

    assert unclipped.exit_code == 1
    assert "--frames" in unclipped.stderr


def test_declared_outputs_are_refused_rather_than_ignored(
    synthetic_video: Path, tmp_path: Path
) -> None:






    project_path = _project(
        synthetic_video,
        tmp_path,
        replicates=(Replicate(replicate_id="a", name="arena 1", roi=ARENA),),
    )
    project = Project.load(project_path)
    project.model_copy(
        update={"outputs": (Sink(sink_id="s", node_id="down", format="parquet", path="out"),)}
    ).save(project_path)

    result = runner.invoke(app, ["run", str(project_path)])

    assert result.exit_code == 1
    assert "parquet" in result.stderr


def test_a_filter_this_build_does_not_have_is_named_before_anything_decodes(
    synthetic_video: Path, tmp_path: Path
) -> None:







    project = (
        Project.for_video(synthetic_video, tmp_path)
        .with_pipeline(
            Pipeline(nodes=(Node(node_id="w", filter_id="wavelet_bands", version="2.1.0"),))
        )
        .with_clip(ClipRange(start=0, end=4))
    )
    path = tmp_path / "missing.sieve.yaml"
    project.save(path)

    result = runner.invoke(app, ["run", str(path)])

    assert result.exit_code == 1
    assert "wavelet_bands" in result.stderr
    assert "2.1.0" in result.stderr
