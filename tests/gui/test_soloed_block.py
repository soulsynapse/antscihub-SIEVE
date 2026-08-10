"""Hovering a cell asks for it, and the solo is what gives a `BLOCK` step a trace.

Four claims about the gesture and one about what it is for. The gesture half is
v2's discipline read back (`gui/composite_view.py`): hover asks, click latches,
leaving reverts to the latch, and *nothing* the pointer does moves the drawn
marker — only the model applying a solo does. So every case here separates the
two, and the ones that would pass on a widget painting its own gesture are
exactly the ones that fail on a widget that never asks.

**The marker and the cell under the pointer are both claims about pixels.**
Which cell carries the mark is not readable off geometry the way a rect is, so
the fixture is `todo/the-source-badge-is-painted-by-nothing.md`'s one layer in —
a `grab()` of the canvas with cell *i* soloed against the same canvas with cell
*j* soloed. The hit test is the same problem from the other side: it must read
the edges the colours landed on, which under a magnification is the view rect
and not the letterbox, and the case that separates those two is a colour
compared against the cell the canvas says is there.

The window case is what the gesture is *for*: `graph_panel` refuses a series
carrying more than one value per frame, so a `BLOCK` step had no trace under the
canvas at all, and the solo is the reduction that makes one value out of the
grid. It is also where the field's colour axis stops being another step's — the
range a cell is drawn against is the pinned step's trace axis, so a pinned,
soloed block step is the first state in which the field is denominated in its
own units (`findings/2026.08.10-the-block-fields-ramp-is-exhausted-four-orders-below-the-values-it-draws.md`).

Qt and `sieve.gui` are imported inside the tests, for the reason `conftest.py`
gives.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sieve.tools import discover
from tests.gui import driving
from tests.integration.test_v2_oracle import BLOCKS, SPAN, graph
from tests.projects import project_over

#: `test_block_field.py`'s ceiling and its reason: every wait ends when the thing
#: it waits on does, so a generous one costs only the flake it prevents.
_TIMEOUT_MS = 60_000

#: `test_block_field.py`'s geometry, and the same reason for it: the under
#: picture decides the letterbox and is smaller than the canvas on both axes, so
#: the never-upscale clamp places it at its own size and the cell arithmetic
#: below is over known numbers.
_CANVAS = (400, 200)
_UNDER = (40, 30)

#: `test_block_field.py`'s playhead — inside the clip's first burst, and the last
#: index the preview can render on this graph.
_AT = 12

#: Big enough that the canvas has an area to paint into on the offscreen
#: platform, where a window is never given one by a compositor.
_WINDOW = (1200, 800)

#: Four cells, all different, so a colour identifies a cell.
_VALUES = np.array([[0.0, 1.0], [0.6, 0.2]], np.float32)

#: Detents enough that one cell of a two-cell field covers the whole letterbox —
#: at 2x the left cell is exactly the fit's width, and `ZOOM_STEP` is 1.25.
_DETENTS = 4


@pytest.fixture
def block_project(stirred_clip: Path, tmp_path: Path) -> Path:
    """The oracle's `crop -> block_signal -> detect` over the stirred clip.

    `test_block_field.py`'s fixture and its reason: the reference workload rather
    than a graph of this file's own, because `detect`'s band decides how far ahead
    of `_AT` the render reaches and a chain assembled here would be a second
    configuration of that.
    """
    video = tmp_path / stirred_clip.name
    video.write_bytes(stirred_clip.read_bytes())
    path = tmp_path / "clip.sieve.yaml"
    project_over(video, tmp_path, graph()).save(path)
    return path


def _under_picture() -> Any:
    """A gradient to lay the field over, and the thing the letterbox is about."""
    from sieve.gui.emission_paint import image_of

    ramp = np.linspace(0.0, 1.0, _UNDER[0] * _UNDER[1], dtype=np.float32)
    image = image_of(ramp.reshape(_UNDER[1], _UNDER[0]))
    assert image is not None
    return image


def _canvas_over(values: Any) -> Any:
    """A canvas showing `values` as a field, at full opacity so the grab is the field's."""
    from sieve.core.tool_base import ElementKind
    from sieve.gui.canvas import VideoCanvas

    canvas = VideoCanvas()
    canvas.resize(*_CANVAS)
    canvas.overlay_opacity = 1.0
    assert canvas.set_values(
        0, values, under=_under_picture(), kind=ElementKind.BLOCK, span=(0.0, 1.0)
    )
    return canvas


