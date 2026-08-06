"""The timeline: the working window, the band that paints it, and the scrub.

Four things can be wrong here and each is tested for its own reason. The window
rules can lose the length the user chose, which is the failure origin-plus-
length exists to prevent and the one two independent marks could not avoid. The
undo path can lose the *absence* of a chosen clip, which is what a saved project
carries and what makes `plan.py` run the whole video. The strip can paint a band
that does not line up with the frames it names, which makes the one visible
readout of the window a lie. And the three mouse events can collapse into one
another, which is either a drag that decodes every pixel or a release that
leaves the user a frame or two from where they let go.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, QSettings
from PySide6.QtGui import QAction
from pytestqt.qtbot import QtBot

from sieve.core.clip_window import DEFAULT_WINDOW_SECONDS
from sieve.core.pipeline_model import ClipRange
from sieve.gui.document import ReplicateDocument
from sieve.gui.main_window import MainWindow
from sieve.gui.preferences import Preferences
from sieve.gui.timeline.bar import TimelineBar, TimelineStrip
from sieve.gui.transport.player import VideoPlayer
from tests.conftest import FIXTURE_FRAMES
from tests.gui import qt_input
from tests.gui.conftest import SOURCE_FPS, SOURCE_FRAMES

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000
FRAME_TIMEOUT_MS = 5_000

MARK_IN_ACTION = "Mark Clip &In"
MARK_OUT_ACTION = "Mark Clip &Out"
CLEAR_CLIP_ACTION = "&Clear Clip"

#: What the `document` fixture opens with: ten seconds at 30 fps.
DEFAULT_WINDOW = ClipRange(start=0, end=300)

#: Width the strip is resized to in these tests. As wide as the source is long,
#: so every frame owns exactly one column and a click can name any of them.
STRIP_WIDTH = 1000

#: A y inside the track but *below* the window's header band, so a press there
#: is a scrub. Named because the difference between this and `HEADER_Y` is the
#: whole distinction between seeking and grabbing the window.
SCRUB_Y = 30.0

#: A y inside the header band along the window's top edge.
HEADER_Y = 8.0


class TestTheWindowIsAlwaysThere:
    def test_a_bound_document_has_a_window_before_anything_is_marked(
        self, document: ReplicateDocument
    ) -> None:
        assert document.window == DEFAULT_WINDOW

    def test_but_has_chosen_no_clip(self, document: ReplicateDocument) -> None:
        """The distinction the whole fallback exists to preserve.

        `Project.clip = None` is what makes `plan.py` run the whole video and
        what the HPC handoff produces by dropping the field. A GUI that resolved
        the default into the document on open would make it unreachable.
        """
        assert document.clip is None
        assert not document.undo_stack.canUndo()

    def test_an_unbound_document_has_no_window(self, document: ReplicateDocument) -> None:
        document.unbind_source()
        assert document.window is None

    def test_a_source_shorter_than_the_default_is_the_window(
        self, document: ReplicateDocument
    ) -> None:
        document.bind_source(640, 480, 60, SOURCE_FPS)
        assert document.window == ClipRange(start=0, end=60)


class TestTheWindowKeepsItsLength:
    def test_moving_the_window_carries_its_length(self, document: ReplicateDocument) -> None:
        document.move_window_to(400)
        assert document.clip == ClipRange(start=400, end=700)

    def test_a_window_moved_past_the_end_rests_against_it_at_full_length(
        self, document: ReplicateDocument
    ) -> None:
        """The gesture is "keep my ten seconds, put them here".

        Two independent marks would silently shorten the span, and the user's
        only way to notice is to read the length back.
        """
        document.move_window_to(900)
        assert document.clip == ClipRange(start=700, end=SOURCE_FRAMES)

    def test_ending_the_window_resizes_it(self, document: ReplicateDocument) -> None:
        document.move_window_to(400)
        document.end_window_at(499)
        assert document.clip == ClipRange(start=400, end=500)

    def test_an_end_before_the_start_releases_the_start(self, document: ReplicateDocument) -> None:
        document.move_window_to(400)
        document.end_window_at(50)
        assert document.clip == ClipRange(start=0, end=51)

    def test_a_typed_length_keeps_the_origin(self, document: ReplicateDocument) -> None:
        document.move_window_to(400)
        document.set_window_length(100)
        assert document.clip == ClipRange(start=400, end=500)

    def test_a_length_that_will_not_fit_slides_the_origin_back(
        self, document: ReplicateDocument
    ) -> None:
        """The length is what the user typed; the origin is what they did not."""
        document.move_window_to(900)
        document.set_window_length(600)
        assert document.clip == ClipRange(start=400, end=SOURCE_FRAMES)

    def test_bringing_a_frame_inside_moves_nothing(self, document: ReplicateDocument) -> None:
        document.move_window_to(400)
        before = document.undo_stack.count()
        document.bring_window_to(500)
        assert document.clip == ClipRange(start=400, end=700)
        assert document.undo_stack.count() == before

    def test_bringing_a_frame_outside_moves_the_least_it_can(
        self, document: ReplicateDocument
    ) -> None:
        document.move_window_to(400)
        document.bring_window_to(800)
        assert document.clip == ClipRange(start=501, end=801)

    def test_marks_are_clamped_to_the_source(self, document: ReplicateDocument) -> None:
        document.move_window_to(-50)
        assert document.clip == DEFAULT_WINDOW

    def test_an_unbound_document_refuses_to_mark(self, document: ReplicateDocument) -> None:
        """No source means no window, and a mark clamped against nothing."""
        document.unbind_source()
        document.move_window_to(10)
        document.end_window_at(20)
        document.set_window_length(5)
        assert document.clip is None
        assert not document.undo_stack.canUndo()

    def test_remarking_the_same_span_records_nothing(self, document: ReplicateDocument) -> None:
        document.move_window_to(400)
        before = document.undo_stack.count()
        document.move_window_to(400)
        document.clear_clip()
        document.clear_clip()
        assert document.undo_stack.count() == before + 1


class TestWindowHistory:
    def test_undo_restores_the_previous_span(self, document: ReplicateDocument) -> None:
        document.move_window_to(100)
        document.end_window_at(199)
        document.undo_stack.undo()
        assert document.clip == ClipRange(start=100, end=400)

    def test_undoing_the_first_mark_restores_no_choice(self, document: ReplicateDocument) -> None:
        """The absence is a state, not a missing value the undo can skip."""
        document.move_window_to(100)
        document.undo_stack.undo()
        assert document.clip is None
        assert document.window == DEFAULT_WINDOW

    def test_clearing_returns_the_window_to_the_default(self, document: ReplicateDocument) -> None:
        document.move_window_to(100)
        document.end_window_at(199)
        document.clear_clip()
        assert document.clip is None
        assert document.window == DEFAULT_WINDOW

        document.undo_stack.undo()
        assert document.clip == ClipRange(start=100, end=200)

    def test_binding_a_new_source_drops_the_clip_and_its_history(
        self, document: ReplicateDocument
    ) -> None:
        """Frame 400 of another video is another moment, or none at all."""
        document.move_window_to(400)
        document.bind_source(640, 480, 60, SOURCE_FPS)
        assert document.clip is None
        assert not document.undo_stack.canUndo()

    def test_every_change_announces_itself(self, document: ReplicateDocument) -> None:
        changes: list[None] = []
        document.clip_changed.connect(lambda: changes.append(None))

        document.move_window_to(100)
        document.clear_clip()
        document.undo_stack.undo()

        assert len(changes) == 3

    def test_command_text_names_the_edit(self, document: ReplicateDocument) -> None:
        document.move_window_to(100)
        assert document.undo_stack.undoText() == "Move Window"
        document.end_window_at(199)
        assert document.undo_stack.undoText() == "Set Window End"
        document.set_window_length(50)
        assert document.undo_stack.undoText() == "Set Window Length"
        document.clear_clip()
        assert document.undo_stack.undoText() == "Clear Clip"


class TestTheStrip:
    @pytest.fixture
    def strip(self, qtbot: QtBot) -> TimelineStrip:
        """A band 1000 px wide over a 1000-frame source: one column per frame."""
        band = TimelineStrip()
        qtbot.addWidget(band)
        band.resize(STRIP_WIDTH, band.height())
        band.set_source_frames(SOURCE_FRAMES)
        band.set_timebase(float(SOURCE_FPS))
        return band

    def test_the_band_covers_the_span_it_was_given(self, strip: TimelineStrip) -> None:
        strip.set_window(ClipRange(start=250, end=750))
        rect = strip.window_rect()
        assert rect.left() == pytest.approx(250.0)
        # `end` and not `end - 1`: the window runs up to the start of the frame
        # after its last, so the band's right edge lands on that boundary.
        assert rect.right() == pytest.approx(750.0)

    def test_the_playhead_sits_in_the_column_it_names(self, strip: TimelineStrip) -> None:
        strip.set_playhead(500)
        assert strip.playhead_x() == pytest.approx(500.5)

    def test_nothing_is_painted_without_a_source(self, qtbot: QtBot) -> None:
        """The state on startup and after closing a video, hit by every paint."""
        band = TimelineStrip()
        qtbot.addWidget(band)
        band.resize(STRIP_WIDTH, band.height())
        band.set_window(ClipRange(start=0, end=10))
        assert band.window_rect().isEmpty()

    def test_press_move_and_release_are_three_claims(self, strip: TimelineStrip) -> None:
        """Collapsing any two either decodes every pixel or lands short.

        A drag that only emitted its release would show nothing while it moved;
        one that only emitted moves would leave the user wherever the coalescer
        happened to stop.
        """
        pressed: list[int] = []
        scrubbed: list[int] = []
        committed: list[int] = []
        strip.pressed.connect(pressed.append)
        strip.scrubbed.connect(scrubbed.append)
        strip.committed.connect(committed.append)

        qt_input.press(strip, QPointF(100.0, 10.0))
        qt_input.move(strip, QPointF(300.0, 10.0))
        qt_input.move(strip, QPointF(600.0, 10.0))
        qt_input.release(strip, QPointF(700.0, 10.0))

        assert pressed == [100]
        assert scrubbed == [300, 600]
        assert committed == [700]

    def test_a_move_without_a_press_says_nothing(self, strip: TimelineStrip) -> None:
        """The cursor crossing the band on its way elsewhere is not a scrub."""
        scrubbed: list[int] = []
        strip.scrubbed.connect(scrubbed.append)
        qt_input.move(strip, QPointF(300.0, 10.0))
        assert scrubbed == []

    def test_a_drag_off_the_end_still_names_a_real_frame(self, strip: TimelineStrip) -> None:
        """The mouse keeps arriving after it leaves the widget."""
        committed: list[int] = []
        strip.committed.connect(committed.append)
        qt_input.drag(strip, QPointF(500.0, 10.0), QPointF(4000.0, 10.0))
        assert committed == [SOURCE_FRAMES - 1]


class TestTheBarDrivesTheWindow:
    @pytest.fixture
    def bar(self, qtbot: QtBot, document: ReplicateDocument) -> Iterator[TimelineBar]:
        """A bar over the 1000-frame document, with a player that has no video.

        The player is real and unopened: everything under test here is the
        window and the strip, and a decode thread with a file in it would make
        the assertions wait on frames nobody is looking at.
        """
        player = VideoPlayer()
        widget = TimelineBar(player, document)
        qtbot.addWidget(widget)
        widget.strip.resize(STRIP_WIDTH, widget.strip.height())
        yield widget
        player.shutdown()

    def test_a_click_inside_the_window_leaves_it_alone(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        document.move_window_to(400)
        before = document.undo_stack.count()
        qt_input.click(bar.strip, QPointF(500.0, SCRUB_Y))
        assert document.clip == ClipRange(start=400, end=700)
        assert document.undo_stack.count() == before

    def test_a_click_outside_the_window_brings_it_over(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        document.move_window_to(400)
        qt_input.click(bar.strip, QPointF(900.0, SCRUB_Y))
        assert document.clip == ClipRange(start=601, end=901)

    def test_the_strip_repaints_from_the_document(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        """The band follows an edit made anywhere, including an undo."""
        document.move_window_to(400)
        assert bar.strip.window_rect().left() == pytest.approx(400.0)
        document.undo_stack.undo()
        assert bar.strip.window_rect().left() == pytest.approx(0.0)


class TestTheWindowBracketIsGrabbable:
    """The drag, and the four ways it can be wrong.

    A press on a handle can seek before it resizes, which throws the playhead
    across the asset on the way to a resize. Containment can be tested before
    the handles, which makes the handles unreachable. A drag can write per
    mouse-move, which is one undo entry per pixel travelled. And it can commit a
    window shorter than anything anybody tunes against.
    """

    @pytest.fixture
    def bar(self, qtbot: QtBot, document: ReplicateDocument) -> Iterator[TimelineBar]:
        """The bar over a window at frames 400-700: left edge at x=400, right at x=700."""
        player = VideoPlayer()
        widget = TimelineBar(player, document)
        qtbot.addWidget(widget)
        widget.strip.resize(STRIP_WIDTH, widget.strip.height())
        document.move_window_to(400)
        yield widget
        player.shutdown()

    def test_a_press_on_an_edge_does_not_seek(self, bar: TimelineBar) -> None:
        """`pressed` is the seek, so classifying after emitting is already too late.

        The failure is visible rather than subtle: reaching for the left handle
        would throw the playhead to the window's start before the resize began.
        """
        sought: list[int] = []
        bar.strip.pressed.connect(sought.append)
        qt_input.press(bar.strip, QPointF(400.0, SCRUB_Y))
        assert sought == []

    def test_an_edge_wins_over_the_body_it_sits_in(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        """A point on the edge is inside the window too — the edge is tested first."""
        qt_input.drag(bar.strip, QPointF(400.0, SCRUB_Y), QPointF(250.0, SCRUB_Y))
        assert document.clip == ClipRange(start=250, end=700)

    def test_the_right_handle_resizes_and_pins_the_start(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        qt_input.drag(bar.strip, QPointF(700.0, SCRUB_Y), QPointF(899.0, SCRUB_Y))
        assert document.clip == ClipRange(start=400, end=900)

    def test_the_header_moves_the_window_whole(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        """Length held: this is the same edit as typing a new start."""
        qt_input.drag(bar.strip, QPointF(500.0, HEADER_Y), QPointF(600.0, HEADER_Y))
        assert document.clip == ClipRange(start=500, end=800)

    def test_a_press_below_the_header_is_still_a_scrub(self, bar: TimelineBar) -> None:
        """Most of the window's area is not a handle, or the band could not be seeked."""
        sought: list[int] = []
        bar.strip.pressed.connect(sought.append)
        qt_input.press(bar.strip, QPointF(500.0, SCRUB_Y))
        assert sought == [500]

    def test_a_drag_shorter_than_a_second_stops_at_a_second(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        """Thirty frames at 30 fps. The floor is a duration, not a frame count."""
        qt_input.drag(bar.strip, QPointF(700.0, SCRUB_Y), QPointF(405.0, SCRUB_Y))
        assert document.clip == ClipRange(start=400, end=430)

    def test_one_drag_is_one_undo_entry(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        """`SetClip` has no `mergeWith`: a write per move is a shredded history."""
        before = document.undo_stack.count()
        qt_input.press(bar.strip, QPointF(700.0, SCRUB_Y))
        for x in (720.0, 760.0, 800.0, 850.0):
            qt_input.move(bar.strip, QPointF(x, SCRUB_Y))
        assert document.undo_stack.count() == before
        qt_input.release(bar.strip, QPointF(899.0, SCRUB_Y))

        assert document.undo_stack.count() == before + 1
        document.undo_stack.undo()
        assert document.clip == ClipRange(start=400, end=700)

    def test_the_bracket_follows_the_drag_before_it_is_written(
        self, bar: TimelineBar, document: ReplicateDocument
    ) -> None:
        """The outline is local, and the document is untouched until release."""
        qt_input.press(bar.strip, QPointF(400.0, SCRUB_Y))
        qt_input.move(bar.strip, QPointF(250.0, SCRUB_Y))

        assert bar.strip.window_rect().left() == pytest.approx(250.0)
        assert document.clip == ClipRange(start=400, end=700)

    def test_the_bracket_and_the_boxes_agree_afterwards(self, bar: TimelineBar) -> None:
        """The lockstep claim, checked on the numbers actually on screen."""
        qt_input.drag(bar.strip, QPointF(700.0, SCRUB_Y), QPointF(899.0, SCRUB_Y))
        start_seconds, length_seconds = bar.window_seconds
        assert start_seconds == pytest.approx(400.0 / SOURCE_FPS, abs=0.01)
        assert length_seconds == pytest.approx(500.0 / SOURCE_FPS, abs=0.01)
        assert bar.strip.window_rect().left() == pytest.approx(400.0)
        assert bar.strip.window_rect().right() == pytest.approx(900.0)


class TestTheHoverBubble:
    @pytest.fixture
    def strip(self, qtbot: QtBot) -> TimelineStrip:
        band = TimelineStrip()
        qtbot.addWidget(band)
        band.resize(STRIP_WIDTH, band.height())
        band.set_source_frames(SOURCE_FRAMES)
        band.set_timebase(float(SOURCE_FPS))
        return band

    def test_it_names_the_frame_under_the_cursor_in_both_units(self, strip: TimelineStrip) -> None:
        qt_input.move(strip, QPointF(300.5, SCRUB_Y))
        assert strip.hover_frame == 300
        assert strip.bubble_text() == "0:10.000   frame 300"

    def test_it_appears_without_a_button_held(self, strip: TimelineStrip) -> None:
        """The widget hears an unpressed move only because it tracks the mouse."""
        assert strip.bubble_rect().isEmpty()
        qt_input.move(strip, QPointF(300.5, SCRUB_Y))
        assert not strip.bubble_rect().isEmpty()

    @pytest.mark.parametrize("x", [1.0, 999.0])
    def test_it_stays_inside_the_widget_at_either_end(self, strip: TimelineStrip, x: float) -> None:
        """Otherwise the readout runs off the edge exactly where the user is marking."""
        qt_input.move(strip, QPointF(x, SCRUB_Y))
        box = strip.bubble_rect()
        assert box.left() >= 0.0
        assert box.right() <= float(STRIP_WIDTH)

    def test_it_clears_when_the_cursor_leaves(self, strip: TimelineStrip) -> None:
        """A bubble left behind is a claim about where a cursor that has gone is."""
        qt_input.move(strip, QPointF(300.5, SCRUB_Y))
        qt_input.leave(strip)
        assert strip.hover_frame is None
        assert strip.bubble_rect().isEmpty()

    def test_without_a_timebase_it_says_only_what_it_knows(self, qtbot: QtBot) -> None:
        """No fps means no second, and a guessed timecode is worse than none."""
        band = TimelineStrip()
        qtbot.addWidget(band)
        band.resize(STRIP_WIDTH, band.height())
        band.set_source_frames(SOURCE_FRAMES)
        qt_input.move(band, QPointF(300.5, SCRUB_Y))
        assert band.bubble_text() == "frame 300"


class TestPlaybackIsBounded:
    @pytest.fixture
    def player(self, qtbot: QtBot, synthetic_video: Path) -> Iterator[VideoPlayer]:
        video = VideoPlayer()
        with qtbot.waitSignal(video.opened, timeout=OPEN_TIMEOUT_MS):
            video.open(str(synthetic_video))
        yield video
        video.shutdown()

    def _lands_on(self, qtbot: QtBot, player: VideoPlayer, index: int) -> None:
        """Wait for the frame to arrive. The position is only real once it has.

        `current_index` is set when a decode comes back, not when a seek is
        asked for, so asserting straight after the call reads the previous
        position and passes for the wrong reason.
        """
        qtbot.waitUntil(lambda: player.current_index == index, timeout=FRAME_TIMEOUT_MS)

    def test_a_seek_outside_the_window_lands_on_its_edge(
        self, qtbot: QtBot, player: VideoPlayer
    ) -> None:
        """`seek` is how every caller reaches a frame, so it is where this holds."""
        player.set_window(ClipRange(start=10, end=20))
        player.seek(35)
        self._lands_on(qtbot, player, 19)
        player.seek(0)
        self._lands_on(qtbot, player, 10)

    def test_moving_the_window_pulls_the_playhead_in(
        self, qtbot: QtBot, player: VideoPlayer
    ) -> None:
        """A window moved out from under the playhead would strand the viewport."""
        player.seek(FIXTURE_FRAMES - 1)
        self._lands_on(qtbot, player, FIXTURE_FRAMES - 1)
        player.set_window(ClipRange(start=0, end=5))
        self._lands_on(qtbot, player, 4)

    def test_no_window_is_the_whole_asset(self, qtbot: QtBot, player: VideoPlayer) -> None:
        player.set_window(None)
        player.seek(999)
        self._lands_on(qtbot, player, FIXTURE_FRAMES - 1)


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

    def _document(self, window: MainWindow) -> ReplicateDocument:
        document = window.findChild(ReplicateDocument)
        assert isinstance(document, ReplicateDocument)
        return document

    def test_the_window_opens_with_a_span_over_the_whole_short_source(
        self, window: MainWindow
    ) -> None:
        """Two seconds of fixture is shorter than the ten-second default.

        This is also the check that the source's length and frame rate reach
        the document at all: without them there is no window to fall back to.
        """
        assert self._document(window).window == ClipRange(start=0, end=FIXTURE_FRAMES)

    def test_marking_in_records_a_choice(self, window: MainWindow) -> None:
        document = self._document(window)
        assert document.clip is None

        self._action(window, MARK_IN_ACTION).trigger()

        assert document.clip == ClipRange(start=0, end=FIXTURE_FRAMES)

    def test_marking_out_at_the_playhead_shortens_the_window(self, window: MainWindow) -> None:
        self._action(window, MARK_OUT_ACTION).trigger()
        assert self._document(window).clip == ClipRange(start=0, end=1)

    def test_clearing_only_offers_itself_once_there_is_a_choice(self, window: MainWindow) -> None:
        clear = self._action(window, CLEAR_CLIP_ACTION)
        assert not clear.isEnabled()

        self._action(window, MARK_IN_ACTION).trigger()
        assert clear.isEnabled()

        clear.trigger()
        assert not clear.isEnabled()


class TestTheLengthOutlivesTheSession:
    """A window length set in one session is the one the next opens at.

    The length, not the span: the user tunes against a stretch of a fixed size
    and is asked to re-choose it on every launch otherwise. Where it lands is a
    property of the video and stays with the project; how long it is is a
    property of the person and follows them to the next file. Two sessions over
    one settings file is the only way to see that, because within a session the
    document holds the length anyway and would pass for the wrong reason.
    """

    #: One second at the fixture's 20 fps — not the shipped ten seconds and not
    #: the fixture's two, so a result equal to either names which fallback ran.
    REMEMBERED_FRAMES = 20

    @pytest.fixture
    def settings_file(self, tmp_path: Path) -> str:
        return str(tmp_path / "sieve.ini")

    @contextmanager
    def _session(
        self, qtbot: QtBot, settings_file: str, video: Path
    ) -> Generator[tuple[MainWindow, ReplicateDocument]]:
        """One launch of the application over `settings_file`, with `video` open."""
        main = MainWindow(Preferences(QSettings(settings_file, QSettings.Format.IniFormat)))
        qtbot.addWidget(main)
        try:
            main.open_video(video)
            qtbot.waitUntil(lambda: main.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)
            document = main.findChild(ReplicateDocument)
            assert isinstance(document, ReplicateDocument)
            yield main, document
        finally:
            main.close()

    def test_a_length_set_in_one_session_is_what_the_next_opens_at(
        self, qtbot: QtBot, settings_file: str, synthetic_video: Path
    ) -> None:
        with self._session(qtbot, settings_file, synthetic_video) as (_, document):
            document.set_window_length(self.REMEMBERED_FRAMES)
            assert document.window == ClipRange(start=0, end=self.REMEMBERED_FRAMES)

        with self._session(qtbot, settings_file, synthetic_video) as (_, reopened):
            assert reopened.window == ClipRange(start=0, end=self.REMEMBERED_FRAMES)
            # The *choice* did not come back with it. A remembered length that
            # arrived as a marked clip would make `Project.clip = None`
            # unreachable from a second launch, which is `plan.py`'s whole-video
            # fallback gone for anyone who has ever dragged the bracket.
            assert reopened.clip is None

    def test_the_fallback_itself_is_never_what_gets_remembered(
        self, qtbot: QtBot, settings_file: str, synthetic_video: Path
    ) -> None:
        """The fixture is shorter than ten seconds, so its fallback is the whole
        asset. Writing that back would teach every later session that two
        seconds is the length this user works in, on the strength of a video
        they never touched the window on."""
        with self._session(qtbot, settings_file, synthetic_video) as (window, _):
            assert window.preferences.window_seconds == pytest.approx(DEFAULT_WINDOW_SECONDS)
