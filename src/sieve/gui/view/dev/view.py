"""The dev bench as a card: the sections there are, and what each is for.

Which sections exist and in what order is the whole of this file. Each one's
contents are its own folder's, so a section is added here by naming it and
importing the surface beside it, and a section is worked on without this file
being opened.

The order is how often a thing is reached for, not how finished it is: the
bench is opened with a key, and a key means the first section is where the user
lands. Sections with nothing under them yet are listed anyway, for the reason
preferences lists its four — a bench that grew an entry the day the tool behind
it worked would never say what there is to look at.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Section, SectionCard
from sieve.gui.view.dev.card_mockups import CardMockups
from sieve.gui.view.dev.icon_sheet import IconSheet

#: How wide and tall the bench stands. Bigger than preferences and for the
#: opposite reason: preferences holds rows of a label and a control, where extra
#: width is distance between the pair, and the bench holds surfaces drawn at the
#: size they will really be seen at — a gallery of cards squeezed into a settings
#: card would be a gallery of the wrong cards.
_WIDTH = 940
_HEIGHT = 560

def _sections() -> tuple[Section, ...]:
    """The sections, each a name, the one line saying what falls under it, and
    the surface it opens — or nothing, for one that is a place rather than a
    thing.

    A function and not a module-level tuple, because a section with a body has
    to build a widget and a widget cannot exist before the `QApplication` does.
    Written as a constant it would run at import, and `import sieve.gui.view.dev`
    would abort the process rather than raise — which is the one failure mode a
    reader cannot debug from a traceback, since there is not one.
    """
    return (
        Section(
            "card mock ups",
            "the shapes a card could take, drawn beside each other",
            CardMockups(),
        ),
        Section("palette", "every colour in `palette.py`, on the ground it is used on"),
        Section(
            "icons",
            "every vendored lucide glyph, grouped by what it is here to say and "
            "drawn in each ink a widget gives it",
            IconSheet(),
        ),
        Section(
            "frame", "the panes and swipe positions, and which view is standing where"
        ),
    )


class Dev(SectionCard):
    """The bench: what there is to look at while building, one section at a time."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "dev",
            "not part of the product — the tree looked at by whoever is editing it",
            _sections(),
            _WIDTH,
            _HEIGHT,
            parent,
        )