def _in_cell(canvas: Any, row: int, col: int) -> tuple[float, float]:
    """The widget point at the centre of cell `(row, col)`.

    Off `grid_edges` against the canvas' own view rect rather than off the
    canvas' answer for where a cell is: a hit test asserted through the mapping
    it is being tested for would pass on any mapping at all.
    """
    from sieve.gui.emission_paint import grid_edges

    ny, nx = canvas.field.values.shape
    xs, ys = grid_edges(canvas.view_rect(), ny, nx)
    return ((xs[col] + xs[col + 1]) / 2.0, (ys[row] + ys[row + 1]) / 2.0)


def test_hovering_a_cell_asks_for_it_and_moves_nothing(qapp) -> None:
    """The pointer asks; the model answers. A widget that self-applied passes neither half.

    The second assertion is the one that matters: the canvas has been told a cell
    is under the pointer and still draws no solo, because what is drawn is what
    the model applied and the model has not answered yet.
    """
    del qapp

    canvas = _canvas_over(_VALUES)
    asked: list[Any] = []
    canvas.soloed.connect(asked.append)

    driving.move(canvas, *_in_cell(canvas, 0, 1))

    assert asked == [(0, 1)]
    assert canvas.solo is None

    canvas.set_solo((0, 1))
    assert canvas.solo == (0, 1)


def test_a_click_latches_and_leaving_an_unlatched_field_drops_the_solo(qapp) -> None:
    """What the pointer leaving reverts to, which is the whole of what a click buys.

    The latch is compared against the *applied* solo rather than against a
    private record of what was asked for, so a crossing the model dropped is
    asked again and one it satisfied is not asked twice — the emissions counted
    below are that rule.
    """
    del qapp

    canvas = _canvas_over(_VALUES)
    asked: list[Any] = []
    canvas.soloed.connect(asked.append)

    driving.move(canvas, *_in_cell(canvas, 0, 1))
    canvas.set_solo((0, 1))
    driving.leave(canvas)
    assert asked == [(0, 1), None], "an unlatched solo is dropped by the pointer leaving"
    canvas.set_solo(None)

    driving.move(canvas, *_in_cell(canvas, 1, 0))
    assert asked[-1] == (1, 0)
    canvas.set_solo((1, 0))
    driving.click(canvas, *_in_cell(canvas, 1, 0))
    driving.leave(canvas)
    assert len(asked) == 3, "a latched solo survives the pointer leaving, and asks for nothing"

    driving.move(canvas, *_in_cell(canvas, 1, 0))
    driving.click(canvas, *_in_cell(canvas, 1, 0))
    driving.leave(canvas)
    assert asked[-1] is None, "the second click unlatches, so leaving drops it again"


def test_the_cell_under_the_pointer_is_the_one_whose_colour_is_under_it(qapp) -> None:
    """Magnified, the hit test and the paint read one rectangle or they read two.

    A field drawn through the letterbox while the hit test reads the view rect
    looks perfectly correct — cells, boundaries, colours — and names the wrong
    cell everywhere the two rectangles disagree, which is everywhere once the
    user has magnified. Two cells, and a zoom that puts the left one across the
    whole letterbox: the canvas then says every point is that cell, and every
    point has to be its colour.
    """
    del qapp
    from PySide6.QtCore import QPointF

    canvas = _canvas_over(np.array([[0.0, 1.0]], np.float32))
    box = canvas.frame_rect()
    left = (int(box.left() + 2), int(box.center().y()))
    right = (int(box.right() - 2), int(box.center().y()))

    fitted = canvas.grab().toImage()
    assert canvas.cell_at(QPointF(*right)) == (0, 1)
    assert fitted.pixelColor(*right) != fitted.pixelColor(*left), "the two cells differ at the fit"

    driving.wheel(canvas, _DETENTS, at=(box.left(), box.top()))
    assert canvas.view_rect() != box

    magnified = canvas.grab().toImage()
    assert canvas.cell_at(QPointF(*right)) == (0, 0)
    assert magnified.pixelColor(*right) == magnified.pixelColor(*left)

    # The grid now runs on past the letterbox, and nothing out there is painted:
    # a point the view rect holds and the fit does not is over bare panel, and
    # answering it with the cell that would have been there picks out a cell the
    # user cannot see.
    beyond = QPointF(box.right() + 4.0, box.bottom() + 4.0)
    assert canvas.view_rect().contains(beyond)
    assert canvas.cell_at(beyond) is None


