"""ROI arithmetic and metadata derivation."""

from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from sieve.core.types import ROI, ChannelSpec, Frame, FrameCount, MediaTime, VideoMetadata

#: The rate the whole exactness argument is about — see `test_quantities.py`,
#: which makes the same point one layer down, on the types alone.
NTSC = Fraction(30000, 1001)


class TestROI:
    def test_from_corners_normalizes_order(self) -> None:
        assert ROI.from_corners(90, 70, 10, 20) == ROI(x=10, y=20, width=80, height=50)

    def test_rejects_zero_extent(self) -> None:
        with pytest.raises(ValueError, match="positive extent"):
            ROI(x=0, y=0, width=0, height=10)

    def test_rejects_negative_origin(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            ROI(x=-1, y=0, width=10, height=10)

    def test_edges_and_area(self) -> None:
        roi = ROI(x=10, y=20, width=30, height=40)
        assert (roi.right, roi.bottom, roi.area) == (40, 60, 1200)

    def test_clamped_to_trims_overhang(self) -> None:
        roi = ROI(x=90, y=90, width=50, height=50)
        assert roi.clamped_to(100, 100) == ROI(x=90, y=90, width=10, height=10)

    def test_clamped_to_is_identity_when_inside(self) -> None:
        roi = ROI(x=5, y=5, width=10, height=10)
        assert roi.clamped_to(100, 100) == roi

    def test_clamped_to_never_produces_empty_region(self) -> None:
        # An ROI entirely outside the frame still has to come back valid,
        # because the alternative is raising from inside a paint or edit path.
        clamped = ROI(x=500, y=500, width=10, height=10).clamped_to(100, 100)
        assert clamped.width >= 1 and clamped.height >= 1

    def test_crop_selects_rows_then_columns(self) -> None:
        array = np.arange(100, dtype=np.uint8).reshape(10, 10)
        cropped = ROI(x=2, y=1, width=3, height=4).crop(array)
        assert cropped.shape == (4, 3)
        assert cropped[0, 0] == array[1, 2]


class TestVideoMetadata:
    def _metadata(self, fps: Fraction) -> VideoMetadata:
        return VideoMetadata(path=Path("clip.mp4"), width=640, height=480, fps=fps, frame_count=300)

    def test_duration_from_frame_count(self) -> None:
        assert self._metadata(Fraction(30)).duration_seconds == MediaTime(Fraction(10))

    def test_unusable_fps_yields_zero_rather_than_dividing(self) -> None:
        zero = MediaTime(Fraction(0))
        assert self._metadata(Fraction(0)).duration_seconds == zero
        assert self._metadata(Fraction(0)).timestamp_of(100) == zero

    def test_timestamp_of_frame(self) -> None:
        assert self._metadata(Fraction(50)).timestamp_of(125) == MediaTime(Fraction(5, 2))

    def test_a_timestamp_lands_back_on_the_frame_it_came_from(self) -> None:
        """Frame 15 of an NTSC source, out to time and back. The whole item.

        This is the arithmetic `test_quantities.py` pins on the types, asked of
        the metadata that actually produces the number — which is where it used
        to fail, because `fps` was the `double` `CAP_PROP_FPS` returned and no
        exactness downstream could recover what that division threw away. The
        second assertion is the old answer: a whole frame, at frame 15, in the
        first second of footage.
        """
        metadata = self._metadata(NTSC)

        assert FrameCount.spanning(metadata.timestamp_of(15), metadata.fps) == FrameCount(15)
        seconds = float(metadata.timestamp_of(15).seconds)
        assert math.floor(seconds * float(metadata.fps)) == 14


class TestFrame:
    def test_dimensions_read_from_the_array(self) -> None:
        frame = Frame(
            data=np.zeros((48, 64, 3), dtype=np.uint8),
            index=7,
            channels=ChannelSpec.BGR,
        )
        assert (frame.width, frame.height, frame.index) == (64, 48, 7)
        assert frame.dtype == np.uint8
        assert frame.channels.channel_count == 3

    def test_gray_declares_one_channel(self) -> None:
        assert ChannelSpec.GRAY.channel_count == 1

    def test_channel_count_leaves_str_count_intact(self) -> None:
        assert ChannelSpec.BGR.count("b") == 1
