"""The text button, in the four weights of emphasis a screen is allowed.

Lifted from `mockup/paper_primitives.py`, where the whole argument of the set is
one sentence: *one filled button per screen*. Emphasis is a currency and a
filled button spends all of it, so the kinds below are ordered by how much they
take and a view is expected to reach down the list rather than up it — `PRIMARY`
for the single thing the pane is for, `DEFAULT` for the ordinary verbs beside
it, `SUBTLE` for the ones that are only there when you look, `GHOST` for the
dismissal that must not compete with what it is dismissing.

`Card` already carries the verbs that act on what a card *holds*; these are the
verbs that act on a whole pane or a whole box — run the chain, add a step,
cancel out of a sheet — and they are text because those are not four fixed
positions a user learns, but a sentence that differs per screen. An icon-only
button is discoverable when its position is the same on the twentieth card as on
the first, and unreadable when it is not.

The filled button's ink is `PANEL`, and that is derived rather than chosen. Every
palette here commits to an accent that clears 4.5:1 against `panel`
(`palette.py`), so the panel colour laid *on* the accent is legible by the same
guarantee, in a light palette whose accent is dark and in a dark palette whose
accent is bright, without this file knowing which it is in. A white named here
would be right in seven palettes and unreadable in two.

Hover is a step off the fill toward the ink, through `palette.mix`, and never
unconditionally lighter — the same move `panel_hot` is, for the reason given
there: on a light ground the pointer's answer is a step down. So one fraction
serves both, and the button darkens on `paper` and lightens on `slate` with no
branch on `current().dark`.

What is missing is the mockup's fifth kind, danger. The red it wears is not one
of the eight roles, and a ninth is a colour every palette below would have to
answer — including the two chosen so that the only hue in the scheme is one an
accent-blind user can still find, which a red for *destructive* silently breaks.
Until that is decided, a destructive verb is refused the way `card.py` refuses
one: the button is disabled and its tooltip says why, rather than shouting.

The corner is this file's 4 and not `metrics.radius()`. That slider is *card
corners* and stops where `sections.py` stops it — a button is not a card, and a
user squaring off their cards did not ask for square buttons.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb

#: The kinds, most emphasis first. Strings and not an enum, because they are what
#: a caller writes at the call site and `Button("Run", PRIMARY)` reads as the
#: sentence it is; the constants exist so the spelling is checked somewhere.
PRIMARY = "primary"
DEFAULT = "default"
SUBTLE = "subtle"
GHOST = "ghost"

#: How far a hovered fill moves toward the ink, and how far a pressed one moves
#: past that. Two steps of the same move rather than two colours: press has to be
#: visibly more than hover, since a pointer that is already over the button is
#: holding the hover state while it clicks.
#:
#: `HOVER` is public and `_PRESS` is not, which is the difference between a
#: filled *thing* and a button: anything in this tree that is filled with a role
#: answers the pointer by this much — the accent-filled checkbox in `check.py`
#: does — while being pressed and held is something only a button is.
HOVER = 0.14
_PRESS = 0.26

#: How far a hovered edge moves off `LINE`, matching the card's — a bordered
#: button standing beside a card should answer the pointer at the same volume.
_HOVER_EDGE = 0.22

#: How far a disabled ghost's ink is washed back into the panel. The other kinds
#: say *off* with a flat fill and `DIM` text; a ghost has no fill to flatten, so
#: its ink is what carries it, and `DIM` alone is the colour it already rests at.
_OFF_INK = 0.45

#: The box around the label, normal and small, and the corner on it. Small is for
#: a button that sits inside something already dense — a table's foot, a row's
#: own verb — where the normal one would set the height of the thing it is in.
_PAD_X = 12
_PAD_Y = 6
_PAD_X_SMALL = 8
_PAD_Y_SMALL = 3
_RADIUS = 4


class Button(QPushButton):
    """A labelled button in one of the four kinds.

    It knows what it looks like and nothing about what pressing it means, which
    is `clicked` and the caller's — the same split every primitive here makes.
    """

    def __init__(
        self,
        text: str = "",
        kind: str = DEFAULT,
        *,
        small: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("button")
        self._kind = kind
        self._small = small
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dress()
        # Bound methods, never lambdas: PySide6 drops a connection to a bound
        # method when the receiver goes, where a lambda closing over `self` would
        # keep a dead button subscribed to both signals for the life of the run.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def set_kind(self, kind: str) -> None:
        """Change how loud this button is.

        Worth having because emphasis is a property of the *screen* and not of
        the verb: the same "Run" is the filled button on the pipeline pane and an
        ordinary one in a box that is mostly about something else, and a caller
        that had to build a second button to say so would have two widgets where
        there is one thing to press.
        """
        self._kind = kind
        self._dress()

    def _dress(self) -> None:
        """The sheet, in the palette and at the size now in use.

        All of it is a sheet and none of it is painted, which is the difference
        from `card.py`: everything here is a filled box with text in it and a
        corner that is a number, and that is the shape a stylesheet is actually
        good at. The card paints because it measures a rule off a sibling widget
        and clips a meter to its own corner, and neither is expressible; a button
        that painted itself would be paying that cost for nothing.

        Scoped to `#button` rather than to `QPushButton`, for the reason
        `sections.py` gives: this is set on a widget standing inside a card whose
        sheet is on an ancestor, and a bare class rule here would reach every
        button in the pane — including ones of another kind.
        """
        fill, ink, edge = _rest(self._kind)
        hover_fill, hover_ink, hover_edge = _hover(self._kind)
        pad_x = _PAD_X_SMALL if self._small else _PAD_X
        pad_y = _PAD_Y_SMALL if self._small else _PAD_Y
        role = "gloss" if self._small else "name"
        self.setStyleSheet(f"""
            #button {{
                background: {fill};
                color: {rgb(ink)};
                border: 1px solid {edge};
                border-radius: {_RADIUS}px;
                padding: {pad_y}px {pad_x}px;
                font-size: {metrics.pt(role)}pt;
            }}
            #button:hover {{
                background: {hover_fill};
                color: {rgb(hover_ink)};
                border-color: {hover_edge};
            }}
            #button:pressed {{ background: {_pressed(self._kind)}; }}
            #button:focus {{ border-color: {rgb(ACCENT)}; }}
            #button:disabled {{
                background: {_off_fill(self._kind)};
                color: {rgb(_off_ink(self._kind))};
                border-color: {_off_edge(self._kind)};
            }}
        """)


#: What a fill of `transparent` is in a sheet — the one value here that is a word
#: rather than a colour, because a ghost's ground is whatever it is standing on
#: and naming a role for it would paint the panel onto a button sitting on the
#: stack's ground.
_NONE = "transparent"


def _rest(kind: str) -> tuple[str, QColor, str]:
    """Fill, ink and edge at rest. The fill and edge are sheet text so that
    `transparent` is sayable; the ink never is, since there is no such thing as
    unpainted text."""
    if kind == PRIMARY:
        return rgb(ACCENT), PANEL, rgb(ACCENT)
    if kind == SUBTLE:
        # Its own edge in its own fill: a subtle button is a shape and not an
        # outline, and a bordered one at this weight reads as a `DEFAULT` that
        # came out wrong.
        return rgb(PANEL_HOT), TEXT, rgb(PANEL_HOT)
    if kind == GHOST:
        return _NONE, DIM, _NONE
    return rgb(PANEL), TEXT, rgb(LINE)


def _hover(kind: str) -> tuple[str, QColor, str]:
    """The same three under the pointer.

    A ghost is the one kind that gains a fill rather than moving the one it has —
    it has none — and gains its ink with it: `DIM` is what a ghost rests at, and
    a ghost that only took a fill on hover would be answering half.
    """
    if kind == PRIMARY:
        return rgb(mix(ACCENT, TEXT, HOVER)), PANEL, rgb(mix(ACCENT, TEXT, HOVER))
    if kind == SUBTLE:
        step = rgb(mix(PANEL_HOT, TEXT, HOVER))
        return step, TEXT, step
    if kind == GHOST:
        return rgb(PANEL_HOT), TEXT, _NONE
    return rgb(PANEL_HOT), TEXT, rgb(mix(LINE, TEXT, _HOVER_EDGE))


def _pressed(kind: str) -> str:
    """One more step of the hover's own move — see `_PRESS`.

    The three unfilled kinds land on the same colour, because by the time the
    pointer is down they are all showing `PANEL_HOT` and a press that differed
    between them would be a difference in a state nobody is looking at.
    """
    if kind == PRIMARY:
        return rgb(mix(ACCENT, TEXT, _PRESS))
    return rgb(mix(PANEL_HOT, TEXT, _PRESS - HOVER))


def _off_fill(kind: str) -> str:
    """A disabled button is flat: every kind that has a fill wears the same one,
    so *off* looks like one state and not like four."""
    return _NONE if kind == GHOST else rgb(PANEL_HOT)


def _off_ink(kind: str) -> QColor:
    return mix(DIM, PANEL, _OFF_INK) if kind == GHOST else DIM


def _off_edge(kind: str) -> str:
    if kind == GHOST:
        return _NONE
    # `LINE` and not the fill: a disabled button keeps its outline, so the thing
    # that cannot be pressed is still visibly a button and its tooltip is still
    # somewhere to put the pointer.
    return rgb(LINE)
