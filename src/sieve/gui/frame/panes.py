"""The three panes, the sides a subpane anchors to in each, and nothing standing in either yet.

Panes are named for position, not content. Each is a core with subpane strips
around it, all `Blank` at this stage so the frame's layout claims are checkable
before any view arrives.
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

BOTTOM_HEIGHT = 128
SUBPANE_EXTENT = 96
SUBPANES_PER_SIDE = 2  # slot 0 at pane edge, each next one inward
_MIN_PANE = 160  # prevent dragging a pane shut


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
    """A region that paints its own fill (stylesheet would bleed into child views)."""

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
    """A core with subpane strips on one axis only (both axes would create ambiguous corners)."""

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
        self.body = self.core.body
        self._subpanes: dict[tuple[Side, int], Blank] = {}

        across = any(side.across for side in self.anchors)
        self._stack: QBoxLayout = QHBoxLayout(self) if across else QVBoxLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setSpacing(0)
        self._stack.addWidget(self.core, 1)

    def attach(
        self, side: Side, slot: int = 0, extent: int = SUBPANE_EXTENT
    ) -> Blank:
        """Take a strip off `side`; idempotent per slot. Slot order is positional, not insertion-order."""
        if side not in self.anchors:
            offered = ", ".join(sorted(s.name.lower() for s in self.anchors)) or "none"
            raise ValueError(
                f"{self.name} anchors a subpane {offered}, not {side.name.lower()}"
            )
        if not 0 <= slot < SUBPANES_PER_SIDE:
            raise ValueError(
                f"{self.name} {side.name.lower()} stacks "
                f"{SUBPANES_PER_SIDE} subpanes, so there is no slot {slot}"
            )
        if (side, slot) in self._subpanes:
            return self._subpanes[side, slot]

        subpane = Blank(f"{self.name} {side.name.lower()} {slot}")
        if side.across:
            subpane.setFixedWidth(extent)
            subpane.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            subpane.setFixedHeight(extent)
            subpane.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._stack.insertWidget(self._index_for(side, slot), subpane)
        self._subpanes[side, slot] = subpane
        return subpane

    def _index_for(self, side: Side, slot: int) -> int:
        """Stack index for a new strip — counts only same-side strips outside it."""
        outside = sum(
            1 for (other, filled) in self._subpanes if other is side and filled < slot
        )
        if side.leading:
            return outside
        return self._stack.count() - outside

    def detach(self, side: Side, slot: int = 0) -> None:
        """Give the strip back to the core. Detaching an empty slot is nothing."""
        subpane = self._subpanes.pop((side, slot), None)
        if subpane is not None:
            self._stack.removeWidget(subpane)
            subpane.deleteLater()

    def subpane(self, side: Side, slot: int = 0) -> Blank | None:
        """What is anchored there, or nothing if that slot is unfilled."""
        return self._subpanes.get((side, slot))


def build_left() -> Pane:
    left = Pane("left", (Side.TOP, Side.BOTTOM))
    left.setMinimumWidth(_MIN_PANE)
    return left


def build_right() -> Pane:
    right = Pane("right", (Side.TOP, Side.BOTTOM))
    right.setMinimumWidth(_MIN_PANE)
    return right


def build_bottom() -> Pane:
    bottom = Pane("bottom", (Side.LEFT, Side.RIGHT))
    bottom.setObjectName("bottom")
    bottom.setFixedHeight(BOTTOM_HEIGHT)
    bottom.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return bottom


def build_seam() -> QWidget:
    """Fixed divider line above the bottom pane (no splitter — height is not user-adjustable)."""
    seam = QWidget()
    seam.setObjectName("seam")
    seam.setFixedHeight(3)
    return seam
