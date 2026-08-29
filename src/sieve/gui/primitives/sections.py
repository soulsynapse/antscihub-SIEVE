"""A card of sections: a list down the left, one of them read on the right.

Lifted out of preferences when the dev view turned out to be the same picture,
and lifted rather than copied for the reason `primitives/__init__.py` gives: two
views drawing one shape from two files is two places a gutter can change.

The shape is the argument, and it is preferences' argument. A settings screen
grows, and a column showing every section at once works only while there are
four of them with nothing under any; the moment a section holds its controls the
column is a scroll where the user's place is a scrollbar position rather than a
thing they chose. The nav says where they are standing at every length, and the
right side is the one region that changes when they move — which is as true of a
dev bench with a gallery under one section as of a settings card with nothing
under any.

A section may hand over a widget or hand over nothing. Nothing is not a blank
panel per section: the sections with no body differ by two strings, and a stack
holding one identical widget each would keep them all alive to say which is on
top, a fact the nav already holds. So they share one frame that is retold, and
only a section that brought something of its own costs a widget. A card whose
sections are all places rather than things is the whole-card case of that — one
frame, retold — and both cards here are the mixed one.

A section may also hand over a way of putting itself back, and the card draws
one button for it — per section, and never a *reset everything*. That is the
sections' own shape rather than a policy about settings: what a card of sections
holds is one region that changes as the nav moves, so the one thing on screen
worth undoing is the one being read. A card-wide reset would be a button whose
effect is mostly in sections the user is not looking at, and the confirmation it
would then need is a dialog this shape does not otherwise want. The button says
the section's name for the same reason it stands where it does — it is in the
head, beside a heading naming the whole card, and *reset* alone there would read
as the card.

What putting a section back *means* is never the card's, and not the section
widget's either: the callable a section arrives with is the setting owner's —
`palette.reset`, `metrics.reset` — which is the split every other write in this
tree makes, and it matters most here because a reset is the one gesture that
touches keys no control on the card is showing.

The card holds no state beyond which section is open, which is its own posture
and not anything about what the sections are for. Closing is emitted and never
done: the card does not know it is standing on an overlay, and the frame is what
put it there (`overlay.py`).
"""

from __future__ import annotations

from typing import Callable, NamedTuple, Sequence

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons, metrics, palette
from sieve.gui.palette import DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb
from sieve.gui.primitives.button import GHOST, Button
from sieve.gui.primitives.nav import SectionNav

#: The gap between rows and the margin around them, one number for both, for the
#: reason the project list uses one: the outermost row sits off the card's edge
#: by the distance it sits off its neighbour.
GUTTER = 10

#: The close verb, named once here for the reason `card.py` names its four: the
#: string is a lucide filename, and a typo in it raises at the first draw rather
#: than at the line that wrote it.
_CLOSE = "x"


class Section(NamedTuple):
    """One entry in the nav and what stands on the right when it is open.

    Named for what the user is looking for rather than for the module that will
    answer it: a section called `decode` is a section only the person who wrote
    the decoder can find.

    `gloss` is what says which section a question belongs under, and it is drawn
    under the name on its own line rather than beside it — eliding it to fit
    would drop exactly the half that answers that.

    `body` is `None` for a section that is a place things will land rather than
    a place they have landed. It is a promise the card keeps visibly, the same
    claim `menu.py` makes with its greyed entries.

    `reset` is what putting this section back the way it came costs, or `None`
    for a section there is nothing to put back — which is every section holding
    no body, and any section whose contents are looked at rather than set. It is
    a callable and not a flag because the card cannot know what a section's
    defaults are; whoever owns the setting says, and the card only offers the
    gesture.
    """

    name: str
    gloss: str
    body: QWidget | None = None
    reset: Callable[[], None] | None = None


