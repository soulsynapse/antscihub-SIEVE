
























from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sieve.gui.commit_combo import CommitCombo

pytestmark = pytest.mark.gui

MODES = ["off", "zscore", "clahe"]


def _key(key: Qt.Key) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)


def _wheel(detents: int) -> QWheelEvent:
    point = QPointF(5.0, 5.0)
    return QWheelEvent(
        point,
        point,
        QPoint(0, 0),
        QPoint(0, detents * 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


@pytest.fixture
def combo(qapp: QApplication) -> CommitCombo:
    del qapp
    box = CommitCombo()
    box.addItems(MODES)
    box.setCurrentIndex(0)
    return box


def _applied(box: CommitCombo) -> list[str]:

    seen: list[str] = []
    box.textActivated.connect(seen.append)
    return seen


def test_arrowing_a_closed_combo_opens_the_popup_and_applies_nothing(
    combo: CommitCombo,
) -> None:
    applied = _applied(combo)

    combo.keyPressEvent(_key(Qt.Key.Key_Down))

    assert combo.view().isVisible()
    assert combo.currentText() == "off"
    assert applied == []
    combo.hidePopup()


def test_walking_the_popup_to_the_third_entry_applies_the_third_and_not_the_second(
    combo: CommitCombo,
) -> None:
    applied = _applied(combo)



    combo.keyPressEvent(_key(Qt.Key.Key_Down))
    view = combo.view()
    view.setCurrentIndex(view.model().index(1, 0))
    view.setCurrentIndex(view.model().index(2, 0))
    assert applied == []
    assert combo.currentText() == "off"

    QTest.keyClick(view, Qt.Key.Key_Return)

    assert applied == ["clahe"]
    assert combo.currentText() == "clahe"


def test_a_wheel_over_a_closed_combo_applies_nothing_and_is_declined(
    combo: CommitCombo,
) -> None:
    applied = _applied(combo)

    event = _wheel(-3)
    combo.wheelEvent(event)

    assert combo.currentText() == "off"
    assert applied == []





    assert not event.isAccepted()


def test_echoing_a_value_into_the_widget_is_not_an_edit(combo: CommitCombo) -> None:
    applied = _applied(combo)

    combo.setCurrentText("zscore")

    assert combo.currentText() == "zscore"
    assert applied == []
