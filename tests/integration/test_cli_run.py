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

import math
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sieve.cli import run_cmd
from sieve.cli.app import app
from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    Sink,
    SourceSpan,
)
from sieve.core.types import ROI
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.pipeline.dag import Dag
from sieve.pipeline.materialize import materialize_crop
from sieve.tools import discover
from tests.conftest import FIXTURE_FPS, FIXTURE_FRAMES

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


#: The detector's low band edge, and the read-ahead it buys at `FIXTURE_FPS`.
#: The transform's reach is charged at the band's lowest frequency, so the
#: wide-open default would put more frames either side of every target than the
#: 40-frame fixture holds and there would be no span to narrow *to* —
#: `tests/integration/test_v2_oracle.py` picks 7 Hz for the same reason.
DETECT_FREQ_LO = 7.0
DETECT_LOOKAHEAD = 11


def _looking_ahead(video: Path, directory: Path) -> Path:
    """A `blocks -> detector` project beside `video`, whose detector reads ahead.

    The smallest graph that reaches the failure: `detect` is the one tool that
    declares a lookahead (`adr/detector-is-a-node.md` is why it can be a node at
    all), and it wants a per-block signal under it.
    """
    project = Project.for_video(video, directory).with_pipeline(
        Pipeline(
            nodes=(
                Node(
                    node_id="blocks",
                    tool_id="block_signal",
                    version="1.0.0",
                    params={
                        "signal": "change_energy",
                        "block": 16,
                        "scale": 1.0,
                        "fps": FIXTURE_FPS,
                    },
                ),
                Node(
                    node_id="detector",
                    tool_id="detect",
                    version="1.0.0",
                    params={
                        "freq_band": (DETECT_FREQ_LO, math.inf),
                        "value_band": (1e6, math.inf),
                        "count_frac": (0.25, math.inf),
                        "window_frames": 9,
                        "centered": True,
                        "fps": FIXTURE_FPS,
                    },
                ),
            ),
            edges=(Edge(upstream="blocks", downstream="detector"),),
        )
    )
    path = directory / "detecting.sieve.yaml"
    project.save(path)
    return path


