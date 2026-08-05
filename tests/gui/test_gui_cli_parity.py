"""A pipeline saved from the GUI produces the same numbers in the CLI.

AUTO-GUARDRAILS §2's open half, and rule 1's only measurement. What is checked
elsewhere is that a second execution path is hard to *assemble* — `gui/` sits
above `pipeline/`, `decode/` is the only route to a frame — which is an argument
about how the code is arranged. This is the argument's premise tested against
output: the same document, run through both front ends, has to yield the same
per-frame series and the same intervals.

**Schema-independent, deliberately.** `tests/gui/test_project_io.py` catches a
field that fails to round-trip; a round-trip test cannot catch the failure this
exists for, which is both sides reading a field and *resolving it differently*
— `edited_params` against a moved baseline, a detector pin the CLI merges in a
different order, a clip that reaches the span by one route and the window by
another. Those produce a plausible frame, and a plausible frame is what rule 6
exists to refuse.

**Output, not the plan.** Comparing resolved plans would pass while both sides
compute the same wrong thing, and would fail on every field that is
legitimately "where it lives and how fast it arrives" rather than "what a result
is" — rule 7's identity line, which the plan straddles on purpose.

**The GUI side is driven through the runner, not around it.** `PreviewRunner` +
`SeriesCollector` + `detector_worker.derive` is what `gui/filter_tab.py` does
with a widget wrapped round it, down to reading `runner.revision + 1` on the GUI
thread immediately before submitting. Reimplementing the resolution here — a
plan built directly, a `detect()` called with settings the test merged itself —
would compare the CLI against this file rather than against the application.

**The document has to be able to disagree with itself.** Two arenas that resolve
to identical parameters would make every assertion below pass against a CLI that
ignored replicate pins entirely. So the two arenas pin different block sizes and
different detection windows, and `test_the_two_arenas_are_not_running_the_same
_thing` fails if that ever stops being true — the guard that keeps the rest of
this module from going quietly vacuous.

**Which is also why this module writes its own footage.** The shared
`synthetic_video` is a spatially uniform ramp, so change energy is constant in
both space and time: every block sits in every band, the count saturates at the
block total, and the windowed mean of a constant is that constant. Under it a
pinned `D` is unobservable and the interval assertions pass against a front end
that drops the detector pin. `stirred_clip` has two bursts of motion, one inside
each arena at different frames, and `VALUE_FLOOR` / `COUNT_FLOOR` were measured
against its band-power distribution rather than guessed — at these values each
arena's intervals move when its own `D` moves, which is what makes the pin
load-bearing in the output and not merely present in the document.

Nothing here is sensitive to how faithfully the encoder reproduces those bursts.
Both front ends read the *same file*, so a build whose mp4v output differs
slightly moves both sides together; what a codec difference could reach is the
guard test, and its two arenas differ by their block grid and by intervals
fifteen frames apart.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytest
from pytestqt.qtbot import QtBot
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from sieve.core.types import ROI
from sieve.gui.chain_model import DetectorState
from sieve.gui.detector_worker import DetectorRequest, derive
from sieve.gui.document import ReplicateDocument
from sieve.gui.preview_runner import PreviewRunner
from sieve.pipeline.executor import FrameResult
from sieve.pipeline.series_collector import SeriesCollector

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 10_000
RENDER_TIMEOUT_MS = 60_000

#: The fixture's shape, spelled here because the document is bound to it before
#: any reader has been opened — which is the real ordering: a GUI knows its
#: source's dimensions from the file dialog's probe, not from a render.
WIDTH, HEIGHT, FRAMES, FPS = 160, 120, 40, 20.0

#: The node the detector's series is taken over on both sides. The CLI finds it
#: as the graph's one sink; the GUI watches it by id. That those two agree is
#: itself part of what is being checked.
SERIES_NODE = "blocks"

#: A window that is neither the whole video nor anchored at zero. Both edges
#: matter: a front end that ran the whole clip fails on the row count, and one
#: that ran the right length from the wrong origin fails on the absolute frame
#: numbers, which are what an interval is stated in.
CLIP_START, CLIP_END = 8, 36

#: `series.csv` columns this module reads. Spelled rather than derived from
#: `series_columns`, because deriving them would make a rename invisible here
#: and `test_the_header_is_a_published_interface` is where a rename is supposed
#: to be argued.
FRAME, TOTAL, IN_BAND, WINDOWED, DETECTED = (
    "frame",
    "blocks_total",
    "blocks_in_band",
    "windowed_mean_blocks",
    "detected",
)

#: The two arenas, and the block size each pins. Top-left and bottom-right, so
#: `stirred_clip`'s two bursts land in one each — an arena whose signal is the
#: other's would show up as identical series under two names.
ARENAS = (
    (ROI(x=0, y=0, width=80, height=64), 16),
    (ROI(x=80, y=56, width=80, height=64), 8),
)

#: The detection window each arena pins, in frames. Different values, and
#: different in a way the *output* can see: at `COUNT_FLOOR` both arenas'
#: intervals move by a frame between these two, so a pin that reached only one
#: front end changes what is claimed rather than only what is stored.
WINDOWS = (5, 9)

#: Band power below this is not counted. Measured, not chosen: over
#: `stirred_clip` the per-block band power spans roughly 1e0 to 1e9 and this sits
#: near the 75th percentile, where each arena's in-band count runs from zero to
#: about a third of its blocks. A wide-open band — the tempting default — counts
#: every block in every frame, and a saturated count makes the threshold, the
#: window, and the gate all unobservable at once.
VALUE_FLOOR = 2.5e8

#: The count threshold, as a fraction of the arena's blocks. Placed on the
#: shoulder of the windowed mean rather than at its foot, which is what makes
#: the gate turn off and on inside the window instead of covering all of it.
COUNT_FLOOR = 0.15


@dataclass(frozen=True)
class Detection:
    """One arena's answer, in the terms both front ends can state it in.

    Not a `DetectorUpdate` and not a CSV row: the two sides hold the same
    numbers in an array and in a file of strings, and the comparable value is
    what survives both spellings. `band_power` is deliberately absent — it is
    an intermediate, and a parity claim about it would fail on the day a
    front end legitimately reuses a cached one.
    """

    #: Absolute source frames the series covers, in order.
    frames: tuple[int, ...]
    #: How many values the series node emitted per frame — the grid, which the
    #: block size decides and which is therefore per-arena here.
    elements: int
    count: tuple[np.float32, ...]
    windowed: tuple[np.float32, ...]
    #: Per frame, or `None` throughout for a disarmed detector. `None` and
    #: `False` are different claims and the tables spell them differently.
    detected: tuple[bool, ...] | None
    intervals: tuple[tuple[int, int], ...] | None


@pytest.fixture(scope="module")
def stirred_clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Footage with motion in one arena and then the other, and nowhere else.

    A textured static background — seeded, so the clip is the same clip on every
    run — with a bright block sweeping through the top-left arena on frames
    12-18 and through the bottom-right arena on frames 24-30. The texture is
    what makes the structure tensor non-degenerate: over a flat field the
    spatial gradients vanish and every block reads the same, which is the shared
    fixture's problem restated.

    Written here rather than added to `tests/conftest.py` because the shared one
    is asserted against by name elsewhere — several tests depend on frame `n`
    being a solid field of `n * 5` — and a fixture two suites disagree about the
    contents of is worse than two fixtures.
    """
    path = tmp_path_factory.mktemp("parity") / "stirred.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        pytest.skip("No usable mp4v encoder in this OpenCV build")
    background = np.random.default_rng(7).integers(40, 90, size=(HEIGHT, WIDTH), dtype=np.uint8)
    for index in range(FRAMES):
        frame = np.dstack([background] * 3).copy()
        if 12 <= index <= 18:
            left = 8 + (index - 12) * 8
            frame[8:40, left : left + 32] = 235
        if 24 <= index <= 30:
            left = 96 + (index - 24) * 6
            frame[64:100, left : left + 28] = 235
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def tuned(qapp: object) -> Iterator[ReplicateDocument]:
    """A document tuned the way a session tunes one, through the commands.

    Every mutation goes through `ReplicateDocument`'s public intents, so the
    two-write mechanism — pin the diff, move the baseline — happens here
    exactly as it happens under a spinbox. A test that assembled a `Project`
    directly would be checking the CLI against a document shape the GUI never
    produces, which is precisely what `tests/integration/test_cli_run.py`
    already does and why it cannot make this claim.
    """
    del qapp
    doc = ReplicateDocument()
    doc.bind_source(WIDTH, HEIGHT, FRAMES, FPS)
    doc.set_pipeline(
        Pipeline(
            nodes=(
                Node(node_id="prep", filter_id="rescale", version="1.0.0", params={"scale": 1.0}),
                Node(
                    node_id=SERIES_NODE,
                    filter_id="block_signal",
                    version="1.0.0",
                    params={"signal": "change_energy", "block": 16, "scale": 1.0, "fps": FPS},
                ),
            ),
            edges=(Edge(upstream="prep", downstream=SERIES_NODE),),
        )
    )
    for roi, _ in ARENAS:
        doc.add_roi(roi)

    # Arena 2 first, then arena 1: the second edit moves the baseline under the
    # first, so arena 1 ends up pinned against a default that has since walked
    # away from it. That is the ordinary consequence of the two-write rule and
    # the state a resolution bug is most likely to get wrong.
    for index in (1, 0):
        doc.select(index)
        doc.edit_params({SERIES_NODE: {"block": ARENAS[index][1]}}, "Block size")

    # Armed on the baseline, with D pinned per arena — so the threshold and the
    # value band are shared and the window they are applied over is not.
    doc.select(0)
    doc.edit_detector(
        {
            "value_band": (VALUE_FLOOR, math.inf),
            "count_frac": (COUNT_FLOOR, math.inf),
            "window_frames": WINDOWS[0],
            "centered": True,
        },
        "Arm",
    )
    doc.select(1)
    doc.edit_detector({"window_frames": WINDOWS[1]}, "Widen D")

    doc.place_window(CLIP_START, CLIP_END)
    doc.select(0)
    yield doc
    doc.deleteLater()


