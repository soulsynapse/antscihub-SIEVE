"""The run of views a pane shows one at a time, and the slide between them.

Positions sit on a track wider than the pane; the track slides so direction of
travel communicates position. The track moves, not the positions — so a view
mid-refill keeps its geometry during the slide.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QWidget

from sieve.gui import icons, palette
from sieve.gui.frame.panes import Blank

SLIDE_MS = 260
POSITIONS = ("project", "pipeline", "step")
_BACK = "arrow-left"
_FORWARD = "arrow-right"


class Swipe(QWidget):
    """A track of positions inside one pane, one visible at a time."""

    #: Emitted at slide start (not end) — UI must reflect where the next keystroke acts.
    moved = Signal(int)

    def __init__(
        self, positions: Sequence[QWidget], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        if not positions:
            raise ValueError("a swipe with no positions has nothing to show")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._positions = list(positions)
        self._current = 0
        self._offset = 0.0

        self._track = QWidget(self)
        for position in self._positions:
            position.setParent(self._track)

        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(SLIDE_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._relayout()

    # -- the animated property ------------------------------------------

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self._track.move(-round(self._offset * self.width()), 0)

    offset = Property(float, _get_offset, _set_offset)

    # -- where the swipe is standing -------------------------------------

    def current(self) -> int:
        """The target position (updated at slide start, not end)."""
        return self._current

    def position(self, index: int) -> QWidget:
        """The view standing at `index`, whether or not it is in front."""
        return self._positions[index]

    def count(self) -> int:
        return len(self._positions)

    # -- moving ----------------------------------------------------------

    def go(self, index: int) -> None:
        """Slide to `index`. No-op if already there; re-aims a running slide."""
        if not 0 <= index < len(self._positions):
            raise ValueError(
                f"a swipe of {len(self._positions)} has no position {index}"
            )
        running = self._animation.state() == QAbstractAnimation.State.Running
        if index == self._current and not running:
            return
        self._current = index
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(float(index))
        self._animation.start()
        self.moved.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` positions, clamped to the ends."""
        self.go(max(0, min(len(self._positions) - 1, self._current + delta)))

    # -- geometry --------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        """Resize track and positions; re-apply offset (pane-widths survive resize)."""
        width, height = self.width(), self.height()
        self._track.resize(width * len(self._positions), height)
        for index, position in enumerate(self._positions):
            position.setGeometry(index * width, 0, width, height)
        self._set_offset(self._offset)


class Arrows(QWidget):
    """← and → buttons for a swipe; disabled at the ends, never hidden."""

    def __init__(self, swipe: Swipe, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._swipe = swipe
        self._back = self._button(_BACK, "Back one position (←)", -1)
        self._forward = self._button(_FORWARD, "On one position (→)", +1)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        row.addWidget(self._back)
        row.addWidget(self._forward)
        self.setStyleSheet(
            "QToolButton { border: 0; padding: 0 2px; background: transparent; }"
        )

        swipe.moved.connect(self._reface)
        palette.CHANGED.connect(self._redraw)
        self._reface(swipe.current())

    def _button(self, glyph: str, tip: str, delta: int) -> QToolButton:
        button = QToolButton()
        button.setIcon(icons.icon(glyph))
        button.setIconSize(QSize(icons.SIZE, icons.SIZE))
        button.setAutoRaise(True)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda *_: self._swipe.step(delta))
        return button

    def _reface(self, index: int) -> None:
        """Refuse the direction the track has no room left in."""
        self._back.setEnabled(index > 0)
        self._forward.setEnabled(index < self._swipe.count() - 1)

    def _redraw(self) -> None:
        """Re-render icons for the current palette (pixmaps bake in their colours)."""
        self._back.setIcon(icons.icon(_BACK))
        self._forward.setIcon(icons.icon(_FORWARD))


def build_swipe(pane: str = "right", names: Iterable[str] = POSITIONS) -> Swipe:
    return Swipe([Blank(f"{pane} {name}") for name in names])