def test_a_default_run_answers_to_the_end_of_footage_it_can_and_says_what_it_dropped(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The default invocation of the only graph shape Phase 4 built a contract for.

    No `--frames` means the whole video, and a graph reading ahead of the frame
    it answers for cannot answer for the last of them — `plan.py` charges the
    read-ahead past `span.end` and the reader refuses an index past the last
    frame. Fails two ways, both of which have shipped: refusing the run entirely
    with `Frame 40 out of range 0..39`, which answers for nothing where it could
    answer for 29 of 40; and narrowing the span quietly, which reports a number
    of frames the user never asked about and never says which frames are missing
    or whose read-ahead cost them.
    """
    project = _looking_ahead(synthetic_video, tmp_path)

    result = runner.invoke(app, ["run", str(project)])

    assert result.exit_code == 0, result.output
    answered = FIXTURE_FRAMES - DETECT_LOOKAHEAD
    assert f"baseline: {answered} frames," in result.output
    warning = next(line for line in result.output.splitlines() if "not answered for" in line)
    assert f"the last {DETECT_LOOKAHEAD} frames" in warning
    assert "detector" in warning
    assert f"0:{answered}" in warning


def test_a_span_wholly_inside_the_end_of_footage_read_ahead_is_still_refused(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """Narrowing stops where there is nothing left to narrow to.

    The last frames of a video are unanswerable rather than merely under-warmed,
    so a span sitting entirely inside the read-ahead has no shorter span that
    would satisfy it — unlike a lead-in, which can always be cut back to frame
    zero. Fails for a clamp applied by reflex, which turns this into a run
    reporting success over zero frames or over a span the user did not ask for.
    """
    project = _looking_ahead(synthetic_video, tmp_path)

    result = runner.invoke(
        app, ["run", str(project), "--frames", f"{FIXTURE_FRAMES - 10}:{FIXTURE_FRAMES}"]
    )

    assert result.exit_code == 1
    assert "nothing is left to compute" in result.stderr
    assert str(DETECT_LOOKAHEAD) in result.stderr


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


#: The box a served run's file already holds, and what it was cut over. The
#: same cut `test_crop_serving.py` and `test_materialize.py` use, so the three
#: files describe one artifact rather than three.
SERVED_REGION = ROI(x=17, y=9, width=64, height=48)
SERVED_SPAN = SourceSpan(start=10, end=16)
CUT = "cut"

#: `crop -> downsample` streams, so its decode range *is* its span and a record
#: cut over `SERVED_SPAN` covers a run of it exactly.
STREAMING = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id="down", tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(Edge(upstream=CUT, downstream="down"),),
)

#: The graph `STREAMING` is not. `detect` reads ahead of every frame it answers
#: for and the signal under it reads behind, so the span and the frames read
#: are different quantities and a record can cover one without the other. The
#: band is narrow for `DETECT_FREQ_LO`'s reason.
WINDOWED = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(
            node_id="blocks", tool_id="block_signal", version="1.0.0", params={"fps": FIXTURE_FPS}
        ),
        Node(
            node_id="detector",
            tool_id="detect",
            version="1.0.0",
            params={"freq_band": (10.0, 14.0), "window_frames": 3, "fps": FIXTURE_FPS},
        ),
    ),
    edges=(Edge(upstream=CUT, downstream="blocks"), Edge(upstream="blocks", downstream="detector")),
)
#: Far enough inside the 40-frame fixture that the whole window is legal
#: footage, so a record short of an end is short on its own span and not on the
#: clamp.
WINDOWED_SPAN = SourceSpan(start=16, end=20)
#: `ExecutionPlan.decode_range` for `WINDOWED` over `WINDOWED_SPAN`: eleven
#: frames of lead-in and ten of read-ahead around four answered frames.
WINDOW = SourceSpan(start=5, end=30)


def _cropping(video: Path, directory: Path, pipeline: Pipeline) -> Path:
    """`pipeline` beside `video`, one replicate pinning the box at `CUT`.

    Geometry lives on the replicate rather than on the node because that is
    where schema v1 puts it (`adr/detector-is-a-node.md`), and it is what makes
    the region a thing the command has to *derive* rather than read.
    """
    box = SERVED_REGION
    replicate = Replicate(name="arena 1", replicate_id="a").with_override(
        CUT, {"region": {"x": box.x, "y": box.y, "width": box.width, "height": box.height}}
    )
    path = directory / "cropping.sieve.yaml"
    Project.for_video(video, directory).with_pipeline(pipeline).with_replicates((replicate,)).save(
        path
    )
    return path


def _cut(project_path: Path, span: SourceSpan) -> Path:
    """Write `SERVED_REGION` over `span`, record it, save. Returns the file."""
    discover()
    project = Project.load(project_path)
    record = materialize_crop(
        project.source_path(project_path),
        SERVED_REGION,
        span,
        name="arena 1",
        project_dir=project_path.parent,
        luma=not Dag.build(project.pipeline).needs_chroma,
    )
    project.with_crop(record).save(project_path)
    return record.resolve(project_path.parent)


def _watch_opens(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Every video the run loop opens, in order, still opening each of them.

    The one thing the printed counts cannot say. A run that drops the crop node
    and then reads the parent reports exactly the numbers a correctly served run
    reports, and every frame it produces is a whole frame where a box was asked
    for.
    """
    opened: list[Path] = []
    real = run_cmd.frame_source

    def watching(video: Path, *, luma: bool) -> PrefetchFrameSource:
        opened.append(video)
        return real(video, luma=luma)

    monkeypatch.setattr(run_cmd, "frame_source", watching)
    return opened


def test_a_served_run_elides_the_crop_node_its_file_already_holds(
    synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The artifact *is* the crop node's output, so the run must not cut again.

    Two invocations of one project either side of the box being written, and the
    difference between them is the whole claim: the same frames answered, one
    node's worth of work gone, and the parent not opened. Fails both ways a
    route can fail — a run that opens the artifact and still runs `crop` cuts a
    box out of a box, and one that drops the node but reads the parent
    downsamples whole frames under the artifact's keys, which is a wrong answer
    with no symptom.

    Dropped rather than neutralised at `crop.WHOLE_FRAME`, which is
    `adr/a-users-file-wires-in-like-any-other-input.md`'s call and is what the
    node count here is the observable of.
    """
    path = _cropping(synthetic_video, tmp_path, STREAMING)
    frames = f"{SERVED_SPAN.start}:{SERVED_SPAN.end}"
    unserved = runner.invoke(app, ["run", str(path), "--frames", frames])
    artifact = _cut(path, SERVED_SPAN)
    opened = _watch_opens(monkeypatch)

    served = runner.invoke(app, ["run", str(path), "--frames", frames])

    assert unserved.exit_code == 0, unserved.output
    assert served.exit_code == 0, served.output
    answered = SERVED_SPAN.frame_count
    assert unserved.output.splitlines() == [
        f"arena 1: {answered} frames, {answered * 2} node outputs computed, 0 from cache"
    ]
    assert served.output.splitlines() == [
        f"arena 1: {answered} frames, {answered} node outputs computed, 0 from cache"
    ]
    assert opened == [artifact]


@pytest.mark.parametrize(
    ("cut", "serves"),
    [
        (WINDOW, True),
        (SourceSpan(start=WINDOW.start + 1, end=WINDOW.end), False),
        (SourceSpan(start=WINDOW.start, end=WINDOW.end - 1), False),
    ],
    ids=["covers-the-window", "a-frame-short-at-the-lead-in", "a-frame-short-at-the-lookahead"],
)
def test_a_served_run_is_matched_against_the_window_it_reads_not_its_span(
    synthetic_video: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cut: SourceSpan,
    serves: bool,
) -> None:
    """`resolve` is handed `decode_range`, and this is the caller that hands it.

    Every one of these three records covers `WINDOWED_SPAN` outright, so a
    command resolving against the span serves all three — and then reads
    twenty-five frames from a file holding at most twenty-five, off by one at
    whichever end is short. The covering row is exact at both ends, so widening
    the clause to `>=` on either side fails here too, and without it the two
    short rows would pass against a command that had stopped serving anything.

    The pair of assertions is what makes a row mean something: which file was
    opened, and whether the crop node ran. Serving is both or neither.
    """
    path = _cropping(synthetic_video, tmp_path, WINDOWED)
    artifact = _cut(path, cut)
    parent = Project.load(path).source_path(path)
    opened = _watch_opens(monkeypatch)

    result = runner.invoke(
        app, ["run", str(path), "--frames", f"{WINDOWED_SPAN.start}:{WINDOWED_SPAN.end}"]
    )

    assert result.exit_code == 0, result.output
    answered = WINDOWED_SPAN.frame_count
    ran = len(WINDOWED.nodes) - (1 if serves else 0)
    assert result.output.splitlines() == [
        f"arena 1: {answered} frames, {answered * ran} node outputs computed, 0 from cache"
    ]
    assert opened == [artifact if serves else parent]


def test_a_checkpointed_crop_node_is_not_elided(
    synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A node someone asked to keep is a node that runs, artifact or not.

    Dropping it would leave the manifest naming a key this run never looked
    anything up under — a plan does not answer for a node its graph no longer
    holds — so the record buys nothing here and the run reads the parent. Fails
    as a traceback out of the writer's key map for a route that elides on the
    record alone.
    """
    path = _cropping(synthetic_video, tmp_path, STREAMING)
    Project.load(path).with_outputs((CUT,), ()).save(path)
    _cut(path, SERVED_SPAN)
    parent = Project.load(path).source_path(path)
    opened = _watch_opens(monkeypatch)

    result = runner.invoke(
        app, ["run", str(path), "--frames", f"{SERVED_SPAN.start}:{SERVED_SPAN.end}"]
    )

    assert result.exit_code == 0, result.output
    answered = SERVED_SPAN.frame_count
    assert f"arena 1: {answered} frames, {answered * 2} node outputs computed" in result.output
    assert f"checkpointed {CUT}" in result.output
    assert opened == [parent]
