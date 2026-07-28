"""Render-fed playback: the render's frames reach the pane, decoded once.

Three claims, one per seam it crosses:

**The ring keeps what the render produced, honestly.** Gray proxies in, LRU
out, frontier a claim about this render only — and a chroma frame refused
whole, because a frontier that advanced past frames the player cannot take
would fold playback toward a gap.

**The player serves a ring frame without asking its decode thread.** The
observable is synchrony: a ring hit repaints inside the `seek` call, where a
decode is a queued round trip to another thread. And the gate holds — a
colour viewport is never served the ring's luma frames.

**A window render fills the ring.** Driven through the real runner over the
synthetic fixture, because the put sits on the render thread inside `execute`'s
delivery path, and a faked runner would test the fake's plumbing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QImage
from pytestqt.qtbot import QtBot

from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame, VideoMetadata
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.render_ring import RenderFrameRing

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 5000
FRAME_TIMEOUT_MS = 5000
RENDER_TIMEOUT_MS = 30_000

GRAY = QImage.Format.Format_Grayscale8
BGR = QImage.Format.Format_BGR888

#: A pixel value no synthetic-video frame carries (blue is `n * 5`, so 213 is
#: nobody's), which is what lets an assertion say a frame came from the ring
#: rather than from a decode that happened to be fast.
MARK = 213


def gray_frame(index: int, width: int = 160, height: int = 120, value: int = MARK) -> Frame:
    return Frame(
        data=np.full((height, width), value, dtype=np.uint8),
        index=index,
        channels=ChannelSpec.GRAY,
    )


class TestTheRing:
    def test_a_put_frame_comes_back_and_advances_the_frontier(self) -> None:
        ring = RenderFrameRing(capacity_bytes=1024 * 1024)
        assert ring.frontier is None
        ring.put(gray_frame(7))
        image = ring.get(7)
        assert image is not None
        assert image.format() == GRAY
        assert image.pixelColor(0, 0).red() == MARK
        assert ring.frontier == 7

    def test_a_wide_frame_is_proxied_down_on_the_way_in(self) -> None:
        ring = RenderFrameRing(capacity_bytes=1024 * 1024)
        ring.set_proxy_width(80)
        ring.put(gray_frame(3))
        image = ring.get(3)
        assert image is not None
        assert image.width() == 80

    def test_a_chroma_frame_is_refused_whole(self) -> None:
        """No proxy and no frontier move: an advanced frontier over frames the
        player cannot take would fold playback toward a gap."""
        ring = RenderFrameRing(capacity_bytes=1024 * 1024)
        colour = Frame(
            data=np.zeros((120, 160, 3), dtype=np.uint8), index=4, channels=ChannelSpec.BGR
        )
        ring.put(colour)
        assert ring.get(4) is None
        assert ring.frontier is None

    def test_the_bound_evicts_the_oldest_and_the_frontier_survives(self) -> None:
        one_frame = 160 * 120
        ring = RenderFrameRing(capacity_bytes=2 * one_frame)
        for index in range(3):
            ring.put(gray_frame(index))
        assert ring.get(0) is None, "the bound did not evict"
        assert ring.get(2) is not None
        assert ring.frontier == 2

    def test_begin_resets_the_frontier_and_keeps_the_frames(self) -> None:
        """A new render of the same source starts from nothing *produced*, but
        the frames already kept are still the frames at their indices."""
        ring = RenderFrameRing(capacity_bytes=1024 * 1024)
        ring.put(gray_frame(5))
        ring.begin()
        assert ring.frontier is None
        assert ring.get(5) is not None

    def test_clear_drops_everything(self) -> None:
        ring = RenderFrameRing(capacity_bytes=1024 * 1024)
        ring.put(gray_frame(5))
        ring.clear()
        assert ring.frontier is None
        assert ring.get(5) is None


class FormatRecorder:
    """Every displayed frame, as (index, format, top-left value), in order."""

    def __init__(self, player: VideoPlayer) -> None:
        self.frames: list[tuple[int, QImage.Format, int]] = []
        player.frame_changed.connect(self._on_frame)

    def _on_frame(self, index: int, image: QImage) -> None:
        self.frames.append((index, image.format(), image.pixelColor(0, 0).red()))


def open_player(qtbot: QtBot, video: Path) -> tuple[VideoPlayer, FormatRecorder]:
    player = VideoPlayer()
    opened: list[VideoMetadata] = []
    player.opened.connect(opened.append)
    recorder = FormatRecorder(player)
    player.open(str(video))
    qtbot.waitUntil(lambda: bool(opened), timeout=OPEN_TIMEOUT_MS)
    qtbot.waitUntil(lambda: bool(recorder.frames), timeout=FRAME_TIMEOUT_MS)
    return player, recorder


class TestThePlayerTakesRingFrames:
    def test_a_ring_hit_repaints_inside_the_seek_with_no_decode(
        self, qtbot: QtBot, synthetic_video: Path
    ) -> None:
        player, recorder = open_player(qtbot, synthetic_video)
        try:
            ring = RenderFrameRing(capacity_bytes=1024 * 1024)
            ring.put(gray_frame(7))
            player.set_render_feed(ring)
            player.set_viewport_luma(True)

            player.seek(7)
            # Synchronously: a decode is a queued round trip to another
            # thread, so a repaint already delivered *here* cannot be one.
            assert recorder.frames[-1] == (7, GRAY, MARK)
            assert player.current_index == 7
        finally:
            player.shutdown()

    def test_a_colour_viewport_is_never_served_the_rings_luma_frames(
        self, qtbot: QtBot, synthetic_video: Path
    ) -> None:
        """The format gate is the tab scope: gray pane or no ring at all."""
        player, recorder = open_player(qtbot, synthetic_video)
        try:
            ring = RenderFrameRing(capacity_bytes=1024 * 1024)
            ring.put(gray_frame(9))
            player.set_render_feed(ring)

            player.seek(9)
            assert recorder.frames[-1][2] != MARK, "a luma frame reached a colour pane"
            qtbot.waitUntil(lambda: recorder.frames[-1][:2] == (9, BGR), timeout=FRAME_TIMEOUT_MS)
        finally:
            player.shutdown()


class TestTheRenderFillsTheRing:
    def test_a_window_render_leaves_its_frames_and_frontier_behind(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path
    ) -> None:
        del qapp
        runner = PreviewRunner()
        finished: list[object] = []
        runner.render_finished.connect(finished.append)
        window = ClipRange(start=10, end=16)
        small = Node(node_id="small", filter_id="downsample", version="1.0.0", params={"factor": 2})
        graph = Pipeline(nodes=(small,))
        try:
            runner.open(synthetic_video)
            qtbot.waitUntil(lambda: runner.is_open, timeout=OPEN_TIMEOUT_MS)
            assert runner.request_render(graph, window)
            qtbot.waitUntil(lambda: bool(finished), timeout=RENDER_TIMEOUT_MS)

            assert runner.ring.frontier == window.end - 1
            for index in range(window.start, window.end):
                image = runner.ring.get(index)
                assert image is not None, f"frame {index} never reached the ring"
                assert image.format() == GRAY
            # The synthetic fixture's blue channel is `n * 5` and luma weights
            # blue at ~0.114, so frames a few indices apart land on different
            # gray values — the ring holds *which* frame, not merely a frame.
            first, last = runner.ring.get(10), runner.ring.get(15)
            assert first is not None and last is not None
            assert first.pixelColor(0, 0).red() != last.pixelColor(0, 0).red()
        finally:
            runner.shutdown()
