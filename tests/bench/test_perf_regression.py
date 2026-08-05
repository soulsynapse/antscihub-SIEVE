"""The budget table enforced against a running player, not against a doc.

`test_budget_table.py` checks that the numbers in code and prose agree. It says
nothing about whether the software meets them — until this file, `check()` had
no call site outside its own unit test, so non-negotiable #4 was enforced by a
measurement someone ran by hand once and wrote down.

Two properties make these useful rather than decorative:

**They run in both sessions.** `nox -s tests` passes `--benchmark-disable`,
which still executes the body once, so the assertion fires in the ordinary
suite. `nox -s benchmark` selects them by marker and runs the rounds for real.
Deleting them now fails the benchmark session on an empty collection.

**The clock is read in the slot, not after a poll.** `qtbot.waitUntil` polls on
a 10 ms interval, which would be a tenth of the `scrub_settle` budget of
invented latency. The timestamps below are taken inside `frame_changed`, so
what is measured is the player's round trip and not the harness's.

The fixture is 160x120 and the reference footage is 5312x2988, so these numbers
are not comparable to the ones in `docs/findings/`. That is fine and deliberate:
the job here is to catch a regression that blows past a ceiling by an order of
magnitude, not to certify the reference hardware.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Protocol

import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.gui.transport.player import VideoPlayer
from tests.bench.gate import TYPICAL, within_budget

pytestmark = [pytest.mark.gui, pytest.mark.benchmark]


class Benchmark(Protocol):
    """The slice of pytest-benchmark's fixture this file uses.

    The plugin ships `py.typed` but no annotations, so pyright infers every
    parameter of `pedantic` as Unknown and strict mode rejects the call.
    Declaring the shape we depend on is the fix that stays honest: it states
    the contract instead of suppressing the complaint, and it stops compiling
    if the plugin changes that signature.

    `pedantic` rather than calling the fixture directly, because these rounds
    are not cheap — each one opens a video — and the calibration loop behind
    the plain call decides the count for us.
    """

    def pedantic(self, target: Callable[[], object], *, rounds: int) -> object: ...


TIMEOUT_MS = 5000

#: Enough rounds for a median to mean something, few enough that the benchmark
#: session stays a gate rather than a coffee break. Each round opens a video.
ROUNDS = 5

#: Cache-cold targets. Every round gets a fresh player, so the only warm frame
#: is 0 — measuring a seek to a cached frame would measure nothing.
DRAG_TARGET = 17
RELEASE_TARGET = 31


def open_measured(qtbot: QtBot, video: Path) -> tuple[VideoPlayer, float]:
    """Open `video`; return the player and the open → first frame time in ms."""
    marks: list[float] = []

    def on_frame(index: int, image: QImage) -> None:
        del index, image
        marks.append(perf_counter())

    player = VideoPlayer()
    player.frame_changed.connect(on_frame)

    started = perf_counter()
    player.open(str(video))
    qtbot.waitUntil(lambda: bool(marks), timeout=TIMEOUT_MS)
    player.frame_changed.disconnect(on_frame)

    return player, (marks[0] - started) * 1000.0


def settle_ms(qtbot: QtBot, player: VideoPlayer, *, drag_to: int, release_at: int) -> float:
    """Time from releasing the slider to the exact frame under it appearing.

    The scrub first is not decoration. The worst case this budget covers is one
    in-flight decode that cannot be cancelled plus the exact one, so the release
    has to be issued while the decode thread is already busy — which is what
    `scrub` then `seek` with no wait between them produces.
    """
    marks: list[float] = []

    def on_frame(index: int, image: QImage) -> None:
        del image
        if index == release_at:
            marks.append(perf_counter())

    player.frame_changed.connect(on_frame)
    player.scrub(drag_to)

    started = perf_counter()
    player.seek(release_at)
    qtbot.waitUntil(lambda: bool(marks), timeout=TIMEOUT_MS)

    return (marks[0] - started) * 1000.0


def test_open_to_first_frame_is_within_budget(
    benchmark: Benchmark, qtbot: QtBot, synthetic_video: Path
) -> None:
    samples: list[float] = []

    def once() -> float:
        player, elapsed_ms = open_measured(qtbot, synthetic_video)
        samples.append(elapsed_ms)
        player.shutdown()
        return elapsed_ms

    benchmark.pedantic(once, rounds=ROUNDS)
    # `TYPICAL`, because this is a felt-latency budget rather than a capability
    # bound: a ceiling only the best round meets is one a user misses half the
    # time. `tests/bench/gate.py` argues the distinction.
    within_budget("open_to_first_frame", samples, resample=once, statistic=TYPICAL)


def test_scrub_release_settles_within_budget(
    benchmark: Benchmark, qtbot: QtBot, synthetic_video: Path
) -> None:
    samples: list[float] = []

    def once() -> float:
        player, _ = open_measured(qtbot, synthetic_video)
        try:
            elapsed = settle_ms(qtbot, player, drag_to=DRAG_TARGET, release_at=RELEASE_TARGET)
        finally:
            player.shutdown()
        samples.append(elapsed)
        return elapsed

    benchmark.pedantic(once, rounds=ROUNDS)
    within_budget("scrub_settle", samples, resample=once, statistic=TYPICAL)
