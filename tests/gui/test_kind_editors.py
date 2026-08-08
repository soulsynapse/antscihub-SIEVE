"""The composite-kind editors: a rectangle on the viewport, a span on the band.

Both surfaces are built bare here rather than reached through `MainWindow`.
Nothing in the tree places an editor yet — where the surfaces are wired to a
node is `todo/the-first-cut-meets-its-gate.md` — and the claim is about the
editor rather than about where it hangs: a value read back through a window
would leave open whether the gesture produced it or the wiring did.

The tool below does not exist and is never registered, for
`test_param_generator.py`'s reason. It declares a composite kind on each of the
two surfaces and a scalar besides, so "an editor per kind, never per tool" is
asked of a spec no registry has heard of and of a parameter that must get none.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives; `driving.py` stands in for `qtbot` and says why there is
none.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Node, Pipeline, Project, SourceRef
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
)
from sieve.core.types import ROI
from sieve.session.session import Session
from tests.gui import driving

_NODE = "n0"

#: The band is as wide as the source is long, so one frame owns one column and
#: an x in a case below reads as the frame it names. `test_timeline.py` sizes
#: its strip the same way and for the same reason.
STRIP_WIDTH = 1000
SOURCE_FRAMES = 1000
SOURCE_FPS = 30.0

#: A y inside the band. Which row a press lands on decides nothing here — the
#: editor's handles are vertical — but a gesture has to happen somewhere.
BAND_Y = 30.0

#: The span the document starts on, and the frames its two handles are at.
SPAN = (100, 300)

CANVAS_SIZE = (200, 100)

#: `(image size, where the canvas paints it, how much it shrinks it)` — the two
#: shapes a frame can meet this viewport in. A frame is inset on exactly one
#: axis: whichever axis the scale is decided by fills the widget, so the offset
#: a landscape frame leaves at zero is the one a portrait frame is inset on. A
#: single shape would leave half of the mapping asserted by nothing, in the
#: direction that reads as correct.
FRAMES = (
    ((400, 100), (0.0, 25.0), 0.5),
    ((100, 400), (87.5, 0.0), 0.25),
)

#: The region the document starts on, in the pixels of that image.
REGION = {"x": 0, "y": 0, "width": 8, "height": 8}


class CompositeParams(ParamsBase):
    """A region, a span, and something typed, so the third gets no editor."""

    region: ROI = ROI(x=0, y=0, width=8, height=8)
    frames: tuple[int, int] = SPAN
    count: int = 4


def _spec() -> ToolSpec:
    return ToolSpec(
        tool_id="composite",
        version="1.0.0",
        summary="A tool that exists to declare a kind on each surface.",
        params_model=CompositeParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
        param_stereotypes={
            "region": ParamStereotype.REGION,
            "frames": ParamStereotype.SPAN,
            "count": ParamStereotype.SCALAR_RANGE,
        },
    )


@pytest.fixture
def session(tmp_path: Path) -> Session:
    """One node of the tool above, with both composite parameters set."""
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_NODE,
                    tool_id="composite",
                    version="1.0.0",
                    params={"region": REGION, "frames": list(SPAN)},
                ),
            )
        ),
    )
    return Session(tmp_path / "clip.sieve.yaml", project)


@pytest.fixture(params=FRAMES, ids=("letterboxed", "pillarboxed"))
def shown(request) -> tuple[tuple[int, int], tuple[float, float], float]:
    """One of the two shapes, and where the canvas puts it. Every canvas case runs twice."""
    return request.param


@pytest.fixture
def canvas(qapp, shown: tuple[tuple[int, int], tuple[float, float], float]) -> Any:
    """A viewport showing one frame, shrunk to fit and inset on one axis."""
    del qapp
    from PySide6.QtGui import QImage

    from sieve.gui.canvas import VideoCanvas

    widget = VideoCanvas()
    widget.resize(*CANVAS_SIZE)
    frame = QImage(*shown[0], QImage.Format.Format_RGB888)
    frame.fill(0)
    widget.set_frame(0, frame)
    return widget


@pytest.fixture
def band(qapp) -> Any:
    """A strip 1000 px wide over a 1000-frame source: one column per frame."""
    del qapp
    from sieve.gui.timeline.bar import TimelineStrip

    strip = TimelineStrip()
    strip.resize(STRIP_WIDTH, strip.height())
    strip.set_source_frames(SOURCE_FRAMES)
    strip.set_timebase(SOURCE_FPS)
    return strip


def _widget_point(
    shown: tuple[tuple[int, int], tuple[float, float], float], x: float, y: float
) -> tuple[float, float]:
    """Where pixel `(x, y)` of the shown image lands on the canvas."""
    _, origin, scale = shown
    return origin[0] + x * scale, origin[1] + y * scale


def test_a_drawn_region_enters_as_a_set_param(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """A box drawn on the viewport is one parameter, in the frame's own pixels.

    Two claims in one gesture, and both are what the ADR binds an overlay to a
    field for (`adr/gui-knows-kinds-not-tools.md`). The value is denominated in
    the image the surface is showing rather than in the pixels the user's mouse
    moved across, which is why the same drag over two differently shaped frames
    is the same region. And it arrives through the command layer — undo is the
    evidence, because a value written onto the document directly would leave
    nothing to step back to.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, shown[0])
    driving.drag(editor, _widget_point(shown, 20, 20), _widget_point(shown, 100, 60))

    assert session.project.params_for(_NODE)["region"] == {
        "x": 20,
        "y": 20,
        "width": 80,
        "height": 40,
    }
    assert session.undo().params_for(_NODE)["region"] == REGION


