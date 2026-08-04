"""Frame display with the four crop gestures: draw, stamp, move, and resize.

Coordinates convert straight from widget space to *source pixels*, never via
the proxy image the viewport happens to be showing. The proxy is a display
detail that can change resolution between frames; the ROI a user draws must
not. The precision limit is therefore the screen — which is the honest limit,
and the one the magnifier below exists to raise.

**Two rectangles, and the difference between them is load-bearing.**
`content_rect` is where the source lands when it is aspect-fitted into the
widget: it is a function of the widget size and the source size and nothing
else. `view_rect` is where the source is actually *painted*, which is
`content_rect` magnified about a pan centre. Every mapping goes through
`view_rect`; `content_rect` survives as the thing `view_rect` is clamped
against, and that clamp is the whole zoom-floor rule. The clamp itself lives
in `gui/zoom.Magnifier`, which is where its reasoning is — this widget owns
the fit and the source-pixel units, and the magnifier owns everything between
them.

**This widget owns the crop mode, and the tools panel is a view over it.**
The mode used to be a one-way panel→view push, which was fine only while the
panel was the sole thing that could change it. It is not: a completed draw
establishes a stamp size, and the gesture the user wants next is placing it,
so the *view* flips itself to `STAMP`. With two owners and no back-channel the
panel's radio buttons would go stale the moment that happened — a toggle
reading "draw" while clicks stamp is rule 6's mirror direction exactly. So
there is one owner, this one, because it is the widget that both acts on the
mode and has cause to change it; `set_mode` is idempotent and announces, and
the panel checks a button and emits a *request*. The echo that costs nothing
is what makes a guard unnecessary on either side.

**Adjustment is for the selected replicate only.** A dozen arenas each wearing
eight handles is an unreadable overlay, and the tab's other rule settles it
anyway: a click on a box the user is *not* tuning accepts it and moves them to
the filter tab, so the box under adjustment is by construction the selected
one. What that costs is that a box is selected in the table before it is
nudged, which is where the user already is while cutting a rack.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.zoom import MAX_ZOOM, MIN_ZOOM, ZOOM_STEP, Magnifier

__all__ = [
    "HANDLE_GRAB_PX",
    "HANDLE_PAINT_PX",
    "MAX_ZOOM",
    "MIN_DRAG_PX",
    "MIN_ZOOM",
    "NO_SELECTION",
    "ZOOM_STEP",
    "CropMode",
    "Handle",
    "VideoView",
]

#: A press-and-release shorter than this in both axes is a click, not a drag.
#: Below it there is no meaningful box, and treating it as one produces
#: one-pixel replicates every time a user misses a selection.
MIN_DRAG_PX = 6

#: Half-width of a handle's hit target, in widget pixels. The painted square is
#: smaller than this: a handle that is hard to grab is worse than one that looks
#: slightly larger than it is.
HANDLE_GRAB_PX = 7.0
HANDLE_PAINT_PX = 4.0

_BACKGROUND = QColor(24, 24, 27)
_LETTERBOX = QColor(16, 16, 18)
_HINT_TEXT = QColor(130, 130, 140)
_BOX = QColor(224, 224, 232)
_BOX_SELECTED = QColor(90, 170, 255)
_LABEL_BACKDROP = QColor(0, 0, 0, 170)
_DRAG = QColor(255, 255, 255)
_HANDLE_FILL = QColor(18, 18, 22)

NO_SELECTION = -1


class CropMode(StrEnum):
    """Whether a click on empty space draws a new box or places a stamp."""

    DRAW = "draw"
    STAMP = "stamp"


class Handle(IntEnum):
    """The eight grab points on the selected box."""

    TOP_LEFT = 0
    TOP = 1
    TOP_RIGHT = 2
    LEFT = 3
    RIGHT = 4
    BOTTOM_LEFT = 5
    BOTTOM = 6
    BOTTOM_RIGHT = 7


#: Which edges each handle moves, as (horizontal, vertical) in {-1, 0, +1}.
#: -1 is the leading edge, +1 the trailing one, 0 means that axis is untouched.
_HANDLE_EDGES: dict[Handle, tuple[int, int]] = {
    Handle.TOP_LEFT: (-1, -1),
    Handle.TOP: (0, -1),
    Handle.TOP_RIGHT: (+1, -1),
    Handle.LEFT: (-1, 0),
    Handle.RIGHT: (+1, 0),
    Handle.BOTTOM_LEFT: (-1, +1),
    Handle.BOTTOM: (0, +1),
    Handle.BOTTOM_RIGHT: (+1, +1),
}

_HANDLE_CURSORS: dict[Handle, Qt.CursorShape] = {
    Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    Handle.TOP: Qt.CursorShape.SizeVerCursor,
    Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    Handle.LEFT: Qt.CursorShape.SizeHorCursor,
    Handle.RIGHT: Qt.CursorShape.SizeHorCursor,
    Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    Handle.BOTTOM: Qt.CursorShape.SizeVerCursor,
    Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
}


@dataclass(frozen=True, slots=True)
class _Adjustment:
    """A live move or resize of one existing box.

    `roi` is the geometry at the moment of the press, and every step of the
    gesture is computed from *it* rather than from the document's current
    value. Accumulating deltas instead would let rounding compound across a
    long drag, and a box that ends a few pixels from where the cursor says is
    exactly the failure a rack of identical arenas cannot absorb.
    """

    row: int
    #: None for a move; a handle for a resize.
    handle: Handle | None
    roi: ROI
    origin: QPointF
    token: int

    @property
    def verb(self) -> str:
        """What the Edit menu should call this gesture."""
        return "Resize" if self.handle is not None else "Move"


class VideoView(QWidget):
    """Letterboxed frame viewport that draws, places, and adjusts regions."""

    #: A drag completed, or a stamp was placed: a new region in source pixels.
    roi_drawn = Signal(ROI)
    #: A click selected a replicate row, or `NO_SELECTION` for empty space.
    selection_requested = Signal(int)
    #: A live move or resize: row, geometry, the token identifying which
    #: gesture it belongs to, and the verb for the Edit menu. Every step of one
    #: drag carries the same token so the undo stack can collapse them — see
    #: `commands.SetReplicateROI`. The verb rides along because only the view
    #: knows whether a handle or the box body was grabbed, and "Undo Resize" on
    #: a drag that moved a box is a small lie the menu does not have to tell.
    roi_adjusted = Signal(int, ROI, int, str)
    #: The button came up on a move or resize: row and the same token. The end
    #: of the gesture is a fact only this widget holds — `roi_adjusted` looks
    #: identical on the last step and on every step before it — and a rule that
    #: has to run once per drag rather than once per pixel needs to be told.
    #: The geometry lock (`ReplicateDocument.finish_roi_gesture`) is that rule.
    #: Emitted after the final `roi_adjusted`, so a receiver sees the geometry
    #: the gesture reached and not the one before it.
    roi_adjust_finished = Signal(int, int)
    #: The stamp's size moved: a region was drawn, or the replicate being
    #: tuned changed and the stamp took its extent. Carries source pixels.
    stamp_size_changed = Signal(int, int)
    #: The crop mode changed, carrying a `CropMode` value. This widget owns the
    #: mode (see the module docstring); the tools panel follows this signal.
    mode_changed = Signal(str)
    #: The magnification changed, as a multiple of the fit scale.
    zoom_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)

        self._image: QImage | None = None
        self._source_size: tuple[int, int] | None = None
        self._replicates: list[Replicate] = []
        self._selected = NO_SELECTION
        self._drag_origin: QPoint | None = None
        self._drag_current: QPoint | None = None
        self._adjustment: _Adjustment | None = None
        self._gesture_serial = 0
        self._mode = CropMode.DRAW
        self._stamp_size: tuple[int, int] | None = None
        self._magnifier = Magnifier()
        self._hint = "File ▸ Open Video…   (Ctrl+O)"

    # ---- content ---------------------------------------------------------

    def set_source_size(self, size: tuple[int, int] | None) -> None:
        """Set the source dimensions ROIs are expressed in, or None to clear."""
        self._source_size = size
        if size is None:
            self._image = None
            self._replicates = []
            self._selected = NO_SELECTION
        self._cancel_gesture()
        self.reset_zoom()
        self.setCursor(
            Qt.CursorShape.CrossCursor if size is not None else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def set_frame(self, image: QImage) -> None:
        """Display a decoded frame."""
        self._image = image
        self.update()

    def set_replicates(self, replicates: list[Replicate]) -> None:
        """Replace the overlay boxes."""
        self._replicates = replicates
        self._take_stamp_from_selection()
        self.update()

    def set_selected(self, index: int) -> None:
        """Highlight one replicate, or `NO_SELECTION` for none."""
        if index == self._selected:
            return
        self._selected = index
        self._take_stamp_from_selection()
        self.update()

    def set_hint(self, text: str) -> None:
        """Message shown when no frame is loaded."""
        self._hint = text
        self.update()

    # ---- tools -----------------------------------------------------------

    @property
    def mode(self) -> CropMode:
        """Whether a click on empty space draws or stamps."""
        return self._mode

    def set_mode(self, mode: CropMode) -> None:
        """Choose between drawing a box and stamping the remembered size.

        Idempotent, and that is load-bearing rather than tidy: the tools panel
        follows `mode_changed` by checking a radio button, which emits its own
        request straight back here, and the early return is what stops that
        round trip at one lap.
        """
        if mode is self._mode:
            return
        self._mode = mode
        self.mode_changed.emit(mode)

    @property
    def stamp_size(self) -> tuple[int, int] | None:
        """Size a stamp will place, or None until one has been established."""
        return self._stamp_size

    def set_stamp_size(self, width: int, height: int) -> None:
        """Set the size a stamp places, in source pixels.

        Does not echo `stamp_size_changed`: this is the setter the tools panel
        calls when its own fields are typed into, and a signal back would race
        the widget that sent it. Only a size this widget *decides* — a drawn
        region, or the selection moving — announces itself.
        """
        if width <= 0 or height <= 0:
            return
        self._stamp_size = (width, height)

    def _take_stamp_from_selection(self) -> None:
        """The stamp takes the extent of the replicate being tuned.

        The vision's third claim: a stamp is placed "based on the highlighted
        replicate". Written into the one stamp size rather than read at
        placement time, and the difference is rule 6. The panel shows the stamp
        size in a field beside the button that applies it to the whole rack; a
        placement that quietly used the selection instead would leave that
        field reading one number while clicks produced another, every time a
        box of a different size was highlighted. Writing it means there stays
        exactly one stamp size, it is on screen, and a typed one stands until
        the selection actually moves.

        Called from both `set_selected` and `set_replicates` because either can
        change the answer — the second is what makes the stamp follow a box
        being resized by its handles, not merely one being clicked.
        """
        if not 0 <= self._selected < len(self._replicates):
            return
        roi = self._replicates[self._selected].roi
        if self._stamp_size == (roi.width, roi.height):
            return
        self._stamp_size = (roi.width, roi.height)
        self.stamp_size_changed.emit(roi.width, roi.height)

    @property
    def zoom(self) -> float:
        """Magnification as a multiple of the fit scale. 1.0 is fitted."""
        return self._magnifier.zoom

    def reset_zoom(self) -> None:
        """Return to the fitted view."""
        if self._magnifier.reset():
            self.zoom_changed.emit(self._magnifier.zoom)
        self.update()

    # ---- geometry --------------------------------------------------------

    def content_rect(self) -> QRectF:
        """Aspect-fit rectangle the source occupies inside this widget.

        The magnifier's floor, and the letterbox the magnified image is clipped
        to. Not the mapping — that is `view_rect`.
        """
        if self._source_size is None:
            return QRectF(self.rect())
        source_width, source_height = self._source_size
        if source_width <= 0 or source_height <= 0:
            return QRectF(self.rect())

        available = QRectF(self.rect())
        scale = min(available.width() / source_width, available.height() / source_height)
        width = source_width * scale
        height = source_height * scale
        return QRectF(
            available.x() + (available.width() - width) / 2.0,
            available.y() + (available.height() - height) / 2.0,
            width,
            height,
        )

    def view_rect(self) -> QRectF:
        """Where the source is painted: `content_rect` magnified and panned.

        The magnifier holds the clamp and the reasoning for it; with no source
        there is no magnification to apply, so the fit is returned unchanged.
        """
        fit = self.content_rect()
        if self._source_size is None:
            return fit
        return self._magnifier.view_rect(fit)

    def source_at(self, point: QPointF) -> QPointF:
        """Widget point as a source coordinate, unrounded and unclamped.

        The magnifier speaks in normalized content coordinates; source pixels
        are this widget's own unit, so the scaling happens here.
        """
        if self._source_size is None:
            return QPointF()
        source_width, source_height = self._source_size
        normalized = self._magnifier.at(point, self.content_rect())
        return QPointF(normalized.x() * source_width, normalized.y() * source_height)

    def to_source(self, point: QPointF) -> tuple[int, int]:
        """Widget point to source pixel, clamped inside the frame."""
        if self._source_size is None:
            return (0, 0)
        source_width, source_height = self._source_size
        view = self.view_rect()
        if view.width() <= 0 or view.height() <= 0:
            return (0, 0)
        source = self.source_at(point)
        return (
            int(min(max(round(source.x()), 0), source_width)),
            int(min(max(round(source.y()), 0), source_height)),
        )

    def to_widget(self, roi: ROI) -> QRectF:
        """Source-pixel ROI to widget rectangle."""
        if self._source_size is None:
            return QRectF()
        source_width, source_height = self._source_size
        view = self.view_rect()
        scale_x = view.width() / source_width
        scale_y = view.height() / source_height
        return QRectF(
            view.x() + roi.x * scale_x,
            view.y() + roi.y * scale_y,
            roi.width * scale_x,
            roi.height * scale_y,
        )

    def _placed(self, x: int, y: int, width: int, height: int) -> ROI:
        """A region of exactly `width` x `height` slid to lie inside the source.

        The rule itself is `ROI.placed_in`, which is where the argument for
        sliding rather than trimming lives. It moved to typed numbers when the
        tools panel's "Set all" needed the same rule from the document side: a
        second copy of a clamp is how a stamp and a batch resize end up
        disagreeing about what happens at the frame edge, which is the one place
        either of them is interesting.
        """
        return ROI.placed_in(x, y, width, height, self._source_size)

    def _replicate_at(self, point: QPointF) -> int:
        """Topmost replicate containing `point`, or `NO_SELECTION`."""
        for index in reversed(range(len(self._replicates))):
            if self.to_widget(self._replicates[index].roi).contains(point):
                return index
        return NO_SELECTION

    def _handle_rects(self) -> dict[Handle, QRectF]:
        """Grab targets on the selected box, empty when nothing is selected."""
        if not 0 <= self._selected < len(self._replicates):
            return {}
        rect = self.to_widget(self._replicates[self._selected].roi)
        xs = (rect.left(), rect.center().x(), rect.right())
        ys = (rect.top(), rect.center().y(), rect.bottom())
        return {
            handle: QRectF(
                xs[horizontal + 1] - HANDLE_GRAB_PX,
                ys[vertical + 1] - HANDLE_GRAB_PX,
                HANDLE_GRAB_PX * 2.0,
                HANDLE_GRAB_PX * 2.0,
            )
            for handle, (horizontal, vertical) in _HANDLE_EDGES.items()
        }

    def _handle_at(self, point: QPointF) -> Handle | None:
        """Handle under `point`, or None.

        Corners are tested before edges — their targets overlap at a small box,
        and a corner is the more specific request.
        """
        rects = self._handle_rects()
        corners = (Handle.TOP_LEFT, Handle.TOP_RIGHT, Handle.BOTTOM_LEFT, Handle.BOTTOM_RIGHT)
        for handle in (*corners, *(h for h in Handle if h not in corners)):
            if handle in rects and rects[handle].contains(point):
                return handle
        return None

    # ---- input -----------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Magnify about the cursor, never below the fit."""
        if self._source_size is None:
            super().wheelEvent(event)
            return
        detents = event.angleDelta().y() / 120.0
        if detents == 0.0:
            super().wheelEvent(event)
            return

        if self._magnifier.wheel(detents, event.position(), self.content_rect()):
            self.zoom_changed.emit(self._magnifier.zoom)
            self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin a gesture: resize a handle, move the selected box, or draw.

        The handle test runs *before* the containment test, and that order is
        the bug it exists to prevent. A handle straddles its corner, so half of
        it lies outside the box it belongs to — and if that half lies inside a
        larger box behind, a containment-first test hands the press to the box
        behind and the corner is unreachable. Overlapping arenas are not exotic;
        one drawn slightly over its neighbour is a Tuesday.
        """
        if event.button() != Qt.MouseButton.LeftButton or self._source_size is None:
            super().mousePressEvent(event)
            return

        point = event.position()
        self._drag_origin = point.toPoint()
        self._drag_current = self._drag_origin
        self._adjustment = None

        handle = self._handle_at(point)
        if handle is not None:
            self._begin_adjustment(handle, point)
        elif self._over_movable_selection(point):
            self._begin_adjustment(None, point)
        self.update()

    def _over_movable_selection(self, point: QPointF) -> bool:
        """Whether a press here would move the selected box."""
        return 0 <= self._selected < len(self._replicates) and self.to_widget(
            self._replicates[self._selected].roi
        ).contains(point)

    def _begin_adjustment(self, handle: Handle | None, origin: QPointF) -> None:
        self._gesture_serial += 1
        self._adjustment = _Adjustment(
            row=self._selected,
            handle=handle,
            roi=self._replicates[self._selected].roi,
            origin=origin,
            token=self._gesture_serial,
        )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Extend the in-progress gesture, or track the cursor over handles."""
        if self._drag_origin is None:
            self._update_cursor(event.position())
            super().mouseMoveEvent(event)
            return
        point = event.position()
        self._drag_current = point.toPoint()
        if self._adjustment is not None and self._is_adjustment(QPointF(self._drag_origin), point):
            self._emit_adjustment(self._adjustment, point)
        self.update()

    @staticmethod
    def _is_adjustment(origin: QPointF, end: QPointF) -> bool:
        """Whether a press that began on the selected box has become a drag.

        Travel in *either* axis, which is the difference from the rule that
        governs drawing. A new region needs extent in both — a one-pixel-tall
        replicate is never what a user meant — but a box slid horizontally
        along a rack has travelled exactly as far as the user intended in the
        only axis they touched, and demanding a stray vertical pixel too would
        read that drag as a click and accept the replicate instead of moving
        it.
        """
        return abs(end.x() - origin.x()) >= MIN_DRAG_PX or abs(end.y() - origin.y()) >= MIN_DRAG_PX

    def _update_cursor(self, point: QPointF) -> None:
        """Show what a press here would do, before it is pressed."""
        if self._source_size is None:
            return
        handle = self._handle_at(point)
        if handle is not None:
            self.setCursor(_HANDLE_CURSORS[handle])
        elif self._over_movable_selection(point):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _emit_adjustment(self, adjustment: _Adjustment, point: QPointF) -> None:
        handle = adjustment.handle
        roi = (
            self._moved(adjustment, point)
            if handle is None
            else self._resized(adjustment, handle, point)
        )
        self.roi_adjusted.emit(adjustment.row, roi, adjustment.token, adjustment.verb)

    def _moved(self, adjustment: _Adjustment, point: QPointF) -> ROI:
        """The dragged box translated by the cursor's travel, size preserved."""
        start = self.source_at(adjustment.origin)
        now = self.source_at(point)
        roi = adjustment.roi
        return self._placed(
            round(roi.x + now.x() - start.x()),
            round(roi.y + now.y() - start.y()),
            roi.width,
            roi.height,
        )

    def _resized(self, adjustment: _Adjustment, handle: Handle, point: QPointF) -> ROI:
        """The dragged box with the handle's edges moved to the cursor.

        `ROI.from_corners` normalizes, so dragging an edge past its opposite
        flips the box rather than refusing — the standard behaviour of every
        drawing tool, and cheaper to live with than a gesture that sticks.
        """
        horizontal, vertical = _HANDLE_EDGES[handle]
        roi = adjustment.roi
        x, y = self.to_source(point)
        left = x if horizontal < 0 else roi.x
        right = x if horizontal > 0 else roi.right
        top = y if vertical < 0 else roi.y
        bottom = y if vertical > 0 else roi.bottom
        if left == right:
            right = left + 1
        if top == bottom:
            bottom = top + 1
        return ROI.from_corners(left, top, right, bottom).clamped_to(*self._source_size or (1, 1))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish a drag as a region, or a click as a selection or a stamp."""
        if event.button() != Qt.MouseButton.LeftButton or self._drag_origin is None:
            super().mouseReleaseEvent(event)
            return

        origin, self._drag_origin = self._drag_origin, None
        adjustment, self._adjustment = self._adjustment, None
        end = event.position()
        self._drag_current = None
        self.update()

        start = QPointF(origin)
        if adjustment is not None:
            # A press on the selected box that never travelled is a click on a
            # replicate, which the tab reads as accepting it. Adjustment and
            # acceptance therefore share a press and are told apart only here,
            # by whether the cursor went anywhere.
            if self._is_adjustment(start, end):
                self._emit_adjustment(adjustment, end)
                self.roi_adjust_finished.emit(adjustment.row, adjustment.token)
            else:
                self.selection_requested.emit(adjustment.row)
            return

        if abs(end.x() - start.x()) < MIN_DRAG_PX or abs(end.y() - start.y()) < MIN_DRAG_PX:
            self._release_click(end)
            return

        x0, y0 = self.to_source(QPointF(origin))
        x1, y1 = self.to_source(end)
        roi = ROI.from_corners(x0, y0, x1, y1)
        if roi.width > 0 and roi.height > 0:
            # Every drawn region sets the stamp, in both modes. Drawing is how
            # the vision says a stamp size is established ("the stamp needs to
            # be drawn first"), and making that a mode-specific side effect
            # would mean switching to stamp mode *before* the draw that defines
            # it — an ordering nobody would guess.
            self._stamp_size = (roi.width, roi.height)
            self.stamp_size_changed.emit(roi.width, roi.height)
            # And stamping is what the user wants next. Drawing the first arena
            # of a rack is how the size gets established; the eleven after it
            # are placements, so the tool that costs no gesture to reach should
            # be the one they need eleven times, not the one they needed once.
            # The flip forecloses nothing: the mode is consulted only in
            # `_release_click`, so a drag draws in either mode and this changes
            # what a *click* means and nothing else.
            self.set_mode(CropMode.STAMP)
            self.roi_drawn.emit(roi)

    def _release_click(self, point: QPointF) -> None:
        """A click that travelled nowhere: stamp on empty space, else select."""
        row = self._replicate_at(point)
        if row != NO_SELECTION or self._mode is not CropMode.STAMP or self._stamp_size is None:
            self.selection_requested.emit(row)
            return
        width, height = self._stamp_size
        x, y = self.to_source(point)
        self.roi_drawn.emit(self._placed(x - width // 2, y - height // 2, width, height))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Escape abandons an in-progress gesture."""
        if event.key() == Qt.Key.Key_Escape and self._drag_origin is not None:
            self._cancel_gesture()
            return
        super().keyPressEvent(event)

    def _cancel_gesture(self) -> None:
        """Drop any live gesture, putting an adjusted box back where it was.

        The restore goes out under the gesture's own token, so it merges into
        the same undo entry the drag has been building and the whole abandoned
        gesture collapses to nothing rather than to a no-op step the user has
        to press Ctrl+Z through.
        """
        adjustment, self._adjustment = self._adjustment, None
        self._drag_origin = None
        self._drag_current = None
        if adjustment is not None:
            self.roi_adjusted.emit(
                adjustment.row, adjustment.roi, adjustment.token, adjustment.verb
            )
        self.update()

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the frame, then the replicate overlay."""
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _LETTERBOX)

        if self._image is None or self._source_size is None:
            self._paint_hint(painter)
            painter.end()
            return

        content = self.content_rect()
        painter.fillRect(content, _BACKGROUND)
        # Everything after this is clipped to the fitted box, so a magnified
        # source spills into the letterbox no more than a fitted one does.
        painter.setClipRect(content)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self.view_rect(), self._image)

        self._paint_replicates(painter)
        self._paint_handles(painter)
        self._paint_drag(painter)
        painter.end()

    def _paint_hint(self, painter: QPainter) -> None:
        painter.setPen(QPen(_HINT_TEXT))
        font = QFont(painter.font())
        font.setPointSizeF(font.pointSizeF() + 1.0)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._hint)

    def _paint_replicates(self, painter: QPainter) -> None:
        label_font = QFont(painter.font())
        label_font.setPointSizeF(max(label_font.pointSizeF() - 0.5, 6.0))
        painter.setFont(label_font)
        metrics = painter.fontMetrics()

        for index, replicate in enumerate(self._replicates):
            selected = index == self._selected
            colour = QColor(_BOX_SELECTED if selected else _BOX)
            rect = self.to_widget(replicate.roi)

            painter.setPen(QPen(colour, 2.0 if selected else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            label = replicate.name
            text_width = metrics.horizontalAdvance(label)
            backdrop = QRectF(
                rect.x(),
                max(rect.y() - metrics.height() - 2.0, 0.0),
                text_width + 8.0,
                metrics.height() + 2.0,
            )
            painter.fillRect(backdrop, QBrush(_LABEL_BACKDROP))
            painter.setPen(QPen(colour))
            painter.drawText(
                backdrop.adjusted(4.0, 0.0, 0.0, 0.0),
                Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def _paint_handles(self, painter: QPainter) -> None:
        painter.setPen(QPen(_BOX_SELECTED, 1.0))
        painter.setBrush(QBrush(_HANDLE_FILL))
        for rect in self._handle_rects().values():
            inset = HANDLE_GRAB_PX - HANDLE_PAINT_PX
            painter.drawRect(rect.adjusted(inset, inset, -inset, -inset))

    def _paint_drag(self, painter: QPainter) -> None:
        if self._drag_origin is None or self._drag_current is None or self._adjustment is not None:
            return
        pen = QPen(_DRAG, 1.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        box = QRectF(QPointF(self._drag_origin), QPointF(self._drag_current))
        painter.drawRect(box.normalized())
