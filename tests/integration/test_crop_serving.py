"""A materialized crop, served: same pixels, other file, one re-key.

`test_materialize.py` proves the artifact holds what the graph would have seen.
This proves the graph is then handed it. The two claims are separable and the
gap between them is where the whole item's value would leak away — a project can
have a perfectly written record and quietly go on decoding the parent, and every
number it produces is right, so nothing anywhere reports it.

Three claims, each failing for its own reason:

- The *file* changes. Asserted by recording what the command opens, because that
  is the only observable difference: identical output either way is the point.
- The *pixels* do not. Asserted frame for frame against a parent-served run,
  which is what catches the two errors this seam invites — cropping an
  already-cropped frame, and reading the artifact at source numbering.
- A *stale* record changes nothing at all, keys included. The fallback has to be
  the status quo rather than an error, and a key that moved on the way back would
  make un-backing a replicate cost a full recompute of work that is still valid.
"""

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
from sieve.pipeline.source_home import SourceHome

runner = CliRunner()

ARENA = ROI(x=16, y=8, width=64, height=48)
#: The clip, and therefore what `sieve materialize` cuts. Inside the fixture's
#: 40 frames with room either side, so a widened clip is a legal span.
CLIP = ClipRange(start=10, end=16)
GRAPH = Pipeline(
    nodes=(Node(node_id="down", filter_id="downsample", version="1.0.0", params={"factor": 2}),)
)


def _project(video: Path, directory: Path, *, replicate: Replicate) -> Path:
    """A one-node, one-arena project over `CLIP`, saved beside `video`."""
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
    """Write the project, cut its one replicate, and record it. Returns the path."""
    project_path = _project(video, directory, replicate=replicate)
    result = runner.invoke(app, ["materialize", str(project_path), "--replicate", "Arena 1"])
    assert result.exit_code == 0, result.output
    return project_path


def _resolved(project: Project, project_dir: Path, replicate: Replicate) -> ResolvedSource:
    """What this project's replicate resolves to, as a front end would ask."""
    discover()
    video = project.source_path(project_dir / "arena.sieve.yaml")
    return resolve(
        project.crops,
        replicate,
        home=SourceHome.for_video(video, project_dir),
        luma=not Dag.build(project.pipeline).needs_chroma,
        want=CLIP,
    )


def _outputs(project: Project, project_dir: Path, replicate: Replicate) -> list[NDArray[Any]]:
    """Every frame of the clip through the graph, however the source resolves.

    Deliberately the whole resolve-plan-execute path rather than the CLI: the
    command prints counts, and counts are exactly what cannot distinguish a
    correct run from one reading the wrong frames.
    """
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
        """The one observable difference, since the results are meant to match.

        Recording the opens rather than deleting the parent, because `sieve run`
        stats the parent to key against it before it opens anything — a deleted
        source is refused for a reason that has nothing to do with this item.
        What is asserted is the *decode*: the parent is named and never read.
        """
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
        """The fallback is silent at run time, so this is where it is visible.

        A user who cut an artifact and then moved the box gets no error and no
        slowdown they would notice on a short clip — only a run that is quietly
        back on the parent. `--dry-run` is where that is checkable.
        """
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
        """The load-bearing one: same pixels, and the same frames in the same order.

        Two failures live here and this catches both. A run that cropped the
        artifact again would produce arrays of the wrong shape or the wrong
        corner. A run that read the artifact at source numbering would produce
        the right shapes off by `span.start` — and the fixture's per-frame blue
        ramp is what turns that from an equal-looking array into a mismatch.
        """
        replicate = Replicate(replicate_id="a", name="Arena 1", roi=ARENA)
        project_path = _project(synthetic_video, tmp_path, replicate=replicate)
        before = _outputs(Project.load(project_path), tmp_path, replicate)

        _materialized(synthetic_video, tmp_path, replicate)
        backed = Project.load(project_path)
        after = _outputs(backed, tmp_path, replicate)

        # Without this the comparison below would pass most convincingly in the
        # one case that means nothing: both runs falling back to the parent.
        assert _resolved(backed, tmp_path, replicate).pre_cropped
        assert len(after) == CLIP.frame_count
        for index, (parent_frame, crop_frame) in enumerate(zip(before, after, strict=True)):
            assert np.array_equal(parent_frame, crop_frame), f"frame {CLIP.start + index}"

    def test_the_run_is_rooted_on_the_artifact_alone_and_says_so(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """ "Filesystem is truth at rest" reaching the read side.

        The artifact is a source in its own right: this run names the parent
        nowhere — not in the identity it keys on, not in the file it opens — and
        still yields the clip in *source* numbering, which is the whole of what
        the offsetting seam is for.

        And every result flags its source as a crop. That flag is the only thing
        standing between a crop-served render and a viewport painting one arena
        as the whole frame, and nothing else in the repo would notice its loss.
        """
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
        """Un-backing must cost nothing but the speed it was buying.

        The record is written for one box and the box then moves. If resolution
        leaked *anything* into the fallback — a different identity, a dropped
        ROI, a nonzero source start — the keys would move and a session's worth
        of correct cache entries would be recomputed for no reason.
        """
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
            home=SourceHome.for_video(video, tmp_path),
            luma=not dag.needs_chroma,
            want=CLIP,
        )

        assert stale.path == video
        assert not stale.pre_cropped
        # And the plan it produces is the plan that existed before the record.
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
