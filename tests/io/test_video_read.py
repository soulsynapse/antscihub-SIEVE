"""The decode boundary's contract (ADR-018).

[INTENT] What is tested here is what a caller is entitled to rely on and what
a hardware change cannot alter: seek accuracy, the delivered dtype and layout,
the reported bit-depth reduction, and the errors. Timing belongs to
`tests/bench/test_decode_seek.py`, which measures through this module.

These read the generated corpus, so they skip on a fresh checkout. They are
deliberately not marked `slow` -- decoding a handful of 640x360 frames costs
milliseconds, and the decode boundary is worth having inside the default gate
on any machine that has the corpus.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from sieve.bench.corpus import Clip
from sieve.io.video_read import (
    DELIVERED_DTYPE,
    DELIVERED_LAYOUT,
    DecoderIdentity,
    DecoderThread,
    FrameReadError,
    FrameRingBuffer,
    VideoOpenError,
    VideoReader,
    VideoReadError,
    build_keyframe_index,
    decoder_identity,
)

FRAME_NDIM = 3
BGR_CHANNELS = 3
EIGHT_BIT = 8
CANCEL_AFTER_CALLS = 2
RING_EVICTION_BUDGET_FRAMES = 2
SCRUB_TARGET_A = 50
SCRUB_TARGET_B = 30


@pytest.fixture
def clip(corpus: list[Clip]) -> Clip:
    """H.264 8-bit: the codec the vision documents' user stories centre on."""
    for candidate in corpus:
        if candidate.label == "h264-8bit":
            return candidate
    pytest.skip("The corpus has no h264-8bit clip.")


@pytest.fixture
def reader(clip: Clip) -> Iterator[VideoReader]:
    with VideoReader(clip.path) as open_reader:
        yield open_reader


def test_open_reports_geometry(reader: VideoReader, clip: Clip) -> None:
    info = reader.info
    assert info.path == clip.path
    assert info.width > 0
    assert info.height > 0
    assert info.frame_count is not None and info.frame_count > 0
    assert info.fps is not None and info.fps > 0
    assert info.codec


def test_delivered_representation_is_the_pinned_one(reader: VideoReader) -> None:
    """ADR-018 pins uint8 BGR delivery whatever the source carries.

    A change here is a change to the decode boundary's declared contract and to
    every downstream assumption about frame dtype, not a test to update.
    """
    frame = reader.read(0)
    assert frame.dtype == np.uint8
    assert frame.ndim == FRAME_NDIM
    assert frame.shape == (reader.info.height, reader.info.width, BGR_CHANNELS)
    assert reader.info.delivered_dtype == DELIVERED_DTYPE
    assert reader.info.delivered_layout == DELIVERED_LAYOUT


def test_bit_depth_matches_the_manifest_for_every_codec(corpus: list[Clip]) -> None:
    """The pixel-format tag is decoded correctly across the whole corpus.

    This is the test that keeps `describe_reduction` honest. The manifest
    records what each clip was encoded at, independently of what OpenCV
    reports, so agreement between them is evidence rather than a tautology --
    and the corpus spans both an 8-bit fourcc (`I420`) and the FFmpeg planar
    tags that carry depth in a raw byte.
    """
    for candidate in corpus:
        with VideoReader(candidate.path) as open_reader:
            info = open_reader.info
            assert info.source_bit_depth == candidate.expected_bit_depth, (
                f"{candidate.label}: manifest says {candidate.expected_bit_depth}-bit, "
                f"decoder reports {info.source_bit_depth} from pixel format "
                f"{info.pixel_format!r}"
            )
            assert info.bit_depth_reduced is (candidate.expected_bit_depth > EIGHT_BIT)


def test_reduction_is_described_only_when_something_is_lost(corpus: list[Clip]) -> None:
    for candidate in corpus:
        with VideoReader(candidate.path) as open_reader:
            described = open_reader.info.describe_reduction()
            if candidate.expected_bit_depth > EIGHT_BIT:
                assert described is not None
                assert str(candidate.expected_bit_depth) in described
                assert candidate.path.name in described
            else:
                assert described is None


