"""The head a pane wears, and the room under it: the chassis every view stands in.

A head is the line at the top of a pane saying what is under it — `Projects` over
the library, the project's name over the pipeline. It is not a card and the
card's arguments do not carry over: nothing selects it, nothing hovers it, and
there is never more than one on screen per pane. What it is judged on is what it
does to the pane *below* it, which is why the shape is settled once here rather
than built inline by each view: two panes that grew their own heads would differ
by things nobody chose, and the cheapest moment to settle that is while there is
one head to move.

The band is a panel strip closed by a rule, against the ground the contents are
seen on, and that is the one thing making it read as a head rather than as the
first row of what it heads. It is the same figure the window's own chrome cuts,
drawn here rather than imported from `frame/chrome.py` because that file dresses
the window and this dresses a view inside a pane — a view that reached into the
frame's chrome would be a view that could not be put in a second pane.

What the head holds is a title, room in the band for whatever the view counts,
and a quiet line at the far end. What it does not hold is verbs yet: a head's
verbs act on the whole pane, there are only ever a couple of them, and which two
depends on what the pane is about — an empty row of them minted here would be
this file deciding that for every view at once.

What it does settle is where a pair of arrows stands, for a view that is one of
several the pane moves between: `set_arrows` takes the pair and puts it at the
band's far end, after the note. The pair itself is not minted here and this file
knows nothing about what it moves — that is the frame's, because only the frame
knows the run of views is a run at all. What is settled is the position, for the
reason the whole band is: two views on one track that each placed their own way
back would be two answers to where the way back is, and the user would have to
find it again on arriving.

The far end and not the leading one, which is the alignment above deciding it
rather than a preference: the title stands on the same x as the contents under
it, and anything put before the title walks that x by its own width — a head
with a way out would be a head whose name no longer lines up with the column
below it, and only the heads that had one.

`CardStack` is this with a scrolling column of cards under it, and is a subclass
rather than a widget holding one: the head was the stack's until a second view
wanted the same band, and a stack that kept its own copy would be the second
place a pane head is decided. So the title, the note and the band's row are all
this file's, and everything about cards is `stack.py`'s.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, LINE, PANEL, STACK_BG, TEXT, rgb

#: Where the band holds its own contents off the pane's edges. The left inset is
#: what whatever stands under the head takes as its own margin, so the title
#: stands on the same x as the contents below it and the whole view is read down
#: one line — which is why it is exported rather than kept private.
PAD_X = 16
PAD_Y = 13


def sheet() -> str:
    """The head's own rules, for a caller that sets a sheet of its own.

    Handed out for the reason `gallery.sheet()` is: a second stylesheet set on a
    widget inside this one replaces nothing, but a sheet set on an *ancestor*
    reaches here and a view that dresses itself has to include these back. Every
    rule is scoped to an object name, never to a bare class, because the room
    under the head holds whatever the view put there and a `QLabel` rule would
    reach into all of it.
    """
    return f"""
        #view {{ background: {rgb(STACK_BG)}; }}
        #viewhead {{
            background: {rgb(PANEL)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #viewtitle {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("heading")}pt;
            font-weight: 600;
        }}
        #viewnote {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
    """


class View(QWidget):
    """A titled band, and under it the room whatever this is a view of stands in.

    Handed its title rather than knowing it: what a pane is a view *of* is the
    view's, and a chassis that reached for a project or a chain would be the one
    file where two views' contents met — the same bargain `card.py` makes two
    levels down.
    """

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("view")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._title = QLabel(title)
        self._title.setObjectName("viewtitle")
        self._arrows: QWidget | None = None
        self._note = QLabel()
        self._note.setObjectName("viewnote")

        self._band = QWidget()
        self._band.setObjectName("viewhead")
        # The band is exactly as tall as what it holds, whatever is under it. Said
        # here and not left to the stretch below, because a view whose room is
        # still empty — one built before its contents, which is every view for the
        # length of its own `__init__` — would otherwise be a head spread down
        # half the pane.
        self._band.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._head = QHBoxLayout(self._band)
        self._head.setContentsMargins(PAD_X, PAD_Y, PAD_X, PAD_Y)
        self._head.setSpacing(12)
        self._head.addWidget(self._title)
        # The stretch is what the caller's own figures land before — see
        # `add_figure`, which counts them rather than reading an index off the
        # layout: what is past the stretch is no longer only the note, so an
        # arithmetic on `count()` would put the next figure at whichever end the
        # last thing added happened to leave nearer.
        self._head.addStretch(1)
        self._figures = 0
        self._head.addWidget(self._note)

        # The room is a widget and not a bare layout, so that it is something with
        # a size policy: an empty layout given the column's stretch cannot take
        # the space it was given, and a `QBoxLayout` with nothing able to expand
        # centres what it holds — which is a head floating in the middle of a
        # pane until something is put under it. It paints nothing itself, so the
        # view's ground is what shows through wherever the contents do not reach.
        self._room = QWidget()
        self._room.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._body = QVBoxLayout(self._room)
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(0)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._band)
        column.addWidget(self._room, 1)

        # Last, because the sheet is set on a widget whose children have to exist
        # for the rules naming them to land on anything. A subclass that builds
        # more calls this again at the foot of its own `__init__`.
        self._restyle()
        # A bound method and never a lambda: PySide6 holds a receiver's bound
        # method weakly and drops the connection when the widget goes, where a
        # lambda closing over `self` would keep a dead view subscribed. Bound
        # once here and never again in a subclass — the method it resolves to is
        # the override, and a second connection would restyle twice per change.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

    # -- the band ----------------------------------------------------------

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_note(self, note: str) -> None:
        """The quiet line at the band's far end — how many there are, how many
        are recomputing. Empty is the honest blank: a note that fell back to a
        dash would be a figure the view never claimed."""
        self._note.setText(note)

    def set_arrows(self, arrows: QWidget | None) -> None:
        """Stand a pair of arrows at the band's far end, or take them away.

        Last in the row, past the note: the title holds the left of the band
        because the contents under it are read down that x, so what a head gains
        it gains at the other end. Nothing else about the pair is this file's —
        what the two presses do, and whether either is refused at an end, are the
        caller's, since only it knows there is a run of views to be at the end of.

        Passing `None` puts the head back to a title with no way out of it. The
        pair is taken out of the row rather than hidden, so a head that is no
        longer one of several does not pay the arrows' width in air.
        """
        if self._arrows is not None:
            self._head.removeWidget(self._arrows)
            self._arrows.setParent(None)
        self._arrows = arrows
        if arrows is not None:
            self._head.addWidget(arrows)

    def add_figure(self, figure: QWidget) -> None:
        """One more of the view's own figures, beside the title.

        The chain's is two figures and their labels — what it costs a frame, and
        what that is in frames per second — and those are the view's because only
        it knows what is being measured. They land in the order they are added,
        after the title and before the stretch, so what the view counts stays
        with the name of the thing counted and never drifts to the far end.
        """
        self._figures += 1
        self._head.insertWidget(self._figures, figure)

    def head(self) -> QHBoxLayout:
        """The band's row itself, for what `add_figure` does not cover.

        Handed out rather than kept private because a head is a row and a caller
        with something else to put in one should not have to be a subclass. Where
        the row's own three go is settled here — title, figures, note, arrows —
        and a caller reaching past that is choosing its own place in it.
        """
        return self._head

    # -- the room under it -------------------------------------------------

    def body(self) -> QVBoxLayout:
        """What the view fills. Its own layout and not this widget's, so the band
        stays the first thing in the column no matter what order a caller builds
        in — the same bargain `Card.body()` makes."""
        return self._body

    # -- what it wears -----------------------------------------------------

    def _sheet(self) -> str:
        """This view's rules, for a subclass that dresses more than the head.

        The hook a subclass overrides rather than `_restyle` itself: what changes
        between one view chassis and the next is the text of the sheet and not
        when it is set, and a subclass that overrode the slot would have to
        remember to call up for the head's own rules.
        """
        return sheet()

    def _restyle(self) -> None:
        """This view's sheet again in the palette and at the sizes now in use.

        What stands in the body is not touched. Each thing in there is subscribed
        to `CHANGED` itself, which is what lets a view rebuild its contents
        without redressing anything — a chassis that dressed its contents would
        have to do it again on every rebuild, and would be dressing widgets it
        does not know the shape of.
        """
        self.setStyleSheet(self._sheet())
