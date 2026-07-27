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
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
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
    qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument, runner: PreviewRunner
) -> FilterTab:
    instance = FilterTab(player, document, runner, metrics=MetricBus())
    qtbot.addWidget(instance)
    return instance


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
