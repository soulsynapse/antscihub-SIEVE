"""One way a card could look, and the handful of ways being considered.

A look is a dress and an arrangement: what the card is painted in when it is
selected and when it is not, and where the title, the four verbs and the knobs
stand. Both halves, together, because the two are not independent — a title
drawn as a filled chip is also the thing carrying selection, so the card's edge
has nothing left to do, and a look that paired that chip with the edge dress
would be arguing for two selection markers at once. A look is therefore a whole
design and is written as one, rather than a point in a grid of dresses × shapes
whose cells mostly nobody would ship.

The dresses are written out one per look and share no fragments on purpose.
These are alternatives, and a fragment two of them read would mean editing one
look changed another — which is exactly the drift a side-by-side comparison is
supposed to make visible rather than hide. The arrangements are the other way
round: `_label`, `_knob_grid` and the like are shared, because those are the
card's *contents* and every look is required to be drawn holding the same
contents. A shape that built its own knob rows could quietly show different
knobs, and then the gallery would be comparing content and look at once.

What is fixed is what a card has to display: its title, the four verbs, and its
knobs. Everything else — where each of those goes, how many lines they take,
what is loud and what is quiet, whether anything is hidden until the card is
current — is what the looks below differ on.

`header bar` breaks that floor upward rather than downward: it draws the four
knobs and the title like everything else, and then a kind icon and a progress
meter besides. That is a real asymmetry and it is deliberate — the argument the
look is making is that the strip and the foot are *room*, and a look claiming to
have found room cannot be judged empty. What is not allowed is the other
direction: a look that dropped a knob or a verb would be a different card, not a
different look.

Nothing here reuses `primitives/card.py`. The real card builds its own head and
re-sets its own sheet, so a look that changed either would have to widen it, and
widening the card to draw the alternatives to the card presumes the answer. The
baseline is the real thing instead, stood at the top of the gallery unmodified
(`view.py`), so the comparison has something true to compare against.
"""

from __future__ import annotations

from typing import Callable, NamedTuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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
#:
#: Public, and split into name and value rather than kept as the two finished
#: strings the card as built shows: half the arrangements below put the names in
#: one column and the values in another, which no pre-joined line can be cut
#: back into. `view.py` fills the real card from these too, through `line()`, so
#: the baseline and the mocks cannot come to be holding different steps.
TITLE = "threshold"
KNOBS: tuple[tuple[str, str], ...] = (("sensitivity", "0.42"), ("min area", "120 px"))

#: What the step is drawn as where a look puts a glyph beside the name. A knobbed
#: step is a slider bank, which is the one thing every card in the chain has and
#: the one thing that differs between them by kind rather than by name.
GLYPH = "sliders-horizontal"

#: How full the meter is drawn. A fraction and not a percentage string: a meter
#: is a width, and the moment it is a string somebody draws it by parsing one.
#: Neither end, so the mock shows both the fill and the groove it runs in — a
#: meter mocked at 0 or 1 is a meter with half of itself untested by the eye.
FULL = 0.62


def line(knob: tuple[str, str]) -> str:
    """A knob as the single string the card as built shows it as."""
    return f"{knob[0]} — {knob[1]}"


class Look(NamedTuple):
    """A candidate card: what it is called, what it costs, and how it is drawn.

    `gloss` is the half worth reading. A gallery of shapes with no argument
    under them is a mood board, and the choice between these is not about which
    is prettiest — it is about what a column of twenty of them does to the eye
    while a slider is being dragged.

    `dress` is handed whether the card is selected and returns the whole sheet,
    rather than being a pair of colours: some of these differ by which property
    carries the selection at all, which no pair of colours can express.

    `shape` is handed the card and fills it — the title, the verb row and the
    knobs, in whatever arrangement the look is about. It reads `card.selected`,
    since an arrangement is allowed to differ between the two states and one of
    these is exactly that.

    `fade` hides the verbs until the pointer arrives. Its own field rather than
    a shape, because it is true or false of *any* arrangement that keeps the
    verbs on the card, and folding it into the shapes would double them.
    """

    name: str
    gloss: str
    dress: Callable[[bool], str]
    shape: Callable[["MockCard"], None]
    fade: bool = False


