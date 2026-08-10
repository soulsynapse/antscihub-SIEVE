"""The same pipeline, run by both repos' CLIs, compared on what came out.

Phase 5's gate. Every parity check before this one pins a kernel: one call, one
array, v2's answer beside v3's. What none of them can see is *composition* —
a graph whose window arithmetic accumulates across three stages, resolved per
replicate, run through a command, and landing as a file. That is what is
compared here, and it is compared as products: the resolved plan is never
diffed, because v3 re-derived the schema and the node graph on purpose and a
plan-level diff would be a test that v3 failed to do what it set out to do.

**The two documents are different by design, and the identity values are what
make "the same pipeline" mechanical.** v2 carried the arena as `Replicate.roi`,
the detector as a `DetectorSettings` beside the graph, and ran a one-node
pipeline; v3 carries all three as nodes — `crop`, `block_signal`, `detect` — and
a replicate deviates through their parameters like anything else
(`adr/detector-is-a-node.md`). The `tool_id` values did not move
(`adr/tools-not-filters.md`), so `blocks` is a `block_signal` node on both
sides and the correspondence is a lookup rather than a judgement. The README
v2 writes beside its tables records the settings it ran under, and
`test_both_documents_configured_the_same_run` reads them back — the "same
pipeline" claim is checked against v2's own account of itself, not asserted
here.

**The reference is v2's *whole-record* answer, and that is the claim.** v2's
detector ran once over the entire series; v3's `detect` is a node answering one
frame at a time from a window it declared — 11 frames of lead-in and 11 of
read-ahead at this band. Those are not the same arithmetic, and the assertion
is that the declared reach is wide enough for them to reach the same *product*:
the transform's leakage past three e-foldings sits at the float32 floor
(`tools/detect.py`, `PAD_EFOLDINGS`), far under the value band and the count
threshold. `tests/unit/test_detect_tool.py` makes that claim for one node over
a synthetic series; what is new here is that it survives a crop and a stateful
extractor in front of it, per-replicate deviation through all three, and the
executor's lag accumulating along the chain. This is where v2's trailing-only
contract failed, and v3's two-sided window (01.3) had not been run end to end.

**Which frames the oracle can answer for is decided by that window.** The
declared read-ahead is charged past the end of the span and the plan does not
clamp it — the reader is asked and the footage is what it is — so the span ends
`lookahead` frames before the end of the clip. `test_the_span_is_the_widest_the
_footage_can_answer_for` derives that rather than trusting the constant. v2 is
run over the whole clip regardless, because a v2 record cut at frame 29 would
have its own contaminated trailing edge and the oracle would be comparing two
edge artifacts instead of two answers.

**CI has no sibling worktree, so the v2 side is a checked-in artifact.** The
three files `sieve detect --csv` writes live under `tests/goldens/oracle_stirred/`
and `REGENERATE` is the exact command that made them, on 03.7's mechanism. A
skip when the worktree is absent is not available: the failure mode of a gate
that goes green because it did not run is the subject of an item of its own
(`docs/todo/a-missing-encoder-skips-the-fixture-and-the-gate-stays-green.md`).

**What is deliberately not compared.** `blocks_in_band` and
`windowed_mean_blocks` are intermediates of v3's `detect`, computed and never
emitted (`tools/detect.py`, `emissions`), so there is no v3 product to hold
them; asserting them would mean this file re-deriving the chain, which is
`test_detect_tool.py`'s job and not an oracle's. What v3 emits is the gate, and
the gate is what a session claims.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from numpy.typing import NDArray
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import (
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    SourceSpan,
    resolved_params,
)
from sieve.core.tool_base import node_lookahead_frames
from sieve.storage.checkpoint_writer import MANIFEST_NAME, checkpoints_dir, replicate_dir
from sieve.tools import discover
from sieve.tools.detect import DetectParams, gate_intervals
from tests.conftest import (
    FIXTURE_FPS,
    FIXTURE_FRAMES,
    FIXTURE_HEIGHT,
    FIXTURE_WIDTH,
    STIRRED_ARENAS,
    STIRRED_BACKGROUND,
    STIRRED_BURSTS,
    STIRRED_FOREGROUND,
    STIRRED_SEED,
)
from tests.projects import rooted_on

runner = CliRunner()

GOLDENS = Path(__file__).resolve().parents[1] / "goldens" / "oracle_stirred"

ARENA, BLOCKS, DETECTOR = "arena", "blocks", "detector"

#: The two replicates, in document order on both sides: display name, the id
#: the checkpoint folder is named for, the arena, the block grid it pins, and
#: the detection window it pins. Two deviations per replicate rather than one,
#: because a single pinned field cannot tell a front end that dropped *this*
#: replicate's overrides from one that dropped the mechanism.
REPLICATES = (
    ("arena-1", "a1", STIRRED_ARENAS[0], 16, 9),
    ("arena-2", "a2", STIRRED_ARENAS[1], 8, 5),
)

#: The band's low edge in Hz, and the only parameter here chosen for the
#: *window* rather than for the footage. The transform's reach is charged at the
#: band's lowest frequency, so the wide-open default would put 165 frames either
#: side of every target and the 40-frame fixture could answer for nothing at
#: all. At 7 Hz it is 11.
FREQ_LO = 7.0

#: Band power below this is not counted, and the fraction of the grid the
#: windowed mean has to reach. Measured against this clip under this band rather
#: than carried from `test_stirred_clip.py`, whose numbers are for the whole
#: frame over the whole bank: here the per-frame count runs from 0 to 14 of
#: arena 1's 20 blocks and 0 to 40 of arena 2's 80, so the threshold sits on a
#: shoulder in both and neither gate is a foregone conclusion.
VALUE_FLOOR = 1e6
COUNT_FRAC = 0.25

#: The frames the run answers for. Derived, not chosen — see
#: `test_the_span_is_the_widest_the_footage_can_answer_for`.
SPAN = SourceSpan(start=0, end=29)

#: What produced `tests/goldens/oracle_stirred/`, run from the repo root, on
#: 03.7's mechanism (`tests/unit/test_downsample.py`). `git diff --quiet` over
#: the whole package rather than over a file list, because this is a run of v2's
#: command and not a call into one kernel: the document model, the replicate
#: model, the dag, the plan, the executor, the decoder, `block_signal`, the
#: `detect` package and the table writer are all on the path, which is most of
#: `src/sieve` and would be a list nobody could check.
#:
#: The clip is spelled out rather than imported for `test_detect_tool.py`'s
#: reason — the regenerating process has v2's `sieve` on its path and not this
#: one's — and what keeps that copy honest is not a string comparison but the
#: parity assertions themselves: footage that drifted from `stirred_clip` moves
#: every gate below. That the *encoded bytes* differ between the two
#: environments and the *decoded frames* do not is what makes regenerating it
#: there legitimate at all
#: (`docs/findings/2026.08.07-the-stirred-clip-survives-its-encoder.md`).
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- src/sieve && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import math, pathlib, tempfile; "
    "import cv2, numpy as np; "
    "from typer.testing import CliRunner; "
    "from sieve.cli.app import app; "
    "from sieve.core.pipeline_model import DetectorSettings, Node, Pipeline, Project; "
    "from sieve.core.replicates import Replicate; "
    "from sieve.core.types import ROI; "
    "d = pathlib.Path(tempfile.mkdtemp()); "
    "v = d / 'stirred.mp4'; "
    "w = cv2.VideoWriter(str(v), cv2.VideoWriter.fourcc(*'mp4v'), 20.0, (160, 120)); "
    "b = np.random.default_rng(7).integers(40, 90, size=(120, 160), dtype=np.uint8); "
    "f = [np.dstack([b] * 3).copy() for _ in range(40)]; "
    "_ = [f[i].__setitem__((slice(8, 40), slice(8 + (i - 12) * 8, 40 + (i - 12) * 8)), 235) "
    "for i in range(12, 19)]; "
    "_ = [f[i].__setitem__((slice(64, 100), slice(96 + (i - 24) * 6, 124 + (i - 24) * 6)), 235) "
    "for i in range(24, 31)]; "
    "_ = [w.write(x) for x in f]; "
    "w.release(); "
    "p = d / 'stirred.sieve.yaml'; "
    "Project.for_video(v, d).model_copy(update={'pipeline': Pipeline(nodes=(Node("
    "node_id='blocks', filter_id='block_signal', version='1.0.0', "
    "params={'signal': 'change_energy', 'block': 16, 'scale': 1.0, 'fps': 20.0}),)), "
    "'replicates': (Replicate(roi=ROI(x=0, y=0, width=80, height=64), name='arena-1', "
    "replicate_id='a1', detector_overrides={'window_frames': 9}), "
    "Replicate(roi=ROI(x=80, y=56, width=80, height=64), name='arena-2', replicate_id='a2', "
    "overrides={'blocks': {'block': 8}}, detector_overrides={'window_frames': 5})), "
    "'detector': DetectorSettings(freq_band=(7.0, math.inf), value_band=(1e6, math.inf), "
    "count_frac=(0.25, math.inf), window_frames=9, centered=True)}).save(p); "
    "r = CliRunner().invoke(app, ['detect', str(p), '--frames', '0:40', '--csv', "
    "'tests/goldens/oracle_stirred', '--workers', '1']); "
    "print(r.output); "
    "raise SystemExit(r.exit_code)"
    '"'
)


def region(arena: tuple[int, int, int, int]) -> dict[str, int]:
    """An arena as the crop node's region parameter.

    A mapping rather than an `ROI`, because a document holds what YAML holds and
    a saved project is what this run is reproducible from — building the node
    from a type the file cannot carry would test a shape no session produces.
    """
    return dict(zip(("x", "y", "width", "height"), arena, strict=True))


def detector_params(window_frames: int) -> DetectParams:
    """v3's spelling of the `DetectorSettings` `REGENERATE` configures.

    One function, so the node's baseline, the replicate's pin and the window
    arithmetic below are three readings of one configuration rather than three
    places a number can be edited.
    """
    return DetectParams(
        freq_band=(FREQ_LO, math.inf),
        value_band=(VALUE_FLOOR, math.inf),
        count_frac=(COUNT_FRAC, math.inf),
        window_frames=window_frames,
        centered=True,
        fps=FIXTURE_FPS,
    )


def graph() -> Pipeline:
    """`crop -> block_signal -> detect`, carrying the first replicate's values.

    The baseline is arena 1's rather than a neutral third setting, matching what
    `Project.with_param_edit` leaves behind after a session configures one arena
    and then deviates the other: the node's parameters are the last configured
    values, and only the second replicate carries pins.
    """
    _, _, arena, block, window = REPLICATES[0]
    return Pipeline(
        nodes=(
            Node(
                node_id=ARENA,
                tool_id="crop",
                version="1.0.0",
                params={"region": region(arena)},
            ),
            Node(
                node_id=BLOCKS,
                tool_id="block_signal",
                version="1.0.0",
                params={
                    "signal": "change_energy",
                    "block": block,
                    "scale": 1.0,
                    "fps": FIXTURE_FPS,
                },
            ),
            Node(
                node_id=DETECTOR,
                tool_id="detect",
                version="1.0.0",
                params=detector_params(window).model_dump(),
            ),
        ),
        edges=(Edge(upstream=ARENA, downstream=BLOCKS), Edge(upstream=BLOCKS, downstream=DETECTOR)),
    )


def replicates() -> tuple[Replicate, ...]:
    """The second arena's three pins, and the first arena following the node.

    Sparse in both levels, which is the document's own rule: arena 1 pins
    nothing because the baseline already holds its values, and arena 2 pins only
    the fields that differ.
    """
    built = []
    for name, replicate_id, arena, block, window in REPLICATES:
        target = Replicate(name=name, replicate_id=replicate_id)
        if (arena, block, window) != REPLICATES[0][2:]:
            target = (
                target.with_override(ARENA, {"region": region(arena)})
                .with_override(BLOCKS, {"block": block})
                .with_override(DETECTOR, {"window_frames": window})
            )
        built.append(target)
    return tuple(built)


def project(video: Path, directory: Path) -> Path:
    """Write v3's half of the oracle beside `video` and return its path."""
    document = Project().model_copy(
        update={
            "pipeline": rooted_on(graph(), video, directory),
            "replicates": replicates(),
            "checkpoints": (BLOCKS, DETECTOR),
        }
    )
    path = directory / "stirred.sieve.yaml"
    Project.model_validate(document).save(path)
    return path


