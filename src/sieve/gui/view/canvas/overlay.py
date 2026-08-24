"""The crop, over the stage: the box that is set and the drag that sets one.

The second half of what a canvas is, which `canvas/view.py` says is coming and
names the terms for. It is a sibling of the content rather than something the
content draws, and that is the whole reason it exists as a file: `VideoCanvas`
scales one frame and knows nothing about crops, and a canvas that painted a
rectangle into the array it was handed would be copying a full frame every tick
to draw four lines — and mutating a frame the store may have admitted.

**It takes the stage rect and computes nothing.** `Canvas.staged` exists so that
what a crop box is drawn against is the same rectangle the content was placed
in. This connects to it and follows the parent's geometry from the same signal,
because the two change together: a stage moves when the pane resizes, and that
is exactly when an overlay sized to the old pane would be drawing the box
somewhere the picture no longer is.

**The gesture leaves in this widget's coordinates.** The explorers' `CropCanvas`
emits the drawn rect in label coordinates "because only it knows what the label
is showing", and the mapping to source pixels — offsets, scale, clamp, even-snap
— belongs to whatever knows what is on the stage. Kept, and for a second reason
they do not state: mapping here would mean clamping here, and a clamp needs the
frame size, which would make this the second place a crop is decided.

**The return direction is not symmetric, and not a second mapping.**
`show_crop` takes source pixels and draws them, which means it maps — but
through `analysis.crop.to_placed`, the same module the owner maps *out* through,
so there is one implementation of the arithmetic read both ways. The asymmetry
is between deciding and displaying: a gesture becomes a crop only once something
has clamped it, and a crop already decided is just a rectangle to draw. Doing it
here rather than having the owner push widget coordinates is what lets a resize
redraw the box correctly with no round trip — and a round trip is a frame in
which the box is drawn where the crop is not.

**Refusing is said, not silently done.** A rectangle dragged over a cropped view
is about a picture that is already a crop, and the arithmetic back to source is
a different sum. The explorer refuses that in words; so does this, by emitting
`refused` with the sentence rather than by ignoring the mouse — a gesture that
does nothing and says nothing reads as a broken canvas.

What is not here: handles. Resizing an existing box by its corners is a second
gesture with its own hit-testing and its own cursor states, the number boxes are
already the other editor, and neither explorer has ever had one.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.analysis import crop as crop_math
from sieve.gui.palette import ACCENT, STACK_BG

#: How wide and tall a band must be, in widget pixels, before a release counts
#: as a drag. Compared against the band's own extents and not against how far
#: the hand travelled, which are not the same number: a `QRect` between two
#: points spans one more pixel than the distance between them, so a hand moving
#: exactly this far produces a band that passes. Carried from the explorers,
#: comparison and all, where the line reads `a drag, not a click`. Without it a
#: stray click on the picture is a rectangle of nothing, which the clamp then
#: floors to `crop.MINIMUM` — so the cheapest possible misclick would set the
#: smallest legal crop and drop every frame derived from the old one.
DRAG_MIN = 8

#: How much of the ground is laid over the pixels a crop leaves out. An outline
#: alone says where the boundary is and not which side of it is kept, which is
#: unreadable exactly when the box runs to an edge of the frame and only three
#: of its sides are visible.
SCRIM = 110

#: The sentence a drag over anything but the whole frame is refused with. Here
#: rather than at the emit so that it is one sentence, and a caller that wants
#: to show it somewhere other than where this is raised can read it.
NOT_FULL_FRAME = ("drawing a crop needs the whole frame on the stage — show it, "
                  "then drag the rectangle")


class CropOverlay(QWidget):
    """The crop box over a stage, and the rubber band that draws a new one."""

    #: A finished drag, in this widget's coordinates, forwards on both axes.
    #: Not a crop: nothing has clamped it, and until something has, it is a
    #: rectangle somebody drew over a picture.
    drawn = Signal(QRect)

    #: A gesture that was not allowed, with the reason as a sentence.
    refused = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cropoverlay")
        # Painted over live video, so only what is drawn should land. Without
        # this the widget fills its whole rect with the palette's window colour
        # first and the frame under it is gone.
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._stage = QRect()
        self._frame: tuple[int, int] | None = None
        self._crop: crop_math.Rect | None = None
        self._origin: QPoint | None = None
        self._band: QRect | None = None
        self._allowed = True
        self._reason = NOT_FULL_FRAME

    # -- what it is drawn against -----------------------------------------
    def set_stage(self, rect: QRect) -> None:
        """Where the picture landed, from `Canvas.staged`.

        Also the moment to match the parent, which is the widget the stage rect
        is measured in. Done here rather than in a `resizeEvent` of its own
        because an overlay that resized on its own schedule could be following
        a geometry the stage had already left.
        """
        self._stage = QRect(rect)
        parent = self.parentWidget()
        if parent is not None and self.geometry() != parent.rect():
            self.setGeometry(parent.rect())
        self.update()

    def set_frame_size(self, width: int, height: int) -> None:
        """The source's own dimensions, which the box is expressed in."""
        self._frame = (int(width), int(height)) if width > 0 and height > 0 \
            else None
        self.update()

    def stage(self) -> QRect:
        return QRect(self._stage)

    # -- the box that is set ----------------------------------------------
    def show_crop(self, rect: crop_math.Rect | None) -> None:
        """Draw a crop, in source pixels. `None` draws no box at all.

        Named for `NumberBox.show_value` and `VideoCanvas.show_frame` and not
        for what it is showing, because all three are the same verb: an owner
        that has decided something tells the widget, and the widget does not
        answer back.
        """
        self._crop = None if rect is None else tuple(int(v) for v in rect)
        self.update()

    def crop(self) -> crop_math.Rect | None:
        return self._crop

    # -- whether a drag is allowed ----------------------------------------
    def allow(self, allowed: bool, reason: str = NOT_FULL_FRAME) -> None:
        """Whether a drag is about the whole frame, and what to say if not.

        Passed in rather than worked out: whether the picture on the stage is
        the whole frame is a fact about the session's form, and an overlay that
        decided it would be reading a session it has no business holding.
        """
        self._allowed = allowed
        self._reason = reason

    def allowed(self) -> bool:
        return self._allowed

    def band(self) -> QRect | None:
        """The gesture in progress, or `None`. For anything watching a drag."""
        return None if self._band is None else QRect(self._band)

    # -- the drag ---------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        point = event.position().toPoint()
        if not self._stage.contains(point):
            # Started on the letterbox. Not a refusal — there is no picture
            # there, so there is nothing to have meant by it.
            event.ignore()
            return
        if not self._allowed:
            self.refused.emit(self._reason)
            return
        self._origin = point
        self._band = QRect(point, point)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is None:
            return
        # Clipped to the stage, so a drag that runs off the picture ends at its
        # edge rather than producing a rectangle the clamp has to rescue. The
        # clamp would rescue it; a band drawn out over the letterbox would
        # still have claimed for a moment that pixels exist there.
        here = _inside(event.position().toPoint(), self._stage)
        self._band = QRect(self._origin, here).normalized()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        del event
        if self._origin is None:
            return
        band = self._band
        self._origin = None
        self._band = None
        self.update()
        if band is None:
            return
        if band.width() > DRAG_MIN and band.height() > DRAG_MIN:
            self.drawn.emit(band)

    # -- what it looks like -----------------------------------------------
    def paintEvent(self, event) -> None:
        del event
        if self._stage.isEmpty():
            return
        painter = QPainter(self)
        box = self._box()
        if box is not None:
            self._scrim(painter, box)
            painter.setPen(QPen(ACCENT, 1))
            painter.drawRect(box.adjusted(0, 0, -1, -1))
        if self._band is not None:
            # A dashed band while the hand is moving, solid once it is a crop.
            # The difference is between a rectangle being drawn and one that
            # has been accepted, and the clamp means the two are not always the
            # same rectangle — a band that looked identical to the box that
            # followed it would make that correction invisible.
            painter.setPen(QPen(ACCENT, 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._band.adjusted(0, 0, -1, -1))
        painter.end()

    def _box(self) -> QRect | None:
        """The set crop, in this widget's coordinates. One mapping, borrowed."""
        if self._crop is None or self._frame is None or self._stage.isEmpty():
            return None
        placed = (self._stage.x(), self._stage.y(),
                  self._stage.width(), self._stage.height())
        x, y, width, height = crop_math.to_placed(
            self._crop, placed, self._frame[0], self._frame[1])
        return QRect(x, y, width, height)

    def _scrim(self, painter: QPainter, box: QRect) -> None:
        """Ground over the pixels the crop leaves out, in four bands.

        Four fills of the difference rather than one fill and a cut-out,
        because a cut-out is a clip region and this runs on the thread that
        draws, once per repaint, over live video.
        """
        shade = QColor(STACK_BG)
        shade.setAlpha(SCRIM)
        kept = box.intersected(self._stage)
        stage = self._stage
        painter.fillRect(QRect(stage.left(), stage.top(),
                               stage.width(), kept.top() - stage.top()), shade)
        painter.fillRect(QRect(stage.left(), kept.bottom() + 1,
                               stage.width(), stage.bottom() - kept.bottom()),
                         shade)
        painter.fillRect(QRect(stage.left(), kept.top(),
                               kept.left() - stage.left(), kept.height()),
                         shade)
        painter.fillRect(QRect(kept.right() + 1, kept.top(),
                               stage.right() - kept.right(), kept.height()),
                         shade)


def _inside(point: QPoint, rect: QRect) -> QPoint:
    """`point` pulled back onto `rect`, on whichever axes it left it."""
    return QPoint(max(rect.left(), min(point.x(), rect.right())),
                  max(rect.top(), min(point.y(), rect.bottom())))


def over(canvas, allowed: bool = True) -> CropOverlay:
    """An overlay parented to a canvas, wired to its stage and raised.

    A function rather than something the canvas does, because a canvas that
    made one of these would be a canvas that knows what a crop is — and the
    thing it is a stage for is not always footage. Three lines, in one place,
    so that the wiring cannot be got half right by the second caller.
    """
    overlay = CropOverlay(canvas)
    overlay.allow(allowed)
    canvas.staged.connect(overlay.set_stage)
    overlay.set_stage(canvas.stage())
    overlay.show()
    overlay.raise_()
    return overlay
