"""A written crop, served: same pixels, other file, one re-key.

`test_materialize.py` proves the artifact holds what the graph would have seen.
This proves the graph is then handed it. The two claims are separable and the gap
between them is where the whole item's value would leak away — a project can have
a perfectly written record and quietly go on decoding the parent, and every
number it produces is right, so nothing anywhere reports it.

Four claims, each failing for its own reason:

- The *file* changes, and the identity with it. That re-key is the price the
  child-source model charges and the thing a caller must not paper over.
- The *pixels* do not. Asserted frame for frame against a parent-served run,
  which is what catches the two errors this seam invites — re-cutting an
  already-cut frame, and reading the artifact at source numbering.
- A record that does not *cover* the window is declined whole rather than in
  part, in both directions, because half-serving would put two decoders' pixels
  in one run under one root key.
- A *stale* record changes nothing at all, keys included. The fallback has to be
  the status quo rather than an error, and a key that moved on the way back would
  make un-backing a box cost a full recompute of work that is still valid.

Nothing here drives the CLI. `sieve materialize` does not exist
(`todo/the-materialize-command-derives-what-v2-was-handed.md`) and `sieve run`
does not yet call `resolve` — the resolve-plan-execute path is the subject
either way, and a command that printed counts is exactly what cannot distinguish
a correct run from one reading the wrong frames.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    SourceSpan,
)
from sieve.core.types import ROI
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.materialize import materialize_crop
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import ResolvedSource, resolve
from sieve.pipeline.source_home import SourceHome
from sieve.tools import discover

#: Wholly inside the 160x120 fixture and at an odd origin in both axes, matching
#: `test_materialize.py` so the two files describe one cut.
ARENA = ROI(x=17, y=9, width=64, height=48)
#: What is cut, with room either side inside the fixture's 40 frames, so a window
#: widened past the record in either direction is still a legal span.
SPAN = SourceSpan(start=10, end=16)
PROJECT_NAME = "arena.sieve.yaml"
CUT = "cut"
DOWN = "down"

#: The crop node carries no region of its own — `crop.WHOLE_FRAME` is its default
#: and that is the identity crop as a value — and the replicate pins the box. This
#: is where a replicate's geometry lives under schema v1
#: (`adr/detector-is-a-node.md`).
GRAPH = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN),),
)


def _replicate(region: ROI = ARENA) -> Replicate:
    pinned = {"x": region.x, "y": region.y, "width": region.width, "height": region.height}
    return Replicate(name="Arena 1", replicate_id="a").with_override(CUT, {"region": pinned})


def _project(video: Path, directory: Path, *, replicate: Replicate) -> Project:
    """A two-node, one-arena project over `video`, saved beside it."""
    project = Project.for_video(video, directory).with_pipeline(GRAPH).with_replicates((replicate,))
    project.save(directory / PROJECT_NAME)
    return project


def _home(project: Project, directory: Path) -> SourceHome:
    return SourceHome.for_video(project.source_path(directory / PROJECT_NAME), directory)


def _resolved(
    project: Project, directory: Path, region: ROI, want: SourceSpan = SPAN
) -> ResolvedSource:
    """What this project's box resolves to, as a front end would ask."""
    discover()
    return resolve(
        project.crops,
        region,
        home=_home(project, directory),
        luma=not Dag.build(project.pipeline).needs_chroma,
        want=want,
    )


def _materialize(project: Project, directory: Path, region: ROI = ARENA) -> Project:
    """Cut `region` over `SPAN`, record it, and save. Returns the new project."""
    discover()
    dag = Dag.build(project.pipeline)
    record = materialize_crop(
        project.source_path(directory / PROJECT_NAME),
        region,
        SPAN,
        name="Arena 1",
        project_dir=directory,
        luma=not dag.needs_chroma,
    )
    backed = project.with_crop(record)
    backed.save(directory / PROJECT_NAME)
    return backed


def _outputs(
    project: Project, directory: Path, replicate: Replicate
) -> tuple[list[NDArray[Any]], ResolvedSource]:
    """Every frame of `SPAN` through the graph, however the source resolves.

    The `target` line is the caller's half of the child-source trade, stated in
    the test because no production code states it yet: the artifact already holds
    the crop node's output, so a served run must not run that node again. Spelt
    as the baseline — whose region is `crop.WHOLE_FRAME`, the identity crop —
    rather than as a flag on the plan, because a v3 plan has no region to
    suppress. `todo/a-served-run-elides-the-node-its-file-already-holds.md` is
    where this moves into `resolve`'s callers.
    """
    discover()
    dag = Dag.build(project.pipeline)
    region = ROI(**project.params_for(CUT, replicate.replicate_id)["region"])
    resolved = _resolved(project, directory, region)
    target = None if resolved.record is not None else replicate
    plan = ExecutionPlan.build(dag, source=resolved.identity, span=SPAN, replicate=target)
    with VideoReader(resolved.path, luma=plan.luma) as reader:
        frames = [np.array(result[DOWN].data) for result in execute(plan, resolved.wrap(reader))]
    return frames, resolved


