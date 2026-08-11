"""The colours every view draws with, and the palettes they are drawn from.

Held above `frame` because the frame is not the only thing that reads them: the
panes' contents paint cards, plots and footage against the same values,
and a palette owned by the frame would be imported back up out of it by
everything the frame contains.

There are eight colours and they are *roles*, not preferences — a card asks for
the panel fill and never for a particular grey, so a view is written once and a
palette is what it comes out looking like. `Palette` is one full set of the
eight, `PALETTES` is every set on offer, and the module constants are whichever
set is currently in use.

Those constants are mutated in place rather than rebound, and that is the whole
of how a change reaches the tree. Every consumer writes `from sieve.gui.palette
import PANEL`, which binds the object at import; rebinding the name here would
change nothing anywhere else, and the alternative — rewriting every call site to
go through the module — would put a dotted lookup in the paint path of the one
loop this project promises not to stall. A `QColor` is mutable, so the object a
view is already holding becomes the new colour and a `paintEvent` needs nothing
said to it at all.

What that does not reach is a stylesheet, which is a string built once from the
values as they were. So `CHANGED` is emitted after the swap, and a widget that
dressed itself with one re-runs its own sheet function on hearing it. The icons
are the third case: a pixmap is drawn at a colour and cached on that colour's
`rgba`, so a mutated colour is a cache miss rather than a stale hit — but a
`QIcon` already handed to a button is a drawing that has to be made again, which
is the holder's to do in the same slot.

`current()` is what a chooser reads to mark the palette in use; nothing else
should need it, since asking *which* palette is on is a different question from
asking what colour to draw with, and only one of the two is a view's business.

The choice outlives the process, and it is `use()` that writes it down rather
than whatever called `use()`. A chooser that saved its own click would be right
only while it was the only way to change one — the same argument the palette
section makes for marking its rows off `CHANGED` instead of off the click — and
a second caller, a hotkey or a system-theme follower, would silently not stick.
Passing through here is what makes a palette change persistent, so there is one
place that has to be reached and no way to change the palette that skips it.
"""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from sieve import settings


class Palette(NamedTuple):
    """One complete set of the eight roles, under a name and its argument.

    Every field is a role rather than a colour: what changes between palettes is
    the eight values, never which eight there are. A palette that left one out
    would be one the tree draws with a hole in it, and a ninth added here is a
    role every palette below has to answer.

    `gloss` is what the choice is actually between. A list of names is a list of
    moods; the line under each says what it is *for* — long sessions, projected
    footage, a figure being screenshotted into a paper, an accent that survives
    a colour-vision deficiency — and that is the half worth reading.

    `dark` is not derivable from the values without picking a threshold, and a
    threshold is a decision better made once by whoever chose the colours than
    inferred at every call site. It is what sorts the list into the two groups
    the user is really choosing between first.
    """

    name: str
    gloss: str
    dark: bool

    #: The ground the panes leave uncovered — the menu bar's strip, splitter
    #: seams. Never a panel: it is what a panel is seen *against*.
    stack_bg: QColor

    #: A pane's own fill, and the lighter one a control wears against it. In a
    #: light palette `panel_hot` is the darker of the two, since the move that
    #: means "the pointer is here" is a step away from the panel and not
    #: unconditionally upward.
    panel: QColor
    panel_hot: QColor

    #: Hairlines and dividers. Legible on `panel`; against `stack_bg` it is what
    #: a seam is made of rather than a line drawn on one.
    line: QColor

    #: What a view standing over the panes lays over them. Dark and translucent
    #: in every palette, light ones included: the work is not being replaced,
    #: only stood in front of, and dimming is what says so. A light scrim over
    #: light panes would raise nothing and read as fog. Alpha is lower in the
    #: light palettes because the same veil over a bright ground hides more.
    scrim: QColor

    text: QColor
    dim: QColor

    #: The one colour that means *this is what you are acting on*: a hovered
    #: seam, a selected crop, a detected block. It is the only hue any palette
    #: here commits to, which is why they differ by it more than by their greys.
    accent: QColor


def _c(*rgba: int) -> QColor:
    """A colour from its channels. Written out rather than as a hex string so an
    alpha is a fourth number instead of a convention about digit count."""
    return QColor(*rgba)


