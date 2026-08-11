"""Preferences as a card: the sections there will be, and what each is for.

What a section card *is* — the list left, the one read right, why it is that and
not a column — is `primitives/sections.py`'s, and was this file's until the dev
view needed the same picture. What is left here is the part that is about
preferences: which sections there are, what each is for, and how much room four
rows of a label and a control want.

Every section is bodiless, and that is the same claim `menu.py` makes with its
greyed entries rather than a different one: a settings screen that grew a
control the day the setting behind it landed would never, at any point, say what
the application is configurable *about*. Written out and empty, it says so from
the start, and each section is a place controls land rather than a place they
have to be argued for.

The view holds no preference and reads none. There is nowhere to keep one yet,
no settings document and no place one would be written, and a view that picked
somewhere would be that decision, made in a view — which is the same refusal the
project list makes about the library it lists.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Section, SectionCard

#: How wide the card is allowed to get. A settings row is a label and a control
#: on one line, and a card that took the window's width would put a full screen
#: of space between the two — the overlay has room to spare, and spending all of
#: it makes the pair harder to read, not easier. Wider than the reading side
#: alone wants, by about what the nav takes: the list is beside the section, not
#: carved out of it. The nav is a fixed column, so every width added past that
#: lands on the reading side, where a row's label and its control are what have
#: to fit on one line.
_WIDTH = 820

#: How tall the card stands, whichever section is open. Sized to the longest
#: gloss and not to the current one — why it is fixed at all is the card's, and
#: stated there.
_HEIGHT = 320

#: The sections, each a name and the one line saying what falls under it. Named
#: for what the user is deciding rather than for the module that will answer it:
#: a row called `decode` is a row only the person who wrote the decoder can find.
_SECTIONS: tuple[Section, ...] = (
    Section("library", "where projects are kept, and which one opens on start"),
    Section("playback", "how much footage is decoded ahead, and how much is held"),
    Section("chain", "what a new step starts at, and what a run writes out"),
    Section("appearance", "the palette, and how large the text is drawn"),
)


class Preferences(SectionCard):
    """What the application is configurable about: sections left, one read right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "preferences",
            "nothing here is settable yet — these are the sections",
            _SECTIONS,
            _WIDTH,
            _HEIGHT,
            parent,
        )
