"""A checkpointed run leaves files, and changes nothing else about the run.

The two claims here are the ones the schema fields were shaped for, and neither
is about the file format. `Project.checkpoints` sits on the project rather than
on a node so that turning it on cannot move a cache key; that is documented in
three places and until now nothing checked it. The other claim is its
consequence: if a checkpoint changed a single computed value, the whole reason
for the placement would be gone and the handoff — a cluster run with the
checkpoints emptied (VISION step 6) — would stop being the same run.

The format's own claims are cheap to state and are stated here too, because they
are what makes this phase's gate a file comparison rather than an assertion about
a count: the file opens with `np.load` and nothing else, and the manifest beside
it names each node's cache key and the source span covered.

Driven through `sieve run` rather than through `execute`, deliberately. A
checkpoint is a property of a *run of a project*, and what would plausibly break
— a writer fed the frames of the wrong replicate, or fed the span the user asked
for rather than the one the plan answered for — lives between the document and
the loop, which is exactly the seam a direct call to `execute` skips.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from numpy.typing import NDArray
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Replicate, SourceSpan
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.storage.checkpoint_writer import BASELINE_DIR, MANIFEST_NAME, checkpoints_dir
from sieve.tools import discover
from tests.conftest import FIXTURE_FRAMES

runner = CliRunner()

PROJECT_NAME = "arena.sieve.yaml"
CUT = "cut"
DOWN = "down"
SPAN = SourceSpan(start=10, end=16)

#: Two nodes, so that checkpointing one of them is a real selection rather than a
#: synonym for "the graph". The crop is also what makes two replicates genuinely
#: different computations, since a replicate deviates through the crop node's
#: region and nothing else (`adr/detector-is-a-node.md`).
GRAPH = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN),),
)


def _replicate(
    name: str, replicate_id: str, x: int, width: int = 64, height: int = 48
) -> Replicate:
    pinned = {"x": x, "y": 9, "width": width, "height": height}
    return Replicate(name=name, replicate_id=replicate_id).with_override(CUT, {"region": pinned})


def _project(
    video: Path,
    directory: Path,
    *,
    checkpoints: tuple[str, ...] = (),
    replicates: tuple[Replicate, ...] = (),
    pipeline: Pipeline = GRAPH,
) -> Path:
    """Write the project into `directory` and return its path.

    `checkpoints` is set through `model_copy` and revalidated because `Project`
    has no `with_checkpoints`: nothing in `src/` edits the list yet, and adding a
    method for a test to call would be the declaration-without-a-consumer this
    phase exists to avoid.
    """
    directory.mkdir(parents=True, exist_ok=True)
    project = (
        Project.for_video(video, directory)
        .with_pipeline(pipeline)
        .with_replicates(replicates)
        .model_copy(update={"checkpoints": checkpoints})
    )
    path = directory / PROJECT_NAME
    Project.model_validate(project).save(path)
    return path


def _run(project_path: Path, span: SourceSpan = SPAN) -> str:
    result = runner.invoke(
        app, ["run", str(project_path), "--frames", f"{span.start}:{span.end}"]
    )
    assert result.exit_code == 0, result.output
    return result.output


def _plan(project_path: Path, replicate: Replicate | None) -> ExecutionPlan:
    """The plan `sieve run` builds for this document, rebuilt outside it."""
    discover()
    project = Project.load(project_path)
    return ExecutionPlan.build(
        Dag.build(project.pipeline),
        source=source_identity(project.source_path(project_path)),
        span=SPAN,
        replicate=replicate,
    )


def _computed(project_path: Path, node_id: str, replicate: Replicate | None) -> list[NDArray[Any]]:
    """What a run of this document produces in memory, frame by frame."""
    plan = _plan(project_path, replicate)
    video = Project.load(project_path).source_path(project_path)
    with VideoReader(video, luma=plan.luma) as reader:
        return [np.array(result[node_id].data) for result in execute(plan, reader)]


class TestTheCheckpointListIsNotAnInput:
    def test_changing_it_between_two_runs_moves_no_cache_key(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The reason `checkpoints` is on `Project` and not on `Node`.

        A cluster handoff empties the list, because the node with the memory to
        skip persisting should; if that moved a key, every entry the tuning
        session earned would be recomputed there and the two runs would stop
        being one run. Fails for any derivation that folds the list — or its
        length, or its emptiness — into `source_key` or a node digest.
        """
        target = _replicate("Arena 1", "a", x=17)
        plain = _project(synthetic_video, tmp_path / "plain", replicates=(target,))
        kept = _project(
            synthetic_video, tmp_path / "kept", checkpoints=(CUT, DOWN), replicates=(target,)
        )
        assert Project.load(plain).checkpoints != Project.load(kept).checkpoints

        keys = [_plan(path, target).keys for path in (plain, kept)]

        assert keys[0] == keys[1]
        assert set(keys[0]) == {CUT, DOWN}, "a graph with no keys would pass this vacuously"


