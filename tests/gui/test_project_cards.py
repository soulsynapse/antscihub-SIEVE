"""The project position is a stack of cards, and a project is chosen like a step.

Five claims. That there is a card per project under a library card is the shape;
that a click selects and only a double click enters are the two verbs that keep
the first surface a user meets reading like the rest of SIEVE rather than like a
platform list; that Up and Down move the project selection without disturbing
the node walk is what "selected the way a step is" has to mean when both
selections exist at once.

The three lines a card carries are asserted on `listings` rather than on labels,
because what a project holds and when it was written are facts about a document
on disk and the widget is handed them already derived. That case is also where
a file that is not a project gets its row: a library with one broken document in
it still has to draw the rest.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from sieve.tools import discover
from tests.gui import driving

#: How many steps each project in the library holds. Three projects because two
#: cannot tell "the selection moved down" from "the selection is the last one",
#: and the chains differ in length so the pane a double click lands on is
#: identifiably the project that was entered.
_LIBRARY = {"arena": 2, "colony": 3, "petri": 1}

_TOOLS = ("crop", "downsample", "detect")


def _write(path: Path, steps: int, source: str = "clip.mp4") -> Path:
    """A project of `steps` tools under a footage root naming `source`.

    The root is not one of the steps and the card must not count it as one
    (`gui/project_select._holds`): a document's footage is a node now
    (`adr/a-document-names-footage-only-through-a-tool.md`), and a chain of two
    that read as three would say so for every project in the library.
    """
    project = Project(
        pipeline=Pipeline(
            nodes=(
                Node(node_id="src", tool_id="footage", version="1.0.0", params={"path": source}),
                *(Node(node_id=f"n{i}", tool_id=_TOOLS[i], version="1.0.0") for i in range(steps)),
            ),
            edges=tuple(
                Edge(upstream="src" if i == 0 else f"n{i - 1}", downstream=f"n{i}")
                for i in range(steps)
            ),
        ),
    )
    project.save(path)
    return path


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A folder of three projects, in a directory of its own.

    Its own, so a case that needs a fourth document — one that will not parse —
    can write it somewhere `projects_in` will not hand to the window.
    """
    folder = tmp_path / "lib"
    folder.mkdir()
    for name, steps in _LIBRARY.items():
        _write(folder / f"{name}.sieve.yaml", steps)
    return folder


@pytest.fixture
def window(qapp, library: Path) -> Iterator[Any]:
    """A window at the project position over that library.

    Closed on the way out: a case that enters a project opens a decode thread
    over a clip that does not exist, and a `QThread` still alive when its
    `QObject` is finalised takes the process down (`app.closeEvent`).
    """
    del qapp
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    opened = MainWindow(projects_in(library))
    yield opened
    opened.close()


def _titles(cards: Any) -> list[str]:
    from PySide6.QtWidgets import QLabel

    return [card.findChild(QLabel).text() for card in cards]


def test_project_cards_are_one_per_project_under_a_library_card(window: Any, library: Path) -> None:
    from sieve.gui.chain_stack import ChainCard
    from sieve.gui.project_select import ProjectSelect

    pane = window.control.project_select

    assert isinstance(pane, ProjectSelect)
    assert len(pane.cards) == len(_LIBRARY)
    assert all(isinstance(card, ChainCard) for card in pane.cards)
    # The card the selection is on, and only it, wears the accent edge.
    assert [card.selected for card in pane.cards] == [True, False, False]
    assert _titles(pane.cards) == sorted(_LIBRARY)

    # What the stack belongs to, named above the scroll and not a card in it.
    assert _titles([pane.library_card]) == [f"library — {library}"]
    assert pane.library_card not in pane.cards


