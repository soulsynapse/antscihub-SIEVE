"""What the window looks like before the user has done anything.

Two of the three edits here can fail without saying so. A remembered video
whose file has since moved could put an error dialog in front of a user who has
not clicked anything yet, and the top-level split could silently drift off 50/50
under a stretch factor or a size hint. Both are tested. That the window comes up
maximized is not: `setWindowState` either took or the platform refused it, and a
test asserting the flag would only restate the line that sets it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QSlider, QTabWidget
from pytestqt.qtbot import QtBot

from sieve.gui.document import ReplicateDocument
from sieve.gui.main_window import MainWindow
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.timeline_bar import TimelineStrip
from sieve.gui.video_view import VideoView

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000

#: Splitter handles take pixels from the panes, and Qt rounds an odd remainder
#: toward one side. Equal to within a handle's width is as equal as it gets.
WIDTH_TOLERANCE_PX = 12


@pytest.fixture
def preferences(qapp: object, tmp_path: Path) -> Preferences:
    """A store on a temporary INI file, never the developer's real one."""
    del qapp
    return Preferences(QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat))


@pytest.fixture
def window(qtbot: QtBot, preferences: Preferences) -> Iterator[MainWindow]:
    main = MainWindow(preferences)
    qtbot.addWidget(main)
    yield main
    main.close()


class TestRestoreLastVideo:
    def test_opening_a_video_records_it(
        self, qtbot: QtBot, window: MainWindow, preferences: Preferences, synthetic_video: Path
    ) -> None:
        window.open_video(synthetic_video)
        qtbot.waitUntil(lambda: window.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)

        assert preferences.last_video == synthetic_video

    def test_a_remembered_video_is_reopened(
        self, qtbot: QtBot, window: MainWindow, preferences: Preferences, synthetic_video: Path
    ) -> None:
        preferences.last_video = synthetic_video

        assert window.restore_last_video() is True
        qtbot.waitUntil(lambda: window.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)

    def test_nothing_remembered_leaves_the_window_empty(self, window: MainWindow) -> None:
        assert window.restore_last_video() is False
        assert window.windowTitle() == "SIEVE"

    def test_a_remembered_video_that_is_gone_leaves_the_window_empty(
        self, window: MainWindow, preferences: Preferences, tmp_path: Path
    ) -> None:
        """The failure this test exists for is a warning dialog at launch: the
        file is gone, the player reports the failure, and the user is asked to
        acknowledge something they never asked for."""
        preferences.last_video = tmp_path / "moved-to-the-nas.mp4"

        assert window.restore_last_video() is False
        assert window.windowTitle() == "SIEVE"
        assert "Open a video to begin" in window.statusBar().currentMessage()


class TestTopSplit:
    def test_the_player_and_the_tool_pane_get_equal_widths(
        self, qtbot: QtBot, document: ReplicateDocument
    ) -> None:
        player = VideoPlayer()
        tab = ReplicateTab(player, document)
        qtbot.addWidget(tab)
        tab.resize(1200, 900)
        with qtbot.waitExposed(tab):
            tab.show()

        left, right = tab.top_splitter.sizes()
        assert abs(left - right) <= WIDTH_TOLERANCE_PX
        assert left > 0

        player.shutdown()

    def test_the_left_pane_is_the_picture_and_nothing_else(
        self, qtbot: QtBot, document: ReplicateDocument
    ) -> None:
        """No transport inside the tab, in either pane.

        The seeker is one band across the bottom of the window now
        (`gui/timeline_bar.py`). A tab that kept its own would answer "where am
        I" once per tab, and the copies drift the first time one is moved
        without the other.
        """
        player = VideoPlayer()
        tab = ReplicateTab(player, document)
        qtbot.addWidget(tab)

        assert tab.findChild(QSlider) is None
        assert tab.findChild(TimelineStrip) is None

        player_pane = tab.top_splitter.widget(0)
        assert player_pane is not None
        assert player_pane.findChild(VideoView) is not None

        player.shutdown()

    def test_the_timeline_is_below_the_tabs_and_outside_them(
        self, qtbot: QtBot, window: MainWindow
    ) -> None:
        """One band, parented to the window, under every tab rather than in one."""
        window.resize(1200, 900)
        with qtbot.waitExposed(window):
            window.show()

        tabs = window.findChild(QTabWidget)
        strip = window.findChild(TimelineStrip)
        assert tabs is not None
        assert strip is not None
        assert not tabs.isAncestorOf(strip)

        tabs_bottom = tabs.mapTo(window, tabs.rect().bottomLeft()).y()
        strip_top = strip.mapTo(window, strip.rect().topLeft()).y()
        assert strip_top >= tabs_bottom
