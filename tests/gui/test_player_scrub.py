"""The player's scrub path: coalescing, the cache, and degrading to coarse mode.

Driven through the real decode thread against the synthetic video, because the
things worth pinning here are ordering properties between the GUI thread and
that thread, and a fake decoder would test the fake's ordering instead.

Degradation is exercised by injecting a policy with an unmeetably low budget.
The alternative — waiting for the real budget to be missed — only fires on a
machine slow enough to miss it, which is to say the test would pass by not
running on exactly the machines that matter.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.bench.metrics import Recorder as MetricRecorder
from sieve.core.types import VideoMetadata
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.transport.scrub_policy import SAMPLE_WINDOW, ScrubPolicy

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 5000
FRAME_TIMEOUT_MS = 5000

#: The synthetic fixture is 20 fps, so a 1 s grid is a stride of 20 frames.
FIXTURE_STRIDE = 20


class Recorder:
    """Collects the frames the player decided to display, in order."""

    def __init__(self, player: VideoPlayer) -> None:
        self.indices: list[int] = []
        player.frame_changed.connect(self._on_frame)

    def _on_frame(self, index: int, image: QImage) -> None:
        del image
        self.indices.append(index)


def open_player(
    qtbot: QtBot, video: Path, policy: ScrubPolicy | None = None
) -> tuple[VideoPlayer, Recorder]:
    """An opened player parked on frame 0, with its first frame already shown."""
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
    """A policy that degrades as soon as it has seen a full window of scrubs.

    A zero budget means every real decode is over it, so `SAMPLE_WINDOW`
    scrubs is both necessary and sufficient — the same rule the real policy
    follows, at a threshold this machine cannot help but cross.
    """
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

            # The point of coalescing: the frames nobody would have seen are
            # discarded rather than queued. Forty requests, far fewer displays.
            assert len(recorder.indices) < 40
            assert recorder.indices[-1] == 39
        finally:
            instance.shutdown()

    def test_a_pending_exact_request_survives_a_later_cached_scrub(
        self, qtbot: QtBot, synthetic_video: Path, impatient_policy: ScrubPolicy
    ) -> None:
        """A released slider is a commitment; a drag position is not.

        The hazard this pins: a scrub that lands on a cached frame is served
        instantly, and it must not take the pending exact request down with it
        — the user would be left on a grid point they never asked for.
        """
        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            # Warm a grid point so the scrub below is served from cache.
            instance.scrub(FIXTURE_STRIDE)
            qtbot.waitUntil(
                lambda: instance.current_index == FIXTURE_STRIDE, timeout=FRAME_TIMEOUT_MS
            )

            instance.seek(33)  # in flight or pending
            instance.scrub(FIXTURE_STRIDE)  # cache hit, may overtake it

            qtbot.waitUntil(lambda: instance.current_index == 33, timeout=FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()


class TestSourceChange:
    """A decode outlives the source it was asked for. It must not outlive it visibly.

    Both tests here start a decode and then change the source in the same turn
    of the event loop, so the reset is guaranteed to happen before the queued
    `frame_ready` is delivered — which is precisely the ordering that made the
    old frame land in the new source's viewport.
    """

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

            # The stale frame must not have been cached either: index 30 in the
            # new source is a decode, not a hit, and a hit would repaint inside
            # this call.
            instance.scrub(30)
            assert instance.current_index == 0
        finally:
            instance.shutdown()


def degrade(qtbot: QtBot, player: VideoPlayer) -> None:
    """Scrub until the injected policy gives up on exactness."""
    for index in range(1, SAMPLE_WINDOW + 1):
        player.scrub(index)
        qtbot.waitUntil(lambda: player.current_index == index, timeout=FRAME_TIMEOUT_MS)  # noqa: B023
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
        """The whole bargain: approximate while dragging, exact on release."""
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
        """Coarse mode is only cheap if the second visit is free."""
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
            # Synchronous: a cache hit repaints inside the call, with no trip
            # to the decode thread at all.
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
        """Degradation is evidence about a pairing of machine and footage."""
        instance, _ = open_player(qtbot, synthetic_video, impatient_policy)
        try:
            degrade(qtbot, instance)
            instance.close()
            assert not instance.is_scrub_degraded
        finally:
            instance.shutdown()


class TestMetrics:
    def test_a_scrub_round_trip_reaches_the_bus(self, qtbot: QtBot, synthetic_video: Path) -> None:
        """`scrub_to_repaint` is published, and only for scrubs.

        The budget table has declared this ceiling since before there was a
        player; what it has never had is a producer, so nothing outside
        `ScrubPolicy`'s private decision could observe the number. Pinning the
        kind matters as much as pinning that anything arrives: playback ticks
        and exact seeks travel the same slot and are not what this budget
        describes, so publishing them would put a different distribution into
        the series a gate reads.
        """
        bus = MetricBus()
        recorder = MetricRecorder()
        bus.subscribe(recorder.record)

        instance = VideoPlayer(metrics=bus)
        opened: list[VideoMetadata] = []
        instance.opened.connect(opened.append)
        instance.open(str(synthetic_video))
        qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)

        try:
            # The open published nothing: its first frame is an EXACT request.
            assert len(recorder) == 0

            instance.scrub(23)
            qtbot.waitUntil(lambda: instance.current_index == 23, timeout=FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

        assert recorder.keys == ("scrub_to_repaint",)
        assert recorder.median_ms("scrub_to_repaint") > 0.0
