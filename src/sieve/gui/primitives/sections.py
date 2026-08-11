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
only a section that brought something of its own costs a widget. Preferences is
the whole-card case of that — four sections, no bodies, one frame — and the dev
view is the mixed one.

The card holds no state beyond which section is open, which is its own posture
and not anything about what the sections are for. Closing is emitted and never
done: the card does not know it is standing on an overlay, and the frame is what
put it there (`overlay.py`).
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

from PySide6.QtCore import Qt, Signal
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

from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb
from sieve.gui.primitives.nav import SectionNav

#: The gap between rows and the margin around them, one number for both, for the
#: reason the project list uses one: the outermost row sits off the card's edge
#: by the distance it sits off its neighbour.
GUTTER = 10


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
    """

    name: str
    gloss: str
    body: QWidget | None = None


def _sheet() -> str:
    """Scoped to this card's own objects, never to a bare class: it is set on a
    widget the frame houses and whose right side holds whatever a caller handed
    over, and a `QLabel` rule here would reach into both."""
    return f"""
        #sections {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #heading {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #note {{ color: {rgb(DIM)}; }}
        #placeholder {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #name {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #gloss, #empty {{ color: {rgb(DIM)}; }}
        #done {{ color: {rgb(DIM)}; border: 0; padding: 0 6px; }}
        #done:hover {{ color: {rgb(ACCENT)}; }}
    """


class SectionCard(QWidget):
    """A heading, a note, and sections listed left against one read right.

    Handed its sections and its size rather than choosing either. What the card
    is about is the view's, and the numbers are too: 820×320 suits four rows of
    a label and a control, and a bench holding a gallery does not, so the caller
    that knows which it is passes them.

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
        self.setStyleSheet(_sheet())
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        # Its own size and no more: the overlay centres it, so a card that asked
        # for the whole column would be a pane again in everything but name,
        # with the scrim reduced to a border.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._sections = tuple(sections)

        title = QLabel(heading)
        title.setObjectName("heading")

        done = QToolButton()
        done.setObjectName("done")
        done.setText("✕")
        done.setAutoRaise(True)
        done.setToolTip(f"Close {heading} (Esc)")
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self.closed)

        head = QHBoxLayout()
        head.setSpacing(GUTTER)
        head.addWidget(title, 1)
        head.addWidget(done)

        subtitle = QLabel(note)
        subtitle.setObjectName("note")
        subtitle.setWordWrap(True)

        #: The one frame every bodiless section is shown in, retold as the nav
        #: moves. Built whether or not any section needs it, because the stack
        #: needs something to show while a caller's list is empty and a card
        #: with no page at all is a card with a hole in its right side.
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

    def _show_section(self, index: int) -> None:
        """Turn the right side to the section now being stood on. Out of range
        is nothing, so this may be called with an empty nav's -1."""
        if not 0 <= index < len(self._sections):
            return
        section = self._sections[index]
        if section.body is not None:
            self._pages.setCurrentWidget(section.body)
            return
        self._placeholder.retell(section.name, section.gloss)
        self._pages.setCurrentWidget(self._placeholder)


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
        # Last, so a section with little to say sits at the top of the panel
        # rather than spread down it, and the name stays where the eye left it
        # as the nav is walked.
        column.addStretch(1)

    def retell(self, name: str, gloss: str) -> None:
        self._name.setText(name)
        self._gloss.setText(gloss)
