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
that is `timeline_model.Geometry`, rebuilt per paint and per click.

**Three mouse events, three claims.** A press is a position the user has
committed to and is where the window rule is applied. A move is a guess they are
still refining, so it scrubs — the player coalesces those and may serve them
coarse. A release is the commitment again, and is what guarantees they land
exactly where they let go however coarse the drag was. Collapsing any two of
them either makes the drag decode every pixel or leaves the user a frame or two
from where they stopped.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import ClipRange
from sieve.core.types import VideoMetadata
from sieve.gui.document import ReplicateDocument
from sieve.gui.player import VideoPlayer
from sieve.gui.timeline_model import Geometry

#: Height of the band. Tall enough to be a target for a mouse rather than a
#: hairline to be aimed at, and sized now for the coverage and detection lanes
#: that land in it later (`docs/todo/coverage-and-detection-lanes.md`) rather
#: than grown when they arrive.
STRIP_HEIGHT = 44

#: Vertical inset of the painted track inside that height.
_TRACK_INSET = 4.0

_PLAY_GLYPH = "▶"
_PAUSE_GLYPH = "⏸"

_TRACK = QColor(30, 30, 36)
_WINDOW = QColor(90, 170, 255, 70)
_WINDOW_EDGE = QColor(90, 170, 255)
_PLAYHEAD = QColor(240, 240, 245)

_EMPTY_HINT = "Open a video to begin"


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
    `timeline_model.py` or in the document.
    """

    #: Mouse-down. A committed position, and where the window rule is applied.
    pressed = Signal(int)
    #: A drag position. A guess, which the player may serve approximately.
    scrubbed = Signal(int)
    #: Mouse-up. The commitment again: land here exactly.
    committed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame_count = 0
        self._window: ClipRange | None = None
        self._playhead = 0
        self._dragging = False
        self.setFixedHeight(STRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.SizeHorCursor)

    # ---- what it paints --------------------------------------------------

    def set_source_frames(self, frame_count: int) -> None:
        """Establish the asset's length, which is the whole horizontal axis."""
        self._frame_count = max(frame_count, 0)
        self.update()

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

    def window_rect(self) -> QRectF:
        """Where the working window is painted, empty when there is none.

        Exposed because it is the claim worth testing — that the band lands
        under the frames it names — and a painted pixel is not something a test
        can ask about.
        """
        geometry = self.geometry_now()
        if self._window is None or geometry.is_empty:
            return QRectF()
        left, right = geometry.span(self._window.start, self._window.end)
        return QRectF(left, _TRACK_INSET, right - left, self.height() - 2.0 * _TRACK_INSET)

    def playhead_x(self) -> float:
        """Centre of the column the playhead sits in."""
        return self.geometry_now().centre_of_frame(self._playhead)

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
            painter.setPen(QPen(_WINDOW_EDGE, 1.0))
            painter.drawRect(window.adjusted(0.5, 0.5, -0.5, -0.5))

        x = self.playhead_x()
        painter.setPen(QPen(_PLAYHEAD, 1.0))
        painter.drawLine(QPointF(x, 0.0), QPointF(x, float(self.height())))
        painter.end()

    # ---- scrubbing -------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Take the position under the cursor as a committed one."""
        if self.geometry_now().is_empty or event.button() is not Qt.MouseButton.LeftButton:
            return
        self._dragging = True
        self.pressed.emit(self.geometry_now().frame_at(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Follow the drag. A guess, and the player is allowed to approximate it."""
        if not self._dragging:
            return
        self.scrubbed.emit(self.geometry_now().frame_at(event.position().x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Land exactly where the user let go, however coarse the drag was."""
        if not self._dragging or event.button() is not Qt.MouseButton.LeftButton:
            return
        self._dragging = False
        self.committed.emit(self.geometry_now().frame_at(event.position().x()))


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

        self._document.clip_changed.connect(self._on_window_changed)

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
