"""Enter and Esc hand the keyboard back, so the spacebar plays again.

`docs/completed-todo/2026.07.27-spacebar-dies-on-focus.md` gave an edit three
exits — Enter, Esc, and leaving the field — and made the *action* live again at
each of them. Only the third gives the user back the **key**. A spin box that
still holds focus swallows Space before the shortcut map ever sees it:
`QLineEdit` accepts the `ShortcutOverride` for any key it would insert as text,
and Space is one. So after typing a window start and pressing Enter, Play/Pause
is enabled in the menu, the transport button works, and the spacebar is dead —
a control looking more live than it is, which is rule 6's mirror direction.

The handback is deferred by one turn of the event loop rather than done in
place. Order is the whole reason: clearing focus *first* delivers a focus-out,
which is a commit, so an Esc meant to abandon a half-typed number would write
it instead. Letting the key run to completion and clearing after leaves each
exit meaning what it means. The widget is the timer's context object, so a
field destroyed between the keypress and the turn takes the pending call with
it.

Scoped to `QAbstractSpinBox` — every knob in the application, including the
ones `param_form` generates for a filter written next year. Text fields are
left alone: their Enter and Esc already belong to something else (the wizard's
search box hands Esc up to the wizard, which cancels it), and no one types
prose into a spin box.

Dialogs need no exception. Esc and Enter there reach `QDialog` by ordinary
propagation whatever this does, and a handback on a dialog that is closing
costs nothing.

Install once on the `QApplication`, beside `wheel_steps.WheelSteps`:

    app.installEventFilter(KeyboardHandback(app))
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QAbstractSpinBox

#: The two keys that end an edit without moving the mouse. Leaving the field is
#: the third exit and already releases the keyboard by definition.
EXITS = frozenset({Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape})


class KeyboardHandback(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() is not QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)
        if not isinstance(watched, QAbstractSpinBox) or not isinstance(event, QKeyEvent):
            return super().eventFilter(watched, event)
        if Qt.Key(event.key()) not in EXITS:
            return super().eventFilter(watched, event)
        QTimer.singleShot(0, watched, watched.clearFocus)
        # Never consumed: the field's own commit, the crop field's Esc revert,
        # and a dialog's accept/reject all still have to run.
        return super().eventFilter(watched, event)
