"""Preferences as a card: the sections there will be, and what each is for.

Every row is inert, and that is the same claim `menu.py` makes with its greyed
entries rather than a different one: a settings screen that grew a control the
day the setting behind it landed would never, at any point, say what the
application is configurable *about*. Written out and disabled, it says so from
the start, and each row is a place a control lands rather than a place one has
to be argued for.

The card holds no state and reads none. There is nowhere to keep a preference
yet — no settings document, no place one would be written — and a view that
picked somewhere would be that decision, made in a view. Which is the same
refusal the project list makes about the library it lists.

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

#: How wide the card is allowed to get. A settings row is a label and a control
#: on one line, and a card that took the window's width would put a full screen
#: of space between the two — the overlay has room to spare, and spending all of
#: it makes the pair harder to read, not easier.
_WIDTH = 520

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
        #name {{ color: {rgb(TEXT)}; }}
        #gloss {{ color: {rgb(DIM)}; }}
        QToolButton {{ color: {rgb(DIM)}; border: 0; padding: 0 6px; }}
        QToolButton:hover {{ color: {rgb(ACCENT)}; }}
    """


class Preferences(QWidget):
    """What the application is configurable about, one row per section."""

    #: The user is done here. The view never acts on it — where it was standing
    #: and what closing costs are both the frame's.
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_sheet())
        self.setMaximumWidth(_WIDTH)
        # Its own height and no more: the overlay centres it, so a card that
        # asked for the whole column would be a pane again in everything but
        # name, with the scrim reduced to a border.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

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

        column = QVBoxLayout(self)
        column.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        column.setSpacing(_GUTTER)
        column.addLayout(head)
        column.addWidget(note)
        for name, gloss in _SECTIONS:
            column.addWidget(_Section(name, gloss))


class _Section(QFrame):
    """One heading's worth of settings, before any of them exist.

    A name and its gloss on two lines rather than one: the gloss is what says
    which of the four a user's question belongs under, and a row that elided it
    to fit beside the name would drop exactly the half that answers that.
    """

    def __init__(self, name: str, gloss: str) -> None:
        super().__init__()
        self.setObjectName("section")

        label = QLabel(name)
        label.setObjectName("name")
        line = QLabel(gloss)
        line.setObjectName("gloss")
        line.setWordWrap(True)

        column = QVBoxLayout(self)
        column.setContentsMargins(_GUTTER, _GUTTER - 2, _GUTTER, _GUTTER - 2)
        column.setSpacing(2)
        column.addWidget(label)
        column.addWidget(line)
