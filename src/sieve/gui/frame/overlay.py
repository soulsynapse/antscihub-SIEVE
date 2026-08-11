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

Which is also what a view can be anchored *to*. A view may stand centred on the
scrim or hang from a given x at the top of it, and the second is for one opened
from a title still visible above it: dropped under that title, the card is read
as belonging to what was clicked, where a centred one is read as belonging to
the window. The caller names the x, because the overlay knows the surface and
not what is drawn over it.

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

#: The scrim left above a view that was anchored instead of centred. Short
#: where `_MARGIN` is generous, and deliberately: the anchored view is standing
#: under the thing that opened it, and a full margin there would put a band of
#: scrim between the two wide enough to read as a gap rather than as an
#: attachment. Not zero — the view is still on the scrim and not on the bar.
_GAP = 6


def _wide(view: QWidget) -> int:
    """How wide the layout will draw `view`, before it has drawn it once.

    Its hint held to its own bounds, and not the hint alone: a view that fixed
    its width did so past a hint that still reports what its contents asked
    for, and reading the hint would under-measure a card by however much it
    widened itself — which is exactly the case an anchor has to fit.
    """
    return min(max(view.sizeHint().width(), view.minimumWidth()), view.maximumWidth())


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
        #: Where the view stands. Margined rather than filling, so the scrim is
        #: visible around it wherever `_place` puts it.
        self.body = QVBoxLayout(self)
        self.body.setSpacing(0)
        #: Where the last raise asked the view's left edge to sit, or `None` for
        #: centred. Kept because a resize has to place the view again and the
        #: caller is not there to be asked a second time.
        self._left: int | None = None
        # It answers Escape, so it has to be able to hold focus; nothing behind
        # it is reachable while it is up, which is the point of covering them.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        host.installEventFilter(self)
        self.hide()

    def raise_over(self, left: int | None = None) -> None:
        """Cover the host, in front of whatever it is showing, and take focus.

        The geometry is set here as well as on resize: the overlay is built
        before the window is first shown, so the host's rectangle at the time
        this was constructed is not the one it is being asked to cover.

        `left` is where the view's left edge goes, in the host's own x, for one
        that reads as hanging off whatever opened it; `None` centres it, which
        is what suits a view with nothing on screen to hang from. Taken per
        raise rather than held: what a view hangs from is the caller's, and a
        bar's titles are only as wide as the platform drew them, so the number
        is worth re-reading each time it is asked for.
        """
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())
        self._left = left
        self._place()
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _place(self) -> None:
        """Put the view where the last raise asked for, at the size the overlay
        is now. Both are needed: the anchor is what the caller wants, and how
        much of it can be honoured depends on a width that changes under it.

        The alignment is set on the view and not on the layout: a layout is
        aligned within the item that holds it, and this one is the widget's
        own, so the flag would have nothing to be aligned against. Nothing to
        place before the frame has stood a view here — the overlay is built
        first and handed its view after, and the host can resize in between.
        """
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

    def _view(self) -> QWidget | None:
        """Whatever is standing on the scrim, or nothing yet."""
        item = self.body.itemAt(0)
        return item.widget() if item is not None else None

    def _inset(self, view: QWidget) -> int:
        """The asked-for anchor, unless the view would hang off the right edge.

        A view standing on the scrim is fixed-size, so nothing shrinks it back
        into view: the anchor is what gives, sliding the card left until the
        scrim shows down its right side again. Narrow enough and it lands flush
        at 0, which is the point past which the window is too small to both
        honour the anchor and stay inside itself.
        """
        room = self.width() - _wide(view) - _MARGIN
        return max(0, min(self._left or 0, room))

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
            self._place()
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