#: The dark palettes. Dark is the default and the longer list because the work is
#: footage: a bright surround around a video pane is what the eye adapts to, and
#: everything shown in the frame is then judged against the wrong white.
_DARK: tuple[Palette, ...] = (
    Palette(
        "slate",
        "neutral cool grey, teal accent — the default",
        True,
        stack_bg=_c(24, 26, 30),
        panel=_c(31, 33, 38),
        panel_hot=_c(38, 41, 47),
        line=_c(55, 58, 66),
        scrim=_c(12, 13, 16, 140),
        text=_c(230, 231, 235),
        dim=_c(139, 142, 152),
        accent=_c(94, 200, 180),
    ),
    Palette(
        "graphite",
        "no hue in the greys, so only an overlay carries one",
        True,
        stack_bg=_c(26, 26, 26),
        panel=_c(33, 33, 33),
        panel_hot=_c(42, 42, 42),
        line=_c(61, 61, 61),
        scrim=_c(13, 13, 13, 140),
        text=_c(233, 233, 233),
        dim=_c(146, 146, 146),
        accent=_c(214, 158, 74),
    ),
    Palette(
        "ink",
        "blue-black, the highest contrast here — a bright room",
        True,
        stack_bg=_c(16, 19, 27),
        panel=_c(22, 26, 36),
        panel_hot=_c(31, 37, 49),
        line=_c(48, 56, 73),
        scrim=_c(8, 10, 15, 145),
        text=_c(234, 238, 246),
        dim=_c(134, 145, 165),
        accent=_c(96, 160, 240),
    ),
    Palette(
        "basalt",
        "warm-neutral greys — least harsh over a long session",
        True,
        stack_bg=_c(28, 26, 24),
        panel=_c(36, 33, 31),
        panel_hot=_c(45, 41, 38),
        line=_c(64, 59, 54),
        scrim=_c(15, 14, 12, 140),
        text=_c(235, 231, 226),
        dim=_c(154, 146, 136),
        accent=_c(209, 138, 86),
    ),
    Palette(
        "abyss",
        "deep blue-green, low throughout — a darkened room",
        True,
        stack_bg=_c(17, 26, 30),
        panel=_c(23, 34, 39),
        panel_hot=_c(30, 44, 50),
        line=_c(48, 68, 76),
        scrim=_c(8, 14, 17, 142),
        text=_c(226, 236, 239),
        dim=_c(130, 152, 159),
        accent=_c(92, 196, 214),
    ),
    # The colour-vision-safe pair, and what that can and cannot mean here. The
    # accents are Okabe & Ito's set (Okabe and Ito, *Color Universal Design*,
    # 2008) — eight hues chosen to stay mutually distinct under protanopia,
    # deuteranopia and tritanopia, and the set most reproducible work in the
    # figure-drawing literature has settled on.
    #
    # But that set solves a problem this module does not have. Okabe–Ito is
    # designed for *categorical* colour, where a reader must tell series apart
    # by hue; a palette here commits to exactly one hue, against greys. So what
    # makes these two safe is not the hue at all — it is that the greys carry no
    # hue to be confused with the accent, and that the accent clears 4.5:1
    # against `panel` on luminance alone, so a user who sees none of its colour
    # still sees the selection. Borrowing the hue is what makes them *also* the
    # right pair to sample a plot's series colours out of when the plotting
    # views land, which is the reason to take the accents from a categorical set
    # rather than tune two more one-offs.
    #
    # Two darks and not one because Okabe–Ito's blue and its warm end fail for
    # different people: the blues are the axis tritanopia degrades, the warm end
    # is the one protanopes see least brightly. Neither is a fallback for the
    # other, so both are on offer and the gloss says which is which.
    Palette(
        "okabe-ito",
        "colour-vision safe: neutral grey, Okabe–Ito sky blue",
        True,
        stack_bg=_c(25, 25, 25),
        panel=_c(32, 32, 32),
        panel_hot=_c(42, 42, 42),
        line=_c(70, 70, 70),
        scrim=_c(12, 12, 12, 142),
        text=_c(240, 240, 240),
        dim=_c(160, 160, 160),
        accent=_c(86, 180, 233),
    ),
    Palette(
        "okabe-ito warm",
        "colour-vision safe: the same greys, orange — no blue to lose",
        True,
        stack_bg=_c(25, 25, 25),
        panel=_c(32, 32, 32),
        panel_hot=_c(42, 42, 42),
        line=_c(70, 70, 70),
        scrim=_c(12, 12, 12, 142),
        text=_c(240, 240, 240),
        dim=_c(160, 160, 160),
        accent=_c(230, 159, 0),
    ),
)

