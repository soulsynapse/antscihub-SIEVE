"""The trace records the real session, not a plausible one.

The unit tests build events by hand, so they cannot catch the two ways this
instrument fails silently. Both are here.

**The source column is right.** A request that the ring served and one that
went to the decode thread have to be distinguishable, because the replay's
whole question is which of them a different policy would have moved. Recording
the same source for both, or recording twice for one request as it fell
through a layer, would give a trace that replays to a confident wrong answer.

**The kind column matches what `bench/` scores on.** `SCRUB_KIND` is a string
spelled out one layer away from the `RequestKind` it mirrors, so nothing but a
test that drives a real drag can notice the day they stop agreeing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.retention_trace import (
    FROM_DECODE,
    FROM_RING,
    GET,
    PUT,
    SCRUB_KIND,
    UNKNOWN_PLAYHEAD,
    TraceRecorder,
    load_trace,
)
from sieve.core.types import ChannelSpec, Frame, VideoMetadata
from sieve.gui.player import VideoPlayer
from sieve.gui.render_ring import RenderFrameRing

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 5000
FRAME_TIMEOUT_MS = 5000


def gray_frame(index: int) -> Frame:
    return Frame(
        data=np.full((120, 160), 213, dtype=np.uint8), index=index, channels=ChannelSpec.GRAY
    )


def test_a_scrub_a_ring_hit_and_a_decode_are_told_apart(
    qtbot: QtBot, synthetic_video: Path, tmp_path: Path
) -> None:
    trace_path = tmp_path / "session.jsonl"
    recorder = TraceRecorder(trace_path)
    player = VideoPlayer(trace=recorder)
    ring = RenderFrameRing(capacity_bytes=1024 * 1024, trace=recorder)
    opened: list[VideoMetadata] = []
    player.opened.connect(opened.append)
    try:
        player.open(str(synthetic_video))
        qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)

        ring.put(gray_frame(7))
        player.set_render_feed(ring)
        player.set_viewport_luma(True)
        player.scrub(7)
        player.scrub(21)
        qtbot.waitUntil(lambda: player.current_index == 21, timeout=FRAME_TIMEOUT_MS)
    finally:
        player.shutdown()
        recorder.close()

    events = load_trace(trace_path)
    puts = [event for event in events if event.op == PUT]
    assert [(event.index, event.frontier, event.playhead) for event in puts] == [
        (7, 7, UNKNOWN_PLAYHEAD)
    ]

    scrubs = [event for event in events if event.op == GET and event.kind == SCRUB_KIND]
    assert [(event.index, event.source) for event in scrubs] == [
        (7, FROM_RING),
        (21, FROM_DECODE),
    ], "one event per request, and the layer that served it"
    # The playhead is where the user *was*: the ring hit moved them to 7, so
    # the drag to 21 is recorded as departing from there.
    assert scrubs[1].playhead == 7
    assert scrubs[1].frontier == 7
