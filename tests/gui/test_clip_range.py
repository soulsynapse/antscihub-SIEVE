"""The representative clip: mark rules, undo, and where the band is painted.

Three things can be wrong here and each is tested for its own reason. The mark
rules can produce the wrong span — including one that `ClipRange` refuses to
construct at all, which is a crash on a keystroke. The undo path can lose the
absence of a clip, which is the state a user returns to by clearing. And the
strip can paint a band that does not line up with the handle the user marked
at, which makes the one visible readout of the clip a lie.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QStyle, QStyleOptionSlider
from pytestqt.qtbot import QtBot

from sieve.core.pipeline_model import ClipRange
from sieve.gui.clip_bar import ClipSlider, ClipStrip
from sieve.gui.document import ReplicateDocument
from sieve.gui.main_window import MainWindow
from sieve.gui.preferences import Preferences
from tests.conftest import FIXTURE_FRAMES
from tests.gui.conftest import SOURCE_FRAMES

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000

MARK_IN_ACTION = "Mark Clip &In"
CLEAR_CLIP_ACTION = "&Clear Clip"


class TestMarkRules:
    def test_an_in_point_alone_runs_to_the_end_of_the_source(
        self, document: ReplicateDocument
    ) -> None:
        document.mark_clip_in(400)
        assert document.clip == ClipRange(start=400, end=SOURCE_FRAMES)

    def test_an_out_point_includes_the_frame_it_was_marked_on(
        self, document: ReplicateDocument
    ) -> None:
        """The user marks out on the last frame they want; the range is half-open."""
        document.mark_clip_in(400)
        document.mark_clip_out(500)
        assert document.clip == ClipRange(start=400, end=501)

    def test_marking_in_past_the_out_point_releases_the_out_point(
        self, document: ReplicateDocument
    ) -> None:
        document.mark_clip_in(100)
        document.mark_clip_out(199)
        document.mark_clip_in(500)
        assert document.clip == ClipRange(start=500, end=SOURCE_FRAMES)

    def test_marking_out_before_the_in_point_releases_the_in_point(
        self, document: ReplicateDocument
    ) -> None:
        document.mark_clip_in(100)
        document.mark_clip_out(199)
        document.mark_clip_out(50)
        assert document.clip == ClipRange(start=0, end=51)

    def test_marking_out_on_the_in_point_leaves_a_single_frame(
        self, document: ReplicateDocument
    ) -> None:
        """The boundary the rule above exists for: `end == start` cannot be built."""
        document.mark_clip_in(100)
        document.mark_clip_out(100)
        assert document.clip == ClipRange(start=100, end=101)

    @pytest.mark.parametrize(
        ("frame", "expected"),
        [(-5, ClipRange(start=0, end=SOURCE_FRAMES)), (9999, ClipRange(start=999, end=1000))],
    )
    def test_marks_are_clamped_to_the_source(
        self, document: ReplicateDocument, frame: int, expected: ClipRange
    ) -> None:
        document.mark_clip_in(frame)
        assert document.clip == expected

    def test_an_unbound_document_refuses_to_mark(self, document: ReplicateDocument) -> None:
        """No source means no frame count, and a mark clamped against nothing."""
        document.unbind_source()
        document.mark_clip_in(10)
        document.mark_clip_out(20)
        assert document.clip is None
        assert not document.undo_stack.canUndo()

    def test_remarking_the_same_span_records_nothing(self, document: ReplicateDocument) -> None:
        document.mark_clip_in(400)
        before = document.undo_stack.count()
        document.mark_clip_in(400)
        document.clear_clip()
        document.clear_clip()
        assert document.undo_stack.count() == before + 1


class TestClipHistory:
    def test_undo_restores_the_previous_span(self, document: ReplicateDocument) -> None:
        document.mark_clip_in(100)
        document.mark_clip_out(199)
        document.undo_stack.undo()
        assert document.clip == ClipRange(start=100, end=SOURCE_FRAMES)

    def test_undoing_the_first_mark_restores_no_clip(self, document: ReplicateDocument) -> None:
        """The absence is a state, not a missing value the undo can skip."""
        document.mark_clip_in(100)
        document.undo_stack.undo()
        assert document.clip is None

    def test_clearing_is_undoable(self, document: ReplicateDocument) -> None:
        document.mark_clip_in(100)
        document.mark_clip_out(199)
        document.clear_clip()
        assert document.clip is None

        document.undo_stack.undo()
        assert document.clip == ClipRange(start=100, end=200)

    def test_binding_a_new_source_drops_the_clip_and_its_history(
        self, document: ReplicateDocument
    ) -> None:
        """Frame 400 of another video is another moment, or none at all."""
        document.mark_clip_in(400)
        document.bind_source(640, 480, 60)
        assert document.clip is None
        assert not document.undo_stack.canUndo()

    def test_every_change_announces_itself(self, document: ReplicateDocument) -> None:
        changes: list[None] = []
        document.clip_changed.connect(lambda: changes.append(None))

        document.mark_clip_in(100)
        document.clear_clip()
        document.undo_stack.undo()

        assert len(changes) == 3

    def test_command_text_names_the_edit(self, document: ReplicateDocument) -> None:
        document.mark_clip_in(100)
        assert document.undo_stack.undoText() == "Set Clip In"
        document.mark_clip_out(199)
        assert document.undo_stack.undoText() == "Set Clip Out"
        document.clear_clip()
        assert document.undo_stack.undoText() == "Clear Clip"


class TestClipStrip:
    @pytest.fixture
    def bar(self, qtbot: QtBot) -> tuple[ClipSlider, ClipStrip]:
        """A slider over a 1000-frame source and the strip that reads it."""
        slider = ClipSlider()
        slider.setRange(0, SOURCE_FRAMES - 1)
        strip = ClipStrip(slider)
        qtbot.addWidget(slider)
        qtbot.addWidget(strip)
        slider.resize(400, 20)
        strip.resize(400, strip.height())
        return slider, strip

    @pytest.mark.parametrize("frame", [0, 1, 500, 999])
    def test_a_frame_maps_to_where_the_handle_parks_on_it(
        self, bar: tuple[ClipSlider, ClipStrip], frame: int
    ) -> None:
        """The claim the whole strip rests on.

        A naive `groove.x() + fraction * groove.width()` passes in the middle
        and is off by half a handle at both ends — which is exactly where a
        user marking the first or last frame of a video is looking.
        """
        slider, _ = bar
        slider.setValue(frame)
        option = QStyleOptionSlider()
        slider.initStyleOption(option)
        handle = slider.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, slider
        )
        assert abs(handle.center().x() - slider.x_of_frame(frame)) <= 1.0

    def test_the_band_covers_the_span_it_was_given(self, bar: tuple[ClipSlider, ClipStrip]) -> None:
        slider, strip = bar
        strip.set_clip(ClipRange(start=250, end=751))
        band = strip.band_rect()
        assert band.left() == pytest.approx(slider.x_of_frame(250))
        assert band.right() == pytest.approx(slider.x_of_frame(750))

    def test_no_clip_and_no_range_paint_nothing(self, qtbot: QtBot) -> None:
        """The empty states are the ones reached on startup and on close."""
        slider = ClipSlider()
        slider.setRange(0, 0)
        strip = ClipStrip(slider)
        qtbot.addWidget(slider)
        qtbot.addWidget(strip)
        assert strip.band_rect().isEmpty()

        strip.set_clip(ClipRange(start=0, end=1))
        assert strip.band_rect().isEmpty()


class TestWindowWiring:
    @pytest.fixture
    def window(self, qtbot: QtBot, tmp_path: Path, synthetic_video: Path) -> Iterator[MainWindow]:
        settings = QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat)
        main = MainWindow(Preferences(settings))
        qtbot.addWidget(main)
        main.show()
        main.open_video(synthetic_video)
        qtbot.waitUntil(lambda: main.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)
        yield main
        main.close()

    def _action(self, window: MainWindow, text: str) -> QAction:
        matches = [action for action in window.findChildren(QAction) if action.text() == text]
        assert len(matches) == 1, f"no unique action titled {text!r}"
        return matches[0]

    def test_marking_in_runs_to_the_length_the_window_bound(self, window: MainWindow) -> None:
        """The source length has to reach the document for any mark to be legal."""
        document = window.findChild(ReplicateDocument)
        assert isinstance(document, ReplicateDocument)

        self._action(window, MARK_IN_ACTION).trigger()

        assert document.clip == ClipRange(start=0, end=FIXTURE_FRAMES)

    def test_clearing_only_offers_itself_once_there_is_a_clip(self, window: MainWindow) -> None:
        clear = self._action(window, CLEAR_CLIP_ACTION)
        assert not clear.isEnabled()

        self._action(window, MARK_IN_ACTION).trigger()
        assert clear.isEnabled()

        clear.trigger()
        assert not clear.isEnabled()
