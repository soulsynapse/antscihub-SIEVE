"""One wheel detent, one step — everywhere, accelerating through a run.

Qt's default wheel handling is neither uniform nor calm: a slider jumps by
`wheelScrollLines * singleStep` (three, on most systems) while a spinbox
steps by one, so the same flick means different things in different widgets.
This filter sits on the application and intercepts wheel events aimed at any
`QAbstractSlider` or `QAbstractSpinBox`: one detent is one `singleStep`,
always.

**A run accelerates.** Detents arriving within `ACCEL_WINDOW_S` of each other
belong to one gesture, and every `ACCEL_EVERY` of them raise the per-detent
multiplier by one (capped at `ACCEL_MAX`) — so a long crank across a
600-frame slider gets there, while a single careful notch is always exactly
one step. A pause ends the run and the next detent is one step again.

**Trackpad deltas accumulate.** High-resolution devices send fractions of a
detent; they are summed per target and spent in whole detents, so a trackpad
neither multi-steps per event nor loses slow scrolls to rounding. The event
is consumed even while accumulating — otherwise Qt's default handling would
step on top of ours.

The clock is injectable so tests can drive the run/pause boundary without
sleeping.
"""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QAbstractSlider, QAbstractSpinBox

#: One wheel notch, in eighths of a degree — Qt's unit for `angleDelta`.
DETENT = 120

#: A gap longer than this (seconds) ends a run; the multiplier resets.
ACCEL_WINDOW_S = 0.25

#: Detents per extra multiple: the 1st..4th step once each, the 5th..8th
#: twice, and so on.
ACCEL_EVERY = 4

#: Ceiling on the per-detent multiplier, so a flywheel scroll cannot turn a
#: fine control into a slot machine.
ACCEL_MAX = 8


class WheelSteps(QObject):
    """Application-level event filter normalizing wheel steps.

    Install once on the `QApplication`:

        app.installEventFilter(WheelSteps(app))
    """

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        super().__init__(parent)
        self._clock = clock
        self._target: QObject | None = None
        self._last = float("-inf")
        self._run = 0
        self._residual = 0.0

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() is not QEvent.Type.Wheel or not isinstance(event, QWheelEvent):
            return super().eventFilter(watched, event)
        if not isinstance(watched, (QAbstractSlider, QAbstractSpinBox)):
            return super().eventFilter(watched, event)

        now = self._clock()
        if watched is not self._target or now - self._last > ACCEL_WINDOW_S:
            self._run = 0
            self._residual = 0.0
        self._target = watched
        self._last = now

        self._residual += event.angleDelta().y()
        detents = int(self._residual / DETENT)
        self._residual -= detents * DETENT
        if detents != 0:
            multiplier = min(1 + self._run // ACCEL_EVERY, ACCEL_MAX)
            self._run += abs(detents)
            steps = detents * multiplier
            if isinstance(watched, QAbstractSlider):
                watched.setValue(watched.value() + steps * watched.singleStep())
            else:
                watched.stepBy(steps)
        # Consumed either way: Qt's own three-line stepping must never run on
        # top, and a partial trackpad delta is spent here, not there.
        return True
