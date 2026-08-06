"""`sieve preview` over a real video, which is where the seams are.

`test_preview.py` pins the session's arithmetic against a hand-written kernel.
What this adds is everything between a document on disk and that session — the
arena a project has to be read to find, the two writes `--edit` performs through
`with_param_edit`, a real `VideoReader` satisfying `FrameSource`, and a
`MetricBus` hearing keys `pipeline/preview.py` names as string literals because
it may not import the budget table.

The last of those is the one only an integration test can catch: a misspelled
key raises `KeyError` at publish, so the first render against a real bus is
where it surfaces, and that render happens here.
"""

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
    """A two-node chain over one arena, so a suffix and the graph differ."""
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


def _baseline_project(video: Path, directory: Path) -> Path:
    """A two-node whole-frame chain, where no source crop exists to lower."""
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
    )
    path = directory / "baseline.sieve.yaml"
    project.save(path)
    return path


def test_a_repeated_render_reuses_the_store_and_reports_both_budgets(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """One session, two renders, and the second computes nothing.

    The second render is where the store earns its place: every key is
    unchanged, so eight node outputs come back from it and no frame is decoded.
    A command that built a session per render would print these same two lines
    with 0% reuse on both and no other symptom.

    Both budget keys appear because a window render publishes both — and they
    appear at all only if the literals in `preview.py` name budgets the bus
    recognises, which is the assertion no unit test of that module can make.
    They are keys and not the table's human labels because those contain an
    arrow and an en dash, and printing them crashes a cp1252 Windows console.
    """
    project = _project(synthetic_video, tmp_path)

    result = runner.invoke(app, ["preview", str(project), "--repeat", "2"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0].startswith("arena 1: window 10:14, 2 nodes")
    if "lowered by ffmpeg-lowered-gray8" in lines[0]:
        assert lines[1] == (
            "render 1: 4 frames 10:14, 4 node outputs computed, 0 from cache (0% reuse)"
        )
        assert lines[2] == (
            "render 2: 4 frames 10:14, 0 node outputs computed, 4 from cache (100% reuse)"
        )
    else:
        assert lines[1] == (
            "render 1: 4 frames 10:14, 8 node outputs computed, 0 from cache (0% reuse)"
        )
        assert lines[2] == (
            "render 2: 4 frames 10:14, 0 node outputs computed, 8 from cache (100% reuse)"
        )
    assert "slider_to_preview: median" in result.output
    assert "full_preview_render: median" in result.output
    assert result.output.isascii()


def test_an_edit_below_the_root_is_reported_as_a_half_reuse(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The claim the module exists for, at the layer a user types.

    `--edit tail:factor=4` moves the downstream node's parameters, so the
    head's four entries are found and the tail's four are computed. 50% reuse
    of a two-node chain is a suffix; 0% would be the graph.
    """
    project = _baseline_project(synthetic_video, tmp_path)

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
    """A typo in `--edit` is a typo, not a render of the unedited graph.

    Worth its own case because the failure it prevents is silent: an edit
    applied to nothing would render twice, report 100% reuse, and look exactly
    like a preview whose caching worked perfectly.
    """
    project = _project(synthetic_video, tmp_path)

    result = runner.invoke(
        app, ["preview", str(project), "--repeat", "2", "--edit", "middle:factor=4"]
    )

    assert result.exit_code == 1
    assert "middle" in result.stderr
    assert "render 1" not in result.output
