"""The chain's edges: down the stack, one lane each, behind whatever they pass.

Four claims, and the last is the one the picture is for. That an edge is
vertical and that it starts and ends where the cards do are read off the
geometry the painter is handed; that overlapping spans take separate lanes is
read off the assignment on its own, which is where the rule lives. Occlusion
cannot be read off either — it is a fact about paint order — so it is asserted
on rendered pixels: the line is there in the gap above the card it passes and
the card's own fill is there where it crosses.

A fan-out is what gives the fourth case a subject. Nothing here draws two edges
into one node and permits one node feeding two, so the graph where an edge has
a card to pass is the branching one, and it is a graph the tree already admits
(`gui/walk.py`).

The panes here are built directly rather than through a window: what is under
test is the drawing, and a `Step` is the record the window hands over. Qt is
imported inside the bodies, for the reason `conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.gui import driving

#: Wide enough that a card holds its title and three lanes, tall enough that
#: every card of these fixtures is laid out rather than scrolled past.
_PANE_SIZE = (360, 700)


def _pane(reads: Sequence[tuple[int, ...]]) -> Any:
    """A pipeline pane of `len(reads)` cards, each reading the positions named."""
    from sieve.core.pipeline_model import Node
    from sieve.gui.chain_stack import PipelinePane, Step

    steps = [
        Step(
            node=Node(node_id=f"n{position}", tool_id="downsample", version="1.0.0"),
            knobs=None,
            removable=True,
            swappable=False,
            reads=sources,
        )
        for position, sources in enumerate(reads)
    ]
    pane = PipelinePane(
        "arena",
        steps,
        current=0,
        pinned=None,
        pinned_note="",
        on_select=lambda _position: None,
        on_open=lambda _position: None,
        on_pin=lambda _position: None,
        on_remove=lambda _position: None,
        on_swap=lambda _position: None,
    )
    pane.resize(*_PANE_SIZE)
    pane.show()
    driving.pump()
    return pane


@pytest.fixture
def linear(qapp) -> Any:
    del qapp
    return _pane([(), (0,), (1,)])


@pytest.fixture
def branching(qapp) -> Any:
    """One card feeding the two below it, so the longer edge has a card to pass."""
    del qapp
    return _pane([(), (0,), (0,)])


def test_an_output_reaches_down_from_one_cards_bottom_to_the_next_cards_top(
    linear: Any,
) -> None:
    from sieve.gui.chain_stack import lane_x

    column = linear.column
    above, below = column.cards[0].geometry(), column.cards[1].geometry()
    start, end = column.edge_line(0, 1)

    assert start.y() == pytest.approx(above.bottom() + 1)
    assert end.y() == pytest.approx(below.top())
    # Vertical, and in the lane read off the card's own left edge: an edge that
    # changed x on the way down would leave a card as something the eye has no
    # reason to join to what went in.
    assert start.x() == pytest.approx(end.x())
    assert start.x() == pytest.approx(lane_x(above.left(), 0))


def test_an_output_that_reaches_down_a_longer_span_takes_a_lane_of_its_own() -> None:
    from sieve.gui.chain_stack import edge_lanes

    # Shortest span first, so the trunk stays with the steps that read the one
    # above them — which is most of a chain.
    assert edge_lanes([(0, 2), (0, 1)]) == {(0, 1): 0, (0, 2): 1}
    # Spans that do not overlap are not two lanes' worth: an edge ending where
    # the next begins shares the trunk with it.
    assert edge_lanes([(0, 1), (1, 2)]) == {(0, 1): 0, (1, 2): 0}


def test_an_arrowhead_reaches_down_onto_the_card_that_reads_it(linear: Any) -> None:
    from sieve.gui.chain_stack import ARROW_HEIGHT, arrowhead

    column = linear.column
    _start, end = column.edge_line(0, 1)
    head = arrowhead(end)

    assert [point.y() for point in head] == pytest.approx(
        [end.y() - ARROW_HEIGHT, end.y() - ARROW_HEIGHT, end.y()]
    )
    # The apex is the point that touches the card, and it is the lowest of the
    # three: an arrowhead in this stack always means a descent.
    assert head[2].x() == pytest.approx(end.x())


def test_an_output_reaches_down_behind_the_card_it_passes(branching: Any) -> None:
    from sieve.gui.chrome import PANEL

    column = branching.column
    passed = column.cards[1].geometry()
    _start, end = column.edge_line(0, 2)
    x = round(end.x())

    image = column.grab().toImage()
    gap = (column.cards[0].geometry().bottom() + passed.top()) // 2

    # Above the card it passes, the line is drawn and nothing else in the gap is.
    assert _painted(image, x, gap)
    assert not _painted(image, x + 60, gap)
    # Across it, the card's own fill: occlusion is the statement that the output
    # never left the chain, and routing around the card would say the opposite.
    assert image.pixelColor(x, passed.bottom() - 4).rgb() == PANEL.rgb()


def _painted(image: Any, x: int, y: int) -> bool:
    """Whether anything but the stack's background is at `(x, y)`, or beside it.

    The neighbouring columns are read too because a hairline at a half-integer x
    is antialiased across two of them, and which two is the painter's business.
    """
    from sieve.gui.chrome import STACK_BG

    return any(image.pixelColor(column, y).rgb() != STACK_BG.rgb() for column in (x - 1, x, x + 1))