class TestTheArtifactIsWhatGetsDecoded:
    def test_a_covering_record_resolves_to_its_own_file_and_its_own_numbering(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The four fields are one decision, so all four are asserted together.

        `first_index` is the one that has no analogue on the parent path and the
        one nothing else in the system can supply: the record says which source
        frame the file's frame 0 is, and a resolver that returned the right path
        with a zero here would read six correct frames from the wrong place in
        the video and report success.
        """
        backed = _materialize(_project(synthetic_video, tmp_path, replicate=_replicate()), tmp_path)

        resolved = _resolved(backed, tmp_path, ARENA)

        assert resolved.record is backed.crops[0]
        assert resolved.path == backed.crops[0].resolve(tmp_path)
        assert resolved.identity == source_identity(resolved.path)
        assert resolved.identity != source_identity(synthetic_video)
        assert int(resolved.first_index) == SPAN.start

    @pytest.mark.parametrize(
        ("start", "end"),
        [(SPAN.start - 1, SPAN.end), (SPAN.start, SPAN.end + 1)],
        ids=["reaching-before", "reaching-after"],
    )
    def test_a_window_reaching_past_what_was_cut_is_declined_whole(
        self, synthetic_video: Path, tmp_path: Path, start: int, end: int
    ) -> None:
        """The clause `CropRecord.backs` deliberately refuses to evaluate.

        The record still matches on parentage, geometry, and format — only the
        window moved — so a resolver that took `backs` as the whole answer would
        serve this. Serving part of the request would put artifact pixels and
        parent pixels in one run under a single root key, which is a wrong answer
        that arrives from cache and leaves no trace. Both directions, because
        only one is caught by the obvious comparison.
        """
        backed = _materialize(_project(synthetic_video, tmp_path, replicate=_replicate()), tmp_path)

        resolved = _resolved(backed, tmp_path, ARENA, want=SourceSpan(start=start, end=end))

        assert resolved.record is None
        assert resolved.path == backed.source_path(tmp_path / PROJECT_NAME)


class TestTheServedFramesAreTheFramesTheParentWouldHaveGiven:
    def test_frame_for_frame_against_a_parent_served_run(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The load-bearing one: same pixels, same frames, same order.

        Two failures live here and this catches both. A run that re-cut the
        artifact would produce arrays of the wrong shape or the wrong corner. A
        run that read the artifact at source numbering would produce the right
        shapes off by `span.start` — and the fixture's per-frame blue ramp is
        what turns that from an equal-looking array into a mismatch.
        """
        replicate = _replicate()
        project = _project(synthetic_video, tmp_path, replicate=replicate)
        before, parent = _outputs(project, tmp_path, replicate)

        after, served = _outputs(_materialize(project, tmp_path), tmp_path, replicate)

        # Without these the comparison below would pass most convincingly in the
        # one case that means nothing: both runs falling back to the parent.
        assert parent.record is None
        assert served.record is not None
        assert len(after) == SPAN.frame_count
        for offset, (parent_frame, crop_frame) in enumerate(zip(before, after, strict=True)):
            assert np.array_equal(parent_frame, crop_frame), f"frame {SPAN.start + offset}"

    def test_the_run_is_rooted_on_the_artifact_alone_and_yields_source_numbering(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """"A source in its own right" reaching the read side.

        The run names the parent nowhere — not in the identity it keys on, not in
        the file it opens — and still answers in *source* numbering, which is the
        whole of what the offsetting seam is for. A reader handed to the executor
        unwrapped would answer frames 10 through 15 with indices 0 through 5, and
        the executor would refuse them as a tool that renumbered its output.
        """
        replicate = _replicate()
        backed = _materialize(_project(synthetic_video, tmp_path, replicate=replicate), tmp_path)
        discover()
        dag = Dag.build(backed.pipeline)
        resolved = _resolved(backed, tmp_path, ARENA)
        plan = ExecutionPlan.build(dag, source=resolved.identity, span=SPAN, replicate=None)

        with VideoReader(resolved.path, luma=plan.luma) as reader:
            results = list(execute(plan, resolved.wrap(reader)))

        parent_rooted = ExecutionPlan.build(
            dag, source=source_identity(synthetic_video), span=SPAN, replicate=None
        )
        assert [int(result.index) for result in results] == list(range(SPAN.start, SPAN.end))
        assert resolved.path != synthetic_video
        assert plan.keys != parent_rooted.keys


class TestAStaleRecordChangesNothing:
    def test_a_moved_box_reproduces_the_pre_artifact_run_keys_included(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Un-backing must cost nothing but the speed it was buying.

        The record is written for one box and the box then moves. If resolution
        leaked *anything* into the fallback — a different identity, a nonzero
        first index — the keys would move and a session's worth of correct cache
        entries would be recomputed for no reason.
        """
        moved = ROI(x=18, y=9, width=64, height=48)
        backed = _materialize(_project(synthetic_video, tmp_path, replicate=_replicate()), tmp_path)
        assert backed.crops, "the record was written"
        video = backed.source_path(tmp_path / PROJECT_NAME)
        discover()
        dag = Dag.build(backed.pipeline)

        stale = _resolved(backed, tmp_path, moved)

        assert stale.record is None
        assert stale.path == video
        assert int(stale.first_index) == 0
        replicate = _replicate(moved)
        assert (
            ExecutionPlan.build(
                dag, source=stale.identity, span=SPAN, replicate=replicate
            ).keys
            == ExecutionPlan.build(
                dag, source=source_identity(video), span=SPAN, replicate=replicate
            ).keys
        )