def test_seeking_to_a_frame_twice_decodes_the_same_pixels(reader: VideoReader) -> None:
    """Seek accuracy, which is the property ADR-018 chose this decoder for.

    A decoder that lands near the requested frame rather than on it fails here
    without failing anything else -- the shapes and dtypes stay right and the
    user simply sees the wrong picture.
    """
    target = 137
    first = reader.read(target).copy()
    reader.read(0)
    second = reader.read(target)
    assert np.array_equal(first, second), (
        f"Two seeks to frame {target} decoded different pixels, so index-based "
        f"scrubbing does not identify a frame."
    )


def test_seek_agrees_with_sequential_decode(reader: VideoReader) -> None:
    """A seek to N and N sequential reads reach the same frame.

    The stronger form of the property above: repeatable seeking could still be
    repeatably wrong. Sequential decode from the start of the file is the
    reference that has no seek in it at all.
    """
    target = 7
    sequential = None
    for _ in range(target + 1):
        sequential = reader.read_next()
    assert sequential is not None
    sequential = sequential.copy()

    seeked = reader.read(target)
    assert np.array_equal(sequential, seeked), (
        f"Frame {target} by seek differs from frame {target} by sequential decode."
    )


def test_position_advances_and_read_next_continues(reader: VideoReader) -> None:
    start = 10
    assert reader.position == 0
    reader.read(start)
    assert reader.position == start + 1
    following = reader.read_next().copy()
    assert reader.position == start + 2
    assert np.array_equal(following, reader.read(start + 1))


def test_adjacent_reads_do_not_reseek(reader: VideoReader, monkeypatch: pytest.MonkeyPatch) -> None:
    """A forward scrub is a run of adjacent reads, and re-seeking each one
    discards the reference frames the next decode is built from.

    The saving is invisible in the returned pixels -- both paths are correct,
    only the cost differs -- so it is asserted at the seek call. That is the
    kind of regression a timing budget notices months late and a reviewer never
    notices at all.
    """
    seeks: list[int] = []
    # Reaching into the private seek deliberately: it is the observable, and
    # the alternative is inferring "no seek happened" from a timing.
    original = reader._seek

    def record(index: int) -> None:
        seeks.append(index)
        original(index)

    reader.read(40)
    monkeypatch.setattr(reader, "_seek", record)
    reader.read(41)
    reader.read(42)
    assert seeks == [], f"Adjacent reads issued seeks to {seeks}"
    reader.read(400)
    assert seeks == [400]


def test_missing_file_is_an_open_error(tmp_path: Path) -> None:
    with pytest.raises(VideoOpenError, match="No such video file"):
        VideoReader(tmp_path / "absent.mp4")


def test_a_file_that_is_not_video_is_an_open_error(tmp_path: Path) -> None:
    decoy = tmp_path / "notes.txt"
    decoy.write_text("This is not a video.", encoding="utf-8")
    with pytest.raises(VideoOpenError):
        VideoReader(decoy)


def test_out_of_range_indices_are_read_errors(reader: VideoReader) -> None:
    total = reader.info.frame_count
    assert total is not None
    with pytest.raises(FrameReadError, match="past the end"):
        reader.read(total)
    with pytest.raises(FrameReadError, match="negative"):
        reader.read(-1)


def test_reading_after_close_is_an_error(clip: Clip) -> None:
    closed = VideoReader(clip.path)
    closed.close()
    assert closed.closed
    with pytest.raises(VideoReadError, match="closed"):
        closed.read(0)


def test_close_is_idempotent(clip: Clip) -> None:
    twice = VideoReader(clip.path)
    twice.close()
    twice.close()
    assert twice.closed


def test_context_manager_closes_on_exit(clip: Clip) -> None:
    with VideoReader(clip.path) as managed:
        assert not managed.closed
    assert managed.closed