def test_a_dragged_span_enters_as_a_set_param(qapp, session: Session, band: Any) -> None:
    """A handle dragged on the band is one parameter, in source frames.

    The same claim as the region's, on the other surface and through the other
    kind: the editor is bound to `frames` and its whole output is that field's
    value. The end lands one past the frame under the cursor because the pair
    is half-open — `timeline/window.py` is where that convention is applied,
    and restating it here would be a second answer.
    """
    del qapp
    from sieve.gui.kind_editors import SpanEditor

    editor = SpanEditor(band, session, _NODE, "frames", list(SPAN))
    driving.drag(editor, (float(SPAN[1]), BAND_Y), (500.0, BAND_Y))

    assert session.project.params_for(_NODE)["frames"] == [SPAN[0], 501]
    assert session.undo().params_for(_NODE)["frames"] == list(SPAN)


def test_an_overlay_is_the_rectangle_its_surface_is(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """The editor follows the surface's size, because the splitter moves it.

    Every coordinate this module reads is in the host's frame, and the two are
    the same rectangle only for as long as the overlay tracks it. An editor
    left at the size it was built at maps a press to whatever pixel used to be
    under it — the failure that reads as a mouse that has come loose, and one
    the user meets by dragging the split rather than by doing anything to the
    editor.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, shown[0])
    # Shown, because Qt holds a hidden widget's resize event until it is: this
    # is the one case here whose subject is what happens when the size actually
    # changes, rather than what the size is.
    canvas.show()
    driving.pump()
    canvas.resize(CANVAS_SIZE[0] * 2, CANVAS_SIZE[1] * 2)

    assert editor.size() == canvas.size()


def test_the_other_handle_moves_the_other_edge(qapp, session: Session, band: Any) -> None:
    """The left handle pins the right, which is the half a mirrored rule loses.

    Two edges and two pins is the whole of what makes these handles rather than
    one mark: a start dragged to 50 that also moved the end would be the body
    gesture the working window has and a span parameter does not.
    """
    del qapp
    from sieve.gui.kind_editors import SpanEditor

    editor = SpanEditor(band, session, _NODE, "frames", list(SPAN))
    driving.drag(editor, (float(SPAN[0]), BAND_Y), (50.0, BAND_Y))

    assert session.project.params_for(_NODE)["frames"] == [50, SPAN[1]]


def test_a_gesture_on_a_viewport_with_no_frame_writes_nothing(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """Nothing on screen is nothing to draw on, during a gesture as well as before.

    The application starts with no frame and returns there when a source
    closes, which can happen with a drag already under way — and the mapping
    divides by a scale that is only defined while there is an image, so the
    half-finished gesture has to end in nothing rather than in a region
    denominated in a frame that has gone.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, shown[0])
    driving.press(editor, *_widget_point(shown, 20, 20))
    canvas.clear()
    driving.release(editor, *_widget_point(shown, 100, 60))

    assert session.project.params_for(_NODE)["region"] == REGION
    assert not session.can_undo()

    driving.press(editor, *_widget_point(shown, 20, 20))
    driving.move(editor, *_widget_point(shown, 100, 60))

    assert editor.shown_rect().isEmpty()


