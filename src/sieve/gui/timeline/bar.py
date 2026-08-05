"""The anchor: one full-width band across the bottom of the window.

It spans the whole asset, it carries the working window and the playhead, and
it is outside the tabs — so "where am I, and what span am I working on" has one
answer that does not depend on which tab is showing. It supersedes the
per-viewport seeker: a slider living inside a tab says the same thing in as many
places as there are tabs, and they drift.

**Why the strip owns no state.** Both things it paints belong to somebody else.
The window is the document's, because it is saved into the project; the playhead
is the player's, because the player is what a frame arrives from. A copy of
either here would be a second answer to a question that already has one, and the
copy is the one that goes stale. What the strip owns is a *mapping*, and even
that is `timeline/geometry.py`, rebuilt per paint and per click.

**Three mouse events, three claims.** A press is a position the user has
committed to and is where the window rule is applied. A move is a guess they are
still refining, so it scrubs — the player coalesces those and may serve them
coarse. A release is the commitment again, and is what guarantees they land
exactly where they let go however coarse the drag was. Collapsing any two of
them either makes the drag decode every pixel or leaves the user a frame or two
from where they stopped.

**Why a window drag is two-tier and a scrub is not.** A scrub emits on every
move because a guess is what the user is asking to see. A window drag paints
from a local draft and writes through exactly once, on release, because
`commands.SetClip` has no `mergeWith` — a command per mouse-move would be one
undo entry per pixel travelled, and the history is the thing that cannot be
un-shredded afterwards. The draft is the one piece of window state this widget
holds, and it exists only between a press and its release.
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

from sieve.core.clip_window import ended_at_handle, moved_to, started_at
from sieve.core.pipeline_model import ClipRange
from sieve.core.types import VideoMetadata
from sieve.gui.document import ReplicateDocument
from sieve.gui.timeline.geometry import Geometry
from sieve.gui.transport.player import VideoPlayer

#: Height of the band. Tall enough to be a target for a mouse rather than a
#: hairline to be aimed at, and sized now for the coverage and detection lanes
#: that land in it later (`docs/todo/coverage-and-detection-lanes.md`) rather
#: than grown when they arrive.
STRIP_HEIGHT = 44

#: Vertical inset of the painted track inside that height.
_TRACK_INSET = 4.0

#: How far either side of a window edge counts as grabbing that edge. Wider than
#: the painted line, because the line is a claim about a frame and the handle is
#: a target for a hand; six is what `video_view.py` settled on for crop handles.
_EDGE_GRAB = 6.0

#: Depth of the darker band along the window's top that moves it whole.
_HEADER_HEIGHT = 9.0

#: Shortest window a drag may produce. A window under a second is a misclick —
#: nothing in VISION step 4 is tuned against less — and the floor is in seconds
#: rather than frames so it means the same thing at 30 fps and at 240.
MIN_WINDOW_SECONDS = 1.0

_PLAY_GLYPH = "▶"
_PAUSE_GLYPH = "⏸"

_TRACK = QColor(30, 30, 36)
_WINDOW = QColor(90, 170, 255, 70)
_WINDOW_EDGE = QColor(90, 170, 255)
_WINDOW_HEADER = QColor(90, 170, 255, 110)
_WINDOW_HEADER_HELD = QColor(90, 170, 255, 180)
_PLAYHEAD = QColor(240, 240, 245)
#: Over the track, outside the span a crop at rest holds the window inside. A
#: wash rather than a hatch: what it says is "not reachable", and the frames
#: under it are still real footage the playhead may sit on.
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
    if seconds < 0.0:
        seconds = 0.0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    milliseconds = round((seconds - int(seconds)) * 1000) % 1000
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
    return f"{minutes}:{whole_seconds:02d}.{milliseconds:03d}"


class TimelineStrip(QWidget):
    """The band itself: the whole asset, the window on it, and the playhead.

    A view and a hit-test, nothing else. It emits frame indices and is told what
    to paint; every rule about what those indices *mean* is in
    `timeline/geometry.py`, `core/clip_window.py`, or in the document.
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
        self._window: ClipRange | None = None
        self._playhead = 0
        self._dragging = False
        # The window as the drag has it so far, painted in place of the
        # document's until release. None whenever no handle is held.
        self._draft: ClipRange | None = None
        self._grab: Grab | None = None
        self._grab_offset = 0
        self._hover: int | None = None
        #: The span a materialized crop is holding the window inside, or None.
        #: Pushed in by the bar from the document; the strip derives nothing
        #: about artifacts and only draws and clamps against it.
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

    def set_window(self, window: ClipRange | None) -> None:
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
    def shown_window(self) -> ClipRange | None:
        """The span on screen: the draft while a handle is held, else the document's.

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

        **Edges before containment**, which is the rule `video_view.py` already
        settled for crop handles: a point on an edge is inside the window too,
        so a containment test run first makes the edges unreachable and leaves
        the user resizing by typing. The header is tested after both, because it
        is the only zone whose claim is about a region rather than a line.
        """
        window = self.window_rect()
        if window.isEmpty():
            return Grab.SCRUB
        x = position.x()
        if abs(x - window.left()) <= _EDGE_GRAB:
            return Grab.START
        if abs(x - window.right()) <= _EDGE_GRAB:
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
        """What the bubble says: where the cursor is, in both units the user thinks in.

        Coverage and the nearest detection belong here too and are absent, not
        blank: neither has a producer yet (see the coverage-and-detection-lanes
        item), and a line reading "not examined" from a module that has never
        been told anything is rule 6's failure exactly — unexamined rendered as
        quiet.
        """
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
        painter.drawText(
            box,
            int(Qt.AlignmentFlag.AlignCenter),
            self.bubble_text(),
        )

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
        """Land exactly where the user let go, or write the drag through once."""
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

    def _dragged_to(self, x: float) -> ClipRange:
        """The window this drag has arrived at. Never written; only painted, until release."""
        window = self._draft if self._draft is not None else self._window
        frame = self.geometry_now().frame_at(x)
        if window is None:
            return ClipRange(start=0, end=max(self._frame_count, 1))
        if self._grab is Grab.START:
            return started_at(window, frame, self._frame_count, self.floor_frames)
        if self._grab is Grab.END:
            return ended_at_handle(window, frame, self._frame_count, self.floor_frames)
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
    """The strip and the row of controls above it.

    Takes the player and the document rather than being wired from outside,
    because every one of its controls is a statement about one or the other and
    a bar holding neither would need a signal per control and a slot per signal
    in the window.
    """

    def __init__(
        self,
        player: VideoPlayer,
        document: ReplicateDocument,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document
        # Set while a spin box is being written to from the document, so the
        # `valueChanged` it fires is not read back as the user having typed it.
        # Without it, rounding a frame count into seconds and back pushes an
        # undo command for a window nobody moved.
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
    def window_seconds(self) -> tuple[float, float]:
        """The window as the two boxes read it: (start, length), in seconds.

        Exposed for the same reason `strip` is. "The bracket and the boxes can
        never disagree" is the lockstep claim this bar exists to keep, and it is
        only checkable if the numbers actually on screen can be read back —
        recomputing them from the document would test the arithmetic twice and
        the lockstep not at all.
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
        # The stretch is first, not last: the reference puts this row hard
        # right, and everything in it reads as one cluster rather than as
        # controls scattered across a width that grows with the window.
        row.addStretch(1)
        row.addWidget(self._play_button)
        row.addWidget(QLabel("Window"))
        row.addWidget(self._start_box)
        row.addWidget(QLabel("+"))
        row.addWidget(self._length_box)
        row.addWidget(self._timecode)
        return row

    def _connect(self) -> None:
        # The document and not the player, though the player is what learns of
        # a new video first. The window binds the document from the player's
        # `opened`, so a bar listening to the same signal would read the length
        # of the *previous* source or of none at all, depending on which slot
        # Qt ran first. The document announcing its own binding has one order.
        self._document.source_changed.connect(self._on_source_changed)
        self._player.frame_changed.connect(self._on_frame_changed)
        self._player.playing_changed.connect(self._on_playing_changed)

        self._play_button.clicked.connect(self._player.toggle_play)
        self._start_box.valueChanged.connect(self._on_start_typed)
        self._length_box.valueChanged.connect(self._on_length_typed)

        self._strip.pressed.connect(self._on_pressed)
        self._strip.scrubbed.connect(self._player.scrub)
        self._strip.committed.connect(self._on_committed)
        # Straight at the document's own window verbs: a header drag holds the
        # length and so is the same edit as a typed start, and a handle drag has
        # already resolved both edges. Neither needs a translation here, and the
        # Edit menu reads back the gesture the user made.
        self._strip.window_moved.connect(self._document.move_window_to)
        self._strip.window_resized.connect(self._document.place_window)

        self._document.clip_changed.connect(self._on_window_changed)
        # A record written or discarded moves the fence without moving the
        # window, and a moved box can lift a freeze the same way — both arrive
        # here so the fence and the clamp are never a beat behind the record.
        self._document.crops_changed.connect(self._on_window_changed)
        self._document.replicate_changed.connect(self._on_window_changed)

    # ---- the source ------------------------------------------------------

    @Slot()
    def _on_source_changed(self) -> None:
        """Re-establish the axis, the window, and the readout for a new video.

        Also the close path: `video_closed` calls it with nothing bound, and
        every branch below has to survive a document with no source, because
        that is the state the application starts in.
        """
        frames = self._document.source_frames
        self._strip.set_source_frames(frames)
        self._strip.set_timebase(self._document.source_fps)
        enabled = frames > 0
        for widget in (self._play_button, self._start_box, self._length_box, self._strip):
            widget.setEnabled(enabled)
        self._on_window_changed()
        self._update_timecode(self._player.current_index if enabled else 0)

    def video_closed(self) -> None:
        """Return to the empty state after the source is unloaded."""
        self._on_source_changed()

    # ---- the window ------------------------------------------------------

    @Slot()
    def _on_window_changed(self) -> None:
        """Push the document's window at everything that shows or enforces it.

        The player is told here and nowhere else. It is the only place that
        knows the window changed at all — a mark, a strip click, a typed number,
        and an undo all arrive as `clip_changed` — and a transport bounded from
        two places would be bounded by whichever spoke last.
        """
        window = self._document.window
        self._strip.set_window(window)
        self._player.set_window(window)
        self._write_boxes(window)

    def _write_boxes(self, window: ClipRange | None) -> None:
        """Restate the window in seconds without treating it as a user edit."""
        fps = self._document.source_fps
        frames = self._document.source_frames
        self._updating = True
        try:
            if window is None or fps <= 0.0 or frames <= 0:
                self._start_box.setRange(0.0, 0.0)
                self._length_box.setRange(0.0, 0.0)
                return
            duration = frames / fps
            self._start_box.setRange(0.0, max(duration - 1.0 / fps, 0.0))
            self._start_box.setValue(window.start / fps)
            self._length_box.setRange(1.0 / fps, duration)
            self._length_box.setValue(window.frame_count / fps)
        finally:
            self._updating = False

    @Slot(float)
    def _on_start_typed(self, seconds: float) -> None:
        if self._updating:
            return
        self._document.move_window_to(self._frames_of(seconds))

    @Slot(float)
    def _on_length_typed(self, seconds: float) -> None:
        if self._updating:
            return
        self._document.set_window_length(max(self._frames_of(seconds), 1))

    def _frames_of(self, seconds: float) -> int:
        """Seconds as a frame index. Frames are authoritative; the boxes are a view."""
        fps = self._document.source_fps
        if fps <= 0.0:
            return 0
        return round(seconds * fps)

    # ---- the playhead ----------------------------------------------------

    @Slot(int)
    def _on_pressed(self, frame: int) -> None:
        """A click: bring the window to it if it is outside, then go there.

        `bring_window_to` is a no-op when the frame is already inside, which is
        what lets one handler serve both halves of the rule — the strip never
        has to decide which gesture it was.
        """
        self._document.bring_window_to(frame)
        self._player.seek(frame)

    @Slot(int)
    def _on_committed(self, frame: int) -> None:
        """A release: the same rule, because a drag can end outside the window."""
        self._document.bring_window_to(frame)
        self._player.seek(frame)

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
        if metadata is None or self._document.source_frames <= 0:
            self._timecode.setText("—")
            return
        self._timecode.setText(
            f"{format_timecode(metadata.timestamp_of(index))} / "
            f"{format_timecode(metadata.duration_seconds)}   "
            f"frame {index:,} / {metadata.frame_count - 1:,}"
        )
