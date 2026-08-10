"""The three rooms the window divides into, and nothing standing in them yet.

Each is a `Blank`: a pane that fills, names itself, and holds a layout for
whatever replaces it. Keeping them empty at this stage is what makes the
frame's own claims checkable — which boundary the user may drag, which is
fixed, what happens to each compartment when the window is resized — without
those answers coming from the size hint of some widget inside.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from sieve.gui.palette import DIM, LINE, PANEL

#: The timeline's height: the band plus one control row. Not the user's to
#: trade against the panes, which is why it is a number here and not a splitter
#: — the working window is read against the whole asset at a size the layout
#: does not get a say in.
TIMELINE_HEIGHT = 128

#: Neither pane may be dragged shut. A compartment the user cannot see is one
#: they cannot get back except by finding a seam with no width.
_MIN_PANE = 160


class Blank(QWidget):
    """A compartment with its name in it, and a layout for what will fill it.

    It paints rather than styles: the compartments come to hold surfaces that
    draw themselves, and a stylesheet rule broad enough to fill this one would
    still be reaching into them after they arrive.
    """

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(LINE)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        if not self.body.count():
            painter.setPen(DIM)
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), self.name)
        painter.end()


def build_canvas() -> Blank:
    """Left: the footage, and every overlay drawn in register with it.

    Bounded below because it is the thing being tuned against — a chain read
    off a canvas too small to see the animals in is read off nothing.
    """
    canvas = Blank("canvas")
    canvas.setMinimumWidth(_MIN_PANE)
    return canvas


def build_controls() -> Blank:
    """Right: the chain, the walked step's knobs, and what the run will write."""
    controls = Blank("controls")
    controls.setMinimumWidth(_MIN_PANE)
    return controls


def build_timeline() -> Blank:
    """Bottom: the whole asset, the working window on it, the playhead.

    Full width under both panes and not inside either, because the window it
    carries is where the canvas and every plot on the right are read — one
    position in one file, held by neither of the two surfaces showing it.
    """
    timeline = Blank("timeline")
    timeline.setObjectName("timeline")
    timeline.setFixedHeight(TIMELINE_HEIGHT)
    timeline.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return timeline


def build_seam() -> QWidget:
    """A splitter handle's line where there is no splitter.

    The timeline's height is fixed, so nothing about that boundary is the
    user's to trade; it reads like the other section dividers without
    answering the cursor.
    """
    seam = QWidget()
    seam.setObjectName("seam")
    seam.setFixedHeight(3)
    return seam
