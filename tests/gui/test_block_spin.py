













from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from sieve.gui.block_spin import AUTO, BlockSpinBox

pytestmark = pytest.mark.gui


@pytest.fixture
def spin(qtbot: QtBot) -> BlockSpinBox:
    widget = BlockSpinBox()
    qtbot.addWidget(widget)
    widget.setRange(0, 256)
    return widget


def test_an_accelerated_run_down_stops_at_one_before_auto(spin: BlockSpinBox) -> None:





    spin.setValue(6)
    spin.stepBy(-9)
    assert spin.value() == 1

    spin.stepBy(-1)
    assert spin.value() == AUTO


def test_every_size_down_to_one_is_enterable(spin: BlockSpinBox) -> None:





    for value in range(0, 40):
        spin.lineEdit().setText(str(value))
        spin.interpretText()
        assert spin.value() == value
