"""One way a card could look, and the handful of ways being considered.

A look is a dress and an arrangement: what the card is painted in when it is
selected and when it is not, and where the title, the four verbs and the knobs
stand. Both halves, together, because the two are not independent — a strip that
takes the accent when the card is current is also the thing carrying selection,
so the card's edge has nothing left to do, and a look that paired that strip
with an accent border would be arguing for two selection markers at once. A look
is therefore a whole design and is written as one, rather than a point in a grid
of dresses × shapes whose cells mostly nobody would ship.

The bench has narrowed. Every look below except the first is a *header bar*: a
full-bleed strip in the ground colour carrying the step's kind, its name and the
four verbs, a body of knobs under it, and a meter across the foot. The
arguments the earlier bench held about the card's edge — accent left rail,
accent rule on the lid, no hairline at all — are mostly settled by that chassis,
because a card bounded above by a strip and below by a meter is already bounded;
what is left of them survives here as `borderless`, which is that argument asked
again in the one form the chassis does not answer. The rest of the looks differ
on what the chassis leaves open: what the body says, what leads the strip, and
where and how thick the meter runs.

`as built, redrawn` stays at the top and stays un-headered on purpose. It is not
a candidate — it is the drift canary, drawn by this file and stood under the
real card in the gallery so a difference between them is visible rather than
hidden. Turning it into a header bar would leave the gallery with no baseline.

What is fixed is what a card has to display: its title, the four verbs, and its
knobs. A look that dropped a knob or a verb would be a different card, not a
different look. `percent in the strip` adds a thing rather than dropping one,
which is allowed and is the whole of its argument.

The dresses are written out one per look and share no fragments on purpose.
These are alternatives, and a fragment two of them read would mean editing one
look changed another — which is exactly the drift a side-by-side comparison is
supposed to make visible rather than hide. The arrangements are the other way
round: `_chassis`, `_strip`, `_meter`, `_knob_grid` and the like are shared,
because those are the card's *contents and frame* and every look is required to
be drawn holding the same contents in the same frame. That division moved when
the bench narrowed — the strip and the meter used to belong to one look and now
belong to all of them, so they crossed from the unshared half of the file to the
shared half. The test has not changed: a thing every look must draw identically
is shared, and a thing the looks are arguing about is written out per look.

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
    QLayout,
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
    since an arrangement is allowed to differ between the two states and two of
    these are exactly that.

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
    """The card as `primitives/card.py` draws it, redrawn here as the baseline
    the header bars are varied from — the real one is in the gallery too, above
    this."""
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


def _bar_lines(selected: bool) -> str:
    """The same chassis with the body back to one `name — value` line per knob.

    Worth drawing because the table under a strip is doing two things at once —
    the strip already gives the card a left edge to hang names from, and a right
    aligned value column adds a second. A line reads as a sentence and a table
    reads as data; which of the two a knob row is is exactly the open question.
    Both halves of the line are `DIM` here, as the built card has them.
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
        #mockline {{ color: {rgb(DIM)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_values(selected: bool) -> str:
    """Values at fifteen pixels in the body, with the strip left alone.

    This is the one pairing the earlier bench could not make: `values first`
    used to spend the card's head on a small caps eyebrow to get the numbers
    top billing, and with a strip carrying the name there is nothing left for
    the body to do but be numbers. The name is in the chrome, the numbers are
    the contents, and the two are no longer competing for one line.
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
        #mockbig {{ color: {rgb(TEXT)}; font-size: 15px; font-weight: 600; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_collapsed(selected: bool) -> str:
    """One dim summary line at rest, the table only when current.

    Folding is cheaper under a header bar than it was without one. The card's
    chrome — strip, meter — is the same height in both states, so what reflows
    when selection moves is only the body between them, and the column's rhythm
    of lids and feet survives the reflow. The summary is `DIM` against the
    table's `TEXT` values, so opening a card steps up in weight as well as in
    height.
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
        #mocksum {{ color: {rgb(DIM)}; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_accent(selected: bool) -> str:
    """Selection moved onto the strip — the refusal the committed look wrote
    down, drawn so it can be checked rather than taken on the argument.

    The whole lid takes the accent and the card keeps no accent border, so there
    is one mark per card instead of two. It reads from much further away than a
    1px border does, which is the case for it. Against it is what the committed
    dress says: with the strip painted differently on the current card, the eye
    is asked to recognise the header shape itself as the selection mark, and a
    column scanned quickly reads that as a different kind of card rather than as
    the same card selected.

    Selected text on the strip is `STACK_BG`, not `TEXT`: the accent is a light
    teal and light text on it is the one combination in this palette with no
    contrast left. The glyph is handed the same colour in the shape, since no
    stylesheet rule reaches inside a pixmap.
    """
    strip = ACCENT if selected else STACK_BG
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(strip)};
            border-bottom: 1px solid {rgb(strip if selected else LINE)};
        }}
        #mocktitle {{
            color: {rgb(STACK_BG if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_numbered(selected: bool) -> str:
    """The step's index leading the strip in place of the kind glyph.

    The chain is ordered and nothing else on the card says so. The index rail
    the earlier bench drew spent 22px of every card's width saying it; in the
    strip it costs a dozen pixels of a row that already exists. What it costs
    instead is the lead position: the glyph said what *kind* of step this is
    before the name said which one, and a number says neither. The index is
    `DIM` and tabular-width so a two-digit step does not shove the title.
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
        #mocklead {{ color: {rgb(ACCENT if selected else DIM)}; font-weight: 600; }}
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


def _bar_borderless(selected: bool) -> str:
    """The card's hairline dropped entirely; the strip and the meter bound it.

    This is the old `flat` argument asked again where it is strongest. A card
    with a dark lid and a dark foot already has a top and a bottom edge that are
    darker than its fill, so the hairline around it is drawing a boundary that
    is mostly already drawn, and the sides are held by the gutter. What it gives
    up is the same thing `flat` gave up — the card's left and right edges, which
    only matter against a pane the same colour as the card.

    Selection has to move somewhere with the border gone, so it is on the body
    fill and the title, and the meter's accent is doing more work here than
    anywhere else on the bench.
    """
    return f"""
        #mock {{
            background: {rgb(PANEL_HOT if selected else PANEL)};
            border: 0;
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{ background: {rgb(STACK_BG)}; }}
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


def _bar_meter_high(selected: bool) -> str:
    """The meter moved from the foot to directly under the strip.

    All of the card's chrome then sits in one block at the top — lid, progress,
    then contents — and the card's bottom edge is the plain hairline every other
    card in the column has, which is easier to keep aligned than a coloured
    foot. Against it: a bar immediately under a title is the shape every browser
    and installer uses for *this title is loading*, so the eye attaches it to the
    header rather than to the step. The groove is `PANEL` here and not
    `STACK_BG`, since it now sits on the body's fill rather than on the card's
    edge, and a `STACK_BG` groove there would read as a second divider.
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
        #mockmeter {{ background: {rgb(PANEL)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_meter_inset(selected: bool) -> str:
    """A 6px rounded meter inset to the body's margin instead of a 4px foot.

    Which makes it a progress *widget* rather than the card's foot, and that is
    the argument: a bar with ends and a visible groove is read as a measurement
    of the thing above it, where a full-bleed 4px strip is read as an edge that
    happens to be two colours. The cost is that the card now contains a control
    it does not contain, and 6px plus the margin is roughly triple the height
    the foot version spends on every card whether or not it is running.
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
        #mockmeter {{ background: {rgb(STACK_BG)}; border-radius: 3px; }}
        #mockfull {{
            background: {rgb(ACCENT if selected else DIM)};
            border-radius: 3px;
        }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_meter_divider(selected: bool) -> str:
    """The strip's own divider *is* the meter: 2px, filled from the left.

    The cheapest version of the idea — the card grows by one pixel over a plain
    hairline and by nothing at all over the divider it already had, so a chain
    of twenty cards pays nothing in height for saying how far each has got. The
    groove is `LINE`, the divider's colour, so an idle card looks exactly like a
    card with a divider and a running one looks like the divider filling in.

    Against it, and it is the same objection the 4px foot was chosen over:
    two pixels is a hairline that happens to be two colours. It cannot be read
    from across the pane, and on the card where progress matters most — a long
    full-clip pass — the one number worth watching is the hardest thing on the
    card to see.
    """
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{ background: {rgb(STACK_BG)}; }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(LINE)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_percent(selected: bool) -> str:
    """The meter's number written out in the strip, before the verbs.

    A bar answers *roughly how far*, and there is no length at which it answers
    *how much longer*. The number does, and the strip is the one row on the card
    with somewhere to put it — right-aligned against the verbs, `DIM`, so it
    reads as chrome and not as a knob value.

    Two costs. The number is the only text on the card that changes while
    nothing is being dragged, and a column of twenty of them ticking is motion
    the tuning loop did not ask for; and the strip is now four things wide, so
    a step name has less room before it elides than in any other look here.
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
        #mockpct {{ color: {rgb(DIM)}; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_hover(selected: bool) -> str:
    """The committed dress, with the verbs hidden until the pointer arrives.

    A dress of its own rather than `_bar` reused with `fade=True`, because the
    two are different arguments and this file's rule is that a shared fragment
    means editing one look changes another. The claim: four icons on every card
    is twenty-four in a six-step chain, and a strip whose height is fixed
    (`_STRIP`) can drop them and get them back without the card moving a pixel —
    which is what made hover verbs unaffordable when the head was a text row
    that sized itself. Resting cards are then a column of kinds and names.
    The cost is the old one and it is not fixed by the strip: a verb nobody
    hovers is a verb nobody finds.
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


