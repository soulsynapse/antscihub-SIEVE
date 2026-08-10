"""The first card of the stack is where the footage is chosen and what it named.

VISION's new-project scenario is the whole of what is asserted here: "the only
pipeline item is the source picker with nothing chosen", a file picked out of a
folder, the source swapped to the folder itself, and "two files now show in the
source tool". Two surfaces answer that — the chooser generated for the path
parameter, which writes, and the line under it saying what the path resolved to,
which does not.

The two are kept apart on purpose and the cases are written against both. The
chooser is the document: it says what `path` holds and it is the only thing here
that edits. The line is the filesystem, read by `MainWindow.resolved_sources`
and stale the moment somebody drops a file in the folder
(`test_source_resolution.py` owns when it is re-read) — so a card drawing the
resolution *as* the value would be showing a fact the document does not hold.

A step that is not a source carries neither, which is the case that separates
"this source names nothing" from "this is not a source": both are an empty
ordering, and only one of them is a sentence the card owes.

Two more claims are about the card's *existence* rather than its lines. A minted
project holds the source node the card draws, because VISION's new project puts
the user "straight into it, where the only pipeline item is the source picker
with nothing chosen" — and the root position offers the sources, which is the
question a root asks in place of the accepts-side one nothing is feeding it.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from sieve.tools import discover

_SOURCE = "clips"
_READER = "smaller"


def _project(path: Path, source_path: str) -> Path:
    """A footage root reading `source_path`, with one ordinary step below it.

    The second node is what makes the source card's line a claim about *source*
    cards: a stack of one would be green whether the line were drawn per source
    root or on every card in the chain.
    """
    document = path / "arena.sieve.yaml"
    Project(
        pipeline=Pipeline(
            nodes=(
                Node(
                    node_id=_SOURCE,
                    tool_id="footage",
                    version="1.0.0",
                    params={"path": source_path},
                ),
                Node(node_id=_READER, tool_id="downsample", version="1.0.0"),
            ),
            edges=(Edge(upstream=_SOURCE, downstream=_READER),),
        )
    ).save(document)
    return document


def _window(document: Path) -> Any:
    discover()
    from sieve.gui.app import MainWindow

    opened = MainWindow([document])
    opened.open_project(document)
    return opened


@pytest.fixture
def folder_window(qapp, tmp_path: Path) -> Iterator[Any]:
    """A source pointed at a folder holding two videos, and a step reading it."""
    del qapp
    folder = tmp_path / "arena"
    folder.mkdir()
    (folder / "a_first.mp4").write_bytes(b"")
    (folder / "b_second.mp4").write_bytes(b"")
    opened = _window(_project(tmp_path, str(folder)))
    yield opened
    opened.close()


@pytest.fixture
def unchosen_window(qapp, tmp_path: Path) -> Iterator[Any]:
    """The state a project is minted into: a source with nothing chosen."""
    del qapp
    opened = _window(_project(tmp_path, ""))
    yield opened
    opened.close()


def _chooser(card: Any) -> Any:
    from sieve.gui.param_form import PathChooser

    return card.findChild(PathChooser)


def test_the_source_card_lists_what_its_path_resolved_to(folder_window: Any) -> None:
    """Two files in the folder, two names on the card, in the resolution's order.

    Read off `MainWindow.resolved_sources` rather than resolved here, which is
    the point of the case: that map was landed with no reader at all, so the
    ordering the window computes and the ordering the user is shown could not
    have disagreed because only one of them existed.
    """
    cards = folder_window.control.pipeline_pane.cards

    assert cards[0].sources is not None
    assert cards[0].sources.text() == "2 files · a_first.mp4 · b_second.mp4"


def test_a_step_that_is_not_a_source_carries_no_resolution_line(folder_window: Any) -> None:
    """The distinction an empty ordering cannot draw on its own.

    A source naming nothing and a step that is not a source both resolve to no
    files. Only the first owes the user a sentence, so the card is handed the
    absence rather than the emptiness.
    """
    cards = folder_window.control.pipeline_pane.cards

    assert cards[1].sources is None
    assert _chooser(cards[1]) is None


def test_a_source_with_nothing_chosen_says_so_on_both_lines(unchosen_window: Any) -> None:
    """VISION's minted project: the picker is there and it is empty.

    Both lines, because they are two facts and a card showing one of them would
    be as green with the other missing.
    """
    from sieve.gui.chain_stack import NO_RESOLUTION_NOTE
    from sieve.gui.param_form import UNCHOSEN

    card = unchosen_window.control.pipeline_pane.cards[0]

    assert card.sources is not None
    assert card.sources.text() == NO_RESOLUTION_NOTE
    assert _chooser(card).shown.text() == UNCHOSEN


def test_the_source_card_chooser_shows_the_path_the_document_holds(
    folder_window: Any, tmp_path: Path
) -> None:
    """The value, not the resolution: what the user swapped to is the folder."""
    chooser = _chooser(folder_window.control.pipeline_pane.cards[0])

    assert chooser.shown.text() == str(tmp_path / "arena")


def test_browsing_for_a_file_writes_it_through_the_command_layer(
    unchosen_window: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Picking a video is a `SetParam` on the source node like any other knob.

    The ask is replaced rather than driven: what a `QFileDialog` looks like is
    Qt's, and what the button does with the answer is the claim.
    """
    from sieve.gui import param_form

    clip = tmp_path / "one.mp4"
    clip.write_bytes(b"")
    monkeypatch.setattr(param_form, "ask_for_file", lambda parent: clip)

    _chooser(unchosen_window.control.pipeline_pane.cards[0]).browse_file.click()

    assert unchosen_window.session.project.params_for(_SOURCE)["path"] == str(clip)


