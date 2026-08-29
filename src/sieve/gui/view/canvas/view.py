"""Aspect-preserving stage: centres content in the pane, letterboxes the rest."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui.palette import DIM, LINE, PANEL, STACK_BG

DEFAULT_ASPECT = 16 / 9
_MARGIN = 8


class Canvas(QWidget):
    """Fixed-aspect stage centred in the pane; content-agnostic."""

    # Emitted on every resize/aspect change so overlays share one stage rect.
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
        """Replace the staged widget (or clear it); the old one is deleted."""
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
        # Ignores non-positive — aspect comes from clip headers that may be bad.
        if aspect <= 0 or aspect == self._aspect:
            return
        self._aspect = aspect
        self._place()
        self.update()

    def aspect(self) -> float:
        return self._aspect

    # -- where it lands ---------------------------------------------------

    def stage(self) -> QRect:
        """Largest centred rect of this aspect inside the margins; empty if too small."""
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