def test_project_cards_say_what_each_holds_and_when_it_was_written(tmp_path: Path) -> None:
    from sieve.gui.project_select import listings

    discover()

    arena = _write(tmp_path / "arena.sieve.yaml", 2)
    one = _write(tmp_path / "one.sieve.yaml", 1, source="pans/dish.mp4")
    empty = _write(tmp_path / "empty.sieve.yaml", 0)
    broken = tmp_path / "broken.sieve.yaml"
    broken.write_text("schema_version: 1\nsource: []\n", encoding="utf-8")

    # Anchored to this machine's own midday rather than to a date written here:
    # what is being asserted is a distance in days, and an mtime is an instant
    # that only becomes a calendar day in some zone. A literal date would make
    # the wording depend on where the test is run.
    now = datetime.now(tz=UTC).astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    long_ago = now - timedelta(days=365)
    os.utime(arena, (0, (now - timedelta(hours=9)).timestamp()))
    os.utime(one, (0, (now - timedelta(days=1)).timestamp()))
    os.utime(empty, (0, (now - timedelta(days=5)).timestamp()))
    os.utime(broken, (0, long_ago.timestamp()))

    rows = {row.name: row for row in listings((arena, one, empty, broken), now=now)}

    assert rows["arena"].holds == "2 steps · clip.mp4"
    assert rows["arena"].when == "saved today"
    # The source is named by its file and not by the path the document spells it
    # with: the card has a card's width, and the folder is the same for all of
    # them often enough that it would spend that width on nothing.
    assert rows["one"].holds == "1 step · dish.mp4"
    assert rows["one"].when == "saved yesterday"
    assert rows["empty"].holds == "no chain yet · clip.mp4"
    assert rows["empty"].when == "saved 5 days ago"
    # A document that will not parse is still a file the user has to see: the row
    # says so rather than being left out of the library or taking it down.
    assert rows["broken"].holds == "unreadable"
    # Past the point where a count of days reads as a duration, the card gives
    # the date instead.
    assert rows["broken"].when == f"saved {long_ago.date().isoformat()}"


def test_the_library_line_reads_footage_through_the_graph(tmp_path: Path) -> None:
    """Both halves of the card come out of the graph, and neither counts the other's node.

    `adr/a-document-names-footage-only-through-a-tool.md` leaves the document no
    field to read, so a card that still had one would be saying "no footage yet"
    about every project a user has ever picked a file for. What makes the
    counting half a claim too is `the-source-is-a-card-in-the-walk`: a mint
    writes an unchosen source node, so a chain length read off `len(nodes)` says
    "1 step" for a project with no chain at all.

    Three documents, one per way the pair can be wrong: a picked source under a
    chain, a source node with nothing chosen, and a graph with no source root at
    all — which is what a project emptied of its footage looks like now, and
    which the card has to survive rather than treat as unreadable.
    """
    from sieve.gui.project_select import listings

    discover()
    picked = _write(tmp_path / "picked.sieve.yaml", 2, source="pans/dish.mp4")
    unchosen = tmp_path / "unchosen.sieve.yaml"
    Project(
        pipeline=Pipeline(nodes=(Node(node_id="src", tool_id="footage", version="1.0.0"),))
    ).save(unchosen)
    rootless = tmp_path / "rootless.sieve.yaml"
    Project(pipeline=Pipeline(nodes=(Node(node_id="n0", tool_id="crop", version="1.0.0"),))).save(
        rootless
    )

    rows = {row.name: row for row in listings((picked, unchosen, rootless))}

    assert rows["picked"].holds == "2 steps · dish.mp4"
    assert rows["unchosen"].holds == "no chain yet · no footage yet"
    assert rows["rootless"].holds == "1 step · no footage yet"


def test_project_cards_click_selects_and_does_not_enter(window: Any) -> None:
    driving.click(window.control.project_select.cards[2], 4.0, 4.0)

    assert [card.selected for card in window.control.project_select.cards] == [
        False,
        False,
        True,
    ]
    # Selecting is the pointer's Up/Down and nothing else: nothing is opened and
    # the track has not moved.
    assert window.session is None
    assert window.control.current_position() == "project"


def test_project_cards_double_click_enters_the_pipeline_position(
    window: Any, library: Path
) -> None:
    from PySide6.QtWidgets import QLabel

    driving.double_click(window.control.project_select.cards[1], 4.0, 4.0)

    assert window.session is not None
    assert window.session.path == library / "colony.sieve.yaml"
    assert window.control.current_position() == "pipeline"
    # The stack it landed on is that project's, headed by its name and holding
    # its chain — the second click carries the selection with it, or it opens
    # whichever project the accent was on before.
    assert window.control.pipeline_pane.project_card.findChild(QLabel).text() == "project — colony"
    # The footage root is a card in the chain even though it is not a step the
    # library's line counts (`tests/gui/test_source_card.py`).
    assert len(window.control.pipeline_pane.cards) == _LIBRARY["colony"] + 1


