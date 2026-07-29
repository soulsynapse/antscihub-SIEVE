










from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from pytestqt.qtbot import QtBot

from sieve.core.pipeline_model import Project, project_path_for
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.main_window import MainWindow
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000


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


def _player(window: MainWindow) -> VideoPlayer:
    player = window.findChild(VideoPlayer)
    assert isinstance(player, VideoPlayer)
    return player


def _document(window: MainWindow) -> ReplicateDocument:
    document = window.findChild(ReplicateDocument)
    assert isinstance(document, ReplicateDocument)
    return document


def test_opening_a_video_leaves_it_playing(qtbot: QtBot, window: MainWindow, video: Path) -> None:
    player = _player(window)
    assert player.is_playing is False

    window.open_video(video)

    qtbot.waitUntil(lambda: player.is_playing, timeout=OPEN_TIMEOUT_MS)


def test_playback_starts_after_the_document_is_bound(
    qtbot: QtBot, window: MainWindow, video: Path
) -> None:




    player = _player(window)
    document = _document(window)
    bound_when_started: list[tuple[int, int] | None] = []

    def record(playing: bool) -> None:
        if playing:
            bound_when_started.append(document.source_size)

    player.playing_changed.connect(record)

    window.open_video(video)
    qtbot.waitUntil(lambda: bool(bound_when_started), timeout=OPEN_TIMEOUT_MS)

    assert bound_when_started[0] is not None


def test_playback_waits_for_the_neighbour_project(
    qtbot: QtBot, window: MainWindow, video: Path
) -> None:







    neighbour = Project.for_video(video, video.parent).with_replicates(
        (Replicate(roi=ROI(x=0, y=0, width=40, height=30), name="Left", replicate_id="r1"),)
    )
    neighbour.save(project_path_for(video))
    player = _player(window)
    document = _document(window)
    restored_when_started: list[int] = []

    def record(playing: bool) -> None:
        if playing:
            restored_when_started.append(len(document))

    player.playing_changed.connect(record)

    window.open_video(video)
    qtbot.waitUntil(lambda: bool(restored_when_started), timeout=OPEN_TIMEOUT_MS)

    assert restored_when_started[0] == 1
