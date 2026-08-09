"""One step under the canvas, and the four things holding it there.

The slot is where the trace lives, so which step is pinned decides which node
the tuning loop is watching — that is the claim the first case makes, and it is
the one a later phase would break by quietly re-pointing `watch` at the walk.
The rest follow from the slot being *one*: pinning evicts, the card of the step
that holds it says so instead of drawing the plot a second time, and a step whose
surface is somewhere else says which surface in words.

The chain is `crop -> downsample -> detect` and needs no footage: every claim
here is about what the window built from the document and the shelf, taken
before a frame could arrive. `crop` carries a `region`, whose editor is on the
canvas, so it is the step that says its surface went elsewhere; `downsample` has
no surface at all; `detect` is one value per frame and is the only one of the
three with a trace to draw.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceRef
from tests.gui import driving

_TOOLS = ("crop", "downsample", "detect")

#: Taller than any of these steps asks for, so the fit is the step's answer;
#: and short enough that the cap is what answers instead.
_ROOMY = 900
_CRAMPED = 60


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=f"n{i}", tool_id=tool, version="1.0.0")
                for i, tool in enumerate(_TOOLS)
            ),
            edges=(Edge(upstream="n0", downstream="n1"), Edge(upstream="n1", downstream="n2")),
        ),
    )
    path = tmp_path / "arena.sieve.yaml"
    project.save(path)
    return path


@pytest.fixture
def window(qapp, project_file: Path) -> Iterator[Any]:
    """A window with the chain open, closed on the way out for `app.closeEvent`'s reason."""
    del qapp
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(project_file.parent))
    # Shown *and* activated, because a `QShortcut`'s default context is
    # `Qt.WindowShortcut` and the map declines to match one whose window is not
    # the active one — offscreen, `show()` alone leaves `activeWindow()` at
    # `None` and the key reaches the widget it was addressed to instead.
    opened.show()
    opened.activateWindow()
    # Activation is delivered rather than set: the window is not the active one
    # until the event announcing it has been drained.
    driving.pump()
    opened.open_project(project_file)
    yield opened
    opened.close()


def test_pinned_slot_holds_the_detection_step_and_its_trace_by_default(window: Any) -> None:
    from PySide6.QtWidgets import QLabel

    from sieve.gui.pinned import PinnedStep

    # The walk is at the head of the chain and the pin is at the foot of it,
    # which is the whole point of the slot: what is under the canvas is not
    # what the control side is showing.
    assert window.current_node.node_id == "n0"
    assert window.pinned_node is not None
    assert window.pinned_node.node_id == "n2"

    pinned = window.viewing.pinned
    assert isinstance(pinned, PinnedStep)
    assert pinned.node.node_id == "n2"
    assert any(label.text() == "3. detect" for label in pinned.findChildren(QLabel))

    # One panel, borrowed by whichever step is pinned — the loop holds it for
    # the window's lifetime and a second one would be a graph nothing fills.
    assert pinned.surface is window.graph
    assert window.tuning.watching == "n2"


def test_pinned_slot_evicts_and_a_step_with_no_plot_states_its_surface_in_words(
    window: Any,
) -> None:
    from PySide6.QtWidgets import QLabel

    from sieve.gui.graph_panel import GraphPanel
    from sieve.gui.pinned import CANVAS_NOTE, NO_SURFACE_NOTE

    window.pin(0)

    assert window.pinned_node.node_id == "n0"
    pinned = window.viewing.pinned
    assert pinned.node.node_id == "n0"
    # `crop`'s box is drawn on the viewport, so the slot names that surface
    # rather than calling the step surfaceless.
    assert pinned.surface is None
    assert pinned.findChild(GraphPanel) is None
    assert any(label.text() == CANVAS_NOTE for label in pinned.findChildren(QLabel))
    # Nothing is watched, because nothing under the canvas is drawing a trace.
    assert window.tuning.watching is None

    window.pin(1)

    # One slot: the second pin is what unpinned the first.
    assert window.pinned_node.node_id == "n1"
    assert window.viewing.pinned.node.node_id == "n1"
    assert any(
        label.text() == NO_SURFACE_NOTE for label in window.viewing.pinned.findChildren(QLabel)
    )


def test_pinned_slot_re_fits_to_the_height_the_step_asks_for(window: Any) -> None:
    from sieve.gui.layout import PIN_MAX_SHARE

    viewing = window.viewing
    with_a_trace = viewing.pinned.natural_height()

    assert viewing.pin_height(_ROOMY) == with_a_trace
    # The canvas keeps the rest however tall the step is, which is what a slot
    # fitted to its step needs a ceiling for.
    assert viewing.pin_height(_CRAMPED) == _CRAMPED * PIN_MAX_SHARE // 100

    window.pin(1)

    # The refit is the point: a step whose surface is a line of text does not
    # hold the height the plot needed, which a fixed split by thirds would.
    without_one = viewing.pinned.natural_height()
    assert without_one < with_a_trace
    assert viewing.pin_height(_ROOMY) == without_one


def test_pinned_slot_card_says_where_the_surface_went_and_draws_no_plot(window: Any) -> None:
    from PySide6.QtWidgets import QLabel

    from sieve.gui.graph_panel import GraphPanel
    from sieve.gui.pinned import PINNED_ELSEWHERE_NOTE

    cards = window.control.pipeline_pane.cards

    # The stack draws no plots at all: the pinned step's surface is under the
    # canvas, and every other step's is wherever its own kind puts it.
    assert all(card.findChild(GraphPanel) is None for card in cards)
    assert any(label.text() == PINNED_ELSEWHERE_NOTE for label in cards[2].findChildren(QLabel))
    assert not any(label.text() == PINNED_ELSEWHERE_NOTE for label in cards[0].findChildren(QLabel))


def test_pinned_slot_p_pins_the_current_step_and_leaves_the_document_alone(window: Any) -> None:
    from PySide6.QtCore import Qt

    window.go_down()
    assert window.current_node.node_id == "n1"

    # Sent to the pane the user is looking at rather than to the window: a
    # window shortcut is matched on the way *to* a child, which is what
    # `findings/2026.08.09-a-key-sent-to-a-widget-inside-the-window-is-taken-by-the-walks-hotkey.md`
    # measured, and an event handed to the window itself is past that point.
    driving.key(window.control.pipeline_pane, Qt.Key.Key_P)

    assert window.pinned_node.node_id == "n1"
    assert window.viewing.pinned.node.node_id == "n1"
    # View state: the pin is not a parameter, so it leaves nothing to undo and
    # nothing for the next `sieve run` to read.
    session = window.session
    assert not session.can_undo()
    assert session.project.params_for("n1") == {}
