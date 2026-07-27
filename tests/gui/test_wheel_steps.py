"""The wheel filter: one detent one step, runs accelerate, fractions add up —
and only on the knob the user is actually pointing at.

Six claims, each a distinct way scrolling could quietly misbehave. Qt's
default gives a slider three steps per detent and a spinbox one — the filter
must make a detent mean exactly one `singleStep` in both, or the same flick
means different things in different widgets. A run must accelerate and a
pause must reset it, or either a 600-frame slider is unreachable by wheel or
a careful single notch overshoots. And trackpad fractions must accumulate to
whole detents, or high-resolution devices either multi-step per event or
never move at all.

The rest are the panel's side of it, and they cut both ways. A wheel meant for
the scroll area must not nudge whatever knob it passed over; it must actually
*reach* the scroll area rather than merely be declined at the knob (declining
hands it straight to `QAbstractSpinBox.wheelEvent`, which steps without
consulting focus); and it must leave the accumulator alone, or scrolling past
a knob poisons the next real gesture on it. Against that, a knob with nothing
scrollable around it — the D slider under the video is the live case — must
keep answering the wheel without being clicked first, because there is no
second thing the gesture could have meant.

Every test here activates its window: focus is half the filter's target test,
and a widget in a window the platform never activated has no focus to have.
`requestActivate` is what makes that true under the offscreen platform CI
runs, where `activateWindow` alone is a no-op.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from pytestqt.qtbot import QtBot

from sieve.gui.wheel_steps import ACCEL_WINDOW_S, DETENT, WheelSteps

pytestmark = pytest.mark.gui


class _Clock:
    """A hand-cranked stand-in for `monotonic`, so runs and pauses are exact."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Panel(QWidget):
    """The filter tab's two columns, reduced to what the wheel rule turns on.

    A knob and a spin box inside a scroll area with a card column taller than
    any viewport it gets — the right side, where a wheel is ambiguous — and a
    bare slider outside it standing for the D slider under the video, where it
    is not. `free` is the control that must keep working without a click.

    Attribute names avoid `scroll`: `QWidget.scroll` already exists, and
    shadowing it is the sort of thing that fails as a type error three files
    away rather than here.
    """

    def __init__(self) -> None:
        super().__init__()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 600)
        self.slider.setValue(100)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(0.0, 1.0)
        self.spin.setSingleStep(0.05)
        self.spin.setValue(0.5)

        contents = QWidget()
        inner = QVBoxLayout(contents)
        for widget in (self.slider, self.spin):
            inner.addWidget(widget)
        contents.setFixedHeight(4000)  # taller than any viewport this gets

        self.area = QScrollArea()
        self.area.setWidget(contents)
        self.area.setWidgetResizable(False)

        self.free = QSlider(Qt.Orientation.Horizontal)
        self.free.setRange(0, 600)
        self.free.setValue(100)

        outer = QVBoxLayout(self)
        outer.addWidget(self.area)
        outer.addWidget(self.free)
        self.resize(200, 200)