def saved(doc: ReplicateDocument, video: Path, directory: Path) -> Path:
    """The document written by the real writer, where the CLI will read it."""
    path = directory / "arena.sieve.yaml"
    doc.apply_to(Project.for_video(video, directory)).save(path)
    return path


def through_the_gui(qtbot: QtBot, doc: ReplicateDocument, video: Path) -> dict[str, Detection]:
    """Every arena rendered and derived the way the filter tab does it.

    One runner for all of them, because that is the session: the store outlives
    the arena switch, so the second arena is served partly from entries the
    first one wrote — which is the state a key that failed to carry the ROI or
    the resolved parameters would show up in, as one arena's numbers appearing
    under the other's name.
    """
    runner = PreviewRunner()
    runner.open(video)
    qtbot.waitUntil(lambda: runner.is_open, timeout=OPEN_TIMEOUT_MS)
    try:
        return {
            replicate.name: _one_arena(qtbot, runner, doc, index)
            for index, replicate in enumerate(doc.all())
        }
    finally:
        runner.shutdown()


def _one_arena(
    qtbot: QtBot, runner: PreviewRunner, doc: ReplicateDocument, index: int
) -> Detection:
    """Select an arena, render the window, derive over the collected series."""
    doc.select(index)
    collector = SeriesCollector(SERIES_NODE)
    finished: list[object] = []
    failures: list[str] = []
    runner.render_started.connect(collector.start)
    runner.render_finished.connect(finished.append)
    runner.render_failed.connect(failures.append)

    # `filter_tab.resubmit`'s line, and it has to be this one: the consumer
    # runs on the render thread and stamps its rows with the revision that was
    # next when the GUI thread submitted.
    expected = runner.revision + 1

    def feed(result: FrameResult) -> None:
        collector.add(expected, result)

    window = doc.window
    assert window is not None
    assert runner.request_render(doc.pipeline, window, doc.selected_replicate, consumer=feed)
    qtbot.waitUntil(lambda: bool(finished or failures), timeout=RENDER_TIMEOUT_MS)
    assert not failures, failures

    rows = collector.snapshot_rows(runner.revision)
    assert rows is not None, "the render produced no rows for the series node"
    result = derive(
        DetectorRequest(
            revision=runner.revision,
            series=rows.rows,
            start_index=rows.start_index,
            fps=doc.source_fps,
            state=DetectorState.from_settings(
                doc.resolved_detector_for_selection(), solo_block=None
            ),
            # A whole-window render is over, so the record has no moving
            # frontier — the same claim `sieve detect` makes by construction.
            final=True,
        )
    )
    runner.render_started.disconnect(collector.start)
    runner.render_finished.disconnect(finished.append)
    runner.render_failed.disconnect(failures.append)

    update = result.update
    gate = update.gate
    return Detection(
        frames=tuple(range(rows.start_index, rows.start_index + result.frames)),
        elements=result.series2d.shape[1],
        count=tuple(update.count),
        windowed=tuple(update.windowed),
        detected=None if gate is None else tuple(bool(value) for value in gate),
        intervals=update.intervals,
    )


