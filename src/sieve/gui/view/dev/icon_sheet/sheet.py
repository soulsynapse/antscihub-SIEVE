"""Vendored glyphs grouped by role, with the inks each is drawn in."""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtGui import QColor

from sieve.gui import icons
from sieve.gui.palette import ACCENT, DIM, LINE


class Group(NamedTuple):
    """A handful of glyphs that are in the tree for one reason, and the reason."""

    name: str
    gloss: str
    glyphs: tuple[str, ...]


class Ink(NamedTuple):
    """One column of the sheet: a glyph drawn one way, and what that way is."""

    caption: str
    colour: QColor
    filled: bool = False
    size: int = icons.SIZE


INKS: tuple[Ink, ...] = (
    Ink("rest", DIM),
    Ink("hover", ACCENT),
    Ink("off", LINE),
    Ink("filled", ACCENT, filled=True),
    Ink("at 32", DIM, size=32),
)

# Ungrouped glyphs still appear under _LOOSE.
_ROLES: tuple[Group, ...] = (
    Group(
        "going somewhere",
        "the two directions the frame moves in, and the one a card offers as "
        "*open this*. Reused between the swipe and a card's head on purpose: a "
        "back arrow that meant one thing in the frame and another on a card "
        "would be the same picture asking to be read twice",
        ("arrow-left", "arrow-right"),
    ),
    Group(
        "acting on a card",
        "the verbs a card's head carries, each doing something to the thing "
        "under it rather than moving anywhere. `pin` is the one glyph whose "
        "meaning is a state as well as an action, which is why it is also the "
        "one drawn filled",
        ("arrow-right-left", "pin", "x"),
    ),
    Group(
        "acting on a list",
        "the verb a view's head carries. `plus` acts on the list under the "
        "head rather than on any card in it, which is why it stands beside the "
        "view's title and not in a card's own row of verbs",
        ("plus",),
    ),
    Group(
        "saying what a thing is",
        "glyphs that name rather than act — a kind ahead of a step's title, a "
        "project's folder. Nothing happens when they are pressed, so they are "
        "drawn on labels and not on buttons, and the rest ink is the one they "
        "are really seen in",
        ("folder-open", "sliders-horizontal"),
    ),
)

_LOOSE = Group(
    "not spoken for yet",
    "vendored, and nothing in the tree has said what for. Either the thing that "
    "draws it has not landed, or the group it belongs to is missing a line in "
    "`sheet.py`",
    (),
)


def groups() -> tuple[Group, ...]:
    """Every vendored glyph, once, under the reason it is here."""
    left = list(icons.names())
    out: list[Group] = []
    for role in _ROLES:
        held = tuple(glyph for glyph in role.glyphs if glyph in left)
        if held:
            out.append(role._replace(glyphs=held))
        for glyph in held:
            left.remove(glyph)
    if left:
        out.append(_LOOSE._replace(glyphs=tuple(left)))
    return tuple(out)
