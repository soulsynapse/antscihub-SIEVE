"""The viewport's two arguments about arithmetic, neither of which a repaint shows.

`canvas.py` is reached from the timeline and app cases, which hand it whatever
frame the walk produced and then read the strip or the graph. Both of the
decisions below are invisible from there: a frame drawn at the wrong scale is
still a frame, and a constant frame comes out the same colour either way.

Qt and `sieve.gui` are imported inside the tests, for the reason `conftest.py`
gives.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

#: A viewport far larger than the frame below it on both axes, so that a scale
#: taken from either dimension would enlarge.
CANVAS_WIDTH = 400
CANVAS_HEIGHT = 200

#: The frame's own pixels. Not proportional to the viewport: a frame whose
#: aspect matched would place the same rectangle under a stretch.
FRAME_WIDTH = 40
FRAME_HEIGHT = 30


@pytest.fixture
def canvas(qapp) -> Any:
    del qapp
    from sieve.gui.canvas import VideoCanvas

    widget = VideoCanvas()
    widget.resize(CANVAS_WIDTH, CANVAS_HEIGHT)
    return widget


def test_a_frame_smaller_than_the_viewport_is_drawn_at_its_own_size(canvas: Any) -> None:
    """The never-upscale rule, which is the whole reason the scale is clamped.

    The decode side hands back a proxy sized for display, so a viewport that
    filled itself with a small frame would invent detail the user then judges
    footage by. Asserted on `frame_rect` because a painted pixel is not
    something a test can ask about.
    """
    from sieve.gui.canvas import image_of

    ramp = np.linspace(0.0, 1.0, FRAME_WIDTH * FRAME_HEIGHT, dtype=np.float32)
    image = image_of(ramp.reshape(FRAME_HEIGHT, FRAME_WIDTH))
    assert image is not None
    canvas.set_frame(0, image)

    box = canvas.frame_rect()
    assert (box.width(), box.height()) == (FRAME_WIDTH, FRAME_HEIGHT)
    assert box.center().x() == pytest.approx(CANVAS_WIDTH / 2.0)
    assert box.center().y() == pytest.approx(CANVAS_HEIGHT / 2.0)


def test_a_constant_frame_is_flat_and_is_not_divided_by_its_own_spread() -> None:
    """A frame whose values do not vary has a spread of zero.

    The assertion is that no division happens, not that the picture is flat:
    `nan_to_num` maps the `0 / 0` the division would produce back to the same
    zero the guarded branch writes, so the two agree on every pixel of an
    ordinary constant frame and only the floating-point operation separates
    them.
    """
    from sieve.gui.canvas import image_of

    with np.errstate(invalid="raise", divide="raise"):
        image = image_of(np.full((4, 5), 7.0, np.float32))

    assert image is not None
    assert {image.pixelColor(x, y).value() for y in range(4) for x in range(5)} == {0}
