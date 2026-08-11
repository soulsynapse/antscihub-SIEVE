"""What is vendored, what each glyph was vendored to say, and the inks it wears.

Two lists, and which is authoritative differs between them on purpose. What
exists is the folder's — `icons.names()` — because a glyph is a file and a
second list of the files is a second answer to a question with one. What a glyph
is *for* is written here, because a filename says what a picture is of and
nothing says why this tree has it: `arrow-right-left` is two arrows, and that it
means *swap the tool on this card* is a fact about the card and not about the
picture.

So the roles below are a map over the folder rather than a copy of it. A name
listed here with no file behind it simply does not appear — the file is what can
be drawn — and a file no role claims lands in the last group, which is what
keeps a glyph vendored this afternoon from being invisible on a bench whose
whole job is to show what is vendored.

The grouping is by what the glyph was brought in to say and not by what it looks
like, which is the split that survives reuse: `arrow-right` leads a card's *open*
and also carries the swipe forward, and a sheet grouped by shape would file it
under *arrows* and tell a reader nothing they could not see. A glyph belongs to
one group — the sheet claims to show every vendored glyph, and one drawn twice
makes that claim ambiguous — so a reused glyph is filed under what it was
vendored for and its group says so.
"""

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
    """One column of the sheet: a glyph drawn one way, and what that way is.

    `caption` is what the column is called on screen rather than the Qt mode's
    name — the sheet is read while deciding whether a state is legible, and
    `QIcon.Mode.Active` is the answer to a different question than *what does it
    look like under the pointer*.
    """

    caption: str
    colour: QColor
    filled: bool = False
    size: int = icons.SIZE


#: The four ways a glyph is ever drawn, plus the same drawing at double size.
#:
#: The first three are `icon()`'s own defaults, in its own order, drawn as three
#: cells rather than as one hoverable button: a button shows one mode at a time
#: and the question the sheet answers — is the disabled ink still a shape, is the
#: hover a change or a flicker — is a comparison. The live button is drawn beside
#: them anyway, since a static swatch cannot show that the modes actually switch.
#:
#: `filled` is fourth because it is a real state and not a variation: the pinned
#: card draws its ◆ that way. It is shown for every glyph and not only for the
#: one that uses it, because what it does to a two-path outline is the thing
#: worth seeing before a second glyph is drawn that way.
#:
#: The last is the same rest ink at 32, and it is on the sheet because the stroke
#: width is calibrated for `icons.SIZE` and nothing else. A glyph that reads at
#: 16 can be a fat scribble at 32, and this is the column that says so before a
#: pane draws one large.
INKS: tuple[Ink, ...] = (
    Ink("rest", DIM),
    Ink("hover", ACCENT),
    Ink("off", LINE),
    Ink("filled", ACCENT, filled=True),
    Ink("at 32", DIM, size=32),
)

#: What each vendored glyph is here to say, in the order the groups read down
#: the sheet: the ones that move you, then the ones that act, then the ones that
#: only name something. A glyph is added to whichever group holds its reason —
#: and a glyph added to none of them still appears, under `_LOOSE`.
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
        "saying what a thing is",
        "glyphs that name rather than act — a kind ahead of a step's title, a "
        "project's folder. Nothing happens when they are pressed, so they are "
        "drawn on labels and not on buttons, and the rest ink is the one they "
        "are really seen in",
        ("folder-open", "sliders-horizontal"),
    ),
)

#: Where a vendored glyph with no role above lands. Not an error and not a
#: silence: a glyph is usually vendored a commit before the thing that draws it,
#: and this group is what the sheet says in between.
_LOOSE = Group(
    "not spoken for yet",
    "vendored, and nothing in the tree has said what for. Either the thing that "
    "draws it has not landed, or the group it belongs to is missing a line in "
    "`sheet.py`",
    (),
)


def groups() -> tuple[Group, ...]:
    """Every vendored glyph, once, under the reason it is here.

    Built from the folder outward rather than from `_ROLES` outward, so the
    sheet's claim — this is all of them — is one the folder makes and not one
    this file asserts.
    """
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