# -- the chassis -----------------------------------------------------------
#
# What every header bar draws identically, held here rather than in each shape
# for the reason the module docstring gives: these are the frame the looks are
# argued inside, not the thing being argued about.

#: How tall the strip is. Fixed rather than left to its contents, so a look that
#: hides the verbs does not get a shorter lid than one that shows them — the
#: gallery is read down a column and a header that changed height between looks
#: would be a difference nobody asked for. Tall enough for a `QToolButton`
#: holding a 16px icon, which is the tallest thing in the row.
_STRIP = 28

#: The body's margins: level with the strip's leading inset, so a knob name and
#: the title above it stand on one x.
_BODY = (8, 7, 8, 8)

#: How tall the meter is where a look does not say otherwise, and the number the
#: committed look was drawn with. Four pixels is the smallest bar that still
#: reads as a length rather than as a hairline that happens to be two colours,
#: and it is small enough that a card carrying one is not a card carrying a
#: progress widget. `meter as the divider` and `inset meter` are the two looks
#: arguing with that number, from either side of it.
_METER = 4


def _chassis(card: MockCard, *pieces: QWidget | QLayout) -> None:
    """Stack the card's parts full bleed, in order, with nothing between them.

    The card's own margins go to zero and each piece gives itself back whatever
    inset it wants. That is the whole of what makes a header bar a header bar: a
    strip inset by 8px is a panel sitting on a card, and the argument every look
    below is making is that the strip is the card's lid and the meter is its
    foot.
    """
    card.column.setContentsMargins(0, 0, 0, 0)
    card.column.setSpacing(0)
    for piece in pieces:
        if isinstance(piece, QWidget):
            card.column.addWidget(piece)
        else:
            card.column.addLayout(piece)


