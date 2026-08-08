"""The timeline: the working window, the band that paints it, and the scrub.

Four things can be wrong here and each is tested for its own reason. The window
rules can lose the length the user chose, which is the failure origin-plus-
length exists to prevent and the one two independent marks could not avoid. The
strip can paint a band that does not line up with the frames it names, which
makes the one visible readout of the window a lie. The three mouse events can
collapse into one another, which is either a drag that decodes every pixel or a
release that leaves the user a frame or two from where they let go. And the
transport can leave the window, which is what makes it a bound rather than a
decoration.

The undo half of v2's file is absent by decision, not by omission: the working
window is view state here, because schema v1 records no clip and what a run
covers is the `span` node's parameters. `docs/todo/` holds the table.

Qt and `sieve.gui` are imported inside the tests, for the reason `conftest.py`
gives; `driving.py` stands in for `qtbot` and says why there is none.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, SourceRef, SourceSpan
from tests.conftest import FIXTURE_FPS, FIXTURE_FRAMES
from tests.gui import driving

OPEN_TIMEOUT_MS = 15_000
FRAME_TIMEOUT_MS = 5_000

#: The synthetic axis these widget tests are laid out over. A thousand frames at
#: 30 fps, so a second is thirty frames and the arithmetic is readable.
SOURCE_FRAMES = 1000
SOURCE_FPS = 30.0

#: Width the strip is resized to. As wide as the source is long, so every frame
#: owns exactly one column and a click can name any of them.
STRIP_WIDTH = 1000

#: The window every bar fixture opens with: the whole source.
WHOLE = SourceSpan(start=0, end=SOURCE_FRAMES)

#: A y inside the track but *below* the window's header band, so a press there
#: is a scrub. Named because the difference between this and `HEADER_Y` is the
#: whole distinction between seeking and grabbing the window.
SCRUB_Y = 30.0

#: A y inside the header band along the window's top edge.
HEADER_Y = 8.0


@pytest.fixture
def bar(qapp) -> Iterator[Any]:
    """A bar over a 1000-frame axis, with a real player that has no video.

    The player is real and unopened: everything under test here is the window
    and the strip, and a decode thread with a file in it would make the
    assertions wait on frames nobody is looking at.
    """
    del qapp
    from sieve.gui.timeline.bar import TimelineBar
    from sieve.gui.transport.player import VideoPlayer

    player = VideoPlayer()
    widget = TimelineBar(player)
    widget.bind_source(SOURCE_FRAMES, SOURCE_FPS)
    widget.strip.resize(STRIP_WIDTH, widget.strip.height())
    yield widget
    player.shutdown()


@pytest.fixture
def strip(qapp) -> Any:
    """A band 1000 px wide over a 1000-frame source: one column per frame."""
    del qapp
    from sieve.gui.timeline.bar import TimelineStrip

    band = TimelineStrip()
    band.resize(STRIP_WIDTH, band.height())
    band.set_source_frames(SOURCE_FRAMES)
    band.set_timebase(SOURCE_FPS)
    return band


class TestTheWindowIsAlwaysThere:
    def test_a_bound_source_has_a_window_over_the_whole_of_it(self, bar: Any) -> None:
        """Not v2's ten seconds: no clip is saved, so nothing here proposes one."""
        assert bar.window == WHOLE

    def test_an_unbound_bar_has_no_window(self, bar: Any) -> None:
        bar.bind_source(0, 0.0)
        assert bar.window is None

    def test_an_unbound_bar_refuses_to_move_one(self, bar: Any) -> None:
        """No source means no window, and a mark clamped against nothing."""
        bar.bind_source(0, 0.0)
        bar.move_window_to(10)
        bar.set_window_length(5)
        assert bar.window is None


class TestTheWindowKeepsItsLength:
    def test_moving_the_window_carries_its_length(self, bar: Any) -> None:
        bar.set_window(SourceSpan(start=0, end=300))
        bar.move_window_to(400)
        assert bar.window == SourceSpan(start=400, end=700)

    def test_a_window_moved_past_the_end_rests_against_it_at_full_length(self, bar: Any) -> None:
        """The gesture is "keep my ten seconds, put them here".

        Two independent marks would silently shorten the span, and the user's
        only way to notice is to read the length back.
        """
        bar.set_window(SourceSpan(start=0, end=300))
        bar.move_window_to(900)
        assert bar.window == SourceSpan(start=700, end=SOURCE_FRAMES)

    def test_a_typed_length_keeps_the_origin(self, bar: Any) -> None:
        bar.set_window(SourceSpan(start=400, end=700))
        bar.set_window_length(100)
        assert bar.window == SourceSpan(start=400, end=500)

    def test_a_length_that_will_not_fit_slides_the_origin_back(self, bar: Any) -> None:
        """The length is what the user typed; the origin is what they did not."""
        bar.set_window(SourceSpan(start=700, end=1000))
        bar.set_window_length(600)
        assert bar.window == SourceSpan(start=400, end=SOURCE_FRAMES)

    def test_marks_are_clamped_to_the_source(self, bar: Any) -> None:
        bar.set_window(SourceSpan(start=0, end=300))
        bar.move_window_to(-50)
        assert bar.window == SourceSpan(start=0, end=300)


