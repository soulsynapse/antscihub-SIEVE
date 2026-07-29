







from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preview_runner import PreviewRunner
from tests.conftest import FIXTURE_FPS, FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_WIDTH

pytestmark = pytest.mark.gui

RENDER_TIMEOUT_MS = 30_000


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
    qtbot: QtBot,
    tmp_path: Path,
    player: VideoPlayer,
    document: ReplicateDocument,
    runner: PreviewRunner,
) -> Iterator[FilterTab]:


    preferences = Preferences(QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat))
    instance = FilterTab(player, document, runner, metrics=MetricBus(), preferences=preferences)
    qtbot.addWidget(instance)
    yield instance




    instance.shutdown()


def test_removing_the_temporal_step_hides_its_graphs_and_says_why(tab: FilterTab) -> None:








    card = tab.stack.card_for("morlet_band")
    assert card is not None
    assert tab.scalogram.parent() is not None

    card.removal_buttons()[0].click()

    assert tab.stack.card_for("morlet_band") is None
    assert tab.scalogram.parent() is None and tab.scalogram.isHidden()
    assert tab.density.parent() is None and tab.density.isHidden()
    assert "no reachable" in tab.count_plot.notice
    assert tab.summary_text == "chain incomplete — see the stack"


def test_the_speed_button_cycles_the_named_rates_and_reports_the_active_one(
    tab: FilterTab, player: VideoPlayer
) -> None:






    assert tab.speed_button.text() == "1x"
    assert player.playback_rate == 1.0

    tab.speed_button.click()
    assert player.playback_rate == 2.0
    assert tab.speed_button.text() == "2x"

    tab.speed_button.click()
    assert player.playback_rate == 5.0
    assert tab.speed_button.text() == "5x"

    tab.speed_button.click()
    assert player.playback_rate == 1.0
    assert tab.speed_button.text() == "1x"


def test_the_gray_decode_applies_only_while_the_tab_is_showing(
    tab: FilterTab, player: VideoPlayer
) -> None:






    tab.show()
    assert not player.viewport_luma

    tab.gray_toggle.click()
    assert player.viewport_luma, "the manual choice did not reach the player"

    tab.hide()
    assert not player.viewport_luma, "leaving the tab must hand the pane back in colour"
    assert tab.gray_toggle.effective_luma, "hiding must not unset the preference"


    tab.gray_toggle.click()
    tab.gray_toggle.click()
    assert not player.viewport_luma

    tab.show()
    assert player.viewport_luma, "returning must reapply the toggle's answer"


def test_a_knob_burst_mid_render_yields_one_final_recompute_with_the_last_value(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    runner: PreviewRunner,
    synthetic_video: Path,
) -> None:








    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_FPS)
    updates: list[int] = []
    tab.graphs_updated.connect(lambda: updates.append(1))


    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: len(updates) >= 1, timeout=RENDER_TIMEOUT_MS)
    qtbot.wait(300)
    base = len(updates)


    tab.downsample_knob.setValue(0.50)
    tab.downsample_knob.setValue(0.40)
    tab.downsample_knob.setValue(0.30)

    qtbot.waitUntil(lambda: len(updates) > base, timeout=RENDER_TIMEOUT_MS)

    qtbot.wait(300)

    assert len(updates) == base + 1, "the burst produced more than one final recompute"
    rescale = next(s for s in tab.chain.steps if s.step_id == "rescale")
    assert rescale.node is not None and rescale.node.params["scale"] == pytest.approx(0.30)


    assert tab.count_plot.notice in ("", "disarmed — place the count threshold")
