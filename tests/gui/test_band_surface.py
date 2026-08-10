"""The declared display surface, from the render that fills it to the handles on it.

Four claims in one file because they are one path, and a break anywhere in it
shows up as a band with no handles: `execute` fills a surface only when asked,
`SurfaceCollector` stacks the columns into a picture, `SurfacePanel` draws it and
says what its axis means, and `BandEditor` reads a cut off that axis into one
`SetParam`.

**The refusal is a case here rather than an omission.** Where a band's handles
read is declared and resolved against what feeds the node, so a band over an
input nothing can describe gets no editor — and a file that only asserted the
ones that resolve would read as though that had been forgotten
(`gui/surface_panel.py`).

The synthetic tool below is `test_kind_editors.py`'s move and for its reason: a
spec no registry has heard of is what asks "per kind, never per tool" of the
editor rather than of `detect`. The end-to-end case uses the real chain, because
which panels exist and what fed them is a claim about the window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sieve.core.pipeline_model import Node, Pipeline, Project, SourceRef, SourceSpan
from sieve.core.tool_base import (
    ArraySpec,
    AxisRelation,
    DisplaySurface,
    ElementRelation,
    Emission,
    FrameSpan,
    ParamAxis,
    ParamsBase,
    ParamStereotype,
    RowAxis,
    ToolSpec,
    ValueAxis,
)
from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.series_collector import CollectedSeries
from sieve.session.session import Session
from tests.gui import driving

_NODE = "n0"

#: The panel's size in the cases below. Tall enough that one axis unit is
#: several pixels, so a press within the grab radius of one handle is nowhere
#: near the other.
PANEL_SIZE = (300, 200)

#: The band the document starts on, as a fraction — `count_frac`'s shape, which
#: is the one surface whose axis is fixed and therefore the one a case can name
#: a pixel for without first knowing the data.
COUNT_BAND = (0.25, 0.75)

#: A count surface's columns: one value per frame, twenty frames from frame 5.
COUNT_COLUMNS = np.linspace(0.1, 0.9, 20, dtype=np.float32).reshape(-1, 1, 1)
COUNT_START = 5

#: The synthetic tool's own bank, four rows and log-spaced like a real one — so
#: a panel that had mapped y linearly in the coordinate rather than in the row
#: would place a handle somewhere a case can tell apart.
SYNTHETIC_BANK = (1.0, 2.0, 4.0, 8.0)

#: The three axes `_spec()` declares, resolved against an input whose elements
#: have a meaning. One of each form the declaration admits.
_AXES: dict[DisplaySurface, ParamAxis] = {
    DisplaySurface.SCALOGRAM: RowAxis(SYNTHETIC_BANK),
    DisplaySurface.TRACE: ValueAxis(),
    DisplaySurface.COUNT: ValueAxis((0.0, 1.0)),
}


class BandParams(ParamsBase):
    """One band per surface kind, and one of each form an axis is declared in."""

    freqs: tuple[float, float] = (2.0, 8.0)
    values: tuple[float, float] = (0.0, 1.0)
    fraction: tuple[float, float] = COUNT_BAND


def _display(params: BandParams, window: FrameSpan, /) -> dict[DisplaySurface, Frame]:
    """Three columns of the shapes the panels expect, and nothing derived."""
    del params
    index = window[window.target_row].index
    return {
        DisplaySurface.SCALOGRAM: Frame(
            data=np.arange(4, dtype=np.float32).reshape(-1, 1),
            index=index,
            channels=ChannelSpec.GRAY,
        ),
        DisplaySurface.TRACE: Frame(
            data=np.arange(3, dtype=np.float32).reshape(-1, 1),
            index=index,
            channels=ChannelSpec.GRAY,
        ),
        DisplaySurface.COUNT: Frame(
            data=np.array([[0.5]], np.float32), index=index, channels=ChannelSpec.GRAY
        ),
    }


def _spec() -> ToolSpec:
    return ToolSpec(
        tool_id="banded",
        version="1.0.0",
        summary="A tool that exists to declare a band on each surface.",
        params_model=BandParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
        param_stereotypes={
            "freqs": ParamStereotype.BAND,
            "values": ParamStereotype.BAND,
            "fraction": ParamStereotype.BAND,
        },
        param_surfaces={
            "freqs": DisplaySurface.SCALOGRAM,
            "values": DisplaySurface.TRACE,
            "fraction": DisplaySurface.COUNT,
        },
        param_axes={
            "freqs": RowAxis(SYNTHETIC_BANK),
            "values": AxisRelation.INPUT_VALUES,
            "fraction": ValueAxis((0.0, 1.0)),
        },
        display=_display,
    )


@pytest.fixture
def session(tmp_path: Path) -> Session:
    """One node of the tool above, with every band placed."""
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_NODE,
                    tool_id="banded",
                    version="1.0.0",
                    params={"fraction": list(COUNT_BAND)},
                ),
            )
        ),
    )
    return Session(tmp_path / "clip.sieve.yaml", project)


@pytest.fixture
def canvas(qapp) -> Any:
    """A viewport, required by `bind_editors` and never reached by a band.

    Built bare rather than fed a frame: the tool above declares no region, so
    what this asserts by being unused is that a band's editor asks the canvas for
    nothing.
    """
    del qapp
    from sieve.gui.canvas import VideoCanvas

    return VideoCanvas()


@pytest.fixture
def band(qapp) -> Any:
    """A scrubber strip, required by `bind_editors` and never reached either."""
    del qapp
    from sieve.gui.timeline.bar import TimelineStrip

    return TimelineStrip()


def _panel(kind: DisplaySurface, columns: np.ndarray, start: int) -> Any:
    from sieve.gui.surface_panel import SurfacePanel

    panel = SurfacePanel(kind, _AXES[kind])
    panel.resize(*PANEL_SIZE)
    panel.set_picture(CollectedSeries(start_index=start, data=columns))
    return panel


# ---- the channel, assembled ------------------------------------------------


def test_a_band_surface_is_only_assembled_for_a_node_the_render_was_asked_to_show(
    qapp, stirred_clip: Path
) -> None:
    """The two halves of the request path, against the same render twice.

    The collector cannot tell a node it was not asked about from one whose tool
    draws nothing, and it does not have to: the empty picture is what a render
    with no `show=` honestly produced. What the pair asserts is that the fill is
    the *request's* consequence and not a default — a channel filled anyway would
    make `show=` decoration and charge every headless run for it.
    """
    del qapp
    from sieve.bench.metrics import MetricBus
    from sieve.decode.prefetch import PrefetchFrameSource
    from sieve.pipeline.cache import MemoryFrameStore
    from sieve.pipeline.cache_key import source_identity
    from sieve.pipeline.dag import graph_needs_chroma
    from sieve.pipeline.preview import PreviewSession
    from sieve.pipeline.series_collector import SurfaceCollector
    from sieve.tools import discover
    from tests.integration.test_v2_oracle import DETECTOR, SPAN, graph

    discover()
    pipeline = graph()
    window = SourceSpan(start=SPAN.start, end=SPAN.end)
    pictures: dict[bool, CollectedSeries | None] = {}
    with PrefetchFrameSource(stirred_clip, luma=not graph_needs_chroma(pipeline)) as reader:
        preview = PreviewSession(
            source=source_identity(stirred_clip),
            reader=reader,
            window=window,
            measure=MetricBus().measure,
            store=MemoryFrameStore(),
        )
        for asked in (False, True):
            collector = SurfaceCollector(
                DETECTOR, DisplaySurface.TRACE, measure=MetricBus().measure
            )
            with collector.refill() as consume:
                preview.render_window(pipeline, on_frame=consume, show=(DETECTOR,) if asked else ())
            pictures[asked] = collector.picture

    assert pictures[False] is None
    filled = pictures[True]
    assert filled is not None
    # The span's own frames, one column each, and the block grid's rows in every
    # column — the shape `graph_panel` refuses and this panel exists for.
    assert filled.start_index == SPAN.start
    assert filled.data.shape[0] == window.frame_count
    assert filled.data.shape[1] > 1


def test_a_band_surface_refill_publishes_the_ceiling_a_drag_is_judged_against(qapp) -> None:
    """`band_drag_repaint`, and under that key rather than the trace's.

    The two collectors publish different keys because the gestures they answer
    for have different ceilings — 50 ms against 200 ms — and a surface refill
    published as `slider_to_graph` would be judged against the looser of the two
    while reading as measured.
    """
    del qapp
    from sieve.bench.budgets import BUDGETS, WITHOUT_PRODUCER
    from sieve.pipeline.series_collector import SURFACE_BUDGET, SurfaceCollector

    assert SURFACE_BUDGET in BUDGETS
    assert SURFACE_BUDGET not in WITHOUT_PRODUCER

    keys: list[str] = []

    class _Bus:
        def measure(self, key: str) -> Any:
            from contextlib import nullcontext

            keys.append(key)
            return nullcontext()

    collector = SurfaceCollector(_NODE, DisplaySurface.COUNT, measure=_Bus().measure)
    with collector.refill():
        pass

    assert keys == [SURFACE_BUDGET]


# ---- the picture, drawn ----------------------------------------------------


def test_a_band_surface_panel_places_a_value_on_the_axis_it_was_declared(qapp) -> None:
    """Three declarations, three axes, and the round trip a handle is read through.

    The count's is *fixed*: a fraction is a fraction of a whole whatever the data
    did, so the top of the plot is one even for columns that never reach it. The
    scalogram's ends are the bank's ends and not the picture's — six rows of
    columns against a four-row declaration, so a panel still reading its own
    shape would answer six. The trace's is the one the data decides, which is the
    only honest answer where the unit is the upstream node's.
    """
    del qapp

    count = _panel(DisplaySurface.COUNT, COUNT_COLUMNS, COUNT_START)
    assert count.value_range() == (0.0, 1.0)
    assert count.value_at(count.y_of(0.25)) == pytest.approx(0.25)
    # The picture's own frames, not the asset's: column zero is frame 5.
    assert count.x_of(COUNT_START) < count.x_of(COUNT_START + 19)
    assert count.x_of(COUNT_START) == pytest.approx(PANEL_SIZE[0] * 0.5 / 20)

    scalogram = _panel(DisplaySurface.SCALOGRAM, np.zeros((4, 6, 1), np.float32), 0)
    assert scalogram.value_range() == (SYNTHETIC_BANK[0], SYNTHETIC_BANK[-1])
    assert scalogram.value_at(scalogram.y_of(2.0)) == pytest.approx(2.0)

    trace = _panel(DisplaySurface.TRACE, np.array([[[2.0], [4.0]]], np.float32), 0)
    low, top = trace.value_range()
    assert low == pytest.approx(2.0)
    assert top > 4.0


def test_a_band_surface_says_it_is_stale_rather_than_blanking(qapp) -> None:
    """The graph's rule on the picture beside it, and for the graph's reason."""
    del qapp

    panel = _panel(DisplaySurface.COUNT, COUNT_COLUMNS, COUNT_START)
    assert panel.status_text() == ""
    panel.mark_stale()
    assert panel.is_stale
    assert panel.picture is not None
    assert panel.status_text() != ""


# ---- the handles -----------------------------------------------------------


def test_a_dragged_band_surface_handle_enters_as_a_set_param(qapp, session: Session) -> None:
    """The whole of the gesture's output: one parameter, at one address.

    The low handle is dragged to three quarters of the way up a fixed 0..1 axis,
    so the value it commits is knowable without reading the picture — which is
    what makes the count surface the one this case is written on. The high edge
    is untouched, because a drag that moved both would be a band replaced rather
    than an edge dragged.
    """
    del qapp
    from sieve.gui.kind_editors import BandEditor

    panel = _panel(DisplaySurface.COUNT, COUNT_COLUMNS, COUNT_START)
    editor = BandEditor(panel, session, _NODE, "fraction", COUNT_BAND)
    editor.resize(*PANEL_SIZE)

    height = PANEL_SIZE[1]
    driving.drag(editor, (10.0, height * 0.75), (10.0, height * 0.25))

    assert session.project.params_for(_NODE)["fraction"] == [
        pytest.approx(0.75),
        pytest.approx(0.75),
    ]


def test_a_band_surface_handle_stops_at_the_other_rather_than_crossing_it(
    qapp, session: Session
) -> None:
    """An ordered pair stays ordered, and the drag says so rather than the model.

    Dragging the low edge past the high one would produce a pair the document
    refuses — reported to the user as a validation error for a gesture they made
    in one direction. It stops instead, which is the strip's rule for the same
    shape one axis over.
    """
    del qapp
    from sieve.gui.kind_editors import BandEditor

    panel = _panel(DisplaySurface.COUNT, COUNT_COLUMNS, COUNT_START)
    editor = BandEditor(panel, session, _NODE, "fraction", COUNT_BAND)
    editor.resize(*PANEL_SIZE)

    driving.drag(editor, (10.0, PANEL_SIZE[1] * 0.75), (10.0, -50.0))
    low, high = session.project.params_for(_NODE)["fraction"]

    assert low == pytest.approx(high)
    assert high == pytest.approx(COUNT_BAND[1])


def test_a_band_whose_axis_did_not_resolve_takes_no_handles(
    qapp, session: Session, canvas: Any, band: Any
) -> None:
    """`RegionEditor`'s refusal, one kind over — and now a state of a graph.

    `values` is declared `INPUT_VALUES`, so a node whose input has no element
    meaning has no axis for it either and the panel is drawn with none. The
    scalogram beside it is the case that says the refusal is no longer the
    *kind*: its axis is declared outright, so it keeps its handles in the same
    call that takes the trace's away.
    """
    del qapp
    from sieve.gui.kind_editors import BandEditor, bind_editors
    from sieve.gui.surface_panel import SurfacePanel

    panels = {kind: SurfacePanel(kind, _AXES[kind]) for kind in DisplaySurface}
    panels[DisplaySurface.TRACE] = SurfacePanel(DisplaySurface.TRACE, None)
    assert panels[DisplaySurface.SCALOGRAM].takes_handles
    assert not panels[DisplaySurface.TRACE].takes_handles

    editors = bind_editors(
        session,
        _NODE,
        _spec(),
        session.project.params_for(_NODE),
        canvas=canvas,
        timeline=band,
        region_extent=None,
        bands=panels,
    )

    assert set(editors) == {"freqs", "fraction"}
    assert all(isinstance(editor, BandEditor) for editor in editors.values())


def test_a_scalogram_handle_reads_the_declared_axis(
    qapp, tmp_path: Path, canvas: Any, band: Any
) -> None:
    """The bank is a declaration, so a cut on the picture is a number in Hz.

    On `detect`'s own spec rather than the synthetic one above, because what is
    being asserted is that the tool that forced the question answers it: the
    coordinates come from `default_freqs(params.fps)`, which no channel and no
    panel could have derived. The round trip is taken at a row in the middle of a
    log-spaced bank, where an axis that had stayed linear in the value would give
    a different answer from one that is linear in the row.
    """
    del qapp
    from sieve.core.tool_base import ElementKind, RowAxis, node_param_axis
    from sieve.core.tool_registry import REGISTRY
    from sieve.gui.kind_editors import BandEditor, bind_editors
    from sieve.gui.surface_panel import SurfacePanel
    from sieve.tools import discover
    from sieve.tools.detect import default_freqs

    discover()
    spec = REGISTRY.get("detect", "1.0.0")
    params = spec.params_model()
    axes = {
        spec.param_surfaces[name]: node_param_axis(declaration, params, ElementKind.BLOCK)
        for name, declaration in spec.param_axes.items()
    }
    bank = tuple(float(hz) for hz in default_freqs(params.fps))
    assert axes[DisplaySurface.SCALOGRAM] == RowAxis(bank)

    panel = SurfacePanel(DisplaySurface.SCALOGRAM, axes[DisplaySurface.SCALOGRAM])
    panel.resize(*PANEL_SIZE)
    panel.set_picture(CollectedSeries(start_index=0, data=np.zeros((8, len(bank), 1), np.float32)))
    assert panel.takes_handles
    assert panel.value_at(panel.y_of(bank[7])) == pytest.approx(bank[7])

    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_NODE,
                    tool_id="detect",
                    version="1.0.0",
                    params={"freq_band": [bank[4], bank[18]]},
                ),
            )
        ),
    )
    session = Session(tmp_path / "clip.sieve.yaml", project)
    editors = bind_editors(
        session,
        _NODE,
        spec,
        session.project.params_for(_NODE),
        canvas=canvas,
        timeline=band,
        region_extent=None,
        bands={DisplaySurface.SCALOGRAM: panel},
    )
    editor = editors["freq_band"]
    assert isinstance(editor, BandEditor)
    editor.resize(*PANEL_SIZE)

    driving.drag(editor, (10.0, panel.y_of(bank[4])), (10.0, panel.y_of(bank[2])))

    low, high = session.project.params_for(_NODE)["freq_band"]
    assert low == pytest.approx(bank[2], rel=0.02)
    assert high == pytest.approx(bank[18])


def test_a_band_with_no_panel_drawn_for_it_gets_no_editor(
    qapp, session: Session, canvas: Any, band: Any
) -> None:
    """The other refusal, and the one that keeps every other step honest.

    A step whose surfaces the caller did not draw is every step but the one on
    screen, so this is the ordinary case rather than the corner. Asked per
    parameter in a single call rather than by binding twice: with only the count
    surface drawn, the band on it is the only one that gets handles, and a
    version that answered by the *kind* would hand editors to all three.
    """
    del qapp
    from sieve.gui.kind_editors import bind_editors
    from sieve.gui.surface_panel import SurfacePanel

    bound = bind_editors(
        session,
        _NODE,
        _spec(),
        session.project.params_for(_NODE),
        canvas=canvas,
        timeline=band,
        region_extent=None,
        bands={
            DisplaySurface.COUNT: SurfacePanel(DisplaySurface.COUNT, _AXES[DisplaySurface.COUNT])
        },
    )

    assert set(bound) == {"fraction"}

    assert (
        bind_editors(
            session,
            _NODE,
            _spec(),
            session.project.params_for(_NODE),
            canvas=canvas,
            timeline=band,
            region_extent=None,
        )
        == {}
    )


# ---- the window ------------------------------------------------------------


def test_the_window_draws_the_band_surfaces_of_the_step_it_stands_on(
    stirred_clip: Path, tmp_path: Path, qapp
) -> None:
    """The path end to end, on the real chain and through a real walk.

    The step pane is where a surface hangs, because a display surface exists only
    while the step declaring it is being looked at — so the assertion is that
    walking onto the detector produces three panels and that a refill fills all
    three, and that walking off leaves none. That last half is what says the
    channel is not being filled for a node nobody is watching, which is the cost
    the ADR takes deliberately and would be paying on every step otherwise.
    """
    del qapp
    from PySide6.QtWidgets import QApplication

    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in
    from sieve.tools import discover
    from tests.integration.test_v2_oracle import DETECTOR, SPAN, graph

    discover()
    QApplication.instance() or QApplication([])
    video = tmp_path / stirred_clip.name
    video.write_bytes(stirred_clip.read_bytes())
    path = tmp_path / "stirred.sieve.yaml"
    Project.for_video(video, tmp_path).model_copy(update={"pipeline": graph()}).save(path)

    window = MainWindow(projects_in(tmp_path))
    try:
        window.show()
        window.open_project(path)
        driving.wait_until(lambda: window.player.metadata is not None, 60_000)
        window.timeline.set_window(SourceSpan(start=SPAN.start, end=SPAN.end))
        window.go_down()
        window.go_down()
        assert window.current_node is not None
        assert window.current_node.node_id == DETECTOR
        driving.wait_until(
            lambda: not window.graph.is_stale or window.tuning.last_error is not None, 60_000
        )
        assert window.tuning.last_error is None, window.tuning.last_error

        assert set(window.surfaces) == set(DisplaySurface)
        assert window.tuning.showing == DETECTOR
        for surface, panel in window.surfaces.items():
            picture = panel.picture
            assert picture is not None, f"{surface.value} was never filled"
            assert picture.start_index == SPAN.start
            assert picture.data.shape[0] == SPAN.frame_count

        window.go_up()
        assert window.surfaces == {}
        assert window.tuning.showing is None
    finally:
        window.close()
