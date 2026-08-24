"""Footage on the stage: one frame at a time, and no opinion about the layout.

The canvas above this decides *where* the picture goes — the largest rectangle
of the content's own aspect, centred, with the leftover drawn as ground
(`canvas/view.py`). What is left for here is only the part that is true of
video: which frame is up, and how it gets from an array to the screen without
the window stopping to think.

**It has no size hints and it never negotiates.** Every size policy is
`Ignored` and both hints are empty. That is not tidiness — it is the rule the
freeze finding states, and the reason it states it is that content *did* drive
layout here: a pixmap's size hint and a line of HUD text nudged the splitter
between them, the canvas oscillated between two widths for the length of a
session, and the video was visibly resizing every few seconds while nothing was
wrong with the decoder
(`docs/findings/2026.08.22-what-froze-the-felt-loop.md`). Panes get their
geometry from the user and the window; content scales into whatever it is
given.

**The scale happens once per frame, not once per paint.** A repaint can be
asked for by anything — a window moving over this one, a sibling resizing —
and rescaling a full-resolution crop on each would be paint cost that grows
with how busy the desktop is rather than with what SIEVE is doing. So the
arriving frame is scaled to the geometry it will be drawn at and kept, and
`paintEvent` blits. A geometry change rescales from the frame that is up,
which is the only other thing that can invalidate it. Same rule
`analysis/surface.py` states for a field: reduce to display resolution once per
data change.

**It shows what it is handed and asks for nothing.** No route, no store, no
session. What frame is up is a decision made where the ladder and the transport
are, and a canvas that pulled would be a second place that was decided — and a
worse one, because it would be pulling on the thread that draws.

**A frame that is not there is a state and not a blank.** The ladder's answer
to a request it cannot serve cheaply is to hold: show what is already up and
let the fill overtake it. So `hold()` exists and does nothing to the picture,
and there is a difference between *nothing has been shown yet* and *the last
frame is still the honest one*.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui.palette import DIM, PANEL


class VideoCanvas(QWidget):
    """One frame, scaled into whatever geometry the stage gives it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("videocanvas")
        # Ignored on both axes, and the hints below are empty to match: a
        # policy that says "ignore me" while a hint still returns the pixmap's
        # size is a widget that has told the layout two different things.
        self.setSizePolicy(QSizePolicy.Policy.Ignored,
                           QSizePolicy.Policy.Ignored)
        self.setMinimumSize(0, 0)
        self._image: QImage | None = None
        self._scaled: QPixmap | None = None
        self._row: int | None = None
        self._standing_in = False
        #: how many times a frame has been scaled. Read by anything asking
        #: whether a repaint storm is costing scales, which is the failure the
        #: cache exists to prevent and is otherwise invisible.
        self.scales = 0

    # -- the two hints, deliberately empty --------------------------------
    def sizeHint(self) -> QSize:
        """Nothing. A hint here is a vote in a negotiation this must not join."""
        return QSize()

    def minimumSizeHint(self) -> QSize:
        return QSize()

    # -- what is up -------------------------------------------------------
    def show_frame(self, frame: np.ndarray, row: int | None = None,
                   standing_in: bool = False) -> None:
        """Put an array on the stage.

        `standing_in` says this is not the frame that was asked for — a
        neighbour, or a coarse derivation shown while the true one arrives.
        The canvas draws it the same and remembers, because whether the
        picture is the answer is a thing the rest of the interface may want to
        say and is not a thing to work out again from the pixels.
        """
        self._image = _as_image(frame)
        self._row = row
        self._standing_in = standing_in
        self._rescale()
        self.update()

    def hold(self) -> None:
        """Keep the picture that is up. The ladder's answer when it has none.

        A method rather than "call nothing", so that a caller walking a
        ladder has something to do at the last rung and a reader can see that
        holding is a decision rather than a gap.
        """
        return None

    def clear(self) -> None:
        self._image = None
        self._scaled = None
        self._row = None
        self.update()

    def row(self) -> int | None:
        return self._row

    def standing_in(self) -> bool:
        return self._standing_in

    def has_frame(self) -> bool:
        return self._image is not None

    # -- getting it there -------------------------------------------------
    def _rescale(self) -> None:
        """Scale the frame that is up to the geometry it will be drawn at."""
        if self._image is None or self.width() <= 0 or self.height() <= 0:
            self._scaled = None
            return
        # Fast transformation on purpose: this runs on the thread that draws,
        # once per frame at the play rate, and a smooth scale of a full crop is
        # the kind of cost that shows up as a rate the loop cannot keep rather
        # than as anything anybody can see in the picture.
        self._scaled = QPixmap.fromImage(self._image).scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.scales += 1

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # The other thing that invalidates the cache, and the only other one.
        self._rescale()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        if self._scaled is not None:
            painter.drawPixmap(self.rect(), self._scaled)
        else:
            painter.fillRect(self.rect(), PANEL)
            painter.setPen(DIM)
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter),
                             "no frame yet")
        painter.end()


def _as_image(frame: np.ndarray) -> QImage:
    """A numpy array as something Qt will draw, copied once.

    Copied and not wrapped. A `QImage` over a numpy buffer is a view, and the
    array it views is one a fill thread may overwrite or a store may evict
    while the paint is happening — which produces a torn picture rather than a
    crash, and only sometimes. One copy per frame is the price of the widget
    owning what it draws.

    Grey and colour both arrive here because a form's pixel format is the
    step's to choose; what the canvas does about it is pick the matching
    Qt format and otherwise not care.
    """
    array = np.ascontiguousarray(frame)
    if array.ndim == 2:
        height, width = array.shape
        image = QImage(array.data, width, height, width,
                       QImage.Format.Format_Grayscale8)
    else:
        height, width, channels = array.shape
        fmt = (QImage.Format.Format_BGR888 if channels == 3
               else QImage.Format.Format_RGBA8888)
        image = QImage(array.data, width, height, width * channels, fmt)
    return image.copy()
