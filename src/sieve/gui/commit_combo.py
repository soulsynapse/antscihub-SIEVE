"""A drop menu whose value changes when the user says it does.

The number fields learned this rule in `spacebar-dies-on-focus`: an edit runs
from the first keystroke to a commit, and nothing in between reaches the
document. Combo boxes are the other half of it, and the obvious fix does not
work. `QComboBox` emits `activated` — Qt's "the user chose this" signal — for
**keyboard navigation of a closed combo** as well as for a click in the popup,
because Qt treats arrowing a closed combo as an act of selection. Swapping
`currentTextChanged` for `textActivated` therefore fixes the popup case and
leaves the arrow-key case exactly as it was: hold Down over a filter's mode
list and every value passed through is a re-plan, a new cache key, and a
render, at whatever speed the key repeats.

So the case is removed rather than filtered. **Navigation keys on a closed
combo open the popup**, where arrowing highlights and only Enter or a click
selects. Highlight and selection become distinct states in both directions,
`textActivated` becomes a complete statement of intent, and it is the only
signal anything wires to. There is no pending-value display to invent, which
is what the alternatives cost — a debounce makes "chosen" a function of how
fast the user moves, and a pending-and-commit combo must *show* its pending
state or it looks more live than it is (rule 6's mirror clause).

**A wheel over a closed combo does nothing either**, and passes to whatever
encloses it. `QComboBox.wheelEvent` steps the current index and activates on
each notch, so a scroll down the card column would commit every mode between
the one showing and the one under the cursor when the scroll ended — the same
defect `wheel_steps.py` removed from spin boxes and sliders, arriving through
a widget kind that filter does not watch. The rule here is simpler than that
one's, because it can be: a knob still has to step for someone who means to
step it, and a combo has no step that is not a commit, so it never answers the
wheel at all.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QComboBox, QWidget

#: The keys `QComboBox` uses to move through a *closed* list. Each one steps
#: the value and emits `activated` on the way past; each one opens the popup
#: here instead.
NAVIGATION_KEYS = frozenset(
    {
        Qt.Key.Key_Up,
        Qt.Key.Key_Down,
        Qt.Key.Key_PageUp,
        Qt.Key.Key_PageDown,
        Qt.Key.Key_Home,
        Qt.Key.Key_End,
    }
)


class CommitCombo(QComboBox):
    """A `QComboBox` that has a highlight state distinct from its selection.

    Wire `textActivated` (or `activated`) and nothing else; `currentTextChanged`
    still fires for programmatic `setCurrentText`, which is how a chain value is
    echoed back into the widget and must not look like an edit.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A wheel must not grant focus on its way to being ignored — the same
        # reason `wheel_steps.py` rewrites this policy on knobs, except that
        # here the widget is the one place that knows.
        if self.focusPolicy() is Qt.FocusPolicy.WheelFocus:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        """Open the popup instead of stepping, while the popup is closed.

        Type-to-search is deliberately left alone: a keystroke that names an
        entry is a statement of *which* entry, not a walk past the ones in
        between, so it is a selection under this rule rather than a violation
        of it.
        """
        if e.key() in NAVIGATION_KEYS and not self.view().isVisible():
            self.showPopup()
            e.accept()
            return
        super().keyPressEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        """Decline the wheel, so it reaches whatever the user is scrolling.

        Declining is enough here — unlike the spin-box case in
        `wheel_steps.py`, where the filter had to forward by hand because
        returning `False` would have handed the event straight to the
        `wheelEvent` it was replacing. This *is* that `wheelEvent`, so an
        ignored spontaneous wheel propagates up the parent chain the way Qt
        propagates any unhandled one.
        """
        e.ignore()
