"""One way a pane's head could look, and the handful being considered.

A head is the line at the top of a pane saying what is under it — `projects`
over the library, the project's name over the pipeline. It is not a card and the
card's arguments do not carry over: there is no selection, nothing hovers it,
and there is never more than one on screen at a time. What it is judged on
instead is what it does to the pane *below* it — whether the eye can tell where
the chrome stops and the contents start, and how much vertical room the answer
costs on a pane whose contents are the point.

A look is a dress and an arrangement, together, for the reason `card_mockups/
look.py` gives: `strip` fills the head with the panel colour, and a strip that
also drew a hairline under itself would be claiming two boundaries where the
argument is that the fill is one. So each look is a whole head and not a cell in
a grid of dresses × shapes.

What is fixed is what a head has to display: where the user is (`PLACE`), what
this pane is about (the name), how much of it there is (`TALLY`), and the verbs
that act on the whole pane. Every look is drawn holding all four wherever it
puts them — including the two that put one of them nowhere, which is then an
argument the look is making rather than a difference in content.

Each look is drawn twice, holding a short name and a long one. That is this
gallery's equivalent of the cards' at-rest-and-selected pair, and it is the
title's real question: a project name is whatever the user typed, panes are
narrow, and half of these looks differ only in how much width is left for the
name by the time the tally and the verbs have taken theirs.

Elision is what every look does when it runs out of room, and it is fixed rather
than varied. Wrapping to a second line, and letting the name set the pane's
minimum width, are the two other answers — both real, both a separate axis, and
folding them in here would draw every look below four times to compare a
property none of them is about.

Nothing here is a redrawing of a primitive, because there is no title primitive:
the library builds its head inline in `project_list/view.py`, and deciding what
this shape is before a second pane copies that row is the whole of why the
section exists. So the baseline below is that inline row redrawn, and unlike the
card gallery there is nothing true standing above it to catch a drift — until a
primitive is minted, `as built, redrawn` has to be checked against the library
by looking at both.
"""

from __future__ import annotations

from typing import Callable, NamedTuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStyleOption,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

#: What acts on a whole pane, in the order a look draws them. Two and not the
#: card's four: a head's verbs are about the pane rather than about a row in it,
#: and there are only ever a couple of those — the card's ⇄ and ◆ have no meaning
#: applied to a library.
_VERBS: tuple[tuple[str, str], ...] = (
    ("folder-open", "Add a source to this project"),
    ("x", "Close this project"),
)

#: Where the pane is standing, for the looks that say so. The library is the one
#: place a pipeline was opened from, so this is a real ancestor and not a
#: decoration — which is what a breadcrumb has to be to be worth its line.
PLACE = "library"

#: What the pane is about, at both the lengths it really arrives in. The short
#: one is what a user types when the project is the only one; the long one is
#: what the same user types in the fourth month, and it is the case every look
#: below is actually judged on.
NAME = "hive entrance, july"
LONG_NAME = "colony 7 — entrance foraging, 14 july, second replicate"

#: How much of it there is. Two facts and not one, because a pipeline's head has
#: to say both how long the chain is and how much of it is on the canvas, and a
#: tally that fits one number and not two is a tally that will be rewritten.
TALLY = "6 steps · 2 pinned"


class Look(NamedTuple):
    """A candidate head: what it is called, what it costs, and how it is drawn.

    `dress` takes no argument, unlike the card's, which is handed selection. A
    head has no second state to dress — the two drawings of each look differ only
    in the string they hold, which is content and not a look.

    `shape` is handed the mock and fills it, reading `head.title` for whichever
    of the two names it is drawing.
    """

    name: str
    gloss: str
    dress: Callable[[], str]
    shape: Callable[["MockHead"], None]


# -- the dresses -----------------------------------------------------------
#
# Each writes every rule its own arrangement needs and no others, and they share
# no fragments: these are alternatives, and a fragment two of them read would
# mean editing one look changed another — the drift a side-by-side comparison
# exists to make visible.
#
# `#head` is left with no background in most of them, so the pane's own ground
# shows through and the head reads as the top of the pane rather than as a thing
# placed on it. The looks that fill it are making exactly that claim.


