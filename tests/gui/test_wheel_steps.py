



























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


    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Panel(QWidget):












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
        contents.setFixedHeight(4000)

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






    instance = WheelSteps(clock=clock)
    qapp.installEventFilter(instance)
    yield instance
    qapp.removeEventFilter(instance)


@pytest.fixture
def panel(qtbot: QtBot, steps: WheelSteps) -> Iterator[_Panel]:

    del steps
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
    clock.now += 10.0
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
    clock.now += ACCEL_WINDOW_S * 2.0
    steps.eventFilter(slider, _wheel(DETENT))
    assert slider.value() == accelerated + 1, "the pause did not reset the multiplier"


def test_trackpad_fractions_accumulate_to_whole_detents(
    panel: _Panel, steps: WheelSteps, clock: _Clock
) -> None:
    slider = panel.slider
    slider.setRange(0, 100)
    slider.setValue(50)
    slider.setFocus()

    for _ in range(3):
        assert steps.eventFilter(slider, _wheel(DETENT // 3)), (
            "a partial delta escaped to Qt's default and would double-step"
        )
        clock.now += ACCEL_WINDOW_S / 2.0
    assert slider.value() == 51


def test_a_wheel_over_an_unfocused_knob_leaves_it_alone(panel: _Panel, steps: WheelSteps) -> None:





    panel.slider.setFocus()
    before_spin = panel.spin.value()

    steps.eventFilter(panel.spin, _wheel(DETENT))
    assert panel.spin.value() == pytest.approx(before_spin), "an unfocused spin box stepped"

    panel.spin.setFocus()
    before_slider = panel.slider.value()
    steps.eventFilter(panel.slider, _wheel(DETENT))
    assert panel.slider.value() == before_slider, "an unfocused slider stepped"


def test_the_passed_through_wheel_reaches_the_scroll_area(panel: _Panel, steps: WheelSteps) -> None:






    panel.slider.setFocus()
    bar = panel.area.verticalScrollBar()
    assert bar.maximum() > 0, "the fixture's scroll area has nowhere to scroll"
    before = bar.value()

    steps.eventFilter(panel.spin, _wheel(-DETENT))

    assert bar.value() > before, "the wheel never reached the enclosing scroll area"


def test_a_knob_with_nothing_to_scroll_steps_without_being_clicked(
    panel: _Panel, steps: WheelSteps
) -> None:








    panel.spin.setFocus()
    before = panel.free.value()
    steps.eventFilter(panel.free, _wheel(DETENT))
    assert panel.free.value() == before + 1, "a knob outside any scroll area was locked"

    bar = panel.area.verticalScrollBar()
    bar.setRange(0, 0)
    before_slider = panel.slider.value()
    steps.eventFilter(panel.slider, _wheel(DETENT))
    assert panel.slider.value() == before_slider + 1, (
        "a knob in a scroll area with nowhere to go was locked"
    )


def test_polish_takes_the_wheel_out_of_a_knob_s_focus_policy(
    panel: _Panel, steps: WheelSteps
) -> None:












    fresh = QDoubleSpinBox()
    assert fresh.focusPolicy() is Qt.FocusPolicy.WheelFocus, "Qt's default moved"
    steps.eventFilter(fresh, QEvent(QEvent.Type.Polish))
    assert fresh.focusPolicy() is Qt.FocusPolicy.StrongFocus

    deliberate = QSlider()
    deliberate.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    steps.eventFilter(deliberate, QEvent(QEvent.Type.Polish))
    assert deliberate.focusPolicy() is Qt.FocusPolicy.NoFocus, "a chosen policy was overruled"


    assert panel.spin.focusPolicy() is Qt.FocusPolicy.StrongFocus


def test_a_pass_through_does_not_poison_the_next_real_gesture(
    panel: _Panel, steps: WheelSteps, clock: _Clock
) -> None:






    slider = panel.slider
    slider.setValue(50)
    slider.setFocus()

    steps.eventFilter(slider, _wheel(DETENT // 3))
    clock.now += ACCEL_WINDOW_S / 2.0
    steps.eventFilter(panel.spin, _wheel(DETENT))
    clock.now += ACCEL_WINDOW_S / 2.0
    steps.eventFilter(slider, _wheel(DETENT // 3))
    clock.now += ACCEL_WINDOW_S / 2.0
    steps.eventFilter(slider, _wheel(DETENT // 3))

    assert slider.value() == 51, "the pass-through disturbed the run in progress"