#: The light palettes. Not a dark one inverted: a light surface wants a smaller
#: step between `panel` and `stack_bg` than a dark one does, because the same
#: difference in luminance reads as a bigger difference the brighter the ground.
#: They exist for the two cases dark does not serve — a screen under room lights
#: or daylight, and a pane about to be screenshotted into a figure whose journal
#: prints on white.
_LIGHT: tuple[Palette, ...] = (
    Palette(
        "paper",
        "warm off-white, deep teal — like a printed figure",
        False,
        stack_bg=_c(226, 222, 214),
        panel=_c(247, 245, 240),
        panel_hot=_c(237, 234, 227),
        line=_c(205, 200, 190),
        scrim=_c(40, 36, 30, 80),
        text=_c(32, 31, 28),
        dim=_c(108, 104, 96),
        accent=_c(20, 122, 110),
    ),
    Palette(
        "lab",
        "cool neutral white — the least colour decision here",
        False,
        stack_bg=_c(222, 225, 229),
        panel=_c(250, 251, 252),
        panel_hot=_c(240, 242, 245),
        line=_c(202, 207, 214),
        scrim=_c(24, 28, 34, 80),
        text=_c(26, 30, 36),
        dim=_c(104, 112, 124),
        accent=_c(30, 102, 190),
    ),
    Palette(
        "parchment",
        "cream and warm ink — the least blue light here",
        False,
        stack_bg=_c(231, 223, 208),
        panel=_c(250, 246, 237),
        panel_hot=_c(242, 236, 224),
        line=_c(212, 203, 186),
        scrim=_c(46, 38, 26, 80),
        text=_c(42, 36, 27),
        dim=_c(122, 112, 95),
        accent=_c(170, 84, 32),
    ),
    Palette(
        "mist",
        "cool blue-grey, indigo accent — quieter than `lab`",
        False,
        stack_bg=_c(214, 220, 228),
        panel=_c(246, 249, 252),
        panel_hot=_c(234, 239, 245),
        line=_c(196, 205, 216),
        scrim=_c(20, 28, 40, 80),
        text=_c(24, 32, 44),
        dim=_c(100, 111, 128),
        accent=_c(62, 78, 168),
    ),
    # The light half of the pair above, and the accent is Okabe–Ito's blue
    # rather than its sky blue: the sky blue is what clears 4.5:1 against a dark
    # panel, and the same hue against a near-white one is a step of almost
    # nothing. Which end of a hue reads as the accent depends on which ground it
    # is on, which is the reason this list is not the dark list inverted.
    Palette(
        "okabe-ito light",
        "colour-vision safe on white — for a figure or a bright room",
        False,
        stack_bg=_c(224, 224, 224),
        panel=_c(252, 252, 252),
        panel_hot=_c(240, 240, 240),
        line=_c(184, 184, 184),
        scrim=_c(20, 20, 20, 80),
        text=_c(24, 24, 24),
        dim=_c(96, 96, 96),
        accent=_c(0, 114, 178),
    ),
)

#: Every palette on offer, dark first. One sequence rather than two exported
#: lists, so a caller that wants the split makes it from `dark` and a caller that
#: only wants "all of them, in order" does not have to concatenate anything.
PALETTES: tuple[Palette, ...] = _DARK + _LIGHT

#: What the application comes up in when nothing has been chosen. `slate`
#: because it is the palette the tree was drawn against, so the default is the
#: one every screenshot and every docstring's colour claim already describes.
DEFAULT = _DARK[0]

#: What the choice is called in the settings document. The *name* is stored and
#: not the eight colours: a palette is a set of decisions this module is allowed
#: to revise — a grey lifted, an accent retuned — and a document holding the
#: values would pin a user to whichever version of `slate` they first launched.
#: A name that no longer matches anything resolves to the default, which is the
#: behaviour a renamed or retired palette should have.
_KEY = "palette"


class _Notifier(QObject):
    """Carrier for the one signal. A `Signal` has to live on a `QObject`, and a
    module is not one."""

    changed = Signal()


#: Held so it is not collected out from under the signal — a bound `Signal`
#: does not keep its owner alive.
_notifier = _Notifier()

#: The palette in use has been swapped. Whoever built a stylesheet out of these
#: values, or handed a `QIcon` to a button, has to make it again; whoever paints
#: in a `paintEvent` is already holding the new colours and needs only a repaint.
CHANGED = _notifier.changed

