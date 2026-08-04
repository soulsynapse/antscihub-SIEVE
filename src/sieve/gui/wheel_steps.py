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

**A knob steps unless the wheel has somewhere better to go.** The test is not
focus alone. A control yields only when it is *both* unfocused and enclosed by
a scroll area that has room to move — so the filter tab's right column, where
the cards scroll, can be scrolled past a spin box instead of nudging it on the
way by, while the D slider in the left column, which nothing encloses, still
answers a wheel the moment the cursor is over it. Clicking a card's knob
focuses it and it steps like any other.

The asymmetry is the point: the panel is the only place where a wheel is
ambiguous, because it is the only place where the wheel has a second possible
meaning. Requiring focus everywhere would tax every knob to fix one column.

Passing through means *forwarding*, not merely declining: `wheelEvent` on both
`QAbstractSlider` and `QAbstractSpinBox` steps without consulting focus, so
declining to handle the event would hand it straight to the behaviour this
filter exists to replace. See `WheelSteps._pass_through`.

The clock is injectable so tests can drive the run/pause boundary without
sleeping.
"""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QScrollBar,
    QWidget,
)

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


def _scrollable_ancestor(watched: QWidget, event: QWheelEvent) -> bool:
    """Could this wheel move something that encloses `watched`?

    Asked on the axis the event is actually on, because that is the axis
    `QAbstractScrollArea.wheelEvent` will pick, and a vertical flick over a
    panel that only scrolls sideways has nowhere to go either.

    Room to move is part of the question, not a refinement of it. A card
    column short enough to fit has no second reading of a wheel — the knob is
    the only thing the gesture could mean, so it steps. The cost is that a
    knob's unfocused behaviour depends on the panel's height, which is
    accepted: the alternative is a knob that is dead to the wheel in a panel
    with nothing to scroll, which is worse and harder to explain.
    """
    delta = event.angleDelta()
    parent = watched.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            bar = (
                parent.horizontalScrollBar()
                if abs(delta.x()) > abs(delta.y())
                else parent.verticalScrollBar()
            )
            if bar.maximum() > bar.minimum():
                return True
        if parent.isWindow():
            break
        parent = parent.parentWidget()
    return False


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
        self._forwarding = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        kind = event.type()
        if kind is not QEvent.Type.Wheel and kind is not QEvent.Type.Polish:
            return super().eventFilter(watched, event)
        if not isinstance(watched, (QAbstractSlider, QAbstractSpinBox)):
            return super().eventFilter(watched, event)
        # A scroll area's own bars are navigation, not values — and they are
        # where a passed-through wheel ends up, so normalizing them would both
        # miss the point and swallow the scroll this filter just forwarded.
        if isinstance(watched, QScrollBar):
            return super().eventFilter(watched, event)
        if kind is QEvent.Type.Polish:
            self._drop_wheel_focus(watched)
            return super().eventFilter(watched, event)
        if not isinstance(event, QWheelEvent):
            return super().eventFilter(watched, event)
        if not watched.hasFocus() and _scrollable_ancestor(watched, event):
            return self._pass_through(watched, event)

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

    @staticmethod
    def _drop_wheel_focus(watched: QWidget) -> None:
        """Stop a wheel from *granting* focus, so `hasFocus` can mean what it says.

        Both widget kinds default to `Qt.WheelFocus`, and
        `QApplicationPrivate::giveFocusAccordingToFocusPolicy` acts on a
        spontaneous wheel *before* `notify_helper` runs any event filter. Left
        alone, the first real notch over an unfocused knob would focus it and
        then arrive here already focused — the focus rule would be true and
        useless, and the panel still unscrollable past a control.

        Only the exact default is rewritten. A widget someone deliberately set
        to `NoFocus` or `ClickFocus` is saying something, and nothing here
        should overrule it; `WheelFocus` on a knob is Qt's choice, not the
        author's, which is why it is the one value treated as a default to
        replace rather than a preference to honour.

        `Polish` is the hook because every widget gets exactly one, before it
        is first shown, and it reaches application filters through
        `QCoreApplication.sendEvent` like any other event — so a knob
        `param_form` generates for a filter written next year is covered
        without anything enumerating it.
        """
        if watched.focusPolicy() is Qt.FocusPolicy.WheelFocus:
            watched.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _pass_through(self, watched: QWidget, event: QWheelEvent) -> bool:
        """Give the wheel to whatever encloses an unfocused control.

        Returning `False` would not do it. `QAbstractSpinBox.wheelEvent` and
        `QAbstractSlider.wheelEvent` step on any wheel that reaches them,
        focused or not — declining here would hand the event to exactly the
        behaviour this filter replaces. The event is consumed at the knob and
        re-offered up the parent chain instead.

        The walk is written out rather than delegated because
        `QApplication.notify` only performs it for *spontaneous* wheel events;
        a re-sent one is delivered to its receiver and stops there. So this
        mirrors Qt's own loop: offer, stop at the first acceptor, and respect
        the two things that end propagation — a window boundary and
        `WA_NoMousePropagation`. The acceptor is normally the enclosing scroll
        area, which forwards to its own scrollbar (excluded above, so Qt's
        default scrolling is what finally runs). With no scroll area in the
        chain nothing accepts and the gesture dies quietly, which is the right
        answer for a knob sitting on a plain form.

        The accumulator is deliberately untouched — not advanced and not
        reset. A scroll past a knob must neither spend a fraction of a detent
        it will later be asked for nor break the acceleration run on the knob
        the user is actually cranking.
        """
        if self._forwarding:
            return True
        # Re-entrancy is not reachable through a parent chain of ordinary
        # widgets, but the flag costs nothing and a wheel filter that can
        # recurse is not a thing to leave to inspection.
        self._forwarding = True
        try:
            target = watched.parentWidget()
            while target is not None:
                forwarded = QWheelEvent(
                    QPointF(watched.mapTo(target, event.position().toPoint())),
                    event.globalPosition(),
                    event.pixelDelta(),
                    event.angleDelta(),
                    event.buttons(),
                    event.modifiers(),
                    event.phase(),
                    event.inverted(),
                )
                forwarded.ignore()
                QCoreApplication.sendEvent(target, forwarded)
                if forwarded.isAccepted():
                    break
                if target.isWindow() or target.testAttribute(
                    Qt.WidgetAttribute.WA_NoMousePropagation
                ):
                    break
                target = target.parentWidget()
        finally:
            self._forwarding = False
        return True
