"""A written crop, wired in: same pixels, another file, no crop node.

`test_materialize.py` proves the artifact holds what the graph would have seen.
This proves the graph is then handed it — and under
`adr/a-users-file-wires-in-like-any-other-input.md` "handed it" is a fact about
the *document* rather than about one command's plan-time route. So the subject
here is the edit `pipeline/crop_serving.py` makes and what every front end does
with a project that has taken it. The gap between the two claims is where the
item's value would leak away: a project can hold a perfectly written record and
go on decoding the parent, and every number it produces is right, so nothing
anywhere reports it.

What each class is for, and why none of them collapses into another:

- The **edit** replaces the node and nothing else. A run of a served project
  opens the artifact and never the parent, and the graph it runs holds no crop
  node — the two halves of a substitution that could fail either way, since a
  graph that reads the artifact and still crops cuts a box out of a box, and one
  that drops the node and reads the parent downsamples whole frames under the
  artifact's keys.
- The **key** the served root folds is the string that file folds as footage,
  which is `adr/a-root-keys-by-its-reader.md` reaching the tree. What it is not
  is asserted beside it: `picked_key` over the same identity is a different
  string, and the first source tool folded that one.
- The **pixels** do not move. Frame for frame against a parent-served run, which
  catches re-cutting an already-cut frame and reading the file at source
  numbering.
- **Every front end** is served alike, and this is the whole reason the route
  became an edit: `sieve run` had it and a preview session did not.
- A folder of **already-cut files** wires in with no record anywhere, which is
  the case that forced the ADR and the one that has no parent to fall back to.

Nothing here re-asserts the record-matching clauses. Those are `CropRecord.backs`
and `tests/unit/test_crop_binding.py`, which is also where the join between the
report and the offer lives.
"""

from __future__ import annotations

from glob import glob
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray
from typer.testing import CliRunner

from sieve.cli import run_cmd
from sieve.cli.app import app
from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    SourceSpan,
)
from sieve.core.types import ROI
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import picked_key, source_identity, source_key
from sieve.pipeline.crop_serving import serving_edit, unserving_edit
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan, validated_params
from sieve.pipeline.preview import PreviewSession
from sieve.pipeline.resolve_source import anchored, picked_identities, source_files
from sieve.pipeline.source_home import SourceHome
from sieve.tools import discover
from tests.projects import footage_of, project_over, rooted_on

runner = CliRunner()

#: Wholly inside the 160x120 fixture and at an odd origin in both axes, matching
#: `test_materialize.py` so the two files describe one cut.
ARENA = ROI(x=17, y=9, width=64, height=48)
#: A second box, for the folder case: two replicates over two written files.
OTHER = ROI(x=81, y=9, width=64, height=48)
#: What a run asks for, with room either side inside the fixture's 40 frames.
SPAN = SourceSpan(start=10, end=16)
PROJECT_NAME = "arena.sieve.yaml"
CUT = "cut"
DOWN = "down"

#: The crop node carries no region of its own — `crop.WHOLE_FRAME` is its default
#: and that is the identity crop as a value — and the replicate pins the box. This
#: is where a replicate's geometry lives under schema v1
#: (`adr/detector-is-a-node.md`), so the edit has to read it off a resolved plan
#: rather than off the document.
GRAPH = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN),),
)


def _replicate(region: ROI = ARENA, name: str = "Arena 1", ident: str = "a") -> Replicate:
    pinned = {"x": region.x, "y": region.y, "width": region.width, "height": region.height}
    return Replicate(name=name, replicate_id=ident).with_override(CUT, {"region": pinned})


def _project(
    video: Path,
    directory: Path,
    *,
    replicates: tuple[Replicate, ...] = (),
    pipeline: Pipeline = GRAPH,
) -> Path:
    """A project over `video`, saved beside it. Returns the file it was saved to."""
    discover()
    path = directory / PROJECT_NAME
    (project_over(video, directory, pipeline).with_replicates(replicates).save(path))
    return path


def _cut(project_path: Path, replicate_id: str = "a") -> None:
    """Cut one replicate through the command, which also wires when it can."""
    result = runner.invoke(app, ["materialize", str(project_path), "--replicate", replicate_id])
    assert result.exit_code == 0, result.output


def _home(project: Project, project_path: Path) -> SourceHome:
    return SourceHome.for_video(footage_of(project, project_path), project_path.parent)


