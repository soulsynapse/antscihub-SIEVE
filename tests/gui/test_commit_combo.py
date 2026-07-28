"""A drop menu applies on selection, not on highlight.

Four claims, each a distinct way the value could change without the user
saying it did.

The first two are the item's own repro. Arrowing a *closed* `QComboBox` steps
its current index and emits `activated` for every entry passed through — Qt
counts arrowing a closed combo as an act of selection — so a plain signal swap
would fix the popup and leave the arrow keys alone. Down must therefore open
the popup and commit nothing, and a walk to the third entry followed by Enter
must apply the third and only the third.

The third is the same defect through a device the tab's wheel filter does not
watch: `wheel_steps.py` only intercepts sliders and spin boxes, so a scroll
down the card column would reach `QComboBox.wheelEvent` and commit every mode
it passed. The combo must decline rather than consume, which is what lets Qt's
spontaneous-wheel propagation carry the gesture to the scroll area.

The fourth is the other direction, and it is what makes the widget safe to
echo into: `_sync_widgets_from_chain` writes the chain's value back with
`setCurrentText`, and that must never read as an edit. `blockSignals` covers
it today; wiring `textActivated` makes it true without the guard, which is the
property worth pinning because the guard is easy to drop.
"""

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
    """Everything the document would have been told, in order."""
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

    # Down opens; inside the popup, moving is a highlight — a state that is now
    # distinct from the selection, so nothing is applied on the way past.
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
    # Declined, which is the whole of this widget's part in it: Qt's own
    # propagation loop for *spontaneous* wheels is what then hands the gesture
    # to the enclosing scroll area. (`wheel_steps.py` has to forward by hand
    # because it is a filter running ahead of a `wheelEvent` that would step
    # regardless; this is that `wheelEvent`.)
    assert not event.isAccepted()


def test_echoing_a_value_into_the_widget_is_not_an_edit(combo: CommitCombo) -> None:
    applied = _applied(combo)

    combo.setCurrentText("zscore")

    assert combo.currentText() == "zscore"
    assert applied == []