def through_the_cli(project: Path, directory: Path) -> dict[str, Detection]:
    """`sieve detect --csv`, read back as something that is not SIEVE would.

    Through the tables rather than by importing `detect_project`, because the
    tables are where a number stops being an array and becomes the thing a
    person compares — and because a helper called in-process could share a
    resolution mistake with the caller that set it up.
    """
    result = CliRunner().invoke(app, ["detect", str(project), "--csv", str(directory)])
    assert result.exit_code == 0, result.output

    series = _rows(directory / "series.csv")
    intervals_path = directory / "intervals.csv"
    claimed: dict[str, list[tuple[int, int]]] = {}
    if intervals_path.is_file():
        for row in _rows(intervals_path):
            claimed.setdefault(row["replicate"], []).append(
                (int(row["start_frame"]), int(row["end_frame_exclusive"]))
            )

    detections: dict[str, Detection] = {}
    for name in dict.fromkeys(row["replicate"] for row in series):
        arena = [row for row in series if row["replicate"] == name]
        totals = {int(row[TOTAL]) for row in arena}
        assert len(totals) == 1, f"{name} reports {totals} elements across its own rows"
        marks = [row[DETECTED] for row in arena]
        detections[name] = Detection(
            frames=tuple(int(row[FRAME]) for row in arena),
            elements=totals.pop(),
            count=tuple(np.float32(row[IN_BAND]) for row in arena),
            windowed=tuple(np.float32(row[WINDOWED]) for row in arena),
            detected=None if marks[0] == "NA" else tuple(mark == "TRUE" for mark in marks),
            intervals=None if name not in claimed else tuple(claimed[name]),
        )
    return detections


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def both(
    qtbot: QtBot, tuned: ReplicateDocument, stirred_clip: Path, tmp_path: Path
) -> tuple[dict[str, Detection], dict[str, Detection]]:
    """The same tuning, run once through each front end. `(gui, cli)`."""
    project = saved(tuned, stirred_clip, tmp_path)
    return through_the_gui(qtbot, tuned, stirred_clip), through_the_cli(
        project, tmp_path / "tables"
    )


