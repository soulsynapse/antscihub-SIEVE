"""What a redraw is allowed to cost, and what it must carry across.

Both stacks are rebuilt whole on every move — the selection is drawn into the
cards rather than pushed onto them — so a redraw is the unit this file is about.
One decision seen from four sides: a rebuild re-reads nothing that has not
moved, it lands where the pane it replaced was, it brings the selection it just
moved back into view, and where the clamp moved nothing it does not happen. The
last case is the source resolution rather than either stack, because a graph
edit redoing a filesystem walk is the same thing again in the one place it can
block rather than merely cost.

The library here is forty projects because that is the size at which the
failures are visible at all: a shorter shelf fits in the viewport, so nothing
scrolls off it, and re-parsing three documents costs nothing anyone would
notice (`findings/2026.08.09-the-shelf-reparses-every-project-per-arrow-key.md`).

Nothing is shown. The panes are laid out by the track that holds them, which is
enough for a scroll area to have a range — a shown window in one added case has
ended a whole-directory run in a native abort with no attribution
(`tests/gui/driving.activate`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from sieve.tools import discover
from tests.gui import driving

#: Long enough that the selection walks off the bottom within a few keystrokes.
_LIBRARY = 40

_SOURCE = "clips"


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A folder of empty projects, named so the scan's order is the mint's."""
    for number in range(_LIBRARY):
        Project().save(tmp_path / f"p{number:02d}.sieve.yaml")
    return tmp_path


def _shelf(library: Path) -> tuple[Any, Any]:
    """A window over `library`, and the projects it scanned, in the scan's order."""
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    paths = projects_in(library)
    return MainWindow(list(paths), library=library), paths


def _scroll(pane: Any) -> Any:
    from PySide6.QtWidgets import QScrollArea

    return pane.findChild(QScrollArea)


def _reads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Every project file parsed from now on, in order."""
    original = Project.load

    seen: list[Path] = []

    def counted(path: Path) -> Any:
        seen.append(path)
        return original(path)

    monkeypatch.setattr(Project, "load", staticmethod(counted))
    return seen


def _in_view(pane: Any, card: Any) -> bool:
    from PySide6.QtCore import QPoint

    scroll = _scroll(pane)
    top = card.mapTo(scroll.widget(), QPoint(0, 0)).y()
    value = scroll.verticalScrollBar().value()
    return value <= top and top + card.height() <= value + scroll.viewport().height()


def test_arrowing_the_shelf_parses_no_document(
    qapp, library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ten moves of the accent, and not one document is read.

    Nothing a card says depends on which card is selected, so every parse a
    selection move pays for produces byte-identical strings — the whole of the
    cost, spent on nothing.
    """
    del qapp
    discover()

    window, _paths = _shelf(library)
    try:
        seen = _reads(monkeypatch)
        for _ in range(10):
            window.go_down()

        assert seen == []
    finally:
        window.close()


