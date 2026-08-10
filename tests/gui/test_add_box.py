"""ADD STEP: a gap is a position, and the box fills it.

Four claims, and the first is the one the other three hang on. **The box never
writes on opening** — it is a picker, so esc costs nothing and exactly one
mutation is issued, when an offer is taken. That the offer is the *gap's* is the
second: it rewrites as the box moves, and it is empty at most gaps on today's
shelf, which is why the empty case is written first here rather than as an edge.
The third is the splice, checked as a document mutation rather than as a
redrawn stack — a chain drawn shorter or longer than the file holds would still
run what the user is not looking at. The fourth is the picture: the two edges
the box would be spliced onto are drawn dashed, and the solid edge it interrupts
is not drawn beside them.

The chain is `pick -> crop -> detect`, chosen so both offer cases are reachable
in one window: `crop` emits an `ArraySpec` stating neither field, so the gap
under it offers nothing
(`findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md`),
while `detect` pins both and the gap under it offers two tools. The gap under
the last step is a position here where it is not in the referent, because the
tree's output card is drawn and not modeled
(`adr/the-output-card-is-a-picture-of-the-write-list.md`) — there is no card
below the chain for a refusal to be about.

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

_TOOLS = ("pick", "crop", "detect")

#: What the gap under `detect` offers, in the order `offered_tools` scores them.
_OFFERED = ["detect", "motion_history"]


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "arena.sieve.yaml"
    Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=f"n{i}", tool_id=tool, version="1.0.0")
                for i, tool in enumerate(_TOOLS)
            ),
            edges=tuple(
                Edge(upstream=f"n{i}", downstream=f"n{i + 1}") for i in range(len(_TOOLS) - 1)
            ),
        ),
    ).save(path)
    return path


def _open(project_file: Path) -> Any:
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(project_file.parent))
    # Activated *after* the project is open, not before it as `test_pinned_slot`
    # does: a redraw orphans the panes it replaces, and draining their deferred
    # deletion takes the application's active window with it
    # (`findings/2026.08.09-a-key-sent-to-a-widget-inside-the-window-is-taken-by-the-walks-hotkey.md`,
    # amended). `open_project` redraws, so activating first leaves the window
    # inactive and every `QShortcut` on it unmatched.
    opened.show()
    opened.open_project(project_file)
    _activate(opened)
    return opened


def _activate(window: Any) -> None:
    """Make `window` the active one, which is what a `QShortcut` is matched against.

    Called again after every redraw a case drives, for the fixture's reason: the
    activation does not survive one.
    """
    from PySide6.QtWidgets import QApplication

    driving.pump()
    window.activateWindow()
    driving.pump()
    assert QApplication.activeWindow() is window


@pytest.fixture
def window(qapp, project_file: Path) -> Iterator[Any]:
    """A window with the chain open, closed on the way out for `app.closeEvent`'s reason."""
    del qapp
    opened = _open(project_file)
    yield opened
    opened.close()


def _box(window: Any) -> Any:
    return window.control.pipeline_pane.add_box


def _offered(window: Any) -> list[str]:
    return [button.text() for button in _box(window).offer_buttons]


def _newest(window: Any) -> str:
    """The node the last splice minted — appended, so it is the tuple's last."""
    return window.session.project.pipeline.nodes[-1].node_id


def _chain(window: Any) -> tuple[list[str], list[tuple[str, str]]]:
    pipeline = window.session.project.pipeline
    return (
        [node.tool_id for node in pipeline.nodes],
        [(edge.upstream, edge.downstream) for edge in pipeline.edges],
    )


def test_the_box_opens_in_the_gap_the_walk_is_on_and_writes_nothing(window: Any) -> None:
    assert _box(window) is None

    window.add_step()

    # In the gap under the walk, carrying the number the step would have — so
    # the box reads as the position it is asking about rather than as a panel
    # about one.
    box = _box(window)
    assert box is not None
    assert box.site == 0
    assert box.number == 2
    # Opening is a picker's, so there is nothing on the stack for esc to undo.
    assert not window.session.can_undo()


