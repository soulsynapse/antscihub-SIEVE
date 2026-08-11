"""One way a card could look, and the handful of ways being considered.

A look is a dress and two arrangements: what the card is painted in when it is
selected and when it is not, where the four verbs sit, and whether anything
leads the title. Those are the axes the shapes below actually differ on — a
mockup set parameterised by everything would be a card widget with options,
which is the thing this exists to avoid building before the choice is made.

The dresses are written out one per look and share no fragments on purpose.
These are alternatives, and a fragment two of them read would mean editing one
look changed another — which is exactly the drift a side-by-side comparison is
supposed to make visible rather than hide.

Nothing here reuses `primitives/card.py`. The real card builds its own head and
re-sets its own sheet, so a look that changed either would have to widen it, and
widening the card to draw the alternatives to the card presumes the answer. The
baseline is the real thing instead, stood at the top of the gallery unmodified
(`view.py`), so the comparison has something true to compare against.
"""

from __future__ import annotations

from typing import Callable, NamedTuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

#: The four verbs, in the order `primitives/card.py` fixes them in and with the
#: names it knows them by. Every look draws all four wherever it puts them: a
#: look that dropped one would be a comparison of two different cards.
_VERBS: tuple[tuple[str, str], ...] = (
    ("arrow-right", "Open this card's settings"),
    ("arrow-right-left", "Swap for another tool"),
    ("pin", "Pin below the canvas"),
    ("x", "Remove this"),
)

#: What a mock card is about, so every look is drawn holding the same thing and
#: the only difference on screen is the look. A chain step with two knobs, which
#: is the shortest card the chain will really contain.
_TITLE = "threshold"
_LINES: tuple[str, ...] = ("sensitivity — 0.42", "min area — 120 px")


class Look(NamedTuple):
    """A candidate card: what it is called, what it costs, and how it is drawn.

    `gloss` is the half worth reading. A gallery of shapes with no argument
    under them is a mood board, and the choice between these is not about which
    is prettiest — it is about what a column of twenty of them does to the eye
    while a slider is being dragged.

    `dress` is handed whether the card is selected and returns the whole sheet,
    rather than being a pair of colours: some of these differ by which property
    carries the selection at all, which no pair of colours can express.

    `verbs` is where the four icons sit — `head` beside the title, `below` under
    the body, `hover` beside the title but only while the pointer is on the
    card. `lead` is whether a step index stands before the title.
    """

    name: str
    gloss: str
    dress: Callable[[bool], str]
    verbs: str = "head"
    lead: bool = False