def test_browsing_for_a_folder_writes_the_folder_itself(
    unchosen_window: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of VISION's swap: a source may name the folder, not a file.

    Two verbs rather than one dialog, because a file dialog that also returns
    directories is not something Qt offers — and the two are different questions
    anyway, which is what the scenario's "change their mind" is.
    """
    from sieve.gui import param_form

    folder = tmp_path / "clips"
    folder.mkdir()
    monkeypatch.setattr(param_form, "ask_for_folder", lambda parent: folder)

    _chooser(unchosen_window.control.pipeline_pane.cards[0]).browse_folder.click()

    assert unchosen_window.session.project.params_for(_SOURCE)["path"] == str(folder)


def test_a_minted_project_opens_on_a_source_card_with_nothing_chosen(
    qapp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NEW PROJECT writes the node this card is a picture of.

    Driven through `new_project` rather than `mint`, because the claim is what
    the user is standing in front of and the document is only half of it: a
    minted file holding a source node that drew no card would be as green.

    The tool is named here and nowhere in `gui`: which source a mint stands on
    is `tool_registry.source_tools`' head, and that this is the one that reads a
    video rather than the one that reads what an earlier run wrote is the whole
    of what the ordering buys.
    """
    del qapp
    import sieve.gui.app as app_module
    from sieve.gui.app import MainWindow
    from sieve.gui.chain_stack import NO_RESOLUTION_NOTE
    from sieve.gui.param_form import UNCHOSEN
    from sieve.gui.project_select import projects_in

    discover()
    library = tmp_path / "lib"
    library.mkdir()
    monkeypatch.setattr(app_module, "ask_where", lambda parent: library)

    opened = MainWindow((), library=library)
    try:
        opened.new_project()
        opened.open_project(projects_in(library)[0])

        cards = opened.control.pipeline_pane.cards
        assert len(cards) == 1
        assert opened.session.project.pipeline.nodes[0].tool_id == "footage"
        assert cards[0].sources is not None
        assert cards[0].sources.text() == NO_RESOLUTION_NOTE
        assert _chooser(cards[0]).shown.text() == UNCHOSEN
    finally:
        opened.close()


def test_the_root_position_offers_the_source_tools(folder_window: Any) -> None:
    """`offered_tools`' source refusal, read the other way.

    Nothing flows into a root, so the accepts-side match every other position
    is offered by is vacuous there and what distinguishes the candidates is
    that they are sources at all. Sources that say what one of their values
    means lead, so the head is a file the user chooses rather than a checkpoint
    an earlier run wrote.
    """
    folder_window.swap_step(0)

    box = folder_window.control.pipeline_pane.add_box
    assert box is not None
    assert box.anchored
    assert box.site == 0
    assert [button.text() for button in box.offer_buttons] == ["footage", "pick", "checkpoint"]
    # Lit on the source already standing there, which is the swap box's rule
    # everywhere and says "and it could stay" at the one position that could
    # never be emptied.
    assert box.lit == 0


def test_a_cancelled_browse_writes_nothing(
    folder_window: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Esc out of the dialog leaves the source pointed where it was.

    A cancelled ask is the one answer a picker gets that must not reach the
    document — the same rule `project_select.ask_where` runs on, where a
    fallback location is the only thing that can write a project nobody asked
    for.
    """
    from sieve.gui import param_form

    monkeypatch.setattr(param_form, "ask_for_file", lambda parent: None)
    monkeypatch.setattr(param_form, "ask_for_folder", lambda parent: None)

    chooser = _chooser(folder_window.control.pipeline_pane.cards[0])
    chooser.browse_file.click()
    chooser.browse_folder.click()

    assert folder_window.session.project.params_for(_SOURCE)["path"] == str(tmp_path / "arena")