def test_the_two_arenas_are_not_running_the_same_thing(
    tuned: ReplicateDocument, both: tuple[dict[str, Detection], dict[str, Detection]]
) -> None:
    """The guard on every other test here, and it is not a formality.

    Two arenas resolving to identical parameters would make the parity
    assertions below pass against a front end that dropped replicate pins
    altogether — the exact bug they exist to catch, agreeing with itself.

    Two claims, and both are needed. The document has to *hold* deviating pins,
    which is what a fixture rewrite would quietly lose; and the deviation has to
    reach the *output*, which is what a fixture with the wrong footage or the
    wrong bands quietly loses instead. The second is the one this module was
    first written without: over a uniform clip the counts saturate, and the two
    arenas came back with the same intervals under different windows.
    """
    gui, _ = both
    first, second = (gui[name] for name in gui)

    resolved: list[tuple[int, int]] = []
    for index in range(len(tuned.all())):
        tuned.select(index)
        resolved.append(
            (
                tuned.resolved_node_params(SERIES_NODE)["block"],
                tuned.resolved_detector_for_selection().window_frames,
            )
        )
    assert resolved == [(block, window) for (_, block), window in zip(ARENAS, WINDOWS, strict=True)]

    assert first.elements != second.elements
    assert first.intervals != second.intervals
    assert first.detected != second.detected


def test_the_series_the_gui_shows_is_the_series_the_cli_computes(
    both: tuple[dict[str, Detection], dict[str, Detection]],
) -> None:
    """Per arena, per frame, both measured columns.

    The one that fails when resolution diverges: `blocks_total` moves if a
    pinned block size reaches one side and not the other, and the counts move
    if the baseline that walked out from under arena 1 is resolved in the wrong
    order. Both are silent in every other test — a plausible series that is a
    different arena's.
    """
    gui, cli = both
    assert set(gui) == set(cli)
    for name, shown in gui.items():
        computed = cli[name]
        assert computed.frames == shown.frames, name
        assert computed.elements == shown.elements, name
        assert computed.count == shown.count, name
        assert computed.windowed == shown.windowed, name


def test_the_intervals_agree_and_are_stated_in_the_same_frames(
    both: tuple[dict[str, Detection], dict[str, Detection]],
) -> None:
    """What is *claimed*, in absolute source frames, and the gate under it.

    A distinct failure from the one above: the series can match while the
    detector settings resolve differently, because `DetectorSettings` rides
    beside the graph and is merged by its own path (`resolved_detector`). A
    per-arena D that reached one side only would leave the counts identical and
    move every interval bound.

    The frames are absolute on both sides, which is the other half — the CLI
    adds `span.start` in `tables.py` and the GUI adds `start_index` in
    `gate_intervals`, and an off-by-the-lead-in in either is a claim about the
    wrong moment of the footage.
    """
    gui, cli = both
    for name, shown in gui.items():
        computed = cli[name]
        assert computed.detected == shown.detected, name
        assert computed.intervals == shown.intervals, name
        for first, last in computed.intervals or ():
            assert CLIP_START <= first < last <= CLIP_END, name


def test_the_saved_clip_is_the_span_both_front_ends_run(
    both: tuple[dict[str, Detection], dict[str, Detection]],
) -> None:
    """The window the user marked is the window a cluster runs, exactly.

    Its own test because the clip reaches the two sides by genuinely different
    routes — `ReplicateDocument.window` with its unset-means-default fallback
    on one, `cli/common.span_for` off `Project.clip` on the other — so this is
    the assertion that fails if the fallback ever leaks into the saved
    document, or if a lead-in frame is delivered as though it were part of the
    span.
    """
    gui, cli = both
    for side in (*gui.values(), *cli.values()):
        assert side.frames == tuple(range(CLIP_START, CLIP_END))
