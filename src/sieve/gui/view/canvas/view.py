"""The canvas as a stage: content held at its own shape, and the room around it.

The one thing the canvas enforces is that its content keeps its aspect. The pane
it stands in is whatever width the user dragged the splitter to, and the footage
in it is whatever the camera recorded; a canvas that resolved that by stretching
would be one where a crop box drawn on screen is not the crop that gets applied,
and where two clips of different shapes are compared at a scale that came from
the window. So the content gets the largest rectangle of its own aspect that
fits, centred, and the leftover is the letterbox — drawn as ground rather than
as panel, because it is not part of the picture and should not read as though it
were.

The canvas holds one content widget and does not know what it draws. It sizes
and places it and nothing else, which is what lets `video_canvas/` be a folder
inside this one instead of a rewrite of it: frames, a still, or a rendered
composite are all *something with a shape*, and that is the whole of what the
stage asks of them.

Overlays are the second half of what a canvas is and are not here yet. When they
land they take the stage rect too, so what a crop box is drawn against is the
same rectangle the content was placed in — which is the reason the stage is
computed in one place and read, rather than each layer working it out from the
pane's size and agreeing by luck.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui.palette import DIM, LINE, PANEL, STACK_BG

#: What shape the stage takes with nothing standing on it. A canvas has to draw
#: some rectangle before it has content, and 16:9 is the shape most footage
#: arrives in.
DEFAULT_ASPECT = 16 / 9

#: How far the stage sits off the pane's edge. Enough to read as a thing placed
#: in the pane rather than as the pane itself repainted.
_MARGIN = 8


class Canvas(QWidget):
    """A stage of a fixed aspect, centred in whatever room the pane gives it.

    Handed its content rather than building it, for the reason the project list
    is handed its projects: what a canvas shows comes from a project that does
    not exist yet, and a canvas that reached for one would be the file where
    *where footage comes from* got settled in passing.
    """

    #: Where the content actually landed, in this widget's coordinates. Emitted
    #: on every resize and on every change of aspect, so an overlay follows the
    #: stage without recomputing it, and every layer reads one answer to *where
    #: is the picture*.
    staged = Signal(QRect)

    def __init__(
        self, aspect: float = DEFAULT_ASPECT, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("canvas")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._aspect = aspect if aspect > 0 else DEFAULT_ASPECT
        self._content: QWidget | None = None

    # -- what stands on it -----------------------------------------------

    def show_content(self, content: QWidget | None) -> None:
        """Put a widget on the stage, or clear it. The old one is dropped and
        not stacked behind: a canvas showing two things at once has no answer
        for which of them the overlays are pinned to."""
        if self._content is not None and self._content is not content:
            self._content.setParent(None)
            self._content.deleteLater()
        self._content = content
        if content is not None:
            content.setParent(self)
            content.show()
        self._place()
        self.update()

    def content(self) -> QWidget | None:
        return self._content

    def set_aspect(self, aspect: float) -> None:
        """The shape the stage holds. Ignoring a non-positive one rather than
        raising: this arrives from whatever a clip's header says, and a canvas
        that refused to draw over a bad number would take the window with it."""
        if aspect <= 0 or aspect == self._aspect:
            return
        self._aspect = aspect
        self._place()
        self.update()

    def aspect(self) -> float:
        return self._aspect

    # -- where it lands ---------------------------------------------------

    def stage(self) -> QRect:
        """The largest rectangle of this aspect that fits inside the margins,
        centred. Empty when the pane is too small to hold one — which the
        painter and the placement both then read as *draw nothing*, instead of
        each guarding against a negative width in its own way."""
        room = self.rect().adjusted(_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)
        if room.width() <= 0 or room.height() <= 0:
            return QRect()
        width = min(room.width(), int(room.height() * self._aspect))
        height = max(1, int(width / self._aspect))
        return QRect(
            room.x() + (room.width() - width) // 2,
            room.y() + (room.height() - height) // 2,
            width,
            height,
        )

    def _place(self) -> None:
        rect = self.stage()
        if self._content is not None:
            self._content.setGeometry(rect)
        self.staged.emit(rect)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        # Ground under the whole pane and panel only under the stage, so the
        # letterbox reads as room the picture does not reach. Content covers the
        # stage fill; the fill is what an empty canvas is.
        painter.fillRect(self.rect(), STACK_BG)
        rect = self.stage()
        if not rect.isEmpty():
            if self._content is None:
                painter.fillRect(rect, PANEL)
            painter.setPen(LINE)
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            if self._content is None:
                painter.setPen(DIM)
                painter.drawText(
                    rect, int(Qt.AlignmentFlag.AlignCenter), "nothing on the canvas"
                )
        painter.end()
