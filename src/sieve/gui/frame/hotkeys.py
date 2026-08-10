"""The keys the window answers, and never what answering them does.

One table, read top to bottom, so what a key is bound to is a fact about the
frame that can be checked by reading a list — the alternative is a `QShortcut`
created wherever the verb happens to live, and then no file can say what the
keyboard does. The verbs themselves are the window's, named here only as
strings: this file decides what a key means and nothing about how the frame
carries it out, which is the same division `menu.py` makes for the bar.

A binding is written only for something the frame can already do. The menu bar
shows disabled entries for what has not landed because a menu is a picture of
the application's shape; a key is not — a bound key that does nothing is
indistinguishable from a key that is broken, and there is nothing greyed out to
look at.

Shortcuts are the window's, not the application's, so they act only while it
holds focus, and none of them repeat: the swipe re-aims a running slide at each
keystroke, so an autorepeating arrow would walk the track at the keyboard's
repeat rate rather than at the user's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence, QShortcut

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

#: Each key sequence and the method name on the window that answers it.
#:
#: ← and → are the swipe's, and are spent on it: it is the one thing in the
#: frame that runs on a line, so the two keys that mean *along a line* say
#: exactly one thing wherever the user is standing. ↑ and ↓ are deliberately
#: not bound — they mean the next row of whatever holds focus, and a view that
#: has rows answers them itself; bound here they would fire for the position in
#: front as easily as for the one the user is looking at.
_KEYS: tuple[tuple[str, str], ...] = (
    ("Left", "swipe_back"),
    ("Right", "swipe_forward"),
)


def bind_hotkeys(window: MainWindow) -> list[QShortcut]:
    """Bind every key to the window that carries it, and hand them back.

    Returned rather than dropped so a caller holds them: a `QShortcut` is kept
    alive by its parent, which is the window here, and the list is what lets a
    later frame take one back without hunting through the window's children.
    """
    shortcuts = []
    for key, verb in _KEYS:
        shortcut = QShortcut(QKeySequence(key), window)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(getattr(window, verb))
        shortcuts.append(shortcut)
    return shortcuts
