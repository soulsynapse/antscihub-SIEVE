"""Preferences as a card: the sections there will be, and what each is for.

What a section card *is* — the list left, the one read right, why it is that and
not a column — is `primitives/sections.py`'s, and was this file's until the dev
view needed the same picture. What is left here is the part that is about
preferences: which sections there are, what each is for, and how much room four
rows of a label and a control want.

Most sections are bodiless, and that is the same claim `menu.py` makes with its
greyed entries rather than a different one: a settings screen that grew a
control the day the setting behind it landed would never, at any point, say what
the application is configurable *about*. Written out and empty, it says so from
the start, and each section is a place controls land rather than a place they
have to be argued for. `appearance` is the first to have had something land in
it, and the others stay listed and empty on exactly the same terms as before.

The view holds no preference and reads none. Where a setting is kept is
`sieve/settings.py`'s and what it means is its own module's — the palette a user
picks is written down by `palette.use()`, not by the row that was clicked — and
a view that opened the settings document itself would be making that decision in
a view, which is the same refusal the project list makes about the library it
lists. What is here is where a setting is *reachable*, and nothing else.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Section, SectionCard
from sieve.gui.view.preferences.appearance import Appearance

#: How wide the card is allowed to get. A settings row is a label and a control
#: on one line, and a card that took the window's width would put a full screen
#: of space between the two — the overlay has room to spare, and spending all of
#: it makes the pair harder to read, not easier. Wider than the reading side
#: alone wants, by about what the nav takes: the list is beside the section, not
#: carved out of it. The nav is a fixed column, so every width added past that
#: lands on the reading side, where a row's label and its control are what have
#: to fit on one line.
_WIDTH = 820

#: How tall the card stands, whichever section is open. Sized to the tallest
#: section and not to the current one — why it is fixed at all is the card's,
#: and stated there. That was the longest gloss while every section was empty;
#: it is now `appearance`, which is a list, and the number is what shows enough
#: of that list to read as one rather than as a row with a scrollbar beside it.
_HEIGHT = 430

def _sections() -> tuple[Section, ...]:
    """The sections, each a name, the one line saying what falls under it, and
    the surface it opens — or nothing, for one that is a place rather than a
    thing. Named for what the user is deciding rather than for the module that
    will answer it: a row called `decode` is a row only the person who wrote the
    decoder can find.

    A function and not a module-level tuple, for the reason the dev bench's is
    one: a section with a body has to build a widget, a widget cannot exist
    before the `QApplication` does, and at import that aborts the process rather
    than raising — the one failure a reader cannot debug from a traceback, since
    there is not one.
    """
    return (
        Section("library", "where projects are kept, and which one opens on start"),
        Section("playback", "how much footage is decoded ahead, and how much is held"),
        Section("chain", "what a new step starts at, and what a run writes out"),
        Section(
            "appearance",
            "the palette everything is drawn in, and how large the text is",
            Appearance(),
        ),
    )


class Preferences(SectionCard):
    """What the application is configurable about: sections left, one read right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "preferences",
            "kept between runs; the empty sections are where the rest will land",
            _sections(),
            _WIDTH,
            _HEIGHT,
            parent,
        )
