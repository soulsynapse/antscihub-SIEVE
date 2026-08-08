"""Phase 7's gate, second half: the same ceilings, through the window.

`test_loop_budget.py` measured the loop before a widget existed, and said in its
own docstring why: a number taken through the GUI can no longer tell a slow
pipeline from a slow paint. This file is the other end of that argument. Every
key here has a headless reading beside it in `budgets.py`'s own terms, so a
regression that shows up here and not there is *the window's* — which is the
attribution Phase 6 was run early to buy, and the only reason it is worth paying
for twice.

**The scope is the keys whose producers this cut builds**, and nothing is added
to the table to fill it out. `scrub_to_repaint` comes from `transport/player.py`
and is the pre-pipeline regime; `full_preview_render`, `slider_to_preview` and
`slider_to_graph` come from `pipeline/preview.py` and
`pipeline/series_collector.py` driven by `gui/tuning.py`, and are the in-pipeline
one. `density_rebuild` is the key deliberately outside it: the band-power density
strip drags band-power caching behind it and is a later cut, so it stays declared
in `budgets.WITHOUT_PRODUCER` rather than measured through a surface that does
not exist. A miss inside the scope is a defect or a debt in `budgets.IN_DEBT`
against the item that repays it — never a widened ceiling (VISION's scope note).

**Every gesture is a real one.** The scrubs go through `VideoPlayer.scrub`, which
is what the band emits on a drag, and the parameter moves go through the spin box
`param_form.py` generated — not through `SetParam`, and not through
`PreviewSession` directly. A benchmark that called the layer under the widget
would measure exactly the thing the headless file already measured, and the
difference between the two numbers is the whole subject.

**A gate over an empty series passes and means nothing**, so every key carries a
sample count and every refill carries a row count, for `test_loop_budget.py`'s
two reasons: samples can vanish, and a collector that assembled nothing publishes
the same span shape as one that assembled the window.

**No Qt-residency claim here, and that is the point of the one next door.** This
process has a `QApplication` in it by construction. What the headless numbers
need is that *they* were taken by code with no Qt in it, which
`test_loop_budget.test_the_measurement_imports_no_qt` asks in a fresh
interpreter — a claim about one measurement's import closure rather than about
whichever test module pytest imported first.

The numbers do not live here. The finding is
`docs/findings/2026.08.08-the-loop-budget-is-met-through-the-gui.md`, with the
margin between these readings and the headless ones, which is what says how much
room the window has left to spend.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import pytest

from sieve.bench.budgets import IN_DEBT
from sieve.bench.metrics import METRICS, Recorder, Sample
from sieve.core.pipeline_model import Project, SourceSpan
from sieve.tools import discover
from tests.bench.test_loop_budget import GRAPH_EDITS, SCRUB_STOPS, within_budget
from tests.gui import driving
from tests.integration.test_v2_oracle import DETECTOR, SPAN, graph

# Set before the first `QGuiApplication` is constructed, for the reason
# `tests/gui/conftest.py` gives: a laptop with a display would otherwise open a
# real window for a benchmark nobody asked to watch. This directory has no
# conftest of its own, and borrowing one from `tests/gui/` would make a bench
# module's platform depend on a fixture directory it does not sit in.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: How long a gesture is given to complete. Generous for `test_save_and_run.py`'s
#: reason: what a slow machine costs here is a flake, and the wait ends when the
#: thing it waits on does. It is not a budget — the budgets are below.
_TIMEOUT_MS = 60_000

#: The parameter the drag moves, and the node it is on. The detector because it
#: is the graph's last node: an edit there must leave the two above it keyed
#: exactly as they were, so a window that re-ran the whole graph shows up here as
#: a `full_preview_render` that never gets cheaper.
_PARAM = "window_frames"

#: Where the drag stops, as source indices in the order they are visited. The
#: headless pass's own stops, minus the ones outside the working window: the
#: transport is confined to the window by construction (`transport/player.py`),
#: so a stop past its end is a request that lands on the last frame instead and
#: a wait for it never ends. The order is preserved, so the median is still over
#: both of the reader's strategies rather than over a monotone sweep.
SCRUBS = tuple(index for index in SCRUB_STOPS if SPAN.start <= index < SPAN.end)


@dataclass(frozen=True, slots=True)
class Reading:
    """One pass over the reference workload through the window, as it published."""

    #: What each median gate reads, narrowed by the clears between the stages —
    #: `test_loop_budget.Reading` says why a clear is not tidiness.
    gated: Mapping[str, tuple[Sample, ...]]
    #: Every sample the pass published, in arrival order across all keys.
    published: tuple[Sample, ...]
    #: Rows the panel held after each edit, in order. `slider_to_graph` is the
    #: one gate whose subject can be fast by being empty.
    rows_per_edit: tuple[int, ...]

    def median_ms(self, key: str) -> float:
        return median(sample.elapsed_ms for sample in self[key])

    def misses(self) -> tuple[Sample, ...]:
        return tuple(sample for sample in self.published if not sample.within_budget)

    def __getitem__(self, key: str) -> tuple[Sample, ...]:
        samples = self.gated.get(key)
        if not samples:
            raise KeyError(f"nothing was measured under {key!r} through the GUI")
        return samples


def _window(stirred_clip: Path, directory: Path) -> Any:
    """A window with the oracle's chain open over the clip, tuned to the span.

    The graph is `test_v2_oracle.graph()` and the span is its `SPAN`, imported
    rather than respelt for that module's reason and for `test_loop_budget.py`'s:
    one reference workload, or the ceilings hold against a chain nothing runs.
    """
    from PySide6.QtWidgets import QApplication

    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    QApplication.instance() or QApplication([])

    video = directory / stirred_clip.name
    video.write_bytes(stirred_clip.read_bytes())
    path = directory / "stirred.sieve.yaml"
    Project.for_video(video, directory).model_copy(update={"pipeline": graph()}).save(path)

    window = MainWindow(projects_in(directory))
    window.show()
    window.open_project(path)
    driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
    window.timeline.set_window(SourceSpan(start=SPAN.start, end=SPAN.end))
    return window


def _settle_graph(window: Any) -> None:
    driving.wait_until(
        lambda: not window.graph.is_stale or window.tuning.last_error is not None, _TIMEOUT_MS
    )
    assert window.tuning.last_error is None, window.tuning.last_error


@pytest.fixture(scope="module")
def reading(stirred_clip: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Reading]:
    """Open, scrub, and drag a parameter — one pass, asked several questions.

    Module-scoped and run once, for `test_loop_budget.py`'s reason: the file
    measures the loop a single time so the gates cannot disagree about which
    session they are judging.

    The clears between the stages are that file's too. The scrubs must not be
    pooled with anything, and the *first* refill of the session is the cold one —
    it decodes the window and runs three tools over it with nothing in the store,
    which is not a drag and is answered for by the 3 s ceiling rather than by the
    per-gesture ones. What each clear drops still reaches `published`, so the
    per-sample gate below judges it.
    """
    discover()
    directory = tmp_path_factory.mktemp("gui_budget")
    recorder = Recorder()
    run: list[Sample] = []
    stop_recording = METRICS.subscribe(recorder.record)
    stop_run = METRICS.subscribe(run.append)

    window = _window(stirred_clip, directory)
    try:
        # The cold render the walk to the detector sets off, before any clock
        # below is read: it is the session's first and no gesture caused it.
        window.go_down()
        window.go_down()
        assert window.current_node is not None and window.current_node.node_id == DETECTOR
        _settle_graph(window)

        recorder.clear()
        for index in SCRUBS:
            window.player.scrub(index)
            driving.wait_until(lambda i=index: window.player.current_index == i, _TIMEOUT_MS)
        collected = {"scrub_to_repaint": recorder.samples("scrub_to_repaint")}

        recorder.clear()
        rows: list[int] = []
        spin = window.control.step_pane.form.widget(_PARAM)
        for window_frames in GRAPH_EDITS:
            spin.setValue(window_frames)
            _settle_graph(window)
            series = window.graph.series
            rows.append(0 if series is None else int(series.data.shape[0]))
        for key in ("slider_to_graph", "full_preview_render", "slider_to_preview"):
            collected[key] = recorder.samples(key)
    finally:
        window.close()
        stop_recording()
        stop_run()

    yield Reading(gated=collected, published=tuple(run), rows_per_edit=tuple(rows))


# ---- pre-pipeline: the video-editor regime -------------------------------


def test_a_scrub_through_the_window_repaints_inside_the_perceptual_threshold(
    reading: Reading,
) -> None:
    """100 ms, over the same twelve stops the headless pass took.

    Headless the number was the reader's; here it is the round trip the player
    measures — a queued request onto the decode thread, a decode, a proxy
    resample, a queued signal back, and the canvas' synchronous update. That
    difference *is* the window's contribution, and it is why the same key is
    gated twice.

    Fewer samples than stops is not a failure of the gesture: a stop the proxy
    cache already holds is served without a decode and publishes nothing, which
    is exactly the mechanism the budget is met by. What the count refuses is a
    series with nothing in it.
    """
    assert 0 < len(reading["scrub_to_repaint"]) <= len(SCRUBS)
    within_budget("scrub_to_repaint", reading.median_ms("scrub_to_repaint"))


# ---- in-pipeline: the direct-manipulation regime -------------------------


def test_the_window_renders_inside_the_attention_band(reading: Reading) -> None:
    """3 s per post-edit window render, driven by the generated spin box.

    The cold render is not in this series and is in the headless one, and the
    difference is deliberate: there the cold sample is the first thing a user
    meets, while here the session has already rendered before the first gesture —
    the walk onto a node fills its graph. What is judged is therefore five real
    post-edit renders, which is the stricter reading.
    """
    assert len(reading["full_preview_render"]) == len(GRAPH_EDITS)
    within_budget("full_preview_render", reading.median_ms("full_preview_render"))


def test_the_first_frame_of_an_edited_window_lands_inside_one_perceived_beat(
    reading: Reading,
) -> None:
    """100 ms, and the ceiling VISION's whole argument rests on.

    Published around the first frame of each window render —
    `test_loop_budget.py` answers there why a window render's first frame is
    judged under the drag ceiling rather than exempted from it.

    **What this is not, in this cut: a repaint.** The canvas is fed decoded
    source frames by the transport and nothing paints a rendered one, so the key
    is measured on the render that would feed a repaint and not on the repaint
    itself — which is why it reads *lower* here than headless rather than higher,
    the first frame of a window on a warm store being nearly free where
    `render_frame`'s was not. In scope because its producer is one this cut
    drives, and the gap is written down rather than left to be inferred from a
    green line: `todo/the-viewport-shows-the-source-and-not-the-render.md`.
    """
    assert len(reading["slider_to_preview"]) == len(GRAPH_EDITS)
    within_budget("slider_to_preview", reading.median_ms("slider_to_preview"))


def test_the_graph_refills_within_two_perceived_beats(reading: Reading) -> None:
    """200 ms, and the number the product is: drag a slider, the graphs refill.

    The span runs from the deferred render to the array existing, and the panel
    is handed it immediately after — so what is measured is everything between
    the user's gesture and the trace, minus the paint Qt does on its own turn.

    The row count is this gate's anti-vacuity assertion, one layer under the
    sample count: every other gate here goes vacuous only if the samples vanish,
    while this one also goes vacuous if the samples arrive around a collector
    that assembled nothing.
    """
    assert len(reading["slider_to_graph"]) == len(GRAPH_EDITS)
    assert reading.rows_per_edit == (SPAN.frame_count,) * len(GRAPH_EDITS)
    within_budget("slider_to_graph", reading.median_ms("slider_to_graph"))


# ---- what the medians above cannot say -----------------------------------


def test_every_sample_the_session_published_is_gated(reading: Reading) -> None:
    """A median that passes over a sample that missed is a janky window.

    Over `published`, which the clears never touched: the cold render's own
    samples are in here and are judged, so the one render the medians above
    exclude is not thereby excused. The bus judged each sample against `BUDGETS`
    on the way past, so this is one pass over what arrived.

    The count assertion is this gate's own, and it is the one that fails if
    `published` had quietly become `gated` — the cold render publishes a
    `full_preview_render` and a `slider_to_preview` that no median above sees, so
    the run has strictly more of both than the five edits produced.
    """
    published = _counted(reading.published)
    assert published["full_preview_render"] > len(GRAPH_EDITS)
    assert published["slider_to_preview"] > len(GRAPH_EDITS)

    missed = [
        f"{sample.key} took {sample.elapsed_ms:.1f} ms, over by {sample.over_ms:.1f}"
        for sample in reading.misses()
        if sample.key not in IN_DEBT
    ]
    assert missed == []


def _counted(samples: Sequence[Sample]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sample in samples:
        counts[sample.key] = counts.get(sample.key, 0) + 1
    return counts