def test_an_empty_offer_still_opens_a_box_that_says_so(window: Any) -> None:
    # Most gaps on today's shelf are this one, so it is the case the box is
    # usually in — and it opens anyway, because the offer is a fact about the
    # gap and ↑/↓ are how the user reaches the gap that has one. A gesture that
    # refused here would leave them no way to find the gaps that offer.
    window.add_step()

    box = _box(window)
    assert box.offer == ()
    assert box.offer_buttons == ()
    assert box.offer_note == "nothing on the shelf declares it could stand here"
    # The box still says which gap it is in, because that is the half of the
    # question it can answer here.
    assert box.note == "after n0 · n1 would read it"

    window.take_offer()

    assert _chain(window) == (list(_TOOLS), [("n0", "n1"), ("n1", "n2")])
    assert not window.session.can_undo()


def test_the_box_moves_through_the_gaps_and_the_offer_rewrites_with_it(window: Any) -> None:
    window.add_step()
    assert _offered(window) == []

    # ↓ moves the box, not the walk: while a box is open it is the position the
    # keys are about, and the walk is standing behind it.
    window.go_down()
    assert _box(window).site == 1
    assert _offered(window) == []
    assert window.current_node.node_id == "n0"

    window.go_down()
    assert _box(window).site == 2
    assert _offered(window) == _OFFERED

    # The gap under the last step is a position, so ↓ stops at the foot of the
    # chain rather than one short of it.
    window.go_down()
    assert _box(window).site == 2

    window.go_up()
    assert _box(window).site == 1
    # The lit offer does not travel: the gap above holds a different list, and
    # an index carried into it would light whatever happened to be second.
    assert _box(window).lit == 0


def test_walking_the_offer_lights_another_and_leaves_the_document_alone(window: Any) -> None:
    window.add_step()
    window.go_down()
    window.go_down()
    assert _box(window).lit == 0

    # ←/→ walk the offer rather than the panes: an open box owns both pairs,
    # because it is a position the walk cannot stand on.
    window.go_forward()
    assert _box(window).lit == 1
    assert window.control.current_position() == "pipeline"

    # Wrapped rather than clamped, unlike the walk: the offer is a short ring of
    # names and neither end is somewhere the user is trying to stop.
    window.go_forward()
    assert _box(window).lit == 0
    window.go_back()
    assert _box(window).lit == 1

    assert not window.session.can_undo()


def test_taking_an_offer_splices_the_step_into_the_gap(window: Any) -> None:
    window.add_step()
    window.go_down()
    window.go_down()
    window.go_forward()

    window.take_offer()

    # One mutation, and it is the document's.
    minted = _newest(window)
    assert _chain(window) == (
        ["pick", "crop", "detect", "motion_history"],
        [("n0", "n1"), ("n1", "n2"), ("n2", minted)],
    )
    assert window.session.can_undo()
    assert _box(window) is None
    # The walk lands on what was just put there, for the reason a removal lands
    # on the step above: the next thing the user does is set it up.
    assert window.current_node.node_id == minted
    assert len(window.control.pipeline_pane.cards) == 4


def test_a_splice_above_a_reader_rewires_it_to_read_the_new_step(window: Any) -> None:
    window.add_step()
    window.go_down()
    window.go_down()
    window.take_offer()
    below = _newest(window)

    # Now into the gap above it, so there is a reader past the gap: what read
    # `detect` has to read the new step instead, which is the half of the splice
    # the foot of the chain cannot show.
    window.add_step()
    window.go_up()
    assert _box(window).site == 2
    window.take_offer()

    spliced = _newest(window)
    assert _chain(window)[1] == [
        ("n0", "n1"),
        ("n1", "n2"),
        (spliced, below),
        ("n2", spliced),
    ]