def _reveal_buttons(cards: Any) -> list[Any]:
    from PySide6.QtWidgets import QPushButton

    return [card.findChild(QPushButton) for card in cards]


def test_open_location_is_on_the_selected_card_alone_and_travels_with_it(window: Any) -> None:
    pane = window.control.project_select

    assert [button is not None for button in _reveal_buttons(pane.cards)] == [True, False, False]
    assert _reveal_buttons(pane.cards)[0].text() == "OPEN LOCATION"

    window.go_down()

    # The pane is rebuilt when the selection moves, so the button is not moved
    # between cards — it is drawn on whichever card the accent landed on.
    moved = window.control.project_select
    assert [button is not None for button in _reveal_buttons(moved.cards)] == [False, True, False]


def test_open_location_opens_that_projects_folder_and_moves_nothing(
    window: Any, library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sieve.gui.app as app_module

    shown: list[Path] = []
    # The real one hands a URL to the desktop, which on a test machine either
    # opens a file manager or does nothing depending on what is installed —
    # neither of which is the claim. That `reveal` is called with this project
    # is; what it does with a folder is its own case below.
    monkeypatch.setattr(app_module, "reveal", shown.append)

    window.go_down()
    _reveal_buttons(window.control.project_select.cards)[1].click()

    assert shown == [library / "colony.sieve.yaml"]
    # The one verb in the surface that acts on the selection and cannot change
    # it: nothing is opened, and the track has not moved.
    assert window.session is None
    assert [card.selected for card in window.control.project_select.cards] == [False, True, False]
    assert window.control.current_position() == "project"


def test_open_location_asks_for_the_folder_the_document_sits_in(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    from PySide6.QtGui import QDesktopServices

    from sieve.gui import project_select

    asked: list[Any] = []
    monkeypatch.setattr(QDesktopServices, "openUrl", asked.append)

    project_select.reveal(tmp_path / "lib" / "arena.sieve.yaml")

    # The folder, not the file: a project on disk is the document beside its
    # footage and above what a run wrote, and no file manager can be asked
    # portably to open with one entry picked out.
    assert [url.toLocalFile() for url in asked] == [(tmp_path / "lib").as_posix()]


def _new_button(pane: Any) -> Any:
    from PySide6.QtWidgets import QPushButton

    return pane.library_card.findChild(QPushButton)


def test_new_project_mints_an_unchosen_source_the_library_lists(
    window: Any, library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sieve.gui.app as app_module
    from sieve.gui.project_select import listings, projects_in

    # Answering the ask with the folder already on the shelf, which is the case
    # the rest of this asserts: the mint's own answer is where it lands, and
    # what a `QFileDialog` looks like is Qt's.
    monkeypatch.setattr(app_module, "ask_where", lambda parent: library)

    # A project sorting *after* the minted names, so that "the shelf is the
    # folder's own answer in the folder's own order" is a claim with a witness:
    # a mint appended to the list in hand would stand below this one.
    _write(library / "zzz.sieve.yaml", 1)

    assert _new_button(window.control.project_select).text() == "NEW PROJECT"

    _new_button(window.control.project_select).click()
    # Twice, because a mint that reused the name would not be a second project —
    # it would silently be the first one again, and the card would say so only
    # once its chain diverged.
    _new_button(window.control.project_select).click()

    minted = [path for path in projects_in(library) if path.name.startswith("untitled")]
    assert len(minted) == 2
    # One node on disk and no file named: the source picker the project opens on
    # is a picture of something the graph carries, so the mint has to write it
    # (`tests/gui/test_source_card.py`). Choosing the footage is the next act.
    written = [Project.load(path) for path in minted]
    assert [[(node.tool_id, node.params) for node in held.pipeline.nodes] for held in written] == [
        [("footage", {})],
        [("footage", {})],
    ]
    # Both halves of the card read the graph and each leaves the other's node
    # out: the picker is the footage, so it is neither a step nor a file chosen.
    assert listings((minted[0],))[0].holds == "no chain yet · no footage yet"

    pane = window.control.project_select
    assert len(pane.cards) == len(_LIBRARY) + 3
    assert _titles(pane.cards)[3:] == ["untitled_1", "untitled_2", "zzz"]
    # The selection lands on the mint without entering it: the chain pane would
    # show a chain the project does not have.
    assert [card.selected for card in pane.cards] == [False] * 4 + [True, False]
    assert window.session is None
    assert window.control.current_position() == "project"


def test_new_project_mints_into_an_empty_library(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    import sieve.gui.app as app_module
    from sieve.gui.app import MainWindow

    folder = tmp_path / "empty"
    folder.mkdir()
    monkeypatch.setattr(app_module, "ask_where", lambda parent: folder)
    # The first-run case, and the reason the folder is a parameter rather than
    # only being derived from the projects: an empty library has no project to
    # read one off, and it is exactly where minting is the only thing to do.
    opened = MainWindow((), library=folder)
    try:
        _new_button(opened.control.project_select).click()

        pane = opened.control.project_select
        assert _titles([pane.library_card]) == [f"library — {folder}"]
        assert _titles(pane.cards) == ["untitled_1"]
        assert [card.selected for card in pane.cards] == [True]
    finally:
        opened.close()


def test_project_cards_up_and_down_move_the_selection_not_the_walk(window: Any) -> None:
    driving.double_click(window.control.project_select.cards[0], 4.0, 4.0)
    # Two steps down: the walk starts on the footage root.
    window.go_down()
    window.go_down()
    assert window.current_node.node_id == "n1"

    window.go_back()
    assert window.control.current_position() == "project"

    window.go_down()
    assert [card.selected for card in window.control.project_select.cards] == [
        False,
        True,
        False,
    ]
    # Two selections exist at once and Up/Down move exactly the one the position
    # showing is about; the walk is still standing where the user left it.
    assert window.current_node.node_id == "n1"

    window.go_up()
    window.go_up()
    assert [card.selected for card in window.control.project_select.cards] == [
        True,
        False,
        False,
    ]


def test_new_project_asks_where_the_project_goes(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    import sieve.gui.app as app_module
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    chosen = tmp_path / "somewhere"
    chosen.mkdir()
    asked: list[Any] = []

    def ask(parent: Any) -> Path:
        asked.append(parent)
        return chosen

    # The real one opens a modal that waits for a person. That the mint asks is
    # the claim; what a `QFileDialog` looks like is Qt's.
    monkeypatch.setattr(app_module, "ask_where", ask)

    # The window `main` builds: no folder and nothing scanned, which is what
    # "nothing defaults anywhere" leaves. The button is the shelf's one gesture
    # and is drawn with no library, or an empty shelf would have no way out.
    opened = MainWindow(())
    try:
        assert opened.control.project_select.cards == ()

        _new_button(opened.control.project_select).click()

        assert asked == [opened]
        minted = projects_in(chosen)
        assert len(minted) == 1
        assert [node.tool_id for node in Project.load(minted[0]).pipeline.nodes] == ["footage"]

        pane = opened.control.project_select
        assert _titles(pane.cards) == ["untitled_1"]
        # The answer is the folder now being listed, so the card above the shelf
        # says so: a title naming a folder the cards did not come out of would be
        # the second answer to which library is being looked at.
        assert _titles([pane.library_card]) == [f"library — {chosen}"]
        assert [card.selected for card in pane.cards] == [True]
        assert opened.session is None
        assert opened.control.current_position() == "project"
    finally:
        opened.close()


def test_a_cancelled_ask_mints_nothing(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    import sieve.gui.app as app_module
    from sieve.gui.app import MainWindow

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "ask_where", lambda parent: None)

    opened = MainWindow(())
    try:
        _new_button(opened.control.project_select).click()

        assert opened.control.project_select.cards == ()
        # The whole of "nothing defaults anywhere": there is no location the ask
        # falls back to when it is given none, and in particular not the
        # directory the process was launched in — which is the only thing that
        # could put a document the user did not ask for beside `pyproject.toml`.
        assert list(tmp_path.iterdir()) == []
        assert opened.session is None
    finally:
        opened.close()
