"""The crop fan: the regions a step cuts, drawn in the gap below its card.

Six claims. That the squares stand in the gap between the card and its reader is
what makes the row the branch rather than a legend; that they are left-aligned on
the trunk is what keeps every arrow into them a descent, which is what an
arrowhead means everywhere else in this stack. That every drop leaves one shared
run out of the card is the picture's whole statement — these all came from that
card — and that the continuing arrow leaves the square the user selected is what
says the stack below is drawn for *that* region and the others are the same
chain, unwalked. The click is the fifth: selecting a square moves the same
selection the window holds, so the picture and the walk agree.

The last goes through a window, because what a region *is* is not the widget's to
invent: the tree's regions are the project's replicates, each a per-replicate
override of the root region step's box (`core/pipeline_model.Replicate`), and a
fan drawn from anything else would be a second home for that value.

The geometry cases build the pane directly — what is under test is the drawing,
and `Fan` is the record the window hands over. Qt is imported inside the bodies,
for the reason `conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Replicate, SourceRef
from tests.gui import driving

#: Wide enough for a card's title and a row of three tiles, tall enough that
#: every card of these fixtures is laid out rather than scrolled past.
_PANE_SIZE = (360, 700)


def _pane(regions: Sequence[str], selected: int, on_select: Any = None) -> Any:
    """`crop -> downsample -> detect`, with the first card's branch fanned."""
    from sieve.gui.chain_stack import Fan, PipelinePane, Step

    steps = [
        Step(
            node=Node(node_id=f"n{position}", tool_id=tool, version="1.0.0"),
            knobs=None,
            removable=True,
            swappable=False,
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
            regions=tuple(regions),
            selected=selected,
            on_select=on_select if on_select is not None else (lambda _index: None),
        ),
    )
    pane.resize(*_PANE_SIZE)
    pane.show()
    driving.pump()
    return pane


@pytest.fixture
def fanned(qapp) -> Any:
    del qapp
    return _pane(("north", "south", "east"), selected=0)


def test_a_region_gets_a_square_in_the_crop_fans_gap_below_the_card(fanned: Any) -> None:
    column = fanned.column
    fan = fanned.fan

    assert len(fan.tile_rects()) == 3
    # In the gap, not above the card or below its reader: a row that stood
    # anywhere else would be a legend rather than the branch itself.
    assert fan.geometry().top() >= column.cards[0].geometry().bottom()
    assert fan.geometry().bottom() <= column.cards[1].geometry().top()


def test_the_crop_fans_squares_are_left_aligned_on_the_trunk(fanned: Any) -> None:
    from sieve.gui.chain_stack import TILE, TILE_GAP, lane_x

    column = fanned.column
    tiles = column.fan_tiles()
    trunk = lane_x(column.cards[0].geometry().left(), 0)

    # The first square sits on the lane the chain descends in, so the arrow into
    # it is vertical; the rest run out to its right at a fixed pitch. Centring
    # the row would put it wherever the count and the pane's width left it, and
    # only a diagonal could reach that from the trunk.
    assert tiles[0].center().x() == pytest.approx(trunk)
    assert [tile.center().x() - trunk for tile in tiles] == pytest.approx(
        [0.0, TILE + TILE_GAP, 2 * (TILE + TILE_GAP)]
    )
    assert [tile.width() for tile in tiles] == pytest.approx([TILE] * 3)


def test_every_crop_fan_arrow_leaves_the_one_card_that_made_them(fanned: Any) -> None:
    column = fanned.column
    edge = column.fanned_edge()
    tiles = column.fan_tiles()

    # One run across the gap, hung off the card's own bottom, and a drop off it
    # into each square: the shared segment is what says these all came from that
    # card, while every arrowhead stays a descent.
    assert edge.stem[0].y() == pytest.approx(column.cards[0].geometry().bottom() + 1)
    assert edge.stem[0].x() == pytest.approx(edge.stem[1].x())
    assert [drop[0].y() for drop in edge.drops] == pytest.approx([edge.stem[1].y()] * 3)
    for drop, tile in zip(edge.drops, tiles, strict=True):
        assert drop[0].x() == pytest.approx(drop[1].x()) == pytest.approx(tile.center().x())
        assert drop[1].y() == pytest.approx(tile.top())


def test_the_crop_fans_continuing_arrow_leaves_the_square_the_user_selected(
    qapp,
) -> None:
    del qapp
    for selected in (0, 2):
        pane = _pane(("north", "south", "east"), selected=selected)
        column = pane.column
        edge = column.fanned_edge()
        chosen = column.fan_tiles()[selected]

        assert edge.rejoin[0].x() == pytest.approx(chosen.center().x())
        assert edge.rejoin[0].y() == pytest.approx(chosen.bottom())
        # And back onto the trunk, so the lane the rest of the stack is drawn in
        # survives the branch.
        assert edge.rejoin[-1].x() == pytest.approx(edge.stem[0].x())
        assert edge.rejoin[-1].y() == pytest.approx(column.cards[1].geometry().top())


def test_clicking_a_crop_fan_square_selects_that_region(qapp) -> None:
    del qapp
    chosen: list[int] = []
    pane = _pane(("north", "south", "east"), selected=0, on_select=chosen.append)
    tile = pane.fan.tile_rects()[1]

    driving.press(pane.fan, tile.center().x(), tile.center().y())

    assert chosen == [1]


# ---- through the window ---------------------------------------------------

_TOOLS = ("crop", "downsample", "detect")


def _project(replicates: tuple[Replicate, ...]) -> Project:
    return Project(
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
        replicates=replicates,
    )


@pytest.fixture
def two_regions(tmp_path: Path) -> Path:
    path = tmp_path / "arena.sieve.yaml"
    _project((Replicate(name="north"), Replicate(name="south"))).save(path)
    return path


@pytest.fixture
def no_regions(tmp_path: Path) -> Path:
    path = tmp_path / "baseline.sieve.yaml"
    _project(()).save(path)
    return path


def _window(path: Path) -> Iterator[Any]:
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(path.parent))
    opened.open_project(path)
    yield opened
    opened.close()


@pytest.fixture
def window(qapp, two_regions: Path) -> Iterator[Any]:
    del qapp
    yield from _window(two_regions)


def test_the_crop_fan_draws_one_square_per_replicate_and_a_click_walks_onto_it(
    window: Any,
) -> None:
    fan = window.control.pipeline_pane.fan
    assert [tile.width() for tile in fan.tile_rects()] and len(fan.tile_rects()) == 2

    tile = fan.tile_rects()[1]
    driving.press(fan, tile.center().x(), tile.center().y())
    driving.pump()

    # The selection is the window's, like the walk's own: the pane is rebuilt
    # from it, so the picture and the walk say the same thing about which chain
    # is on screen.
    assert window.region == 1
    assert window.control.pipeline_pane.fan.selected == 1


def test_a_project_with_no_regions_gets_no_crop_fan(qapp, no_regions: Path) -> None:
    del qapp
    for opened in _window(no_regions):
        assert opened.control.pipeline_pane.fan is None
        assert opened.region == 0
