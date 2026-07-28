"""`sieve detect` from a YAML file on disk to intervals, with no Qt in the room.

The claim `docs/todo/headless-detection.md` made is not "detection is correct" —
`tests/unit/test_detection.py` and `tests/unit/test_partial_detector.py` own
that — it is that a *document* can be detected against without a GUI. So these
tests type the command a cluster job would type, and what they can catch is the
seam between a saved `DetectorSettings` and the derivation: a detector that is
absent rendering as zero intervals, a disarmed one rendering as "found nothing",
and a graph whose series node is ambiguous being picked for silently.

Not marked `gui`, deliberately, and that is half the point: before
`sieve.detect` existed there was no import path from a project to intervals
that did not go through `sieve.gui`.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import DetectorSettings, Node, Pipeline, Project

runner = CliRunner()

SERIES_NODE = Node(
    node_id="blocks",
    filter_id="block_signal",
    version="1.0.0",
    params={"block": 16, "fps": 20.0},
)


def _project(
    video: Path, directory: Path, *, detector: DetectorSettings | None, two_sinks: bool = False
) -> Path:
    """Write a block-signal project beside `video` and return its path."""
    nodes: tuple[Node, ...] = (SERIES_NODE,)
    if two_sinks:
        nodes = (*nodes, SERIES_NODE.model_copy(update={"node_id": "blocks2"}))
    project = Project.for_video(video, directory).with_pipeline(Pipeline(nodes=nodes))
    if detector is not None:
        project = project.model_copy(update={"detector": detector})
    path = directory / "arena.sieve.yaml"
    project.save(path)
    return path


def test_an_armed_project_prints_intervals_without_a_gui(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The whole item: a saved threshold becomes intervals from a shell.

    The fixture ramps its blue channel linearly, so change energy is flat and
    a threshold spanning the whole population gates every settled frame — the
    interval count is not the assertion, the fact that one was computed at all
    is. Fails if the derivation is still only reachable through a Qt widget.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        detector=DetectorSettings(count_frac=(0.0, 1.0), window_frames=5, centered=True),
    )

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 0, result.output
    assert "interval" in result.output
    assert "disarmed" not in result.output


def test_an_untuned_project_says_so_rather_than_claiming_nothing(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """`Project.detector` unset is *never tuned*, and must not read as zero.

    The one output a wrong answer would look identical to a right one in:
    "0 intervals" from a project that never had a threshold is a claim about
    the footage that nothing ever made. Rule 6, at the one field that
    documents a `None`.
    """
    project = _project(synthetic_video, tmp_path, detector=None)

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 0, result.output
    assert "no detector" in result.output
    assert "0 intervals" not in result.output


def test_two_sinks_are_refused_rather_than_one_being_picked(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """Which series a detection was taken over is part of what it means.

    Fails if `_series_node` falls back to the last node in topological order,
    which is the plausible implementation and the one that makes the choice
    invisible in the output.
    """
    project = _project(
        synthetic_video, tmp_path, detector=DetectorSettings(count_frac=(0.0, 1.0)), two_sinks=True
    )

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 1
    assert "--node" in result.output
