"""Which keys exist and which verb each one calls.

Not what the verbs mean — `app.py` owns that, and this module names seven
methods it never looks inside. Rebinding a key must not touch `app.py`;
changing what "forward" reaches must never touch this file.

Bound once, at window construction, because every target is a method on the
window itself and stays valid across every screen swap. A shortcut aimed at a
widget that gets replaced would need rebinding with it, which is why the pairs
that will do that — play/pause on a canvas — are not bound here.

**Enter and esc are switched rather than bound and left.** They belong to the
add box and to nothing else, and a window shortcut is matched ahead of the
widget holding focus — so a Return bound whether or not a box is open would be
swallowed before it reached the spin box it was typed into, which is where a
committed edit lands (`param_form.py`). Binding them only while a box stands in
the chain would make the binding stateful; the switch below keeps the binding
where the rest of them are and leaves the state with the window, which is the
only thing that knows whether a box is open.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow


def bind_navigation_hotkeys(window: QMainWindow) -> Callable[[bool], None]:
    """Left/Right walk the positions; Up/Down walk the graph; P pins; A adds.

    Returns:
        The switch for the two keys only an open box owns. Called with whether
        one is.
    """
    for key, verb in (
        (Qt.Key.Key_Left, window.go_back),
        (Qt.Key.Key_Right, window.go_forward),
        (Qt.Key.Key_Up, window.go_up),
        (Qt.Key.Key_Down, window.go_down),
        (Qt.Key.Key_P, window.pin_current),
        (Qt.Key.Key_A, window.add_step),
    ):
        shortcut = QShortcut(QKeySequence(key), window)
        # Auto-repeat off: every one of these verbs is a discrete step, and a
        # held key would run the walk to its end faster than the eye follows.
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(verb)

    owned = []
    # Return and Enter both, because the keypad's is a different key and a user
    # reaching for the one under their hand is not asking for a different verb.
    for key, verb in (
        (Qt.Key.Key_Return, window.take_offer),
        (Qt.Key.Key_Enter, window.take_offer),
        (Qt.Key.Key_Escape, window.cancel_add),
    ):
        shortcut = QShortcut(QKeySequence(key), window)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(verb)
        owned.append(shortcut)

    def switch(enabled: bool) -> None:
        for shortcut in owned:
            shortcut.setEnabled(enabled)

    return switch
