"""The canvas is the walked step's result over its input, off one render.

`adr/the-walked-step-owns-the-canvas.md` rules the picture is the referent's
composite. The two claims here are the two halves of that ruling that can be
made false independently: *what* is drawn — both layers, blended at the opacity
the canvas holds — and *what it costs*, which is one `render_frame` and not a
second one for the input. `FrameResult` carries every node's output for the
frame, so the input is the parent entry of the same result; a second render
would be a second answer to `slider_to_preview` and attributable to neither
half.

The graph is two `PIXEL` nodes over the stirred clip, which is `PLAN.md`'s Phase
10 gate and not a preference: `synthetic_video`'s frames are spatially uniform
(`findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md`), and
`image_of` stretches a frame between its own extremes, so a constant frame and a
constant difference paint the same black rectangle and a composite of them says
nothing.

Qt and `sieve.gui` are imported inside the test, for the reason `conftest.py`
gives.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceSpan
from sieve.tools import discover
from tests.gui import driving

#: A downsample at the root and a motion history under it. The second's picture
#: differs from the first's, which a step that only rescales its input —
#: normalize, an upscaling rescale — would not: the canvas maps every frame
#: through its own extremes, so such a step paints exactly what it was handed and
#: the composite would be invisible for a reason that is not the composite's.
_COARSE = "coarse"
_MOTION = "motion"

#: `test_app.py`'s ceiling and its reason: every wait ends when the thing it
#: waits on does, so a generous one costs only the flake it prevents.
_TIMEOUT_MS = 60_000

#: Inside the clip's first burst, so the step below has motion to be a picture
#: of: outside one, a motion history has decayed to a constant and paints black.
_AT = 13

#: Big enough that the canvas has an area to paint into on the offscreen
#: platform, where a window is never given one by a compositor.
_WINDOW = (1200, 800)


@pytest.fixture
def two_picture_project(stirred_clip: Path, tmp_path: Path) -> Path:
    video = tmp_path / stirred_clip.name
    video.write_bytes(stirred_clip.read_bytes())
    path = tmp_path / "clip.sieve.yaml"
    Project.for_video(video, tmp_path).model_copy(
        update={
            "pipeline": Pipeline(
                nodes=(
                    Node(node_id=_COARSE, tool_id="downsample", version="1.0.0"),
                    Node(node_id=_MOTION, tool_id="motion_history", version="1.0.0"),
                ),
                edges=(Edge(upstream=_COARSE, downstream=_MOTION),),
            )
        }
    ).save(path)
    return path


def _opened(window: Any, project: Path) -> None:
    """Open, adopt the whole clip as the window, and walk onto the second node."""
    window.open_project(project)
    driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
    window.timeline.set_window(SourceSpan(start=0, end=window.player.metadata.frame_count))
    window.go_down()
    assert window.current_node is not None and window.current_node.node_id == _MOTION
    window.player.seek(_AT)
    driving.wait_until(lambda: window.player.current_index == _AT, _TIMEOUT_MS)
    driving.wait_until(lambda: window.viewport.under is not None, _TIMEOUT_MS)
    assert window.tuning.last_error is None, window.tuning.last_error


def test_the_canvas_paints_the_result_over_input_and_both_layers_show(
    qapp, two_picture_project: Path
) -> None:
    """Two layers, and the opacity between them is what decides the picture.

    Asserted by painting rather than by comparing the two arrays: what the item
    claims is about the surface, and a canvas holding both images and drawing
    one of them would satisfy every assertion made about its fields. At full
    opacity the input is hidden and at zero the result is, so three grabs that
    all differ is the blend itself being visible.
    """
    del qapp
    from sieve.gui.app import MainWindow

    discover()
    window = MainWindow([two_picture_project])
    # Given a size before it is shown: a grab of a widget with no area is a null
    # image, and two null images compare equal, so the assertions below would
    # pass on a canvas that painted nothing at all.
    window.resize(_WINDOW[0], _WINDOW[1])
    window.show()
    try:
        _opened(window, two_picture_project)
        assert not window.viewport.frame_rect().isEmpty()

        assert window.viewport.frame is not None
        assert window.viewport.under is not None
        assert not window.viewport.showing_source

        blended = window.viewport.grab().toImage()
        window.viewport.overlay_opacity = 1.0
        result_alone = window.viewport.grab().toImage()
        window.viewport.overlay_opacity = 0.0
        input_alone = window.viewport.grab().toImage()

        assert result_alone != input_alone
        assert blended != result_alone
        assert blended != input_alone
    finally:
        window.close()


def test_the_result_over_input_at_zero_opacity_is_the_input_painted(
    qapp, two_picture_project: Path
) -> None:
    """The under layer reaches the surface, pinned to a picture and not to a grab.

    The case above compares three grabs that sweep the *result*'s alpha, so an
    under layer that is held and never painted still passes it: at opacity 0.0
    the grab is the empty letterbox, which differs from the other two exactly as
    a real input layer would
    (`findings/loop/2026.08.10-three-grabs-that-all-differ-are-green-with-the-under-layer-never-painted.md`).
    Equality against a canvas handed the input as its only frame is false for a
    background and false for a layer nobody drew.

    The two boxes coincide because `frame_rect` fits the result and
    `motion_history` keeps its input's shape; a step that reshaped its input
    would letterbox the pair differently and this equality would be about the
    fit rather than about the layer.
    """
    del qapp
    from PySide6.QtGui import QImage

    from sieve.gui.app import MainWindow
    from sieve.gui.canvas import VideoCanvas

    # A shown widget grabs premultiplied and an unshown one does not, and QImage
    # compares unequal across formats whatever the pixels say. Both are opaque
    # over the canvas background, so the conversion is lossless here.
    opaque = QImage.Format.Format_RGB32

    discover()
    window = MainWindow([two_picture_project])
    window.resize(_WINDOW[0], _WINDOW[1])
    window.show()
    try:
        _opened(window, two_picture_project)
        assert not window.viewport.frame_rect().isEmpty()

        under = window.viewport.under
        assert under is not None

        window.viewport.overlay_opacity = 0.0
        input_alone = window.viewport.grab().toImage().convertToFormat(opaque)

        reference = VideoCanvas()
        reference.resize(window.viewport.size())
        reference.set_frame(_AT, under)
        assert reference.frame_rect() == window.viewport.frame_rect()

        assert input_alone == reference.grab().toImage().convertToFormat(opaque)
    finally:
        window.close()


def test_the_pair_comes_off_one_render_and_not_two(qapp, two_picture_project: Path) -> None:
    """The input is the parent entry of the render the result came out of.

    Counted on `PreviewSession.render_frame`, which is the single-frame path the
    viewport asks for: a repaint that asked twice would be affordable nowhere
    and attributable to neither half of the budget.
    """
    del qapp
    from sieve.gui.app import MainWindow
    from sieve.pipeline.preview import PreviewSession

    discover()
    window = MainWindow([two_picture_project])
    window.show()
    try:
        _opened(window, two_picture_project)

        calls: list[int] = []
        rendered = PreviewSession.render_frame

        def counted(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls.append(1)
            return rendered(self, *args, **kwargs)

        window.viewport.clear()
        PreviewSession.render_frame = counted  # type: ignore[method-assign]
        try:
            window.tuning.refilled.emit()
        finally:
            PreviewSession.render_frame = rendered  # type: ignore[method-assign]

        assert len(calls) == 1
        assert window.viewport.under is not None
    finally:
        window.close()
