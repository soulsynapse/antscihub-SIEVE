"""What stands over the panes instead of in one.

Everything else the frame shows is a view in a pane (ADR-0001), or a position
on a track inside one (ADR-0003), and both are the same claim: the window is
divided, and what a thing is doing on screen is answered by which region it was
handed. An overlay is the one arrangement that is not that — it takes no room
from the panes, divides nothing, and covers all three at once.

Which is what suits a view that is about the application rather than about the
work. Preferences are read *instead of* the footage and the chain, not against
them, so housing them in a pane would mean taking the canvas away for as long
as they are up and then having to decide what to give back; and housing them in
a swipe position would put them on the track ← and → walk, where they are not a
step in the work at all.

It covers the panes and not the menu bar. The bar is where this was asked for
and is the one thing on screen that acts on the window rather than on the
project; leaving it uncovered keeps what opened the overlay visible while it is
open, and keeps the frame's top boundary where it sits at rest.

The scrim is what says *this is not a pane*: the work stays where it was and
stays legible under it, and no boundary has moved, so nothing has to be put
back when the overlay goes. Clicking it is the way out that needs nothing
found, and Escape the one that needs no pointer — answered here rather than
bound in `hotkeys.py`, because it means "close what is on top" and only the
thing on top knows whether there is one.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from sieve.gui.palette import SCRIM

#: How far the scrim shows around whatever is standing on it. Enough that the
#: view over the panes is read as being over them and not as a pane that just
#: arrived, at every window size the frame opens at.
_MARGIN = 40


class Overlay(QWidget):
    """A surface the size of what it covers, with one view standing on it.

    Parented to the widget it covers rather than to the window, so what "all of
    it" means is that widget's rectangle and nothing here has to know the menu
    bar's height. It follows the host's resizes by watching it: the host lays
    out panes, and an overlay added to that layout would be a fourth thing in
    the column taking room from them.
    """

    #: The cover has gone, however it was asked to. Two of the three ways out
    #: are the overlay's own — the scrim and Escape — so a frame that had to be
    #: told about the third would learn about a closed overlay only when it was
    #: the one that closed it.
    dismissed = Signal()

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        #: Where the view stands. Centred and margined rather than filling, so
        #: the scrim is visible on every side of it.
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        self.body.setSpacing(0)
        self.body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # It answers Escape, so it has to be able to hold focus; nothing behind
        # it is reachable while it is up, which is the point of covering them.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        host.installEventFilter(self)
        self.hide()

    def raise_over(self) -> None:
        """Cover the host, in front of whatever it is showing, and take focus.

        The geometry is set here as well as on resize: the overlay is built
        before the window is first shown, so the host's rectangle at the time
        this was constructed is not the one it is being asked to cover.
        """
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def dismiss(self) -> None:
        """Uncover the panes. Nothing to put back — nothing was taken.

        Dismissing what is already down is nothing, so the window may call this
        without first asking whether the user got there before it.
        """
        if not self.isVisible():
            return
        self.hide()
        self.dismissed.emit()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Resize and watched is self.parentWidget():
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), SCRIM)
        painter.end()

    def mousePressEvent(self, event) -> None:
        """A click on the scrim is a click outside, and closes.

        Only the scrim's own: the view standing on it is a child widget and
        takes its clicks itself, so this is reached exactly when the pointer
        landed on nothing.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.dismiss()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
            return
        super().keyPressEvent(event)