def _as_built(selected: bool) -> str:
    """The card as `primitives/card.py` draws it, redrawn here as the mock the
    others are varied from — the real one is in the gallery too, above these."""
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockline {{ color: {rgb(DIM)}; }}
        #mocklead {{ color: {rgb(DIM)}; font-weight: 600; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _fill(selected: bool) -> str:
    """Selection as a fill instead of an edge — the arrangement `card.py`
    refused, drawn so the refusal can be checked rather than taken. The cost is
    at the bottom of the card: hover is a fill too, so a hovered card and a
    selected one are one picture, and the accent title is all that separates
    them."""
    return f"""
        #mock {{
            background: {rgb(PANEL_HOT if selected else PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockline {{ color: {rgb(DIM)}; }}
        #mocklead {{ color: {rgb(DIM)}; font-weight: 600; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _rule(selected: bool) -> str:
    """The accent moved from the leading side to the top, full width. Louder at
    a glance down a column, and it costs a card's worth of vertical rhythm — the
    rule is a boundary the eye reads as a gap between cards, not as one card's
    lid."""
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-top: 3px solid {rgb(ACCENT if selected else PANEL)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockline {{ color: {rgb(DIM)}; }}
        #mocklead {{ color: {rgb(DIM)}; font-weight: 600; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _flat(selected: bool) -> str:
    """No hairline at all: the cards are told apart by the gutter and by their
    fill against the pane's darker ground. Quietest in a long column, and it
    gives up the one thing a border does that a gutter cannot — saying where a
    card ends when the next one has scrolled off."""
    # The unselected edge is the card's own fill and not `transparent`: the
    # column behind is a different colour, and a see-through edge would show it
    # as a dark stripe down every card that is not current.
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL_HOT if selected else PANEL)};
            border: 0;
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockline {{ color: {rgb(DIM)}; }}
        #mocklead {{ color: {rgb(DIM)}; font-weight: 600; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _quiet_head(selected: bool) -> str:
    """The title given up as the loud thing and the knobs taking it. What a user
    scans a tuned chain for is the values, not the step names they chose; the
    cost is that a card whose name has gone quiet is harder to find when the
    chain is long and the values mean nothing yet."""
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{
            color: {rgb(DIM)};
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        #mockline {{ color: {rgb(TEXT)}; }}
        #mocklead {{ color: {rgb(DIM)}; font-weight: 600; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _numbered(selected: bool) -> str:
    """A step index in a leading column of its own. The chain is ordered and
    nothing else on the card says so; the cost is a column of width that every
    card pays, including the ones in a list that is not ordered at all."""
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockline {{ color: {rgb(DIM)}; }}
        #mocklead {{
            color: {rgb(ACCENT if selected else DIM)};
            font-weight: 600;
            background: {rgb(STACK_BG)};
            border: 1px solid {rgb(LINE)};
            padding: 1px 6px;
        }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


#: The shapes on the bench, in the order they are argued about. `as built` is
#: first so every look below it is read as a change *from* something, and the
#: real card stands above all of them in the gallery.
LOOKS: tuple[Look, ...] = (
    Look(
        "as built, redrawn",
        "the current dress, drawn by this file — if it differs from the real "
        "card above, this file has drifted and is what to fix",
        _as_built,
    ),
    Look(
        "verbs on hover",
        "four icons on every card is twenty-four icons in a six-step chain; "
        "hidden until the pointer arrives, the column is only titles and values "
        "— and a verb nobody hovers is a verb nobody finds",
        _as_built,
        verbs="hover",
    ),
    Look(
        "verbs below",
        "the title line becomes only the title, so a long step name has the "
        "whole width before it elides; costs a row of height on every card",
        _as_built,
        verbs="below",
    ),
    Look(
        "fill, not edge",
        "selection as a filled panel — reads from further away than a 3px edge, "
        "and collides with hover, which is also a fill",
        _fill,
    ),
    Look(
        "accent rule on top",
        "the same accent across the card's lid instead of down its side",
        _rule,
    ),
    Look(
        "flat, no hairline",
        "borders dropped; the gutter and the fill do the separating",
        _flat,
    ),
    Look(
        "quiet head",
        "the values loud and the step name dim — a tuned chain is scanned for "
        "numbers, not for names",
        _quiet_head,
    ),
    Look(
        "numbered",
        "a step index leading the title, since the chain is ordered and nothing "
        "else on the card says so",
        _numbered,
        lead=True,
    ),
)


class MockCard(QFrame):
    """One look, drawn holding the same step every other look is drawn holding.

    Inert: the icons carry their real tooltips so the row can be judged at the
    width it will really have, and none of them is connected to anything. A
    mockup that acted would be a card, and there is already one of those.
    """

    def __init__(
        self, look: Look, selected: bool, index: int = 3, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(look.dress(selected))

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 8)
        column.setSpacing(4)

        title = QLabel(_TITLE)
        title.setObjectName("mocktitle")

        head = QHBoxLayout()
        head.setSpacing(4)
        if look.lead:
            lead = QLabel(str(index))
            lead.setObjectName("mocklead")
            head.addWidget(lead)
        head.addWidget(title)
        head.addStretch(1)

        #: Held whichever arrangement it is in, so `enterEvent` has something to
        #: show without knowing where the row ended up.
        self._verbs = _verb_row()
        if look.verbs == "below":
            column.addLayout(head)
            for line in _LINES:
                column.addWidget(_line(line))
            below = QHBoxLayout()
            below.setSpacing(4)
            below.addStretch(1)
            below.addWidget(self._verbs)
            column.addLayout(below)
        else:
            head.addWidget(self._verbs)
            column.addLayout(head)
            for line in _LINES:
                column.addWidget(_line(line))

        #: Hidden rather than left out, so the card is the height it would be
        #: with the row showing and does not jump under the pointer — which is
        #: half of what this look has to be judged on.
        self._fades = look.verbs == "hover"
        if self._fades:
            self._verbs.setVisible(False)

    def enterEvent(self, event) -> None:
        if self._fades:
            self._verbs.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._fades:
            self._verbs.setVisible(False)
        super().leaveEvent(event)


def _verb_row() -> QWidget:
    """The four icons as one widget, so a look can move them or hide them
    without the arrangement having to know there are four."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    # The real card's head spaces its four buttons by 4 and this row must too:
    # the mock sitting directly under the baseline is only worth having while
    # any difference between them is a difference the look asked for.
    layout.setSpacing(4)
    for glyph, tip in _VERBS:
        button = QToolButton()
        button.setIcon(icons.icon(glyph))
        button.setIconSize(QSize(icons.SIZE, icons.SIZE))
        button.setAutoRaise(True)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(button)
    return row


def _line(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("mockline")
    return label
