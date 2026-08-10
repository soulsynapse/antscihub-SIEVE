"""⇄: the same box, standing where the card is, keeping the node it is.

Four claims and a picture. The first is that there is no second surface — the
box `test_add_box.py` drives is the one that opens here, with one fewer axis
rather than a different keyboard: it stands at a position that exists, so ↑/↓
have nothing to move, ←/→ still walk the offer, and esc restores the card
having written nothing.

The second is the one that makes a swap a third mutation rather than a removal
and an addition dressed as one: **the node keeps its identity.** `node_id` names
the artifact on disk, holds the checkpoints and the sinks, and is what `bench/`
addresses, so the remove-then-add spelling would break every one of those with
nothing going red. What does not survive is the parameters, and that is right
rather than a shortfall — they were the departed tool's.

The third is the empty offer, which is sharper here than it is for add: a box
that opened at a position offering nothing would take the card away and leave
esc as the only exit, where an empty *gap* is merely useless. So the ⇄ is dead
there, and the method behind it refuses for the same reason.

The chain is `pick -> crop -> detect -> motion_history`, and the position that
offers nothing is now the root alone: a position's offer is computed from the
stream it resolved to rather than from its upstream's declaration, so a `crop`
that preserves uint8 frames offers everything that takes them
(`todo/the-stream-a-position-produces-is-resolved-not-declared.md`). The root
has no upstream to resolve from and its own offer is the source question, which
`todo/the-source-is-a-card-in-the-walk.md` carries.

The picture is last and it is built without a window, the way `test_crop_fan.py`
builds one: what is under test is the drawing. Two boxes over a fanned card,
because the fan is where a picture can say two things at once — the add box in
the gap the fan hangs in, which is the branch `fanned_edge(dst)` exists for and
which nothing had entered, and the anchored box over the fanned card itself,
where the squares are not drawn at all.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Sink, SourceRef
from tests.gui import driving

_TOOLS = ("pick", "crop", "detect", "motion_history")

#: What the position under `detect` offers, in the order `offered_tools` scores
#: them — so the swap over `motion_history` opens lit on the second. The two
#: that pin `detect`'s float32 gray exactly lead, then the accepts that tolerate
#: dtypes it will not see, then the two that state no field at all. `downsample`
#: and `rescale` are absent on the *other* leg: they aggregate, and a mean of
#: frame-valued elements has no noun.
_OFFERED = [
    "detect",
    "motion_history",
    "temporal_baseline",
    "background_ema",
    "block_signal",
    "normalize",
    "crop",
    "span",
]

#: A value of the departed tool's, set so the swap has something to drop.
_TAU = 2.5


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "arena.sieve.yaml"
    Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(
            nodes=tuple(
                Node(
                    node_id=f"n{i}",
                    tool_id=tool,
                    version="1.0.0",
                    params={"tau_seconds": _TAU} if tool == "motion_history" else {},
                )
                for i, tool in enumerate(_TOOLS)
            ),
            edges=tuple(
                Edge(upstream=f"n{i}", downstream=f"n{i + 1}") for i in range(len(_TOOLS) - 1)
            ),
        ),
        # Both kinds of reference to the node that is about to be swapped: a
        # result kept along the way and a result written out. Neither may move.
        checkpoints=("n3",),
        outputs=(Sink(sink_id="s0", node_id="n3", format="csv", path="tracks"),),
    ).save(path)
    return path


def _open(project_file: Path) -> Any:
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(project_file.parent))
    # Shown, opened, then activated, in that order and for `test_add_box.py`'s
    # reason: `open_project` redraws, and a redraw does not carry the activation.
    opened.show()
    opened.open_project(project_file)
    driving.pump()
    opened.activateWindow()
    driving.pump()
    return opened


@pytest.fixture
def window(qapp, project_file: Path) -> Iterator[Any]:
    del qapp
    opened = _open(project_file)
    yield opened
    opened.close()


def _box(window: Any) -> Any:
    return window.control.pipeline_pane.add_box


def _swap_button(card: Any) -> Any:
    """The ⇄, which is the third of the card's four head-row buttons."""
    from PySide6.QtWidgets import QToolButton

    return card.findChildren(QToolButton)[2]