def test_decoder_identity_is_recorded_for_cache_keys(reader: VideoReader) -> None:
    """ARCHITECTURE.md 12 puts the decoder inside the code-version hash.

    The hash input is asserted for shape rather than for a literal, because
    pinning the string would make an OpenCV upgrade fail here instead of doing
    what it is supposed to do -- invalidate caches.
    """
    identity = reader.info.decoder
    assert isinstance(identity, DecoderIdentity)
    assert identity.library
    assert identity.version
    assert identity.backend and identity.backend != "unresolved"
    assert identity.as_hash_input() == f"{identity.library}=={identity.version}@{identity.backend}"


def test_identity_without_a_capture_declines_to_name_a_backend() -> None:
    """VideoCapture resolves its backend per file, so there is no process-wide
    answer to invent."""
    assert decoder_identity().backend == "unresolved"


def test_last_frame_type_reports_a_keyframe_at_index_zero(reader: VideoReader) -> None:
    """Frame 0 is always a keyframe -- there is nothing before it to reference."""
    reader.read(0)
    assert reader.last_frame_type() == ord("I")


class TestKeyframeIndex:
    """`build_keyframe_index` -- `ARCHITECTURE.md` 5.5's background index.

    Confirms the index is constructible through the pinned ADR-018 decoder
    with no second decode dependency: `cv2.CAP_PROP_FRAME_TYPE` reports an
    ASCII frame-type code after each decode (probed directly against the
    corpus before this module was written), so the index needs nothing beyond
    what `VideoReader` already exposes via `last_frame_type`.
    """

    def test_starts_at_zero_and_is_sorted(self, clip: Clip) -> None:
        index = build_keyframe_index(clip.path)
        assert index is not None
        assert index.frame_count > 0
        assert index.keyframes[0] == 0
        assert list(index.keyframes) == sorted(index.keyframes)

    def test_nearest_at_or_before_never_overshoots(self, clip: Clip) -> None:
        index = build_keyframe_index(clip.path)
        assert index is not None
        for target in (0, index.frame_count // 2, index.frame_count - 1):
            nearest = index.nearest_at_or_before(target)
            assert nearest <= target
            assert nearest in index.keyframes

    def test_cancellation_yields_no_index(self, clip: Clip) -> None:
        """A cancelled build reports `None` rather than a partial index, which
        would silently mis-answer the frames the build never reached."""
        calls = 0

        def cancelled() -> bool:
            nonlocal calls
            calls += 1
            return calls > CANCEL_AFTER_CALLS

        assert build_keyframe_index(clip.path, cancelled=cancelled) is None


def _blank_frame(width: int = 4, height: int = 4) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class TestFrameRingBuffer:
    """Byte-budgeted LRU cache backing the decoder thread's read-ahead."""

    def test_evicts_oldest_past_the_byte_budget(self) -> None:
        oldest, middle, newest = 0, 1, 2
        frame = _blank_frame()
        ring = FrameRingBuffer(max_bytes=frame.nbytes * RING_EVICTION_BUDGET_FRAMES)
        ring.put(oldest, frame)
        ring.put(middle, frame)
        ring.put(newest, frame)
        assert oldest not in ring
        assert middle in ring
        assert newest in ring
        assert len(ring) == RING_EVICTION_BUDGET_FRAMES

    def test_get_refreshes_recency(self) -> None:
        touched, untouched, newest = 0, 1, 2
        frame = _blank_frame()
        ring = FrameRingBuffer(max_bytes=frame.nbytes * RING_EVICTION_BUDGET_FRAMES)
        ring.put(touched, frame)
        ring.put(untouched, frame)
        ring.get(touched)  # touches it, leaving `untouched` as the least recently used
        ring.put(newest, frame)
        assert touched in ring
        assert untouched not in ring
        assert newest in ring

    def test_clear_empties_the_buffer(self) -> None:
        frame = _blank_frame()
        ring = FrameRingBuffer(max_bytes=frame.nbytes * 4)
        ring.put(0, frame)
        ring.clear()
        assert len(ring) == 0
        assert ring.get(0) is None


@pytest.fixture
def ring() -> FrameRingBuffer:
    return FrameRingBuffer(max_bytes=64 * 1024 * 1024)


class TestDecoderThread:
    """Background decode-ahead with latest-wins coalescing.

    Waits are on `threading.Event`, not `time.sleep`: a sleep-based wait either
    races a slow CI machine or pads every run with idle time, where an event
    returns the instant the awaited call happens.
    """

    def test_delivers_the_requested_frame(self, clip: Clip, ring: FrameRingBuffer) -> None:
        received = threading.Event()
        result: dict[str, object] = {}

        def on_frame(index: int, frame: np.ndarray) -> None:
            result["index"] = index
            result["frame"] = frame
            received.set()

        thread = DecoderThread(clip.path, ring, on_frame=on_frame)
        thread.start()
        try:
            thread.request(SCRUB_TARGET_A)
            assert received.wait(timeout=5.0), "no frame delivered within 5s"
        finally:
            thread.stop()
        assert result["index"] == SCRUB_TARGET_A
        assert isinstance(result["frame"], np.ndarray)
        assert result["frame"].dtype == np.uint8
        assert SCRUB_TARGET_A in ring

    def test_prefetch_fills_the_ring_ahead_of_the_target(
        self, clip: Clip, ring: FrameRingBuffer
    ) -> None:
        """The read-ahead fills the ring after the requested target, not just
        the target itself -- that fill is what turns a subsequent adjacent
        scrub into a `FrameRingBuffer.get` hit instead of a decode.

        Polled with a deadline rather than a single wait: the prefetch loop
        has no completion signal of its own (it is deliberately fire-and-
        forget), so "did it fill in" is only observable by checking the ring
        repeatedly, bounded so a genuine failure still fails in finite time.
        """
        lookahead_range = range(11, 15)
        thread = DecoderThread(clip.path, ring, lookahead=4)
        thread.start()
        try:
            thread.request(10)
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and not any(i in ring for i in lookahead_range):
                time.sleep(0.02)
        finally:
            thread.stop()
        assert any(index in ring for index in lookahead_range), (
            "prefetch did not fill any lookahead frame in time"
        )

    def test_request_coalesces_to_the_latest_target(
        self, clip: Clip, ring: FrameRingBuffer
    ) -> None:
        """Repeated `request` calls before the thread wakes leave only the
        latest target pending, not a queue of all of them -- the mechanism
        that keeps a fast drag from trailing through every intermediate
        value. Asserted against the pending-target state directly, the same
        way `test_adjacent_reads_do_not_reseek` reaches into `VideoReader`'s
        private seek: the alternative is inferring coalescing from timing.
        """
        thread = DecoderThread(clip.path, ring)  # not started
        thread.request(10)
        thread.request(20)
        thread.request(SCRUB_TARGET_B)
        assert thread._target == SCRUB_TARGET_B

    def test_reports_errors_for_a_rejected_target(self, clip: Clip, ring: FrameRingBuffer) -> None:
        errors: list[tuple[int, str]] = []
        got_error = threading.Event()

        def on_error(index: int, message: str) -> None:
            errors.append((index, message))
            got_error.set()

        thread = DecoderThread(clip.path, ring, on_error=on_error)
        thread.start()
        try:
            thread.request(-1)
            assert got_error.wait(timeout=5.0), "no error reported within 5s"
        finally:
            thread.stop()
        assert errors[0][0] == -1
        assert "negative" in errors[0][1]

    def test_stop_joins_the_thread(self, clip: Clip, ring: FrameRingBuffer) -> None:
        thread = DecoderThread(clip.path, ring)
        thread.start()
        thread.stop()
        assert not thread._thread.is_alive()
