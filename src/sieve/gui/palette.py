"""Eight colour roles, mutated in place so every holder sees the swap."""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from sieve import settings


class Palette(NamedTuple):
    """A named set of the eight colour roles.

    Constraints on a new palette: a light one is not a dark one inverted — it
    wants a smaller `panel`/`stack_bg` step, and `panel_hot` steps *darker*,
    away from the panel. `scrim` stays dark and translucent even in light
    palettes (a light scrim raises nothing and reads as fog), with lower alpha
    there. `line` must be legible on `panel`. `accent` is the only hue any
    palette commits to.
    """

    name: str
    gloss: str
    dark: bool

    stack_bg: QColor
    panel: QColor
    panel_hot: QColor
    line: QColor
    scrim: QColor
    text: QColor
    dim: QColor
    accent: QColor


def _c(*rgba: int) -> QColor:
    return QColor(*rgba)


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
    # Accents from Okabe & Ito (2008); neutral greys so the accent
    # clears 4.5:1 on luminance alone regardless of colour vision.
    # Two darks because the failures differ: blue is the axis tritanopia
    # degrades, the warm end is what protanopes see least brightly —
    # neither is a fallback for the other.
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

PALETTES: tuple[Palette, ...] = _DARK + _LIGHT
DEFAULT = _DARK[0]
_KEY = "palette"


class _Notifier(QObject):
    changed = Signal()


# prevent GC: a bound Signal does not prevent its owner's collection
_notifier = _Notifier()
CHANGED = _notifier.changed

STACK_BG = QColor()
PANEL = QColor()
PANEL_HOT = QColor()
LINE = QColor()
SCRIM = QColor()
TEXT = QColor()
DIM = QColor()
ACCENT = QColor()

_current: Palette | None = None


def current() -> Palette:
    """The palette in use, for whoever is drawing the choice between them."""
    assert _current is not None
    return _current


def use(palette: Palette) -> None:
    """Swap to palette; mutates live QColors in place so holders see the change.

    Written down *above* the no-change return, deliberately: the document and
    the screen can disagree (an unreadable settings file leaves the run at the
    default with nothing stored), and re-picking the palette on screen is the
    user insisting on it.
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
    """Revert to default and forget the stored choice."""
    use(DEFAULT)
    settings.forget(_KEY)


def rgb(color: QColor) -> str:
    """A colour as a stylesheet's `rgb(...)`, since Qt's own repr is not one."""
    return f"rgb({color.red()},{color.green()},{color.blue()})"


def mix(start: QColor, end: QColor, fraction: float) -> QColor:
    """Lerp between two roles; do not cache — roles mutate on palette swap."""
    return QColor(
        round(start.red() + (end.red() - start.red()) * fraction),
        round(start.green() + (end.green() - start.green()) * fraction),
        round(start.blue() + (end.blue() - start.blue()) * fraction),
    )


def _remembered() -> Palette:
    """Stored palette by name, falling back to DEFAULT on mismatch."""
    name = settings.stored(_KEY)
    for palette in PALETTES:
        if palette.name == name:
            return palette
    return DEFAULT


use(_remembered())
