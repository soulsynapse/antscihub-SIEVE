"""What the window paints when the node under the walk owns a drawn rectangle.

`app.viewport_node` refuses to show a render for a source-fed node carrying a
`region` parameter, because that is the one case where an editor's box is on the
canvas: the value is denominated in the frame the node reads, and painting the
node's *output* would draw the box over a rectangle the value does not index
(`kind_editors.RegionEditor`). Every other case in the suite walks to the
detector on a graph whose `crop` is downstream of a `downsample`, so nothing ever
stands where that refusal is reachable.

The first case here decodes nothing. The source is a name the window resolves
and hands to the transport, which fails on it asynchronously; what is asserted
is the decision `viewport_node` makes from the document and the shelf, which is
taken before any frame arrives.

**The second case decodes, because it is about the panel and not the document.**
A window with no footage open has no series to be stale about — `TuningLoop`
declines the request outright — so a case asserting that a dropped write leaves
no stale mark would pass on a window nothing could have marked. Real footage and
a settled first refill are what make both halves of it say something.

Qt and `sieve.gui` are imported inside the test, for the reason `conftest.py`
gives.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceRef, SourceSpan
from sieve.tools import discover
from tests.gui import driving

#: `crop` at the root, so its `region` is denominated in the footage, and one
#: node under it with no stereotype of its own — which is what separates "the
#: window has no picture to show" from "the window declines to show one".
_ROOT = "cut"
_BELOW = "smaller"

#: The second case's graph. The combo belongs to `blocks`, which is also the
#: node the panel draws, so the two constraints are one node: a graph is one
#: value per frame (`gui/graph_panel.py`), and `block_signal` over a block wider
#: than the frame is the cheapest tool on the shelf that emits one. It is the
#: second of two because the walk onto it is what asks for the first refill —
#: nothing else does, the bar holding the working window and no signal carrying
#: it to `refill_graph`, which reads it on the way past.
_COARSE = "coarse"
_BLOCKS = "blocks"

#: Wider than the downsampled frame, so the grid is a single block. Explicit
#: rather than left at the auto block, which is denominated in source pixels and
#: would put the grid's size at the mercy of the fixture's dimensions.
_ONE_BLOCK = 1024

#: The entry the combo opens on, and the one the popup's first Return
#: re-selects. The second gesture takes End to the far end of the list, so the
#: chosen one is the last of `block_signal.Signal`.
_SHOWN = "change_energy"
_CHOSEN = "flow_agreement"

#: Two frames of the fixture, well apart so the pictures at them differ, and
#: both inside it. Which is which matters only in that the drag lands somewhere
#: the settle then has to repaint.
_SETTLED_ON = 13
_DRAGGED_TO = 27

#: How long the decode thread is given to open the clip and the preview to
#: render it. `test_gui_cli_parity.py`'s number and its reason: every wait here
#: ends when the thing it waits on does, so a generous ceiling costs nothing but
#: the flake it prevents.
_TIMEOUT_MS = 60_000


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=(
                Node(node_id=_ROOT, tool_id="crop", version="1.0.0"),
                Node(node_id=_BELOW, tool_id="downsample", version="1.0.0"),
            ),
            edges=(Edge(upstream=_ROOT, downstream=_BELOW),),
        ),
    )
    path = tmp_path / "clip.sieve.yaml"
    project.save(path)
    return path


def test_a_source_fed_region_node_keeps_the_source_on_the_canvas(qapp, project_file: Path) -> None:
    """The refusal, and the ordinary case that says the refusal is doing it.

    Standing on the second node is not decoration: `viewport_node` is `None` for
    a walk with no spec above it too, so a case asserting only the `None` would
    pass on a shelf that had never resolved `crop` at all.
    """
    del qapp
    from sieve.gui.app import MainWindow

    window = MainWindow([project_file])
    try:
        window.open_project(project_file)

        assert window.current_node is not None
        assert window.current_node.node_id == _ROOT
        assert window.viewport_node is None

        window.go_down()
        assert window.current_node.node_id == _BELOW
        assert window.viewport_node == _BELOW
    finally:
        window.close()


@pytest.fixture
def tunable_project(synthetic_video: Path, tmp_path: Path) -> Path:
    """A downsample and a block signal over real footage, the choice at a value.

    `signal` is written into the document rather than left at the model's
    default: re-selecting the entry a combo shows is only a no-op if the value
    it holds is the value the document holds, and a document with no `signal`
    key at all would be *changed* by a write of the shown one.
    """
    video = tmp_path / synthetic_video.name
    video.write_bytes(synthetic_video.read_bytes())
    path = tmp_path / "clip.sieve.yaml"
    Project.for_video(video, tmp_path).model_copy(
        update={
            "pipeline": Pipeline(
                nodes=(
                    Node(node_id=_COARSE, tool_id="downsample", version="1.0.0"),
                    Node(
                        node_id=_BLOCKS,
                        tool_id="block_signal",
                        version="1.0.0",
                        params={"signal": _SHOWN, "block": _ONE_BLOCK},
                    ),
                ),
                edges=(Edge(upstream=_COARSE, downstream=_BLOCKS),),
            )
        }
    ).save(path)
    return path


def _settled(window: Any) -> None:
    """Wait for the refill in flight, and fail with its exception rather than a timeout."""
    driving.wait_until(
        lambda: not window.graph.is_stale or window.tuning.last_error is not None, _TIMEOUT_MS
    )
    assert window.tuning.last_error is None, window.tuning.last_error


def test_a_dropped_write_leaves_the_graph_where_it_was(qapp, tunable_project: Path) -> None:
    """A gesture the document refuses does not announce a refill it will not do.

    `Session.commit` drops a value equal to the one it holds, so re-selecting a
    combo's shown entry appends nothing and leaves no undo entry. What outlives
    that refusal is the notification: the widget emits `edited` beside the write
    rather than out of it, `refill_graph` believes it, and the panel wears the
    stale mark for an edit that never landed. The keys are identical so nothing
    recomputes — the cost is entirely what the user is told.

    Both halves, because a panel nothing could mark is not stale either: the
    change on the same combo two lines down is what says this window's mark
    works and that its absence above is the refusal being visible.
    """
    del qapp
    from PySide6.QtCore import Qt

    from sieve.gui.app import MainWindow

    discover()
    window = MainWindow([tunable_project])
    window.show()
    try:
        window.open_project(tunable_project)
        driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
        # The stretch the user is tuning on. Set rather than defaulted: the bar
        # holds no window until something asks for one, and a refill with none
        # is declined before it reaches the panel.
        window.timeline.set_window(SourceSpan(start=0, end=window.player.metadata.frame_count))
        # The walk onto the node fills its graph, and that render is the
        # session's cold one. Waited for so the mark asserted below is about
        # this gesture rather than about a panel that had never come clean.
        window.go_down()
        assert window.current_node is not None
        assert window.current_node.node_id == _BLOCKS
        _settled(window)
        assert window.graph.series is not None

        combo = window.control.step_pane.form.widget("signal")
        assert combo.currentData() == _SHOWN

        # PageDown opens the popup on the entry the combo already shows, and
        # Return selects it — Qt's `activated`, a complete statement of intent
        # over a value that is not a change (`gui/param_form.py`). PageDown
        # rather than Down because Down is the walk's own hotkey and the window
        # takes it before the combo sees it
        # (`findings/2026.08.09-a-key-sent-to-a-widget-inside-the-window-is-taken-by-the-walks-hotkey.md`).
        driving.key(combo, Qt.Key.Key_PageDown)
        driving.key(combo.view(), Qt.Key.Key_Return)

        session = window.session
        assert session is not None
        assert session.project.params_for(_BLOCKS)["signal"] == _SHOWN
        assert not session.can_undo()
        assert not window.graph.is_stale

        driving.key(combo, Qt.Key.Key_PageDown)
        driving.key(combo.view(), Qt.Key.Key_End)
        driving.key(combo.view(), Qt.Key.Key_Return)

        assert session.project.params_for(_BLOCKS)["signal"] == _CHOSEN
        assert window.graph.is_stale
        # Left settled: a window closed mid-render tears down the reader the
        # render is holding.
        _settled(window)
    finally:
        window.close()


def test_the_source_badge_rises_on_a_drag_and_falls_on_the_settle(
    qapp, tunable_project: Path
) -> None:
    """The interval the render-on-settle ruling opened, with the mark on it.

    The walk stands on `block_signal`, whose output is not footage, so the drag
    does not merely delay the picture — it swaps which node's picture is up.
    Both halves are needed: a badge that never falls would mark a window that is
    showing exactly what it claims to, and a badge that never rises is the
    unmarked interval this case exists about.

    Driven through the player rather than through a slider, because what decides
    the render is the permission the frame arrives with
    (`transport/request_intent.py`) and `scrub` is where a drag produces one.
    """
    del qapp
    from sieve.gui.app import MainWindow

    discover()
    window = MainWindow([tunable_project])
    window.show()
    try:
        window.open_project(tunable_project)
        driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
        window.timeline.set_window(SourceSpan(start=0, end=window.player.metadata.frame_count))
        window.go_down()
        assert window.current_node is not None and window.current_node.node_id == _BLOCKS
        _settled(window)

        window.player.seek(_SETTLED_ON)
        driving.wait_until(lambda: window.player.current_index == _SETTLED_ON, _TIMEOUT_MS)
        # The field rather than the frame: `block_signal` declares `BLOCK`, so
        # its output is drawn as cells and the viewport holds no image of its own
        # while it is up (`gui/emission_paint.py`).
        driving.wait_until(lambda: window.viewport.field is not None, _TIMEOUT_MS)
        assert not window.viewport.showing_source

        window.player.scrub(_DRAGGED_TO)
        driving.wait_until(lambda: window.player.current_index == _DRAGGED_TO, _TIMEOUT_MS)
        assert window.viewport.showing_source
        assert window.viewport.badge_text() == "source"
        dragged = window.viewport.frame
        assert dragged is not None

        window.player.seek(_DRAGGED_TO)
        driving.wait_until(lambda: not window.viewport.showing_source, _TIMEOUT_MS)
        # One index, painted twice and differently: what the badge was about is
        # which node's picture was up, not which frame — and here the two are not
        # even the same kind of picture.
        assert window.viewport.frame is None
        assert window.viewport.field is not None
    finally:
        window.close()