def test_an_editor_per_kind_never_per_tool(
    qapp, session: Session, canvas: Any, band: Any, shown: Any
) -> None:
    """Which parameters get an editor is the kinds' answer, and which surface too.

    The generator's asymmetry one surface out (`param_form.py`): a tool that
    declares a region gets the viewport for free, and a tool declaring a kind
    with no entry gets nothing rather than a refusal — most kinds are typed
    into the panel, and the absence is what says so. `count` is the case that
    holds the second half.
    """
    del qapp
    from sieve.gui.kind_editors import _EDITORS, RegionEditor, SpanEditor, bind_editors

    # Both composite kinds a tool on the shelf declares today, and no others:
    # `BAND` is dragged on an axis nothing has named
    # (`todo/a-bands-axis-has-no-vocabulary-and-no-plot.md`) and `POINT` is
    # declared by no tool at all.
    assert set(_EDITORS) == {ParamStereotype.REGION, ParamStereotype.SPAN}

    editors = bind_editors(
        session,
        _NODE,
        _spec(),
        session.project.params_for(_NODE),
        canvas=canvas,
        timeline=band,
        region_extent=shown[0],
    )

    assert set(editors) == {"region", "frames"}
    assert isinstance(editors["region"], RegionEditor)
    assert isinstance(editors["frames"], SpanEditor)


