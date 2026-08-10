"""The one magnifier, and the two things that must agree about where a pixel is.

The canvas paints through the view rect and the region editor maps through it,
and the case this file exists for is the one where those two can silently
disagree: an editor re-homed onto the fit while the picture is magnified draws a
box that looks perfectly correct on screen and commits coordinates the user
never aimed at. So the round trip below is pinned to the *painted* geometry —
the widget point where the canvas puts a given source pixel — and not to the
editor's own inverse, which a wrong-but-self-consistent pair would satisfy just
as well.

The frame is the source at its own resolution here, so the extent and the image
agree and the only thing between a source pixel and a widget point is the
magnifier. `test_kind_editors.py` is where they are made to disagree.

Qt and `sieve.gui` are imported inside the tests, for the reason `conftest.py`
gives; `driving.py` stands in for `qtbot` and says why there is none.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sieve.core.pipeline_model import Node, Pipeline, Project, SourceRef
from sieve.session.session import Session
from tests.gui import driving

_NODE = "n0"

#: A viewport the frame is letterboxed in, so the fit has an offset on one axis
#: and a scale that is neither 1.0 nor the magnified one. A fit scale of 1.0
#: would leave source pixels and widget pixels equal and the mapping asserted
#: by a coincidence.
CANVAS = (300, 200)
FRAME = (400, 200)

#: `FRAME` fitted into `CANVAS`: 0.75 per source pixel, inset vertically.
FIT_SCALE = 0.75
FIT_TOP = 25.0

#: Detents enough to reach `MAX_ZOOM` in one wheel, and the widget point they
#: are anchored on. Off the fit's centre on both axes: a centred anchor leaves
#: the view rect symmetric about the same point the fit is, and the two
#: rectangles then agree at exactly the pixel a case would sample.
DETENTS = 13
ANCHOR = (60.0, 100.0)

#: The two regions the round trip carries, in source pixels. Different values,
#: because a magnified drag that maps its corners onto the same clamped point
#: writes nothing at all — and a case that drew the same region twice would
#: read the *first* drag's value back and call it the second's.
#:
#: `AT_ZOOM` is small and sits where `ANCHOR` leaves the view, so both of its
#: corners are inside the widget at maximum magnification: a corner off the
#: widget would be a gesture no hand could make.
AT_FIT = {"x": 20, "y": 30, "width": 100, "height": 60}
AT_ZOOM = {"x": 80, "y": 96, "width": 12, "height": 6}

#: What the document starts on, so the value the drag writes is never the value
#: that was already there.
REGION = {"x": 0, "y": 0, "width": 8, "height": 8}

#: The two greys `image_of` stretches the frame below onto. Sampled from deep
#: inside a uniform half rather than near the seam, where a smooth upscale
#: interpolates between them.
DARK_HALF = 0
BRIGHT_HALF = 255


@pytest.fixture
def session(tmp_path: Path) -> Session:
    """One node carrying a region, with no tool behind it — see `test_kind_editors.py`."""
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_NODE,
                    tool_id="composite",
                    version="1.0.0",
                    params={"region": REGION},
                ),
            )
        ),
    )
    return Session(tmp_path / "clip.sieve.yaml", project)


@pytest.fixture
def canvas(qapp) -> Any:
    """A viewport showing a frame that is black on its left half and white on its right.

    The halves are what makes a painted pixel answerable: "the picture moved" is
    otherwise a claim about grey values nobody can name.
    """
    del qapp
    from sieve.gui.canvas import VideoCanvas
    from sieve.gui.emission_paint import image_of

    values = np.zeros((FRAME[1], FRAME[0]), np.float32)
    values[:, FRAME[0] // 2 :] = 1.0
    frame = image_of(values)
    assert frame is not None

    widget = VideoCanvas()
    widget.resize(*CANVAS)
    widget.set_frame(0, frame)
    return widget


def _painted_at(canvas: Any, x: float, y: float) -> tuple[float, float]:
    """The widget point where the canvas paints source pixel `(x, y)`.

    Off `view_rect`, which is what `paintEvent` draws into, so a gesture built
    on this is aimed at the picture the user is looking at rather than at
    whatever the editor believes about the geometry.
    """
    view = canvas.view_rect()
    return (
        view.x() + x * view.width() / FRAME[0],
        view.y() + y * view.height() / FRAME[1],
    )


def _corners(
    canvas: Any, region: dict[str, int]
) -> tuple[tuple[float, float], tuple[float, float]]:
    """`region`'s two corners, where the canvas is currently painting them."""
    return (
        _painted_at(canvas, region["x"], region["y"]),
        _painted_at(canvas, region["x"] + region["width"], region["y"] + region["height"]),
    )