def test_a_shelf_re_reads_the_one_document_that_moved(
    qapp, library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A save is what a card goes stale against, and it is the only thing that is.

    The memo is keyed on what the filesystem knows about the file rather than on
    the redraw that asked, so a shelf drawn after one project was written re-reads
    that project and holds the other thirty-nine.
    """
    del qapp
    from sieve.gui.project_select import HeldListings, projects_in

    paths = projects_in(library)
    held = HeldListings()
    assert len(held.rows(paths)) == _LIBRARY

    seen = _reads(monkeypatch)
    assert len(held.rows(paths)) == _LIBRARY and seen == [], "nothing moved, nothing re-read"

    moved = paths[7]
    Project().save(moved)

    assert len(held.rows(paths)) == _LIBRARY
    assert seen == [moved]


def test_an_arrow_at_the_end_of_the_shelf_rebuilds_nothing(qapp, library: Path) -> None:
    """A held Up at the top of a library redraws forty cards to move nothing.

    The clamp is what makes the index the same; the rebuild was unconditional
    behind it, so the keystroke that is most likely to be *held* was the one that
    paid the most.
    """
    del qapp
    discover()

    window, _paths = _shelf(library)
    try:
        before = window.control.project_select
        window.go_up()

        assert window.control.project_select is before
    finally:
        window.close()


def test_the_accent_stays_in_view_as_the_shelf_is_arrowed(qapp, library: Path) -> None:
    """The card the arrow key moved to is on screen after it moved to it.

    A fresh `QScrollArea` starts at the top, so without this the accent leaves
    the visible region on the way down and the user is arrowing something they
    cannot see.
    """
    del qapp
    discover()

    window, _paths = _shelf(library)
    try:
        for _ in range(10):
            window.go_down()
        pane = window.control.project_select

        assert _scroll(pane).verticalScrollBar().value() > 0
        assert _in_view(pane, pane.cards[10])
    finally:
        window.close()


def test_a_shelf_redrawn_on_the_way_back_is_where_it_was_left(qapp, library: Path) -> None:
    """Entering a project and coming back out lands on the same view of the shelf.

    The way back rebuilds the shelf deliberately — a project saved since it was
    last drawn has a different date on it — so it is the redraw that proves the
    offset survives one rather than being recovered by the reveal: the selection
    is left clear of both edges, where bringing it into view moves nothing.
    """
    del qapp
    discover()

    window, paths = _shelf(library)
    try:
        for _ in range(20):
            window.go_down()
        for _ in range(3):
            window.go_up()
        left = _scroll(window.control.project_select).verticalScrollBar().value()
        assert left > 0, "a selection that never left the first screen proves nothing"

        window.enter_project(17)
        window.go_back()

        assert _scroll(window.control.project_select).verticalScrollBar().value() == left
        assert window.session is not None and window.session.path == paths[17]
    finally:
        window.close()


def _chain(directory: Path, steps: int) -> Path:
    """A project whose chain is long enough to scroll."""
    path = directory / "long.sieve.yaml"
    Project(
        pipeline=Pipeline(
            nodes=tuple(
                Node(node_id=f"s{index}", tool_id="downsample", version="1.0.0")
                for index in range(steps)
            ),
            edges=tuple(
                Edge(upstream=f"s{index}", downstream=f"s{index + 1}") for index in range(steps - 1)
            ),
        )
    ).save(path)
    return path


def test_the_chain_stack_lands_where_the_pane_it_replaced_was(qapp, tmp_path: Path) -> None:
    """The pipeline pane loses its scroll on every rebuild for the shelf's reason.

    The remedy is the same one and is taken once for both stacks, which is why
    this case is in this file: a chain is longer than most libraries, and the
    stack is rebuilt when a knob is turned and not only when the walk moves.
    """
    del qapp
    discover()
    from sieve.gui.app import MainWindow

    path = _chain(tmp_path, 14)
    window = MainWindow([path])
    try:
        window.open_project(path)
        assert _scroll(window.control.pipeline_pane).verticalScrollBar().maximum() > 0, (
            "a stack that does not scroll cannot lose a scroll"
        )
        # Down to the foot and back up three, which leaves the walk clear of both
        # edges of the viewport: what is being asserted is that the offset is
        # carried, and a selection at an edge would be put back there by the
        # reveal whether or not it was.
        for _ in range(13):
            window.go_down()
        for _ in range(3):
            window.go_up()
        left = _scroll(window.control.pipeline_pane).verticalScrollBar().value()
        assert left > 0

        window.pin(1)

        assert _scroll(window.control.pipeline_pane).verticalScrollBar().value() == left
    finally:
        window.close()


@pytest.fixture
def folder_project(tmp_path: Path) -> tuple[Path, Path]:
    """A project reading a folder, with a step under it that may be dropped."""
    folder = tmp_path / "arena"
    folder.mkdir()
    (folder / "a_first.mp4").write_bytes(b"")
    path = tmp_path / "folder.sieve.yaml"
    Project(
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_SOURCE,
                    tool_id="footage",
                    version="1.0.0",
                    params={"path": str(folder)},
                ),
                Node(node_id="thin", tool_id="downsample", version="1.0.0"),
            ),
            edges=(Edge(upstream=_SOURCE, downstream="thin"),),
        )
    ).save(path)
    return path, folder


def _walks(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every folder the source resolution lists from now on."""
    from sieve.tools import footage

    seen: list[str] = []
    original = footage.named_files

    def counted(pattern: str, tool: str) -> Any:
        seen.append(pattern)
        return original(pattern, tool)

    monkeypatch.setattr(footage, "named_files", counted)
    return seen


def test_a_step_leaving_the_chain_walks_no_folder(
    qapp, folder_project: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A graph edit re-derives four folds over memory and stats nothing.

    The fifth fact the window holds about the document read the filesystem, and
    it was re-read beside them — so every step dropped from a chain walked every
    folder the document names, on the GUI thread. A step leaving the chain cannot
    have changed what a folder holds.

    The other leg — the caller that exists *because* a folder can move under a
    window that did nothing — is
    `test_source_resolution.test_a_resolution_goes_stale_when_the_folder_changes`,
    and it is what stops this one being satisfied by never re-reading at all.
    """
    del qapp
    discover()
    from sieve.gui.app import MainWindow

    path, _folder = folder_project
    window = MainWindow([path])
    try:
        window.open_project(path)
        seen = _walks(monkeypatch)

        window.remove_step(1)

        assert seen == []
    finally:
        driving.activate(window, active=False)
        window.close()