def _strip_row(card: MockCard, lead: QWidget, *tail: QWidget) -> QWidget:
    """The lid: what the card leads with, its name, and the verbs at the far end.

    `lead` is a widget and not a name, because the looks disagree about what
    leads — a kind glyph on most of them, a step index on one. Whatever it is,
    it is not a verb: nothing happens when it is pressed, and a glyph in a row
    of four things that do act is a fifth button that refuses to be pressed.
    Ahead of the name it is read as part of the name, which is what makes a
    column of twenty scannable by shape before it is read by word.

    `tail` is whatever goes between the title and the verbs, which is nothing on
    every look but `percent in the strip`. The verbs are added last here rather
    than passed in, so no look can accidentally put them anywhere but the end of
    the row.
    """
    bar = QWidget()
    bar.setObjectName("mockbar")
    bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    bar.setFixedHeight(_STRIP)
    inside = QHBoxLayout(bar)
    inside.setContentsMargins(8, 0, 6, 0)
    inside.setSpacing(4)
    inside.addWidget(lead)
    inside.addWidget(_label(TITLE, "mocktitle"), 1)
    for extra in tail:
        inside.addWidget(extra)
    inside.addWidget(card.verbs)
    return bar


def _meter(full: float, height: int = _METER) -> QWidget:
    """A bar across the card saying how far along the step is.

    The fill is a stretch factor and not a fixed width, so the bar stays right at
    any card width — the mocks are drawn at one width but the pane they will sit
    in is a splitter, and a meter that only reads at 300px is a meter that will
    be wrong the first time somebody drags the seam. Thousandths, because a
    stretch is an integer ratio and hundredths visibly quantise a slow bar.

    Both children are told to style their background, since a plain `QWidget`
    ignores a sheet's `background` without it.
    """
    bar = QWidget()
    bar.setObjectName("mockmeter")
    bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    bar.setFixedHeight(height)

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
    pressed. Its colour is chosen at the call site and not in the dress, because
    a pixmap is not text and no stylesheet rule reaches inside one — which is the
    same trade `icons/__init__.py` describes making for the verbs.
    """
    label = QLabel()
    label.setPixmap(icons.pixmap(name, colour))
    label.setFixedSize(QSize(icons.SIZE, icons.SIZE))
    return label


def _kind(card: MockCard) -> QLabel:
    """The step's kind, tinted for the state the card is in. Accent when current
    because the title beside it is, and a dim glyph next to an accent name reads
    as an icon that failed to update rather than as chrome."""
    return _glyph(GLYPH, ACCENT if card.selected else DIM)


# -- the arrangements ------------------------------------------------------
#
# Each is handed the card and fills `card.column` out of the chassis above and
# the content helpers at the bottom of the file, and holds nothing else.


def _shape_head(card: MockCard) -> None:
    """Title and verbs on one line, then one line per knob. What is built."""
    card.column.addLayout(_head(_label(TITLE, "mocktitle"), card.verbs))
    for knob in KNOBS:
        card.column.addWidget(_label(line(knob), "mockline"))


def _shape_bar(card: MockCard) -> None:
    """Strip, table, 4px foot. The header bar as it stands."""
    _chassis(card, _strip_row(card, _kind(card)), _inset(_knob_grid()), _meter(FULL))


def _shape_bar_lines(card: MockCard) -> None:
    """The same, with the body as one line per knob."""
    _chassis(card, _strip_row(card, _kind(card)), _inset(_line_stack()), _meter(FULL))


def _shape_bar_values(card: MockCard) -> None:
    """The same, with the values at 15px and their names beside them.

    The names go to the right of the values rather than above them: the strip
    has already spent the card's top line on the step's name, and a second
    label line under it would put two names over one number.
    """
    grid = QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(2)
    for row, (name, value) in enumerate(KNOBS):
        grid.addWidget(_label(value, "mockbig"), row, 0)
        label = _label(name, "mockname")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(label, row, 1)
    grid.setColumnStretch(1, 1)
    _chassis(card, _strip_row(card, _kind(card)), _inset(grid), _meter(FULL))


def _shape_bar_collapsed(card: MockCard) -> None:
    """One summary line at rest; the table only on the current card.

    The verbs stay in the strip in both states rather than arriving with the
    table. A verb that appears only once the card is current is a verb that
    cannot be used to make a card current, and ✕ on a card you did not want to
    select is the commonest of the four.
    """
    if card.selected:
        body: QLayout = _knob_grid()
    else:
        body = QVBoxLayout()
        body.setSpacing(0)
        body.addWidget(_label(" · ".join(v for _, v in KNOBS), "mocksum"))
    _chassis(card, _strip_row(card, _kind(card)), _inset(body), _meter(FULL))


def _shape_bar_numbered(card: MockCard) -> None:
    """The index in the lead position instead of the kind glyph.

    Given the glyph's fixed width so the titles down a column start on one x
    whether the step is 3 or 12, and centred in it — a number that grew the lead
    would shove every title on the card by a digit.
    """
    lead = _label(str(card.index), "mocklead")
    lead.setFixedWidth(icons.SIZE)
    lead.setAlignment(Qt.AlignmentFlag.AlignCenter)
    _chassis(card, _strip_row(card, lead), _inset(_knob_grid()), _meter(FULL))


def _shape_bar_meter_high(card: MockCard) -> None:
    """The meter directly under the strip instead of across the foot."""
    _chassis(
        card, _strip_row(card, _kind(card)), _meter(FULL), _inset(_knob_grid())
    )


def _shape_bar_meter_inset(card: MockCard) -> None:
    """A taller meter held off the card's edges by the body's own margin."""
    held = QHBoxLayout()
    held.setContentsMargins(8, 0, 8, 8)
    held.addWidget(_meter(FULL, 6))
    body = _inset(_knob_grid())
    body.setContentsMargins(8, 7, 8, 6)
    _chassis(card, _strip_row(card, _kind(card)), body, held)


def _shape_bar_meter_divider(card: MockCard) -> None:
    """No foot: the 2px line under the strip is the meter.

    The strip's own `border-bottom` is dropped in this look's dress, so the
    meter is the divider rather than sitting under one — two lines there would
    be three pixels of chrome pretending to be one.
    """
    _chassis(
        card, _strip_row(card, _kind(card)), _meter(FULL, 2), _inset(_knob_grid())
    )


def _shape_bar_percent(card: MockCard) -> None:
    """The meter's number in the strip, between the title and the verbs."""
    percent = _label(f"{round(FULL * 100)}%", "mockpct")
    _chassis(
        card,
        _strip_row(card, _kind(card), percent),
        _inset(_knob_grid()),
        _meter(FULL),
    )