def test_esc_closes_the_box_having_written_nothing(window: Any) -> None:
    window.add_step()
    window.go_down()
    window.go_down()

    window.cancel_add()

    assert _box(window) is None
    assert _chain(window) == (list(_TOOLS), [("n0", "n1"), ("n1", "n2")])
    assert not window.session.can_undo()
    # The keys go back to the panes and the walk the moment the box does.
    window.go_forward()
    assert window.control.current_position() == "step"


def test_add_step_pressed_again_takes_the_box_back(window: Any) -> None:
    window.add_step()
    window.add_step()

    assert _box(window) is None
    assert not window.session.can_undo()


def _bindings(window: Any) -> dict[str, bool]:
    """Every key bound on the window, and whether its shortcut is live."""
    from PySide6.QtGui import QShortcut

    return {
        shortcut.key().toString(): shortcut.isEnabled()
        for shortcut in window.findChildren(QShortcut)
    }


def test_the_keys_the_box_owns_are_dead_until_it_is_open(window: Any) -> None:
    # Enter and esc are switched on with the box and off with it, and that is
    # why they are switched rather than simply bound: a window shortcut is
    # matched ahead of the widget holding focus, so a Return live at all times
    # would be swallowed before it reached the spin box it was typed into, which
    # is where a committed edit lands (`param_form.py`).
    assert _bindings(window) == {
        "Left": True,
        "Right": True,
        "Up": True,
        "Down": True,
        "P": True,
        "A": True,
        "Return": False,
        "Enter": False,
        "Esc": False,
    }

    window.add_step()
    assert _bindings(window)["Return"] is True
    assert _bindings(window)["Esc"] is True

    window.cancel_add()
    assert _bindings(window)["Return"] is False

    # And they go back off through the other exit too, which is the one that
    # writes: a box that had been filled would otherwise leave Return armed over
    # a chain with no box in it.
    window.add_step()
    window.go_down()
    window.go_down()
    window.take_offer()
    assert _bindings(window)["Return"] is False
    assert _chain(window)[0] == ["pick", "crop", "detect", "detect"]


def test_a_bound_key_reaches_the_box_it_opens(window: Any) -> None:
    from PySide6.QtCore import Qt

    # Sent to the pane rather than to the window, for `test_pinned_slot.py`'s
    # reason: a window shortcut is matched on the way *to* a child, and an event
    # handed to the window itself is past that point.
    driving.key(window.control.pipeline_pane, Qt.Key.Key_A)
    assert _box(window) is not None

    _activate(window)
    driving.key(window.control.pipeline_pane, Qt.Key.Key_Escape)

    assert _box(window) is None
    assert not window.session.can_undo()


def test_an_empty_chain_has_no_gap_for_a_box_to_stand_in(qapp, tmp_path: Path) -> None:
    # A gap is between two positions the chain has, and a project with no steps
    # has none. The first step of an empty project is a source, and offering
    # against a folder of picked files is not a question this predicate answers
    # yet (`core/tool_registry.offered_tools`).
    del qapp
    path = tmp_path / "empty.sieve.yaml"
    Project().save(path)
    window = _open(path)
    try:
        window.add_step()
        assert window.control.pipeline_pane.add_box is None
    finally:
        window.close()


def test_the_box_is_dashed_on_the_edges_it_would_be_spliced_onto(window: Any) -> None:
    window.add_step()
    window.go_down()
    pane = window.control.pipeline_pane
    pane.resize(320, 900)
    driving.pump()

    column, box = pane.column, pane.add_box
    # Out of the gap's step into the box, and out of the box into what read past
    # the gap: the picture of what taking an offer would write.
    assert column.provisional_edges() == ((1, column.box_slot), (column.box_slot, 2))
    # The edge those two interrupt is not drawn beside them — one chain on
    # screen, or the picture is claiming both.
    assert (1, 2) in column.edges
    assert (1, 2) not in column.painted_edges()

    # And the box stands in the gap it is asking about.
    assert box.geometry().top() >= pane.cards[1].geometry().bottom()
    assert box.geometry().bottom() <= pane.cards[2].geometry().top()
