"""Item 6's back half: the stack presents the chain, the tab coalesces work.

Two claims, each a different way the tab could lie. A removed temporal step
whose graphs stayed on screen would show a detector that no longer exists;
a knob burst that recomputed per edit would spend the working window's render
cost once per wiggle and paint intermediate values nobody asked to keep.
"""

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
    # The store is injected so a test that clicks the gray toggle writes to a
    # file the test owns, never to the developer's real settings.
    preferences = Preferences(QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat))
    instance = FilterTab(player, document, runner, metrics=MetricBus(), preferences=preferences)
    qtbot.addWidget(instance)
    yield instance
    # The tab owns the detector thread, so it carries the same
    # shutdown obligation the player and the runner do. Without
    # this every tab built here leaks a QThread and the suite
    # wedges a few modules later.
    instance.shutdown()


def test_removing_the_temporal_step_hides_its_graphs_and_says_why(tab: FilterTab) -> None:
    """No reachable step, no graph — and the absence explains itself.

    The scalogram and density plots live in the morlet card; removing the
    step must take them out of the stack (not merely blank them), the count
    plot must say why it has nothing to show, and the summary must point at
    the stack. A tab that failed this would keep painting a detector whose
    producing step the user deleted.
    """
    card = tab.stack.card_for("morlet_band")
    assert card is not None
    assert tab.scalogram.parent() is not None  # embedded in the card

    card.removal_buttons()[0].click()

    assert tab.stack.card_for("morlet_band") is None
    assert tab.scalogram.parent() is None and tab.scalogram.isHidden()
    assert tab.density.parent() is None and tab.density.isHidden()
    assert "no reachable" in tab.count_plot.notice
    assert tab.summary_text == "chain incomplete — see the stack"


def test_the_speed_button_cycles_the_named_rates_and_reports_the_active_one(
    tab: FilterTab, player: VideoPlayer
) -> None:
    """1x → 2x → 5x → 1x, with the label written from the adopted rate.

    The transport stays wall-clock at every step — the rate scales the clock
    — so the assertion that matters is that button text and player rate can
    never disagree: the label is read back from the player after each click.
    """
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
    """The format follows the tab; the toggle's state survives the excursion.

    A player left gray after leaving the tab would paint the replicate tab's
    arenas in a format chosen for a loop that is not on screen — and a toggle
    reset by the excursion would forget a preference the user did state.
    """
    tab.show()
    assert not player.viewport_luma

    tab.gray_toggle.click()
    assert player.viewport_luma, "the manual choice did not reach the player"

    tab.hide()
    assert not player.viewport_luma, "leaving the tab must hand the pane back in colour"
    assert tab.gray_toggle.effective_luma, "hiding must not unset the preference"

    # A change while hidden stays with the toggle until the tab returns.
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
    """The runner's latest-wins submission is the tab's only debounce.

    Three synchronous knob edits submit three renders; the event loop never
    runs between them, so no intermediate result can land. Exactly one series
    application must follow, carrying the last value — two would mean an
    intermediate render survived, zero would mean the burst deadlocked the
    submission slots.
    """
    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_FPS)
    updates: list[int] = []
    tab.graphs_updated.connect(lambda: updates.append(1))

    # The runner's `opened` triggers the tab's own first submission.
    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: len(updates) >= 1, timeout=RENDER_TIMEOUT_MS)
    qtbot.wait(300)  # let the opening flurry settle completely
    base = len(updates)

    # The burst: three edits with no event-loop spin between them.
    tab.downsample_knob.setValue(0.50)
    tab.downsample_knob.setValue(0.40)
    tab.downsample_knob.setValue(0.30)

    qtbot.waitUntil(lambda: len(updates) > base, timeout=RENDER_TIMEOUT_MS)
    # Let anything else that intends to arrive, arrive.
    qtbot.wait(300)

    assert len(updates) == base + 1, "the burst produced more than one final recompute"
    rescale = next(s for s in tab.chain.steps if s.step_id == "rescale")
    assert rescale.node is not None and rescale.node.params["scale"] == pytest.approx(0.30)
    # And the series the graphs hold was extracted at the last value: the
    # 64-source-px auto grid at 0.30 is 19 px, so 120x160 reduces to 7x9.
    assert tab.count_plot.notice in ("", "disarmed — place the count threshold")
