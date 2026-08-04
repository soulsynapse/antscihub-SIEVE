"""Secret: what the user has configured for appearance, its defaults, and
how a change gets announced.

Not how a value becomes Qt styling — ``gui/style.py`` owns that. Not how
this section is picked or displayed — ``gui/windows/preferences.py`` owns
that. Nothing outside this file mutates ``Appearance`` directly; a setter
here is the only path, so every change goes through the same announcement.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

# The defaults appearance falls back to before anything is overridden.
# These are the exact values gui/style.py hardcoded before preferences
# existed — moving them here didn't change what the app looks like on
# first launch, only where the source of truth is.


@dataclass(frozen=True)
class Appearance:
    background: str = "#1e1f24"
    surface: str = "#26282f"
    border: str = "#33353d"
    text: str = "#e4e4e8"
    text_muted: str = "#8b8d97"
    accent: str = "#5b8def"
    spacing_unit: int = 8
    radius: int = 4
    bar_height: int = 64


_appearance = Appearance()
_subscribers: list[Callable[[], None]] = []


def get_appearance() -> Appearance:
    return _appearance


def set_appearance(**changes: object) -> None:
    global _appearance
    _appearance = replace(_appearance, **changes)
    for callback in _subscribers:
        callback()


def subscribe(callback: Callable[[], None]) -> None:
    """``callback`` fires after every ``set_appearance`` call, including
    ones to fields it doesn't care about — cheap enough (re-applying a
    stylesheet) that a per-field subscription isn't worth the bookkeeping
    yet. Revisit if a subscriber ever does real work."""
    _subscribers.append(callback)
