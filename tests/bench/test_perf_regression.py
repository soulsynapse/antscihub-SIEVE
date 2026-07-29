
























from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Protocol

import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.gui.player import VideoPlayer
from tests.bench.gate import TYPICAL, within_budget

pytestmark = [pytest.mark.gui, pytest.mark.benchmark]


class Benchmark(Protocol):













    def pedantic(self, target: Callable[[], object], *, rounds: int) -> object: ...


TIMEOUT_MS = 5000



ROUNDS = 5



DRAG_TARGET = 17
RELEASE_TARGET = 31


def open_measured(qtbot: QtBot, video: Path) -> tuple[VideoPlayer, float]:

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
