





















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
from sieve.gui.history import SnapshotStore, history_directory
from sieve.gui.main_window import MainWindow
from sieve.gui.preferences import Preferences

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000

DOWNSAMPLE = Node(node_id="n1", filter_id="downsample", version="1.0.0", params={"factor": 4})
THRESHOLD = Node(node_id="n2", filter_id="threshold", version="2.1.0", params={"level": 0.25})
GRAPH = Pipeline(nodes=(DOWNSAMPLE, THRESHOLD), edges=(Edge(upstream="n1", downstream="n2"),))


def _replicates() -> tuple[Replicate, ...]:






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






    destination = tmp_path / "arena.mp4"
    shutil.copy(synthetic_video, destination)
    return destination


@pytest.fixture
def window(qtbot: QtBot, tmp_path: Path) -> Iterator[MainWindow]:
    settings = QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat)
    main = MainWindow(Preferences(settings))
    qtbot.addWidget(main)
    yield main




    main.close()


def _open(qtbot: QtBot, window: MainWindow, video: Path) -> None:
    window.open_video(video)
    qtbot.waitUntil(lambda: window.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)


def _document(window: MainWindow) -> ReplicateDocument:
    document = window.findChild(ReplicateDocument)
    assert isinstance(document, ReplicateDocument)
    return document


def _project_file(path: Path, video: Path, **overrides: object) -> Project:

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


    def chosen(*_args: object, **_kwargs: object) -> tuple[str, str]:
        return path, ""

    return chosen


def _recording(seen: list[object]) -> Callable[..., QMessageBox.StandardButton]:







    def reply(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        seen.append(args)
        return QMessageBox.StandardButton.Ok

    return reply


def _history_texts(video: Path) -> list[str]:

    store = SnapshotStore(history_directory(project_path_for(video)))
    return [snapshot.text for snapshot in store.entries()]


def _save_as(monkeypatch: pytest.MonkeyPatch, window: MainWindow, path: Path) -> bool:

    monkeypatch.setattr(QFileDialog, "getSaveFileName", _choosing(str(path)))
    return window.save_project_as()


class TestRoundTrip:
    def test_a_project_reopens_as_the_document_it_was_saved_from(
        self, qtbot: QtBot, window: MainWindow, video: Path, tmp_path: Path
    ) -> None:






        path = tmp_path / "arena.sieve.yaml"
        _project_file(path, video)

        window.open_project(path)
        qtbot.waitUntil(lambda: len(_document(window)) == 2, timeout=OPEN_TIMEOUT_MS)

        document = _document(window)
        assert [replicate.name for replicate in document.all()] == ["Left", "Right"]
        assert document.at(1).overrides == {"n2": {"level": 0.75}}
        assert document.clip == ClipRange(start=5, end=25)
        assert document.pipeline == GRAPH


        assert document.equivalence_groups() == (1, 2)

    def test_saving_keeps_the_fields_the_gui_cannot_edit(
        self, qtbot: QtBot, window: MainWindow, video: Path, tmp_path: Path
    ) -> None:






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

        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        assert _save_as(monkeypatch, window, video.parent / "arena") is True
        assert project_path_for(video).is_file()


class TestLoadPath:


    def test_loading_leaves_no_history_and_nothing_to_save(
        self, document: ReplicateDocument
    ) -> None:

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

            (ClipRange(start=900, end=1200), ClipRange(start=900, end=1000)),


            (ClipRange(start=1500, end=1600), None),
        ],
    )
    def test_a_clip_is_trimmed_onto_the_source_actually_bound(
        self, document: ReplicateDocument, saved: ClipRange, expected: ClipRange | None
    ) -> None:

        document.load_project(
            Project.for_video(Path("arena.mp4")).model_copy(update={"clip": saved})
        )
        assert document.clip == expected

    def test_replicates_are_refitted_to_the_source_actually_bound(
        self, document: ReplicateDocument
    ) -> None:

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

    def test_closing_with_unsaved_edits_asks_nothing_and_keeps_the_edit(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:








        asked: list[object] = []
        monkeypatch.setattr(QMessageBox, "warning", _recording(asked))
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        assert window.close() is True
        assert asked == []
        assert _history_texts(video) == ["Add Replicate 1"]

    def test_closing_the_video_keeps_the_edit_it_dropped(
        self, qtbot: QtBot, window: MainWindow, video: Path
    ) -> None:








        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        window.close_video()

        assert _history_texts(video) == ["Add Replicate 1"]
        assert len(_document(window)) == 0

    def test_opening_another_video_over_unsaved_edits_asks_nothing(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:






        asked: list[object] = []
        monkeypatch.setattr(QMessageBox, "warning", _recording(asked))
        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", _choosing(""))

        window.open_video_dialog()

        assert asked == []

    def test_backing_out_of_the_save_dialog_writes_nothing(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:






        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", _choosing(""))

        assert window.save_project_as() is False
        assert window.isWindowModified() is True
        assert not project_path_for(video).exists()


class TestNeighbourOpen:
    def test_opening_a_video_opens_the_project_filed_beside_it_without_asking(
        self, qtbot: QtBot, window: MainWindow, video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

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

        _open(qtbot, window, video)
        _document(window).add_roi(ROI(x=1, y=1, width=20, height=20))

        orphan = tmp_path / "moved.sieve.yaml"
        _project_file(orphan, tmp_path / "on-the-nas.mp4")
        window.open_project(orphan)

        assert len(_document(window)) == 1
        assert window.windowTitle() != "SIEVE"