def test_the_soloed_cell_is_marked_where_the_field_is_drawn(qapp) -> None:
    """Which cell carries the mark is a claim about pixels and nothing else.

    Three grabs of one field: unsoloed, and with each of two cells picked out.
    None of the three may look alike, and the values behind them never move — so
    a difference is the marker and cannot be the picture.
    """
    del qapp

    bare = _canvas_over(_VALUES).grab().toImage()

    first = _canvas_over(_VALUES)
    first.set_solo((0, 0))
    second = _canvas_over(_VALUES)
    second.set_solo((1, 1))

    assert first.grab().toImage() != bare
    assert second.grab().toImage() != bare
    assert first.grab().toImage() != second.grab().toImage()


def test_a_soloed_cell_is_the_pinned_block_steps_trace_and_the_fields_axis(
    qapp, block_project: Path
) -> None:
    """The reduction the selection already names, and the axis it puts under the field.

    Two claims about one screen. A `BLOCK` step pinned with nothing soloed has no
    trace — `graph_panel` refuses a series of more than one value per frame — and
    the hover is what makes one: the series that arrives is that cell's own
    numbers, frame for frame, and not a reduction invented in the window.

    The second is what that buys the picture. The field is coloured against the
    pinned step's trace axis, so before this the cells of a block grid were drawn
    against `detect`'s gate — a count, four orders below the values in the field
    — and every cell above the gate's ceiling clipped to the ramp's hot end. With
    the block step itself pinned the axis is the field's own units, which is the
    soloed cell landing inside it rather than off the top.
    """
    del qapp
    from sieve.gui.app import MainWindow

    discover()
    window = MainWindow([block_project])
    window.resize(*_WINDOW)
    window.show()
    try:
        window.open_project(block_project)
        driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
        window.timeline.set_window(SPAN)
        window.go_down()
        window.go_down()
        assert window.current_node is not None and window.current_node.node_id == BLOCKS
        # The pin the item is about: the slot under the canvas is given to the
        # step whose field is on the canvas, which is what makes one axis of two.
        window.pin_current()
        assert window.pinned_node is not None and window.pinned_node.node_id == BLOCKS

        window.player.seek(_AT)
        driving.wait_until(lambda: window.player.current_index == _AT, _TIMEOUT_MS)
        driving.wait_until(lambda: window.viewport.field is not None, _TIMEOUT_MS)
        field = window.viewport.field
        assert field is not None
        assert window.graph.series is None, "a block step has no trace until a cell is soloed"

        loudest = np.unravel_index(int(np.argmax(field.values)), field.values.shape)
        cell = (int(loudest[0]), int(loudest[1]))
        driving.move(window.viewport, *_in_cell(window.viewport, *cell))
        assert window.solo == cell

        driving.wait_until(lambda: not window.graph.is_stale, _TIMEOUT_MS)
        assert window.tuning.last_error is None, window.tuning.last_error

        series = window.graph.series
        assert series is not None
        assert series.start_index == SPAN.start
        assert series.data.shape == (SPAN.frame_count, 1, 1)
        assert float(series.data[_AT - SPAN.start, 0, 0]) == pytest.approx(
            float(field.values[cell])
        )

        painted = window.viewport.field
        assert painted is not None
        assert (painted.low, painted.high) == window.graph.value_range()
        assert painted.low <= float(painted.values[cell]) <= painted.high
    finally:
        window.close()
