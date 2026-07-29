











from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.bench.metrics import Recorder as MetricRecorder
from sieve.core.types import VideoMetadata
from sieve.gui.player import VideoPlayer
from sieve.gui.scrub_policy import SAMPLE_WINDOW, ScrubPolicy

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 5000
FRAME_TIMEOUT_MS = 5000


FIXTURE_STRIDE = 20


class Recorder:


    def __init__(self, player: VideoPlayer) -> None:
        self.indices: list[int] = []
        player.frame_changed.connect(self._on_frame)

    def _on_frame(self, index: int, image: QImage) -> None:
        del image
        self.indices.append(index)


def open_player(
    qtbot: QtBot, video: Path, policy: ScrubPolicy | None = None
) -> tuple[VideoPlayer, Recorder]:

    player = VideoPlayer(policy=policy)
    opened: list[VideoMetadata] = []
    player.opened.connect(opened.append)
    recorder = Recorder(player)

    player.open(str(video))
    qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)
    qtbot.waitUntil(lambda: bool(recorder.indices), timeout=FRAME_TIMEOUT_MS)
    return player, recorder


@pytest.fixture
def player(qtbot: QtBot, synthetic_video: Path) -> Iterator[VideoPlayer]:
    instance, _ = open_player(qtbot, synthetic_video)
    yield instance
    instance.shutdown()


@pytest.fixture
def impatient_policy() -> ScrubPolicy:






    return ScrubPolicy(budget_ms=0.0, coarse_interval_seconds=1.0)


class TestExactScrubbing:
    def test_a_scrub_shows_the_exact_frame_when_not_degraded(
        self, qtbot: QtBot, player: VideoPlayer
    ) -> None:
        player.scrub(13)
        qtbot.waitUntil(lambda: player.current_index == 13, timeout=FRAME_TIMEOUT_MS)

    def test_a_seek_shows_the_exact_frame(self, qtbot: QtBot, player: VideoPlayer) -> None:
        player.seek(27)
        qtbot.waitUntil(lambda: player.current_index == 27, timeout=FRAME_TIMEOUT_MS)

    def test_targets_are_clamped_to_the_source(self, qtbot: QtBot, player: VideoPlayer) -> None:
        player.seek(10_000)
        qtbot.waitUntil(lambda: player.current_index == 39, timeout=FRAME_TIMEOUT_MS)


class TestCoalescing:
    def test_a_burst_settles_on_the_final_target(self, qtbot: QtBot, synthetic_video: Path) -> None:
        instance, recorder = open_player(qtbot, synthetic_video)
        try:
            for index in range(1, 40):
                instance.scrub(index)
            qtbot.waitUntil(lambda: instance.current_index == 39, timeout=FRAME_TIMEOUT_MS)



            assert len(recorder.indices) < 40
            assert recorder.indices[-1] == 39
        finally:
            instance.shutdown()

    def test_a_pending_exact_request_survives_a_later_cached_scrub(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:






        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)

            instance.scrub(FIXTURE_STRIDE)
            qtbot.waitUntil(
                lambda: instance.current_index == FIXTURE_STRIDE, timeout=FRAME_TIMEOUT_MS
            )

            instance.seek(33)
            instance.scrub(FIXTURE_STRIDE)

            qtbot.waitUntil(lambda: instance.current_index == 33, timeout=FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()


class TestSourceChange:








    def test_a_frame_decoded_before_a_close_is_not_shown(
        self, qtbot: QtBot, synthetic_video: Path
    ) -> None:
        instance, recorder = open_player(qtbot, synthetic_video)
        try:
            instance.seek(30)
            instance.close()

            qtbot.wait(300)
            assert recorder.indices == [0], "a closed player displayed a frame"
            assert instance.current_index == 0
        finally:
            instance.shutdown()

    def test_a_frame_decoded_before_a_reopen_is_not_shown(
        self, qtbot: QtBot, synthetic_video: Path
    ) -> None:
        instance, recorder = open_player(qtbot, synthetic_video)
        try:
            instance.seek(30)

            opened: list[VideoMetadata] = []
            instance.opened.connect(opened.append)
            instance.open(str(synthetic_video))
            qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)
            qtbot.waitUntil(lambda: len(recorder.indices) > 1, timeout=FRAME_TIMEOUT_MS)

            qtbot.wait(300)
            assert recorder.indices == [0, 0], "frame 30 of the old source was painted"




            instance.scrub(30)
            assert instance.current_index == 0
        finally:
            instance.shutdown()


def degrade(qtbot: QtBot, player: VideoPlayer) -> None:

    for index in range(1, SAMPLE_WINDOW + 1):
        player.scrub(index)
        qtbot.waitUntil(lambda: player.current_index == index, timeout=FRAME_TIMEOUT_MS)
    assert player.is_scrub_degraded


class TestDegradation:
    def test_sustained_slow_scrubbing_degrades_and_announces_once(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:
        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            announcements: list[int] = []
            instance.scrub_degraded.connect(lambda: announcements.append(1))

            degrade(qtbot, instance)
            assert announcements == [1]

            for index in (7, 11, 19):
                instance.scrub(index)
                qtbot.wait(20)
            assert announcements == [1], "the notice must not repeat"
        finally:
            instance.shutdown()

    def test_degraded_scrubs_snap_to_the_grid(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:
        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            instance.scrub(23)
            qtbot.waitUntil(
                lambda: instance.current_index == FIXTURE_STRIDE, timeout=FRAME_TIMEOUT_MS
            )
        finally:
            instance.shutdown()

    def test_release_lands_exactly_however_coarse_the_drag_was(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:

        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            instance.scrub(23)
            qtbot.waitUntil(
                lambda: instance.current_index == FIXTURE_STRIDE, timeout=FRAME_TIMEOUT_MS
            )

            instance.seek(23)
            qtbot.waitUntil(lambda: instance.current_index == 23, timeout=FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

    def test_a_warmed_grid_point_needs_no_decode(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:

        instance, recorder = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            instance.scrub(23)
            qtbot.waitUntil(
                lambda: instance.current_index == FIXTURE_STRIDE, timeout=FRAME_TIMEOUT_MS
            )
            instance.seek(0)
            qtbot.waitUntil(lambda: instance.current_index == 0, timeout=FRAME_TIMEOUT_MS)

            before = len(recorder.indices)
            instance.scrub(23)


            assert instance.current_index == FIXTURE_STRIDE
            assert len(recorder.indices) == before + 1
        finally:
            instance.shutdown()


class TestPreferences:
    def test_forbidding_degradation_restores_exact_scrubbing(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:
        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            impatient_policy.set_allow_degrade(False)

            instance.scrub(23)
            qtbot.waitUntil(lambda: instance.current_index == 23, timeout=FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

    def test_opening_a_new_source_starts_exact_again(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:

        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            instance.close()
            assert not instance.is_scrub_degraded
        finally:
            instance.shutdown()


class TestMetrics:
    def test_a_scrub_round_trip_reaches_the_bus(self, qtbot: QtBot, synthetic_video: Path) -> None:










        bus = MetricBus()
        recorder = MetricRecorder()
        bus.subscribe(recorder.record)

        instance = VideoPlayer(metrics=bus)
        opened: list[VideoMetadata] = []
        instance.opened.connect(opened.append)
        instance.open(str(synthetic_video))
        qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)

        try:

            assert len(recorder) == 0

            instance.scrub(23)
            qtbot.waitUntil(lambda: instance.current_index == 23, timeout=FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

        assert recorder.keys == ("scrub_to_repaint",)
        assert recorder.median_ms("scrub_to_repaint") > 0.0