def test_a_region_drawn_over_the_magnified_frame_lands_on_the_same_source_pixels_round_trip(
    qapp, session: Session, canvas: Any
) -> None:
    """A region aimed at the pixels the canvas is painting, at the fit and at 16x.

    This is the one place in the phase that can write a wrong value into a saved
    project: the box is drawn over the picture, the crop runs, the file is
    written, and nothing downstream can tell that the numbers are not the ones
    the user drew. The fit half is the control — it is the mapping that already
    worked — and the magnified half is the claim.

    The last assertion is the same mapping run the other way. A box that
    resolves correctly and then paints itself somewhere else is a box the user
    watches slide off the thing they aimed it at, and it is the half of the port
    that a round trip through the editor's own inverse cannot see.
    """
    del qapp
    from sieve.gui.kind_editors import RegionEditor

    editor = RegionEditor(canvas, session, _NODE, "region", REGION, FRAME)

    start, end = _corners(canvas, AT_FIT)
    assert start == (
        AT_FIT["x"] * FIT_SCALE,
        FIT_TOP + AT_FIT["y"] * FIT_SCALE,
    ), "the fit is where the magnifier's floor puts it"
    driving.drag(editor, start, end)
    assert session.project.params_for(_NODE)["region"] == AT_FIT

    driving.wheel(canvas, DETENTS, at=ANCHOR)
    assert canvas.view_rect() != canvas.frame_rect()

    magnified = RegionEditor(canvas, session, _NODE, "region", REGION, FRAME)
    start, end = _corners(canvas, AT_ZOOM)
    assert canvas.rect().contains(int(start[0]), int(start[1]))
    assert canvas.rect().contains(int(end[0]), int(end[1]))
    driving.drag(magnified, start, end)

    assert session.project.params_for(_NODE)["region"] == AT_ZOOM

    box = magnified.region_rect()
    assert (box.left(), box.top()) == pytest.approx(start)
    assert (box.right(), box.bottom()) == pytest.approx(end)


def test_the_magnified_frame_is_painted_through_the_view_rect_and_clipped_to_the_fit(
    qapp, canvas: Any
) -> None:
    """Where the picture is drawn, which is what makes the round trip above real.

    Sampled at one widget point the two rectangles disagree about: at the fit it
    shows a column from the bright half of the frame, and magnified about
    `ANCHOR` it shows one from the dark half. A canvas that mapped through the
    view rect and painted through the fit would leave the round trip green and
    the user aiming at the wrong thing.

    The letterbox is the second half: magnified content is wider and taller than
    the fit on both axes, so without a clip the inset rows fill with picture and
    the frame stops being a frame.
    """
    del qapp

    sample = (210, 100)
    inset = (150, 5)
    assert canvas.frame_rect().top() > inset[1], "the sample must be outside the fit"

    fitted = canvas.grab().toImage()
    assert fitted.pixelColor(*sample).red() == BRIGHT_HALF

    driving.wheel(canvas, DETENTS, at=ANCHOR)
    magnified = canvas.grab().toImage()

    assert magnified.pixelColor(*sample).red() == DARK_HALF
    assert magnified.pixelColor(*inset) == fitted.pixelColor(*inset)


def test_wheeling_back_out_leaves_nothing_magnified_and_the_view_rect_exactly_the_fit(
    qapp, canvas: Any
) -> None:
    """The floor is the fit itself, not a rectangle within an epsilon of it.

    The round trip above compares a value drawn at the fit with one drawn at
    16x, so a wheel-out that landed near the fit rather than on it would make
    the two disagree by a pixel at the edges and for a reason no case could
    name.
    """
    del qapp
    from sieve.gui.zoom import MIN_ZOOM

    driving.wheel(canvas, DETENTS, at=ANCHOR)
    driving.wheel(canvas, -DETENTS * 4, at=ANCHOR)

    assert canvas.zoom == MIN_ZOOM
    assert canvas.view_rect() == canvas.frame_rect()
