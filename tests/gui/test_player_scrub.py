"""The player's scrub path: coalescing, the cache, and degrading to coarse mode.

Driven through the real decode thread against the synthetic video, because the
things worth pinning here are ordering properties between the GUI thread and
that thread, and a fake decoder would test the fake's ordering instead.

Degradation is exercised by injecting a policy with an unmeetably low budget.
The alternative — waiting for the real budget to be missed — only fires on a
machine slow enough to miss it, which is to say the test would pass by not
running on exactly the machines that matter.

`sieve.gui` and Qt are imported inside the tests rather than above them, for the
reason `conftest.py` gives; `driving.py` is the stand-in for `qtbot`, and says
why there is no `qtbot` to use.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FIXTURE_FRAMES
from tests.gui import driving

OPEN_TIMEOUT_MS = 5000
FRAME_TIMEOUT_MS = 5000

#: The synthetic fixture is 20 fps, so a 1 s grid is a stride of 20 frames.
FIXTURE_STRIDE = 20


class Recorder:
    """Collects the frames the player decided to display, in order."""

    def __init__(self, player: Any) -> None:
        self.indices: list[int] = []
        player.frame_changed.connect(self._on_frame)

    def _on_frame(self, index: int, image: Any) -> None:
        del image
        self.indices.append(index)


class Kinds:
    """Collects why the player says each frame it displayed was asked for.

    Separate from `Recorder` above rather than a third field on it: what the
    cases below assert about is the provenance the frame arrives with, and the
    two never want the same list.
    """

    def __init__(self, player: Any) -> None:
        self.seen: list[Any] = []
        player.frame_changed.connect(self._on_frame)

    def _on_frame(self, index: int, image: Any, kind: Any) -> None:
        del index, image
        self.seen.append(kind)


def open_player(video: Path, policy: Any | None = None) -> tuple[Any, Recorder]:
    """An opened player parked on frame 0, with its first frame already shown."""
    from sieve.gui.transport.player import VideoPlayer

    player = VideoPlayer(policy=policy)
    opened: list[Any] = []
    player.opened.connect(opened.append)
    recorder = Recorder(player)

    player.open(str(video))
    driving.wait_until(lambda: bool(opened), OPEN_TIMEOUT_MS)
    driving.wait_until(lambda: bool(recorder.indices), FRAME_TIMEOUT_MS)
    return player, recorder


@pytest.fixture
def player(qapp, synthetic_video: Path) -> Iterator[Any]:
    del qapp
    instance, _ = open_player(synthetic_video)
    yield instance
    instance.shutdown()


@pytest.fixture
def impatient_policy(qapp) -> Any:
    """A policy that degrades as soon as it has seen a full window of scrubs.

    A zero budget means every real decode is over it, so `SAMPLE_WINDOW`
    scrubs is both necessary and sufficient — the same rule the real policy
    follows, at a threshold this machine cannot help but cross.
    """
    del qapp
    from sieve.gui.transport.scrub_policy import ScrubPolicy

    return ScrubPolicy(budget_ms=0.0, coarse_interval_seconds=1.0)


def degrade(player: Any) -> None:
    """Scrub until the injected policy gives up on exactness."""
    from sieve.gui.transport.scrub_policy import SAMPLE_WINDOW

    for index in range(1, SAMPLE_WINDOW + 1):
        player.scrub(index)
        driving.wait_until(lambda: player.current_index == index, FRAME_TIMEOUT_MS)  # noqa: B023
    assert player.is_scrub_degraded


class TestExactScrubbing:
    def test_a_scrub_shows_the_exact_frame_when_not_degraded(self, player: Any) -> None:
        player.scrub(13)
        driving.wait_until(lambda: player.current_index == 13, FRAME_TIMEOUT_MS)

    def test_a_seek_shows_the_exact_frame(self, player: Any) -> None:
        player.seek(27)
        driving.wait_until(lambda: player.current_index == 27, FRAME_TIMEOUT_MS)

    def test_targets_are_clamped_to_the_source(self, player: Any) -> None:
        player.seek(10_000)
        driving.wait_until(lambda: player.current_index == FIXTURE_FRAMES - 1, FRAME_TIMEOUT_MS)


class TestCoalescing:
    def test_a_burst_settles_on_the_final_target(self, qapp, synthetic_video: Path) -> None:
        del qapp
        instance, recorder = open_player(synthetic_video)
        try:
            last = FIXTURE_FRAMES - 1
            for index in range(1, FIXTURE_FRAMES):
                instance.scrub(index)
            driving.wait_until(lambda: instance.current_index == last, FRAME_TIMEOUT_MS)

            # The point of coalescing: the frames nobody would have seen are
            # discarded rather than queued. Forty requests, far fewer displays.
            assert len(recorder.indices) < FIXTURE_FRAMES
            assert recorder.indices[-1] == last
        finally:
            instance.shutdown()

    def test_a_pending_exact_request_survives_a_later_cached_scrub(
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        """A released slider is a commitment; a drag position is not.

        The hazard this pins: a scrub that lands on a cached frame is served
        instantly, and it must not take the pending exact request down with it
        — the user would be left on a grid point they never asked for.
        """
        del qapp
        instance, _ = open_player(synthetic_video, impatient_policy)
        try:
            degrade(instance)
            # Warm a grid point so the scrub below is served from cache.
            instance.scrub(FIXTURE_STRIDE)
            driving.wait_until(lambda: instance.current_index == FIXTURE_STRIDE, FRAME_TIMEOUT_MS)

            instance.seek(33)  # in flight or pending
            instance.scrub(FIXTURE_STRIDE)  # cache hit, may overtake it

            driving.wait_until(lambda: instance.current_index == 33, FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()


class TestSourceChange:
    """A decode outlives the source it was asked for. It must not outlive it visibly.

    Both tests here start a decode and then change the source in the same turn
    of the event loop, so the reset is guaranteed to happen before the queued
    `frame_ready` is delivered — which is precisely the ordering that made the
    old frame land in the new source's viewport.
    """

    def test_a_frame_decoded_before_a_close_is_not_shown(self, qapp, synthetic_video: Path) -> None:
        del qapp
        instance, recorder = open_player(synthetic_video)
        try:
            instance.seek(30)
            instance.close()

            driving.wait(300)
            assert recorder.indices == [0], "a closed player displayed a frame"
            assert instance.current_index == 0
        finally:
            instance.shutdown()

    def test_a_frame_decoded_before_a_reopen_is_not_shown(
        self, qapp, synthetic_video: Path
    ) -> None:
        del qapp
        instance, recorder = open_player(synthetic_video)
        try:
            instance.seek(30)

            opened: list[Any] = []
            instance.opened.connect(opened.append)
            instance.open(str(synthetic_video))
            driving.wait_until(lambda: bool(opened), OPEN_TIMEOUT_MS)
            driving.wait_until(lambda: len(recorder.indices) > 1, FRAME_TIMEOUT_MS)

            driving.wait(300)
            assert recorder.indices == [0, 0], "frame 30 of the old source was painted"

            # The stale frame must not have been cached either: index 30 in the
            # new source is a decode, not a hit, and a hit would repaint inside
            # this call.
            instance.scrub(30)
            assert instance.current_index == 0
        finally:
            instance.shutdown()


class TestDegradation:
    def test_sustained_slow_scrubbing_degrades_and_announces_once(
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        del qapp
        instance, _ = open_player(synthetic_video, impatient_policy)
        try:
            announcements: list[int] = []
            instance.scrub_degraded.connect(lambda: announcements.append(1))

            degrade(instance)
            assert announcements == [1]

            for index in (7, 11, 19):
                instance.scrub(index)
                driving.wait(20)
            assert announcements == [1], "the notice must not repeat"
        finally:
            instance.shutdown()

    def test_degraded_scrubs_snap_to_the_grid(
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        del qapp
        instance, _ = open_player(synthetic_video, impatient_policy)
        try:
            degrade(instance)
            instance.scrub(23)
            driving.wait_until(lambda: instance.current_index == FIXTURE_STRIDE, FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

    def test_release_lands_exactly_however_coarse_the_drag_was(
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        """The whole bargain: approximate while dragging, exact on release."""
        del qapp
        instance, _ = open_player(synthetic_video, impatient_policy)
        try:
            degrade(instance)
            instance.scrub(23)
            driving.wait_until(lambda: instance.current_index == FIXTURE_STRIDE, FRAME_TIMEOUT_MS)

            instance.seek(23)
            driving.wait_until(lambda: instance.current_index == 23, FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

    def test_a_warmed_grid_point_needs_no_decode(
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        """Coarse mode is only cheap if the second visit is free."""
        del qapp
        instance, recorder = open_player(synthetic_video, impatient_policy)
        try:
            degrade(instance)
            instance.scrub(23)
            driving.wait_until(lambda: instance.current_index == FIXTURE_STRIDE, FRAME_TIMEOUT_MS)
            instance.seek(0)
            driving.wait_until(lambda: instance.current_index == 0, FRAME_TIMEOUT_MS)

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
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        del qapp
        instance, _ = open_player(synthetic_video, impatient_policy)
        try:
            degrade(instance)
            impatient_policy.set_allow_degrade(False)

            instance.scrub(23)
            driving.wait_until(lambda: instance.current_index == 23, FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

    def test_opening_a_new_source_starts_exact_again(
        self, qapp, synthetic_video: Path, impatient_policy: Any
    ) -> None:
        """Degradation is evidence about a pairing of machine and footage."""
        del qapp
        instance, _ = open_player(synthetic_video, impatient_policy)
        try:
            degrade(instance)
            instance.close()
            assert not instance.is_scrub_degraded
        finally:
            instance.shutdown()


class TestRenderOnSettle:
    """A drag is answered with the raw frame; the settle is what pays for a render.

    Nothing here renders — `gui/app.py` does, in the slot connected to
    `frame_changed` — so what is pinned is the permission each frame carries
    with it. The player is where that has to be decided: 07.12 put the render
    inside this round trip and `scrub_to_repaint` is both what the round trip
    publishes and `ScrubPolicy`'s degradation trigger, so a drag frame carrying
    the permission lets a slow pipeline snap the *transport* onto a coarse
    grid — a remedy aimed at decode, applied to something else.
    """

    def test_render_on_settle_refuses_a_drag_frame(self, player: Any) -> None:
        kinds = Kinds(player)
        player.scrub(13)
        driving.wait_until(lambda: player.current_index == 13, FRAME_TIMEOUT_MS)

        assert kinds.seen and not kinds.seen[-1].may_be_rendered

    def test_render_on_settle_pays_on_the_release(self, player: Any) -> None:
        """The release is a commitment, and what it commits to is the exact picture."""
        kinds = Kinds(player)
        player.scrub(13)
        driving.wait_until(lambda: player.current_index == 13, FRAME_TIMEOUT_MS)
        player.seek(27)
        driving.wait_until(lambda: player.current_index == 27, FRAME_TIMEOUT_MS)

        assert kinds.seen[-1].may_be_rendered

    def test_render_on_settle_leaves_playback_alone(self, player: Any) -> None:
        """Outside the ruling: a playback tick is not a drag in flight.

        Playback already drops the frames it cannot decode, so the render is
        charged against the achieved rate rather than against a gesture's
        latency, and the alternative — a moving picture of the footage under a
        graph of the pipeline — is the split the viewport exists to close.
        """
        from sieve.gui.transport.request_intent import RequestKind

        kinds = Kinds(player)
        player.play()
        try:
            driving.wait_until(lambda: RequestKind.PLAYBACK in kinds.seen, FRAME_TIMEOUT_MS)
        finally:
            player.pause()

        ticks = [kind for kind in kinds.seen if kind is RequestKind.PLAYBACK]
        assert ticks and all(kind.may_be_rendered for kind in ticks)


class TestMetrics:
    def test_a_scrub_round_trip_reaches_the_bus(self, qapp, synthetic_video: Path) -> None:
        """`scrub_to_repaint` is published, and only for scrubs.

        The budget table has declared this ceiling since before there was a
        player; what it has never had is a producer, so nothing outside
        `ScrubPolicy`'s private decision could observe the number. Pinning the
        kind matters as much as pinning that anything arrives: playback ticks
        and exact seeks travel the same slot and are not what this budget
        describes, so publishing them would put a different distribution into
        the series a gate reads.
        """
        del qapp
        from sieve.bench.metrics import MetricBus
        from sieve.bench.metrics import Recorder as MetricRecorder
        from sieve.gui.transport.player import VideoPlayer

        bus = MetricBus()
        recorder = MetricRecorder()
        bus.subscribe(recorder.record)

        instance = VideoPlayer(metrics=bus)
        opened: list[Any] = []
        instance.opened.connect(opened.append)
        instance.open(str(synthetic_video))
        driving.wait_until(lambda: bool(opened), OPEN_TIMEOUT_MS)

        try:
            # The open published nothing: its first frame is an EXACT request.
            assert len(recorder) == 0

            instance.scrub(23)
            driving.wait_until(lambda: instance.current_index == 23, FRAME_TIMEOUT_MS)
        finally:
            instance.shutdown()

        assert recorder.keys == ("scrub_to_repaint",)
        assert recorder.median_ms("scrub_to_repaint") > 0.0
