"""The source boundary: what the card says, and what a crop at rest holds still.

Four claims, each failing for its own reason.

**Stale is not absent, on screen and not only in the model.** The reading was
pinned when `gui/crop_binding.py` landed; what is new here is that the card
renders the two differently — a user who cannot tell an orphaned artifact from
one that was never cut re-cuts a file they already have, which is a minute of
encoding rule 6 exists to prevent.

**The freeze binds, and it binds at the last gate.** A frozen box is refused by
the *document*, not merely made hard to grab in the viewport, because the
viewport is one of three ways geometry moves (a drag, a typed number, set-all)
and a guard on the gesture is a guard on one of them.

**Faded means frozen.** The same replicate that refuses the edit also grows no
handles, and the timeline cannot be dragged out of the span the cut covers. A
control that looked live and then snapped back would be the mirror failure of
the one above.

**Discard is the way out, and it is the only way out.** After it, both freezes
lift — which is what makes refusing them safe in the first place.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, QSettings
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.types import ROI
from sieve.gui.chain_stack import SourceCard
from sieve.gui.crop_binding import CropState
from sieve.gui.document import ReplicateDocument, SourceHome
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.timeline_bar import TimelineStrip
from sieve.gui.video_view import VideoView
from tests.gui import qt_input

pytestmark = pytest.mark.gui

BOX = ROI(x=10, y=20, width=100, height=80)
#: A nudge, not a relocation. Attribution of an orphaned record is geometric
#: (`crop_binding`), so a box that still overlaps its old cut is the case where
#: the card has something to say — a box moved clear across the frame is
#: correctly attributed to nobody, which is a claim that module already pins.
NUDGED = ROI(x=30, y=20, width=100, height=80)
ELSEWHERE = ROI(x=400, y=300, width=100, height=80)
IDENTITY = "sha256:the-parent-as-it-was-when-the-cut-was-made"
SPAN = ClipRange(start=100, end=400)


def _record(path: Path, *, roi: ROI = BOX, span: ClipRange = SPAN) -> CropArtifact:
    """A record of a cut whose file is really there."""
    path.write_bytes(b"not a video, but a file that exists")
    return CropArtifact(
        path=path.name,
        roi=roi,
        format="luma",
        span=span,
        cut_from=IDENTITY,
        decoder="test-decoder",
    )


@pytest.fixture
def backed(document: ReplicateDocument, tmp_path: Path) -> CropArtifact:
    """One replicate at `BOX`, backed by a matching record over `SPAN`."""
    document.add_roi(BOX)
    document.set_source_home(
        SourceHome(video=tmp_path / "parent.mp4", project_dir=tmp_path, identity=IDENTITY)
    )
    # The clip has to sit inside the cut, or the record is stale for the window
    # rather than at rest — which is a different test, one class down.
    document.place_window(SPAN.start, SPAN.end)
    artifact = _record(tmp_path / "arena-luma-100-400.mkv")
    document.register_crop(artifact)
    assert document.decodes_luma(), "the empty graph decodes luma; this fixture assumes it"
    return artifact


class TestTheFourStates:
    def test_no_record_reads_absent(self, document: ReplicateDocument, tmp_path: Path) -> None:
        document.add_roi(BOX)
        document.set_source_home(
            SourceHome(video=tmp_path / "parent.mp4", project_dir=tmp_path, identity=IDENTITY)
        )

        assert document.crop_backing(0).state is CropState.ABSENT
        assert not document.is_crop_frozen(0)

    def test_a_matching_record_reads_at_rest(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        backing = document.crop_backing(0)

        assert backing.state is CropState.AT_REST
        assert backing.artifact == backed
        assert backing.frozen

    def test_a_moved_box_reads_stale_and_not_absent(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """The collapse rule 6 forbids, asserted from the state *and* the reason.

        A box that has moved out from under its record leaves a file on disk
        that nothing serves. Reporting that as `ABSENT` would offer the user a
        fresh cut of footage they have already cut.
        """
        del backed
        # Not through `set_roi`: that path is refused while the record backs the
        # replicate, which is the next class's claim. This is the state the
        # document reaches by a discard-and-move, or by loading a project whose
        # geometry was edited elsewhere.
        document.apply_replace(0, document.at(0).with_roi(NUDGED))

        backing = document.crop_backing(0)
        assert backing.state is CropState.STALE
        assert backing.state is not CropState.ABSENT
        assert backing.artifact is not None
        assert "moved" in backing.reason
        assert not backing.frozen

    def test_a_window_past_the_cut_reads_stale_with_the_span(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        del backed
        # Placed directly, because `place_window` is refused past the fence —
        # this is the state a loaded project can be in, and the card has to
        # explain it rather than merely decline to serve from it.
        document.apply_clip(ClipRange(start=SPAN.start, end=SPAN.end + 50))

        backing = document.crop_backing(0)
        assert backing.state is CropState.STALE
        assert f"[{SPAN.start}:{SPAN.end})" in backing.reason

    def test_the_card_renders_absent_and_stale_differently(self, qapp: object) -> None:
        """Assert on state and affordances, never on pixels."""
        del qapp
        card = SourceCard()
        materialize, cancel, discard = card.buttons()

        card.set_state(CropState.ABSENT, subject="arena", detail="not cut yet")
        assert (materialize.isVisibleTo(card), discard.isVisibleTo(card)) == (True, False)
        absent_offer = materialize.text()

        card.set_state(CropState.STALE, subject="arena", detail="the region has moved since")
        assert (materialize.isVisibleTo(card), discard.isVisibleTo(card)) == (True, True)
        assert materialize.text() != absent_offer
        assert card.detail == "the region has moved since"

        card.set_state(CropState.AT_REST, subject="arena", detail="at rest")
        assert (materialize.isVisibleTo(card), discard.isVisibleTo(card)) == (False, True)

        card.set_state(CropState.WRITING, subject="arena", detail="cutting")
        assert cancel.isVisibleTo(card)
        assert not materialize.isVisibleTo(card)


class TestTheFreeze:
    def test_a_frozen_box_refuses_the_edit_and_says_why(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        del backed
        refusals: list[str] = []
        document.edit_refused.connect(refusals.append)
        before = document.at(0).roi

        document.set_roi(0, ELSEWHERE)

        assert document.at(0).roi == before
        assert refusals and "Discard" in refusals[0]

    def test_set_all_skips_the_frozen_row_and_squares_up_the_rest(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """One artifact must not veto a rack. The other arenas still move."""
        del backed
        document.add_roi(ELSEWHERE)
        frozen_before = document.at(0).roi

        document.set_all_to_size(64, 64)

        assert document.at(0).roi == frozen_before
        assert (document.at(1).roi.width, document.at(1).roi.height) == (64, 64)

    def test_the_viewport_will_not_drag_a_frozen_box(
        self, qapp: object, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """Driven as the gesture, not read off the widget's state.

        The claim is that the drag does not happen — the same shape as
        `test_an_unselected_box_has_no_handles`, one condition over. A frozen
        selection emits no adjustment from a press inside it and none from its
        corner either, which is the handles being gone rather than merely
        unpainted.
        """
        del qapp, backed
        view = VideoView()
        view.resize(400, 320)
        view.set_source_size(document.source_size)
        view.set_replicates(document.all())
        view.set_selected(0)
        adjustments: list[ROI] = []

        def record(_row: int, roi: ROI, _token: int, _verb: str) -> None:
            adjustments.append(roi)

        view.roi_adjusted.connect(record)
        box = view.to_widget(BOX)
        qt_input.drag(view, box.center(), box.center() + QPointF(40.0, 0.0))
        assert adjustments, "an unfrozen selection drags"
        adjustments.clear()

        view.set_frozen_rows(document.frozen_rows())

        qt_input.drag(view, box.center(), box.center() + QPointF(40.0, 0.0))
        qt_input.drag(view, box.topLeft(), box.topLeft() + QPointF(40.0, 40.0))
        assert adjustments == []

    def test_the_clip_cannot_leave_the_span_the_cut_covers(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        del backed
        refusals: list[str] = []
        document.edit_refused.connect(refusals.append)

        document.place_window(SPAN.start - 10, SPAN.end)
        assert document.clip == SPAN
        assert refusals

        # And inside it is still ordinary editing: the freeze is a fence, not a
        # lock on the control.
        document.place_window(SPAN.start + 10, SPAN.end - 10)
        assert document.clip == ClipRange(start=SPAN.start + 10, end=SPAN.end - 10)

    def test_the_strip_clamps_a_drag_to_the_fence(self, qapp: object) -> None:
        """A handle dragged to frame 0 stops at the fence, mid-drag.

        Asserted on the draft rather than on the release, which is the point:
        a window that travelled past the fence and snapped back on release
        would have looked live for the length of the drag.
        """
        del qapp
        strip = TimelineStrip()
        strip.resize(1000, 40)
        strip.set_source_frames(1000)
        strip.set_timebase(30.0)
        strip.set_window(ClipRange(start=150, end=250))
        strip.set_frozen_span(SPAN)
        centre = strip.header_rect().center()
        qt_input.press(strip, centre)

        qt_input.move(strip, QPointF(0.0, centre.y()))

        dragged = strip.shown_window
        assert dragged is not None
        assert dragged.start >= SPAN.start
        assert dragged.end <= SPAN.end

    def test_discard_releases_both_freezes(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        document.discard_crop(backed)

        assert document.crops == ()
        assert document.frozen_rows() == frozenset()
        assert document.frozen_clip_span() is None
        document.set_roi(0, ELSEWHERE)
        assert document.at(0).roi == ELSEWHERE
        document.place_window(0, 300)
        assert document.clip == ClipRange(start=0, end=300)


@pytest.fixture
def tab(
    qtbot: QtBot, tmp_path: Path, document: ReplicateDocument
) -> Iterator[tuple[FilterTab, PreviewRunner]]:
    """A filter tab over its own player and runner, for the write-pass arc."""
    player = VideoPlayer()
    runner = PreviewRunner(metrics=MetricBus())
    preferences = Preferences(QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat))
    instance = FilterTab(player, document, runner, metrics=MetricBus(), preferences=preferences)
    qtbot.addWidget(instance)
    yield instance, runner
    instance.shutdown()
    runner.shutdown()
    player.shutdown()


def test_a_write_pauses_the_preview_and_a_failure_gives_it_back(
    qtbot: QtBot,
    tab: tuple[FilterTab, PreviewRunner],
    document: ReplicateDocument,
    tmp_path: Path,
) -> None:
    """Rule 5's borrowing, from both ends.

    The pause is taken *before* the worker is handed the request — a render
    still in flight when a sequential decode of the same footage begins is the
    bandwidth wall the artifact exists to remove — and it is given back on every
    exit, failure included. A write that failed with the preview still paused
    would leave a tab that renders nothing and says nothing about why.

    The parent is deliberately missing, so the failure is real, immediate, and
    needs no footage: what is under test is the arc, not the encoder.
    """
    filter_tab, runner = tab
    document.add_roi(BOX)
    document.set_source_home(
        SourceHome(video=tmp_path / "not-here.mp4", project_dir=tmp_path, identity=IDENTITY)
    )

    with qtbot.waitSignal(filter_tab.materializer.failed, timeout=10_000):
        filter_tab.stack.source_card.buttons()[0].click()
        assert runner.paused

    assert not runner.paused
    assert document.crops == ()
    assert not any(tmp_path.glob("*.mkv"))


def test_a_window_longer_than_the_fence_is_cut_down_to_it(qapp: object) -> None:
    """The one case where the clamp changes a length, and it cannot not.

    No window of 400 frames fits inside a 100-frame fence, so a drag that was
    already under way has to end somewhere legal. This state is only reachable
    from a project loaded with a clip outside its own cut — the state the card
    is reporting as stale in the same moment.
    """
    del qapp
    strip = TimelineStrip()
    strip.resize(1000, 40)
    strip.set_source_frames(1000)
    strip.set_timebase(30.0)
    strip.set_window(ClipRange(start=300, end=700))
    strip.set_frozen_span(ClipRange(start=100, end=200))
    centre = strip.header_rect().center()

    qt_input.press(strip, centre)
    qt_input.move(strip, QPointF(0.0, centre.y()))

    dragged = strip.shown_window
    assert dragged is not None
    assert (dragged.start, dragged.end) == (100, 200)