class TestTheStrip:
    def test_the_band_covers_the_span_it_was_given(self, strip: Any) -> None:
        strip.set_window(SourceSpan(start=250, end=750))
        rect = strip.window_rect()
        assert rect.left() == pytest.approx(250.0)
        # `end` and not `end - 1`: the window runs up to the start of the frame
        # after its last, so the band's right edge lands on that boundary.
        assert rect.right() == pytest.approx(750.0)

    def test_the_playhead_sits_in_the_column_it_names(self, strip: Any) -> None:
        strip.set_playhead(500)
        assert strip.playhead_x() == pytest.approx(500.5)

    def test_nothing_is_painted_without_a_source(self, qapp) -> None:
        """The state on startup and after closing a video, hit by every paint."""
        del qapp
        from sieve.gui.timeline.bar import TimelineStrip

        band = TimelineStrip()
        band.resize(STRIP_WIDTH, band.height())
        band.set_window(SourceSpan(start=0, end=10))
        assert band.window_rect().isEmpty()

    def test_press_move_and_release_are_three_claims(self, strip: Any) -> None:
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

        driving.press(strip, 100.0, 10.0)
        driving.move(strip, 300.0, 10.0)
        driving.move(strip, 600.0, 10.0)
        driving.release(strip, 700.0, 10.0)

        assert pressed == [100]
        assert scrubbed == [300, 600]
        assert committed == [700]

    def test_a_move_without_a_press_says_nothing(self, strip: Any) -> None:
        """The cursor crossing the band on its way elsewhere is not a scrub."""
        scrubbed: list[int] = []
        strip.scrubbed.connect(scrubbed.append)
        driving.move(strip, 300.0, 10.0)
        assert scrubbed == []

    def test_a_drag_off_the_end_still_names_a_real_frame(self, strip: Any) -> None:
        """The mouse keeps arriving after it leaves the widget."""
        committed: list[int] = []
        strip.committed.connect(committed.append)
        driving.drag(strip, (500.0, 10.0), (4000.0, 10.0))
        assert committed == [SOURCE_FRAMES - 1]


class TestTheBarDrivesTheWindow:
    def test_a_click_inside_the_window_leaves_it_alone(self, bar: Any) -> None:
        bar.set_window(SourceSpan(start=400, end=700))
        driving.click(bar.strip, 500.0, SCRUB_Y)
        assert bar.window == SourceSpan(start=400, end=700)

    def test_a_click_outside_the_window_brings_it_over(self, bar: Any) -> None:
        bar.set_window(SourceSpan(start=400, end=700))
        driving.click(bar.strip, 900.0, SCRUB_Y)
        assert bar.window == SourceSpan(start=601, end=901)

    def test_the_strip_repaints_from_the_bar(self, bar: Any) -> None:
        """The band follows an edit made anywhere, not only one made on it."""
        bar.set_window(SourceSpan(start=400, end=700))
        assert bar.strip.window_rect().left() == pytest.approx(400.0)
        bar.set_window(WHOLE)
        assert bar.strip.window_rect().left() == pytest.approx(0.0)

    def test_the_transport_is_told_once_and_from_here(self, bar: Any) -> None:
        """A transport bounded from two places is bounded by whichever spoke last."""
        bar.set_window(SourceSpan(start=400, end=700))
        assert bar.strip.shown_window == bar.window


