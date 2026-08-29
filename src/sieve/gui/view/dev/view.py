"""Dev bench: section catalogue for internal tools."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Section, SectionCard
from sieve.gui.view.dev.card_mockups import CardMockups
from sieve.gui.view.dev.icon_grid import IconGrid
from sieve.gui.view.dev.icon_sheet import IconSheet

_WIDTH = 940
_HEIGHT = 560

def _sections() -> tuple[Section, ...]:
    # Function, not module constant — widgets can't exist before QApplication.
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
            "all icons",
            "the same set with nothing said about it — every glyph at one size, "
            "wrapped, for finding out what is in here",
            IconGrid(),
        ),
        Section(
            "frame", "the panes and swipe positions, and which view is standing where"
        ),
    )


class Dev(SectionCard):
    """Dev bench shown as a sectioned card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "dev",
            "not part of the product — the tree looked at by whoever is editing it",
            _sections(),
            _WIDTH,
            _HEIGHT,
            parent,
        )