def _watch_opens(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Every video the run loop opens, in order, still opening each of them.

    What it pins is `run_cmd._reads_the_footage`, and since
    `adr/a-document-names-footage-only-through-a-tool.md` that is a claim about
    every document rather than about served ones: a project names its footage in
    a source node, so every root of every graph opens its own file and the run
    builds no reader at all. The log is therefore empty on both sides of the
    edit, and it stays here because a run that started building a reader again
    would be one deciding for itself what the footage is.

    Which file each side actually read is the pixel case's — the counts cannot
    say it, since a run that re-cut whole frames from the parent prints exactly
    the numbers a correctly served one prints.
    """
    opened: list[Path] = []
    real = run_cmd.frame_source

    def watching(video: Path, *, luma: bool) -> PrefetchFrameSource:
        opened.append(video)
        return real(video, luma=luma)

    monkeypatch.setattr(run_cmd, "frame_source", watching)
    return opened


def _plan(project: Project, project_path: Path, replicate: Replicate | None) -> ExecutionPlan:
    """The plan a front end builds for `replicate`, source roots resolved.

    Spelt once, because what several cases below compare is two front ends'
    answers to this and a helper that resolved differently from either would be
    a third answer nothing runs.
    """
    dag = Dag.build(anchored(project.pipeline, project_path.parent))
    return ExecutionPlan.build(
        dag,
        source=source_identity(footage_of(project, project_path)),
        span=SPAN,
        replicate=replicate,
        picked=picked_identities(source_files(dag, validated_params(dag, replicate))),
    )


class TestTheEditTheProjectHolds:
    def test_the_served_graph_holds_no_crop_node(
        self, synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The load-bearing claim, in the document and then in a run of it.

        Not neutralised at `crop.WHOLE_FRAME` and not dropped per run: the node
        is *gone from the graph the project holds*, replaced by a `footage` node
        over the file that already holds its output.

        **The node count does not move, and that is the shape of this
        substitution rather than a miss.** The plan-time route this replaces
        dropped the crop node and left the graph one node shorter; a source tool
        is a node, so what a served run saves is the cut, not an entry in the
        tally. Which is why the file that was opened is asserted here and the
        count is only asserted to be unchanged: the counts a correct run prints
        and the counts of a run that quietly re-cut whole frames from the parent
        are the same counts.

        What the served run no longer saves is the *parent decode*, and the graph
        is why. The document names its footage in a source node
        (`adr/a-document-names-footage-only-through-a-tool.md`), so the parent is
        a root of the served graph too — reading nothing, since the crop that
        read it was the thing replaced, and computed anyway because the executor
        computes every node the graph holds. `opened` stays empty for the served
        run because the run's own reader is what it watches and that reader is
        never built (`run_cmd._reads_the_footage`); the parent's frames come out
        of the source tool's own pool instead.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        frames = f"{SPAN.start}:{SPAN.end}"
        opened = _watch_opens(monkeypatch)
        unserved = runner.invoke(app, ["run", str(path), "--frames", frames])

        _cut(path)
        served_project = Project.load(path)
        served = runner.invoke(app, ["run", str(path), "--frames", frames])

        assert unserved.exit_code == 0, unserved.output
        assert served.exit_code == 0, served.output
        assert [node.tool_id for node in served_project.pipeline.nodes] == [
            "footage",
            "footage",
            "downsample",
        ]
        assert served_project.crops, "the record survives the edit that reads it"
        record = served_project.crops[0]
        assert glob(served_project.params_for(CUT, "a")["path"]) == [str(record.resolve(tmp_path))]
        assert served_project.params_for(CUT, "a")["first_index"] == record.span.start
        answered = SPAN.frame_count
        expected = [
            f"Arena 1: {answered} frames, {answered * 3} node outputs computed, 0 from cache"
        ]
        assert unserved.output.splitlines() == expected
        assert served.output.splitlines() == expected
        assert opened == [], "neither run built a reader of its own; every root opens its file"

    def test_the_served_root_folds_the_key_its_file_would_fold_as_footage(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """`adr/a-root-keys-by-its-reader.md`, asserted where it is observable.

        The served root is read through the shared decode stack, so what it
        folds is `source_key` over its own file in the graph's own format — the
        string a run whose *footage* was that file would fold. The `picked_key`
        line is what makes that mean something: it is the same identity through
        the other flavour, it is what the first source tool folded for every
        root, and it is a different string.

        Asserted through the plan rather than by calling `Dag.node_keys` with a
        hand-made argument, because the thing that could be wrong is the walk
        choosing the flavour, and a caller passing one in would be choosing for
        it.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        _cut(path)
        project = Project.load(path)
        artifact = project.crops[0].resolve(tmp_path)
        identity = source_identity(artifact)

        plan = _plan(project, path, project.replicates[0])

        # The graph reads no chroma, so this is the format it derives — the same
        # one `materialize_crop` wrote the file in.
        assert not Dag.build(project.pipeline).needs_chroma
        upstream = source_key(identity, decode_format="luma")
        assert plan.keys[CUT] != upstream, "the node has a key of its own"
        assert (
            plan.keys[CUT]
            == ExecutionPlan.build(
                Dag.build(project.pipeline),
                source="anything else entirely",
                span=SPAN,
                replicate=project.replicates[0],
                picked={CUT: identity},
            ).keys[CUT]
        ), "the parent's identity reaches no key in a fully served graph"
        assert upstream != picked_key(identity)

    def test_a_stale_record_offers_no_edit(self, synthetic_video: Path, tmp_path: Path) -> None:
        """Un-backing costs nothing but the speed it was buying.

        The record is written for one box and the box then moves. Nothing is
        offered, so the document is untouched and the project goes on cutting
        from the parent under exactly the keys it had — which is what makes a
        box a thing a user may drag after materializing it.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        _cut(path)
        recorded = Project.load(path)
        moved = recorded.with_pipeline(rooted_on(GRAPH, synthetic_video, tmp_path)).with_replicates(
            (_replicate(ROI(x=18, y=9, width=64, height=48)),)
        )

        assert serving_edit(moved, _home(moved, path)) is None
        assert serving_edit(recorded, _home(recorded, path)) is None, (
            "an already-served project has no crop node left to offer for"
        )

    def test_a_checkpointed_crop_node_is_not_replaced(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A node someone asked to keep is a node that runs, artifact or not.

        Replacing it would leave the manifest naming a node the document no
        longer holds — and unlike the plan-time route this replaces, which could
        decline for one run, an edit removes it for good.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        Project.load(path).with_outputs((CUT,), ()).save(path)
        _cut(path)
        project = Project.load(path)

        assert project.pipeline.node(CUT).tool_id == "crop"
        assert project.crops, "the file was still written and recorded"


class TestTheWayBackFromAServedProject:
    """The reverse of the edit above, and the two states it is the way out of.

    Taking the serving edit used to be one-way in the tree
    (`findings/2026.08.09-a-served-project-cannot-grow-a-replicate-or-be-cut-again.md`):
    a served project has no root crop node, so `sieve materialize` had nothing to
    cut, and a thirteenth arena drawn on one carried a `region` override of a
    node whose tool has no such parameter — a document that saved and then failed
    every plan.

    Both are the same missing edit rather than two bugs, which is why they share
    a class: the records survive the substitution, so the crop node and every
    replicate's box can be read back out of them.
    """

    def test_a_served_project_can_be_cut_again(self, synthetic_video: Path, tmp_path: Path) -> None:
        """The reverse edit, and then a whole cut through the command that takes it.

        The direct assertion first, because the round trip alone would pass for a
        `materialize` that had merely learnt to skip the refusal: what
        `unserving_edit` hands back is a *crop* node, and the box on it is the
        one the record was cut at rather than the graph's `WHOLE_FRAME` default.

        Then the round trip, which is what a user does. Cutting a served project
        un-wires it, cuts, and wires it back, so the document is where it started
        — the same node, the same file, the same one record — and the only thing
        that moved is the artifact on disk.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        _cut(path)
        served = Project.load(path)

        reverted = unserving_edit(served, _home(served, path))

        assert served.pipeline.node(CUT).tool_id == "footage"
        assert reverted is not None
        assert reverted.pipeline.node(CUT).tool_id == "crop"
        assert reverted.params_for(CUT, "a") == {
            "region": {"x": ARENA.x, "y": ARENA.y, "width": ARENA.width, "height": ARENA.height}
        }
        assert reverted.crops == served.crops, "the records are what it was read out of"

        _cut(path)

        again = Project.load(path)
        assert again.pipeline.node(CUT).tool_id == "footage"
        assert again.params_for(CUT, "a") == served.params_for(CUT, "a")
        assert again.crops == served.crops

    def test_a_replicate_added_to_a_served_project_runs(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A thirteenth arena on twelve, at the scale the fixture affords.

        The override the new replicate carries is a `region` on `CUT`, because
        that is what a front end writes for an arena and it is written against a
        document whose crop node is already gone. Cutting it is what makes it
        runnable: the invocation un-wires the project, so `region` names a
        parameter that exists again, and re-wires it once both arenas have files.

        The run at the end is the assertion the item's criterion asks for rather
        than a smoke test — before this, the document saved and every plan built
        from it raised `extra_forbidden` on a field the user never typed.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        _cut(path)
        served = Project.load(path)
        grown = _replicate(OTHER, "Arena 2", "b")
        served.with_replicates((*served.replicates, grown)).save(path)

        _cut(path, "b")
        result = runner.invoke(app, ["run", str(path), "--frames", f"{SPAN.start}:{SPAN.end}"])

        assert result.exit_code == 0, result.output
        after = Project.load(path)
        assert after.pipeline.node(CUT).tool_id == "footage"
        assert len(after.crops) == 2
        assert after.params_for(CUT, "a") != after.params_for(CUT, "b"), "one file each"
        answered = SPAN.frame_count
        # The second arena finds the parent footage root's entries: the served
        # graph still holds that root, and it is the one node the two replicates
        # do not deviate, so it is computed once and looked up once.
        assert result.output.splitlines() == [
            f"Arena 1: {answered} frames, {answered * 3} node outputs computed, 0 from cache",
            (
                f"Arena 2: {answered} frames, {answered * 2} node outputs computed, "
                f"{answered} from cache"
            ),
        ]


class TestTheServedFramesAreTheFramesTheParentWouldHaveGiven:
    def test_frame_for_frame_against_a_parent_served_run(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Same pixels, same frames, same order.

        Two failures live here and this catches both. A run that re-cut the
        artifact would produce arrays of the wrong shape or the wrong corner. A
        run that read the file at source numbering would produce the right
        shapes off by `span.start` — and the fixture's per-frame blue ramp is
        what turns that from an equal-looking array into a mismatch.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        before = _outputs(Project.load(path), path)

        _cut(path)
        served = Project.load(path)
        after = _outputs(served, path)

        assert served.pipeline.node(CUT).tool_id == "footage"
        assert len(after) == SPAN.frame_count
        for offset, (parent_frame, served_frame) in enumerate(zip(before, after, strict=True)):
            assert np.array_equal(parent_frame, served_frame), f"frame {SPAN.start + offset}"


class TestEveryFrontEndIsServedAlike:
    """The gap the edit closes, and the one it does not close by itself.

    A preview session and a render worker never had the plan-time route, so
    before this they decoded the parent and re-cut a box already on disk. They
    are served now because the graph they are handed is the served graph — no
    call was added to either. What is *not* free is `picked`: a front end that
    builds a plan without resolving its source roots leaves the served root
    unkeyed and everything under it recomputing, which is a silent loss of the
    interactive loop rather than a wrong answer.
    """

    def test_a_preview_is_served_by_the_written_crop(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A session over a served project reads the artifact and not the parent.

        The reader handed to the session is the parent's, exactly as a preview
        over an unserved project's would be, and the assertion is that it is
        never asked for a frame: every root in the served graph opens its own
        file. That is the difference between being served and being told to be
        served — nothing in `preview.py` knows an artifact exists.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        _cut(path)
        project = Project.load(path)
        reads: list[int] = []

        with VideoReader(synthetic_video, luma=True) as parent:
            session = PreviewSession(
                source=source_identity(synthetic_video),
                reader=_Counting(parent, reads),
                window=SPAN,
                measure=lambda label: _nothing(),
                replicate=project.replicates[0],
                store=MemoryFrameStore(),
            )
            graph = anchored(project.pipeline, path.parent)
            first = session.render_window(graph)
            again = session.render_window(graph)

        assert first.frames == SPAN.frame_count
        assert reads == [], "the parent reader was never asked for a frame"
        # The second render answers entirely from the store, which is only
        # possible if every node — the served root included — was keyed.
        assert (again.computed, again.from_cache) == (0, first.computed)

    def test_a_served_source_root_reaches_every_front_ends_plan_keyed(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Two front ends, two independently built plans, one key dict.

        The case fails while any front end builds a plan without `picked`:
        `Dag.node_keys` drops a source root it was given no identity for and
        every node below it goes with the subtree, so the two dicts stop being
        equal and neither is full. Asserting the whole dict rather than its
        length is what makes it fail for the right reason — two front ends
        agreeing on an *empty* answer would satisfy a length check.

        `sieve materialize` is the third plan builder and is absent here for a
        reason rather than by omission: it refuses a graph with no root crop
        node, so it has no plan to build over a served project. Its own keying
        is `test_materialize.py`'s.
        """
        path = _project(synthetic_video, tmp_path, replicates=(_replicate(),))
        _cut(path)
        project = Project.load(path)
        replicate = project.replicates[0]
        node_ids = {node.node_id for node in project.pipeline.nodes}

        dry = runner.invoke(
            app, ["run", str(path), "--dry-run", "--frames", f"{SPAN.start}:{SPAN.end}"]
        )
        with VideoReader(synthetic_video, luma=True) as parent:
            session = PreviewSession(
                source=source_identity(synthetic_video),
                reader=parent,
                window=SPAN,
                measure=lambda label: _nothing(),
                replicate=replicate,
                store=MemoryFrameStore(),
            )
            rendered = session.render_window(anchored(project.pipeline, path.parent))

        assert dry.exit_code == 0, dry.output
        assert set(rendered.plan.keys) == node_ids
        assert rendered.plan.keys == _plan(project, path, replicate).keys
        for node_id, key in rendered.plan.keys.items():
            assert f"{node_id}  " in dry.output
            assert key[:12] in dry.output


class TestAFolderOfAlreadyCutFilesNeedsNoRecord:
    def test_a_pre_cropped_folder_needs_no_crop_record(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The case that forced the ADR: same mechanism, nothing to hang a record on.

        Two replicates, two files somebody else cut, and no `CropRecord`
        anywhere — so nothing about parentage, geometry or format is matched and
        there is no parent to decline back to. What makes this more than a
        restatement of the served case is that the two replicates key
        differently: each source root resolves its own deviated path, so a walk
        that resolved one file for the graph would give both arenas one answer.
        """
        cut = _project(
            synthetic_video, tmp_path, replicates=(_replicate(), _replicate(OTHER, "Arena 2", "b"))
        )
        _cut(cut, "a")
        _cut(cut, "b")
        files = [record.resolve(tmp_path) for record in Project.load(cut).crops]
        assert len(files) == 2

        folder = tmp_path / "folder"
        folder.mkdir()
        path = _project(
            synthetic_video,
            folder,
            replicates=tuple(
                Replicate(name=f"Arena {index + 1}", replicate_id=ident).with_override(
                    CUT, {"path": str(file), "first_index": SPAN.start}
                )
                for index, (ident, file) in enumerate(zip("ab", files, strict=True))
            ),
            pipeline=Pipeline(
                nodes=(
                    Node(node_id=CUT, tool_id="footage", version="1.0.0"),
                    Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
                ),
                edges=(Edge(upstream=CUT, downstream=DOWN),),
            ),
        )
        project = Project.load(path)

        result = runner.invoke(app, ["run", str(path), "--frames", f"{SPAN.start}:{SPAN.end}"])

        assert result.exit_code == 0, result.output
        assert project.crops == ()
        answered = SPAN.frame_count
        assert result.output.splitlines() == [
            f"Arena {index + 1}: {answered} frames, {answered * 2} node outputs computed, "
            "0 from cache"
            for index in range(2)
        ]
        first, second = (_plan(project, path, target) for target in project.replicates)
        assert first.keys[CUT] != second.keys[CUT]


def _outputs(project: Project, project_path: Path) -> list[NDArray[Any]]:
    """Every frame of `SPAN` through `project`'s graph, however it is rooted.

    One path for both sides of the pixel comparison, which is the point: a
    served project and an unserved one differ in the document and in nothing a
    caller does.
    """
    discover()
    replicate = project.replicates[0]
    plan = _plan(project, project_path, replicate)
    with VideoReader(footage_of(project, project_path), luma=plan.luma) as reader:
        return [np.array(result[DOWN].data) for result in execute(plan, reader)]


class _Counting:
    """A `FrameSource` that records every index it was asked for."""

    def __init__(self, inner: VideoReader, reads: list[int]) -> None:
        self._inner = inner
        self._reads = reads

    def read(self, index: int) -> Any:
        self._reads.append(int(index))
        return self._inner.read(index)


class _nothing:
    """The measure a case that is not about timings hands a session."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_exc: object) -> None:
        return None