class TestTheWindowBracketIsGrabbable:
    """The drag, and the four ways it can be wrong.

    A press on a handle can seek before it resizes, which throws the playhead
    across the asset on the way to a resize. Containment can be tested before
    the handles, which makes the handles unreachable. A drag can announce itself
    per mouse-move, which is a window edit per pixel travelled. And it can
    commit a window shorter than anything anybody tunes against.
    """

    @pytest.fixture
    def held(self, bar: Any) -> Any:
        """The bar over a window at frames 400-700: left edge at x=400, right at x=700."""
        bar.set_window(SourceSpan(start=400, end=700))
        return bar

    def test_a_press_on_an_edge_does_not_seek(self, held: Any) -> None:
        """`pressed` is the seek, so classifying after emitting is already too late.

        The failure is visible rather than subtle: reaching for the left handle
        would throw the playhead to the window's start before the resize began.
        """
        sought: list[int] = []
        held.strip.pressed.connect(sought.append)
        driving.press(held.strip, 400.0, SCRUB_Y)
        assert sought == []

    def test_an_edge_wins_over_the_body_it_sits_in(self, held: Any) -> None:
        """A point on the edge is inside the window too — the edge is tested first."""
        driving.drag(held.strip, (400.0, SCRUB_Y), (250.0, SCRUB_Y))
        assert held.window == SourceSpan(start=250, end=700)

    def test_the_right_handle_resizes_and_pins_the_start(self, held: Any) -> None:
        driving.drag(held.strip, (700.0, SCRUB_Y), (899.0, SCRUB_Y))
        assert held.window == SourceSpan(start=400, end=900)

    def test_the_header_moves_the_window_whole(self, held: Any) -> None:
        """Length held: this is the same edit as typing a new start."""
        driving.drag(held.strip, (500.0, HEADER_Y), (600.0, HEADER_Y))
        assert held.window == SourceSpan(start=500, end=800)

    def test_a_press_below_the_header_is_still_a_scrub(self, held: Any) -> None:
        """Most of the window's area is not a handle, or the band could not be seeked."""
        sought: list[int] = []
        held.strip.pressed.connect(sought.append)
        driving.press(held.strip, 500.0, SCRUB_Y)
        assert sought == [500]

    def test_a_drag_shorter_than_a_second_stops_at_a_second(self, held: Any) -> None:
        """Thirty frames at 30 fps. The floor is a duration, not a frame count."""
        driving.drag(held.strip, (700.0, SCRUB_Y), (405.0, SCRUB_Y))
        assert held.window == SourceSpan(start=400, end=430)

    def test_one_drag_is_one_window_edit(self, held: Any) -> None:
        """A write per move would be one history entry per pixel travelled.

        v2 pinned this by counting undo commands. There is no undo stack behind
        a window that is view state, so what is counted is the announcement the
        stack used to be fed — same edge, one layer earlier.
        """
        announced: list[tuple[int, int]] = []
        held.strip.window_resized.connect(lambda start, end: announced.append((start, end)))

        driving.press(held.strip, 700.0, SCRUB_Y)
        for x in (720.0, 760.0, 800.0, 850.0):
            driving.move(held.strip, x, SCRUB_Y)
        assert announced == []
        assert held.window == SourceSpan(start=400, end=700)

        driving.release(held.strip, 899.0, SCRUB_Y)
        assert announced == [(400, 900)]

    def test_the_bracket_follows_the_drag_before_it_is_written(self, held: Any) -> None:
        """The outline is local, and the window is untouched until release."""
        driving.press(held.strip, 400.0, SCRUB_Y)
        driving.move(held.strip, 250.0, SCRUB_Y)

        assert held.strip.window_rect().left() == pytest.approx(250.0)
        assert held.window == SourceSpan(start=400, end=700)

    def test_the_bracket_and_the_boxes_agree_afterwards(self, held: Any) -> None:
        """The lockstep claim, checked on the numbers actually on screen."""
        driving.drag(held.strip, (700.0, SCRUB_Y), (899.0, SCRUB_Y))
        start_seconds, length_seconds = held.window_seconds
        assert start_seconds == pytest.approx(400.0 / SOURCE_FPS, abs=0.01)
        assert length_seconds == pytest.approx(500.0 / SOURCE_FPS, abs=0.01)
        assert held.strip.window_rect().left() == pytest.approx(400.0)
        assert held.strip.window_rect().right() == pytest.approx(900.0)


class TestTheHoverBubble:
    def test_it_names_the_frame_under_the_cursor_in_both_units(self, strip: Any) -> None:
        driving.move(strip, 300.5, SCRUB_Y)
        assert strip.hover_frame == 300
        assert strip.bubble_text() == "0:10.000   frame 300"

    def test_it_appears_without_a_button_held(self, strip: Any) -> None:
        """The widget hears an unpressed move only because it tracks the mouse."""
        assert strip.bubble_rect().isEmpty()
        driving.move(strip, 300.5, SCRUB_Y)
        assert not strip.bubble_rect().isEmpty()

    @pytest.mark.parametrize("x", [1.0, 999.0])
    def test_it_stays_inside_the_widget_at_either_end(self, strip: Any, x: float) -> None:
        """Otherwise the readout runs off the edge exactly where the user is marking."""
        driving.move(strip, x, SCRUB_Y)
        box = strip.bubble_rect()
        assert box.left() >= 0.0
        assert box.right() <= float(STRIP_WIDTH)

    def test_it_clears_when_the_cursor_leaves(self, strip: Any) -> None:
        """A bubble left behind is a claim about where a cursor that has gone is."""
        driving.move(strip, 300.5, SCRUB_Y)
        driving.leave(strip)
        assert strip.hover_frame is None
        assert strip.bubble_rect().isEmpty()

    def test_without_a_timebase_it_says_only_what_it_knows(self, qapp) -> None:
        """No fps means no second, and a guessed timecode is worse than none."""
        del qapp
        from sieve.gui.timeline.bar import TimelineStrip

        band = TimelineStrip()
        band.resize(STRIP_WIDTH, band.height())
        band.set_source_frames(SOURCE_FRAMES)
        driving.move(band, 300.5, SCRUB_Y)
        assert band.bubble_text() == "frame 300"


