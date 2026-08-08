"""The anchor: one full-width band across the bottom of the window.

It spans the whole asset, it carries the working window and the playhead, and it
sits under the canvas rather than inside any one position of the control track —
so "where am I, and what stretch am I working on" has one answer that does not
depend on which position is showing.

**Why the strip owns no state.** Both things it paints belong to somebody else.
The playhead is the player's, because the player is what a frame arrives from;
the window is the bar's, because the bar is what confines the transport. A copy
of either here would be a second answer to a question that already has one, and
the copy is the one that goes stale. What the strip owns is a *mapping*, and
even that is `geometry.py`, rebuilt per paint and per click.

**Three mouse events, three claims.** A press is a position the user has
committed to and is where the window rule is applied. A move is a guess they are
still refining, so it scrubs — the player coalesces those and may serve them
coarse. A release is the commitment again, and is what guarantees they land
exactly where they let go however coarse the drag was. Collapsing any two of
them either makes the drag decode every pixel or leaves the user a frame or two
from where they stopped.

**Why a window drag is two-tier and a scrub is not.** A scrub emits on every
move because a guess is what the user is asking to see. A window drag paints
from a local draft and announces itself exactly once, on release. The draft is
the one piece of window state the strip holds, and it exists only between a
press and its release.
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFontMetricsF,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import SourceSpan
from sieve.core.types import VideoMetadata
from sieve.gui.timeline.geometry import Geometry
from sieve.gui.timeline.window import containing, ended_at, moved_to, started_at, whole_of
from sieve.gui.transport.player import VideoPlayer

#: Height of the band. VISION asks for v2's scrubber "much taller", because the
#: band is where the cached signal for the current run is read (v1's habit,
#: reimagined): the lanes that carry it land in this height rather than growing
#: it when they arrive.
STRIP_HEIGHT = 96

#: Vertical inset of the painted track inside that height.
_TRACK_INSET = 4.0

#: How far either side of a window edge counts as grabbing that edge. Wider than
#: the painted line, because the line is a claim about a frame and the handle is
#: a target for a hand. Public because a span parameter's handles are dragged on
#: this same band (`gui/kind_editors.py`): how big a target is, is a fact about
#: the hand and not about which of the two the hand is reaching for.
EDGE_GRAB = 6.0

#: Depth of the darker band along the window's top that moves it whole.
_HEADER_HEIGHT = 9.0

#: Shortest window a drag may produce. A window under a second is a misclick,
#: and the floor is in seconds rather than frames so it means the same thing at
#: 30 fps and at 240.
MIN_WINDOW_SECONDS = 1.0

_PLAY_GLYPH = "▶"
_PAUSE_GLYPH = "⏸"

_TRACK = QColor(30, 30, 36)
_WINDOW = QColor(90, 170, 255, 70)
_WINDOW_EDGE = QColor(90, 170, 255)
_WINDOW_HEADER = QColor(90, 170, 255, 110)
_WINDOW_HEADER_HELD = QColor(90, 170, 255, 180)
_PLAYHEAD = QColor(240, 240, 245)
_BUBBLE = QColor(18, 18, 22, 235)
_BUBBLE_EDGE = QColor(80, 84, 96)
_BUBBLE_TEXT = QColor(232, 233, 238)

#: Padding inside the hover bubble, horizontal and vertical.
_BUBBLE_PAD = (8.0, 3.0)

_EMPTY_HINT = "Open a video to begin"


class Grab(Enum):
    """What a press on the band is taking hold of.

    Classified once, on press, and held for the gesture: a drag that
    re-classified as it travelled would change what it was doing halfway
    through, because the window it is testing against is moving under it.
    """

    #: Neither edge nor header: the position itself, which is a seek.
    SCRUB = auto()
    #: The window's left edge. Resizes, pinning the right.
    START = auto()
    #: The window's right edge. Resizes, pinning the left.
    END = auto()
    #: The header band. Moves the window whole, holding its length.
    BODY = auto()


def format_timecode(seconds: float) -> str:
    """`M:SS.mmm`, or `H:MM:SS.mmm` past an hour."""
    seconds = max(seconds, 0.0)
    hours, remainder = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    milliseconds = round((seconds - int(seconds)) * 1000) % 1000
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
    return f"{minutes}:{whole_seconds:02d}.{milliseconds:03d}"


class TimelineStrip(QWidget):
    """The band itself: the whole asset, the window on it, and the playhead.

    A view and a hit-test, nothing else. It emits frame indices and is told what
    to paint; every rule about what those indices *mean* is in `geometry.py` or
    in `window.py`.
    """

    #: Mouse-down. A committed position, and where the window rule is applied.
    pressed = Signal(int)
    #: A drag position. A guess, which the player may serve approximately.
    scrubbed = Signal(int)
    #: Mouse-up. The commitment again: land here exactly.
    committed = Signal(int)
    #: A finished header drag, as the window's new origin. Release only.
    window_moved = Signal(int)
    #: A finished handle drag, as the window's new span. Release only.
    window_resized = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame_count = 0
        self._fps = 0.0
        self._window: SourceSpan | None = None
        self._playhead = 0
        self._dragging = False
        # The window as the drag has it so far, painted in place of the bar's
        # until release. None whenever no handle is held.
        self._draft: SourceSpan | None = None
        self._grab: Grab | None = None
        self._grab_offset = 0
        self._hover: int | None = None
        self.setFixedHeight(STRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        # Without this the widget hears a move only while a button is down, and
        # the bubble would appear on press rather than on approach.
        self.setMouseTracking(True)

    # ---- what it paints --------------------------------------------------

    def set_source_frames(self, frame_count: int) -> None:
        """Establish the asset's length, which is the whole horizontal axis."""
        self._frame_count = max(frame_count, 0)
        self.update()

    def set_timebase(self, fps: float) -> None:
        """Tell the band what a second is.

        Two things need it and neither is a frame index: the bubble reads a
        timecode, and the floor on a window drag is a duration. Not truth the
        strip owns — it is the source's, restated here for the same reason the
        frame count is.
        """
        self._fps = max(fps, 0.0)

    def set_window(self, window: SourceSpan | None) -> None:
        """Show `window` as the working span, or nothing for None."""
        self._window = window
        self.update()

    def set_playhead(self, frame: int) -> None:
        """Move the playhead to `frame`."""
        self._playhead = frame
        self.update()

    # ---- geometry --------------------------------------------------------

    def geometry_now(self) -> Geometry:
        """The mapping at the current width.

        Not cached: the width changes under the user and the frame count changes
        under the file, and a mapping held across either paints one video's
        proportions onto another's.
        """
        return Geometry(frame_count=self._frame_count, width=float(self.width()))

    @property
    def shown_window(self) -> SourceSpan | None:
        """The span on screen: the draft while a handle is held, else the bar's.

        Everything that reads the window — the paint, the hit test, the rect a
        test asks about — goes through here, so a drag cannot be visible in one
        of them and absent from another.
        """
        return self._draft if self._draft is not None else self._window

    @property
    def floor_frames(self) -> int:
        """`MIN_WINDOW_SECONDS` in frames, or one frame when there is no timebase.

        One rather than a guessed frame count: without an fps the container has
        not said how long a second is, and a floor invented here would refuse
        drags for a duration nobody stated.
        """
        if self._fps <= 0.0:
            return 1
        return max(round(MIN_WINDOW_SECONDS * self._fps), 1)

    def window_rect(self) -> QRectF:
        """Where the working window is painted, empty when there is none.

        Exposed because it is the claim worth testing — that the band lands
        under the frames it names — and a painted pixel is not something a test
        can ask about.
        """
        geometry = self.geometry_now()
        window = self.shown_window
        if window is None or geometry.is_empty:
            return QRectF()
        left, right = geometry.span(window.start, window.end)
        return QRectF(left, _TRACK_INSET, right - left, self.height() - 2.0 * _TRACK_INSET)

    def header_rect(self) -> QRectF:
        """The band along the window's top that moves it whole, empty when there is none."""
        window = self.window_rect()
        if window.isEmpty():
            return QRectF()
        return QRectF(window.left(), window.top(), window.width(), _HEADER_HEIGHT)

    def column_centre(self, frame: int) -> float:
        """Centre of the column `frame` occupies. Where a mark on it is drawn."""
        return self.geometry_now().centre_of_frame(frame)

    def playhead_x(self) -> float:
        """Centre of the column the playhead sits in."""
        return self.column_centre(self._playhead)

    # ---- the hit test ----------------------------------------------------

    def grab_at(self, position: QPointF) -> Grab:
        """What a press at `position` would take hold of.

        **Edges before containment**: a point on an edge is inside the window
        too, so a containment test run first makes the edges unreachable and
        leaves the user resizing by typing. The header is tested after both,
        because it is the only zone whose claim is about a region rather than a
        line.
        """
        window = self.window_rect()
        if window.isEmpty():
            return Grab.SCRUB
        x = position.x()
        if abs(x - window.left()) <= EDGE_GRAB:
            return Grab.START
        if abs(x - window.right()) <= EDGE_GRAB:
            return Grab.END
        if self.header_rect().contains(position):
            return Grab.BODY
        return Grab.SCRUB

    # ---- the hover bubble ------------------------------------------------

    @property
    def hover_frame(self) -> int | None:
        """The frame under the cursor, or None when the cursor is not on the band."""
        return self._hover

    def bubble_text(self) -> str:
        """What the bubble says: where the cursor is, in both units the user thinks in."""
        if self._hover is None:
            return ""
        if self._fps <= 0.0:
            return f"frame {self._hover:,}"
        return f"{format_timecode(self._hover / self._fps)}   frame {self._hover:,}"

    def bubble_rect(self) -> QRectF:
        """Where the bubble sits, empty when there is nothing to say.

        Clamped to the widget, so a cursor near either end reads a bubble that
        stops at the edge rather than one trailing off it. It sits *below* the
        header band rather than at the very top of the track: the bubble follows
        the cursor, the header is what the cursor is often approaching, and a
        readout that covers the handle it is guiding you to is worse than one
        sitting a few pixels lower.
        """
        if self._hover is None or self.geometry_now().is_empty:
            return QRectF()
        pad_x, pad_y = _BUBBLE_PAD
        metrics = QFontMetricsF(self.font())
        width = metrics.horizontalAdvance(self.bubble_text()) + 2.0 * pad_x
        height = metrics.height() + 2.0 * pad_y
        left = max(min(self.column_centre(self._hover) - width / 2.0, self.width() - width), 0.0)
        return QRectF(left, _TRACK_INSET + _HEADER_HEIGHT, width, height)

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        """Track, then window, then playhead — back to front."""
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(self.rect()).adjusted(0.0, _TRACK_INSET, 0.0, -_TRACK_INSET)
        painter.fillRect(track, _TRACK)

        if self.geometry_now().is_empty:
            painter.setPen(QColor(120, 120, 130))
            painter.drawText(
                track.adjusted(8.0, 0.0, -8.0, 0.0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                _EMPTY_HINT,
            )
            painter.end()
            return

        window = self.window_rect()
        if not window.isEmpty():
            painter.fillRect(window, _WINDOW)
            held = self._grab is Grab.BODY
            painter.fillRect(self.header_rect(), _WINDOW_HEADER_HELD if held else _WINDOW_HEADER)
            edge = 2.0 if self._grab in (Grab.START, Grab.END) else 1.0
            painter.setPen(QPen(_WINDOW_EDGE, edge))
            painter.drawRect(window.adjusted(0.5, 0.5, -0.5, -0.5))

        x = self.playhead_x()
        painter.setPen(QPen(_PLAYHEAD, 1.0))
        painter.drawLine(QPointF(x, 0.0), QPointF(x, float(self.height())))
        self._paint_bubble(painter)
        painter.end()

    def _paint_bubble(self, painter: QPainter) -> None:
        """The hover readout, and nothing while a drag is under way.

        A drag already answers "where am I" through the thing being dragged, and
        a bubble tracking the cursor through a resize covers the edge the user
        is placing.
        """
        box = self.bubble_rect()
        if box.isEmpty() or self._dragging or self._grab is not None:
            return
        painter.setPen(QPen(_BUBBLE_EDGE, 1.0))
        painter.setBrush(_BUBBLE)
        painter.drawRoundedRect(box, 3.0, 3.0)
        painter.setPen(_BUBBLE_TEXT)
        painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), self.bubble_text())

    # ---- scrubbing and dragging ------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Classify first, and only then take the position as a committed one.

        The classification has to come before the emit and not after it:
        `pressed` *is* the seek, so a strip that emitted unconditionally would
        jump the playhead to the window's left edge the moment the user reached
        for that edge to resize it, before the resize had begun.
        """
        if self.geometry_now().is_empty or event.button() is not Qt.MouseButton.LeftButton:
            return
        grab = self.grab_at(event.position())
        if grab is Grab.SCRUB:
            self._dragging = True
            self.pressed.emit(self.geometry_now().frame_at(event.position().x()))
            return
        window = self.shown_window
        if window is None:
            return
        self._grab = grab
        self._draft = window
        self._grab_offset = self.geometry_now().frame_at(event.position().x()) - window.start
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Follow the drag. A guess, and the player is allowed to approximate it."""
        position = event.position()
        self._hover = self.geometry_now().frame_at(position.x())
        if self._dragging:
            self.scrubbed.emit(self._hover)
        elif self._grab is not None:
            self._draft = self._dragged_to(position.x())
        else:
            self._follow_cursor(position)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Land exactly where the user let go, or announce the drag once."""
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        if self._dragging:
            self._dragging = False
            self.committed.emit(self.geometry_now().frame_at(event.position().x()))
            return
        if self._grab is None:
            return
        window = self._dragged_to(event.position().x())
        grab, self._grab, self._draft = self._grab, None, None
        self.update()
        if grab is Grab.BODY:
            self.window_moved.emit(window.start)
        else:
            self.window_resized.emit(window.start, window.end)

    def leaveEvent(self, event: QEvent) -> None:
        """Drop the bubble. A cursor that has left names no frame."""
        del event
        if self._hover is not None:
            self._hover = None
            self.update()

    def _dragged_to(self, x: float) -> SourceSpan:
        """The window this drag has arrived at. Never written; only painted, until release."""
        window = self._draft if self._draft is not None else self._window
        frame = self.geometry_now().frame_at(x)
        if window is None:
            return SourceSpan(start=0, end=max(self._frame_count, 1))
        if self._grab is Grab.START:
            return started_at(window, frame, self._frame_count, self.floor_frames)
        if self._grab is Grab.END:
            return ended_at(window, frame, self._frame_count, self.floor_frames)
        return moved_to(window, frame - self._grab_offset, self._frame_count)

    def _follow_cursor(self, position: QPointF) -> None:
        """Say what the zone under the cursor does before it is pressed.

        The band is one surface with three behaviours on it and no visual
        boundary between two of them; the cursor is where that is announced.
        """
        self.setCursor(
            {
                Grab.START: Qt.CursorShape.SizeHorCursor,
                Grab.END: Qt.CursorShape.SizeHorCursor,
                Grab.BODY: Qt.CursorShape.OpenHandCursor,
                Grab.SCRUB: Qt.CursorShape.PointingHandCursor,
            }[self.grab_at(position)]
        )


class TimelineBar(QWidget):
    """The strip, the row of controls above it, and the working window.

    Takes the player rather than being wired from outside, because every one of
    its controls is a statement about the transport and a bar holding none would
    need a signal per control and a slot per signal in the window.

    The window lives here and nowhere else. It is not the document's — schema v1
    saves no such span — and it is not the player's, which is *told* a bound and
    holds no opinion about how it moves. One owner is what lets the bracket, the
    two boxes, and the transport never disagree.
    """

    def __init__(self, player: VideoPlayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._player = player
        self._window: SourceSpan | None = None
        self._frame_count = 0
        self._fps = 0.0
        # Set while a spin box is being written to from the window, so the
        # `valueChanged` it fires is not read back as the user having typed it.
        # Without it, rounding a frame count into seconds and back moves a
        # window nobody touched.
        self._updating = False

        self._strip = TimelineStrip()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 4)
        layout.setSpacing(2)
        layout.addLayout(self._build_controls())
        layout.addWidget(self._strip)

        self._connect()
        self._on_source_changed()

    @property
    def strip(self) -> TimelineStrip:
        """The band. Exposed for the window's shortcuts and for tests."""
        return self._strip

    @property
    def window(self) -> SourceSpan | None:
        """The working window: what the transport is confined to."""
        return self._window

    @property
    def window_seconds(self) -> tuple[float, float]:
        """The window as the two boxes read it: (start, length), in seconds.

        Exposed for the same reason `strip` is. "The bracket and the boxes can
        never disagree" is the lockstep claim this bar exists to keep, and it is
        only checkable if the numbers actually on screen can be read back —
        recomputing them from the window would test the arithmetic twice and the
        lockstep not at all.
        """
        return self._start_box.value(), self._length_box.value()

    # ---- construction ----------------------------------------------------

    def _build_controls(self) -> QHBoxLayout:
        """Play, window start, window length, timestamp — hard right."""
        self._play_button = QPushButton(_PLAY_GLYPH)
        self._play_button.setFixedWidth(40)
        self._play_button.setToolTip("Play / pause (Space)")

        self._start_box = QDoubleSpinBox()
        self._start_box.setDecimals(2)
        self._start_box.setSingleStep(1.0)
        self._start_box.setSuffix(" s")
        self._start_box.setToolTip("Where the working window starts")

        self._length_box = QDoubleSpinBox()
        self._length_box.setDecimals(2)
        self._length_box.setSingleStep(1.0)
        self._length_box.setSuffix(" s")
        self._length_box.setToolTip("How long the working window is")

        self._timecode = QLabel("—")
        self._timecode.setTextFormat(Qt.TextFormat.PlainText)
        self._timecode.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        # The stretch is first, not last: this row sits hard right, and
        # everything in it reads as one cluster rather than as controls
        # scattered across a width that grows with the window.
        row.addStretch(1)
        row.addWidget(self._play_button)
        row.addWidget(QLabel("Window"))
        row.addWidget(self._start_box)
        row.addWidget(QLabel("+"))
        row.addWidget(self._length_box)
        row.addWidget(self._timecode)
        return row

    def _connect(self) -> None:
        self._player.opened.connect(self._on_opened)
        self._player.frame_changed.connect(self._on_frame_changed)
        self._player.playing_changed.connect(self._on_playing_changed)

        self._play_button.clicked.connect(self._player.toggle_play)
        self._start_box.valueChanged.connect(self._on_start_typed)
        self._length_box.valueChanged.connect(self._on_length_typed)

        self._strip.pressed.connect(self._on_pressed)
        self._strip.scrubbed.connect(self._player.scrub)
        self._strip.committed.connect(self._on_committed)
        # Straight at the bar's own window verbs: a header drag holds the length
        # and so is the same edit as a typed start, and a handle drag has
        # already resolved both edges. Neither needs a translation here.
        self._strip.window_moved.connect(self.move_window_to)
        self._strip.window_resized.connect(self._on_window_resized)

    # ---- the source ------------------------------------------------------

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        """Adopt a newly opened source: its axis, its timebase, its whole span.

        The window restarts at the whole source rather than carrying over. Frame
        400 of another video is another moment, and a span kept across the
        change would confine the transport to a stretch of footage the user has
        never seen.
        """
        self.bind_source(metadata.frame_count, float(metadata.fps))

    def bind_source(self, frame_count: int, fps: float) -> None:
        """Establish the axis for a source of `frame_count` frames at `fps`.

        Separate from `_on_opened` so the empty state — nothing open, which is
        what the application starts in and returns to on close — is the same
        code path with zeroes in it.
        """
        self._frame_count = max(frame_count, 0)
        self._fps = max(fps, 0.0)
        self._window = whole_of(self._frame_count)
        self._on_source_changed()

    def _on_source_changed(self) -> None:
        self._strip.set_source_frames(self._frame_count)
        self._strip.set_timebase(self._fps)
        enabled = self._frame_count > 0
        for widget in (self._play_button, self._start_box, self._length_box, self._strip):
            widget.setEnabled(enabled)
        self._push_window()
        self._update_timecode(self._player.current_index if enabled else 0)

    # ---- the window ------------------------------------------------------

    def set_window(self, window: SourceSpan | None) -> None:
        """Adopt `window` and push it at everything that shows or enforces it."""
        self._window = window
        self._push_window()

    def _push_window(self) -> None:
        """The strip, the transport, and the boxes, from one value.

        The player is told here and nowhere else. A bracket drag, a typed
        number, and a click outside the window all arrive through this, and a
        transport bounded from two places would be bounded by whichever spoke
        last.
        """
        self._strip.set_window(self._window)
        self._player.set_window(self._window)
        self._write_boxes(self._window)

    def _write_boxes(self, window: SourceSpan | None) -> None:
        """Restate the window in seconds without treating it as a user edit."""
        self._updating = True
        try:
            if window is None or self._fps <= 0.0 or self._frame_count <= 0:
                self._start_box.setRange(0.0, 0.0)
                self._length_box.setRange(0.0, 0.0)
                return
            duration = self._frame_count / self._fps
            self._start_box.setRange(0.0, max(duration - 1.0 / self._fps, 0.0))
            self._start_box.setValue(window.start / self._fps)
            self._length_box.setRange(1.0 / self._fps, duration)
            self._length_box.setValue(window.frame_count / self._fps)
        finally:
            self._updating = False

    @Slot(int)
    def move_window_to(self, origin: int) -> None:
        """Put the window at `origin`, holding its length. A no-op with no source."""
        if self._window is None:
            return
        self.set_window(moved_to(self._window, origin, self._frame_count))

    def set_window_length(self, frames: int) -> None:
        """Make the window `frames` long, keeping its origin where it will fit.

        The length is what the user typed; the origin is what they did not, so a
        length that runs off the end slides the origin back rather than being
        refused or truncated.
        """
        if self._window is None:
            return
        length = min(max(frames, 1), self._frame_count)
        start = min(self._window.start, self._frame_count - length)
        self.set_window(SourceSpan(start=start, end=start + length))

    @Slot(float)
    def _on_start_typed(self, seconds: float) -> None:
        if self._updating:
            return
        self.move_window_to(self._frames_of(seconds))

    @Slot(float)
    def _on_length_typed(self, seconds: float) -> None:
        if self._updating:
            return
        self.set_window_length(max(self._frames_of(seconds), 1))

    def _frames_of(self, seconds: float) -> int:
        """Seconds as a frame index. Frames are authoritative; the boxes are a view."""
        if self._fps <= 0.0:
            return 0
        return round(seconds * self._fps)

    @Slot(int, int)
    def _on_window_resized(self, start: int, end: int) -> None:
        self.set_window(SourceSpan(start=start, end=end))

    # ---- the playhead ----------------------------------------------------

    @Slot(int)
    def _on_pressed(self, frame: int) -> None:
        """A click: bring the window to it if it is outside, then go there.

        `containing` returns the window unchanged when the frame is already
        inside, which is what lets one handler serve both halves of the rule —
        the strip never has to decide which gesture it was.
        """
        self._bring_to(frame)
        self._player.seek(frame)

    @Slot(int)
    def _on_committed(self, frame: int) -> None:
        """A release: the same rule, because a drag can end outside the window."""
        self._bring_to(frame)
        self._player.seek(frame)

    def _bring_to(self, frame: int) -> None:
        if self._window is None:
            return
        moved = containing(self._window, frame, self._frame_count)
        if moved != self._window:
            self.set_window(moved)

    @Slot(int, QImage)
    def _on_frame_changed(self, index: int, image: QImage) -> None:
        del image
        self._strip.set_playhead(index)
        self._update_timecode(index)

    @Slot(bool)
    def _on_playing_changed(self, playing: bool) -> None:
        self._play_button.setText(_PAUSE_GLYPH if playing else _PLAY_GLYPH)

    def _update_timecode(self, index: int) -> None:
        metadata: VideoMetadata | None = self._player.metadata
        if metadata is None or self._frame_count <= 0:
            self._timecode.setText("—")
            return
        self._timecode.setText(
            f"{format_timecode(float(metadata.timestamp_of(index).seconds))} / "
            f"{format_timecode(float(metadata.duration_seconds.seconds))}   "
            f"frame {index:,} / {metadata.frame_count - 1:,}"
        )
