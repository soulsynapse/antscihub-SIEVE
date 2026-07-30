"""The reader, including the seek paths that make scrubbing viable.

Frame identity is asserted through the synthetic fixture's intensity ramp:
these tests fail if a seek lands on the wrong frame, not merely if it fails to
decode. That is the failure mode that matters — a scrub that silently shows a
neighbouring frame is invisible until it corrupts a cut.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sieve.core.types import ChannelSpec
from sieve.decode.identity import decoder_identity
from sieve.decode.reader import GRAB_FORWARD_LIMIT, VideoDecodeError, VideoReader
from tests.conftest import FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_WIDTH


class TestOpen:
    def test_reports_container_metadata(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            metadata = reader.metadata
            assert (metadata.width, metadata.height) == (FIXTURE_WIDTH, FIXTURE_HEIGHT)
            assert metadata.frame_count == FIXTURE_FRAMES
            assert metadata.fps > 0.0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(VideoDecodeError, match="No such video file"):
            VideoReader(tmp_path / "absent.mp4")

    def test_non_video_raises(self, tmp_path: Path) -> None:
        junk = tmp_path / "not-a-video.mp4"
        junk.write_bytes(b"this is not a video")
        with pytest.raises(VideoDecodeError):
            VideoReader(junk)

    def test_close_is_idempotent(self, synthetic_video: Path) -> None:
        reader = VideoReader(synthetic_video)
        reader.close()
        reader.close()
        assert not reader.is_open


class TestRead:
    def test_sequential_reads_return_successive_frames(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            for index in range(5):
                assert reader.read(index).index == index

    def test_frame_carries_source_dimensions(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            frame = reader.read(0)
            assert (frame.width, frame.height) == (FIXTURE_WIDTH, FIXTURE_HEIGHT)

    def test_out_of_range_raises(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            with pytest.raises(VideoDecodeError, match="out of range"):
                reader.read(FIXTURE_FRAMES)
            with pytest.raises(VideoDecodeError, match="out of range"):
                reader.read(-1)

    def test_backward_seek_lands_on_the_requested_frame(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            reader.read(FIXTURE_FRAMES - 1)
            assert reader.read(2).index == 2

    def test_short_forward_jump_lands_on_the_requested_frame(self, synthetic_video: Path) -> None:
        # Below GRAB_FORWARD_LIMIT this is served by grabbing through the gap
        # rather than seeking; the point is that both paths agree.
        with VideoReader(synthetic_video) as reader:
            reader.read(0)
            target = min(GRAB_FORWARD_LIMIT - 1, FIXTURE_FRAMES - 1)
            assert reader.read(target).index == target

    def test_grab_and_seek_paths_agree_on_content(self, synthetic_video: Path) -> None:
        target = min(GRAB_FORWARD_LIMIT - 1, FIXTURE_FRAMES - 1)
        with VideoReader(synthetic_video) as grabbed_reader:
            grabbed_reader.read(0)
            grabbed = grabbed_reader.read(target).data.copy()
        with VideoReader(synthetic_video) as sought_reader:
            sought_reader.read(FIXTURE_FRAMES - 1)  # force a backward seek next
            sought = sought_reader.read(target).data.copy()
        assert grabbed.shape == sought.shape
        assert abs(int(grabbed.mean()) - int(sought.mean())) <= 1

    def test_repeated_read_of_the_same_index_is_stable(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            first = reader.read(6).data.copy()
            second = reader.read(6).data.copy()
            assert abs(int(first.mean()) - int(second.mean())) <= 1


class TestProxyScaling:
    def test_max_width_downscales_and_keeps_aspect(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            frame = reader.read(0, max_width=80)
            assert frame.width == 80
            assert frame.height == pytest.approx(FIXTURE_HEIGHT * 80 / FIXTURE_WIDTH, abs=1)

    def test_max_width_never_upscales(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video) as reader:
            assert reader.read(0, max_width=FIXTURE_WIDTH * 4).width == FIXTURE_WIDTH


class TestIdentity:
    def test_identity_is_stable_and_names_the_decoder(self) -> None:
        assert decoder_identity() == decoder_identity()
        assert decoder_identity().startswith("opencv-")
        assert "policy-" in decoder_identity()


class TestLumaPath:
    """`luma=True` declines the colour convert. What must survive is *which* frame.

    The fixture's ramp lives in the blue channel, which luma weights at 0.114 —
    so a luma read of frame `n` is a dim but strictly increasing function of `n`.
    That is enough to catch the failure that matters here: a format change that
    also moved the seek, which would decode fine and land somewhere else.
    """

    def test_luma_frames_are_single_channel_at_source_size(self, synthetic_video: Path) -> None:
        with VideoReader(synthetic_video, luma=True) as reader:
            frame = reader.read(3)
            assert frame.channels is ChannelSpec.GRAY
            assert frame.data.ndim == 2
            assert frame.data.shape == (FIXTURE_HEIGHT, FIXTURE_WIDTH)

    def test_the_colour_path_is_untouched_by_default(self, synthetic_video: Path) -> None:
        """The fallback stays byte-identical: no caller gets luma without asking."""
        with VideoReader(synthetic_video) as reader:
            assert reader.luma is False
            assert reader.read(3).channels is ChannelSpec.BGR

    def test_luma_still_lands_on_the_frame_that_was_asked_for(self, synthetic_video: Path) -> None:
        """Seek accuracy is the property `reader.py` is shaped around; it holds here.

        Both seek paths, because `_position_at` chooses between grabbing forward
        and `set(POS_FRAMES)` and only one of them retrieves through the changed
        format.
        """
        with VideoReader(synthetic_video, luma=True) as reader:
            forward = [float(reader.read(index).data.mean()) for index in range(0, 12, 3)]
            assert forward == sorted(forward)
            assert forward[0] < forward[-1]

            far = float(reader.read(30).data.mean())
            back = float(reader.read(2).data.mean())
            assert back < far

    def test_a_plane_that_is_not_the_plane_asked_for_raises(
        self, synthetic_video: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The guard that replaces the per-frame warning `sieve/__init__.py` silences.

        `CAP_PROP_CONVERT_RGB = 0` is a request, and a build that answers it with
        a packed layout would hand back an array this reader must not interpret
        as luma — plausible pixels, wrong pixels, and nothing downstream able to
        tell. Simulated by returning a three-channel frame, which is exactly what
        a build ignoring the property would produce.
        """
        reader = VideoReader(synthetic_video, luma=True)
        packed = np.zeros((FIXTURE_HEIGHT, FIXTURE_WIDTH, 3), np.uint8)

        class PackedCapture:
            """Stands in for a build that ignores `CAP_PROP_CONVERT_RGB`.

            The capture itself cannot be patched — `cv2.VideoCapture.read` is
            read-only — so the whole object is replaced. Only `read` is reached:
            the reader is freshly opened, so `_position_at(0)` is a no-op.
            """

            def read(self) -> tuple[bool, object]:
                return True, packed

        monkeypatch.setattr(reader, "_capture", PackedCapture())
        with pytest.raises(VideoDecodeError, match="asked for the luma plane"):
            reader.read(0)
