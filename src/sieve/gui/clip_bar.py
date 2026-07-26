"""The transport slider and the strip that shows the representative clip.

Two widgets rather than one painted slider. A band drawn into the slider's own
groove has to be drawn after `QSlider.paintEvent` — which has already drawn the
handle — so it either paints across the handle or has to guess at the handle's
geometry to avoid it. A sibling strip under the groove never competes with the
handle, survives a style change that moves the groove, and is where the drag
grips for the in and out points will go when they are built.

What the two share is a mapping, and only one of them can own it: the slider,
because the mapping *is* Qt's — `sliderPositionFromValue` over the groove less
the handle width, which is where Qt puts the handle. That is what makes marking
in at the current position draw the band edge under the handle instead of a few
pixels off it, at every window width and in every style.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QSlider, QStyle, QStyleOptionSlider, QWidget

from sieve.core.pipeline_model import ClipRange

#: Height of the strip. Enough to read as a band at a glance and not so much
#: that it competes with the groove above it for the eye.
STRIP_HEIGHT = 10

#: Vertical inset of the painted track inside that height.
_TRACK_INSET = 3.0

_TRACK = QColor(58, 58, 66)
_BAND = QColor(90, 170, 255)


class ClipSlider(QSlider):
    """Horizontal transport slider that can say where a frame index lands."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def x_of_frame(self, frame: int) -> float:
        """Centre of the handle when it is parked on `frame`, in widget pixels.

        The handle centre and not its left edge: a mark is a position on the
        timeline, and the position the user reads off a slider is the middle of
        the thing they dragged.
        """
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderGroove, self
        )
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, self
        )
        span = groove.width() - handle.width()
        if span <= 0:
            return float(groove.center().x())
        offset = QStyle.sliderPositionFromValue(
            self.minimum(), self.maximum(), frame, span, option.upsideDown
        )
        return groove.x() + handle.width() / 2.0 + offset


class ClipStrip(QWidget):
    """A band under the transport showing which frames the clip covers.

    Holds no clip range of its own beyond what it is told to paint, and no
    frame arithmetic: both belong to the document and the slider respectively.
    It is a view, and the only reason it is a widget at all is that Qt has no
    way to draw outside one.
    """

    def __init__(self, slider: ClipSlider, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slider = slider
        self._clip: ClipRange | None = None
        self.setFixedHeight(STRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_clip(self, clip: ClipRange | None) -> None:
        """Show `clip`, or an empty track for None."""
        self._clip = clip
        self.update()

    def band_rect(self) -> QRectF:
        """Where the clip is painted, empty when there is nothing to paint.

        Exposed because it is the claim worth testing — that the band lands
        under the span of the groove the frames correspond to — and a painted
        pixel is not something a test can ask about.
        """
        if self._clip is None or self._slider.maximum() <= self._slider.minimum():
            return QRectF()
        left = self._slider.x_of_frame(self._clip.start)
        # The last frame *inside* the clip, because `end` is one past it and
        # would put the band's right edge on a frame the run never reaches.
        right = self._slider.x_of_frame(self._clip.end - 1)
        return QRectF(
            left,
            _TRACK_INSET,
            max(right - left, 2.0),
            self.height() - 2.0 * _TRACK_INSET,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the empty track, then the clip band over it."""
        del event
        if self._slider.maximum() <= self._slider.minimum():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(
            self._slider.x_of_frame(self._slider.minimum()),
            _TRACK_INSET,
            self._slider.x_of_frame(self._slider.maximum())
            - self._slider.x_of_frame(self._slider.minimum()),
            self.height() - 2.0 * _TRACK_INSET,
        )
        painter.fillRect(track, _TRACK)

        band = self.band_rect()
        if not band.isEmpty():
            painter.fillRect(band, _BAND)
        painter.end()
