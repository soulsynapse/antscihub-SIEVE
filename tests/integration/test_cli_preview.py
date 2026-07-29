













from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline, Project
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

runner = CliRunner()

ARENA = ROI(x=16, y=8, width=64, height=48)


def _project(video: Path, directory: Path) -> Path:

    project = (
        Project.for_video(video, directory)
        .with_pipeline(
            Pipeline(
                nodes=(
                    Node(
                        node_id="head",
                        filter_id="downsample",
                        version="1.0.0",
                        params={"factor": 2},
                    ),
                    Node(
                        node_id="tail",
                        filter_id="downsample",
                        version="1.0.0",
                        params={"factor": 2},
                    ),
                ),
                edges=(Edge(upstream="head", downstream="tail"),),
            )
        )
        .with_clip(ClipRange(start=10, end=14))
        .with_replicates((Replicate(replicate_id="a", name="arena 1", roi=ARENA),))
    )
    path = directory / "arena.sieve.yaml"
    project.save(path)
    return path


def test_a_repeated_render_reuses_the_store_and_reports_both_budgets(
    synthetic_video: Path, tmp_path: Path
) -> None:













    project = _project(synthetic_video, tmp_path)

    result = runner.invoke(app, ["preview", str(project), "--repeat", "2"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "arena 1: window 10:14, 2 nodes"
    assert lines[1] == "render 1: 4 frames 10:14, 8 node outputs computed, 0 from cache (0% reuse)"
    assert lines[2] == (
        "render 2: 4 frames 10:14, 0 node outputs computed, 8 from cache (100% reuse)"
    )
    assert "slider_to_preview: median" in result.output
    assert "full_preview_render: median" in result.output
    assert result.output.isascii()


def test_an_edit_below_the_root_is_reported_as_a_half_reuse(
    synthetic_video: Path, tmp_path: Path
) -> None:







    project = _project(synthetic_video, tmp_path)

    result = runner.invoke(
        app, ["preview", str(project), "--repeat", "2", "--edit", "tail:factor=4"]
    )

    assert result.exit_code == 0, result.output
    assert (
        "render 2: 4 frames 10:14 after tail:factor=4, 4 node outputs computed, "
        "4 from cache (50% reuse)" in result.output
    )


def test_an_edit_naming_no_node_is_refused_before_anything_decodes(
    synthetic_video: Path, tmp_path: Path
) -> None:






    project = _project(synthetic_video, tmp_path)

    result = runner.invoke(
        app, ["preview", str(project), "--repeat", "2", "--edit", "middle:factor=4"]
    )

    assert result.exit_code == 1
    assert "middle" in result.stderr
    assert "render 1" not in result.output