def _wheel(delta: int) -> QWheelEvent:
    point = QPointF(5.0, 5.0)
    return QWheelEvent(
        point,
        point,
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture
def steps(qapp: QApplication, clock: _Clock) -> Iterator[WheelSteps]:
    """Installed on the application, as `main.py` installs it.

    Most tests here call `eventFilter` directly, but the `Polish` hook only
    fires through real delivery — so the filter has to be genuinely installed
    before the panel's widgets are built, which is why `panel` depends on it.
    """
    instance = WheelSteps(clock=clock)
    qapp.installEventFilter(instance)
    yield instance
    qapp.removeEventFilter(instance)


@pytest.fixture
def panel(qtbot: QtBot, steps: WheelSteps) -> Iterator[_Panel]:
    """A shown, activated panel — without activation nothing can hold focus."""
    del steps  # ordering only: the filter must be installed before Polish
    widget = _Panel()
    qtbot.addWidget(widget)
    widget.show()
    handle = widget.windowHandle()
    assert handle is not None
    handle.requestActivate()
    qtbot.waitUntil(lambda: widget.isActiveWindow(), timeout=5_000)
    yield widget


def test_one_detent_is_exactly_one_step_up_and_down(
    panel: _Panel, steps: WheelSteps, clock: _Clock
) -> None:
    panel.slider.setFocus()
    assert steps.eventFilter(panel.slider, _wheel(DETENT)), "the event escaped to Qt's default"
    assert panel.slider.value() == 101, "one detent was not one singleStep"
    clock.now += 10.0  # a pause, so the second notch is its own run
    steps.eventFilter(panel.slider, _wheel(-DETENT))
    assert panel.slider.value() == 100

    panel.spin.setFocus()
    clock.now += 10.0
    steps.eventFilter(panel.spin, _wheel(DETENT))
    assert panel.spin.value() == pytest.approx(0.55), "the spinbox stepped by something else"


def test_a_rapid_run_accelerates_and_a_pause_resets_it(
    panel: _Panel, steps: WheelSteps, clock: _Clock
) -> None:
    slider = panel.slider
    slider.setRange(0, 10_000)
    slider.setValue(0)
    slider.setFocus()

    detents = 12
    for _ in range(detents):
        steps.eventFilter(slider, _wheel(DETENT))
        clock.now += ACCEL_WINDOW_S / 2.0
    assert slider.value() > detents, "a rapid run never accelerated"

    accelerated = slider.value()
    clock.now += ACCEL_WINDOW_S * 2.0  # the pause that ends the run
    steps.eventFilter(slider, _wheel(DETENT))
    assert slider.value() == accelerated + 1, "the pause did not reset the multiplier"


def test_trackpad_fractions_accumulate_to_whole_detents(
    panel: _Panel, steps: WheelSteps, clock: _Clock
) -> None:
    slider = panel.slider
    slider.setRange(0, 100)
    slider.setValue(50)
    slider.setFocus()

    for _ in range(3):  # 3 x 40 = one detent, no more, no less
        assert steps.eventFilter(slider, _wheel(DETENT // 3)), (
            "a partial delta escaped to Qt's default and would double-step"
        )
        clock.now += ACCEL_WINDOW_S / 2.0
    assert slider.value() == 51


def test_a_wheel_over_an_unfocused_knob_leaves_it_alone(panel: _Panel, steps: WheelSteps) -> None:
    """The bug: scrolling to reach a control below nudged what it passed over.

    Both widget kinds, because their default `wheelEvent`s differ and only one
    of them would be caught by testing a slider alone.
    """
    panel.slider.setFocus()  # focus is somewhere else in the same panel
    before_spin = panel.spin.value()

    steps.eventFilter(panel.spin, _wheel(DETENT))
    assert panel.spin.value() == pytest.approx(before_spin), "an unfocused spin box stepped"

    panel.spin.setFocus()
    before_slider = panel.slider.value()
    steps.eventFilter(panel.slider, _wheel(DETENT))
    assert panel.slider.value() == before_slider, "an unfocused slider stepped"


def test_the_passed_through_wheel_reaches_the_scroll_area(panel: _Panel, steps: WheelSteps) -> None:
    """Not consumed, not merely declined — forwarded, and it scrolls.

    Returning `False` would look like a pass-through and be the opposite:
    `QAbstractSpinBox.wheelEvent` steps whatever reaches it. The claim is that
    the panel actually moves, which is the whole gesture the bug denied.
    """
    panel.slider.setFocus()
    bar = panel.area.verticalScrollBar()
    assert bar.maximum() > 0, "the fixture's scroll area has nowhere to scroll"
    before = bar.value()

    steps.eventFilter(panel.spin, _wheel(-DETENT))

    assert bar.value() > before, "the wheel never reached the enclosing scroll area"


def test_a_knob_with_nothing_to_scroll_steps_without_being_clicked(
    panel: _Panel, steps: WheelSteps
) -> None:
    """The other half of the rule, and the reason it is not focus alone.

    The D slider under the video is enclosed by nothing that scrolls, so a
    wheel over it has exactly one possible meaning and requiring a click first
    would be a tax paid to fix a different column. Two cases: a knob outside
    any scroll area, and a knob inside one that has nowhere to go — the second
    is what a short card column is, and it must not leave the knob dead.
    """
    panel.spin.setFocus()  # focus is elsewhere, as in the failing gesture
    before = panel.free.value()
    steps.eventFilter(panel.free, _wheel(DETENT))
    assert panel.free.value() == before + 1, "a knob outside any scroll area was locked"

    bar = panel.area.verticalScrollBar()
    bar.setRange(0, 0)  # the card column now fits; nothing left to scroll to
    before_slider = panel.slider.value()
    steps.eventFilter(panel.slider, _wheel(DETENT))
    assert panel.slider.value() == before_slider + 1, (
        "a knob in a scroll area with nowhere to go was locked"
    )


def test_polish_takes_the_wheel_out_of_a_knob_s_focus_policy(
    panel: _Panel, steps: WheelSteps
) -> None:
    """Without this the focus rule is true and useless.

    Qt hands focus to a `WheelFocus` widget on a *spontaneous* wheel, inside
    `QApplication.notify` and before any event filter runs — so the first real
    notch over an unfocused spin box would focus it on the way in and step it
    here. Tests never see this (a hand-built event is not spontaneous), which
    is exactly why the policy is pinned directly rather than left to be
    noticed in the application.

    The `NoFocus` case is the other half: only Qt's default is rewritten, not
    a policy someone chose.
    """
    fresh = QDoubleSpinBox()
    assert fresh.focusPolicy() is Qt.FocusPolicy.WheelFocus, "Qt's default moved"
    steps.eventFilter(fresh, QEvent(QEvent.Type.Polish))
    assert fresh.focusPolicy() is Qt.FocusPolicy.StrongFocus

    deliberate = QSlider()
    deliberate.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    steps.eventFilter(deliberate, QEvent(QEvent.Type.Polish))
    assert deliberate.focusPolicy() is Qt.FocusPolicy.NoFocus, "a chosen policy was overruled"

    # And the widgets the panel already showed went through the real hook.
    assert panel.spin.focusPolicy() is Qt.FocusPolicy.StrongFocus


def test_a_pass_through_does_not_poison_the_next_real_gesture(
    panel: _Panel, steps: WheelSteps, clock: _Clock
) -> None:
    """Scrolling past a knob must not spend, or reset, the accumulator.

    Three partial deltas make one detent. If the pass-through in the middle
    took a share of the residual — or cleared it, or advanced the run — the
    focused knob would land somewhere other than exactly one step on.
    """
    slider = panel.slider
    slider.setValue(50)
    slider.setFocus()

    steps.eventFilter(slider, _wheel(DETENT // 3))
    clock.now += ACCEL_WINDOW_S / 2.0
    steps.eventFilter(panel.spin, _wheel(DETENT))  # a scroll past the unfocused one
    clock.now += ACCEL_WINDOW_S / 2.0
    steps.eventFilter(slider, _wheel(DETENT // 3))
    clock.now += ACCEL_WINDOW_S / 2.0
    steps.eventFilter(slider, _wheel(DETENT // 3))

    assert slider.value() == 51, "the pass-through disturbed the run in progress"
