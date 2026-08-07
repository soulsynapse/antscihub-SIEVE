"""`sieve run` from a YAML file on disk to frames through the shared executor.

An integration test because that is the whole claim: the CLI is the path with
no decode thread of its own, no coalescer, and no display proxy, so if frames
come out of `sieve run` then `pipeline/executor.py` produced them.
`tests/unit/test_executor.py` makes the same claim one layer down, by calling
`execute` directly; this one adds the layer that a user actually types, and the
seams it can catch are the ones between a document on disk and a plan — a
source path resolved against the wrong directory, a span that never reaches the
executor, a replicate set that fans out into one run instead of two.

Schema v1 records no clip of its own (`adr/detector-is-a-node.md`), so the span
is the flag or it is the whole video, and both halves of that sentence are
invocations here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Node, Pipeline, Project, Replicate, Sink
from tests.conftest import FIXTURE_FRAMES

runner = CliRunner()


def _project(video: Path, directory: Path, *, replicates: tuple[Replicate, ...] = ()) -> Path:
    """Write a one-node project beside `video` and return its path."""
    project = (
        Project.for_video(video, directory)
        .with_pipeline(
            Pipeline(
                nodes=(
                    Node(
                        node_id="down",
                        tool_id="downsample",
                        version="1.0.0",
                        params={"factor": 2},
                    ),
                )
            )
        )
        .with_replicates(replicates)
    )
    path = directory / "arena.sieve.yaml"
    project.save(path)
    return path


def test_two_replicates_run_and_the_second_reuses_the_first(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """One store spans the whole invocation, so identical work is done once.

    Two replicates that override nothing resolve to the same params and
    therefore to the same keys, so the second finds every entry the first wrote.
    Fails if the command builds a store per replicate — which would report these
    same four frames twice and silently pay for them twice, the difference being
    invisible in the results.

    Where v2's version of this case cropped both arenas to one region to make
    the keys coincide, schema v1 has no `Replicate.roi` to set: a replicate
    deviates through `overrides` or not at all, and two that deviate in nothing
    are the two-replicates-one-computation case in its plainest form.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        replicates=(Replicate(name="arena 1"), Replicate(name="arena 2")),
    )

    result = runner.invoke(app, ["run", str(project), "--frames", "10:14"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "arena 1: 4 frames, 4 node outputs computed, 0 from cache"
    assert lines[1] == "arena 2: 4 frames, 0 node outputs computed, 4 from cache"


def test_a_project_with_no_replicates_runs_its_graph_once(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """No fan-out is one run, not zero, and it says `baseline`.

    A replicate is a deviation from the graph, so a project holding none has a
    graph to run all the same — `_targets` spells that `(None,)` and `plan.py`
    already carries `replicate=None`. Fails if the target list is taken straight
    from `project.replicates`, which for this project runs nothing, prints
    nothing, and still exits 0: a user's whole run silently doing nothing.
    """
    project = _project(synthetic_video, tmp_path)

    result = runner.invoke(app, ["run", str(project), "--frames", "10:14"])

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "baseline: 4 frames, 4 node outputs computed, 0 from cache"
    ]


def test_a_run_with_no_frames_covers_the_whole_video(synthetic_video: Path, tmp_path: Path) -> None:
    """The other half of "the flag or the whole video".

    `span_for` falls back to the container's frame count, and every other case
    here passes `--frames`, so the fallback's only reader of record is this one.
    Fails for any fallback that is a fixed or truncated range rather than the
    footage's own length — which decodes a prefix, reports success over it, and
    leaves the rest of the video unprocessed without saying so.
    """
    project = _project(synthetic_video, tmp_path, replicates=(Replicate(name="arena 1"),))

    result = runner.invoke(app, ["run", str(project)])

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        f"arena 1: {FIXTURE_FRAMES} frames, {FIXTURE_FRAMES} node outputs computed, 0 from cache"
    ]


def test_a_dry_run_never_opens_the_video(
    synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The plan is derivable without a codec, and this is what says so.

    `plan.py` justifies its existence on being buildable where no video can be
    opened; nothing until now could demonstrate it, because every caller held a
    reader anyway. Fails the moment a convenience — a frame count, a resolution
    for a cost estimate — reaches for the container on the dry path.
    """
    project = _project(synthetic_video, tmp_path, replicates=(Replicate(name="arena 1"),))

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError("--dry-run opened the video")

    # Both doors into the container: the reader the run loop decodes through,
    # and the one the span falls back to when no `--frames` was given. Patching
    # only the first would leave the second able to open a video on the path
    # this test exists to keep closed.
    monkeypatch.setattr("sieve.cli.run_cmd.frame_source", refuse)
    monkeypatch.setattr("sieve.cli.run_cmd.VideoReader", refuse)

    result = runner.invoke(app, ["run", str(project), "--frames", "10:14", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "frames 10:14" in result.output
    # The key is the half of a dry run that needs the *footage* rather than the
    # container: `source_identity` stats the file, which is why a plan is still
    # a plan for this video and not for any video.
    assert "key " in result.output

    # And the one span it cannot derive without the container it refuses to
    # open. Schema v1 records no clip, so this is every project that has not
    # been given a span on the command line.
    unspanned = runner.invoke(app, ["run", str(project), "--dry-run"])

    assert unspanned.exit_code == 1
    assert "--frames" in unspanned.stderr


def test_declared_outputs_are_refused_rather_than_ignored(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """A run that wrote none of the project's outputs must not report success.

    No sink writer exists yet — `PLAN.md` builds them in Phase 5. Fails if the
    command grows the obvious convenience of running the graph and saying
    nothing about the outputs it did not produce, which is a wrong answer a user
    has no way to notice.
    """
    project_path = _project(synthetic_video, tmp_path, replicates=(Replicate(name="arena 1"),))
    project = Project.load(project_path)
    project.model_copy(
        update={"outputs": (Sink(sink_id="s", node_id="down", format="parquet", path="out"),)}
    ).save(project_path)

    result = runner.invoke(app, ["run", str(project_path), "--frames", "10:14"])

    assert result.exit_code == 1
    assert "parquet" in result.stderr


def test_a_tool_this_build_does_not_have_is_named_before_anything_decodes(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """`UnresolvedToolError` reaches the terminal as the thing to install.

    The rejection `dag.py` collects rather than raising on the first miss, which
    only matters if a front end prints it. Fails if the CLI catches `GraphError`
    too broadly and reports a generic failure, or too narrowly and shows a
    traceback.
    """
    project = Project.for_video(synthetic_video, tmp_path).with_pipeline(
        Pipeline(nodes=(Node(node_id="w", tool_id="wavelet_bands", version="2.1.0"),))
    )
    path = tmp_path / "missing.sieve.yaml"
    project.save(path)

    result = runner.invoke(app, ["run", str(path), "--frames", "0:4"])

    assert result.exit_code == 1
    assert "wavelet_bands" in result.stderr
    assert "2.1.0" in result.stderr
