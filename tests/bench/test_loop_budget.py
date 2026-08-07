"""Phase 6's gate: the loop's two regimes, measured, with no Qt in the process.

Everything in `bench/` up to here declares. This file is the first thing in the
repo that puts a clock on a ceiling and reports what the clock said, which is
what turns twelve numbers into a claim about the product. VISION's argument is
that tuning feels direct; the number that settles it is the one taken *before*
a widget exists, because a measurement taken through the GUI can no longer tell
a slow pipeline from a slow paint.

**The workload is the oracle's, imported and not respelled.** VISION's scope
note promises these ceilings for a reference workload — the stirred clip through
the chain the preview session runs — and `tests/integration/test_v2_oracle.py`
already holds that chain: `crop -> block_signal -> detect` over `stirred_clip`,
the graph both repos' CLIs were compared on. A second spelling here would be a
second reference workload, and the first symptom would be a budget that held
against a chain nothing else runs. So `graph()` and `SPAN` are imported from it.
What is *not* imported is its replicates and checkpoints: those are about a run
leaving files behind, and a preview is one viewport that writes nothing.

**Both regimes, and only one of them has a pipeline in it.** The in-pipeline
pair is the preview session's own — `full_preview_render` around a window and
`slider_to_preview` around the single frame a drag asks for. The pre-pipeline
budgets are measured through `decode/reader.py` and not through a session,
because *pre-pipeline means before a pipeline exists*: opening a file and
scrubbing it are a player's gestures, and a session over an empty graph would be
a fiction invented to route the number through this module. The reader is the
session's own collaborator, so the boundary being measured is the one the loop
actually stands on. `cut_to_ready` is the fourth pre-pipeline budget and is not
measured here: confirming a cut writes a crop artifact, the command that does it
headless is not built
(`todo/the-materialize-command-derives-what-v2-was-handed.md`), and
`todo/cut-to-ready-gets-a-headless-referent.md` holds the gap.

**Every gate is a median, and no single sample is allowed to miss either.**
`Recorder.median_ms` argues the median: one page fault should not fail a gate.
But a series whose median passes while a sample misses by 400 ms is the preview
a user calls janky, so `test_no_single_sample_missed_its_ceiling` asserts the
bus's own per-sample verdict as well — the same verdict `preview_cmd` prints as
`MISS by`. Two readings of one series, not two statistics for one gate.

**A gate over an empty series passes and means nothing**, which is the failure
that matters most in a file whose assertions are all inequalities. Every key
therefore carries a sample count assertion, and the samples come from the metric
bus rather than from local `perf_counter` arithmetic, so a key the session
stopped publishing is an empty series and a red test rather than a silent one.

The numbers themselves do not live here — a passing budget test tells the next
reader nothing about the margin, and margin is what says whether the GUI has
room to spend. They are in
`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md`, with the machine
they were taken on and the caveat that outranks the margin: the reference clip
is 160x120, and a ceiling met on it is not yet a ceiling met on 5.3K footage.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter

import pytest

from sieve.bench.budgets import IN_DEBT, check
from sieve.bench.metrics import MetricBus, Recorder, Sample
from sieve.core.pipeline_model import Pipeline
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import graph_needs_chroma
from sieve.pipeline.preview import PreviewSession
from sieve.tools import discover
from tests.integration.test_v2_oracle import DETECTOR, SPAN, graph

#: Fresh opens of the container, each followed by its first frame. Repeated
#: because the first open of a process pays for whatever the OS has not cached
#: yet, and a budget stated from that one sample would describe a cold machine
#: rather than the gesture.
OPENS = 5

#: Where a scrub lands, as source indices in the order they are visited. They
#: alternate direction so the median is over both of the reader's strategies
#: rather than over whichever one a monotone sweep hits: a backward jump can
#: only seek, a forward one grabs. The third path is unreachable on this
#: fixture — `reader.GRAB_FORWARD_LIMIT` is 40 and the clip is 40 frames, so no
#: forward jump here is long enough to fall back to a seek.
SCRUB_STOPS = (30, 3, 25, 8, 19, 1, 35, 12, 27, 5, 33, 16)

#: A scrub *release*, as (where the drag was when the user let go, the frame
#: actually under the cursor). Two decodes, which is what the budget's anchor
#: says it is paying for: one in-flight decode that cannot be cancelled plus the
#: exact one.
SETTLES = ((30, 28), (3, 5), (25, 22), (8, 10), (19, 17), (35, 31))

#: Detection windows dragged through, in order. The first is the graph's own, so
#: the first render is the cold one and every render after it follows an edit —
#: which is the interval the loop is about. On the detector because it is the
#: graph's last node: an edit there must leave the two nodes above it keyed
#: exactly as they were, and a session that re-ran the graph would show up here
#: as a `full_preview_render` that never gets cheaper.
WINDOWS = (9, 7, 11, 5, 13)

#: Where the playhead is put during the drag, as source indices inside the
#: window. After the window has been rendered once, because that is when a user
#: drags: the store is warm and the frame under the cursor is the only thing
#: being asked for.
PLAYHEAD_STOPS = (5, 12, 20, 25, 8, 17, 2, 27)

#: Qt in the process would make the whole measurement a different claim. Named
#: rather than probed by prefix so the assertion says what it is looking for.
QT_MODULES = ("PyQt6", "PyQt5", "PySide6", "PySide2")


def within_budget(key: str, elapsed_ms: float) -> None:
    """Fail unless `elapsed_ms` meets `key`'s ceiling, or xfail if it is in debt.

    The one call site shape `budgets.TIMED` is derived from, so a benchmark that
    measures a key without judging it cannot be mistaken for one that does —
    `tests/bench/test_budget_producers.py` scans for exactly this call and fails
    in both directions.

    A debt is xfailed rather than passed, which is `budgets.py`'s rule: the miss
    stays in the report next to the item that repays it, instead of becoming a
    green line that says the ceiling was met.
    """
    debt = check(key, elapsed_ms, honor_debt=True)
    if debt is not None:
        pytest.xfail(f"{key} is in debt against {debt.item}: {debt.why}")


@dataclass(frozen=True, slots=True)
class Reading:
    """One pass over the reference workload, as the samples it published.

    Keyed by budget key rather than by phase: what a gate asks is "what did this
    ceiling measure", and a reader that had to know which phase produced a key
    would be re-deriving the structure of the run to read its result.
    """

    samples: Mapping[str, tuple[Sample, ...]]

    def median_ms(self, key: str) -> float:
        """Median interval published under `key`.

        Raises:
            KeyError: if nothing was published under it. A gate over an empty
                series passes vacuously, so the collection layer refuses first.
        """
        return median(sample.elapsed_ms for sample in self[key])

    def worst(self, key: str) -> Sample:
        """The slowest sample published under `key`."""
        return max(self[key], key=lambda sample: sample.elapsed_ms)

    def misses(self) -> tuple[Sample, ...]:
        """Every sample that exceeded its ceiling, across every key."""
        return tuple(
            sample
            for samples in self.samples.values()
            for sample in samples
            if not sample.within_budget
        )

    def __getitem__(self, key: str) -> tuple[Sample, ...]:
        samples = self.samples.get(key)
        if not samples:
            raise KeyError(f"nothing was measured under {key!r}")
        return samples


def _edited(pipeline: Pipeline, window_frames: int) -> Pipeline:
    """`pipeline` with the detector's window moved — one slider, one value.

    Through `model_copy` on the node rather than through `Project.with_param_edit`
    because there is no replicate here to pin it on: a preview of the baseline
    runs the node's own parameters, and this is the smallest thing an edit can be.
    """
    node = pipeline.node(DETECTOR)
    moved = node.model_copy(update={"params": {**node.params, "window_frames": window_frames}})
    return pipeline.model_copy(
        update={
            "nodes": tuple(
                moved if candidate.node_id == DETECTOR else candidate
                for candidate in pipeline.nodes
            )
        }
    )


def _pre_pipeline(bus: MetricBus, video: Path) -> None:
    """Open, scrub, and release, published as the three pre-pipeline ceilings.

    `VideoReader` and not `PrefetchFrameSource`: prefetch reads ahead of a
    consumer walking a span, which is a run. A scrub is random access with no
    next index to guess, so the reader is the whole of what a player would have.

    BGR rather than luma, for the same reason the reader defaults that way: a
    frame shown to a user before any tool exists is a displayed frame, and no
    graph has yet asked for the cheaper plane.
    """
    for _ in range(OPENS):
        started = perf_counter()
        with VideoReader(video) as reader:
            reader.read(0)
        bus.publish("open_to_first_frame", (perf_counter() - started) * 1000.0)

    with VideoReader(video) as reader:
        for index in SCRUB_STOPS:
            started = perf_counter()
            reader.read(index)
            bus.publish("scrub_to_repaint", (perf_counter() - started) * 1000.0, detail=str(index))
        for in_flight, exact in SETTLES:
            started = perf_counter()
            reader.read(in_flight)
            reader.read(exact)
            bus.publish("scrub_settle", (perf_counter() - started) * 1000.0, detail=str(exact))


@pytest.fixture(scope="module")
def reading(stirred_clip: Path) -> Iterator[Reading]:
    """One pass over the reference workload: open, scrub, render, drag.

    Module-scoped and run once. Each gate below reads one key out of it, so the
    file measures the loop a single time and then asks it several questions —
    rather than re-decoding the clip per assertion, which would make the gates
    disagree about which run they were judging.

    The recorder is emptied between the window renders and the drags, and that
    is not tidiness: `render_window` publishes `slider_to_preview` around its own
    first frame, which is the cold decode of a window and not a drag. Pooled with
    the drags it would raise the median of the ceiling that decides whether
    direct manipulation is direct — by exactly the interval the store exists to
    keep out of it.
    """
    discover()
    pipeline = graph()
    bus = MetricBus()
    recorder = Recorder()
    bus.subscribe(recorder.record)

    _pre_pipeline(bus, stirred_clip)
    collected = {key: recorder.samples(key) for key in recorder.keys}

    luma = not graph_needs_chroma(pipeline)
    with PrefetchFrameSource(stirred_clip, luma=luma) as reader:
        session = PreviewSession(
            source=source_identity(stirred_clip),
            reader=reader,
            window=SPAN,
            measure=bus.measure,
            store=MemoryFrameStore(),
        )
        recorder.clear()
        for window_frames in WINDOWS:
            session.render_window(_edited(pipeline, window_frames))
        collected["full_preview_render"] = recorder.samples("full_preview_render")

        recorder.clear()
        for index in PLAYHEAD_STOPS:
            session.render_frame(_edited(pipeline, WINDOWS[-1]), index)
        collected["slider_to_preview"] = recorder.samples("slider_to_preview")

    yield Reading(samples=collected)


# ---- pre-pipeline: the video-editor regime -------------------------------


def test_opening_the_clip_shows_its_first_frame(reading: Reading) -> None:
    """The one pre-pipeline budget that is not a per-gesture ceiling.

    500 ms is a "something is happening" latency, and what fills it is the
    container open rather than the decode — which is why the sample covers both
    and cannot be met by a faster tool.
    """
    assert len(reading["open_to_first_frame"]) == OPENS
    within_budget("open_to_first_frame", reading.median_ms("open_to_first_frame"))


def test_a_scrub_repaints_inside_the_perceptual_threshold(reading: Reading) -> None:
    """100 ms, over jumps that take the reader's grab path and its seek path.

    v2 measured ~68 ms for a random seek into 5.3K H.264, of which ~47 ms was
    the container seek — so this passing on the reference clip is a statement
    about the reference clip, and the finding says so.
    """
    assert len(reading["scrub_to_repaint"]) == len(SCRUB_STOPS)
    within_budget("scrub_to_repaint", reading.median_ms("scrub_to_repaint"))


def test_releasing_the_scrubber_lands_on_the_exact_frame(reading: Reading) -> None:
    """250 ms for two decodes, which is what the anchor budgets for."""
    assert len(reading["scrub_settle"]) == len(SETTLES)
    within_budget("scrub_settle", reading.median_ms("scrub_settle"))


# ---- in-pipeline: the direct-manipulation regime -------------------------


def test_the_whole_window_renders_inside_the_attention_band(reading: Reading) -> None:
    """3 s for the window, over one cold render and four that followed an edit.

    The cold sample stays in the series rather than being reported apart from
    it: a user meets the cold render first, and a gate that excluded it would be
    judging the ceiling on the renders the store already made cheap.
    """
    assert len(reading["full_preview_render"]) == len(WINDOWS)
    within_budget("full_preview_render", reading.median_ms("full_preview_render"))


def test_the_slider_path_repaints_inside_one_perceived_beat(reading: Reading) -> None:
    """100 ms, and the number VISION's whole argument rests on.

    Measured on a warm store at eight playhead positions, because that is the
    gesture: the window has been rendered and the user is dragging across it.
    """
    assert len(reading["slider_to_preview"]) == len(PLAYHEAD_STOPS)
    within_budget("slider_to_preview", reading.median_ms("slider_to_preview"))


# ---- what the medians above cannot say -----------------------------------


def test_no_single_sample_missed_its_ceiling(reading: Reading) -> None:
    """A median that passes over a sample that missed is a janky preview.

    The bus judged each sample against `BUDGETS` on the way past, so this is one
    pass over what arrived rather than a second opinion about the table.
    """
    missed = [
        f"{sample.key} took {sample.elapsed_ms:.1f} ms, over by {sample.over_ms:.1f}"
        for sample in reading.misses()
        if sample.key not in IN_DEBT
    ]
    assert missed == []


def test_the_measurement_ran_with_no_qt_in_the_process(reading: Reading) -> None:
    """The claim the phase is named for, and the only one a later run can lose.

    Phase 7 measures these same ceilings through the GUI. If Qt were resident
    here, a regression that appeared then could not be attributed to it — which
    is the entire reason this number is taken before a widget exists.
    """
    del reading
    assert [name for name in QT_MODULES if name in sys.modules] == []
