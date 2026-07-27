"""The wheel filter: one detent one step, runs accelerate, fractions add up.

Three claims, each a distinct way scrolling could quietly misbehave. Qt's
default gives a slider three steps per detent and a spinbox one — the filter
must make a detent mean exactly one `singleStep` in both, or the same flick
means different things in different widgets. A run must accelerate and a
pause must reset it, or either a 600-frame slider is unreachable by wheel or
a careful single notch overshoots. And trackpad fractions must accumulate to
whole detents, or high-resolution devices either multi-step per event or
never move at all.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QDoubleSpinBox, QSlider
from pytestqt.qtbot import QtBot

from sieve.gui.wheel_steps import ACCEL_WINDOW_S, DETENT, WheelSteps

pytestmark = pytest.mark.gui


class _Clock:
    """A hand-cranked stand-in for `monotonic`, so runs and pauses are exact."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


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
def steps(clock: _Clock) -> WheelSteps:
    return WheelSteps(clock=clock)


def test_one_detent_is_exactly_one_step_up_and_down(
    qtbot: QtBot, steps: WheelSteps, clock: _Clock
) -> None:
    slider = QSlider()
    qtbot.addWidget(slider)
    slider.setRange(0, 600)
    slider.setValue(100)

    assert steps.eventFilter(slider, _wheel(DETENT)), "the event escaped to Qt's default"
    assert slider.value() == 101, "one detent was not one singleStep"
    clock.now += 10.0  # a pause, so the second notch is its own run
    steps.eventFilter(slider, _wheel(-DETENT))
    assert slider.value() == 100

    spin = QDoubleSpinBox()
    qtbot.addWidget(spin)
    spin.setRange(0.0, 1.0)
    spin.setSingleStep(0.05)
    spin.setValue(0.5)
    clock.now += 10.0
    steps.eventFilter(spin, _wheel(DETENT))
    assert spin.value() == pytest.approx(0.55), "the spinbox stepped by something else"


def test_a_rapid_run_accelerates_and_a_pause_resets_it(
    qtbot: QtBot, steps: WheelSteps, clock: _Clock
) -> None:
    slider = QSlider()
    qtbot.addWidget(slider)
    slider.setRange(0, 10_000)
    slider.setValue(0)

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
    qtbot: QtBot, steps: WheelSteps, clock: _Clock
) -> None:
    slider = QSlider()
    qtbot.addWidget(slider)
    slider.setRange(0, 100)
    slider.setValue(50)

    for _ in range(3):  # 3 x 40 = one detent, no more, no less
        assert steps.eventFilter(slider, _wheel(DETENT // 3)), (
            "a partial delta escaped to Qt's default and would double-step"
        )
        clock.now += ACCEL_WINDOW_S / 2.0
    assert slider.value() == 51
