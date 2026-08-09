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

Nothing here drives the CLI, though both ends of it now exist: `sieve
materialize` writes the record and `sieve run` resolves against it. The
resolve-plan-execute path is the subject either way, and a command that printed
counts is exactly what cannot distinguish a correct run from one reading the
wrong frames.
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
from sieve.pipeline.resolve_source import ResolvedSource, crop_bound, resolve
from sieve.pipeline.source_home import SourceHome
from sieve.tools import discover
from tests.conftest import FIXTURE_FPS

#: Wholly inside the 160x120 fixture and at an odd origin in both axes, matching
#: `test_materialize.py` so the two files describe one cut.
ARENA = ROI(x=17, y=9, width=64, height=48)
#: What is cut, with room either side inside the fixture's 40 frames, so a window
#: widened past the record in either direction is still a legal span.
SPAN = SourceSpan(start=10, end=16)
PROJECT_NAME = "arena.sieve.yaml"
CUT = "cut"
DOWN = "down"
SIGNAL = "signal"
GATE = "gate"

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

#: `detect`'s band, chosen for the reason `test_cli_run.py` chooses one: the
#: transform's reach is charged at the band's low edge, so the wide-open default
#: would want more frames either side of every target than the 40-frame fixture
#: holds.
DETECT_BAND = (10.0, 14.0)

#: The graph `GRAPH` is not: `crop -> downsample` streams, so its decode range
#: *is* its span and every case above passes over the distinction. Here the
#: detector reads 10 frames past every frame it answers for and 10 behind, and
#: the difference under it one more, so a run of `WINDOWED_SPAN` answers for four
#: frames and reads twenty-five.
WINDOWED_GRAPH = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=SIGNAL, tool_id="block_signal", version="1.0.0", params={"fps": FIXTURE_FPS}),
        Node(
            node_id=GATE,
            tool_id="detect",
            version="1.0.0",
            params={"freq_band": DETECT_BAND, "window_frames": 3, "fps": FIXTURE_FPS},
        ),
    ),
    edges=(Edge(upstream=CUT, downstream=SIGNAL), Edge(upstream=SIGNAL, downstream=GATE)),
)
#: Far enough inside the fixture that the whole window is legal footage, so a
#: record failing to cover an end failed on its own span and not on the clamp.
WINDOWED_SPAN = SourceSpan(start=16, end=20)

#: Two boxes at the root and nothing in the document to choose between them.
TWO_CUTS = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
        Node(node_id="other", tool_id="crop", version="1.0.0"),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN),),
)

#: A crop of another node's output rather than of the footage.
CUT_BELOW = Pipeline(
    nodes=(
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
    ),
    edges=(Edge(upstream=DOWN, downstream=CUT),),
)


def _replicate(region: ROI = ARENA) -> Replicate:
    pinned = {"x": region.x, "y": region.y, "width": region.width, "height": region.height}
    return Replicate(name="Arena 1", replicate_id="a").with_override(CUT, {"region": pinned})


def _project(
    video: Path, directory: Path, *, replicate: Replicate, pipeline: Pipeline = GRAPH
) -> Project:
    """A one-arena project over `video`, saved beside it."""
    project = (
        Project.for_video(video, directory).with_pipeline(pipeline).with_replicates((replicate,))
    )
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


def _window(pipeline: Pipeline, span: SourceSpan, replicate: Replicate | None = None) -> SourceSpan:
    """The source frames a run of `pipeline` over `span` reads, window included.

    What `resolve` must be handed, and the two-pass shape a caller owes it: the
    window folds over the graph and its params alone, so a plan built on any
    identity answers it and the run is then keyed on whichever identity comes
    back. Handing over the span instead certifies a record for the frames in the
    answer and then reads the frames around them, which raises at both ends
    (`findings/2026.08.07-a-served-run-is-resolved-against-its-span-and-decoded-over-its-window.md`).
    """
    discover()
    reach = ExecutionPlan.build(
        Dag.build(pipeline), source="", span=span, replicate=replicate
    ).decode_range
    return SourceSpan(start=int(reach.start), end=int(reach.stop))


def _bound(pipeline: Pipeline, replicate: Replicate | None = None) -> tuple[str, ROI] | None:
    """What `crop_bound` answers for `pipeline`, as a front end would ask.

    Through a plan rather than off the document, because that is the only place
    a replicate's deviation has been resolved into a value.
    """
    discover()
    dag = Dag.build(pipeline)
    plan = ExecutionPlan.build(dag, source="", span=SPAN, replicate=replicate)
    return crop_bound(dag, plan.params)