def _shape_bar_accent(card: MockCard) -> None:
    """The committed arrangement with everything in the lid tinted for it.

    Its own shape and not `_shape_bar` reused, for the reason `_glyph` exists at
    all: a pixmap's colour is chosen where it is built, and on a selected card
    here the strip behind it is the accent, so the `ACCENT` glyph and the `DIM`
    verbs every other look leads with would be smudges on a teal bar. All of
    them go to `STACK_BG`, which is what the title beside them uses.

    The verbs are rebuilt rather than recoloured, since the card hands its
    arrangement a row it has already made. Their hover colour goes to `STACK_BG`
    too, which is the accent lid's third cost and the one nothing can be done
    about: the accent is already on the strip, so there is none left to mark the
    verb under the pointer with, and the `autoRaise` frame is all that is left
    saying which one is about to be pressed.
    """
    if card.selected:
        card.verbs = _verb_row(STACK_BG, STACK_BG)
    lead = _glyph(GLYPH, STACK_BG if card.selected else DIM)
    _chassis(card, _strip_row(card, lead), _inset(_knob_grid()), _meter(FULL))


#: The looks on the bench, in the order they are argued about. `as built` is
#: first and is the only one that is not a header bar — the real card stands
#: above it in the gallery and the two together are what makes drift visible.
#: Then the header bar as it stands, then the looks that vary its body, then its
#: strip, then its meter: a reader who has not seen the chassis whole cannot
#: judge a variation on one third of it.
LOOKS: tuple[Look, ...] = (
    Look(
        "as built, redrawn",
        "the current dress, drawn by this file — if it differs from the real "
        "card above, this file has drifted and is what to fix. The only look "
        "here with no header bar, kept as the thing the rest are changes from",
        _as_built,
        _shape_head,
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
        "lines, not a table",
        "the same chassis with `sensitivity — 0.42` per knob instead of two "
        "columns. A line is read as a sentence and a table as data; the table "
        "puts every value in a chain on one x, and the line keeps the knob's "
        "name at the weight of the thing it names. Cheapest to fill from a step "
        "that has not decided how many knobs it has",
        _bar_lines,
        _shape_bar_lines,
    ),
    Look(
        "values first",
        "the numbers at fifteen pixels in the body, reachable from the far side "
        "of the pane, with the step's name left to the strip — the pairing the "
        "old `values first` could not make, since it had to spend the head on an "
        "eyebrow to get the numbers top billing. Costs the most height here, and "
        "a chain nobody has tuned yet is a column of large meaningless numbers",
        _bar_values,
        _shape_bar_values,
    ),
    Look(
        "collapsed until current",
        "values folded to one dim summary line at rest and opened to the table "
        "only on the current card — twenty steps fit in the pane at once, and "
        "the chrome above and below the fold does not move when selection does. "
        "Costs the thing the fold is for: the values you scan a chain for are "
        "the ones now hidden",
        _bar_collapsed,
        _shape_bar_collapsed,
    ),
    Look(
        "accent strip",
        "the lid itself takes the accent on the current card and the border "
        "gives it up — one selection mark instead of two, and it reads from "
        "across the room. This is the arrangement the committed look wrote a "
        "paragraph refusing: with the strip painted differently, the eye reads a "
        "different *kind* of card rather than the same card selected. Drawn so "
        "the refusal can be checked instead of taken. Costs the verbs their "
        "hover tint on the current card — the accent is under them now",
        _bar_accent,
        _shape_bar_accent,
    ),
    Look(
        "numbered strip",
        "the step's index in the lead position instead of its kind — the chain "
        "is ordered and nothing else on the card says so, and the strip says it "
        "for a dozen pixels where the old index rail spent 22 of every card's "
        "width. Costs the lead: a glyph says what kind of step this is before "
        "the name says which one, and a number says neither",
        _bar_numbered,
        _shape_bar_numbered,
    ),
    Look(
        "borderless",
        "the hairline dropped: a dark lid and a dark foot already give the card "
        "a top and a bottom edge, and the gutter holds the sides. Quietest thing "
        "on the bench in a long column. Costs the one thing a border does that a "
        "lid and a gutter cannot — saying where a card ends when the pane behind "
        "it is the card's own colour",
        _bar_borderless,
        _shape_bar,
    ),
    Look(
        "meter under the head",
        "the meter moved from the foot to under the strip, so all the chrome is "
        "one block at the top and the card's bottom edge stays a plain hairline. "
        "Costs the meter its subject: a bar directly under a title is the shape "
        "every installer uses for *this title is loading*, and the eye attaches "
        "it to the header rather than to the step",
        _bar_meter_high,
        _shape_bar_meter_high,
    ),
    Look(
        "inset meter",
        "6px, rounded, held off the card's edges by the body's margin — a bar "
        "with ends reads as a measurement of the card, where a full-bleed 4px "
        "strip reads as an edge that happens to be two colours. Costs about "
        "triple the height, and makes the card look like it contains a control "
        "it does not contain",
        _bar_meter_inset,
        _shape_bar_meter_inset,
    ),
    Look(
        "meter as the divider",
        "no foot at all: the 2px line under the strip is the meter, so progress "
        "costs the card nothing in height over the divider it already had. Costs "
        "legibility, which is the whole point of a meter — on the long full-clip "
        "pass where progress matters most, it is the hardest thing on the card "
        "to see",
        _bar_meter_divider,
        _shape_bar_meter_divider,
    ),
    Look(
        "percent in the strip",
        "the meter's number written out before the verbs, because a bar answers "
        "*roughly how far* at any length and never answers *how much longer*. "
        "Costs the title its room — the strip is four things wide now — and puts "
        "the only text on the card that changes while nothing is being dragged "
        "into twenty cards at once",
        _bar_percent,
        _shape_bar_percent,
    ),
    Look(
        "verbs on hover",
        "the strip holds only the kind and the name until the pointer arrives. "
        "Four icons on every card is twenty-four in a six-step chain, and a "
        "fixed-height strip can drop them and get them back without the card "
        "moving a pixel — which is what made this unaffordable when the head "
        "sized itself. Costs the old thing hover costs: a verb nobody hovers is "
        "a verb nobody finds",
        _bar_hover,
        _shape_bar,
        fade=True,
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
        #: step number in the strip.
        self.selected = selected
        self.index = index

        #: Held whichever arrangement it is put in, so `enterEvent` has
        #: something to show without knowing where the row ended up.
        self.verbs = _verb_row()

        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(8, 6, 8, 8)
        self.column.setSpacing(4)
        look.shape(self)

        #: Hidden rather than left out. On the un-headered baseline this is what
        #: keeps the card the height it would be with the row showing; on a
        #: header bar the strip's fixed height already guarantees that, which is
        #: half of what `verbs on hover` is claiming.
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


def _inset(body: QLayout) -> QLayout:
    """A body layout given the card's margins back, since the chassis took the
    card's own away. Handed the layout and returning it, so a shape reads as one
    expression rather than as three statements about margins."""
    body.setContentsMargins(*_BODY)
    return body


def _head(title: QLabel, verbs: QWidget) -> QHBoxLayout:
    """The title with the verbs at the end of its line, for the baseline.

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


def _line_stack() -> QVBoxLayout:
    """The knobs as one `name — value` line each, which is what is built."""
    stack = QVBoxLayout()
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(4)
    for knob in KNOBS:
        stack.addWidget(_label(line(knob), "mockline"))
    return stack


def _verb_row(normal: QColor = DIM, active: QColor = ACCENT) -> QWidget:
    """The four icons as one widget, so a look can move them or hide them
    without the arrangement having to know there are four.

    The two colours are arguments because one look draws the verbs on an accent
    lid, where the defaults are a grey icon and a teal hover both sitting on
    teal. A pixmap's colour is chosen where it is built and no sheet reaches
    inside one, so a look that changes the ground under the verbs has to hand
    them their colours here.
    """
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    # The real card's head spaces its four buttons by 4 and this row must too:
    # the mock sitting directly under the baseline is only worth having while
    # any difference between them is a difference the look asked for.
    layout.setSpacing(4)
    for glyph, tip in _VERBS:
        button = QToolButton()
        button.setIcon(icons.icon(glyph, normal, active))
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
