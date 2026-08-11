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
have to be argued for. `palette` and `minor visuals` are the two that have had
something land in them, and the others stay listed and empty on exactly the same
terms as before.

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
from sieve.gui.view.preferences.minor_visuals import MinorVisuals
from sieve.gui.view.preferences.palettes import Palettes

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
#: and stated there. That was the longest gloss while every section was empty,
#: then `palette`, which is a list and wanted enough of it to read as one rather
#: than as a row with a scrollbar beside it. It is now `minor visuals`, which is
#: a countable five rows rather than a catalogue: the number is what stands all
#: five at the default text size, so the section that sets the sizes is not the
#: one section a user has to scroll to finish reading. It scrolls anyway at the
#: sizes it can be set to, which is the point of it scrolling.
_HEIGHT = 545

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
            "palette",
            "the colours everything is drawn in, including colour-vision-safe sets",
            Palettes(),
        ),
        # `text` was the section this one is now, and it is folded in rather
        # than left standing beside it. It was split off `palette` to keep a
        # promise the card had made about text size, and this section keeps that
        # promise with controls under it — an empty `text` left below would be
        # the card offering the same setting twice, once where it works and once
        # where it says nothing is here yet, which is worse than either.
        #
        # The name is the user's word and not the tree's. What falls under it is
        # a corner radius and four point sizes: small, unrelated to each other,
        # and none of them a decision about what the application *does*. There
        # is no module these are the settings of — they reach `primitives/` and
        # every view at once through `gui/metrics.py` — so naming the section
        # for one would name it after the wrong half.
        Section(
            "minor visuals",
            "how round the cards are, and how large each kind of text is",
            MinorVisuals(),
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
