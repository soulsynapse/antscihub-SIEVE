"""`band_drag_repaint` through the window, because there is nowhere else.

Every other in-pipeline ceiling is timed twice — once headless in
`test_loop_budget.py` and once through the window in `test_gui_loop_budget.py` —
and the difference between the two readings is the window's contribution. This
key has no headless reading and cannot have one: the gesture is a drag on a pair
of handles painted on a display surface, so the surface is a widget and the
gesture is a mouse. What the file next door attributes by subtraction, this one
cannot; what it can do is measure the real thing rather than a stand-in for it.

**The gesture is a drag on the handles**, through `BandEditor` on the count
surface the window built for the detector — not a `SetParam`, and not a call into
`TuningLoop`. The count surface is the one whose axis is fixed at zero to one, so
a drag to a given fraction of the panel commits a known value and every drag in
the series is a different one; a series that re-committed the same band would be
timing a document write that changed no key and a render served whole from the
store.

**50 ms is the tightest ceiling in the table**, and it is deliberately tighter
than `slider_to_graph` because a drag emits continuously: two consecutive ticks
must land inside one perceived beat. What that ceiling is on, in this tree, is a
whole window render with the display channel filled — v3 has no cheap tier, and
`gui/tuning.py` says why publishing every surface refill under this key is
therefore honest rather than generous.

The numbers do not live here; the finding is
`docs/findings/2026.08.10-the-display-channel-costs-a-watched-nodes-re-use-and-the-band-budget-holds.md`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import pytest

from sieve.bench.metrics import METRICS, Recorder, Sample
from sieve.core.pipeline_model import Project, SourceSpan
from sieve.core.tool_base import DisplaySurface
from sieve.tools import discover
from tests.bench.test_loop_budget import within_budget
from tests.gui import driving
from tests.integration.test_v2_oracle import DETECTOR, SPAN, graph

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: `test_gui_loop_budget.py`'s wait, and not a budget — see its constant.
_TIMEOUT_MS = 60_000

#: The band the drag moves, and the surface it is dragged on. Its low edge is
#: the oracle's `COUNT_FRAC` and its high edge is infinity, which paints at the
#: top of the axis — so the low handle is the one with a neighbour to stop
#: against and the one every drag below takes hold of.
_PARAM = "count_frac"
_SURFACE = DisplaySurface.COUNT

#: Where the low handle is dragged to, as fractions of the axis, in the order
#: they are visited. Five, matching `GRAPH_EDITS`, and every one a value none of
#: the others took: a repeated value writes no edit, the document drops it, and
#: the refill that never happened would leave a gap in the series rather than a
#: miss in it. All below the high edge, so none of them is the stop-at-the-other
#: case — that is a correctness claim and lives in `tests/gui/test_band_surface.py`.
_DRAGS = (0.30, 0.45, 0.20, 0.55, 0.35)

#: How far along the panel the drag happens. Anywhere: a band's handles run the
#: full width, so which column the cursor is over decides nothing.
_DRAG_X = 10.0


def _window(stirred_clip: Path, directory: Path) -> Any:
    """The oracle's chain open over the clip, walked onto the detector.

    `test_gui_loop_budget._window` with the walk folded in, because this file's
    gesture is only available *at* the detector: the surfaces are the step pane's
    and the step pane is the node the walk is on.
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
    window.go_down()
    window.go_down()
    assert window.current_node is not None and window.current_node.node_id == DETECTOR
    return window


def _settle(window: Any) -> None:
    driving.wait_until(
        lambda: not window.graph.is_stale or window.tuning.last_error is not None, _TIMEOUT_MS
    )
    assert window.tuning.last_error is None, window.tuning.last_error


@dataclass(frozen=True, slots=True)
class Reading:
    """One pass of drags, as what it published and what each drag left behind."""

    samples: tuple[Sample, ...]
    #: The band on screen after each drag, in order. This gate's anti-vacuity
    #: assertion one layer under the sample count — see the case that reads it.
    bands: tuple[tuple[float, float], ...]
    #: How many surfaces the step declared, and therefore how many spans one
    #: drag publishes: the detector declares three and each has a collector of
    #: its own, because a span covering all three would report the slowest as
    #: each. They nest around one render and so read alike, which is right — a
    #: surface's picture is complete only when the render that filled every
    #: column of it is.
    surfaces: int

    def median_ms(self) -> float:
        return median(sample.elapsed_ms for sample in self.samples)


@pytest.fixture(scope="module")
def reading(stirred_clip: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Reading]:
    """Open, walk to the detector, and drag the count band's low handle five times.

    Module-scoped and run once, for `test_loop_budget.py`'s reason. The recorder
    is cleared after the walk's own cold render, which decodes the window and
    runs three tools over it with nothing in the store: that is not a drag, and
    it is answered for by the 3 s ceiling rather than by this one.
    """
    discover()
    directory = tmp_path_factory.mktemp("band_budget")
    recorder = Recorder()
    stop = METRICS.subscribe(recorder.record)

    window = _window(stirred_clip, directory)
    bands: list[tuple[float, float]] = []
    try:
        _settle(window)
        editor = window.overlays[_PARAM]
        panel = window.surfaces[_SURFACE]
        assert panel.picture is not None, "the count surface was never filled"

        recorder.clear()
        for fraction in _DRAGS:
            cuts = editor.cut_positions()
            assert cuts is not None, "the band is unplaced and has no handle to take hold of"
            driving.drag(editor, (_DRAG_X, cuts[0]), (_DRAG_X, panel.height() * (1.0 - fraction)))
            _settle(window)
            shown = editor.shown_band
            assert shown is not None
            bands.append(shown)
        samples = recorder.samples("band_drag_repaint")
        surfaces = len(window.surfaces)
    finally:
        window.close()
        stop()

    yield Reading(samples=samples, bands=tuple(bands), surfaces=surfaces)


def test_a_band_drag_repaints_the_surface_inside_half_a_perceived_beat(
    reading: Reading,
) -> None:
    """50 ms, and the row VISION's tuning centerpiece is measured on.

    The anti-vacuity assertions are two, for `test_gui_loop_budget.py`'s reasons
    one level apart: a sample per drag, so a gate cannot pass because the
    gesture published nothing, and a distinct band per drag, so it cannot pass
    because every drag after the first wrote the value already there and was
    dropped by the document before any render happened.
    """
    assert len(reading.samples) == len(_DRAGS) * reading.surfaces
    assert len({band[0] for band in reading.bands}) == len(_DRAGS)
    within_budget("band_drag_repaint", reading.median_ms())


def test_every_band_drag_the_session_published_is_gated(reading: Reading) -> None:
    """A median that passes over a sample that missed is a janky drag.

    The median is what the ceiling is judged on, because one slow tick inside a
    continuous gesture is a stutter and a run of them is the loop not working.
    Judged per sample as well, on the bus' own verdict, so the distinction stays
    a deliberate one rather than a consequence of only ever looking at medians.
    """
    from sieve.bench.budgets import IN_DEBT

    missed = [
        f"band_drag_repaint took {sample.elapsed_ms:.1f} ms, over by {sample.over_ms:.1f}"
        for sample in reading.samples
        if not sample.within_budget and sample.key not in IN_DEBT
    ]
    assert missed == []
