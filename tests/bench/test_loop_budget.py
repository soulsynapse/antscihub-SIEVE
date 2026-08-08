"""Phase 6's gate: the loop's two regimes, measured, with no Qt in the code.

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
budgets are the preview session's own — `full_preview_render` around a window,
`slider_to_preview` around the single frame a drag asks for, and
`slider_to_graph` around a `SeriesCollector` refill, which is the same render
carried on to the array a graph is drawn from. The pre-pipeline
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

**Every gate is a median over its own series, and no sample anywhere in the run
is allowed to miss.** `Recorder.median_ms` argues the median: one page fault
should not fail a gate. But a series whose median passes while a sample misses
by 400 ms is the preview a user calls janky, so
`test_every_sample_the_run_published_is_gated` asserts the bus's own per-sample
verdict as well — the same verdict `preview_cmd` prints as `MISS by`.

Those are two readings of the *run*, over two different collections, and
`Reading` keeps them apart because narrowing one must not narrow the other. A
median gate wants the samples its own gesture published and no others, which is
what the fixture's clears cut it down to. The per-sample gate wants everything
the run published, the dropped samples included — a first frame that decodes is
the largest `slider_to_preview` of the run, so a guard reading only the survivors
sat further from firing than its own numbers suggested
(`docs/findings/2026.08.07-the-per-sample-gate-cannot-see-the-cold-first-frame.md`).
`Reading.published` is therefore flat and in arrival order rather than keyed: no
median can be taken over it by accident.

**A gate over an empty series passes and means nothing**, which is the failure
that matters most in a file whose assertions are all inequalities. Every key
therefore carries a sample count assertion, and the samples come from the metric
bus rather than from local `perf_counter` arithmetic, so a key the session
stopped publishing is an empty series and a red test rather than a silent one.

**Two of the readings here are judged by no ceiling, and that is deliberate.**
The reuse split and the collector's share of a refill are numbers the finding's
argument rests on — which mechanism makes a post-edit render cheap, and whether a
longer window would cost the render or the assembly — and neither has a ceiling
anyone has argued for. They are produced by this pass anyway, because the
alternative is what happened three times: a session builds a scratch probe,
reports the number, and deletes it, so no review can re-run it and the next
change to what may be keyed re-orders the same harness from nothing
(`todo/the-reuse-figure-has-no-committed-probe.md`). What they assert is the
shape the mechanism forces, so a change to the admission rule is red here rather
than unmeasured.

The numbers themselves do not live here — a passing budget test tells the next
reader nothing about the margin, and margin is what says whether the GUI has
room to spend. They are in
`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md`, with the machine
they were taken on and the caveat that outranks the margin: the reference clip
is 160x120, and a ceiling met on it is not yet a ceiling met on 5.3K footage.
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
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
from sieve.pipeline.preview import PreviewRender, PreviewSession
from sieve.pipeline.series_collector import SeriesCollector
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

#: Detection windows dragged through again, with a collector on the detector —
#: the same gesture as `WINDOWS` above, asked the other half of the question.
#: Values none of `WINDOWS` used, so every one of these is a real post-edit
#: render; the store is warm by the time they run, which is when a user drags.
#: No cold render among them, and that is the difference from `WINDOWS`: the 3 s
#: ceiling is judged including the cold one because a user meets it, while
#: `slider_to_graph` is a per-gesture ceiling and the first render is not a
#: gesture.
GRAPH_EDITS = (6, 10, 8, 12, 4)

#: Qt reached by anything this file measures through would make the whole
#: measurement a different claim. Named rather than probed by prefix so the
#: assertion says what it is looking for.
QT_MODULES = ("PyQt6", "PyQt5", "PySide6", "PySide2")

#: What the pass above runs on, as a fresh interpreter would have to import to
#: run it. The four packages the fixture reaches into and no more: naming
#: `sieve` whole would prove the tree is Qt-free rather than that the
#: measurement is, which is a claim `.importlinter`'s `headless` contract
#: already makes and this one deliberately does not repeat.
MEASURED_MODULES = (
    "sieve.bench.metrics",
    "sieve.decode.prefetch",
    "sieve.decode.reader",
    "sieve.pipeline.preview",
    "sieve.pipeline.series_collector",
    "sieve.tools",
)


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

    #: What each median gate reads: the samples that gate's own gesture
    #: published, narrowed by the fixture's clears. A subset of `published` for
    #: the two keys more than one stage publishes under.
    gated: Mapping[str, tuple[Sample, ...]]
    #: Every sample the run published, in arrival order across all keys. Flat
    #: rather than keyed so that nothing can take a median over it — see the
    #: module docstring.
    published: tuple[Sample, ...]
    #: Rows each `GRAPH_EDITS` refill assembled, in order. Not a timing and here
    #: anyway: `slider_to_graph` is the one gate whose subject can be fast by
    #: being empty, because a collector that assembled nothing publishes the
    #: same span shape as one that assembled the window.
    rows_per_refill: tuple[int, ...]
    #: What each `WINDOWS` render did, in order — the cold one first. Per render
    #: and not summed over the run, because the reuse row's claim is about one
    #: post-edit render and a total would average the cold one into it.
    window_renders: tuple[PreviewRender, ...]
    #: The window render nested inside each `GRAPH_EDITS` refill, in order. Held
    #: apart from `gated["full_preview_render"]`, which is the second stage's
    #: series: the subtraction below is only meaningful against the render a
    #: refill's own span contained.
    refill_renders: tuple[Sample, ...]

    @property
    def stack_shares(self) -> tuple[float, ...]:
        """Milliseconds each refill spent outside the render it wrapped.

        The collector's own cost, by subtraction rather than by a second clock:
        a refill publishes `slider_to_graph` around a render that publishes
        `full_preview_render` inside it, so the difference is already measured
        and only needs pairing.

        Raises:
            ValueError: if the two series are different lengths, which means the
                samples being subtracted are not one gesture's.
        """
        return tuple(
            refill.elapsed_ms - render.elapsed_ms
            for refill, render in zip(self["slider_to_graph"], self.refill_renders, strict=True)
        )

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
        """Every sample the run published that exceeded its ceiling.

        Over `published` and not over `gated`: a sample a median gate excluded
        still happened, and the ones excluded here are the slowest of their key.
        """
        return tuple(sample for sample in self.published if not sample.within_budget)

    def __getitem__(self, key: str) -> tuple[Sample, ...]:
        samples = self.gated.get(key)
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
    """One pass over the reference workload: open, scrub, render, drag, refill.

    Module-scoped and run once. Each gate below reads one key out of it, so the
    file measures the loop a single time and then asks it several questions —
    rather than re-decoding the clip per assertion, which would make the gates
    disagree about which run they were judging.

    The recorder is emptied between the stages, and that is not tidiness:
    `render_window` publishes `slider_to_preview` around its own first frame,
    which is the cold decode of a window and not a drag. Pooled with the drags it
    would raise the median of the ceiling that decides whether direct
    manipulation is direct — by exactly the interval the store exists to keep out
    of it. The refills of the third stage publish both of the earlier stages'
    keys again, for the same reason and with the same consequence.

    That narrowing is per gate and stops there, which is the whole of what
    `run` is for: it is subscribed alongside and never emptied, so the samples
    each clear drops still reach `Reading.published` and the per-sample gate
    still judges them. A clear that also removed them from the run would be a
    filter on the collection wearing the argument for a filter on one statistic.
    """
    discover()
    pipeline = graph()
    bus = MetricBus()
    recorder = Recorder()
    run: list[Sample] = []
    bus.subscribe(recorder.record)
    bus.subscribe(run.append)

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
        renders = [
            session.render_window(_edited(pipeline, window_frames)) for window_frames in WINDOWS
        ]
        collected["full_preview_render"] = recorder.samples("full_preview_render")

        recorder.clear()
        for index in PLAYHEAD_STOPS:
            session.render_frame(_edited(pipeline, WINDOWS[-1]), index)
        collected["slider_to_preview"] = recorder.samples("slider_to_preview")

        recorder.clear()
        collector = SeriesCollector(DETECTOR, measure=bus.measure)
        rows: list[int] = []
        for window_frames in GRAPH_EDITS:
            with collector.refill() as consume:
                session.render_window(_edited(pipeline, window_frames), on_frame=consume)
            series = collector.series
            rows.append(0 if series is None else int(series.data.shape[0]))
        collected["slider_to_graph"] = recorder.samples("slider_to_graph")
        # After this stage's clear, so these are the refills' own renders and not
        # the second stage's — which is what `stack_shares` may subtract.
        refill_renders = recorder.samples("full_preview_render")

    yield Reading(
        gated=collected,
        published=tuple(run),
        rows_per_refill=tuple(rows),
        window_renders=tuple(renders),
        refill_renders=tuple(refill_renders),
    )


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


def test_the_graph_refills_within_two_perceived_beats(reading: Reading) -> None:
    """200 ms, and the other half of PLAN.md's Phase 6 gate.

    The span is a post-edit window render plus the stack that makes it drawable,
    which is what a user's drag actually costs once the store is warm. Judged
    over five edits and never over the cold render, because the ceiling is a
    per-gesture one and the first render of a window is not a gesture — the 3 s
    ceiling above is where that render is answered for.

    The row count is asserted for the reason the module docstring gives about
    empty series, one layer down: every other gate here goes vacuous only if the
    *samples* vanish, while this one also goes vacuous if the samples arrive
    around a collector that assembled nothing.
    """
    assert len(reading["slider_to_graph"]) == len(GRAPH_EDITS)
    assert reading.rows_per_refill == (SPAN.frame_count,) * len(GRAPH_EDITS)
    within_budget("slider_to_graph", reading.median_ms("slider_to_graph"))


# ---- what the medians above cannot say -----------------------------------


def test_every_sample_the_run_published_is_gated(reading: Reading) -> None:
    """A median that passes over a sample that missed is a janky preview.

    The bus judged each sample against `BUDGETS` on the way past, so this is one
    pass over what arrived rather than a second opinion about the table.

    The counts first, and they are this gate's own anti-vacuity assertion rather
    than a restatement of the fixture. Every other gate here goes vacuous if its
    samples vanish; this one goes vacuous if it is handed a *narrowed* series,
    which is not empty and passes. The two keys asserted are the two the clears
    narrow — the cold first frame of each window render, and the whole-window
    span of each refill — so a `published` that had quietly become `gated` again
    is red here rather than green everywhere.

    That the cold first frame is judged under `slider_to_preview` at all is the
    question the finding left open, and it is answered yes: a window render
    follows a parameter edit, so its first frame is the repaint that edit asked
    for and the 100 ms ceiling is exactly the promise being made about it. The
    only render here that no drag caused is the first, and that one is the
    strictest reading of the ceiling rather than an exemption from it.
    """
    published = Counter(sample.key for sample in reading.published)
    assert published["slider_to_preview"] == len(WINDOWS) + len(PLAYHEAD_STOPS) + len(GRAPH_EDITS)
    assert published["full_preview_render"] == len(WINDOWS) + len(GRAPH_EDITS)

    missed = [
        f"{sample.key} took {sample.elapsed_ms:.1f} ms, over by {sample.over_ms:.1f}"
        for sample in reading.misses()
        if sample.key not in IN_DEBT
    ]
    assert missed == []


def test_reuse_on_a_post_edit_render(reading: Reading) -> None:
    """What the store served, per render, and it is not a ceiling.

    The finding's reuse row, produced by the same pass the timings come from
    rather than by a scratch probe a session deletes — which is what lets a
    change to `cache_key.cache_policy` land as a red line here instead of as a
    number nobody re-took.

    Exact counts and not an inequality, because the interesting thing about this
    row is which outputs recompute rather than how many. The cold render has
    nothing to serve. A post-edit render recomputes the edited detector at every
    frame, since an edit gives it a key nothing has ever written, plus
    `block_signal` at the span's first frame, where `decode_start` is clamped and
    the one frame of warmup its key is admitted for has nowhere to come from —
    which is why this is `frame_count + 1` and not `frame_count`, and why a
    window away from the start of the footage would be one lower.
    """
    cold, *post_edit = reading.window_renders
    outputs = SPAN.frame_count * len(cold.plan.dag.order)
    recomputed = SPAN.frame_count + 1

    assert (cold.computed, cold.from_cache) == (outputs, 0)
    assert [(render.computed, render.from_cache) for render in post_edit] == [
        (recomputed, outputs - recomputed)
    ] * (len(WINDOWS) - 1)


def test_the_stack_share_of_a_refill(reading: Reading) -> None:
    """How much of a refill is the assembly rather than the render inside it.

    A reading and not a gate: `slider_to_graph` is the ceiling and it is judged
    above, while the split between the render and the stack has no ceiling anyone
    has argued for. What it decides is where a longer working window would first
    cost — the render or the assembly — and it needs no clock of its own, because
    a refill's own window render publishes inside the refill's span.

    Positive per refill is the whole assertion: the render is nested, so a
    non-positive share is a subtraction over two spans that were not the same
    gesture. `stack_shares` pairs strictly, so a stage that stopped publishing
    one of the two is red here rather than silently paired off by one.
    """
    assert len(reading.refill_renders) == len(GRAPH_EDITS)
    assert [share for share in reading.stack_shares if share <= 0.0] == []


def test_the_measurement_imports_no_qt(reading: Reading) -> None:
    """The claim the phase is named for, restated as a claim about *this* code.

    It used to read `sys.modules` at assertion time, which was the whole of the
    claim while nothing in the tree imported Qt. 07.11 measures these same
    ceilings *through* the GUI, in a session where a `QApplication` exists by
    construction, so the old form goes red for a reason that says nothing about
    what was measured here — pytest imports every test module during collection,
    and one Qt import anywhere in the suite made the assertion a statement about
    file ordering rather than about this pass.

    What the headless numbers actually need is that they were taken by code with
    no Qt in it, which is a claim about one measurement's import closure and not
    about the suite's process. So it is asked in a fresh interpreter that imports
    exactly what this file's pass runs on, and nothing else. Stronger than the
    original in the way that matters — a Qt import reaching any of these four
    modules is red here whatever else the suite happens to have loaded — and it
    survives every later phase, which the `sys.modules` form could not.

    The `headless` contract in `.importlinter` forbids the same edge statically,
    and this is not a duplicate of it: a contract holds `PySide6` out of the
    packages it names, while this holds it out of whatever the measurement
    imports, including the third-party path that would arrive under a
    dependency's name rather than under `sieve`'s.
    """
    del reading
    imports = "; ".join(f"import {name}" for name in MEASURED_MODULES)
    probe_source = (
        f"{imports}; import sys; "
        f"print([n for n in sys.modules if n.split('.')[0] in {list(QT_MODULES)!r}])"
    )
    probe = subprocess.run(
        [sys.executable, "-c", probe_source],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert probe.stdout.strip() == "[]", probe.stdout
