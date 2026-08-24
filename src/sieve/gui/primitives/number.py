"""The number box: a quantity in a range, typed into or stepped.

A control and not a wrapper, on `field.py`'s terms and for its reason — it is
dressed and knows nothing about a label, so it stands in a row, a cell, or a
`Field` without any of them being the one place it can go. A unit beside it is
`Field(unit=…)`'s and not this file's, because a unit is a thing said about a
value and not a part of one.

`LineField(numeric=True)` is next to this and is not it. That right-aligns text
and takes anything; this holds a number, refuses what is not one, knows its own
range, and can be stepped. The two are different controls for different jobs and
the one that reads a crop's four corners is this.

**What makes it a primitive is that it can be told.** Everything it edits is a
clamped quantity — a crop corner that must stay on the frame, a budget that must
stay positive — and the shape of every such editor is the same: the user pushes
a value, something decides what is actually allowed, and the box has to end up
showing *that*. `show_value` does it without emitting, and the omission matters.
A box that announced a correction as though a person had typed it would tell its
owner to push again, and an owner whose clamp is not idempotent would be pushed
and corrected and pushed for as long as the two disagreed. Blocking the signal
takes that whole class of loop off the table rather than relying on every clamp
to terminate.

**It reports when editing finishes, not on every keystroke.** Typing `1024` into
an empty box passes through 1, 10 and 102, and a clamp reading those would fight
the person typing them — the crop would jump to the minimum twice before the
last digit landed. `keyboardTracking` off is Qt's own answer to this and is used
rather than a timer: the value is announced when the field is left or Return is
pressed, and immediately when the arrows or the wheel step it, which is what
those are for.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSpinBox, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb
from sieve.gui.primitives.field import EDGE, EDGE_HOVER, RADIUS


class NumberBox(QSpinBox):
    """A whole number in a range, in the tree's roles."""

    #: The value, once the person is done choosing it. Distinct from
    #: `valueChanged`, which Qt also emits when `setValue` is called from code;
    #: this one is only ever a person's doing, so an owner can push a correction
    #: through `show_value` without hearing about it.
    chosen = Signal(int)

    def __init__(
        self,
        value: int = 0,
        *,
        low: int = 0,
        high: int = 1_000_000,
        step: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("numberbox")
        self.setRange(low, high)
        self.setSingleStep(step)
        self.setValue(value)
        self.setAlignment(Qt.AlignmentFlag.AlignRight
                          | Qt.AlignmentFlag.AlignVCenter)
        # Off, so a half-typed number is not announced. See the module
        # docstring: with it on, typing 1024 announces 1, then 10, then 102.
        self.setKeyboardTracking(False)
        # Not on scroll. A box in a scrolling column that ate the wheel would
        # change the value of whatever the pointer passed over on the way down,
        # which is a change nobody asked for and would not notice making.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._quiet = False

        self.valueChanged.connect(self._announce)
        # Bound methods and never lambdas, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` would keep a dead box subscribed.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)
        self._dress()

    # -- being told ------------------------------------------------------
    def show_value(self, value: int) -> None:
        """Display `value` without announcing it.

        Not called `show`, which was its first name and shadowed
        `QWidget.show` — a box put in a layout and then made visible the
        ordinary way would have raised for want of an argument, somewhere with
        nothing to do with numbers. Matches `VideoCanvas.show_frame`.

        What an owner calls after deciding what is actually allowed. The
        silence is the point: announcing a correction would ask the owner to
        decide again about a value it has just decided, and two decisions that
        disagree would trade the value back and forth for as long as they did.
        """
        if value == self.value():
            return
        self._quiet = True
        try:
            self.setValue(value)
        finally:
            self._quiet = False

    def _announce(self, value: int) -> None:
        if not self._quiet:
            self.chosen.emit(value)

    def wheelEvent(self, event) -> None:
        """Ignore the wheel unless this box is the one being used.

        A column of these inside a scroll area would otherwise each take a turn
        at the wheel as the pointer crossed them, and somebody scrolling past a
        crop would arrive at the bottom having changed it.
        """
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    # -- what it wears ---------------------------------------------------
    def _dress(self) -> None:
        """The sheet, in the palette and at the size now in use.

        Scoped to `#numberbox` rather than to `QSpinBox`, for the reason
        `field.py` gives: this stands inside a card whose sheet is set on an
        ancestor, and a bare class rule would reach every spin box in the pane.

        The same fill and edge as a field, because it *is* a field with a
        different thing in it, and two controls on one card that differ only in
        what they accept should not also differ in how they look.
        """
        self.setStyleSheet(f"""
            #numberbox {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-radius: {RADIUS}px;
                padding: 4px 8px;
                font-size: {metrics.pt("name")}pt;
                selection-background-color: {rgb(ACCENT)};
                selection-color: {rgb(PANEL)};
            }}
            #numberbox:hover {{
                border-color: {rgb(mix(LINE, TEXT, EDGE_HOVER))};
            }}
            #numberbox:focus {{ border-color: {rgb(ACCENT)}; }}
            #numberbox:disabled {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border-color: {rgb(LINE)};
            }}
            #numberbox::up-button, #numberbox::down-button {{
                width: 14px;
                background: transparent;
                border: 0;
            }}
        """)