def _materialize(
    project: Project, directory: Path, region: ROI = ARENA, span: SourceSpan = SPAN
) -> Project:
    """Cut `region` over `span`, record it, and save. Returns the new project."""
    discover()
    dag = Dag.build(project.pipeline)
    record = materialize_crop(
        project.source_path(directory / PROJECT_NAME),
        region,
        span,
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


class TestWhichNodeARecordCouldStandFor:
    """The argument `resolve` will not derive for itself.

    Two graphs a served run must not elide from, beside the one it must, and the
    three are one case. Alone, either refusal passes against a derivation that
    answered `None` to everything, and the answer alone passes against one that
    took the first crop it saw at any depth.
    """

    def test_the_single_root_crop_answers_with_the_replicates_resolved_box(self) -> None:
        """The box is the replicate's, and the node's default is not a box.

        `GRAPH` holds `crop.WHOLE_FRAME` at `CUT` and the deviation is where
        geometry lives under schema v1, so a derivation reading the document
        would hand `resolve` the identity crop, match no record ever written,
        and fall back to the parent on every project that has one.
        """
        assert _bound(GRAPH, _replicate()) == (CUT, ARENA)

    def test_a_second_crop_at_the_root_leaves_no_box_to_serve(self) -> None:
        """Two boxes are two answers, and a caller eliding either is guessing.

        The fallback is the parent, and the failure it refuses is silent: the
        wrong node dropped is a run whose frames were never cut to the box its
        keys claim. `cli/materialize_cmd.py` reads the same walk and refuses
        instead, because declining to guess costs a serving caller only speed
        and would cost a writing one a file recorded as a cut it is not.
        """
        assert _bound(TWO_CUTS) is None

    def test_a_crop_of_another_nodes_output_is_not_one_a_file_could_hold(self) -> None:
        """A record is cut from the footage, so only a root can be stood in for.

        Both nodes here resolve to the same `WHOLE_FRAME` a single-root graph
        would, so nothing about the box distinguishes this case — only the edge
        above it does. A derivation ignoring that would match a record on
        geometry alone and serve a downsampled stream's crop out of a file cut
        from the parent.
        """
        assert _bound(CUT_BELOW) is None


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


class TestTheWindowIsWhatARecordIsCheckedAgainst:
    """A declared window, not a hand-made one, and both ends of it.

    The class above supplies its own `want` a frame either side of the span,
    which pins the clause and says nothing about who computes the argument. Here
    the window comes off a graph — `_window` — and that is the whole subject: a
    caller handing over the span certifies a record for the four frames in the
    answer and then reads twenty-five.

    Two rows per end, and the pairing is the point. A row per end would pass
    against a resolver that had stopped serving anything at all, and the covering
    row is exact at the end under test, so widening the clause to `>=` on that
    side fails here too.

    **This is also why the far end needs no guard of its own.**
    `OffsetFrameSource` catches an index before the artifact begins and rewrites
    the message in source numbering; the trailing end has no counterpart, and the
    raw `VideoReader` message — "Frame 30 out of range 0..29", in the artifact's
    numbering, against a project that mentions neither number — is what the
    finding measured. It is unreachable from here: a record that cannot supply
    the read-ahead does not serve the run, so no served reader is ever asked past
    its own end, and a guard no case can reach is what
    `adr/declared-means-verified.md` refuses.
    """

    @pytest.mark.parametrize(
        ("cut", "served"),
        [
            (SourceSpan(start=5, end=40), True),
            (SourceSpan(start=6, end=40), False),
            (SourceSpan(start=0, end=30), True),
            (SourceSpan(start=0, end=29), False),
        ],
        ids=["lead_in-covered", "lead_in-short", "lookahead-covered", "lookahead-short"],
    )
    def test_a_record_reaching_only_as_far_as_the_span_does_not_serve(
        self, synthetic_video: Path, tmp_path: Path, cut: SourceSpan, served: bool
    ) -> None:
        """Serve or fall back, and the keys say which without being asked.

        The last assertion is the one that makes the pair mean something in both
        directions: serving is a re-key, because the artifact is a source in its
        own right, and falling back is the status quo down to the last key. A
        resolver that returned the parent path with the artifact's identity would
        satisfy every other line here.
        """
        replicate = _replicate()
        project = _project(synthetic_video, tmp_path, replicate=replicate, pipeline=WINDOWED_GRAPH)
        backed = _materialize(project, tmp_path, span=cut)
        parent = backed.source_path(tmp_path / PROJECT_NAME)
        dag = Dag.build(backed.pipeline)

        resolved = _resolved(
            backed, tmp_path, ARENA, want=_window(backed.pipeline, WINDOWED_SPAN, replicate)
        )

        assert (resolved.record is not None) is served
        assert resolved.path == (backed.crops[0].resolve(tmp_path) if served else parent)
        assert int(resolved.first_index) == (cut.start if served else 0)
        on_artifact = ExecutionPlan.build(
            dag, source=resolved.identity, span=WINDOWED_SPAN, replicate=replicate
        )
        on_parent = ExecutionPlan.build(
            dag, source=source_identity(parent), span=WINDOWED_SPAN, replicate=replicate
        )
        assert (on_artifact.keys == on_parent.keys) is not served


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
        """ "A source in its own right" reaching the read side.

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
            ExecutionPlan.build(dag, source=stale.identity, span=SPAN, replicate=replicate).keys
            == ExecutionPlan.build(
                dag, source=source_identity(video), span=SPAN, replicate=replicate
            ).keys
        )
