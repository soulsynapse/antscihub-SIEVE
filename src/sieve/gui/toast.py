"""A small, self-dismissing notice in the bottom-right corner of its parent.

For things the user should know but must not be interrupted by. The case that
motivated it is the player degrading to coarse scrubbing: silently changing
what a drag means would be worse than the latency it fixes, but a modal — or
anything that takes focus mid-drag — would be far worse than either.

So this is a plain child widget rather than a window. It cannot steal focus,
it cannot outlive its parent, it never appears in the taskbar, and it does not
participate in the layout, which is what lets it sit over the viewport instead
of displacing it. The cost of that choice is that it is clipped to the window;
for a notice that is a feature.
"""

from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

#: How long a notice stays up before fading out. Long enough to read twice at
#: a glance, short enough that it is gone before it becomes furniture.
DEFAULT_TIMEOUT_MS = 8000

FADE_MS = 180

#: Distance from the parent's bottom-right corner.
MARGIN = 18

#: Kept narrow on purpose: a notice that needs more than a couple of lines is
#: a dialog wearing a disguise.
MAX_WIDTH = 380

_STYLE = """
QFrame#toastPanel {
    background-color: rgba(32, 33, 36, 235);
    border: 1px solid rgba(255, 255, 255, 38);
    border-radius: 8px;
}
QLabel#toastText {
    color: rgba(255, 255, 255, 229);
    font-size: 12px;
    background: transparent;
}
"""


class Toast(QFrame):
    """A transient notice anchored to the bottom-right of `parent`.

    A `QFrame` rather than a `QWidget` so the rounded panel in the stylesheet
    is actually painted — a plain widget ignores a background rule unless it
    is told to draw one.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toastPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_STYLE)
        # Never focusable: a notice must not take the keyboard from the table
        # or swallow a shortcut mid-drag.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to dismiss")

        self._label = QLabel(self)
        self._label.setObjectName("toastText")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setMaximumWidth(MAX_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.addWidget(self._label)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

        parent.installEventFilter(self)
        self.hide()

    # ---- api -------------------------------------------------------------

    def show_message(self, text: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
        """Display `text`, replacing any notice already up."""
        self._label.setText(text)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._animate_to(1.0)
        self._dismiss_timer.start(timeout_ms)

    @property
    def message(self) -> str:
        """The text currently displayed. Empty before the first notice."""
        return self._label.text()

    def dismiss(self) -> None:
        """Fade out and hide. Safe to call when already hidden."""
        self._dismiss_timer.stop()
        if not self.isVisible():
            return
        self._animate_to(0.0, then_hide=True)

    # ---- internals -------------------------------------------------------

    def _animate_to(self, opacity: float, *, then_hide: bool = False) -> None:
        self._fade.stop()
        # Reconnected each run rather than once: the same animation object
        # serves both directions, and a stale hide-on-finish would blank the
        # widget at the end of a fade *in*.
        with suppress(RuntimeError):
            self._fade.finished.disconnect()
        if then_hide:
            self._fade.finished.connect(self.hide)
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(opacity)
        self._fade.start()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.move(
            max(MARGIN, parent.width() - self.width() - MARGIN),
            max(MARGIN, parent.height() - self.height() - MARGIN),
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Track the parent's size so the corner stays the corner."""
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Click anywhere on the notice to get rid of it."""
        del event
        self.dismiss()