@pytest.fixture(scope="module")
def produced(stirred_clip: Path, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """`sieve run` over the stirred clip, as the folders it left behind.

    Through the command rather than through `execute`, for the reason
    `tests/integration/test_checkpoints.py` states and one more that is this
    file's: what an oracle is comparing is what a cluster produces, and the
    resolution between the document and the loop — which replicate's pins reach
    which node — is exactly the seam a direct call skips.
    """
    directory = tmp_path_factory.mktemp("oracle")
    path = project(stirred_clip, directory)

    result = runner.invoke(app, ["run", str(path), "--frames", f"{SPAN.start}:{SPAN.end}"])

    assert result.exit_code == 0, result.output
    base = checkpoints_dir(stirred_clip, directory)
    return {replicate.replicate_id: replicate_dir(base, replicate) for replicate in replicates()}


def checkpoint(produced: dict[str, Path], replicate_id: str, node_id: str) -> NDArray[np.float32]:
    """One node's checkpointed stack for one replicate.

    Found through the manifest rather than by composing the name, which is what
    the manifest is for: the file is named for its node *and* the product that
    node computed (`storage/checkpoint_writer.py`), and an oracle spelling that
    join itself would agree with a writer that had stopped recording it.
    """
    directory = produced[replicate_id]
    manifest = yaml.safe_load((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    (entry,) = (item for item in manifest["entries"] if item["node_id"] == node_id)
    return np.load(directory / entry["file"])


def gate(produced: dict[str, Path], replicate_id: str) -> NDArray[np.float32]:
    """The detector's per-frame gate, as the one value per frame it emits."""
    stack = checkpoint(produced, replicate_id, DETECTOR)
    assert stack.shape == (SPAN.frame_count, 1, 1), stack.shape
    return stack.reshape(-1)


def rows(name: str, replicate: str) -> list[dict[str, str]]:
    """One replicate's rows of a v2 table, in file order."""
    with (GOLDENS / name).open("r", encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["replicate"] == replicate]


def test_the_span_is_the_widest_the_footage_can_answer_for() -> None:
    """Why the run stops at 29 of 40 frames, derived rather than asserted.

    `ExecutionPlan.decode_range` is unclamped at the trailing end on purpose —
    this module's `plan.py` may not open a container — so a span reaching within
    the declared read-ahead of the last frame asks the reader for footage that is
    not there. The number is the detector's, since nothing above it in this graph
    reads ahead at all, and it is the same for both replicates because the
    transform's reach dominates both pinned windows.
    """
    lookaheads = {
        node_lookahead_frames((DetectParams.spec(), detector_params(window))).frames
        for *_, window in REPLICATES
    }

    assert lookaheads == {11}
    assert SPAN.end + lookaheads.pop() == FIXTURE_FRAMES


def test_both_documents_configured_the_same_run() -> None:
    """v2's own account of what it ran, against v3's document.

    `sieve detect --csv` writes a README naming the settings each replicate was
    detected under, so the correspondence between two differently-shaped
    documents is checkable rather than asserted in a comment here. The node id
    and the tool id are in it too, and they are the same strings on both sides
    because the identity values did not move (`adr/tools-not-filters.md`).
    """
    readme = (GOLDENS / "README.md").read_text(encoding="utf-8")

    for name, _, _, _, window in REPLICATES:
        assert f"### {name}" in readme
        assert f"detection window: {window} frames, centered" in readme
    assert f"signal node: `{BLOCKS}` (`block_signal`), {FIXTURE_FPS:g} fps" in readme
    assert f"frequency band: {FREQ_LO:g} and above Hz" in readme
    assert f"value band: {VALUE_FLOOR:g} and above" in readme
    assert f"count threshold: {COUNT_FRAC} and above" in readme


def test_the_two_replicates_are_not_running_the_same_thing(
    produced: dict[str, Path],
) -> None:
    """The guard on everything below, and it is not a formality.

    Two replicates resolving to the same computation would make every parity
    assertion here pass against a run that dropped per-replicate deviation
    altogether — the bug they exist to catch, agreeing with itself. Two claims
    and both are needed: the pins have to *resolve* differently, which a document
    edit could lose, and the difference has to reach the *output*, which the
    wrong footage or the wrong bands would lose instead.
    """
    first, second = replicates()
    node = graph().node(DETECTOR)
    assert resolved_params(node, first) != resolved_params(node, second)

    grids = [checkpoint(produced, replicate_id, BLOCKS).shape for _, replicate_id, *_ in REPLICATES]
    gates = [gate(produced, replicate_id).tolist() for _, replicate_id, *_ in REPLICATES]
    assert grids[0] != grids[1]
    assert gates[0] != gates[1]
    # And neither is a constant, which is what makes "they differ" a statement
    # about two detections rather than about one detection and one flat line.
    for values in gates:
        assert 0 < sum(values) < len(values)


def test_the_grid_each_replicate_ran_on_is_the_grid_v2_counted_over(
    produced: dict[str, Path],
) -> None:
    """`blocks_total`, per replicate, against the checkpointed grid.

    The column that moves if a pinned block size reaches one side and not the
    other. It is also the denominator of v2's count threshold, so the two sides
    agreeing here is what makes the gate comparison below a comparison of the
    same question.
    """
    for name, replicate_id, _, _, _ in REPLICATES:
        stack = checkpoint(produced, replicate_id, BLOCKS)
        totals = {int(row["blocks_total"]) for row in rows("series.csv", name)}

        assert len(totals) == 1, (name, totals)
        assert totals.pop() == stack[0].size, name


def test_the_gate_v3_emits_is_the_gate_v2_claimed(produced: dict[str, Path]) -> None:
    """Frame by frame, per replicate: the product, and the whole oracle.

    v2 derived this once over 40 frames; v3 derived each value from a 23-frame
    window through three nodes and wrote it to a file. Equality rather than a
    tolerance — the gate is a predicate, and a declared reach too short by even
    one frame moves it at the edges of an event, which is precisely where a
    detection is claimed or not.

    `NaN` is checked for rather than compared, because it is `detect`'s spelling
    of *disarmed* and `bool(nan)` is `True`: a run whose count threshold failed
    to resolve would otherwise arrive here as an all-detected gate.
    """
    for name, replicate_id, _, _, _ in REPLICATES:
        emitted = gate(produced, replicate_id)
        claimed = [row["detected"] == "TRUE" for row in rows("series.csv", name)]

        assert set(emitted.tolist()) <= {0.0, 1.0}, name
        assert [bool(value) for value in emitted] == claimed[SPAN.start : SPAN.end], name


def test_the_intervals_agree_and_are_stated_in_the_same_frames(
    produced: dict[str, Path],
) -> None:
    """What is *claimed*, in absolute source frames rather than in gate offsets.

    A distinct failure from the one above: the frames are absolute on both sides
    by different routes — v2 adds `span.start` in its table writer, v3's come
    from `gate_intervals` over a checkpoint whose manifest carries the span — so
    an off-by-the-lead-in in either is a claim about the wrong moment of the
    footage, with the gate itself identical.

    v2's intervals are clipped to the span before comparison, and that is not a
    weakening: arena 2's event runs past the last frame v3 may answer for, and an
    interval a run did not cover is not an interval it got wrong.
    """
    for name, replicate_id, _, _, _ in REPLICATES:
        claimed = [
            (
                max(SPAN.start, int(row["start_frame"])),
                min(SPAN.end, int(row["end_frame_exclusive"])),
            )
            for row in rows("intervals.csv", name)
        ]
        found = gate_intervals(gate(produced, replicate_id) > 0.0, SPAN.start)

        assert found == [span for span in claimed if span[0] < span[1]], name
        assert found, name


def test_the_checkpoint_says_which_span_it_answers_for(produced: dict[str, Path]) -> None:
    """The manifest, because the comparison above reads a file and not a stream.

    A checkpoint sized for the wrong span would end in the zeros `open_memmap`
    created, and zeros read back as a gate that is off — a wrong answer that
    looks like a right one, which is the one this phase spends effort on.
    """
    for _, replicate_id, *_ in REPLICATES:
        manifest = yaml.safe_load(
            (produced[replicate_id] / MANIFEST_NAME).read_text(encoding="utf-8")
        )
        assert manifest["span"] == {"start": SPAN.start, "end": SPAN.end}
        assert [entry["node_id"] for entry in manifest["entries"]] == [BLOCKS, DETECTOR]


def test_the_regeneration_command_writes_this_folder_over_this_fixture() -> None:
    """A golden the recorded command does not write is a golden nobody can redo.

    The file names are v2's rather than the command's — `write_tables` chooses
    all three — so what `REGENERATE` has to name is the folder, and what this
    checks beside it is that the folder holds exactly the three files that
    command writes and nothing that arrived some other way.

    The second half is this oracle's own hazard and did not exist for a kernel
    golden: the command builds its own copy of `stirred_clip` in v2's
    environment, and a copy that drifted from `tests/conftest.py` would produce
    three files that load and compare exactly as well as correct ones. The
    fragments below are built from the fixture's constants, so a constant that
    moves without the command moving fails here rather than silently minting a
    golden for footage nothing runs on.
    """
    assert sorted(path.name for path in GOLDENS.iterdir()) == [
        "README.md",
        "intervals.csv",
        "series.csv",
    ]
    assert f"'tests/goldens/{GOLDENS.name}'" in REGENERATE

    for fragment in (
        f"default_rng({STIRRED_SEED})",
        f"integers({STIRRED_BACKGROUND[0]}, {STIRRED_BACKGROUND[1]}",
        f"size=({FIXTURE_HEIGHT}, {FIXTURE_WIDTH})",
        f"({FIXTURE_WIDTH}, {FIXTURE_HEIGHT})",
        f"range({FIXTURE_FRAMES})",
        f"), {STIRRED_FOREGROUND})",
        f"range({STIRRED_BURSTS[0][0]}, {STIRRED_BURSTS[0][1] + 1})",
        f"range({STIRRED_BURSTS[1][0]}, {STIRRED_BURSTS[1][1] + 1})",
        f"'0:{FIXTURE_FRAMES}'",
    ):
        assert fragment in REGENERATE, fragment


def test_the_tools_the_oracle_runs_are_the_ones_v2_named() -> None:
    """Three nodes on this side, and the two v2 spells are spelt the same.

    `adr/tools-not-filters.md` froze the identity values so that a parity fixture
    keeps meaning what it says. This is where that is cashed: v2's tables record
    `block_signal` as the filter that produced the series, and the graph below
    reaches it under the same string through a registry that never heard of v2.
    """
    discover()
    tools = [node.tool_id for node in graph().nodes]

    assert tools == ["crop", "block_signal", "detect"]
    assert {row["filter"] for row in rows("series.csv", REPLICATES[0][0])} == {"block_signal"}
