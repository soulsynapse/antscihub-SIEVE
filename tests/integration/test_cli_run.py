"""`sieve run` from a YAML file on disk to frames through the shared executor.

An integration test because that is the whole claim: the CLI is the path with
no decode thread, no coalescer, and no display proxy, so if frames come out of
`sieve run` then `pipeline/executor.py` produced them. `test_executor_run.py`
makes the same claim one layer down, by calling `execute` directly; this one
adds the layer that a user actually types, and the seams it can catch are the
ones between a document on disk and a plan — a source path resolved against the
wrong directory, a clip that never reaches the span, a replicate set that
fans out into one run instead of two.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline, Project, Sink
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

runner = CliRunner()

#: Two arenas covering the same pixels of the 160x120 fixture. Identical
#: geometry is the point in `test_two_replicates...` and irrelevant everywhere
#: else, so one constant serves both and the tests that do not care say nothing.
ARENA = ROI(x=16, y=8, width=64, height=48)


def _project(video: Path, directory: Path, *, replicates: tuple[Replicate, ...]) -> Path:
    """Write a one-node project beside `video` and return its path."""
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
    """One store spans the whole invocation, so identical work is done once.

    Two replicates cropping the same region resolve to the same key, so the
    second finds every entry the first wrote. Fails if the command builds a
    store per replicate — which would report these same four frames twice and
    silently pay for them twice, the difference being invisible in the results.
    """
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


def test_a_hand_written_crop_node_runs_with_no_replicates(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The crop reaches a run from a YAML file and nothing else.

    What `docs/todo/the-crop-is-a-filter.md` asks for end to end: a project with
    no fan-out — so `plan.roi` is `None` and the executor crops nothing — whose
    graph names the region itself. It is the whole chain the GUI does not touch:
    the params model parsing a nested `roi` out of YAML, discovery putting the
    kernel on the shelf, and `Dag.build` chaining an unconstrained `ArraySpec`
    into the next filter's declared dtypes.
    """
    project = (
        Project.for_video(synthetic_video, tmp_path)
        .with_pipeline(
            Pipeline(
                nodes=(
                    Node(
                        node_id="crop",
                        filter_id="crop",
                        version="1.0.0",
                        params={
                            "roi": {
                                "x": ARENA.x,
                                "y": ARENA.y,
                                "width": ARENA.width,
                                "height": ARENA.height,
                            }
                        },
                    ),
                    Node(node_id="down", filter_id="downsample", version="1.0.0"),
                ),
                edges=(Edge(upstream="crop", downstream="down"),),
            )
        )
        .with_clip(ClipRange(start=10, end=14))
    )
    path = tmp_path / "cropped.sieve.yaml"
    project.save(path)

    result = runner.invoke(app, ["run", str(path)])

    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[0] == (
        "baseline: 4 frames, 8 node outputs computed, 0 from cache"
    )


def test_a_dry_run_never_opens_the_video(
    synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The plan is derivable without a codec, and this is what says so.

    `plan.py` justifies its existence on being buildable where no video can be
    opened; nothing until now could demonstrate it, because every caller held a
    reader anyway. Fails the moment a convenience — a frame count, a resolution
    for a cost estimate — reaches for the container on the dry path.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        replicates=(Replicate(replicate_id="a", name="arena 1", roi=ARENA),),
    )

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError("--dry-run opened the video")

    # Both doors into the container, because there are two now: the reader the
    # run loop decodes through, and the one `span_for` falls back to when a
    # project has no clip. Patching only the first would leave the second able to
    # open a video on the path this test exists to keep closed.
    monkeypatch.setattr("sieve.cli.run_cmd.frame_source", refuse)
    monkeypatch.setattr("sieve.cli.common.VideoReader", refuse)

    result = runner.invoke(app, ["run", str(project), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "frames 10:14" in result.output
    # The key is the half of a dry run that needs the *footage* rather than the
    # container: `source_identity` stats the file, which is why a plan is still
    # a plan for this video and not for any video.
    assert "key " in result.output

    # And the one span it cannot derive without the container it refuses to
    # open — which is the only reason the property above survives a project
    # that has not been clipped yet.
    Project.load(project).with_clip(None).save(project)
    unclipped = runner.invoke(app, ["run", str(project), "--dry-run"])

    assert unclipped.exit_code == 1
    assert "--frames" in unclipped.stderr


def test_declared_outputs_are_refused_rather_than_ignored(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """A run that wrote none of the project's outputs must not report success.

    No sink writer exists yet. Fails if the command grows the obvious
    convenience of running the graph and saying nothing about the outputs it
    did not produce, which is a wrong answer a user has no way to notice.
    """
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
    """`UnresolvedFilterError` reaches the terminal as the thing to install.

    The rejection `dag.py` collects rather than raising on the first miss, which
    only matters if a front end prints it. Fails if the CLI catches `GraphError`
    too broadly and reports a generic failure, or too narrowly and shows a
    traceback.
    """
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