def _as_built() -> str:
    """The library's head as `project_list/view.py` draws it: bold name, dim
    tally at the far end, nothing under it but the gutter."""
    return f"""
        #head {{ background: transparent; }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _ruled() -> str:
    """A hairline under the head. The cheapest possible boundary — one pixel and
    no extra height — and it costs the one thing a rule always costs: at the top
    of a column of bordered cards it is a fourth horizontal line in twelve
    pixels, and the eye reads it as the first card's lid."""
    return f"""
        #head {{ background: transparent; border-bottom: 1px solid {rgb(LINE)}; }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _strip() -> str:
    """The head as a filled band across the pane, in the panel colour the
    contents are drawn in and against the ground the pane leaves bare. It is the
    loudest separation here and the only one that survives the column scrolling
    under it; it costs a second fill in a pane already made of them, and a head
    the same colour as the cards below can read as the first card."""
    return f"""
        #head {{
            background: {rgb(PANEL)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _stacked() -> str:
    """Name on its line, place and tally on a quiet one under it. The name gets
    the pane's whole width before it elides, which is what a long project name
    needs and what nothing else here gives it."""
    return f"""
        #head {{ background: transparent; }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #hunder {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _crumb() -> str:
    """The place ahead of the name on the same line, dim, with a dim separator.
    A pane reached by swiping has no back button and no window title, so this is
    the only look that says what the pipeline was opened *from* — at the price of
    the width it takes from the name, on the axis the name is shortest on."""
    return f"""
        #head {{ background: transparent; }}
        #hplace, #hsep {{ color: {rgb(DIM)}; }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _eyebrow() -> str:
    """The same crumb turned vertical: the place above the name in small caps.
    It costs a line of height instead of a share of the width, which is the
    trade the whole gallery keeps making — and small caps at this size is the
    one thing here that could fail to be legible on a coarse screen."""
    return f"""
        #head {{ background: transparent; }}
        #heyebrow {{
            color: {rgb(DIM)};
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _chip() -> str:
    """The tally as a filled tag rather than as dim text at the end of the line.

    The count is the one thing in a head that changes while the user works, and
    a number that changes inside a shape is findable in peripheral vision in a
    way a dim word at the pane's edge is not. It costs the padding either side,
    and a tally of two facts makes a wide tag.
    """
    return f"""
        #head {{ background: transparent; }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #hchip {{
            background: {rgb(PANEL_HOT)};
            color: {rgb(DIM)};
            border: 1px solid {rgb(LINE)};
            padding: 1px 6px;
        }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _accent_name() -> str:
    """The name in the accent. It is the fastest thing here to find on a screen
    of two panes, and it spends the palette's one meaningful colour — `ACCENT`
    means *this is what you are acting on*, and a head that wears it permanently
    is a head that has taken the accent's meaning away from the selection."""
    return f"""
        #head {{ background: transparent; }}
        #htitle {{ color: {rgb(ACCENT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _big() -> str:
    """The name at fifteen pixels instead of at the body size in bold. A pane's
    name read from the far side of the desk, and the only look here whose height
    grows with nothing added to it — the line is taller, so the contents start
    lower on every pane whether or not anyone is looking at the name."""
    return f"""
        #head {{ background: transparent; }}
        #htitle {{ color: {rgb(TEXT)}; font-size: 15px; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _verbs() -> str:
    """The pane's verbs at the end of the head's own line, with the tally moved
    in beside the name. The head becomes where a pane is acted on and not only
    where it is named, which is the only place those verbs can live that is not
    a menu; it is also what takes the most width from the name of anything
    here."""
    return f"""
        #head {{ background: transparent; }}
        #htitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #htally {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _absent() -> str:
    """No head at all. Nothing to dress, and the rules are here anyway so the
    file does not read as though the look were unfinished."""
    return """
        #head { background: transparent; }
        QToolButton { border: 0; padding: 0 4px; background: transparent; }
    """


# -- the arrangements ------------------------------------------------------
#
# Each is handed the mock and fills `head.column`. They share the content
# helpers at the bottom of the file and nothing else, so no arrangement can
# quietly draw a different name or a different tally than its neighbours.


def _shape_name_tally(head: MockHead) -> None:
    """Name at the left, tally at the far right. What the library does."""
    head.column.addLayout(_line(_name(head), _label(TALLY, "htally")))


def _shape_stacked(head: MockHead) -> None:
    """Name on its own line, place and tally under it on a quiet one."""
    head.column.addWidget(_name(head))
    head.column.addWidget(_label(f"{PLACE} · {TALLY}", "hunder"))


def _shape_crumb(head: MockHead) -> None:
    """Place, separator, name — then the tally at the far end.

    The place and the separator are added at their natural width and the name
    takes the remainder, so it is the name that elides. A crumb that shortened
    to make room for the ancestor would be showing where the user came from at
    the cost of where they are.
    """
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(_label(PLACE, "hplace"), 0)
    row.addWidget(_label("›", "hsep"), 0)
    row.addWidget(_name(head), 1)
    row.addWidget(_label(TALLY, "htally"), 0)
    head.column.addLayout(row)


def _shape_eyebrow(head: MockHead) -> None:
    """Place above, in small caps, then the name and the tally."""
    head.column.addWidget(_label(PLACE, "heyebrow"))
    head.column.addLayout(_line(_name(head), _label(TALLY, "htally")))


def _shape_chip(head: MockHead) -> None:
    """Tally as a tag at the end of the name's line.

    The chip is added without a stretch factor, so it is the width of the count
    it holds — a tag taking the row's remainder is a second header bar.
    """
    chip = _label(TALLY, "hchip")
    chip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    head.column.addLayout(_line(_name(head), chip))


def _shape_verbs(head: MockHead) -> None:
    """Name, tally beside it, verbs at the end of the line.

    The tally moves in against the name rather than staying at the far edge:
    left where it was, it would sit directly under the pointer's path to the ✕,
    and a number that has to be read is a bad thing to put next to a verb that
    closes the project.
    """
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(_name(head), 1)
    row.addWidget(_label(TALLY, "htally"), 0)
    row.addWidget(head.verbs, 0)
    head.column.addLayout(row)


def _shape_absent(head: MockHead) -> None:
    """Nothing. The pane starts at its contents, and what it is about is
    whatever the frame already says elsewhere."""
    head.column.setContentsMargins(0, 0, 0, 0)


#: The heads on the bench, in the order they are argued about. `as built` is
#: first so every look below it is read as a change *from* something. The
#: boundary looks come next, since where the head stops is the question a reader
#: has to have an answer to before a look that adds a line to it can be judged;
#: then the ones that add something; then the one that takes the head away, last
#: because it is only worth considering once the others have been priced.
LOOKS: tuple[Look, ...] = (
    Look(
        "as built, redrawn",
        "what `project_list/view.py` builds inline — name bold at the left, "
        "tally dim at the right, and nothing but a gutter between it and the "
        "cards. Every look below is a change from this",
        _as_built,
        _shape_name_tally,
    ),
    Look(
        "rule under",
        "a hairline where the head stops. One pixel, no extra height, and it "
        "lands directly above a column of bordered cards — a fourth line in "
        "twelve pixels, which the eye can read as the first card's lid rather "
        "than as the head's floor",
        _ruled,
        _shape_name_tally,
    ),
    Look(
        "filled strip",
        "the head as a band in the panel colour across the pane's ground. The "
        "only separation here that still reads when the column has scrolled "
        "under it; costs a second fill in a pane already made of them, and a "
        "band the colour of the cards can read as one",
        _strip,
        _shape_name_tally,
    ),
    Look(
        "tally under the name",
        "the name gets the pane's whole width before it elides, and the place "
        "and the count drop to a dim second line. The only look that fits a "
        "long project name on a narrow pane; costs a row of height on every "
        "pane, including the ones whose names are one word",
        _stacked,
        _shape_stacked,
    ),
    Look(
        "breadcrumb",
        "`library › name` on one line. A pane reached by swiping has no back "
        "button and no window title, so this is the only look that says what "
        "the pipeline was opened from — taking that width from the name, on "
        "the axis the name has least to spare",
        _crumb,
        _shape_crumb,
    ),
    Look(
        "place as an eyebrow",
        "the same ancestor, above instead of beside, in small caps. Trades the "
        "breadcrumb's width for a line of height and leaves the name the whole "
        "row; small caps at this size is the one thing here that can fail to "
        "be legible on a coarse screen",
        _eyebrow,
        _shape_eyebrow,
    ),
    Look(
        "tally as a chip",
        "the count in a filled tag rather than as dim text at the pane's edge. "
        "It is the one thing in a head that changes while the user works, and "
        "a number inside a shape is findable without looking straight at it; "
        "costs the tag's padding, and two facts make a wide tag",
        _chip,
        _shape_chip,
    ),
    Look(
        "name in the accent",
        "fastest thing on a two-pane screen to find, and it spends the "
        "palette's one meaningful colour: `ACCENT` means *this is what you are "
        "acting on*, and a head wearing it permanently has taken that meaning "
        "away from the selection",
        _accent_name,
        _shape_name_tally,
    ),
    Look(
        "name at fifteen",
        "size instead of weight, readable from the far side of the desk. The "
        "only look whose height grows without anything being added — the "
        "contents start lower on every pane, whether or not anyone is reading "
        "the name",
        _big,
        _shape_name_tally,
    ),
    Look(
        "verbs on the line",
        "what acts on the whole pane, in the head with what names it — the "
        "only home those verbs have that is not a menu. Takes more width from "
        "the name than anything else here, and puts a ✕ that closes a project "
        "on the row the eye goes to first",
        _verbs,
        _shape_verbs,
    ),
    Look(
        "no head",
        "the pane starts at its contents. Every pixel goes to the work, and "
        "the answer to *which project is this* moves to the frame — which is "
        "only a real answer if the frame is giving one. Worth pricing before "
        "the others: a head is a row of chrome on a screen whose point is the "
        "footage",
        _absent,
        _shape_absent,
    ),
)


class MockHead(QFrame):
    """One look, drawn holding one of the two names every look is drawn holding.

    Inert: the icons carry their real tooltips so the row can be judged at the
    width it will really have, and none of them is connected to anything.
    """

    #: The margins a head keeps off the pane's edges. The library's own, so the
    #: baseline is the baseline; the bottom one stands in for the gap between the
    #: head and the first card, which in the real pane is the column's margin.
    MARGIN = 6

    def __init__(
        self, look: Look, title: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("head")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(look.dress())

        #: Read by the arrangements: which of the two names this drawing holds.
        self.title = title

        #: Held whichever arrangement it is put in — and built even for the
        #: arrangements that never add it, so a look that leaves the verbs off
        #: is a look making that choice rather than a shape that happens not to
        #: have them.
        self.verbs = _verb_row()

        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(
            self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN
        )
        self.column.setSpacing(2)
        look.shape(self)


# -- what every arrangement is drawn holding -------------------------------


def _line(title: QWidget, right: QWidget) -> QHBoxLayout:
    """The name taking the row, with one quiet thing at the far end."""
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(title, 1)
    row.addWidget(right, 0)
    return row


def _name(head: MockHead) -> QLabel:
    """The pane's name, elided to whatever width the arrangement leaves it."""
    return _Eliding(head.title)


