"""Preferences card: which sections exist and what each is for."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui import metrics, palette
from sieve.gui.primitives import Section, SectionCard
from sieve.gui.view.preferences.minor_visuals import MinorVisuals
from sieve.gui.view.preferences.palettes import Palettes

_WIDTH = 820
# Sized to fit `minor visuals` (the tallest section) at default text size.
_HEIGHT = 545

def _sections() -> tuple[Section, ...]:
    # Function, not module-level: widgets can't exist before QApplication.

    return (
        Section("library", "where projects are kept, and which one opens on start"),
        Section("playback", "how much footage is decoded ahead, and how much is held"),
        Section("chain", "what a new step starts at, and what a run writes out"),
        Section(
            "palette",
            "the colours everything is drawn in, including colour-vision-safe sets",
            Palettes(),
            palette.reset,
        ),
        Section(
            "minor visuals",
            "how round the cards are, and how large each kind of text is",
            MinorVisuals(),
            metrics.reset,
        ),
    )


class Preferences(SectionCard):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "preferences",
            "kept between runs; the empty sections are where the rest will land",
            _sections(),
            _WIDTH,
            _HEIGHT,
            parent,
        )
