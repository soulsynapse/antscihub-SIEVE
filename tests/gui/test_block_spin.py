"""The Block spin box refuses nothing, and steps across one semantic boundary.

This file used to pin a refusal: `density_plot.MAX_BLOCKS` implied a
per-replicate floor and the spin box stepped over the sizes under it. That is
gone (`docs/todo/budgets-attribute-cost-they-do-not-cap-it.md`) — block count
is a scientific parameter and the stall that justified capping it left the GUI
thread. What survives is the distinction the hole was hiding: `0` is auto, a
*mode*, and a crank down the range must not cross into it without the smallest
size being seen on the way.

The two tests fail for different reasons: an accelerated run that overshoots
into the mode, and a floor that has quietly come back.
"""

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
    """`wheel_steps.py` routes a detent through `stepBy` with several steps.

    A run that landed straight on auto would change the *meaning* of the knob
    — from a size to a mode — without the user seeing the smallest size.
    """
    spin.setValue(6)
    spin.stepBy(-9)
    assert spin.value() == 1

    spin.stepBy(-1)
    assert spin.value() == AUTO


def test_every_size_down_to_one_is_enterable(spin: BlockSpinBox) -> None:
    """No hole anywhere: the whole range is a legal block edge.

    Fails if a floor returns — including one reintroduced as a `setMinimum`,
    which would take auto with it.
    """
    for value in range(0, 40):
        spin.lineEdit().setText(str(value))
        spin.interpretText()
        assert spin.value() == value
