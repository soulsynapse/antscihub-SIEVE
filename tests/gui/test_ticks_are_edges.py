"""The output card at the foot of the chain, and the ticks that become its edges.

Four claims, and the first two are the item's title read literally. That what the
document says the run keeps is derived from `Project.checkpoints` and
`Project.outputs` together is the derivation — a picture that read only one of
the two would go quiet about a sink a handoff wrote. That each of those becomes
an edge into the card, named by product at the arrowhead, is the picture; the
name is asserted on rendered pixels as well as on the geometry, because a label
that is placed and never painted is exactly as unheld as one that is neither.

The third claim is the arrowhead rule's other leg: a port is named only where the
destination has more than one input (MOCKUP-MAP row "Arrow logic"), so a single
tick leaves the arrowhead bare and the gap beside it empty.

The fourth is what makes the card a step rather than a legend. A tick on the save
screen redraws the picture — nothing here holds a second copy of the write list —
and the card's arrow opens the form the write list and Run sit on, which is the
whole of the save screen dissolving into it
(`adr/the-output-card-is-a-picture-of-the-write-list.md`).

No output node enters the contract for any of this: the card is drawn over the
document's own two lists, and the graph the window is holding is the graph the
file holds.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Sink
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
)
from tests.gui import driving

#: Wide enough for a card, three lanes and a product name beside the arrowhead;
#: tall enough that every card of these fixtures is laid out rather than
#: scrolled past.
_PANE_SIZE = (420, 700)

_TOOLS = ("pick", "crop", "downsample", "detect")

#: How far right of a name's origin the pixels are read. Short of the next lane,
#: and short of the shoulder of *that* lane's arrowhead — either would otherwise
#: be read as ink from this name, and the arrowhead is the wider of the two.
_NAME_WINDOW = 14


class Product(StrEnum):
    POWER = "power"
    PHASE = "phase"


class TwoProductParams(ParamsBase):
    """A tool whose enum picks which of two measurements leaves the node."""

    signal: Product = Product.POWER


class OneProductParams(ParamsBase):
    """A tool that computes one thing, so its edge has nothing to choose."""

    count: int = 4


def _specs() -> dict[str, ToolSpec]:
    one = ToolSpec(
        tool_id="one_product",
        version="1.0.0",
        summary="A tool with a single product.",
        params_model=OneProductParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("frames"),),
        element=ElementRelation.PRESERVED,
        param_stereotypes={"count": ParamStereotype.SCALAR_RANGE},
    )
    two = ToolSpec(
        tool_id="two_products",
        version="1.0.0",
        summary="A tool whose parameter picks the product.",
        params_model=TwoProductParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission(Product.POWER, "signal"), Emission(Product.PHASE, "signal")),
        element=ElementRelation.PRESERVED,
        param_value_labels={"signal": {Product.POWER: "Power", Product.PHASE: "Phase"}},
        param_stereotypes={"signal": ParamStereotype.ENUM},
    )
    return {"n0": one, "n1": two}


def _project(**fields: Any) -> Project:
    """A two-node chain over footage that is deliberately not there."""
    return Project(
        pipeline=Pipeline(
            nodes=(
                Node(node_id="n0", tool_id="one_product", version="1.0.0"),
                Node(node_id="n1", tool_id="two_products", version="1.0.0"),
            ),
            edges=(Edge(upstream="n0", downstream="n1"),),
        ),
        **fields,
    )


def _pane(reads: Sequence[tuple[int, ...]], writes: Sequence[tuple[int, str]]) -> Any:
    """A pane of `len(reads)` cards over an output card the writes reach into."""
    from sieve.gui.chain_stack import Outputs, PipelinePane, Step, Write

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
        outputs=Outputs(
            writes=tuple(Write(position, product) for position, product in writes),
            on_open=lambda: None,
        ),
    )
    pane.resize(*_PANE_SIZE)
    pane.show()
    driving.pump()
    return pane


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    """`pick -> crop -> downsample -> detect`, with two of the four kept."""
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
        checkpoints=("n2", "n3"),
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


def test_what_the_run_keeps_is_read_off_both_of_the_documents_lists() -> None:
    from sieve.gui.save_screen import kept_products

    project = _project(checkpoints=("n1",), outputs=(Sink(node_id="n0", format="csv", path="out"),))

    # Walk order, so the picture's edges arrive in the order the chain does, and
    # the product is the one this node's own parameters select — `checkpoints`
    # records a node and not a product.
    assert kept_products(project, _specs()) == (("n0", "frames"), ("n1", "Power"))

    # A parameter that moves the selected product moves the name the tick stands
    # for: the label is derived, not stored beside the tick.
    moved = project.with_param_default("n1", {"signal": Product.PHASE})

    assert kept_products(moved, _specs()) == (("n0", "frames"), ("n1", "Phase"))


def test_a_kept_product_is_an_edge_into_the_card_at_the_foot(qapp) -> None:
    del qapp
    from sieve.gui.chain_stack import lane_x

    pane = _pane([(), (0,), (1,)], [(1, "cropped"), (2, "downsampled")])
    column = pane.column
    foot = pane.output_card.geometry()

    # One edge per kept product, into the card below the last step — and the
    # chain's own three edges are still the three the document holds.
    assert set(column.edges) == {(0, 1), (1, 2), (1, 3), (2, 3)}

    start, end = column.edge_line(2, 3)
    assert end.y() == pytest.approx(foot.top())
    assert start.x() == pytest.approx(end.x())
    # The two writes overlap in span, so they are two lanes rather than one line
    # the eye would have to unpick.
    assert column.lane_of(1, 3) != column.lane_of(2, 3)
    assert start.x() == pytest.approx(lane_x(pane.cards[2].geometry().left(), column.lane_of(2, 3)))


def test_the_edges_into_the_card_are_named_by_product_at_the_arrowhead(qapp) -> None:
    del qapp
    from sieve.gui.chain_stack import port_label_origin

    pane = _pane([(), (0,), (1,)], [(1, "cropped"), (2, "downsampled")])
    column = pane.column

    assert column.port_labels() == {(1, 3): "cropped", (2, 3): "downsampled"}

    from sieve.gui.chain_stack import ARROW_WIDTH

    _start, end = column.edge_line(2, 3)
    origin = port_label_origin(end)
    image = column.grab().toImage()

    # Painted, not merely placed: a name the picture has a position for and never
    # draws leaves the arrowhead exactly as bare as no name at all.
    assert _ink(image, origin.x(), origin.x() + _NAME_WINDOW, origin.y())
    # And beside the head rather than over it: a shoulder's width past the
    # shoulder is still clear, which is what makes the name readable at the one
    # arrowhead in the stack that has a neighbour.
    assert not _ink(image, end.x() + ARROW_WIDTH + 1, end.x() + 2 * ARROW_WIDTH, origin.y())


def test_a_single_input_leaves_its_arrowhead_bare(qapp) -> None:
    """The arrowhead rule's other leg: a name only where there is a choice to name.

    One tick means the card has one input, and a product written beside it would
    be a label on a line that could not have come from anywhere else.
    """
    del qapp
    from sieve.gui.chain_stack import port_label_origin

    pane = _pane([(), (0,), (1,)], [(2, "downsampled")])
    column = pane.column

    assert column.port_labels() == {}

    _start, end = column.edge_line(2, 3)
    origin = port_label_origin(end)
    assert not _ink(column.grab().toImage(), origin.x(), origin.x() + _NAME_WINDOW, origin.y())


def test_the_cards_two_names_do_not_collide(qapp) -> None:
    """The case the whole clause exists for: naming happens only where there are two.

    Both edges land on the card's top edge, so a rule that gave every name the
    same baseline paints the shorter of the two through the middle of the longer
    — the arrowheads are one lane apart and no product name in the tree is that
    narrow. Read as boxes rather than as a pixel: two names overlapping by a
    stroke are unreadable in the same way as two that coincide, and what the
    pixels are asked is only whether both were drawn at all.
    """
    del qapp

    pane = _pane([(), (0,), (1,)], [(1, "cropped"), (2, "downsampled")])
    column = pane.column
    named = sorted(column.port_labels())

    assert len(named) == 2

    boxes = [column.label_rect(*edge) for edge in named]

    # Each box is its name's own run of ink. The clause exists at all because a
    # product name is wider than the lane pitch the two arrowheads are separated
    # by, so a box narrower than that would clear its neighbour by arithmetic
    # that has nothing to do with what is drawn.
    from sieve.gui.chain_stack import EDGE_LANE

    assert all(box.width() > EDGE_LANE for box in boxes)

    assert not boxes[0].intersects(boxes[1])

    # Both still inside the gap: the edges are painted before the cards are, so a
    # name lifted past the card above is erased by it — the same collision as the
    # first, against the one rectangle in the picture that is not a name.
    assert all(box.top() > column.cards[-2].geometry().bottom() for box in boxes)

    # And painted where the geometry says: a name the picture has a box for and
    # never draws leaves the arrowhead as bare as no name at all.
    image = column.grab().toImage()
    for box in boxes:
        assert _ink(image, box.left(), box.left() + _NAME_WINDOW, box.bottom())


def test_a_tick_on_the_form_redraws_the_picture_and_moves_no_edge_of_the_graph(
    window: Any,
) -> None:
    """The card's inputs are derived from the writes, so they cannot disagree.

    Driven through the save screen's own checkbox rather than through the
    document, because what the item claims is that *ticking* is what draws the
    edge — a test that wrote `checkpoints` directly would pass against a picture
    nothing refreshes.
    """
    pipeline = window.session.project.pipeline
    foot = len(window.control.pipeline_pane.cards)

    assert set(window.control.pipeline_pane.column.edges) >= {(2, foot), (3, foot)}

    screen = window.control.save_pane
    downsampled = next(row for row in screen.rows if row.node_id == "n2")
    screen.checkbox(downsampled).click()

    assert set(window.control.pipeline_pane.column.edges) & {(2, foot), (3, foot)} == {(3, foot)}
    # No cache key moved: the card is a picture of what is kept, and keeping less
    # is not a shorter chain.
    assert window.session.project.pipeline == pipeline


def test_run_sits_on_the_output_cards_own_form(window: Any) -> None:
    from PySide6.QtWidgets import QPushButton, QToolButton

    arrow = window.control.pipeline_pane.output_card.findChildren(QToolButton)[0]

    arrow.click()

    assert window.control.current_position() == "save"
    assert isinstance(window.control.save_pane.run_button, QPushButton)


def _ink(image: Any, left: float, right: float, baseline: float) -> bool:
    """Whether anything is drawn in a band of the line a name is written on.

    A band rather than a pixel: glyph coverage at this size is sparse and which
    columns of it are inked is the font's business, not the painter's. It stops
    short of the next lane — `_NAME_WINDOW` — because a wider look would find the
    neighbouring edge's arrowhead and call it a name.
    """
    from sieve.gui.chrome import STACK_BG

    return any(
        image.pixelColor(x, y).rgb() != STACK_BG.rgb()
        for x in range(round(left), round(right) + 1)
        for y in range(round(baseline) - 11, round(baseline) + 1)
    )