class TestPlaybackIsBounded:
    @pytest.fixture
    def player(self, qapp, synthetic_video: Path) -> Iterator[Any]:
        del qapp
        from sieve.gui.transport.player import VideoPlayer

        video = VideoPlayer()
        opened: list[Any] = []
        video.opened.connect(opened.append)
        video.open(str(synthetic_video))
        driving.wait_until(lambda: bool(opened), OPEN_TIMEOUT_MS)
        yield video
        video.shutdown()

    def _lands_on(self, player: Any, index: int) -> None:
        """Wait for the frame to arrive. The position is only real once it has.

        `current_index` is set when a decode comes back, not when a seek is
        asked for, so asserting straight after the call reads the previous
        position and passes for the wrong reason.
        """
        driving.wait_until(lambda: player.current_index == index, FRAME_TIMEOUT_MS)

    def test_a_seek_outside_the_window_lands_on_its_edge(self, player: Any) -> None:
        """`seek` is how every caller reaches a frame, so it is where this holds."""
        player.set_window(SourceSpan(start=10, end=20))
        player.seek(35)
        self._lands_on(player, 19)
        player.seek(0)
        self._lands_on(player, 10)

    def test_moving_the_window_pulls_the_playhead_in(self, player: Any) -> None:
        """A window moved out from under the playhead would strand the viewport."""
        player.seek(FIXTURE_FRAMES - 1)
        self._lands_on(player, FIXTURE_FRAMES - 1)
        player.set_window(SourceSpan(start=0, end=5))
        self._lands_on(player, 4)

    def test_no_window_is_the_whole_asset(self, player: Any) -> None:
        player.set_window(None)
        player.seek(999)
        self._lands_on(player, FIXTURE_FRAMES - 1)


class TestTheSkeletonBindsTheSource:
    """Opening a project reaches the decode path, the canvas, and the band.

    v2's equivalent drove menu actions that marked a clip. There are none here —
    the skeleton has no menu bar, and the span a run covers is a graph node — so
    what is left of that case is the wiring it depended on: the source's length
    and rate reach the bar, and a frame reaches the canvas.
    """

    @pytest.fixture
    def window(self, qapp, tmp_path: Path, synthetic_video: Path) -> Iterator[Any]:
        del qapp
        import shutil

        from sieve.gui.app import MainWindow

        shutil.copy(synthetic_video, tmp_path / "clip.mp4")
        project = Project(
            source=SourceRef(path="clip.mp4"),
            pipeline=Pipeline(
                nodes=(
                    Node(node_id="n0", tool_id="downsample", version="1.0.0"),
                    Node(node_id="n1", tool_id="crop", version="1.0.0"),
                ),
                edges=(Edge(upstream="n0", downstream="n1"),),
            ),
        )
        path = tmp_path / "clip.sieve.yaml"
        project.save(path)

        main = MainWindow((path,))
        main.show()
        main.open_project(path)
        yield main
        main.close()

    def test_the_window_opens_over_the_whole_source(self, window: Any) -> None:
        driving.wait_until(lambda: window.timeline.window is not None, OPEN_TIMEOUT_MS)
        assert window.timeline.window == SourceSpan(start=0, end=FIXTURE_FRAMES)

    def test_the_first_frame_reaches_the_canvas(self, window: Any) -> None:
        driving.wait_until(
            lambda: window.player.metadata is not None and window.player.fps == FIXTURE_FPS,
            OPEN_TIMEOUT_MS,
        )
        driving.wait_until(lambda: not window.timeline.strip.window_rect().isEmpty(), 1000)
        assert window.timeline.strip.window_rect().left() == pytest.approx(0.0)

    def test_a_scrub_on_the_band_moves_the_playhead(self, window: Any) -> None:
        driving.wait_until(lambda: window.timeline.window is not None, OPEN_TIMEOUT_MS)
        strip = window.timeline.strip
        strip.resize(STRIP_WIDTH, strip.height())
        driving.click(strip, 500.0, SCRUB_Y)
        target = strip.geometry_now().frame_at(500.0)
        driving.wait_until(lambda: window.player.current_index == target, FRAME_TIMEOUT_MS)