class TestAPersistedRunComputesWhatAnUnpersistedOneDoes:
    def test_the_written_stack_is_frame_for_frame_what_the_plain_run_produced(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The load-bearing one: persistence changes where, never what.

        Compared against a run of the *same document with the field absent*, so
        the comparison cannot be satisfied by both sides sharing a mistake the
        checkpoint introduced. Fails if the writer files a frame under the wrong
        row — the fixture's per-frame ramp is what turns an off-by-one into a
        mismatch rather than into two equal-looking arrays.
        """
        target = _replicate("Arena 1", "a", x=17)
        expected = _computed(
            _project(synthetic_video, tmp_path / "plain", replicates=(target,)), DOWN, target
        )
        kept = tmp_path / "kept"
        project_path = _project(
            synthetic_video, kept, checkpoints=(DOWN,), replicates=(target,)
        )

        _run(project_path)

        written = np.load(checkpoints_dir(synthetic_video, kept) / "a" / f"{DOWN}.npy")
        assert written.shape == (SPAN.frame_count, *expected[0].shape)
        for row, frame in enumerate(expected):
            assert np.array_equal(written[row], frame), f"frame {SPAN.start + row}"

    def test_each_replicate_writes_its_own_file_under_its_own_id(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Two arenas, two folders, and the geometry tells them apart.

        Both are named the same on purpose. Fails for a writer keyed on the
        display name, and for one that reused a single file across the fan-out —
        which would report success twice and leave the last replicate's result
        standing for all of them.

        Distinguished by *size* rather than by content, which is a property of
        the fixture and not a weakening: every frame it holds is a uniform field,
        so two boxes of one size anywhere in it are literally the same pixels and
        a content comparison would be asserting nothing. Two sizes make the two
        files different objects that no single write could satisfy.
        """
        first = _replicate("Arena", "aaa", x=17, width=64, height=48)
        second = _replicate("Arena", "bbb", x=40, width=32, height=24)
        project_path = _project(
            synthetic_video, tmp_path, checkpoints=(DOWN,), replicates=(first, second)
        )

        _run(project_path)

        base = checkpoints_dir(synthetic_video, tmp_path)
        assert np.load(base / "aaa" / f"{DOWN}.npy").shape == (SPAN.frame_count, 24, 32)
        assert np.load(base / "bbb" / f"{DOWN}.npy").shape == (SPAN.frame_count, 12, 16)

    def test_a_project_with_no_fan_out_writes_the_baseline_folder(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """`None` is a target, not an absence — `_targets` already says so.

        Fails for a writer that derives its folder from `replicate.replicate_id`
        without answering the no-replicate case, which is every project before
        the first arena is drawn. The reported line is asserted here rather than
        in its own case: a sink record nothing prints is a return value with no
        consumer, which is the thing this phase refuses to build.
        """
        project_path = _project(synthetic_video, tmp_path, checkpoints=(DOWN,))

        output = _run(project_path)

        directory = checkpoints_dir(synthetic_video, tmp_path) / BASELINE_DIR
        assert np.load(directory / f"{DOWN}.npy").shape[0] == SPAN.frame_count
        assert f"checkpointed {DOWN} as npy in synthetic.checkpoints" in output


class TestTheManifestSaysWhatTheFilesAre:
    def test_it_names_each_node_its_key_and_the_span_covered(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The two fields the item asks for, and the one that must not be a path.

        The key is recorded beside the file rather than in its name: a checkpoint
        may never enter a key (`cache_key.py`), so a folder named by one would
        make the location depend on the thing forbidden to depend on it, while a
        reader still needs to know what the file was computed under. Fails for a
        manifest that records the span the user asked for rather than the span
        the plan answered for, and for one whose shape does not describe the file
        beside it.
        """
        target = _replicate("Arena 1", "a", x=17)
        project_path = _project(
            synthetic_video, tmp_path, checkpoints=(CUT, DOWN), replicates=(target,)
        )

        _run(project_path)

        directory = checkpoints_dir(synthetic_video, tmp_path) / "a"
        manifest = yaml.safe_load((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
        assert manifest["span"] == {"start": SPAN.start, "end": SPAN.end}
        assert manifest["replicate_id"] == "a"
        assert manifest["replicate_name"] == "Arena 1"

        plan = _plan(project_path, target)
        entries = {entry["node_id"]: entry for entry in manifest["entries"]}
        assert set(entries) == {CUT, DOWN}
        for node_id, entry in entries.items():
            assert entry["key"] == plan.key(node_id)
            assert entry["format"] == "npy"
            assert list(np.load(directory / entry["file"]).shape) == entry["shape"]


class TestAnUnfinishedRunLeavesNothingToBelieve:
    def test_a_span_the_footage_cannot_supply_writes_no_checkpoint(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The part-file discipline, and why a `.npy` needs one.

        The array is sized before the second frame exists, so a run that stops
        short leaves a file whose header is right and whose tail is the zeros it
        was created as — indistinguishable, on read, from a stretch of black
        footage. Fails for any writer that opens the destination name directly.
        """
        project_path = _project(synthetic_video, tmp_path, checkpoints=(DOWN,))

        result = runner.invoke(
            app,
            ["run", str(project_path), "--frames", f"{FIXTURE_FRAMES - 2}:{FIXTURE_FRAMES + 4}"],
        )

        assert result.exit_code == 1
        directory = checkpoints_dir(synthetic_video, tmp_path) / BASELINE_DIR
        assert not (directory / f"{DOWN}.npy").exists()
        assert not (directory / MANIFEST_NAME).exists()


@pytest.mark.parametrize("node_id", ["../escape", "a/b"])
def test_a_node_id_that_is_not_a_file_name_is_refused(
    synthetic_video: Path, tmp_path: Path, node_id: str
) -> None:
    """`Node.node_id` carries no spelling rule and this one reaches a path.

    A project is hand-editable YAML, so an id with a separator in it would aim a
    write outside the folder it was meant for. Refused rather than sanitized:
    two ids that sanitize alike would silently become one file.
    """
    project_path = _project(
        synthetic_video,
        tmp_path,
        checkpoints=(node_id,),
        pipeline=Pipeline(nodes=(Node(node_id=node_id, tool_id="downsample", version="1.0.0"),)),
    )

    result = runner.invoke(app, ["run", str(project_path), "--frames", f"{SPAN.start}:{SPAN.end}"])

    assert result.exit_code == 1
    assert "file name" in result.stderr
