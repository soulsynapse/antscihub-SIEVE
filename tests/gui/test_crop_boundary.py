

























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
from sieve.gui.crop_binding import CropState
from sieve.gui.document import ReplicateDocument, SourceHome
from sieve.gui.filter_tab import FilterTab
from sieve.gui.materialize_worker import MaterializeRequest
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.video_view import VideoView
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




NUDGED = ROI(x=30, y=20, width=100, height=80)
ELSEWHERE = ROI(x=400, y=300, width=100, height=80)
IDENTITY = "sha256:the-parent-as-it-was-when-the-cut-was-made"
SPAN = ClipRange(start=100, end=400)


WINDOW = ClipRange(start=0, end=6)


def _record(path: Path, *, roi: ROI = BOX, span: ClipRange = SPAN) -> CropArtifact:

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

    document.add_roi(BOX)
    document.set_source_home(
        SourceHome(video=tmp_path / "parent.mp4", project_dir=tmp_path, identity=IDENTITY)
    )


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









    def test_a_backed_box_moves_and_nothing_is_refused(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:
        del backed
        refusals: list[str] = []
        document.edit_refused.connect(refusals.append)

        document.set_roi(0, ELSEWHERE)

        assert document.at(0).roi == ELSEWHERE
        assert refusals == []



        assert document.crops != ()

    def test_set_all_squares_up_the_backed_row_too(
        self, document: ReplicateDocument, backed: CropArtifact
    ) -> None:

        del backed
        document.add_roi(ELSEWHERE)

        document.set_all_to_size(64, 64)

        assert (document.at(0).roi.width, document.at(0).roi.height) == (64, 64)
        assert (document.at(1).roi.width, document.at(1).roi.height) == (64, 64)

    def test_the_viewport_drags_a_backed_box(
        self, qapp: object, document: ReplicateDocument, backed: CropArtifact
    ) -> None:






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

        del backed
        refusals: list[str] = []
        document.edit_refused.connect(refusals.append)

        document.place_window(SPAN.start - 50, SPAN.end)

        assert document.clip == ClipRange(start=SPAN.start - 50, end=SPAN.end)
        assert refusals == []


def test_materialize_cuts_the_whole_source_not_the_window(
    tab: tuple[FilterTab, PreviewRunner], document: ReplicateDocument, tmp_path: Path
) -> None:







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

    filter_tab.materializer.start = refuse
    filter_tab.stack.source_card.buttons()[0].click()

    assert len(asked) == 1
    assert asked[0].span == ClipRange(start=0, end=SOURCE_FRAMES)


class TestDiscardLetsGoOfTheFile:







    def test_a_file_the_preview_is_reading_can_still_be_deleted(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path, tmp_path: Path
    ) -> None:







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

    def test_the_record_is_dropped_even_when_the_file_cannot_be_deleted(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tab: tuple[FilterTab, PreviewRunner],
        document: ReplicateDocument,
        backed: CropArtifact,
        tmp_path: Path,
    ) -> None:







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


@pytest.fixture
def tab(
    qtbot: QtBot, tmp_path: Path, document: ReplicateDocument
) -> Iterator[tuple[FilterTab, PreviewRunner]]:

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
