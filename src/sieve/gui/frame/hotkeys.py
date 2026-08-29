"""Frame-level key bindings: eager shortcuts and yielded keys.

`_KEYS` are QShortcuts and fire before the focused widget — only keys nothing
else wants belong there. `_YIELDED_KEYS` are handled in keyPressEvent after
the focus chain declines. No autorepeat on either table: the swipe re-aims a
running slide, so a held arrow would walk at the keyboard's repeat rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

_KEYS: tuple[tuple[str, str], ...] = (("Ctrl+R", "reload"),)

#: Answered only if nothing nearer the user wanted the key.
#:
#: The transport is on Space and the comma/period pair because ADR-0003 spent
#: the arrows: ← and → walk the swipe track, and ↑/↓ belong to whatever
#: selection the position in view owns. Yielded rather than eager, so a text
#: field still gets its own space bar.
_YIELDED_KEYS: tuple[tuple[str, str], ...] = (
    ("Left", "swipe_back"),
    ("Right", "swipe_forward"),
    ("Space", "play_pause"),
    (",", "step_back"),
    (".", "step_forward"),
    # The whole frame under the crop, which is where a crop gets drawn. A key
    # and not a button because there is nowhere to put a button: the bottom
    # pane is the transport's and this is about the canvas, and a 96-pixel
    # subpane over the left pane for one toggle would be the wrong trade.
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

    The flag covers yielded keys too: an unhandled key walks up the parent
    chain, so disabling the shortcuts alone would still let `answer_key` act.
    """
    hotkeys.suspended = suspended
    for shortcut in hotkeys.shortcuts:
        shortcut.setEnabled(not suspended)
