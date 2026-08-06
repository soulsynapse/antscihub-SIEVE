"""Item 7's claims, each a different way the wizard could betray its plan.

A Cancel that leaves residue makes every experiment in the wizard a
commitment; a provisional render that recomputes the upstream prefix pays the
cold-render price per hover and the mockups' strongest architectural
validation was that it must not; a disabled candidate that can be committed
means the wizard can break the chain after all.
"""

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
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.wizard_lifecycle import WIZARD_LIFECYCLE_SIGNALS, WizardLifecycle
from sieve.pipeline.preview import PreviewRender
from tests.conftest import FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_RATE, FIXTURE_WIDTH

pytestmark = pytest.mark.gui

RENDER_TIMEOUT_MS = 30_000

#: The seam between `normalize` and `block_signal` in the parity chain — the
#: insertion point every test here uses, chosen because both an enabled offer
#: (downsample) and both disable reasons are visible from it.
SEAM_ABOVE_EXTRACTION = 2

EXPECTED_LIFECYCLE_SIGNALS = (
    "chain_proposed",
    "hover_preview_requested",
    "hover_ended",
    "accepted",
    "cancelled",
    "seek_requested",
    "scrub_requested",
    "value_band_changed",
    "value_band_committed",
    "count_band_changed",
    "count_band_committed",
    "d_pressed",
    "d_released",
    "window_frames_changed",
    "centered_toggled",
)


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
    # The tab owns the detector thread, so it carries the same
    # shutdown obligation the player and the runner do. Without
    # this every tab built here leaks a QThread and the suite
    # wedges a few modules later.
    instance.shutdown()


def test_wizard_lifecycle_boundary_is_named_signals(qapp: object) -> None:
    """The extraction boundary is signals, not a hidden tab reference."""
    del qapp
    lifecycle = WizardLifecycle()
    try:
        assert WIZARD_LIFECYCLE_SIGNALS == EXPECTED_LIFECYCLE_SIGNALS
        assert all(name in WizardLifecycle.__dict__ for name in EXPECTED_LIFECYCLE_SIGNALS)
        assert lifecycle.parent() is None
        assert not {"_tab", "_filter_tab"} & vars(lifecycle).keys()
    finally:
        lifecycle.close()


def test_cancel_restores_the_exact_prior_state(qtbot: QtBot, tab: FilterTab) -> None:
    """Cancel/Esc is a full undo of everything the wizard session touched.

    The session deliberately touches all three kinds of state the claim
    names: the chain (a provisional step is adopted for real), its params (a
    settings-pane edit re-proposes), and the detector (the wizard's own D
    slider writes through the shared handlers). One snapshot value must
    restore all of it, because the tab holds exactly one value.
    """
    snapshot = tab.chain
    tab.stack.insert_requested.emit(SEAM_ABOVE_EXTRACTION)

    wizard = tab.wizard
    assert wizard is not None
    assert wizard.selected_entry is not None
    assert wizard.selected_entry.entry_id == "downsample"
    # The provisional step is really in the chain, dashed.
    card = tab.stack.card_for("downsample")
    assert card is not None and card.provisional
    assert tab.chain is not snapshot

    # A settings edit and a detector edit, both through the wizard's widgets.
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
    """Pass-back must reach the knobs, not only the document and the captions.

    The wizard's D slider is a separate widget instance sharing the tab's
    handlers, and its edits write the chain live — so when Add lands the net
    change in the document, the echo compares equal against the chain and
    must still sync the tab's widgets. Before it did, the document held the
    tuned value, the label said so, and the tab's slider displayed the
    pre-wizard number until something unrelated happened to re-sync it.
    """
    tab.stack.insert_requested.emit(SEAM_ABOVE_EXTRACTION)
    wizard = tab.wizard
    assert wizard is not None
    before = tab.chain.detector.window_frames
    wizard.d_slider.setValue(before + 60)

    wizard.accepted.emit()

    assert tab.wizard is None
    assert tab.chain.detector.window_frames == before + 60
    # The tab's own slider, not the wizard's (which is destroyed by now).
    assert tab._d_slider.value() == before + 60  # pyright: ignore[reportPrivateUsage]


def test_a_disabled_candidate_cannot_be_committed_by_any_input_path(tab: FilterTab) -> None:
    """The model's judgment holds at the last gate every input path crosses.

    `normalize` is already in the chain, so its row is disabled. Selecting it
    by API, clicking its row, and pressing Add must all leave the chain with
    exactly one normalize step — the wizard cannot break the chain, and a
    duplicate is one of the two ways it could.
    """
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
    """The wizard's preview is nearly free by construction (plan learning 3).

    The provisional pipeline differs from the rendered one only below the
    seam, and content-derived node keys mean every upstream output is served
    from the session's store. If this fails, every hover in the wizard pays
    a cold render — the exact cost the mockup cycle validated away.
    """
    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_RATE)
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
    assert tab.wizard is not None  # and its selection submitted a render

    qtbot.waitUntil(lambda: len(renders) > seen, timeout=RENDER_TIMEOUT_MS)
    provisional = renders[-1]
    # rescale and normalize sit above the seam: one stored output each per
    # frame must come back from the store rather than a kernel.
    frames = provisional.frames
    assert frames > 0
    assert provisional.from_cache >= 2 * frames
    assert provisional.reuse > 0.0
