"""Which keys exist and which verb each one calls.

Not what the verbs mean — `app.py` owns that, and this module names five
methods it never looks inside. Rebinding a key must not touch `app.py`;
changing what "forward" reaches must never touch this file.

Bound once, at window construction, because every target is a method on the
window itself and stays valid across every screen swap. A shortcut aimed at a
widget that gets replaced would need rebinding with it, which is why the pairs
that will do that — play/pause on a canvas — are not bound here.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow


def bind_navigation_hotkeys(window: QMainWindow) -> None:
    """Left/Right walk the positions; Up/Down walk the graph; P pins where it is."""
    for key, verb in (
        (Qt.Key.Key_Left, window.go_back),
        (Qt.Key.Key_Right, window.go_forward),
        (Qt.Key.Key_Up, window.go_up),
        (Qt.Key.Key_Down, window.go_down),
        (Qt.Key.Key_P, window.pin_current),
    ):
        shortcut = QShortcut(QKeySequence(key), window)
        # Auto-repeat off: every one of these verbs is a discrete step, and a
        # held key would run the walk to its end faster than the eye follows.
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(verb)