def _sheet() -> str:
    """Scoped to this card's own objects, never to a bare class: it is set on a
    widget the frame houses and whose right side holds whatever a caller handed
    over, and a `QLabel` rule here would reach into both.

    The corner is on `#sections` and not on `#placeholder`, and that is the
    distinction `metrics.radius()` is about: this widget is a card, and the panel
    on its right is a panel inside one. Rounding every rectangle in the tree
    would spend the setting on things a user changing *the corner of the cards*
    did not ask to move, and would put a curve on the one surface — the reading
    side — that a section's own contents are laid out square against.
    """
    return f"""
        #sections {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-radius: {metrics.radius()}px;
        }}
        #heading {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("heading")}pt;
            font-weight: 600;
        }}
        #note {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #placeholder {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #name {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #gloss, #empty {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #done {{ border: 0; padding: 0 6px; }}
    """


class SectionCard(QWidget):
    """A heading, a note, and sections listed left against one read right.

    Handed its sections and its size rather than choosing either. What the card
    is about is the view's, and the numbers are too: what suits a column of a
    label and a control per row is not what suits a bench holding a gallery, so
    the caller that knows which it is passes them.

    Fixed at whatever it was passed, though, and that is the card's own claim
    rather than the caller's: the nav is walked with ↑ and ↓, and a card sized
    to its current section would resize under the key as the glosses change
    length — and the overlay centres it, so every one of those resizes would
    also move the list the user is arrowing down.
    """

    #: The user is done here. The card never acts on it — where it was standing
    #: and what closing costs are both the frame's.
    closed = Signal()

    def __init__(
        self,
        heading: str,
        note: str,
        sections: Sequence[Section],
        width: int,
        height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sections")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._restyle()
        # A stylesheet is a string built from the palette's values as they were,
        # so it is remade when they change. The same pair appears on every widget
        # here that dresses itself with one, always as a bound method: PySide6
        # holds a receiver's bound method weakly and drops the connection when
        # the widget goes, where a lambda closing over `self` keeps a dead card
        # subscribed and calls into it.
        palette.CHANGED.connect(self._restyle)
        # And the close icon, which the sheet does not reach: it is a pixmap
        # drawn at the colours in force when it was made, so a palette change has
        # to draw it again. Its own slot and not `_restyle`, for `card.py`'s
        # reason: a size change does not touch a pixmap.
        palette.CHANGED.connect(self._redress)
        # The same sheet carries the corner and the three text sizes, so the
        # answer to both signals is the one string built again. Two connections,
        # for the reason `metrics.py` gives: what they are telling this card is
        # different, even where what it does about them is the same.
        metrics.CHANGED.connect(self._restyle)
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        # Its own size and no more: the overlay centres it, and the scrim around
        # it is what says the card is standing over the panes.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._sections = tuple(sections)

        title = QLabel(heading)
        title.setObjectName("heading")

        #: The close, kept as an attribute only so a palette change can redraw
        #: it: an icon is a pixmap tinted when it was made, where the glyph it
        #: replaces was recoloured by the sheet alone.
        done = self._done = QToolButton()
        done.setObjectName("done")
        done.setIcon(icons.icon(_CLOSE))
        done.setIconSize(QSize(icons.SIZE, icons.SIZE))
        done.setAutoRaise(True)
        done.setToolTip(f"Close {heading} (Esc)")
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self.closed)

        #: The one reset button, renamed as the nav moves, or `None` on a card
        #: no section of which can be put back — the dev bench is one.
        self._reset: Button | None = None
        if any(section.reset is not None for section in self._sections):
            # Ghost and small, so the heading stays the loudest thing in this
            # head and the verb that undoes work is not what draws the eye.
            self._reset = Button("", GHOST, small=True)
            self._reset.clicked.connect(self._put_back)

        head = QHBoxLayout()
        head.setSpacing(GUTTER)
        head.addWidget(title, 1)
        # Left of the close, which holds the corner: this is the quieter of the
        # two verbs and the one the user is less often reaching for.
        if self._reset is not None:
            head.addWidget(self._reset)
        head.addWidget(done)

        subtitle = QLabel(note)
        subtitle.setObjectName("note")
        subtitle.setWordWrap(True)

        #: The one frame every bodiless section is shown in, retold as the nav
        #: moves. Built whether or not any section needs it, so the stack has
        #: something to show while a caller's list is empty.
        self._placeholder = _Placeholder()

        self._pages = QStackedWidget()
        self._pages.addWidget(self._placeholder)
        for section in self._sections:
            if section.body is not None:
                self._pages.addWidget(section.body)

        #: The nav is the whole card's, not the reading side's: the heading and
        #: the note above are about the card and not about a section, so they
        #: span both columns and the split starts under them.
        self.nav = SectionNav([section.name for section in self._sections])
        self.nav.chosen.connect(self._show_section)
        self._show_section(self.nav.current())

        body = QHBoxLayout()
        body.setSpacing(GUTTER)
        body.addWidget(self.nav)
        body.addWidget(self._pages, 1)

        column = QVBoxLayout(self)
        column.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        column.setSpacing(GUTTER)
        column.addLayout(head)
        column.addWidget(subtitle)
        column.addLayout(body, 1)

    def _restyle(self) -> None:
        self.setStyleSheet(_sheet())

    def _redress(self) -> None:
        """The close drawn again at the colours now in force."""
        self._done.setIcon(icons.icon(_CLOSE))

    def _show_section(self, index: int) -> None:
        """Turn the right side to the section now being stood on. Out of range
        is nothing, so this may be called with an empty nav's -1."""
        if not 0 <= index < len(self._sections):
            return
        section = self._sections[index]
        self._offer_reset(section)
        if section.body is not None:
            self._pages.setCurrentWidget(section.body)
            return
        self._placeholder.retell(section.name, section.gloss)
        self._pages.setCurrentWidget(self._placeholder)

    def _offer_reset(self, section: Section) -> None:
        """Name the button after the section now open, or take it off the head.

        Hidden rather than greyed, which is not what this tree does elsewhere:
        `card.py` and `menu.py` disable a verb that exists here and cannot be
        taken *now*, and a section with no defaults is one this verb does not
        apply to at all — a greyed *reset library* would promise a gesture that
        arrives with the section's controls rather than one that is unavailable.
        Nothing steps sideways when it goes, since the heading takes the stretch
        and the close button is the far edge either way.
        """
        if self._reset is None:
            return
        self._reset.setVisible(section.reset is not None)
        if section.reset is None:
            return
        self._reset.setText(f"reset {section.name}")
        self._reset.setToolTip(f"Put {section.name} back to what it came with")

    def _put_back(self) -> None:
        """Ask the section now open to put itself back.

        The section is read off the nav at the moment of the click rather than
        held from when the button was last renamed. The two cannot disagree
        while this button is the only way in, which is exactly the kind of claim
        that stops being true the first time a hotkey or a menu entry reaches
        the same verb.

        Nothing is confirmed. Every section that carries a reset is one whose
        settings apply where they are made and are shown by the card you are
        standing on — see `view/preferences/palettes.py` — so the result is on
        screen before the pointer has moved, and a dialog would be asking about
        something the user is about to see either way.
        """
        index = self.nav.current()
        if not 0 <= index < len(self._sections):
            return
        reset = self._sections[index].reset
        if reset is not None:
            reset()


class _Placeholder(QFrame):
    """A section that has nothing under it yet, saying which one it is.

    Written out rather than left off the nav: a card that grew a section the day
    the thing behind it landed would never, at any point, say what the
    application is configurable — or inspectable — *about*.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("placeholder")

        self._name = QLabel()
        self._name.setObjectName("name")
        self._gloss = QLabel()
        self._gloss.setObjectName("gloss")
        self._gloss.setWordWrap(True)

        nothing = QLabel("nothing here yet")
        nothing.setObjectName("empty")

        column = QVBoxLayout(self)
        column.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        column.setSpacing(2)
        column.addWidget(self._name)
        column.addWidget(self._gloss)
        column.addSpacing(GUTTER)
        column.addWidget(nothing)
        # Last, so a section with little to say sits at the top of the panel and
        # its name stays where the eye left it as the nav is walked.
        column.addStretch(1)

    def retell(self, name: str, gloss: str) -> None:
        self._name.setText(name)
        self._gloss.setText(gloss)
