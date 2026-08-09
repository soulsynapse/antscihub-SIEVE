"""What a run says it needs before it starts, and refuses before it keys anything.

VISION's reviewer loads the project and the files it names, and is told by name
what is missing *up front* rather than discovering it from a run already under
way. The mechanism is a walk over the graph's source roots
(`pipeline/resolve_source.source_files`), called at the top of `sieve run`, and
the three claims it makes are each checked here against the command rather than
against the function — the function answering correctly while nothing calls it
is the state this replaces.

- **The list is derived, never stored.** No field on `Project` repeats the
  external files, so a rewired graph is answered for the moment it is rewired
  and there is nothing to migrate. A project with no source tool owes nothing,
  which is the shape every project had before source tools existed.
- **The same walk pays for the keys.** The identity it resolves for the missing
  file report is the identity `Dag.node_keys` wants, so a source root reaches
  the plan keyed rather than left out of it — and an unkeyed root takes its
  whole subtree with it, recomputing on every run and every preview.
- **Naming is not recognition, except where a hash was recorded.** A file at
  the matching name resolves and the run completes; that is the gap
  `Project.input_hashes` closes, and this is where the closing is called.

The refusals are read off `--dry-run` where the claim is about ordering, because
what a dry run prints is the plan — every node with its key — so a refusal that
printed nothing is a refusal that reached the user before any key existed.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Node, Pipeline, Project, SourceRef
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import validated_params
from sieve.pipeline.resolve_source import source_files
from sieve.tools import discover

runner = CliRunner()

PICK = "background"
SECOND = "other"
DOWN = "shrunk"
SPAN = "0:4"

#: Big enough that `downsample` leaves something, and irrelevant to every
#: assertion below — these cases turn on which files a run names, not on pixels.
WIDTH = HEIGHT = 64


def write_picture(path: Path, fill: int, *, width: int = WIDTH) -> Path:
    """A single-channel picture of one value, at `path`.

    `width` varies so a rewrite of one path is a different file by size as well
    as by content, for `test_source_tool.write_picture`'s reason.
    """
    cv2.imwrite(str(path), np.full((HEIGHT, width), fill, dtype=np.uint8))
    return path


def picker(node_id: str, pattern: str) -> Node:
    return Node(node_id=node_id, tool_id="pick", version="1.0.0", params={"pattern": pattern})


def downsample() -> Node:
    return Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2})


def write_project(video: Path, directory: Path, pipeline: Pipeline, **hashes: Path) -> Path:
    """Save a project over `pipeline` beside `video`, recording `hashes`.

    The keyword form is the document's claim about what a node reads —
    `background=<file>` records `content_hash` for the node called `background`.
    """
    project = Project.for_video(video, directory).with_pipeline(pipeline)
    for node_id, file in hashes.items():
        project = project.with_input_hash(node_id, file)
    path = directory / "arena.sieve.yaml"
    project.save(path)
    return path


def plan_line(output: str, node_id: str) -> str:
    """The `--dry-run` line describing `node_id`."""
    matches = [line for line in output.splitlines() if line.strip().startswith(f"{node_id} ")]
    assert len(matches) == 1, f"expected one {node_id!r} line in {output!r}"
    return matches[0]


def test_every_named_external_input_is_reported_missing_before_execution(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """Two unmounted inputs are two names in one refusal, and nothing decodes.

    The promise is what a reviewer is owed *before* a run, so the count is the
    load-bearing half: a walk that raised at the first root would send someone
    who copied a folder without its two backgrounds around the loop twice, each
    lap paying for whatever the run had already done. `ToolSource.file` refuses
    one file at a time and cannot know there is a second, so collecting is the
    caller's and this is the caller.

    Not a dry run: the claim is that execution never starts, and the frame-count
    line every completed run prints is what its absence is read off.
    """
    project = write_project(
        synthetic_video,
        tmp_path,
        Pipeline(
            nodes=(
                picker(PICK, str(tmp_path / "*_bg.png")),
                picker(SECOND, str(tmp_path / "*_plate.png")),
                downsample(),
            )
        ),
    )

    result = runner.invoke(app, ["run", str(project), "--frames", SPAN])

    assert result.exit_code == 1, result.output
    assert PICK in result.output
    assert SECOND in result.output
    assert "_bg.png" in result.output
    assert "_plate.png" in result.output
    assert "frames," not in result.output, "a run reported work after refusing its inputs"


def test_a_project_with_no_source_tool_owes_nothing(synthetic_video: Path, tmp_path: Path) -> None:
    """A graph with no root that reads its own file names no external input.

    The shape every project had before source tools existed, and the one the
    walk must not charge for: a derived list over a graph with nothing to derive
    is empty, and the run is the run it always was. Fails if the walk asks
    something of every root rather than of the roots the declaration separates
    out (`Dag.source_roots`).
    """
    pipeline = Pipeline(nodes=(downsample(),))
    project = write_project(synthetic_video, tmp_path, pipeline)
    discover()
    dag = Dag.build(pipeline)

    assert source_files(dag, validated_params(dag)) == {}

    result = runner.invoke(app, ["run", str(project), "--frames", SPAN])

    assert result.exit_code == 0, result.output
    assert "baseline: 4 frames" in result.output


def test_the_list_follows_a_rewired_graph_with_nothing_to_migrate(tmp_path: Path) -> None:
    """Rewiring the graph moves the list, and the document holds no copy to move.

    The whole argument for deriving rather than storing: a `Project` field
    repeating the external files would answer the first graph after the second
    was drawn, and would need a migration on the day a node was added. Here
    adding one is adding a node, and `input_hashes` — the only external-input
    field the document has — is untouched by the rewire, because it claims what
    a node reads and not which nodes read.
    """
    first = write_picture(tmp_path / "plate_bg.png", 200)
    second = write_picture(tmp_path / "plate_plate.png", 40, width=WIDTH + 2)
    discover()

    before = Pipeline(nodes=(picker(PICK, str(tmp_path / "*_bg.png")), downsample()))
    after = Pipeline(
        nodes=(
            picker(PICK, str(tmp_path / "*_bg.png")),
            picker(SECOND, str(tmp_path / "*_plate.png")),
            downsample(),
        )
    )
    project = Project(source=SourceRef(path="arena.MP4"), pipeline=before)

    rewired = project.with_pipeline(after)
    listed = source_files(Dag.build(after), validated_params(Dag.build(after)))

    assert source_files(Dag.build(before), validated_params(Dag.build(before))) == {PICK: first}
    assert listed == {PICK: first, SECOND: second}
    assert rewired.input_hashes == project.input_hashes == {}


def test_a_source_root_reaches_the_plan_as_a_picked_identity(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The walk that reports absence is the walk that keys the file.

    A source root handed no identity is left out of `Dag.node_keys`, and an
    unkeyed node takes everything below it with it — so the picker and its
    subtree would recompute on every run of a project whose background never
    moved, which is the tuning loop the product is built around. `--dry-run`
    prints the plan's own key per node, so this is that map read back rather
    than a proxy for it.
    """
    write_picture(tmp_path / "plate_bg.png", 200)
    project = write_project(
        synthetic_video,
        tmp_path,
        Pipeline(nodes=(picker(PICK, str(tmp_path / "*_bg.png")), downsample())),
    )

    result = runner.invoke(app, ["run", str(project), "--frames", SPAN, "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "key " in plan_line(result.output, PICK)
    assert "uncacheable" not in plan_line(result.output, PICK)


def test_a_recorded_input_that_changed_refuses_before_any_key_is_built(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """A file swapped at the matching name is refused, and refused early.

    Naming and absence alone would let this run: the pattern resolves, the file
    is there, and the numbers differ with no symptom. The recorded
    `content_hash` is what makes it visible, and where it is checked is what
    makes the check worth anything — a dry run prints every node's key, so an
    output holding none of them is the refusal arriving before the plan that
    would have been keyed on the wrong file.
    """
    picture = write_picture(tmp_path / "plate_bg.png", 200)
    project = write_project(
        synthetic_video,
        tmp_path,
        Pipeline(nodes=(picker(PICK, str(tmp_path / "*_bg.png")), downsample())),
        background=picture,
    )
    write_picture(picture, 40, width=WIDTH + 2)

    result = runner.invoke(app, ["run", str(project), "--frames", SPAN, "--dry-run"])

    assert result.exit_code == 1, result.output
    assert PICK in result.output
    assert "key " not in result.output, "a plan was described for a run that was refused"