# The live colours. Empty here and filled by the `use()` at the bottom of the
# module: two places stating slate's greys is one place for them to disagree.
STACK_BG = QColor()
PANEL = QColor()
PANEL_HOT = QColor()
LINE = QColor()
SCRIM = QColor()
TEXT = QColor()
DIM = QColor()
ACCENT = QColor()

#: `None` only during this module's own import, between the colours being
#: declared and the `use()` at the foot filling them. Nothing outside can
#: observe it: an importer holds the module only after that line has run.
_current: Palette | None = None


def current() -> Palette:
    """The palette in use, for whoever is drawing the choice between them."""
    assert _current is not None
    return _current


def use(palette: Palette) -> None:
    """Draw everything in `palette` from here on, and in it again next run.

    Each live colour is assigned into rather than replaced, because that object
    is what every view is already holding — see the module docstring. Asking for
    the palette already in use redraws nothing rather than emitting: `CHANGED`
    costs a stylesheet rebuild and an icon redraw everywhere in the tree, and a
    chooser that re-picks the current row on every arrow key would pay it each
    time.

    It is still written down in that case, above the early return and not below
    it. What the document holds and what the process is drawing in can differ —
    an unreadable settings file leaves the run at the default with nothing
    stored — and asking for the palette already on screen is exactly the gesture
    a user makes to insist on it.
    """
    global _current
    settings.remember(_KEY, palette.name)
    if palette is _current:
        return
    _current = palette
    for live, chosen in (
        (STACK_BG, palette.stack_bg),
        (PANEL, palette.panel),
        (PANEL_HOT, palette.panel_hot),
        (LINE, palette.line),
        (SCRIM, palette.scrim),
        (TEXT, palette.text),
        (DIM, palette.dim),
        (ACCENT, palette.accent),
    ):
        live.setRgba(chosen.rgba())
    CHANGED.emit()


def reset() -> None:
    """Draw everything in the default palette again, and remember no choice.

    Applied first and forgotten second, which is the only order that works:
    `use()` writes down the palette it is handed, so a key cleared before the
    call would be written straight back by it. What is left is the state a first
    run is in, and that is the reason for forgetting rather than storing
    `DEFAULT.name` — which palette is the default is a decision this module is
    allowed to revise, on the same grounds `_KEY` gives for storing a name
    rather than eight colours, and a document naming today's answer is a user
    pinned to it for every run after.
    """
    use(DEFAULT)
    settings.forget(_KEY)


def rgb(color: QColor) -> str:
    """A colour as a stylesheet's `rgb(...)`, since Qt's own repr is not one."""
    return f"rgb({color.red()},{color.green()},{color.blue()})"


def mix(start: QColor, end: QColor, fraction: float) -> QColor:
    """A colour a fraction of the way from one role to another.

    Here rather than in whichever widget wanted it first, because more than one
    does and the states they want it for are the same state: a hovered card's
    edge and a hovered button's fill are both *a step off the role it rests at,
    toward the ink*. Taken as a step between two roles rather than as a ninth
    and tenth colour, so every palette keeps answering eight questions and a
    hover is not a decision each of them has to make again.

    Whoever calls it calls it at the moment of drawing or of building a sheet,
    and never keeps what comes back. The roles are mutated in place when the
    palette changes, and a colour mixed off them and held would be the one thing
    on screen still wearing the old greys.
    """
    return QColor(
        round(start.red() + (end.red() - start.red()) * fraction),
        round(start.green() + (end.green() - start.green()) * fraction),
        round(start.blue() + (end.blue() - start.blue()) * fraction),
    )


def _remembered() -> Palette:
    """The palette last chosen, if it is still one of the palettes on offer.

    Matched by name against `PALETTES` rather than trusted: the document is
    written by a version of this module that may not be the one reading it, and
    is a file a user is invited to edit. Anything that does not name a palette
    here — a retired one, a typo, a number — comes up as the default, which is
    what a first run does and needs no other handling.
    """
    name = settings.stored(_KEY)
    for palette in PALETTES:
        if palette.name == name:
            return palette
    return DEFAULT


# At import, because the colours are what everything below this module is built
# out of: a window that came up in the default and was re-dressed once the
# settings were read would show the wrong palette for as long as it took, which
# is a flash of the wrong application on every launch. Reading the document here
# is the one disk touch on the way up, and it is a few hundred bytes.
use(_remembered())
