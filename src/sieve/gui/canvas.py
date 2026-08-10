"""The viewport: the composite it was last handed, drawn to fit.

Nothing here decides which frames are shown. It is handed them, it paints them,
and it holds them only so a resize has something to redraw — the playhead is
`transport/player.py`'s, the window is `timeline/bar.py`'s, and *which* frames a
source index now has is `app.py`'s, since only the window knows where the walk
is standing. A copy of any of the three here would be the stale one.

**Two layers, one rectangle: the walked step's result over that step's input**
(`adr/the-walked-step-owns-the-canvas.md`). What makes tuning legible is seeing
what the step *did*, which is a comparison and not a picture, so the input is
painted whole and the result over it at an opacity the user holds. Both go into
the same rect — the input is a different node's output and may be a different
size, and drawing it anywhere else would be two pictures side by side rather
than one composite. The pair comes off one render (`gui/tuning.render_at`); the
opacity is the only thing about the picture this widget decides.

Aspect ratio is preserved and the frame is never enlarged past its own pixels:
the decode side already hands back a proxy sized for display
(`transport/decode_worker.PROXY_WIDTH`), so upscaling here would invent detail
the user would then judge footage by.

**The badge says what is shown, not that it is stale.** The source frame stands
in for the watched node's output in four cases — before the first render, while
a drag is in flight, for a node with no picture, and after a render that failed
— and the frame it puts up is at the *correct* index, so "stale" is the wrong
word for it and `graph_panel`'s mark is the wrong mark. What the user cannot
otherwise tell is whose picture it is, which on a node whose output is a mask or
a difference is a change of kind. The state is raised by the one caller that
knows (`app._paint_viewport`) and lowered only by a render landing.

**What a result looks like is not decided here.** A frame and a block grid are
different pictures of the same kind of array, and which one a node's output makes
is `emission_paint.py`'s — including the range each is coloured against, which
the two entries answer differently on purpose. This widget is handed the kind
along with the values and dispatches; it does not know which tools exist.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QSlider, QVBoxLayout, QWidget

from sieve.core.tool_base import ElementKind
from sieve.gui.emission_paint import BlockField, picture_of
from sieve.gui.zoom import Magnifier

_BACKGROUND = QColor(18, 18, 22)
_HINT = QColor(120, 120, 130)
_EMPTY_HINT = "No frame"
_SOURCE_BADGE = "source"

#: Where the overlay starts, as a percentage. v2's number and its reason: high
#: enough that a binary mask is unmissable, low enough that the input stays
#: legible under it.
DEFAULT_OPACITY = 65

#: The slider's label. The step's own name is the card's, and repeating it here
#: would be a second answer to which step the canvas is about.
_OPACITY_LABEL = "result"


class VideoCanvas(QWidget):
    """Draws the most recent composite, centred, letterboxed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame: QImage | None = None
        self._field: BlockField | None = None
        self._under: QImage | None = None
        self._opacity = DEFAULT_OPACITY / 100.0
        self._showing_source = False
        self._magnifier = Magnifier()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @property
    def frame(self) -> QImage | None:
        """The image on screen, or None before the first frame arrives.

        None also for a result that is not an image — a block field is drawn as
        cells and has no frame of its own, which is `field` below.
        """
        return self._frame

    @property
    def field(self) -> BlockField | None:
        """The cells on screen, or None when what is shown is an image."""
        return self._field

    @property
    def under(self) -> QImage | None:
        """What the result is drawn over, or None when it is drawn alone."""
        return self._under

    @property
    def overlay_opacity(self) -> float:
        """How much of the result is drawn over its input, in 0..1."""
        return self._opacity

    @overlay_opacity.setter
    def overlay_opacity(self, value: float) -> None:
        self._opacity = min(max(float(value), 0.0), 1.0)
        self.update()

    @property
    def showing_source(self) -> bool:
        """Whether what is drawn is the footage standing in for a node's output."""
        return self._showing_source

    def mark_source(self) -> None:
        """The frame just handed over is the source, not the watched node's output."""
        self._showing_source = True
        self.update()

    def badge_text(self) -> str:
        """The word drawn over the picture, empty when the picture speaks for itself."""
        return _SOURCE_BADGE if self._showing_source and self._frame is not None else ""

    def set_frame(self, index: int, image: QImage) -> None:
        """Show `image` alone. `index` is accepted and ignored — the readout is the bar's."""
        del index
        self._frame = image
        # The one frame the window can produce without asking the graph is the
        # source, and it is nothing's result: leaving the previous step's input
        # under it, or the cells of a step it is not the output of, would compose
        # two pictures the user never asked to compare.
        self._field = None
        self._under = None
        self.update()

    def set_values(
        self,
        index: int,
        values: NDArray[np.float32],
        under: QImage | None = None,
        *,
        kind: ElementKind | None = ElementKind.PIXEL,
        span: tuple[float, float] = (0.0, 1.0),
    ) -> bool:
        """Show `values` over `under`. False, and nothing shown, if they are no picture.

        The refusal is returned rather than raised because the caller has a
        second frame in hand for exactly this case — the source — and a node
        whose output is not an image is an ordinary place for the walk to stand,
        not an error. It is the *result* that decides: an input with no picture
        in it leaves the result drawn alone, which is a step composed over
        nothing rather than a step that cannot be shown.

        `kind` and `span` are handed over rather than looked up (`emission_paint`
        says why): the first decides which picture the values make, the second is
        the range a field is coloured against and is `graph_panel.value_range`'s
        answer. A field is refused where there is nothing under it, and that is
        not the input-less case above: cells have no pixels of their own, so
        without an input they have neither a letterbox to fill nor anything to be
        a measurement *of*.
        """
        del index
        picture = picture_of(kind, values, span)
        if picture is None:
            return False
        field = picture if isinstance(picture, BlockField) else None
        if field is not None and under is None:
            return False
        self._frame = None if field is not None else picture
        self._field = field
        self._under = under
        # A render is the watched node's output by definition, which is the one
        # thing that displaces the badge. The refusal above leaves it alone: the
        # caller's next move is to hand back the source and raise it again, and
        # clearing in between would drop the mark on every repaint of a node
        # that has no picture at all.
        self._showing_source = False
        return True

    def clear(self) -> None:
        """Return to the empty state. The source has gone."""
        self._frame = None
        self._field = None
        self._under = None
        self._showing_source = False
        self.update()

    def frame_rect(self) -> QRectF:
        """Where the picture is painted, empty when there is none.

        Exposed for the same reason the strip exposes its rects: a painted pixel
        is not something a test can ask about, and "the footage is not stretched"
        is a claim about this rectangle.

        A field's letterbox is its *input's*, because cells have no pixels of
        their own: fitting the widget to an `(ny, nx)` grid would letterbox the
        footage to the block aspect and put the picture somewhere the frame is
        not.
        """
        image = self._frame if self._frame is not None else self._under
        if image is None or image.isNull():
            return QRectF()
        scale = min(self.width() / image.width(), self.height() / image.height(), 1.0)
        width = image.width() * scale
        height = image.height() * scale
        return QRectF((self.width() - width) / 2.0, (self.height() - height) / 2.0, width, height)

    def view_rect(self) -> QRectF:
        """Where the frame is *painted*: `frame_rect` magnified and panned.

        The mapping every overlay goes through, and the difference from the fit
        is the whole of `zoom.py`. Nothing to magnify with no frame, so the
        empty fit is returned as it is rather than scaled up into a rectangle
        about nothing.
        """
        fit = self.frame_rect()
        if fit.isEmpty():
            return fit
        return self._magnifier.view_rect(fit)

    @property
    def zoom(self) -> float:
        """Magnification as a multiple of the fit scale. 1.0 is fitted."""
        return self._magnifier.zoom

    def reset_zoom(self) -> None:
        """Return to the fitted view."""
        self._magnifier.reset()
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Magnify about the cursor, never below the fit.

        Declined outright when there is nothing on screen, so the wheel keeps
        whatever meaning the enclosing widget gives it rather than being
        swallowed by a viewport that would do nothing with it.
        """
        detents = event.angleDelta().y() / 120.0
        if detents == 0.0 or self.frame_rect().isEmpty():
            super().wheelEvent(event)
            return
        if self._magnifier.wheel(detents, event.position(), self.frame_rect()):
            self.update()
        event.accept()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND)
        box = self.frame_rect()
        if box.isEmpty() or (self._frame is None and self._field is None):
            painter.setPen(_HINT)
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), _EMPTY_HINT)
            painter.end()
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # Into the view rect, which is `frame_rect` magnified: a step that
        # reshaped its input is still one picture of one thing, so both layers
        # take the same rectangle, and they take the same magnification for the
        # same reason.
        painted = self.view_rect()
        # The fit is the letterbox, and a magnified frame overruns it on both
        # axes: without this, the inset a portrait frame leaves fills with
        # picture and the widget stops showing where the frame ends.
        painter.setClipRect(box)
        if self._under is not None:
            painter.drawImage(painted, self._under)
            painter.setOpacity(self._opacity)
        if self._frame is not None:
            painter.drawImage(painted, self._frame)
        elif self._field is not None:
            self._field.draw(painter, painted, box)
        painter.setOpacity(1.0)
        badge = self.badge_text()
        if badge:
            # Over the frame rather than over the letterbox, which is empty on a
            # viewport the picture happens to fill.
            painter.setPen(_HINT)
            painter.drawText(
                box.adjusted(6, 4, -6, -4),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft),
                badge,
            )
        painter.end()


class CanvasPane(QWidget):
    """The picture and the one control over it.

    The control is the composite's opacity and nothing else. The three alpha
    sliders and Shift-to-peek wait for the ring they modulate
    (`todo/the-in-band-ring-reads-a-mask-no-node-emits.md`), so a row rather
    than a panel: what would fill a panel is not here yet, and a chrome built
    for it now would be built against a guess.
    """

    def __init__(self, canvas: VideoCanvas, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas = canvas
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(DEFAULT_OPACITY)
        self._slider.setToolTip("How much of the step's result is drawn over its input")
        self._slider.valueChanged.connect(self._on_opacity)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(canvas)
        row = QHBoxLayout()
        row.setContentsMargins(6, 2, 6, 2)
        row.addWidget(QLabel(_OPACITY_LABEL))
        row.addWidget(self._slider)
        column.addLayout(row)

    @property
    def canvas(self) -> VideoCanvas:
        """The picture. What the window paints into and what the editors bind to."""
        return self._canvas

    @property
    def opacity_slider(self) -> QSlider:
        """The one control, for the case that drives it."""
        return self._slider

    def _on_opacity(self, value: int) -> None:
        self._canvas.overlay_opacity = value / 100.0
