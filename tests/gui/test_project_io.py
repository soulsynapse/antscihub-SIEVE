"""Reading and writing a project from the window.

Four things can go wrong here and each is tested on its own account.

The round trip can lose a field — either one the user edited, or one the GUI
cannot edit and would therefore drop silently on every save, which is the worse
of the two because nothing in the interface would ever show it.

The *ordering* can be wrong. `bind_source` clears replicates, clip, and graph,
and opening a project opens its video first, so a load written as a sequence of
ordinary edits would be erased by the very bind that made the source known. The
async player is what makes this a real hazard rather than a hypothetical, so the
test drives the real window rather than calling `load_project` directly.

The load can leave history behind, which turns Ctrl+Z into something that undoes
a file open and leaves a freshly opened project claiming to be unsaved.

And the document can be restored against a source it no longer fits, because a
project names its video by path and a path promises nothing about dimensions or
length.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from sieve.core.pipeline_model import (
    ClipRange,
    Edge,
    Node,
    Pipeline,
    Project,
    Sink,
    project_path_for,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.main_window import MainWindow
from sieve.gui.preferences import Preferences
from tests.gui.conftest import answering

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000

DOWNSAMPLE = Node(node_id="n1", filter_id="downsample", version="1.0.0", params={"factor": 4})
THRESHOLD = Node(node_id="n2", filter_id="threshold", version="2.1.0", params={"level": 0.25})
GRAPH = Pipeline(nodes=(DOWNSAMPLE, THRESHOLD), edges=(Edge(upstream="n1", downstream="n2"),))


def _replicates() -> tuple[Replicate, ...]:
    """Two arenas, the second deviating from the graph's defaults.

    The override is the part worth carrying: it is stored against a node id, so
    it is the field that goes wrong first if the graph and the replicates are
    restored out of step with each other.
    """
    return (
        Replicate(roi=ROI(x=0, y=0, width=40, height=30), name="Left", replicate_id="r1"),
        Replicate(
            roi=ROI(x=60, y=20, width=40, height=30),
            name="Right",
            replicate_id="r2",
            overrides={"n2": {"level": 0.75}},
        ),
    )


@pytest.fixture
def video(tmp_path: Path, synthetic_video: Path) -> Path:
    """The fixture video, copied somewhere this test may write beside it.

    `synthetic_video` is session-scoped: a project written next to it would
    still be there for the next test, and the neighbour offer would fire in
    tests that never asked about one.
    """
    destination = tmp_path / "arena.mp4"
    shutil.copy(synthetic_video, destination)
    return destination


@pytest.fixture
def window(qtbot: QtBot, tmp_path: Path) -> Iterator[MainWindow]:
    settings = QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat)
    main = MainWindow(Preferences(settings))
    qtbot.addWidget(main)
    yield main
    # Declared clean before closing, because teardown is not a user decision.
    # Two tests here deliberately refuse a close, and a window that refuses one
    # never reaches `_player.shutdown()` — the decode thread outlives the
    # QApplication and takes the interpreter down with it, mid-suite and with no
    # traceback naming the test that did it.
    _document(main).undo_stack.setClean()
    main.close()


def _open(qtbot: QtBot, window: MainWindow, video: Path) -> None:
    window.open_video(video)
    qtbot.waitUntil(lambda: window.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)


def _document(window: MainWindow) -> ReplicateDocument:
    document = window.findChild(ReplicateDocument)
    assert isinstance(document, ReplicateDocument)
    return document


def _project_file(path: Path, video: Path, **overrides: object) -> Project:
    """A project on disk naming `video`, with two replicates, a clip, and a graph."""
    project = Project.for_video(video, path.parent).model_copy(
        update={
            "replicates": _replicates(),
            "clip": ClipRange(start=5, end=25),
            "pipeline": GRAPH,
            **overrides,
        }
    )
    project.save(path)
    return project


def _choosing(path: str) -> Callable[..., tuple[str, str]]:
    """A stand-in for `QFileDialog.getSaveFileName`. Empty `path` means Cancel."""

    def chosen(*_args: object, **_kwargs: object) -> tuple[str, str]:
        return path, ""

    return chosen


def _save_as(monkeypatch: pytest.MonkeyPatch, window: MainWindow, path: Path) -> bool:
    """Drive Save As with the file dialog answering `path`."""
    monkeypatch.setattr(QFileDialog, "getSaveFileName", _choosing(str(path)))
    return window.save_project_as()


class TestRoundTrip:
    def test_a_project_reopens_as_the_document_it_was_saved_from(
        self, qtbot: QtBot, window: MainWindow, video: Path, tmp_path: Path
    ) -> None:
        """The whole item, through the real asynchronous open.

        This is also the ordering test: `open_project` opens the video, which
        clears the document from a queued signal, and the project has to be
        applied on the far side of that clear.
        """
        path = tmp_path / "arena.sieve.yaml"
        _project_file(path, video)

        window.open_project(path)
        qtbot.waitUntil(lambda: len(_document(window)) == 2, timeout=OPEN_TIMEOUT_MS)

        document = _document(window)
        assert [replicate.name for replicate in document.all()] == ["Left", "Right"]
        assert document.at(1).overrides == {"n2": {"level": 0.75}}
        assert document.clip == ClipRange(start=5, end=25)
        assert document.pipeline == GRAPH
        # Two arenas running different thresholds are not one group. Restoring
        # the graph without the overrides, or the reverse, reads as one.
        assert document.equivalence_groups() == (1, 2)

    def test_saving_keeps_the_fields_the_gui_cannot_edit(
        self, qtbot: QtBot, window: MainWindow, video: Path, tmp_path: Path
    ) -> None:
        """A sink is invisible in this GUI, so dropping one would never show.

        `apply_to` copies the project it was handed rather than assembling a
        fresh one precisely to stop this; building `Project(source=...)` from
        the document's three fields would pass every other test in this file.
        """
        path = tmp_path / "arena.sieve.yaml"
        _project_file(
            path,
            video,
            checkpoints=("n1",),
            outputs=(Sink(sink_id="s1", node_id="n2", format="png", path="out"),),
        )

        window.open_project(path)
        qtbot.waitUntil(lambda: len(_document(window)) == 2, timeout=OPEN_TIMEOUT_MS)
        _document(window).rename(0, "Renamed")
        assert window.save_project() is True

        reloaded = Project.load(path)
        assert reloaded.checkpoints == ("n1",)
        assert [sink.sink_id for sink in reloaded.outputs] == ["s1"]
        assert reloaded.replicates[0].name == "Renamed"

    def test_a_video_opened_on_its_own_can_be_saved_as_a_project(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The path with no project to copy from, where one is built instead.

        The source reference is what this is really about: it is stored
        relative to the file being written, so a project that names its video
        by an absolute path — or by one relative to the wrong directory —
        passes every in-memory assertion and cannot be opened from anywhere.
        """
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        path = project_path_for(video)
        assert _save_as(monkeypatch, window, path) is True

        saved = Project.load(path)
        assert saved.source.path == video.name
        assert saved.source_path(path) == video.resolve()
        assert len(saved.replicates) == 1

    def test_a_name_typed_without_the_suffix_still_lands_beside_the_video(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`project_path_for` is a convention other code reads back."""
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        assert _save_as(monkeypatch, window, video.parent / "arena") is True
        assert project_path_for(video).is_file()


class TestLoadPath:
    """`load_project` on its own, without a player in the way."""

    def test_loading_leaves_no_history_and_nothing_to_save(
        self, document: ReplicateDocument
    ) -> None:
        """Ctrl+Z must not undo a file open, and an untouched project is clean."""
        document.add_roi(ROI(x=0, y=0, width=10, height=10))
        document.load_project(
            Project.for_video(Path("arena.mp4")).model_copy(
                update={"replicates": _replicates(), "pipeline": GRAPH}
            )
        )

        assert len(document) == 2
        assert not document.undo_stack.canUndo()
        assert document.undo_stack.isClean()

    @pytest.mark.parametrize(
        ("saved", "expected"),
        [
            # Straddling the end: the part that exists is kept.
            (ClipRange(start=900, end=1200), ClipRange(start=900, end=1000)),
            # Entirely past it: there is no span to keep, and clamping to the
            # last frame would invent a one-frame clip nobody marked.
            (ClipRange(start=1500, end=1600), None),
        ],
    )
    def test_a_clip_is_trimmed_onto_the_source_actually_bound(
        self, document: ReplicateDocument, saved: ClipRange, expected: ClipRange | None
    ) -> None:
        """A project names its video by path; a path is not a length."""
        document.load_project(
            Project.for_video(Path("arena.mp4")).model_copy(update={"clip": saved})
        )
        assert document.clip == expected

    def test_replicates_are_refitted_to_the_source_actually_bound(
        self, document: ReplicateDocument
    ) -> None:
        """The `document` fixture binds 1000x800; this box hangs off the right."""
        document.load_project(
            Project.for_video(Path("arena.mp4")).model_copy(
                update={
                    "replicates": (
                        Replicate(roi=ROI(x=900, y=0, width=400, height=100), name="Wide"),
                    )
                }
            )
        )
        assert document.at(0).roi == ROI(x=900, y=0, width=100, height=100)


class TestUnsavedChanges:
    def test_an_edit_marks_the_window_and_saving_unmarks_it(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _open(qtbot, window, video)
        assert window.isWindowModified() is False

        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))
        assert window.isWindowModified() is True

        assert _save_as(monkeypatch, window, project_path_for(video)) is True
        assert window.isWindowModified() is False

    def test_cancelling_the_prompt_refuses_the_close(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cancel means cancel. Returning True here loses the session silently."""
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))
        monkeypatch.setattr(QMessageBox, "warning", answering(QMessageBox.StandardButton.Cancel))

        assert window.confirm_discard() is False
        assert window.close() is False

    def test_backing_out_of_the_save_dialog_is_not_consent_to_discard(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Save, then Cancel at the file dialog, is a user who has saved nothing.

        The bug this exists for is `confirm_discard` treating "the user chose
        Save" as the end of the question rather than waiting to hear whether a
        file was actually written.
        """
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))
        monkeypatch.setattr(QMessageBox, "warning", answering(QMessageBox.StandardButton.Save))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", _choosing(""))

        assert window.confirm_discard() is False
        assert window.isWindowModified() is True


class TestNeighbourOpen:
    def test_opening_a_video_opens_the_project_filed_beside_it_without_asking(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """It restores, and it does so with no question in front of the video."""
        _project_file(project_path_for(video), video)
        asked: list[object] = []

        def answer(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
            asked.append(args)
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(QMessageBox, "question", answer)

        _open(qtbot, window, video)

        assert asked == []
        assert len(_document(window)) == 2

    def test_the_restore_says_which_project_and_from_where(
        self, qtbot: QtBot, window: MainWindow, video: Path
    ) -> None:
        """The provenance the question used to carry has to survive somewhere.

        Restoring two replicates the user cannot account for is the surprise the
        modal existed to prevent; the status bar is where that argument now
        lands, so a silent restore is a regression even though the state is
        right.
        """
        _project_file(project_path_for(video), video)

        _open(qtbot, window, video)

        message = window.statusBar().currentMessage()
        assert "arena.sieve.yaml" in message
        assert str(video.parent) in message

    def test_a_video_with_no_project_beside_it_restores_nothing(
        self, qtbot: QtBot, window: MainWindow, video: Path
    ) -> None:
        _open(qtbot, window, video)

        assert len(_document(window)) == 0
        assert "Restored" not in window.statusBar().currentMessage()


class TestSourceMismatch:
    def test_a_project_whose_video_is_gone_is_refused_before_anything_is_cleared(
        self, qtbot: QtBot, window: MainWindow, video: Path, tmp_path: Path
    ) -> None:
        """Refusing after the clear would cost the user the document they had."""
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        orphan = tmp_path / "moved.sieve.yaml"
        _project_file(orphan, tmp_path / "on-the-nas.mp4")
        window.open_project(orphan)

        assert len(_document(window)) == 1
        assert window.windowTitle() != "SIEVE"
