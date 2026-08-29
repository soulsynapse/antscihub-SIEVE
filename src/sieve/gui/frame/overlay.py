"""What stands over the panes instead of in one.

A scrim covers the panes (not the menu bar) and holds one view at a time —
centred, or anchored to a given x for a card opened from a bar title. Multiple
views live on the scrim; exactly one is visible. Escape and scrim-click dismiss.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from sieve.gui.palette import SCRIM

_MARGIN = 40
_GAP = 6  # top margin for an anchored view — reads as attached to the bar title


def _wide(view: QWidget) -> int:
    """Effective width: sizeHint clamped to min/max (hint alone under-measures fixed-width views)."""
    return min(max(view.sizeHint().width(), view.minimumWidth()), view.maximumWidth())


class Overlay(QWidget):
    """A scrim parented to the pane host, sized by event filter (not layout — that would steal pane room)."""

    dismissed = Signal()  # scrim-click or Escape closed the overlay

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.body = QVBoxLayout(self)
        self.body.setSpacing(0)
        self._left: int | None = None  # anchor x, or None for centred; kept for resize
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # must hold focus for Escape
        host.installEventFilter(self)
        self.hide()

    def stand(self, view: QWidget) -> None:
        """Show `view`, hide the rest. Can switch views without dismissing."""
        for index in range(self.body.count()):
            standing = self.body.itemAt(index).widget()
            if standing is not None:
                standing.setVisible(standing is view)
        self._place()

    def raise_over(self, left: int | None = None) -> None:
        """Cover the host and take focus. `left` anchors; None centres."""
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())
        self._left = left
        self._place()
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _place(self) -> None:
        """Position the standing view — centred or anchored at `_left`."""
        view = self._view()
        if view is None:
            return
        if self._left is None:
            self.body.setAlignment(view, Qt.AlignmentFlag.AlignCenter)
            self.body.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
            return
        self.body.setAlignment(
            view, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.body.setContentsMargins(self._inset(view), _GAP, _MARGIN, _MARGIN)

    def showing(self, view: QWidget) -> bool:
        """True if the scrim is up and `view` is the one standing."""
        return self.isVisible() and self._view() is view

    def _view(self) -> QWidget | None:
        """The visible view, not just itemAt(0) — hidden views are still in the layout."""
        for index in range(self.body.count()):
            view = self.body.itemAt(index).widget()
            if view is not None and not view.isHidden():
                return view
        return None

    def _inset(self, view: QWidget) -> int:
        """Left margin: the anchor clamped so the view stays inside the scrim."""
        room = self.width() - _wide(view) - _MARGIN
        return max(0, min(self._left or 0, room))

    def dismiss(self) -> None:
        """Hide the scrim. Idempotent."""
        if not self.isVisible():
            return
        self.hide()
        self.dismissed.emit()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Resize and watched is self.parentWidget():
            self.setGeometry(watched.rect())
            self._place()
        return super().eventFilter(watched, event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), SCRIM)
        painter.end()

    def mousePressEvent(self, event) -> None:
        # childAt distinguishes scrim from view — ignored presses on a view's
        # background bubble up here, so position alone is ambiguous.
        if self.childAt(event.position().toPoint()) is None:
            if event.button() == Qt.MouseButton.LeftButton:
                self.dismiss()
        event.accept()  # never leak to the panes underneath

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
            return
        super().keyPressEvent(event)
