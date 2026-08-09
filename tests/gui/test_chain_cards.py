"""The pipeline position is a stack of cards, and the cards are the walk's.

Four claims about the stack, and each is a thing a later phase could break
without noticing.
That there is a card per step under a project card is the shape; that clicking
one moves the same selection Up and Down move, and that the arrow moves it *and*
slides, are the two verbs 09.1 owns; that the knobs on a card are the generated
form is what keeps the stack from growing a table keyed by tool.

The chrome is asserted as the two selectors rather than as pixels. What the
sheets have to get right is which widgets they reach — `.QWidget` and not
`QWidget`, so the scrollbars stay the platform's — and a rendered background is
the same colour under either spelling for every widget except the scrollbar,
which offscreen Qt may not draw at all.

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

#: A chain of three real tools, so every card has a spec to generate knobs from.
#: `crop` is first because its parameter is a composite the generator restates
#: rather than a spin box, which is what makes the third case's assertion about
#: `downsample`'s `factor` a statement about the generator and not about a label.
_TOOLS = ("crop", "downsample", "detect")


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
    """A window standing at the pipeline position of the chain above.

    Closed on the way out rather than left to the interpreter: the window opens
    a decode thread over a clip that does not exist, and a `QThread` still alive
    when its `QObject` is finalised takes the process down (`app.closeEvent`).
    """
    del qapp
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(project_file.parent))
    opened.open_project(project_file)
    yield opened
    opened.close()


def _arrow(card: Any) -> Any:
    from PySide6.QtWidgets import QToolButton

    return card.findChild(QToolButton)


def test_chain_cards_are_one_per_step_under_a_project_card(window: Any) -> None:
    from sieve.gui.chain_stack import ChainCard, PipelinePane

    pane = window.control.pipeline_pane

    assert isinstance(pane, PipelinePane)
    assert len(pane.cards) == len(_TOOLS)
    assert all(isinstance(card, ChainCard) for card in pane.cards)
    # The card that is the walk's, and only it, wears the accent edge.
    assert [card.selected for card in pane.cards] == [True, False, False]

    from PySide6.QtWidgets import QLabel

    assert [card.findChild(QLabel).text() for card in pane.cards] == [
        f"{position}. {tool}" for position, tool in enumerate(_TOOLS, start=1)
    ]
    # The project the stack belongs to, named above the scroll and not in it.
    assert pane.project_card.findChild(QLabel).text() == "project — arena"
    assert pane.project_card not in pane.cards


def test_chain_cards_click_moves_the_selection_up_and_down_move(window: Any) -> None:
    driving.click(window.control.pipeline_pane.cards[2], 4.0, 4.0)

    assert window.current_node.node_id == "n2"
    # The same selection, not a second one: the rail and the step position are
    # drawn from the walk, and a click that moved only the card's own paint would
    # leave the three disagreeing.
    assert window.control.step_pane.node.node_id == "n2"
    assert [card.selected for card in window.control.pipeline_pane.cards] == [
        False,
        False,
        True,
    ]
    # Selecting is not entering: the pointer's Up/Down, and nothing else.
    assert window.control.current_position() == "pipeline"


def test_chain_cards_arrow_selects_the_step_and_slides_to_its_form(window: Any) -> None:
    assert window.current_node.node_id == "n0"

    _arrow(window.control.pipeline_pane.cards[1]).click()

    assert window.control.current_position() == "step"
    assert window.current_node.node_id == "n1"
    # Both halves: the arrow on a card the walk was not standing on has to carry
    # the selection with it, or it opens the form of the step it left behind.
    assert window.control.step_pane.node.node_id == "n1"


def test_chain_cards_carry_the_generated_form_and_write_through_it(window: Any) -> None:
    from sieve.gui.param_form import ParamForm

    card = window.control.pipeline_pane.cards[1]

    form = card.findChild(ParamForm)
    assert form is not None
    factor = form.widget("factor")
    factor.setValue(4)

    # The knob on the card is the document's own writer, through the ordinary
    # command path — not a display of a value some other surface owns.
    assert window.session.project.params_for("n1")["factor"] == 4


def test_chain_cards_wear_a_sheet_that_leaves_the_scrollbars_alone(qapp) -> None:
    from sieve.gui.chrome import stack_stylesheet, window_stylesheet

    stack = stack_stylesheet()
    # Instances of exactly QWidget: a bare `QWidget` selector reaches QScrollBar,
    # and any rule on a scrollbar makes Qt draw the whole control from the sheet.
    assert ".QWidget {" in stack
    assert "QScrollBar" not in stack

    # The window's sheet is anchored to the window and its seams, so it cannot
    # reach down into the stack and fight the sheet above over every card.
    assert "QMainWindow" in window_stylesheet()
    assert "QWidget" not in window_stylesheet()
