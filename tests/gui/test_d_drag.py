
















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
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner

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
    return tab._d_slider


def _arena(document: ReplicateDocument) -> None:
    document.add_roi(ROI(0, 0, 100, 100))
    document.select(0)


def test_a_d_drag_reaches_the_document_once_on_release(
    tab: FilterTab, document: ReplicateDocument
) -> None:






    _arena(document)
    slider = _slider(tab)
    start = document.undo_stack.count()

    slider.sliderPressed.emit()
    for value in (55, 50, 45, 40, 35):
        slider.setValue(value)
    assert document.undo_stack.count() == start, (
        "a mid-drag step reached the document — the per-detent round trip is back"
    )


    assert tab.chain.detector.window_frames == 35

    slider.sliderReleased.emit()
    assert document.undo_stack.count() == start + 1
    assert document.resolved_detector_for_selection().window_frames == 35


def test_a_step_outside_a_gesture_still_commits(
    tab: FilterTab, document: ReplicateDocument
) -> None:

    _arena(document)
    start = document.undo_stack.count()

    _slider(tab).setValue(45)

    assert document.undo_stack.count() == start + 1
    assert document.resolved_detector_for_selection().window_frames == 45


def test_the_heat_ceiling_is_not_recomputed_while_the_band_power_stands_still(
    tab: FilterTab, monkeypatch: pytest.MonkeyPatch
) -> None:









    calls = 0
    real = np.percentile

    def counting(a: NDArray[np.float32], q: float) -> np.floating[Any]:
        nonlocal calls
        calls += 1
        return real(a, q)

    monkeypatch.setattr(np, "percentile", counting)

    power = np.random.default_rng(0).random((32, 48)).astype(np.float32)
    first = tab._heat_scale(power)
    again = tab._heat_scale(power)
    assert calls == 1
    assert first == again



    moved = power * 2.0
    assert tab._heat_scale(moved) != first
    assert calls == 2