def test_a_region_is_drawn_in_the_space_the_value_names_and_not_the_one_on_screen(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """The proxy trap, and the whole of 07.11's answer to it.

    The canvas is fed a display proxy of the footage
    (`transport/decode_worker.PROXY_WIDTH`), while `crop.py` says a region
    indexes the frame its own node is handed. On footage wider than the proxy the
    two are different rectangles, and an editor reading the image's own width
    writes a box that is a constant factor too small — silently, and only on
    large footage.

    So the extent is declared and the image's width is never read. Here the
    extent is twice the shown image on both axes, which is the shape a 2560-wide
    source meets a 1280-wide proxy in: every coordinate the gesture produces is
    twice what the same drag would have named before the declaration existed.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    (image_width, image_height), _, _ = shown
    extent = (image_width * 2, image_height * 2)
    editor = RegionEditor(canvas, session, _NODE, "region", REGION, extent)

    driving.drag(editor, _widget_point(shown, 20, 20), _widget_point(shown, 100, 60))

    # `_widget_point` places the cursor over *image* pixels (20, 20) and
    # (100, 60); in the space the value is denominated in those are twice as far
    # from the frame's origin.
    assert session.project.params_for(_NODE)["region"] == {
        "x": 40,
        "y": 40,
        "width": 160,
        "height": 80,
    }


def test_a_node_whose_space_the_window_cannot_name_gets_no_region_editor(
    qapp, session: Session, canvas: Any, band: Any
) -> None:
    """The other half of the same decision: no extent, no gesture.

    The extent of a node's input is a fact about what its upstream produces, and
    the only frame a window knows the size of is the footage's own — so a region
    parameter on a node reading a cropped or rescaled frame is denominated in a
    space nothing on screen is showing. `None` says so, and what the user gets is
    the form's read-only restatement of the value: a parameter they must type is
    better than a box that draws in units nobody can name.

    The span editor is unaffected, which is the assertion that keeps this from
    reading as "an editor was dropped": a span is denominated in source frames
    whatever a node does to the pixels.
    """
    del qapp
    from sieve.gui.kind_editors import SpanEditor, bind_editors

    editors = bind_editors(
        session,
        _NODE,
        _spec(),
        session.project.params_for(_NODE),
        canvas=canvas,
        timeline=band,
        region_extent=None,
    )

    assert set(editors) == {"frames"}
    assert isinstance(editors["frames"], SpanEditor)


def test_a_gesture_the_editor_does_not_own_reaches_the_surface(
    qapp, session: Session, band: Any
) -> None:
    """A press that is not on a handle is the band's, even inside the span.

    The strip means "seek here" everywhere it is not a handle, and an overlay
    covering it would take scrubbing away for as long as a span node is on
    screen. The press is placed *inside* the painted band rather than beside
    it, because the weaker version — a press somewhere the editor draws nothing
    — would pass for an overlay that owned every pixel it had painted.
    """
    del qapp
    from sieve.gui.kind_editors import SpanEditor

    editor = SpanEditor(band, session, _NODE, "frames", list(SPAN))
    seen: list[int] = []
    band.pressed.connect(seen.append)

    inside = (SPAN[0] + SPAN[1]) / 2.0
    driving.press(editor, inside, BAND_Y)

    assert seen == [int(inside)]
    assert not session.can_undo()


def test_a_drag_is_announced_once_on_release(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """The rectangle is painted from a draft and committed exactly once.

    The strip's two-tier rule, and the reason is sharper here than it is there:
    every value passed through on the way is a re-plan, a new cache key and a
    render of a region the user is still choosing. One undo entry per gesture
    is the other half — a drag that committed per move would take a hundred
    steps to undo.
    """
    del qapp
    from PySide6.QtCore import QRectF

    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, shown[0])
    start, end = _widget_point(shown, 20, 20), _widget_point(shown, 100, 60)
    driving.press(editor, *start)
    driving.move(editor, *end)

    assert editor.shown_rect() == QRectF(*start, end[0] - start[0], end[1] - start[1])
    assert not session.can_undo()

    driving.release(editor, *end)

    # And the box does not jump when the draft goes: what is painted after the
    # release is the committed value mapped back onto the frame, which is the
    # round trip the two coordinate spaces have to agree on.
    assert editor.shown_rect() == QRectF(*start, end[0] - start[0], end[1] - start[1])
    assert session.project.params_for(_NODE)["region"]["width"] == 80
    # Exactly one entry for the gesture: one step back reaches the document the
    # drag started from, and there is nothing behind it.
    assert session.undo().params_for(_NODE)["region"] == REGION
    assert not session.can_undo()


def test_a_region_drawn_off_the_frame_names_only_pixels_it_has(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """A drag across the whole viewport is the whole frame, and no more than it.

    Corner to corner of the *widget*, which on one axis is the frame's own edge
    and on the other is out in the margin the canvas leaves around it. Clamping
    to the widget instead of to the image would scale that margin into pixel
    coordinates the frame does not have, and `crop` would be handed a region it
    could only silently trim. Both shapes run, because which axis the margin is
    on is the thing the two of them disagree about.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, shown[0])
    driving.drag(editor, (0.0, 0.0), (float(CANVAS_SIZE[0]), float(CANVAS_SIZE[1])))

    assert session.project.params_for(_NODE)["region"] == {
        "x": 0,
        "y": 0,
        "width": shown[0][0],
        "height": shown[0][1],
    }


def test_a_gesture_that_encloses_nothing_writes_nothing(
    qapp, session: Session, canvas: Any, shown: Any
) -> None:
    """A click on the viewport is how a half-started rectangle is abandoned.

    `ROI` refuses a zero extent outright, so the alternative to ignoring the
    gesture is a refusal the user gets for having clicked — and a region of no
    area is not a value anybody could have meant.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, shown[0])
    driving.click(editor, *_widget_point(shown, 20, 20))

    assert session.project.params_for(_NODE)["region"] == REGION
    assert not session.can_undo()


def test_building_an_editor_is_not_an_edit_of_the_document(
    qapp, session: Session, canvas: Any, band: Any, shown: Any
) -> None:
    """Showing a value must not write it back — the form's rule, on the overlays.

    An editor is built for whichever node the walk is on, which is every
    keystroke of an Up-and-Down walk through a graph. One write per build would
    put a value nobody drew on the undo stack per redraw, and the first undo of
    the session would step back to the document already on screen.
    """
    del qapp
    from sieve.gui.kind_editors import bind_editors

    bind_editors(
        session,
        _NODE,
        _spec(),
        session.project.params_for(_NODE),
        canvas=canvas,
        timeline=band,
        region_extent=shown[0],
    )

    assert not session.can_undo()
