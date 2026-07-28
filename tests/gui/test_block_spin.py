"""The Block spin box refuses the sizes that stall the density graph.

Refusing at the control rather than computing slowly is rule 6's preference,
and the defect it closes is a *gesture*: one wheel notch from a comfortable
block edge multiplies the block count, because the value is an edge in pixels
and everything downstream is counted in blocks. So what has to be pinned is
that the refused range cannot be *entered*, by any of the three paths a value
arrives through, rather than merely that some validator would reject it.

The three tests below fail for three different reasons: a hole that is not
stepped over, a hole that is typed into, and a hole that swallows the auto
mode sitting under it.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.types import ROI
from sieve.filters.block_signal import min_block_for
from sieve.gui.block_spin import AUTO, BlockSpinBox
from sieve.gui.density_plot import MAX_BLOCKS
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner

pytestmark = pytest.mark.gui

FLOOR = 15


@pytest.fixture
def spin(qtbot: QtBot) -> BlockSpinBox:
    widget = BlockSpinBox()
    qtbot.addWidget(widget)
    widget.setRange(0, 256)
    widget.set_floor(FLOOR, reason="too many blocks")
    return widget


class TestTheRefusedRangeCannotBeSteppedInto:
    def test_stepping_down_stops_at_the_floor_before_reaching_auto(
        self, spin: BlockSpinBox
    ) -> None:
        """The wheel is the whole defect, and this is one notch of it.

        `wheel_steps.py` routes every detent through `stepBy`, accelerating a
        run — so a single crank asks for a step of several, which must land on
        the floor rather than inside the hole it crosses.
        """
        spin.setValue(FLOOR + 1)
        spin.stepBy(-1)
        assert spin.value() == FLOOR

        spin.setValue(FLOOR + 5)
        spin.stepBy(-9)
        assert spin.value() == FLOOR

    def test_auto_is_still_reachable_from_the_floor_and_leads_back_to_it(
        self, spin: BlockSpinBox
    ) -> None:
        """The refusal is a hole, not a floor: `0 = auto` lives under it.

        A bound implemented as `setMinimum` would have taken auto with it, and
        auto is the resting default — the one value whose block count is a
        property of the source rather than of the knob.
        """
        spin.setValue(FLOOR)
        spin.stepBy(-1)
        assert spin.value() == AUTO

        spin.stepBy(1)
        assert spin.value() == FLOOR

    def test_no_step_lands_inside_the_hole(self, spin: BlockSpinBox) -> None:
        """Every start and every step size, exhaustively over the small range."""
        for start in range(0, 40):
            for steps in (-9, -3, -1, 1, 3, 9):
                spin.setValue(start if start == AUTO or start >= FLOOR else FLOOR)
                spin.stepBy(steps)
                assert not (AUTO < spin.value() < FLOOR), f"{start} + {steps} landed inside"


class TestATypedSizeCommitsAsSomethingLegal:
    def test_a_size_inside_the_hole_snaps_up_to_the_floor(self, spin: BlockSpinBox) -> None:
        """Typed input goes through `valueFromText`, not `stepBy`.

        Snapping up rather than rejecting the keystroke: a spin box that
        refused to interpret its own line edit would leave the user with a
        field they cannot commit and no statement of why.
        """
        spin.lineEdit().setText("3")
        spin.interpretText()
        assert spin.value() == FLOOR

    def test_a_legal_size_is_left_exactly_alone(self, spin: BlockSpinBox) -> None:
        spin.lineEdit().setText("64")
        spin.interpretText()
        assert spin.value() == 64


class TestTheFloorStatesItselfAndDoesNotRewriteHistory:
    def test_the_tooltip_carries_the_bound_and_the_reason(self, spin: BlockSpinBox) -> None:
        """Rule 6's other half: a refusal a user cannot read is a broken knob."""
        assert str(FLOOR) in spin.toolTip()
        assert "too many blocks" in spin.toolTip()

    def test_a_value_already_below_a_new_floor_is_not_silently_raised(
        self, spin: BlockSpinBox
    ) -> None:
        """A saved project's block size is a real parameter, not an entry.

        Raising it here would show a number the chain does not hold — a
        control looking more settled than it is. The stall such a value causes
        is refused at the surface (`density_plot.set_series`) instead.
        """
        spin.set_floor(1)
        spin.setValue(2)
        spin.set_floor(FLOOR, reason="too many blocks")
        assert spin.value() == 2


class TestTheFloorIsDerivedFromTheReplicateUnderTuning:
    """The bound is on *B*, and B depends on the crop — so the floor cannot be
    a constant in the widget. These go through the tab, because the coupling
    being claimed is between a document's ROI and a control's refusal."""

    @pytest.fixture
    def player(self, qapp: object) -> Iterator[VideoPlayer]:
        del qapp
        instance = VideoPlayer()
        yield instance
        instance.shutdown()

    @pytest.fixture
    def preview(self, qapp: object) -> Iterator[PreviewRunner]:
        del qapp
        instance = PreviewRunner(metrics=MetricBus())
        yield instance
        instance.shutdown()

    @pytest.fixture
    def tab(
        self,
        qtbot: QtBot,
        player: VideoPlayer,
        document: ReplicateDocument,
        preview: PreviewRunner,
    ) -> Iterator[FilterTab]:
        instance = FilterTab(player, document, preview, metrics=MetricBus())
        qtbot.addWidget(instance)
        yield instance
        instance.shutdown()

    def test_a_smaller_crop_admits_a_smaller_block_size(
        self, tab: FilterTab, document: ReplicateDocument
    ) -> None:
        """Two replicates, two floors, and the small one must be lower.

        The failure this catches is a floor derived once at construction: the
        tab would then refuse over a postage-stamp crop everything it refuses
        over the whole frame, which is a control forbidding block sizes the
        density surface would have binned in single-digit milliseconds.
        """
        document.add_roi(ROI(x=0, y=0, width=1000, height=800))
        document.select(0)
        whole = tab._block.floor  # pyright: ignore[reportPrivateUsage]

        document.add_roi(ROI(x=0, y=0, width=100, height=80))
        document.select(1)
        small = tab._block.floor  # pyright: ignore[reportPrivateUsage]

        assert small < whole
        assert whole == min_block_for(800, 1000, MAX_BLOCKS)
        assert small == min_block_for(80, 100, MAX_BLOCKS)
