








from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSpinBox
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner
from sieve.pipeline.preview import PreviewRender
from tests.conftest import FIXTURE_FPS, FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_WIDTH

pytestmark = pytest.mark.gui

RENDER_TIMEOUT_MS = 30_000




SEAM_ABOVE_EXTRACTION = 2


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
    yield instance




    instance.shutdown()


def test_cancel_restores_the_exact_prior_state(qtbot: QtBot, tab: FilterTab) -> None:








    snapshot = tab.chain
    tab.stack.insert_requested.emit(SEAM_ABOVE_EXTRACTION)

    wizard = tab.wizard
    assert wizard is not None
    assert wizard.selected_entry is not None
    assert wizard.selected_entry.entry_id == "downsample"

    card = tab.stack.card_for("downsample")
    assert card is not None and card.provisional
    assert tab.chain is not snapshot


    factor = next(w for w in wizard.settings_host.findChildren(QSpinBox) if w.value() == 2)
    factor.setValue(4)
    wizard.d_slider.setValue(120)
    assert tab.chain.detector.window_frames == 120

    QTest.keyClick(wizard, Qt.Key.Key_Escape)

    assert tab.wizard is None
    assert tab.chain == snapshot
    assert tab.stack.card_for("downsample") is None
    assert all(not c.provisional for c in tab.stack.cards())


def test_add_displays_the_wizard_tuning_on_the_tabs_own_widgets(tab: FilterTab) -> None:









    tab.stack.insert_requested.emit(SEAM_ABOVE_EXTRACTION)
    wizard = tab.wizard
    assert wizard is not None
    before = tab.chain.detector.window_frames
    wizard.d_slider.setValue(before + 60)

    wizard.accepted.emit()

    assert tab.wizard is None
    assert tab.chain.detector.window_frames == before + 60

    assert tab._d_slider.value() == before + 60


def test_a_disabled_candidate_cannot_be_committed_by_any_input_path(tab: FilterTab) -> None:







    tab.stack.insert_requested.emit(SEAM_ABOVE_EXTRACTION)
    wizard = tab.wizard
    assert wizard is not None
    before = wizard.selected_entry

    assert not wizard.select_entry("normalize")
    assert wizard.selected_entry is before

    row = next(
        item
        for item in wizard.candidate_rows()
        if item.data(Qt.ItemDataRole.UserRole) == "normalize"
    )
    assert not row.flags() & Qt.ItemFlag.ItemIsEnabled
    wizard.candidate_list.itemClicked.emit(row)
    assert wizard.selected_entry is before

    wizard.add_button.click()
    assert tab.wizard is None
    assert sum(1 for s in tab.chain.steps if s.step_id == "normalize") == 1


def test_a_provisional_render_reuses_the_store_above_the_seam(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    runner: PreviewRunner,
    synthetic_video: Path,
) -> None:







    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_FPS)
    updates: list[int] = []
    renders: list[PreviewRender] = []
    tab.graphs_updated.connect(lambda: updates.append(1))

    def collect(render: PreviewRender) -> None:
        renders.append(render)

    runner.render_finished.connect(collect)

    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: len(updates) >= 1, timeout=RENDER_TIMEOUT_MS)
    qtbot.wait(300)
    seen = len(renders)

    tab.stack.insert_requested.emit(SEAM_ABOVE_EXTRACTION)
    assert tab.wizard is not None

    qtbot.waitUntil(lambda: len(renders) > seen, timeout=RENDER_TIMEOUT_MS)
    provisional = renders[-1]


    frames = provisional.frames
    assert frames > 0
    assert provisional.from_cache >= 2 * frames
    assert provisional.reuse > 0.0
