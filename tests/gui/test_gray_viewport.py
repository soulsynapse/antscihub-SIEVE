"""The gray viewport: the format flip, the frames it must not show, the policy.

Three claims, each failing for a distinct real reason:

**The flip changes what the decode thread produces, in place.** Driven through
the real thread against the synthetic video, like the scrub tests, because the
reopen is a cross-thread ordering (format change, then re-request) and a fake
decoder would test the fake's ordering.

**A frame decoded in the old format never lands in the new viewport.** The
same hazard as a source change — the decode in flight cannot be recalled — and
the same mechanism answers it, the coalescer's generation stamp. Shown or
cached, either is a colour frame in a gray pane.

**The toggle's policy is the decided one.** Manual persists; a window render
engages auto-gray; a click during the render pins colour for that render and
no longer; the effective answer is announced exactly when it changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.core.types import VideoMetadata
from sieve.gui.gray_toggle import GrayToggle
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 5000
FRAME_TIMEOUT_MS = 5000

GRAY = QImage.Format.Format_Grayscale8
BGR = QImage.Format.Format_BGR888


class FormatRecorder:
    """Every displayed frame, as (index, format), in display order."""

    def __init__(self, player: VideoPlayer) -> None:
        self.frames: list[tuple[int, QImage.Format]] = []
        player.frame_changed.connect(self._on_frame)

    def _on_frame(self, index: int, image: QImage) -> None:
        self.frames.append((index, image.format()))


def open_player(qtbot: QtBot, video: Path) -> tuple[VideoPlayer, FormatRecorder]:
    player = VideoPlayer()
    opened: list[VideoMetadata] = []
    player.opened.connect(opened.append)
    recorder = FormatRecorder(player)
    player.open(str(video))
    qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)
    qtbot.waitUntil(lambda: bool(recorder.frames), timeout=FRAME_TIMEOUT_MS)
    return player, recorder


class TestTheFlip:
    def test_the_frame_on_screen_is_redelivered_in_the_new_format(
        self, qtbot: QtBot, synthetic_video: Path
    ) -> None:
        """The playhead survives the reopen and the pane never blanks."""
        player, recorder = open_player(qtbot, synthetic_video)
        try:
            player.seek(7)
            qtbot.waitUntil(lambda: player.current_index == 7, timeout=FRAME_TIMEOUT_MS)
            assert recorder.frames[-1] == (7, BGR)

            player.set_viewport_luma(True)
            qtbot.waitUntil(lambda: recorder.frames[-1] == (7, GRAY), timeout=FRAME_TIMEOUT_MS)

            player.set_viewport_luma(False)
            qtbot.waitUntil(lambda: recorder.frames[-1] == (7, BGR), timeout=FRAME_TIMEOUT_MS)
        finally:
            player.shutdown()

    def test_a_frame_decoded_in_colour_is_not_shown_or_cached_after_the_flip(
        self, qtbot: QtBot, synthetic_video: Path
    ) -> None:
        """The decode in flight answers the format nobody is asking for any more.

        The seek and the flip land in one turn of the event loop, so the
        colour decode is guaranteed to still be in flight when the generation
        bumps — precisely the ordering that would paint colour into the gray
        pane without the stamp.
        """
        player, recorder = open_player(qtbot, synthetic_video)
        try:
            before = len(recorder.frames)
            player.seek(30)
            player.set_viewport_luma(True)

            qtbot.waitUntil(
                lambda: len(recorder.frames) > before and recorder.frames[-1][1] == GRAY,
                timeout=FRAME_TIMEOUT_MS,
            )
            qtbot.wait(300)
            assert all(fmt == GRAY for _, fmt in recorder.frames[before:]), (
                "a colour frame was painted after the flip"
            )

            # Nor cached: a hit would repaint synchronously, inside this call.
            shown = len(recorder.frames)
            player.scrub(30)
            assert not any(fmt == BGR for _, fmt in recorder.frames[shown:])
            qtbot.waitUntil(lambda: recorder.frames[-1] == (30, GRAY), timeout=FRAME_TIMEOUT_MS)
        finally:
            player.shutdown()


@pytest.fixture
def preferences(qapp: object, tmp_path: Path) -> Preferences:
    del qapp
    return Preferences(QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat))


class Announcements:
    def __init__(self, toggle: GrayToggle) -> None:
        self.values: list[bool] = []
        toggle.luma_changed.connect(self.values.append)


class TestTogglePolicy:
    def test_a_render_engages_gray_and_its_end_returns_colour(
        self, qtbot: QtBot, preferences: Preferences
    ) -> None:
        toggle = GrayToggle(preferences)
        qtbot.addWidget(toggle)
        heard = Announcements(toggle)

        toggle.set_rendering(True)
        assert toggle.effective_luma
        assert toggle.isChecked()

        toggle.set_rendering(False)
        assert not toggle.effective_luma
        assert heard.values == [True, False]

    def test_a_click_during_a_render_pins_colour_for_that_render_only(
        self, qtbot: QtBot, preferences: Preferences
    ) -> None:
        toggle = GrayToggle(preferences)
        qtbot.addWidget(toggle)

        toggle.set_rendering(True)
        toggle.click()
        assert not toggle.effective_luma, "the click did not pin colour"
        assert not preferences.viewport_luma, "a pin is not a preference"

        # The pin dies with the render: the next one engages auto-gray again.
        toggle.set_rendering(False)
        toggle.set_rendering(True)
        assert toggle.effective_luma

    def test_a_manual_click_persists_and_survives_a_new_store(
        self, qtbot: QtBot, preferences: Preferences
    ) -> None:
        toggle = GrayToggle(preferences)
        qtbot.addWidget(toggle)

        toggle.click()
        assert toggle.effective_luma
        assert preferences.viewport_luma

        again = GrayToggle(preferences)
        qtbot.addWidget(again)
        assert again.effective_luma, "the persisted preference was not read back"

        toggle.click()
        assert not preferences.viewport_luma

    def test_unchecking_during_a_render_means_colour_not_a_fallback_to_auto(
        self, qtbot: QtBot, preferences: Preferences
    ) -> None:
        """A click that visibly did nothing would be the worst reading."""
        toggle = GrayToggle(preferences)
        qtbot.addWidget(toggle)
        toggle.click()  # manual gray
        toggle.set_rendering(True)

        toggle.click()
        assert not toggle.effective_luma
        assert not preferences.viewport_luma