def _verb_row() -> QWidget:
    """The pane's verbs as one widget, so a look can move them or leave them out
    without the arrangement having to know how many there are."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    # The card's head spaces its buttons by 4 and this row does too: a head and
    # a card seen in the same pane with differently spaced icon rows would be
    # showing a difference nobody chose.
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


def _label(text: str, name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    return label


class _Eliding(QLabel):
    """A label that shortens its text to the room it was given, with an ellipsis.

    A plain `QLabel` does neither half of this. It asks the layout for the width
    of its whole string — which on a pane is a name deciding how narrow the
    splitter may be dragged — and when it is squeezed anyway it cuts the text off
    mid-glyph with nothing saying it did. Both are the wrong answer for a head
    holding a name the user typed, and a gallery that let the mocks do either
    would be comparing looks at a width the pane will not have.

    So the width is given up in both directions: `Ignored` horizontally, so a
    long name never widens the pane, and the text elided at paint time to
    whatever it ended up with. The full name goes in the tooltip, since a title
    that cannot be read at all is not an acceptable end state for any of these.

    Drawn through `drawItemText` rather than with a pen taken from the palette:
    the colour comes from a stylesheet rule on `#htitle`, and it is the polished
    style option that knows what that resolved to.
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("htitle")
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def minimumSizeHint(self) -> QSize:
        """As wide as an ellipsis and as tall as the line. `QLabel` would report
        the whole string here, which is the half of the problem that a size
        policy alone does not fix — a minimum is a floor the layout may not go
        under, policy or not."""
        return QSize(
            self.fontMetrics().horizontalAdvance("…"), super().minimumSizeHint().height()
        )

    def paintEvent(self, event) -> None:
        del event
        option = QStyleOption()
        option.initFrom(self)
        text = self.fontMetrics().elidedText(
            self.text(), Qt.TextElideMode.ElideRight, self.width()
        )
        painter = QPainter(self)
        self.style().drawItemText(
            painter,
            self.rect(),
            int(self.alignment()),
            option.palette,
            self.isEnabled(),
            text,
            self.foregroundRole(),
        )
        painter.end()
