"""`sieve run` from a YAML file on disk to frames through the shared executor.

An integration test because that is the whole claim: the CLI is the path with
no decode thread of its own, no coalescer, and no display proxy, so if frames
come out of `sieve run` then `pipeline/executor.py` produced them.
`tests/unit/test_executor.py` makes the same claim one layer down, by calling
`execute` directly; this one adds the layer that a user actually types, and the
seams it can catch are the ones between a document on disk and a plan — a
source path resolved against the wrong directory, a span that never reaches the
executor, a replicate set that fans out into one run instead of two.

Every invocation passes `--frames`, and that is schema v1 rather than an
oversight: there is no `Project.clip` (`adr/detector-is-a-node.md`), so the span
is the flag or it is the whole video.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Node, Pipeline, Project, Replicate, Sink

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
