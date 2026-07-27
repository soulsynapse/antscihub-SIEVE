"""The step composite: selection targeting, the refresh guard, and the HUD.

Four claims, each a distinct way the composite could quietly wreck the tab.
A wrong target would compose frames of a step the user did not select; a
playhead refresh that ran while a window render was outstanding would
displace the graphs' render from the runner's one pending slot and the
series would never arrive; a refresh that cleared the HUD would erase
the window's cost series thirty times a second during playback; and a
pair that painted only at `render_finished` would leave the pane blank
for the whole first window render of every source.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer

pytestmark = pytest.mark.gui


class _StubRunner(QObject):
    """A runner that records submissions instead of rendering.

    The tab only reads `revision` and calls the two request methods; the
    signals exist so `_connect` finds what it wires. Everything a test
    asserts about ordering is in `window_renders` and `frame_renders`.
    """

    frame_cost = Signal(int, float)
    render_started = Signal(int)
    render_finished = Signal(object)
    render_failed = Signal(str)
    opened = Signal()
    open_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.revision = 0
        self.window_renders: list[object] = []
        self.frame_renders: list[int] = []
        self.consumers: list[object] = []

    def request_render(
        self, pipeline: object, window: object, replicate: object, consumer: object = None
    ) -> bool:
        self.revision += 1
        self.window_renders.append(pipeline)
        self.consumers.append(consumer)
        return True

    def request_frame(
        self, pipeline: object, index: int, replicate: object, consumer: object = None
    ) -> bool:
        self.revision += 1
        self.frame_renders.append(index)
        return True


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def stub() -> _StubRunner:
    return _StubRunner()


@pytest.fixture
def tab(
    qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument, stub: _StubRunner
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, stub, metrics=MetricBus())  # type: ignore[arg-type]
    qtbot.addWidget(instance)
    yield instance
    # The tab owns the detector thread, so it carries the same
    # shutdown obligation the player and the runner do. Without
    # this every tab built here leaks a QThread and the suite
    # wedges a few modules later.
    instance.shutdown()


def test_selection_defaults_to_the_tail_and_targets_the_deepest_rendered_step(
    tab: FilterTab,
) -> None:
    """Full current state is a selection, not a mode.

    The stack always has a selected step, defaulting to the tail — and a
    tab-side selection (windowed count has no node) must resolve the
    composite to the deepest step the render actually produced, which the
    caption says out loud. Clicking a card retargets, and the marker follows
    the model rather than the click.
    """
    assert tab.selected_step == "windowed_count"
    assert tab.composite.caption == "Block signal (deepest rendered)"

    card = tab.stack.card_for("rescale")
    assert card is not None and not card.selected
    card.mousePressEvent(None)

    assert tab.selected_step == "rescale"
    assert tab.composite.caption == "Rescale"
    assert card.selected
    tail = tab.stack.card_for("windowed_count")
    assert tail is not None and not tail.selected


def test_a_playhead_refresh_never_displaces_a_pending_window_render(
    tab: FilterTab, stub: _StubRunner, player: VideoPlayer
) -> None:
    """The guard the graphs depend on.

    The runner holds one pending request; a stream of single-frame composite
    refreshes issued while a window render is outstanding would overwrite it
    and the series would never arrive. So: after a resubmit, playhead moves
    must submit nothing — and once the render reports back, the next move
    must submit exactly the frame refresh it suppressed.
    """
    stub.opened.emit()  # the tab's own resubmit path, as the runner announces it
    assert len(stub.window_renders) == 1

    frame = QImage(160, 120, QImage.Format.Format_RGB32)
    player.frame_changed.emit(5, frame)
    player.frame_changed.emit(6, frame)
    assert stub.frame_renders == [], "a refresh ran while the graphs' render was outstanding"

    stub.render_finished.emit(object())
    player.frame_changed.emit(7, frame)
    assert stub.frame_renders == [7]


def test_the_pair_paints_at_the_playhead_frame_not_at_render_finished(
    tab: FilterTab, stub: _StubRunner
) -> None:
    """The first composite must not cost a whole window render.

    The window render's consumer catches the pair the moment the playhead
    frame passes — usually the window's first frame — and the pane must
    paint it on that frame's cost tick, hundreds of frames before
    `render_finished`. v1 drew its frame near-instantly; a pane that waits
    for the full window is the regression this test pins.
    """
    stub.opened.emit()
    consumer = stub.consumers[-1]
    assert consumer is not None

    frames = {
        "rescale": np.full((8, 8), 100, np.uint8),
        "normalize": np.full((8, 8), 128, np.uint8),
        "block_signal": np.ones((2, 3), np.float32),
    }
    outputs = {
        step.node.node_id: SimpleNamespace(data=frames[step.step_id])
        for step in tab.chain.steps
        if step.node is not None
    }
    consumer(SimpleNamespace(index=0, outputs=outputs))  # type: ignore[operator]
    assert tab.composite.frames() == (None, None), "painted before the GUI thread heard"

    stub.frame_cost.emit(0, 5.0)
    base, over = tab.composite.frames()
    assert base is not None and over is not None, "the pair waited for render_finished"


def test_a_composite_refresh_leaves_the_hud_series_alone(
    tab: FilterTab, stub: _StubRunner, player: VideoPlayer
) -> None:
    """Playback must not erase the window's cost series.

    A composite refresh is one frame at the playhead, served from the store;
    its `render_started` must not clear the HUD and its near-zero frame cost
    must not overwrite the render's real cost at that index. A window
    render's start, by contrast, still replaces the series — that contract
    stays the runner's.
    """
    stub.opened.emit()
    stub.render_started.emit(stub.revision)
    stub.frame_cost.emit(3, 25.0)
    stub.render_finished.emit(object())
    assert tab.hud.costs() == ((3, 25.0),)

    player.frame_changed.emit(3, QImage(160, 120, QImage.Format.Format_RGB32))
    assert stub.frame_renders == [3]
    stub.render_started.emit(stub.revision)  # the composite refresh starting
    stub.frame_cost.emit(3, 0.2)

    assert tab.hud.costs() == ((3, 25.0),), "the composite refresh touched the HUD"


def test_the_heat_panels_context_frame_is_the_replicates_crop(
    tab: FilterTab, document: ReplicateDocument, player: VideoPlayer
) -> None:
    """The grid says *where inside the replicate*, so the frame under it must
    be the replicate's crop, not the parent footage the graph never saw.

    Two ways this can silently regress: the ROI is in source pixels
    (1000x800 here) while the player frame may be a half-size proxy, so the
    crop must scale; and a selection change moves the ROI while the playhead
    stands still, so switching replicates must re-crop the held frame without
    waiting for the next frame_changed.
    """
    document.add_roi(ROI(x=200, y=100, width=300, height=200))
    document.select(0)
    player.frame_changed.emit(3, QImage(500, 400, QImage.Format.Format_RGB32))

    held = tab.heat.context_frame
    assert held is not None
    assert (held.width(), held.height()) == (150, 100), "the crop ignored the proxy scale"

    document.add_roi(ROI(x=0, y=0, width=400, height=400))
    document.select(1)
    held = tab.heat.context_frame
    assert held is not None
    assert (held.width(), held.height()) == (200, 200), "the selection change did not re-crop"
