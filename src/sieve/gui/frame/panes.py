"""The three panes, the sides a subpane anchors to in each, and nothing standing in either yet.

Each is named for where it sits and not for what it will hold, because a pane
is the space and never its occupant: `left` stays the left pane whatever view
is put in it, where `canvas` would be a claim about its contents that the frame
has no way to keep. The names of the sides a subpane anchors to are the same
four words, one level in — `bottom left` is the left strip of the bottom pane.

Each pane is a core with room for subpanes around it, and every one of them is
a `Blank`: a region that fills, names itself, and holds a layout for whatever
replaces it. Keeping them empty at this stage is what makes the frame's own
claims checkable — which boundary the user may drag, which is fixed, what
happens to each pane when the window is resized, where a subpane may anchor —
without those answers coming from the size hint of some widget inside.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.palette import DIM, LINE, PANEL

#: The bottom pane's height: the timeline band plus one control row. Not the
#: user's to trade against the other panes, which is why it is a number here and
#: not a splitter — the working window is read against the whole asset at a size
#: the layout does not get a say in.
BOTTOM_HEIGHT = 128

#: How deep a subpane is along the axis it anchors on, across the boundary it
#: adds. A number rather than a splitter for the same reason the bottom pane's
#: height is one: a strip the user could drag until it swallowed the core would
#: stop being the smaller pane anchored to a side, which is the whole of what a
#: subpane is.
SUBPANE_EXTENT = 96

#: Neither pane may be dragged shut. A pane the user cannot see is one
#: they cannot get back except by finding a seam with no width.
_MIN_PANE = 160


class Side(Enum):
    """Where in its pane a subpane anchors, and so which axis it divides."""

    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()

    @property
    def across(self) -> bool:
        """Whether anchoring here divides the pane left to right."""
        return self in (Side.LEFT, Side.RIGHT)

    @property
    def leading(self) -> bool:
        """Whether the strip comes before the core rather than after it."""
        return self in (Side.TOP, Side.LEFT)


class Blank(QWidget):
    """A region with its name in it, and a layout for what will fill it.

    It paints rather than styles: the panes come to hold views that
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


class Pane(QWidget):
    """A core, and the subpanes anchored around it.

    Which sides are on offer is the pane's own, and each pane offers the axis
    its outer boundary does not already answer: the left and right panes sit
    either side of a vertical splitter, so what is left to divide in them is the
    top side against the bottom; the bottom pane runs the full width under both,
    so its spare axis is left against right. Offering both axes in one pane is
    refused rather than nested — the second cut would have to say which of the
    two strips owns the corner, and no pane here has a reason to answer that.

    The pane is the space and never its occupant: a view goes in `body`, which
    is the core's, so attaching a subpane does not move what already stands in
    the pane, and detaching one gives the core back the strip.
    """

    def __init__(
        self, name: str, anchors: Iterable[Side], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.name = name
        self.anchors = frozenset(anchors)
        if any(side.across for side in self.anchors) and any(
            not side.across for side in self.anchors
        ):
            raise ValueError(f"{name} would be cut on both axes at once")

        self.core = Blank(name)
        #: Where a view stands. The core's, not the pane's.
        self.body = self.core.body
        self._subpanes: dict[Side, Blank] = {}

        across = any(side.across for side in self.anchors)
        self._stack: QBoxLayout = QHBoxLayout(self) if across else QVBoxLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setSpacing(0)
        self._stack.addWidget(self.core, 1)

    def attach(self, side: Side, extent: int = SUBPANE_EXTENT) -> Blank:
        """Take a strip off `side` for a subpane, and hand that subpane back.

        Fixed along the axis it anchors on and filling across it: the strip is
        the pane's boundary restated one level in, and the core takes the whole
        of what the resize leaves. Asking twice for the same side gives back the
        subpane already there rather than a second one behind it.
        """
        if side not in self.anchors:
            offered = ", ".join(sorted(s.name.lower() for s in self.anchors)) or "none"
            raise ValueError(
                f"{self.name} anchors a subpane {offered}, not {side.name.lower()}"
            )
        if side in self._subpanes:
            return self._subpanes[side]

        subpane = Blank(f"{self.name} {side.name.lower()}")
        if side.across:
            subpane.setFixedWidth(extent)
            subpane.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            subpane.setFixedHeight(extent)
            subpane.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._stack.insertWidget(0 if side.leading else self._stack.count(), subpane)
        self._subpanes[side] = subpane
        return subpane

    def detach(self, side: Side) -> None:
        """Give the strip back to the core. Detaching an empty side is nothing."""
        subpane = self._subpanes.pop(side, None)
        if subpane is not None:
            self._stack.removeWidget(subpane)
            subpane.deleteLater()

    def subpane(self, side: Side) -> Blank | None:
        """What is anchored there, or nothing if that side is undivided."""
        return self._subpanes.get(side)


def build_left() -> Pane:
    """The left half of the splitter, for the footage and its overlays.

    Bounded below because what it will hold is the thing being tuned against —
    a chain read off a canvas too small to see the animals in is read off
    nothing.
    """
    left = Pane("left", (Side.TOP, Side.BOTTOM))
    left.setMinimumWidth(_MIN_PANE)
    return left


def build_right() -> Pane:
    """The right half, for the chain, the walked step's knobs, and the run."""
    right = Pane("right", (Side.TOP, Side.BOTTOM))
    right.setMinimumWidth(_MIN_PANE)
    return right


def build_bottom() -> Pane:
    """Full width under the other two, for the whole asset and the playhead.

    Under both and inside neither, because the working window it will carry is
    where the footage on the left and every plot on the right are read — one
    position in one file, held by neither of the two views showing it.
    """
    bottom = Pane("bottom", (Side.LEFT, Side.RIGHT))
    bottom.setObjectName("bottom")
    bottom.setFixedHeight(BOTTOM_HEIGHT)
    bottom.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return bottom


def build_seam() -> QWidget:
    """A splitter handle's line where there is no splitter.

    The bottom pane's height is fixed, so nothing about that boundary is the
    user's to trade; it reads like the other section dividers without
    answering the cursor.
    """
    seam = QWidget()
    seam.setObjectName("seam")
    seam.setFixedHeight(3)
    return seam
