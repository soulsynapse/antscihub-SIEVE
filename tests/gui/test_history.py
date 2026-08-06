"""Autosave and rollback, driven through the real window.

Three claims, each of which would fail for a different real reason:

* an edit nobody saved is on disk afterwards, beside a video that has no project
  file yet — the whole point of taking the save prompt away;
* a rollback returns the document *and* is itself undoable, so the net covers
  itself and a mistaken restore is one Ctrl+Z;
* a history that cannot be written turns itself off and says so, rather than
  leaving a user trusting a net that is not there.

The window is driven rather than the store called, because the load-bearing part
is the wiring: the store has to be pointed at a directory before the first edit,
including in the ordinary case where the user has opened a video and saved
nothing.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from pytestqt.qtbot import QtBot

from sieve.core.history import SnapshotStore, history_directory
from sieve.core.pipeline_model import Project, project_path_for
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.history_dialog import age_text
from sieve.gui.main_window import HISTORY_FAILED, MainWindow
from sieve.gui.preferences import Preferences

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000


@pytest.fixture
def video(tmp_path: Path, synthetic_video: Path) -> Path:
    """The fixture video, copied where this test may write beside it."""
    destination = tmp_path / "arena.mp4"
    shutil.copy(synthetic_video, destination)
    return destination


@pytest.fixture
def window(qtbot: QtBot, tmp_path: Path) -> Iterator[MainWindow]:
    settings = QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat)
    main = MainWindow(Preferences(settings))
    qtbot.addWidget(main)
    yield main
    _document(main).undo_stack.setClean()
    main.close()


def _document(window: MainWindow) -> ReplicateDocument:
    document = window.findChild(ReplicateDocument)
    assert isinstance(document, ReplicateDocument)
    return document


def _open(qtbot: QtBot, window: MainWindow, video: Path) -> ReplicateDocument:
    window.open_video(video)
    qtbot.waitUntil(lambda: window.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)
    return _document(window)


def _history_of(video: Path) -> SnapshotStore:
    """The store a reader would find, built from the convention alone."""
    return SnapshotStore(history_directory(project_path_for(video)))


class TestAnEditReachesDiskWithoutBeingSaved:
    def test_a_replicate_drawn_into_an_unsaved_project_is_in_the_history(
        self, qtbot: QtBot, window: MainWindow, video: Path
    ) -> None:
        document = _open(qtbot, window, video)
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        qtbot.waitUntil(lambda: bool(_history_of(video).entries()), timeout=OPEN_TIMEOUT_MS)

        entries = _history_of(video).entries()
        assert [snapshot.text for snapshot in entries] == ["Add Replicate 1"]
        # The session's first write, so retention will keep it past the window.
        assert entries[0].session_start

    def test_a_snapshot_is_a_project_that_opens_on_its_own(
        self, qtbot: QtBot, window: MainWindow, video: Path
    ) -> None:
        document = _open(qtbot, window, video)
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        qtbot.waitUntil(lambda: bool(_history_of(video).entries()), timeout=OPEN_TIMEOUT_MS)

        path = _history_of(video).entries()[-1].path
        restored = Project.load(path)
        assert len(restored.replicates) == 1
        # The anchoring claim: a snapshot names its video relative to the
        # directory it actually sits in, one level below the project's.
        assert restored.source_path(path) == video.resolve()

    def test_two_edits_in_one_turn_write_one_snapshot(
        self, qtbot: QtBot, window: MainWindow, video: Path
    ) -> None:
        # The coalescing claim. Autosave is keyed to the undo stack, so a burst
        # inside one event-loop turn is one write, not one per command.
        document = _open(qtbot, window, video)
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        document.add_roi(ROI(x=40, y=40, width=20, height=20))
        qtbot.waitUntil(lambda: bool(_history_of(video).entries()), timeout=OPEN_TIMEOUT_MS)
        assert [snapshot.text for snapshot in _history_of(video).entries()] == ["Add Replicate 2"]

    def test_a_write_failure_turns_history_off_and_says_so(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        document = _open(qtbot, window, video)
        status_messages: list[str] = []
        window.statusBar().messageChanged.connect(status_messages.append)

        def refuse(*_args: object, **_kwargs: object) -> None:
            raise OSError("read-only")

        monkeypatch.setattr(SnapshotStore, "record", refuse)
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        qtbot.waitUntil(
            lambda: any(HISTORY_FAILED.split("{")[0] in message for message in status_messages),
            timeout=OPEN_TIMEOUT_MS,
        )
        # And it stays off: retrying every keystroke would bury the one message
        # that matters under a hundred identical ones.
        document.add_roi(ROI(x=40, y=40, width=20, height=20))
        assert not _history_of(video).entries()


class TestRollback:
    def test_restoring_returns_the_document_and_is_itself_undoable(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        earlier = document.capture()
        document.add_roi(ROI(x=40, y=40, width=20, height=20))
        assert len(document) == 2

        document.restore(earlier, "Add Replicate 1")
        assert len(document) == 1

        document.undo_stack.undo()
        assert len(document) == 2

    def test_restoring_the_state_already_showing_stacks_nothing(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        before = document.undo_stack.count()
        document.restore(document.capture(), "Add Replicate 1")
        assert document.undo_stack.count() == before

    def test_a_restore_keeps_the_selection_on_a_row_that_exists(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        earlier = document.capture()
        document.add_roi(ROI(x=40, y=40, width=20, height=20))
        assert document.selected_index == 1
        document.restore(earlier, "Add Replicate 1")
        assert document.selected_index == 0

    def test_a_snapshot_is_refitted_onto_the_source_actually_bound(
        self, document: ReplicateDocument, tmp_path: Path
    ) -> None:
        # A history file written before the footage was re-encoded must not come
        # back as a replicate hanging off the frame. The document fixture binds
        # 1000x800; the saved ROI runs past it.
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"")
        document.add_roi(ROI(x=1, y=1, width=20, height=20))
        oversized = (
            document.capture().replicates[0].with_roi(ROI(x=0, y=0, width=4000, height=3000))
        )
        project = Project.for_video(video, tmp_path).with_replicates((oversized,))

        document.restore(document.state_from_project(project), "Add Replicate 1")
        assert document.at(0).roi == ROI(x=0, y=0, width=1000, height=800)


class TestAge:
    def test_the_units_are_the_coarsest_that_still_distinguish(self) -> None:
        # Lives with the dialog because it is a rendering, not a fact about
        # what is on disk: a snapshot carries an mtime and nothing else.
        assert age_text(5) == "just now"
        assert age_text(300) == "5 min ago"
        assert age_text(3600) == "1 hour ago"
        assert age_text(7200) == "2 hours ago"
        assert age_text(86400) == "yesterday"
        assert age_text(86400 * 3) == "3 days ago"
