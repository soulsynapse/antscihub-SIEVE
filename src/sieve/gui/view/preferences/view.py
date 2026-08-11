"""Preferences as a card: the sections there will be, and what each is for.

The sections stand in a list down the left and one of them is read at a time on
the right, rather than all four stacked in a column. A settings screen grows,
and a column shows every section at once only while there are four of them and
nothing under any of them; the moment a section holds its controls the column is
a scroll where the user's place is a scrollbar position rather than a thing they
chose. The nav says where they are standing at every length, and the right side
is the one region that changes when they move.

Every row is inert, and that is the same claim `menu.py` makes with its greyed
entries rather than a different one: a settings screen that grew a control the
day the setting behind it landed would never, at any point, say what the
application is configurable *about*. Written out and disabled, it says so from
the start, and each section is a place controls land rather than a place they
have to be argued for.

The card holds no state and reads none — nothing here is which section is open,
which is the card's own posture and not a preference. There is nowhere to keep a
preference yet, no settings document and no place one would be written, and a
view that picked somewhere would be that decision, made in a view. Which is the
same refusal the project list makes about the library it lists.

Closing is emitted and never done. The view does not know it is standing on an
overlay, and the frame is what put it there: it says it is finished, and what
that costs is the window's to carry out (`overlay.py`).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb
from sieve.gui.view.preferences.nav import SectionNav

#: How wide the card is allowed to get. A settings row is a label and a control
#: on one line, and a card that took the window's width would put a full screen
#: of space between the two — the overlay has room to spare, and spending all of
#: it makes the pair harder to read, not easier. Wider than the reading side
#: alone wants, by about what the nav takes: the list is beside the section, not
#: carved out of it. The nav is a fixed column, so every width added past that
#: lands on the reading side, where a row's label and its control are what have
#: to fit on one line.
_WIDTH = 820

#: How tall the card stands, whichever section is open. The nav is walked with
#: ↑ and ↓, and a card sized to its current section would resize under the key
#: as the glosses change length — and the overlay centres it, so every one of
#: those resizes would also move the list the user is arrowing down.
_HEIGHT = 320

#: The gap between rows and the margin around them, one number for both, for the
#: reason the project list uses one: the outermost row sits off the card's edge
#: by the distance it sits off its neighbour.
_GUTTER = 10

#: The sections, each a name and the one line saying what falls under it. Named
#: for what the user is deciding rather than for the module that will answer it:
#: a row called `decode` is a row only the person who wrote the decoder can find.
_SECTIONS: tuple[tuple[str, str], ...] = (
    ("library", "where projects are kept, and which one opens on start"),
    ("playback", "how much footage is decoded ahead, and how much is held"),
    ("chain", "what a new step starts at, and what a run writes out"),
    ("appearance", "the palette, and how large the text is drawn"),
)


def _sheet() -> str:
    """Scoped to this view's own objects, never to a bare class: it is set on a
    widget the frame houses, and a `QLabel` rule here would still be reaching
    into whatever else stands beside it."""
    return f"""
        #preferences {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #heading {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #note {{ color: {rgb(DIM)}; }}
        #section {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #name {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #gloss {{ color: {rgb(DIM)}; }}
        #empty {{ color: {rgb(DIM)}; }}
        QToolButton {{ color: {rgb(DIM)}; border: 0; padding: 0 6px; }}
        QToolButton:hover {{ color: {rgb(ACCENT)}; }}
    """


class Preferences(QWidget):
    """What the application is configurable about: sections left, one read right."""

    #: The user is done here. The view never acts on it — where it was standing
    #: and what closing costs are both the frame's.
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_sheet())
        self.setFixedWidth(_WIDTH)
        self.setFixedHeight(_HEIGHT)
        # Its own size and no more: the overlay centres it, so a card that asked
        # for the whole column would be a pane again in everything but name,
        # with the scrim reduced to a border.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        heading = QLabel("preferences")
        heading.setObjectName("heading")

        done = QToolButton()
        done.setText("✕")
        done.setAutoRaise(True)
        done.setToolTip("Close preferences (Esc)")
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self.closed)

        head = QHBoxLayout()
        head.setSpacing(_GUTTER)
        head.addWidget(heading, 1)
        head.addWidget(done)

        note = QLabel("nothing here is settable yet — these are the sections")
        note.setObjectName("note")
        note.setWordWrap(True)

        #: The nav is the whole card's, not the reading side's: the heading and
        #: the note above are about preferences and not about a section, so they
        #: span both columns and the split starts under them.
        self.nav = SectionNav([name for name, _ in _SECTIONS])
        self._section = _Section()
        self.nav.chosen.connect(self._show_section)
        self._show_section(self.nav.current())

        body = QHBoxLayout()
        body.setSpacing(_GUTTER)
        body.addWidget(self.nav)
        body.addWidget(self._section, 1)

        column = QVBoxLayout(self)
        column.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        column.setSpacing(_GUTTER)
        column.addLayout(head)
        column.addWidget(note)
        column.addLayout(body, 1)

    def _show_section(self, index: int) -> None:
        """Redraw the reading side for the section now being stood on. Out of
        range is nothing, so this may be called with an empty nav's -1."""
        if not 0 <= index < len(_SECTIONS):
            return
        self._section.show_section(*_SECTIONS[index])


class _Section(QFrame):
    """The section being read, before any of its settings exist.

    One frame that is retold rather than one per section swapped under a stack:
    the sections differ by two strings, and a stack would keep four identical
    widgets alive to say which of them is on top — a fact the nav already holds.

    A name and its gloss on two lines: the gloss is what says which of the four
    a user's question belongs under, and eliding it to fit beside the name would
    drop exactly the half that answers that.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("section")

        self._name = QLabel()
        self._name.setObjectName("name")
        self._gloss = QLabel()
        self._gloss.setObjectName("gloss")
        self._gloss.setWordWrap(True)

        nothing = QLabel("no settings here yet")
        nothing.setObjectName("empty")

        column = QVBoxLayout(self)
        column.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        column.setSpacing(2)
        column.addWidget(self._name)
        column.addWidget(self._gloss)
        column.addSpacing(_GUTTER)
        column.addWidget(nothing)
        # Last, so a section with little to say sits at the top of the panel
        # rather than spread down it, and the name stays where the eye left it
        # as the nav is walked.
        column.addStretch(1)

    def show_section(self, name: str, gloss: str) -> None:
        self._name.setText(name)
        self._gloss.setText(gloss)
