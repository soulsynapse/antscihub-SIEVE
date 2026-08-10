"""A `BLOCK` result is a field of cells over its input, not a stretched frame.

`emission_paint.py` dispatches on `ElementKind`, so what is asserted here is the
half a greyscale `image_of` cannot produce: cells with boundaries, coloured by a
range that does not move with the frame. Both are claims about pixels — a cell's
colour has no geometric referent the way a rect does — so the fixture is
`todo/the-source-badge-is-painted-by-nothing.md`'s: a `grab()` of the canvas over
one field compared against the same canvas over another.

Two of the three cases drive `VideoCanvas` directly. What separates a field from
a stretch is visible on any values at all, and a window is the wrong instrument
for it: the block grid a real clip produces is whatever `block_signal`'s auto
size makes of the footage, and an assertion about cell boundaries would then be
about the fixture's dimensions. The window case is the wiring — that the kind
reaches the canvas from `app._elements` and the range from `graph_panel` — which
is the half no unit case can reach.

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

#: `test_app.py`'s ceiling and its reason: every wait ends when the thing it
#: waits on does, so a generous one costs only the flake it prevents.
_TIMEOUT_MS = 60_000

#: Inside the clip's first burst, so the grid has a signal in it rather than the
#: zeros `block_signal` emits where nothing moved. `test_gui_loop_budget.py`'s
#: index over the same graph and the same clip, and it is the last one there is:
#: `detect` reads ahead of every frame it answers for, and the preview does not
#: know where the footage ends, so a render past here decodes off the end of it
#: (`findings/2026.08.07-a-lookahead-at-the-end-of-a-video-is-a-decode-error.md`).
_AT = 12

#: Big enough that the canvas has an area to paint into on the offscreen
#: platform, where a window is never given one by a compositor.
_WINDOW = (1200, 800)

#: The canvas the unit cases paint on, and the picture under the field. The
#: under image decides the letterbox — a field has no pixels of its own — and it
#: is smaller than the canvas on both axes, so the never-upscale clamp places it
#: at its own size and the cell arithmetic below is over known numbers.
_CANVAS = (400, 200)
_UNDER = (40, 30)


@pytest.fixture
def block_project(stirred_clip: Path, tmp_path: Path) -> Path:
    """The oracle's `crop -> block_signal -> detect` over the stirred clip.

    The reference workload rather than a graph of this file's own, for
    `test_gui_loop_budget.py`'s reason: `detect`'s band decides how far ahead of
    `_AT` the render reaches, and a chain assembled here would be a second
    configuration of that with nothing keeping the two in step. It also supplies
    the pin — a `BLOCK` step has no trace of its own until a solo reduces it
    (`todo/the-solo-is-what-gives-a-block-step-a-trace.md`), and the range this
    item reads comes off the graph panel.
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


def _canvas_over(values: Any, span: tuple[float, float]) -> Any:
    """A canvas showing `values` as a field over `_under_picture`, field alone.

    At full opacity so the grab is the field's own colours: a blend against the
    input would make every assertion below about the input too.
    """
    from sieve.core.tool_base import ElementKind
    from sieve.gui.canvas import VideoCanvas

    canvas = VideoCanvas()
    canvas.resize(*_CANVAS)
    canvas.overlay_opacity = 1.0
    assert canvas.set_values(0, values, under=_under_picture(), kind=ElementKind.BLOCK, span=span)
    return canvas


def test_the_block_field_is_flat_cells_and_not_the_frame_stretched(qapp) -> None:
    """Cells, with boundaries between them, and colour rather than grey.

    Three claims one grab answers. A greyscale `image_of` of the same array,
    which is what the viewport did before, fails all three: smoothed up to the
    letterbox it is a gradient, so no two points inside a cell agree, and every
    pixel of it has equal channels.
    """
    del qapp
    from sieve.gui.emission_paint import grid_edges

    values = np.array([[0.0, 1.0], [0.6, 0.2]], np.float32)
    canvas = _canvas_over(values, (0.0, 1.0))
    grabbed = canvas.grab().toImage()

    xs, ys = grid_edges(canvas.view_rect(), 2, 2)
    assert xs[2] - xs[0] == _UNDER[0], "the field spans the picture it is drawn over"

    def cell(row: int, col: int, dx: int, dy: int) -> Any:
        return grabbed.pixelColor(xs[col] + dx, ys[row] + dy)

    # Two points well inside one cell, and one of them next to the cell's own
    # edge: a stretch varies across a cell, a field does not.
    assert cell(0, 0, 2, 2) == cell(0, 0, 8, 6)
    assert cell(0, 0, 2, 2) != cell(0, 1, 2, 2)
    assert cell(0, 0, 2, 2) != cell(1, 0, 2, 2)

    coloured = cell(0, 1, 2, 2)
    assert coloured.red() != coloured.blue(), "a cell is coloured, not grey"


def test_the_block_field_colour_is_the_windows_range_and_not_the_frames(qapp) -> None:
    """A cell means the same thing at every playhead position.

    `image_of` maps each frame through its own extremes and says why — a picture
    has no axis. A field does have one, so the same value must paint the same
    colour whatever else is in the frame: the two canvases below carry the same
    values against different ranges and cannot look alike, and the two that carry
    proportional values against proportional ranges cannot look different.
    """
    del qapp

    values = np.array([[0.0, 0.5], [1.0, 0.25]], np.float32)
    against_one = _canvas_over(values, (0.0, 1.0)).grab().toImage()
    against_two = _canvas_over(values, (0.0, 2.0)).grab().toImage()
    doubled = _canvas_over(values * 2.0, (0.0, 2.0)).grab().toImage()

    assert against_one != against_two, "the range is ignored; the frame is being stretched"
    assert against_one == doubled


def test_the_block_field_reaches_the_canvas_with_the_kind_and_the_range(
    qapp, block_project: Path
) -> None:
    """The kind is handed to the canvas, and the range comes off the graph.

    The canvas never looks either one up — that is what keeps the registry out of
    a widget — so the wiring is the claim: standing on a `BLOCK` node leaves the
    viewport holding that node's values as a field, with the graph's own axis,
    and holding no greyscale picture at all.
    """
    del qapp
    from sieve.gui.app import MainWindow

    discover()
    window = MainWindow([block_project])
    window.resize(_WINDOW[0], _WINDOW[1])
    window.show()
    try:
        window.open_project(block_project)
        driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
        window.timeline.set_window(SPAN)
        window.go_down()
        window.go_down()
        assert window.current_node is not None and window.current_node.node_id == BLOCKS
        window.player.seek(_AT)
        driving.wait_until(lambda: window.player.current_index == _AT, _TIMEOUT_MS)
        driving.wait_until(lambda: window.viewport.field is not None, _TIMEOUT_MS)
        driving.wait_until(lambda: not window.graph.is_stale, _TIMEOUT_MS)
        assert window.tuning.last_error is None, window.tuning.last_error

        field = window.viewport.field
        assert field is not None
        assert field.values.ndim == 2
        assert float(field.values.max()) > float(field.values.min())
        assert (field.low, field.high) == window.graph.value_range()

        assert window.viewport.frame is None, "a block result has no greyscale picture"
        assert window.viewport.under is not None
        assert not window.viewport.showing_source
        # The letterbox is the input's, not the grid's: a field has no pixels of
        # its own, and a canvas fitted to `(ny, nx)` is the stretch this item
        # exists to stop.
        under = window.viewport.under
        box = window.viewport.frame_rect()
        assert box.width() / box.height() == pytest.approx(under.width() / under.height())
    finally:
        window.close()