# -- the dresses -----------------------------------------------------------
#
# Each writes every rule its own arrangement needs and no others. A dress
# carrying rules for object names its shape never builds would be a dress being
# kept ready for a shape it is not paired with, which is the grid this file
# refuses to be.


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
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _table(selected: bool) -> str:
    """The knobs as a two-column table. The value column is the only thing that
    changes while a slider is dragged, so it is the one drawn in `TEXT` and the
    names are handed to `DIM` — the opposite weighting to a line that reads
    `sensitivity — 0.42`, where the label is as loud as the number."""
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar(selected: bool) -> str:
    """The title in a strip of its own, in the ground colour rather than the
    card's fill, so it reads as the card's chrome and the fill below it reads as
    the card's contents. Under the contents, a 4px meter saying how far along
    whatever the step is doing has got.

    The strip is drawn the same in both states — same fill, same hairline under
    it. It has to be legible on every card, since it is what says where one
    card's values stop, and a divider that brightened on the current card would
    make the chrome itself the selection mark: the eye would read a *different*
    header rather than the same header on a selected card. Selection is left to
    the card's border and the title's colour, and the strip is left saying only
    that it is a strip. What keeps it visible without being loud is that it says
    so twice and quietly — a fill a step darker than the card and a hairline —
    rather than once and brightly.

    Its cost is written into these rules and not only into the gloss: `#mockbar`
    is painted unconditionally, so the `#mock:hover` fill reaches the body and
    stops at the strip. A hovered card lights up under its own header, which is
    the price of giving the header a fill of its own.

    The meter's fill follows selection instead of being accent everywhere. The
    accent means *this is what you are acting on* (`palette.py`), and a column of
    twenty cards each with an accent stripe along its bottom spends that meaning
    on twenty things at once. Dim at rest is still a readable bar against the
    `STACK_BG` groove, and the meter is not carrying selection alone — the border
    and the title are already saying it.
    """
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _chip(selected: bool) -> str:
    """The title as a filled tag, which is also where the selection lives — so
    the card keeps no accent edge and no accent border at all.

    The selected chip's text is `STACK_BG` and not `TEXT`: the accent is a light
    teal, and light text on it is the one combination in this palette with no
    contrast left.
    """
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockchip {{
            background: {rgb(ACCENT if selected else PANEL_HOT)};
            color: {rgb(STACK_BG if selected else TEXT)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
            font-weight: 600;
            padding: 1px 7px;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _values_first(selected: bool) -> str:
    """The values given the size and the step name given up as the loud thing.
    What a user scans a tuned chain for is the numbers, not the step names they
    chose; the cost is that a card whose name has gone quiet is harder to find
    when the chain is long and the values mean nothing yet.

    The one place in the gallery that sets a font size. A value drawn at the
    body size and merely coloured `TEXT` is what `table` already is, and the
    argument here is that the number should be reachable at a glance from the
    far side of the pane — which is a size, not a weight.
    """
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockeyebrow {{
            color: {rgb(ACCENT if selected else DIM)};
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockbig {{ color: {rgb(TEXT)}; font-size: 15px; font-weight: 600; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _collapsed(selected: bool) -> str:
    """Two lines at rest and the table only when current. The summary is `DIM`
    and the table's values are `TEXT`, so opening a card is a step up in weight
    as well as in height and the eye is told which card it is reading."""
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL_HOT if selected else PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mocksum {{ color: {rgb(DIM)}; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _rail(selected: bool) -> str:
    """A leading rail of its own carrying the step index, wide enough to hold a
    number instead of the 3px an edge needs. The chain is ordered and nothing
    else on the card says so; the accent moves onto the rail, so the index and
    the selection are one mark rather than two things down the same side."""
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockrail {{ background: {rgb(ACCENT if selected else STACK_BG)}; }}
        #mocklead {{
            color: {rgb(STACK_BG if selected else DIM)};
            font-weight: 600;
        }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


# -- the arrangements ------------------------------------------------------
#
# Each is handed the card and fills `card.column`. They share the content
# helpers at the bottom of the file, and nothing else.


def _shape_head(card: MockCard) -> None:
    """Title and verbs on one line, then one line per knob. What is built."""
    card.column.addLayout(_head(_label(TITLE, "mocktitle"), card.verbs))
    for knob in KNOBS:
        card.column.addWidget(_label(line(knob), "mockline"))


def _shape_verbs_below(card: MockCard) -> None:
    """The verbs off the title line and under the knobs, so the whole width is
    the title's before it has to elide."""
    card.column.addWidget(_label(TITLE, "mocktitle"))
    for knob in KNOBS:
        card.column.addWidget(_label(line(knob), "mockline"))
    below = QHBoxLayout()
    below.setSpacing(4)
    below.addStretch(1)
    below.addWidget(card.verbs)
    card.column.addLayout(below)


def _shape_table(card: MockCard) -> None:
    """The knobs as name and value in two columns."""
    card.column.addLayout(_head(_label(TITLE, "mocktitle"), card.verbs))
    card.column.addLayout(_knob_grid())


def _shape_bar(card: MockCard) -> None:
    """The head lifted into a strip of its own, full bleed to the card's edges,
    with the step's icon ahead of its name and a meter across the card's foot.

    Which is why this shape takes the card's margins away and gives them back
    inside the three parts: a strip inset by 8px is a panel sitting on a card,
    and the argument here is that the title is the card's lid.

    The icon leads the title rather than sitting with the verbs at the other end.
    It is not a verb — nothing happens when it is clicked — and a glyph in a row
    of four things that do act is a fifth button that refuses to be pressed. Ahead
    of the name it is read as part of the name: what *kind* of step this is,
    answered before the name says which one, which is what makes a column of
    twenty scannable by shape before it is read by word.
    """
    card.column.setContentsMargins(0, 0, 0, 0)
    card.column.setSpacing(0)

    bar = QWidget()
    bar.setObjectName("mockbar")
    bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    inside = QHBoxLayout(bar)
    inside.setContentsMargins(8, 5, 6, 5)
    inside.setSpacing(4)
    inside.addWidget(_glyph(GLYPH, ACCENT if card.selected else DIM))
    inside.addWidget(_label(TITLE, "mocktitle"), 1)
    inside.addWidget(card.verbs)
    card.column.addWidget(bar)

    body = _knob_grid()
    body.setContentsMargins(8, 7, 8, 8)
    card.column.addLayout(body)

    card.column.addWidget(_meter(FULL))


#: How tall the meter is, and the number the look is named for. Four pixels is
#: the smallest bar that still reads as a length rather than as a hairline that
#: happens to be two colours, and it is small enough that a card carrying one is
#: not a card carrying a progress widget.
_METER = 4


def _meter(full: float) -> QWidget:
    """A 4px bar across the card's foot saying how far along the step is.

    The fill is a stretch factor and not a fixed width, so the bar stays right at
    any card width — the mocks are drawn at one width but the pane they will sit
    in is a splitter, and a meter that only reads at 300px is a meter that will
    be wrong the first time somebody drags the seam. Thousandths, because a
    stretch is an integer ratio and hundredths visibly quantise a slow bar.

    Full bleed like the strip above it and for the same reason: inset by the
    body's 8px it would be a widget lying on the card, and what it is is the
    card's own foot. Both children are told to style their background, since a
    plain `QWidget` ignores a sheet's `background` without it.
    """
    bar = QWidget()
    bar.setObjectName("mockmeter")
    bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    bar.setFixedHeight(_METER)

    done = QWidget()
    done.setObjectName("mockfull")
    done.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    inside = QHBoxLayout(bar)
    inside.setContentsMargins(0, 0, 0, 0)
    inside.setSpacing(0)
    filled = max(0, min(1000, round(full * 1000)))
    inside.addWidget(done, filled)
    inside.addStretch(1000 - filled)
    return bar


def _glyph(name: str, colour: QColor) -> QLabel:
    """An icon beside a label rather than on a button.

    A `QLabel` holding a pixmap and not a `QToolButton`: a tool button in the
    head would be hoverable and pressable, and this one means nothing when
    pressed. Its colour is chosen here and not in the dress, because a pixmap is
    not text and no stylesheet rule reaches inside one — which is the same trade
    `icons/__init__.py` describes making for the verbs.
    """
    label = QLabel()
    label.setPixmap(icons.pixmap(name, colour))
    label.setFixedSize(QSize(icons.SIZE, icons.SIZE))
    return label


def _shape_chip(card: MockCard) -> None:
    """The title as a tag rather than as bold text.

    The chip is added without a stretch factor and with the stretch after it, so
    it is the width of the name it holds — a chip taking the row's remainder is
    a header bar with rounded ends and not a tag.
    """
    chip = _label(TITLE, "mockchip")
    chip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    head = QHBoxLayout()
    head.setSpacing(4)
    head.addWidget(chip, 0)
    head.addStretch(1)
    head.addWidget(card.verbs)
    card.column.addLayout(head)
    card.column.addLayout(_knob_grid())


def _shape_values_first(card: MockCard) -> None:
    """The step name as a small caps eyebrow and each value as the big text.

    The verbs stay on the eyebrow's line rather than dropping to the values',
    which would put the row of icons at the same weight as the numbers it is
    supposed to sit quietly beside.
    """
    card.column.addLayout(_head(_label(TITLE, "mockeyebrow"), card.verbs))
    grid = QGridLayout()
    grid.setContentsMargins(0, 2, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(2)
    for row, (name, value) in enumerate(KNOBS):
        grid.addWidget(_label(value, "mockbig"), row, 0)
        label = _label(name, "mockname")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(label, row, 1)
    grid.setColumnStretch(1, 1)
    card.column.addLayout(grid)


def _shape_collapsed(card: MockCard) -> None:
    """One summary line at rest; the table only on the current card.

    The verbs are on the head in both states rather than appearing with the
    table. A verb that arrives only once the card is current is a verb that
    cannot be used to make a card current, and ✕ on a card you did not want to
    select is the commonest of the four.
    """
    card.column.addLayout(_head(_label(TITLE, "mocktitle"), card.verbs))
    if card.selected:
        card.column.addLayout(_knob_grid())
    else:
        card.column.addWidget(_label(" · ".join(v for _, v in KNOBS), "mocksum"))


def _shape_rail(card: MockCard) -> None:
    """A full-height leading rail holding the step index, then the usual head
    and table in the room left over."""
    card.column.setContentsMargins(0, 0, 0, 0)
    card.column.setSpacing(0)

    rail = QWidget()
    rail.setObjectName("mockrail")
    rail.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    rail.setFixedWidth(22)
    inside = QVBoxLayout(rail)
    inside.setContentsMargins(0, 7, 0, 0)
    index = _label(str(card.index), "mocklead")
    index.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    inside.addWidget(index)
    inside.addStretch(1)

    right = QVBoxLayout()
    right.setContentsMargins(8, 6, 8, 8)
    right.setSpacing(4)
    right.addLayout(_head(_label(TITLE, "mocktitle"), card.verbs))
    right.addLayout(_knob_grid())

    beside = QHBoxLayout()
    beside.setContentsMargins(0, 0, 0, 0)
    beside.setSpacing(0)
    beside.addWidget(rail)
    beside.addLayout(right, 1)
    card.column.addLayout(beside)


#: The shapes on the bench, in the order they are argued about. `as built` is
#: first so every look below it is read as a change *from* something, and the
#: real card stands above all of them in the gallery. The dress-only looks come
#: before the rearrangements, since a reader who has not yet seen what selection
#: costs cannot judge a shape that moves it somewhere else.
LOOKS: tuple[Look, ...] = (
    Look(
        "as built, redrawn",
        "the current dress, drawn by this file — if it differs from the real "
        "card above, this file has drifted and is what to fix",
        _as_built,
        _shape_head,
    ),
    Look(
        "verbs on hover",
        "four icons on every card is twenty-four icons in a six-step chain; "
        "hidden until the pointer arrives, the column is only titles and values "
        "— and a verb nobody hovers is a verb nobody finds",
        _as_built,
        _shape_head,
        fade=True,
    ),
    Look(
        "verbs below",
        "the title line becomes only the title, so a long step name has the "
        "whole width before it elides; costs a row of height on every card",
        _as_built,
        _shape_verbs_below,
    ),
    Look(
        "fill, not edge",
        "selection as a filled panel — reads from further away than a 3px edge, "
        "and collides with hover, which is also a fill",
        _fill,
        _shape_head,
    ),
    Look(
        "accent rule on top",
        "the same accent across the card's lid instead of down its side",
        _rule,
        _shape_head,
    ),
    Look(
        "flat, no hairline",
        "borders dropped; the gutter and the fill do the separating",
        _flat,
        _shape_head,
    ),
    Look(
        "table",
        "knob names left and values in a right-aligned column of their own, so "
        "a chain's numbers land on one x and are read by moving the eye "
        "straight down; the ragged `name — value` line cannot be scanned that "
        "way. Costs the names their weight, and a value long enough to reach "
        "the names is a value that will collide with one",
        _table,
        _shape_table,
    ),
    Look(
        "header bar",
        "the title in a full-bleed strip in the ground colour, its kind as an "
        "icon ahead of the name and the verbs at the far end — the head becomes "
        "chrome and everything below it is contents, which is what tells a "
        "reader where one card's values stop. The strip is drawn identically on "
        "both cards, so it stays a strip rather than becoming a second selection "
        "mark. A 4px meter across the foot says how far along the step is, which "
        "is the one number a long crop or a full-clip pass has that no knob row "
        "can hold. Costs a second fill per card, takes the hover tint off the "
        "head, and adds four pixels every card pays whether or not it is running",
        _bar,
        _shape_bar,
    ),
    Look(
        "title as a chip",
        "the name as a filled tag, which is where selection lives too, so the "
        "card carries no accent edge — one mark instead of two down one side, "
        "and the mark is on the thing that names the card. Costs the width of "
        "the tag's padding, and a long name makes a very wide tag",
        _chip,
        _shape_chip,
    ),
    Look(
        "values first",
        "the numbers at fifteen pixels and the step name a small caps eyebrow "
        "above them — a tuned chain is scanned for values, and this is the only "
        "look where they are reachable from the far side of the pane. Costs the "
        "most height of anything here, and a chain nobody has tuned yet is a "
        "column of large meaningless numbers over quiet names",
        _values_first,
        _shape_values_first,
    ),
    Look(
        "collapsed until current",
        "values folded to one dim summary line at rest and opened to the table "
        "only on the current card — twenty steps fit in the pane at once. Costs "
        "the thing the fold is for: the values you scan a chain for are the "
        "ones now hidden, and the column reflows every time selection moves",
        _collapsed,
        _shape_collapsed,
    ),
    Look(
        "index rail",
        "a full-height leading rail holding the step number, carrying the "
        "accent instead of the edge — the chain is ordered and this is the only "
        "look that says so. Costs 22px of every card, including the cards in a "
        "list that has no order at all",
        _rail,
        _shape_rail,
    ),
)


class MockCard(QFrame):
    """One look, drawn holding the same step every other look is drawn holding.

    Inert: the icons carry their real tooltips so the row can be judged at the
    width it will really have, and none of them is connected to anything. A
    mockup that acted would be a card, and there is already one of those.

    The verb row and the column are built here and the arrangement is handed
    both. It is the other way round from where this file started — the card used
    to hold the two arrangements there were — because the shapes now differ by
    more than where one row lands, and a card that knew all of them would be the
    card-with-options this bench exists to avoid building.
    """

    def __init__(
        self, look: Look, selected: bool, index: int = 3, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(look.dress(selected))

        #: Read by the arrangements. `selected` because a shape is allowed to
        #: differ between the two states, and `index` because one of them puts a
        #: step number on the card.
        self.selected = selected
        self.index = index

        #: Held whichever arrangement it is put in, so `enterEvent` has
        #: something to show without knowing where the row ended up.
        self.verbs = _verb_row()

        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(8, 6, 8, 8)
        self.column.setSpacing(4)
        look.shape(self)

        #: Hidden rather than left out, so the card is the height it would be
        #: with the row showing and does not jump under the pointer — which is
        #: half of what this look has to be judged on.
        self._fades = look.fade
        if self._fades:
            self.verbs.setVisible(False)

    def enterEvent(self, event) -> None:
        if self._fades:
            self.verbs.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._fades:
            self.verbs.setVisible(False)
        super().leaveEvent(event)


# -- what every arrangement is drawn holding -------------------------------


def _head(title: QLabel, verbs: QWidget) -> QHBoxLayout:
    """The title with the verbs at the end of its line.

    The title takes the row's remainder rather than a stretch sitting after it,
    the way `project_list/card.py` does: a label reports no width of its own
    under an `Ignored` policy, and the two arrangements have to agree about who
    is asking for the room before a title long enough to matter can be judged.
    """
    row = QHBoxLayout()
    row.setSpacing(4)
    row.addWidget(title, 1)
    row.addWidget(verbs)
    return row


def _knob_grid() -> QGridLayout:
    """The knobs as name left, value right-aligned in a column of its own.

    The value column is right-aligned and the stretch is on the name's, so the
    numbers land on the card's right edge — which is the same x on every card in
    a column, and is the whole of what makes a table readable at a glance.
    """
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(4)
    for row, (name, value) in enumerate(KNOBS):
        grid.addWidget(_label(name, "mockname"), row, 0)
        value_label = _label(value, "mockvalue")
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        grid.addWidget(value_label, row, 1)
    grid.setColumnStretch(0, 1)
    return grid


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


def _label(text: str, name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    return label
