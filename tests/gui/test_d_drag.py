"""Dragging D is a drag, not sixty committed edits.

D was the one control in the tab that wrote to the document on every step and
leaned on `EditDetector.mergeWith` to fold the history back up afterwards.
Merging fixes the undo stack; it does not make the work go away — each step
still pushed a command, re-pinned the diff on the replicate, re-resolved the
detector through the pin chain, re-synced the knobs, and rebuilt every card
caption before reaching the derive the user is actually dragging for. That is
why D was dead in the filter tab and merely slow in the wizard, whose
`_cheap_retune` skips every line of it.

Three claims, each failing for a distinct reason: a drag that still reaches the
document (the round trip is back), a drag whose value never reaches the graphs
(the drag tier is inert), and a keystroke that never commits (the split ate the
non-drag path, which has no release coming to commit it).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray
from PySide6.QtWidgets import QSlider
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.transport.player import VideoPlayer

pytestmark = pytest.mark.gui


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def runner(qapp: object) -> Iterator[PreviewRunner]:
    del qapp
    instance = PreviewRunner(metrics=MetricBus())
    yield instance
    instance.shutdown()


@pytest.fixture
def tab(
    qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument, runner: PreviewRunner
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, runner, metrics=MetricBus())
    qtbot.addWidget(instance)
    document.bind_source(1000, 800, 1000, 30.0)
    yield instance
    instance.shutdown()


def _slider(tab: FilterTab) -> QSlider:
    return tab._d_slider  # pyright: ignore[reportPrivateUsage]


def _arena(document: ReplicateDocument) -> None:
    document.add_roi(ROI(0, 0, 100, 100))
    document.select(0)


def test_a_d_drag_reaches_the_document_once_on_release(
    tab: FilterTab, document: ReplicateDocument
) -> None:
    """Not once per detent, and not zero times.

    The mid-drag count is the load-bearing half: `mergeWith` would make the
    *final* stack look identical either way, so a test that only counted
    entries after the release would pass against the behaviour this fixes.
    """
    _arena(document)
    slider = _slider(tab)
    start = document.undo_stack.count()

    slider.sliderPressed.emit()
    for value in (55, 50, 45, 40, 35):
        slider.setValue(value)
    assert document.undo_stack.count() == start, (
        "a mid-drag step reached the document — the per-detent round trip is back"
    )
    # ...and the graphs are following it anyway, which is the point of a drag
    # tier that skips the document rather than skipping the work.
    assert tab.chain.detector.window_frames == 35

    slider.sliderReleased.emit()
    assert document.undo_stack.count() == start + 1
    assert document.resolved_detector_for_selection().window_frames == 35


def test_a_step_outside_a_gesture_still_commits(
    tab: FilterTab, document: ReplicateDocument
) -> None:
    """Keyboard, wheel, and `setValue` have no release coming to commit them."""
    _arena(document)
    start = document.undo_stack.count()

    _slider(tab).setValue(45)

    assert document.undo_stack.count() == start + 1
    assert document.resolved_detector_for_selection().window_frames == 45


def test_the_heat_ceiling_is_not_recomputed_while_the_band_power_stands_still(
    tab: FilterTab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cheap tier hands back the same `band_power`; the percentile over it
    must not be paid again.

    It is a percentile across the largest array the tab holds — ~29 ms at
    (600, 8040) against ~0.01 ms for the prefix-sum a D step actually changes —
    so paying it per detent is what made both paths lag regardless of the
    document round trip. Counted rather than timed: a timing assertion here
    would be a flake, and the claim is that the call does not happen at all.
    """
    calls = 0
    real = np.percentile

    def counting(a: NDArray[np.float32], q: float) -> np.floating[Any]:
        nonlocal calls
        calls += 1
        return real(a, q)

    monkeypatch.setattr(np, "percentile", counting)

    power = np.random.default_rng(0).random((32, 48)).astype(np.float32)
    first = tab._heat_scale(power)  # pyright: ignore[reportPrivateUsage]
    again = tab._heat_scale(power)  # pyright: ignore[reportPrivateUsage]
    assert calls == 1
    assert first == again

    # A real move still recounts: a frequency commit or a new render builds a
    # fresh array, and that is exactly when the ceiling is owed one.
    moved = power * 2.0
    assert tab._heat_scale(moved) != first  # pyright: ignore[reportPrivateUsage]
    assert calls == 2
