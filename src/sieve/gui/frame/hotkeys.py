"""Frame-level key bindings: eager shortcuts and yielded keys.

No autorepeat on either table — a held arrow would walk at the keyboard's
repeat rate instead of re-aiming the running swipe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

_KEYS: tuple[tuple[str, str], ...] = (("Ctrl+R", "reload"),)

#: Yielded (not eager) so a focused text field still gets its own space bar.
_YIELDED_KEYS: tuple[tuple[str, str], ...] = (
    ("Left", "swipe_back"),
    ("Right", "swipe_forward"),
    ("Space", "play_pause"),
    (",", "step_back"),
    (".", "step_forward"),
    ("F", "show_whole_frame"),
)


@dataclass
class Hotkeys:
    """The frame's bound keys and their suspension state."""

    window: MainWindow
    shortcuts: list[QShortcut] = field(default_factory=list)
    suspended: bool = False


def bind_hotkeys(window: MainWindow) -> Hotkeys:
    """Bind `_KEYS` as shortcuts; `_YIELDED_KEYS` are read by `answer_key`."""
    hotkeys = Hotkeys(window)
    for key, verb in _KEYS:
        shortcut = QShortcut(QKeySequence(key), window)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(getattr(window, verb))
        hotkeys.shortcuts.append(shortcut)
    return hotkeys


def answer_key(hotkeys: Hotkeys, event: QKeyEvent) -> bool:
    """Try the yielded-key table; True if the frame acted."""
    if hotkeys.suspended or event.isAutoRepeat():
        return False
    pressed = QKeySequence(event.keyCombination())
    for key, verb in _YIELDED_KEYS:
        if pressed == QKeySequence(key):
            getattr(hotkeys.window, verb)()
            return True
    return False


def suspend_hotkeys(hotkeys: Hotkeys, suspended: bool) -> None:
    """Disable both tables while a cover stands over the panes.

    Covers yielded keys too — disabling shortcuts alone still lets unhandled
    keys walk up the parent chain to `answer_key`.
    """
    hotkeys.suspended = suspended
    for shortcut in hotkeys.shortcuts:
        shortcut.setEnabled(not suspended)
