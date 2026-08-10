"""The card's ✕: the chain reads past the step it drops.

Three claims, and the first is what makes the other two worth anything. That the
removal is a *document* mutation is what stops the stack becoming a second
answer to what the project computes — a chain drawn shorter than the file holds
would still run the dropped step. That the walk and the pin land on the step
above is the part a rebuild gets wrong in the quiet direction: both are indices
into a list that renumbered under them. And the source's ✕ is offered disabled
rather than left off, so the buttons keep their positions down the stack and the
refusal is a sentence rather than an absence.

The chain is `pick -> crop -> downsample -> detect`, because a source tool is
what makes the third claim's subject exist: `pick` declares a `source`, and that
declaration — not the tool id — is what the disabled button is read off.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from tests.gui import driving

_TOOLS = ("pick", "crop", "downsample", "detect")


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    project = Project(
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=f"n{i}", tool_id=tool, version="1.0.0")
                for i, tool in enumerate(_TOOLS)
            ),
            edges=tuple(
                Edge(upstream=f"n{i}", downstream=f"n{i + 1}") for i in range(len(_TOOLS) - 1)
            ),
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
    opened.open_project(project_file)
    yield opened
    opened.close()


def _remove(card: Any) -> Any:
    """The ✕, which is the last of the card's four head-row buttons."""
    from PySide6.QtWidgets import QToolButton

    return card.findChildren(QToolButton)[3]


def _chain(window: Any) -> tuple[list[str], set[tuple[str, str]]]:
    pipeline = window.session.project.pipeline
    return (
        [node.node_id for node in pipeline.nodes],
        {(edge.upstream, edge.downstream) for edge in pipeline.edges},
    )


def test_the_document_closes_over_the_dropped_step_and_not_only_the_screen(
    window: Any,
) -> None:
    _remove(window.control.pipeline_pane.cards[2]).click()

    # What read `downsample` now reads what `downsample` read, rather than the
    # tail of the chain becoming a second root reading the footage.
    assert _chain(window) == (["n0", "n1", "n3"], {("n0", "n1"), ("n1", "n3")})
    # Through the ordinary command path, so it is on the undo stack like any
    # other edit and the next `sieve run` runs the chain the user is looking at.
    assert window.session.can_undo()
    assert len(window.control.pipeline_pane.cards) == 3


def test_the_walk_and_the_pin_land_on_the_step_above_the_gap(window: Any) -> None:
    window.pin(2)
    driving.click(window.control.pipeline_pane.cards[2], 4.0, 4.0)
    assert window.current_node.node_id == "n2"
    assert window.pinned_node.node_id == "n2"

    _remove(window.control.pipeline_pane.cards[2]).click()

    # Above, and not whatever slid into the gap: `crop` is what the dropped step
    # read, so it is the nearest surviving place the user was standing.
    assert window.current_node.node_id == "n1"
    assert window.pinned_node.node_id == "n1"
    assert window.viewing.pinned.node.node_id == "n1"

    # A position below the gap keeps the node it was already on, which in a
    # stack that renumbered under it is one card higher than it was.
    driving.click(window.control.pipeline_pane.cards[2], 4.0, 4.0)
    assert window.current_node.node_id == "n3"

    _remove(window.control.pipeline_pane.cards[1]).click()

    assert window.current_node.node_id == "n3"
    assert [card.selected for card in window.control.pipeline_pane.cards] == [False, True]


def test_the_source_step_offers_a_disabled_remove_and_the_chain_keeps_it(
    window: Any,
) -> None:
    cards = window.control.pipeline_pane.cards

    # Offered, and in the same place on every card: a chain with nothing to read
    # is not a shorter chain, and the tooltip is where that is said instead.
    assert [_remove(card).isEnabled() for card in cards] == [False, True, True, True]
    assert _remove(cards[0]).toolTip() == "The chain has to read something"

    window.remove_step(0)

    # The guard is the method's as well as the button's: a caller reaching past
    # the disabled button gets the same refusal and the document does not move.
    assert _chain(window) == (
        ["n0", "n1", "n2", "n3"],
        {("n0", "n1"), ("n1", "n2"), ("n2", "n3")},
    )
    assert not window.session.can_undo()
