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


@dataclass(frozen=True)
class Appearance:
    background: str = "#f5f5f7"
    surface: str = "#ffffff"
    border: str = "#d8d8dc"
    text: str = "#1e1f24"
    text_muted: str = "#6b6d76"
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
