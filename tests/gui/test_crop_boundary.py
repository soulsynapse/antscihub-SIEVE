"""The source boundary: what the card says, and what a crop at rest does not hold.

Four claims, each failing for its own reason.

**Stale is not absent, on screen and not only in the model.** The reading was
pinned when `pipeline/crop_binding.py` landed; what is new here is that the card
renders the two differently — a user who cannot tell an orphaned artifact from
one that was never cut re-cuts a file they already have, which is a minute of
encoding rule 6 exists to prevent.

**Nothing is held still.** An artifact used to freeze the box it was cut at and
the window it was cut over, and the freeze was removed: an acceleration that
refuses the tuning it exists to accelerate has inverted its own purpose. Every
edit those gates refused now goes through, and what the user gets back is a
`STALE` card rather than a refusal — which is the report, not the gate.

**The cut covers the whole source, not the working window.** Moving the window
is the most ordinary gesture on the timeline, and a window-shaped cut would put
a re-encode behind it. This is what makes removing the clip freeze safe rather
than merely permissive.

**Discard lets go of the file before it deletes it.** The render thread holds a
pool of captures over an artifact it is serving, and on Windows an open handle
is an unlink that fails — which is the whole of "discard does nothing".
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, QSettings
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.types import ROI
from sieve.gui.chain_stack import SourceCard
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.materialize_worker import MaterializeRequest
from sieve.gui.preferences import Preferences
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.source_boundary import SourceBoundary
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.video_view import VideoView
from sieve.pipeline.crop_binding import CropState
from sieve.pipeline.source_home import SourceHome
from tests.gui import qt_input
from tests.gui.conftest import SOURCE_FRAMES, answering
from tests.gui.test_preview_runner import (
    RENDER_TIMEOUT_MS,
    Landings,
    downsampling,
    opened_runner,
)

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

#: A window well inside the 40-frame fixture, for the runner tests below.
WINDOW = ClipRange(start=0, end=6)


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

    def test_a_matching_record_reads_at_rest(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        backing = document.crop_backing(0)

        assert backing.state is CropState.AT_REST
        assert backing.artifact == backed

    def test_a_moved_box_reads_stale_and_not_absent(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """The collapse rule 6 forbids, asserted from the state *and* the reason.

        A box that has moved out from under its record leaves a file on disk
        that nothing serves. Reporting that as `ABSENT` would offer the user a
        fresh cut of footage they have already cut.
        """
        del backed
        document.set_roi(0, NUDGED)

        backing = document.crop_backing(0)
        assert backing.state is CropState.STALE
        assert backing.state is not CropState.ABSENT
        assert backing.artifact is not None
        assert "moved" in backing.reason

    def test_a_window_past_the_cut_reads_stale_with_the_span(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        del backed
        document.place_window(SPAN.start, SPAN.end + 50)

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


class TestNothingIsHeldStill:
    """The removed freeze, asserted edit by edit rather than from one flag.

    Geometry moves three ways — a drag, a typed number, set-all — and the gate
    that used to refuse them sat at the last of the three. So each is driven
    here on its own, and each ends with the edit having *happened*: a test that
    only asked the document whether it was frozen would pass against a document
    that still refused the drag.
    """

    def test_a_backed_box_moves_and_nothing_is_refused(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        del backed
        refusals: list[str] = []
        document.edit_refused.connect(refusals.append)

        document.set_roi(0, ELSEWHERE)

        assert document.at(0).roi == ELSEWHERE
        assert refusals == []
        # The record is still on the books and still on disk. What the move
        # changed is only whether it backs anything — which is what the card
        # reads, and `test_a_moved_box_reads_stale_and_not_absent` pins.
        assert document.crops != ()

    def test_set_all_squares_up_the_backed_row_too(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """One artifact must not be a hole in a rack."""
        del backed
        document.add_roi(ELSEWHERE)

        document.set_all_to_size(64, 64)

        assert (document.at(0).roi.width, document.at(0).roi.height) == (64, 64)
        assert (document.at(1).roi.width, document.at(1).roi.height) == (64, 64)

    def test_the_viewport_drags_a_backed_box(
        self, qapp: object, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """Driven as the gesture, because the handles were removed on the widget.

        A press inside the selection and a press on its corner both have to
        emit an adjustment. Reading a flag off the document would not notice a
        viewport that still refused to grow handles.
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
        assert adjustments, "a press inside the selection moves it"
        adjustments.clear()

        qt_input.drag(view, box.topLeft(), box.topLeft() + QPointF(40.0, 40.0))
        assert adjustments, "a press on the corner resizes it"

    def test_the_window_moves_outside_the_span_the_cut_covers(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        """The gesture this whole change is about, and it is not refused."""
        del backed
        refusals: list[str] = []
        document.edit_refused.connect(refusals.append)

        document.place_window(SPAN.start - 50, SPAN.end)

        assert document.clip == ClipRange(start=SPAN.start - 50, end=SPAN.end)
        assert refusals == []


def test_materialize_cuts_the_whole_source_not_the_window(
    tab: tuple[FilterTab, PreviewRunner], document: ReplicateDocument, tmp_path: Path
) -> None:
    """The span on the request, taken off the request rather than off the file.

    Intercepted at the runner rather than run: what is under test is which span
    the tab asks for, and letting the encoder answer would pin the same claim
    behind a minute of decode. The window is deliberately narrow and nowhere
    near the source's ends, so a request that carried it would be unmistakable.
    """
    filter_tab, _ = tab
    document.add_roi(BOX)
    document.set_source_home(
        SourceHome(video=tmp_path / "parent.mp4", project_dir=tmp_path, identity=IDENTITY)
    )
    document.place_window(300, 400)
    asked: list[MaterializeRequest] = []

    def refuse(request: MaterializeRequest) -> bool:
        asked.append(request)
        return False

    filter_tab.materializer.start = refuse  # type: ignore[method-assign]
    filter_tab.stack.source_card.buttons()[0].click()

    assert len(asked) == 1
    assert asked[0].span == ClipRange(start=0, end=SOURCE_FRAMES)


class TestDiscardLetsGoOfTheFile:
    """The delete, and the handle that used to stop it.

    Driven through the real runner over real footage, because the failure lives
    entirely in the file handles: every model-level test of discard passed
    while the gesture did nothing in the application.
    """

    def test_a_file_the_preview_is_reading_can_still_be_deleted(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """On Windows this is the bug; elsewhere it passes for free.

        POSIX unlinks an open file happily, so what this pins on Linux is only
        that `release_files` is harmless. The claim it is here for is the
        Windows one — an open capture is a refusal to unlink, and the discard
        reported that it could not delete and left the record standing.
        """
        del qapp
        copy = tmp_path / "footage.mp4"
        shutil.copy(synthetic_video, copy)
        runner = opened_runner(qtbot, copy)
        landings = Landings(runner)
        try:
            assert runner.request_render(downsampling(), WINDOW)
            qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

            runner.set_paused(True)
            runner.release_files()
            copy.unlink()
        finally:
            runner.shutdown()

        assert not copy.exists()

    def test_the_footage_stays_open_and_the_next_render_rebuilds(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path
    ) -> None:
        """`release_files` is not `close`.

        The session and the reader go; the source does not. A release that
        unloaded the footage would leave the tab with nothing to resubmit
        against after a discard, which is a black viewport until the user
        reopens the project.
        """
        del qapp
        runner = opened_runner(qtbot, synthetic_video)
        landings = Landings(runner)
        try:
            assert runner.request_render(downsampling(), WINDOW)
            qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

            runner.set_paused(True)
            runner.release_files()
            runner.set_paused(False)

            assert runner.is_open
            assert runner.request_render(downsampling(), WINDOW)
            qtbot.waitUntil(lambda: len(landings.finished) == 2, timeout=RENDER_TIMEOUT_MS)
        finally:
            runner.shutdown()

        assert landings.failures == []

    def test_the_hold_reaches_the_runner_before_the_unlink(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tab: tuple[FilterTab, PreviewRunner],
        document: ReplicateDocument,
        backed: CropArtifact,
        tmp_path: Path,
    ) -> None:
        """The ordering the seam has to preserve, asserted as an order.

        `render_hold(True)` crosses from the boundary controller to the tab and
        has to have *run* by the time the next statement deletes the file. A
        queued connection would satisfy every other assertion in this file — the
        record drops, the message is right — and leave the unlink racing the
        release, which is the bug reported as "discard does nothing".
        """
        del backed
        filter_tab, runner = tab
        document.select(0)
        monkeypatch.setattr(QMessageBox, "question", answering(QMessageBox.StandardButton.Discard))
        order: list[str] = []
        real_unlink = Path.unlink
        real_release = runner.release_files

        def watched_release() -> None:
            order.append(f"release paused={runner.paused}")
            real_release()

        def watched_unlink(self: Path, **kwargs: object) -> None:
            order.append("unlink")
            real_unlink(self, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(runner, "release_files", watched_release)
        monkeypatch.setattr(Path, "unlink", watched_unlink)

        filter_tab.stack.source_card.buttons()[2].click()

        assert order == ["release paused=True", "unlink"]
        assert document.crops == ()
        assert not (tmp_path / "arena-luma-100-400.mkv").exists()
        assert not runner.paused, "the hold is given back"

    def test_the_record_is_dropped_even_when_the_file_cannot_be_deleted(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tab: tuple[FilterTab, PreviewRunner],
        document: ReplicateDocument,
        backed: CropArtifact,
        tmp_path: Path,
    ) -> None:
        """A delete that fails is reported, not treated as a veto.

        The record is what makes the file serve, and dropping it is the whole of
        what was asked for — leaving it standing because a lock outlived the
        release would put the user back where the bug had them. The surviving
        file is named in the message; it is in a folder they can open.
        """
        del backed
        filter_tab, _ = tab
        document.select(0)
        monkeypatch.setattr(QMessageBox, "question", answering(QMessageBox.StandardButton.Discard))

        def locked(_self: Path, **_kwargs: object) -> None:
            raise OSError("in use")

        monkeypatch.setattr(Path, "unlink", locked)
        messages: list[str] = []
        filter_tab.status_message.connect(messages.append)

        filter_tab.stack.source_card.buttons()[2].click()

        assert document.crops == ()
        assert messages and "arena-luma-100-400.mkv" in messages[-1]
        assert (tmp_path / "arena-luma-100-400.mkv").exists()


def test_the_boundary_runs_the_discard_with_no_tab_in_the_room(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    document: ReplicateDocument,
    backed: CropArtifact,
    tmp_path: Path,
) -> None:
    """The seam, stated as a test rather than left to a reading.

    A `FilterTab` is a player, a runner, a detector thread and 2,100 lines the
    source boundary has nothing to say about. What this pins is that none of it
    is reachable from the controller: the whole gesture runs over a document and
    a card, and what would have been a reach into the tab leaves as a signal.
    """
    del backed
    card = SourceCard()
    qtbot.addWidget(card)
    boundary = SourceBoundary(document, card)
    document.select(0)
    monkeypatch.setattr(QMessageBox, "question", answering(QMessageBox.StandardButton.Discard))
    holds: list[bool] = []
    stale: list[None] = []
    boundary.render_hold.connect(holds.append)
    boundary.render_stale.connect(lambda: stale.append(None))
    try:
        card.buttons()[2].click()
    finally:
        boundary.shutdown()

    assert holds == [True, False]
    assert len(stale) == 1
    assert document.crops == ()
    assert not (tmp_path / "arena-luma-100-400.mkv").exists()
    assert card.state is CropState.ABSENT, "the card repaints itself, off the document"


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