def _offered(window: Any) -> list[str]:
    return [button.text() for button in _box(window).offer_buttons]


def _chain(window: Any) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Every node as (id, tool), and every edge — the two halves identity is about."""
    pipeline = window.session.project.pipeline
    return (
        [(node.node_id, node.tool_id) for node in pipeline.nodes],
        [(edge.upstream, edge.downstream) for edge in pipeline.edges],
    )


_UNTOUCHED = (
    [("n0", "pick"), ("n1", "crop"), ("n2", "detect"), ("n3", "motion_history")],
    [("n0", "n1"), ("n1", "n2"), ("n2", "n3")],
)


def test_the_swap_box_stands_where_the_card_is_lit_on_the_tool_already_there(
    window: Any,
) -> None:
    assert _box(window) is None

    _swap_button(window.control.pipeline_pane.cards[3]).click()

    box = _box(window)
    assert box is not None
    assert box.anchored
    assert box.site == 3
    # The number the step already carries, not the one after it: nothing is
    # being inserted, so nothing below is renumbered.
    assert box.number == 4
    assert _offered(window) == _OFFERED
    # Lit on what is standing there — the entry a menu would have carried
    # checked, which is also the offer that says "and it could stay".
    assert box.lit == 1
    # Opening is a picker's here as it is in a gap.
    assert not window.session.can_undo()
    assert _chain(window) == _UNTOUCHED


def test_the_anchored_box_takes_the_cards_place_in_the_picture(window: Any) -> None:
    window.swap_step(3)
    pane = window.control.pipeline_pane
    pane.resize(320, 900)
    driving.pump()

    column, box = pane.column, pane.add_box
    # It *is* that position for the drawing's purposes, so the edge into the
    # position and the write out of it land on the box rather than beside it.
    assert column.cards[3] is box
    assert pane.cards[3].isHidden()
    # And nothing is dashed: a swap rewires no edge, so the chain around the box
    # is the chain the document holds.
    assert column.provisional_edges() == ()
    assert column.painted_edges() == column.edges
    assert box.geometry().top() >= pane.cards[2].geometry().bottom()


def test_the_anchored_box_has_no_up_and_down_and_still_walks_its_offer(window: Any) -> None:
    window.swap_step(3)

    # ↑/↓ have nothing to move: a box that walked into the gaps would flip
    # between replacing and inserting as it travelled.
    window.go_down()
    assert _box(window).site == 3
    window.go_up()
    assert _box(window).site == 3
    # The walk has not moved either, and it never did: the ⇄ acts on the position
    # it is drawn at, and selecting on the way past would make the one verb on
    # the card that mutates the document also able to change the selection.
    assert window.current_node.node_id == "n0"

    # ←/→ are the axis it does have, wrapped as they are in a gap.
    window.go_forward()
    assert _box(window).lit == 2
    window.go_back()
    window.go_back()
    assert _box(window).lit == 0
    window.go_back()
    assert _box(window).lit == len(_OFFERED) - 1
    assert window.control.current_position() == "pipeline"
    assert not window.session.can_undo()


def test_taking_an_offer_keeps_the_node_it_replaces(window: Any) -> None:
    window.swap_step(3)
    window.go_back()
    assert _offered(window)[0] == "detect"

    window.take_offer()

    # Same name, different tool, same edges — and the name is the whole of what
    # the checkpoint, the sink and the artifact on disk are addressed by.
    project = window.session.project
    assert _chain(window) == (
        [("n0", "pick"), ("n1", "crop"), ("n2", "detect"), ("n3", "detect")],
        [("n0", "n1"), ("n1", "n2"), ("n2", "n3")],
    )
    assert project.checkpoints == ("n3",)
    assert [(sink.sink_id, sink.node_id) for sink in project.outputs] == [("s0", "n3")]
    # The parameters do not survive: they were the departed tool's, and a value
    # left in a field the arriving tool spells the same way would be a setting
    # the user never made for it.
    assert project.pipeline.node("n3").params == {}
    # One mutation, on the ordinary undo stack.
    assert window.session.can_undo()
    assert _box(window) is None
    # The walk stays where it was standing, because the position did.
    assert window.current_node.node_id == "n3"
    assert len(window.control.pipeline_pane.cards) == 4


def test_esc_restores_the_step_the_box_was_standing_over(window: Any) -> None:
    window.swap_step(3)

    window.cancel_add()

    pane = window.control.pipeline_pane
    assert pane.add_box is None
    assert not pane.cards[3].isHidden()
    assert _chain(window) == _UNTOUCHED
    assert not window.session.can_undo()
    # The keys go back to the panes and the walk the moment the box does.
    window.go_forward()
    assert window.control.current_position() == "step"


def test_a_position_with_nothing_to_offer_has_a_dead_swap_and_opens_no_box(
    window: Any,
) -> None:
    # The root alone, and it is the resolution that leaves it there rather than
    # the shelf: every position below it resolved to uint8 frames and offers
    # what takes them, while the root has no upstream for the offer to be
    # computed from. Offering against a folder of picked files is a question
    # this predicate does not answer, so the source is unswappable here rather
    # than merely unoffered-for.
    cards = window.control.pipeline_pane.cards
    assert [_swap_button(card).isEnabled() for card in cards] == [False, True, True, True]
    assert _swap_button(cards[0]).toolTip() == "Nothing on the shelf declares it could stand here"

    # And the method refuses too, because a caller reaching it directly is the
    # case where the button was not the gesture.
    window.swap_step(0)

    assert _box(window) is None
    assert _chain(window) == _UNTOUCHED


# ---- the picture over a fanned card ---------------------------------------
#
# Built without a window: what is under test is where the lines land.

_PANE_SIZE = (360, 700)


def _fanned_pane(adding_site: int, anchored: bool) -> Any:
    """`crop -> downsample -> detect` with three regions, and a box at `adding_site`."""
    from sieve.gui.chain_stack import Adding, Fan, PipelinePane, Step

    steps = [
        Step(
            node=Node(node_id=f"n{position}", tool_id=tool, version="1.0.0"),
            knobs=None,
            removable=True,
            swappable=True,
            reads=() if position == 0 else (position - 1,),
        )
        for position, tool in enumerate(("crop", "downsample", "detect"))
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
        fan=Fan(
            position=0,
            regions=("north", "south", "east"),
            selected=0,
            on_select=lambda _index: None,
        ),
        adding=Adding(
            site=adding_site,
            offer=("detect",),
            lit=0,
            on_take=lambda _position: None,
            anchored=anchored,
        ),
    )
    pane.resize(*_PANE_SIZE)
    pane.show()
    driving.pump()
    return pane


def test_the_fans_way_out_lands_on_a_box_standing_in_the_gap_it_hangs_in(qapp) -> None:
    del qapp
    pane = _fanned_pane(adding_site=0, anchored=False)
    try:
        column, box = pane.column, pane.add_box
        # The branch is the card's own and is real; where it continues to is
        # exactly what the box is standing in the way of, so the way out ends on
        # the box rather than on the card that used to read it.
        assert column.provisional_edges() == ((0, column.box_slot), (column.box_slot, 1))
        assert column.fanned_edge(column.box_slot).rejoin[-1].y() == box.geometry().top()
        # The drops are still the fan's three regions: what the box interrupts is
        # the continuation, not the branch.
        assert len(column.fanned_edge(column.box_slot).drops) == 3
        # And the edge the pair replaces is not drawn beside them.
        assert (0, 1) in column.edges
        assert (0, 1) not in column.painted_edges()
    finally:
        pane.close()


def test_a_box_standing_over_the_fanned_card_draws_no_fan(qapp) -> None:
    del qapp
    pane = _fanned_pane(adding_site=0, anchored=True)
    try:
        # The squares are that step's regions — what its parameters cut — so
        # drawing them under a box asking what should stand there instead would
        # be the picture claiming both at once.
        assert pane.fan is None
        assert pane.column.fan is None
        assert pane.column.cards[0] is pane.add_box
        assert pane.column.provisional_edges() == ()
    finally:
        pane.close()
