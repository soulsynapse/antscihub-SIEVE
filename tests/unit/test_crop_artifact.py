"""The crop's output as a file: the tool and `storage/crop_writer.py`, together.

Neither half is new here — `write_ffv1` landed with 03.2 for a decode fixture,
and the kernel is `test_crop.py`'s subject. What is new is that they meet, and
the meeting is the one place a lossless path can stop being lossless without
saying so: v2 measured an encoding that advertised `-qp 0`, reported no error,
and served pixels matching no input frame on every frame of its gray variant
(`docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md` in v2). Byte-identical
read-back is the only assertion that catches that, so it is asserted for both
formats a crop can be written in rather than for the one that happened to work.

This is not Phase 5. Nothing here names a replicate, a `CropRecord`, or where
the file would live — `pipeline/materialize.py` owns identity and this owns the
pixels, which is the split `crop_writer`'s own docstring draws.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.types import ROI, ChannelSpec, Frame, FrameSpan
from sieve.decode.reader import VideoReader
from sieve.storage.crop_writer import CropWriteError, write_ffv1
from sieve.tools.crop import CropParams, run

SOURCE_WIDTH, SOURCE_HEIGHT, FRAMES = 160, 120, 6
RATE = Fraction(20)

#: Inside the frame on every side, and at an odd origin in both axes: a crop
#: aligned to the macroblock grid would survive a codec that quietly re-aligned
#: it, and this one would not.
REGION = ROI(x=11, y=7, width=48, height=32)


def source_frame(index: int, *, colour: bool) -> Frame:
    """A frame whose every pixel is a function of its position and the index.

    Both terms matter. Position, so a crop taken at the wrong offset comes back
    as different numbers rather than as the same flat field; index, so a decoder
    that served a neighbouring frame is caught rather than absorbed.
    """
    plane = ((np.arange(SOURCE_HEIGHT * SOURCE_WIDTH) + index * 7) % 251).astype(np.uint8)
    plane = plane.reshape(SOURCE_HEIGHT, SOURCE_WIDTH)
    if not colour:
        return Frame(data=plane, index=index, channels=ChannelSpec.GRAY)
    data = np.stack([plane, (plane + 83) % 251, (plane + 167) % 251], axis=-1)
    return Frame(data=data.astype(np.uint8), index=index, channels=ChannelSpec.BGR)


def crops(*, colour: bool, region: ROI = REGION) -> list[NDArray[np.uint8]]:
    """Every source frame through one crop node, as the writer will see them."""
    params = CropParams(region=region)
    return [
        run(params, FrameSpan((source_frame(index, colour=colour),)), None).data
        for index in range(FRAMES)
    ]


@pytest.mark.parametrize("colour", [False, True], ids=["luma", "bgr"])
def test_every_cropped_frame_comes_back_byte_identical(tmp_path: Path, colour: bool) -> None:
    """The guard the codec finding exists to demand, on both formats.

    Equality rather than a tolerance: the failure being excluded is not drift,
    it is a file that decodes cleanly into pixels that were never written, and
    any tolerance at all would let the whole of that through.
    """
    written = crops(colour=colour)
    path = tmp_path / "crop.mkv"

    assert write_ffv1(path, iter(written), fps=RATE) == FRAMES

    with VideoReader(path, luma=not colour) as reader:
        for index, expected in enumerate(written):
            assert np.array_equal(reader.read(index).data, expected), f"frame {index} differs"


def test_the_file_is_the_size_of_the_region_not_of_the_source(tmp_path: Path) -> None:
    # The point of writing a crop at all. A writer that took its geometry from
    # anything but the arrays it was handed would produce a correct-looking file
    # of the wrong footage, and the frame count is checked beside it because a
    # truncated stream is the other way a clip stops being the clip.
    path = tmp_path / "crop.mkv"
    write_ffv1(path, iter(crops(colour=False)), fps=RATE)

    with VideoReader(path, luma=True) as reader:
        assert (reader.metadata.width, reader.metadata.height) == (REGION.width, REGION.height)
        assert reader.metadata.frame_count == FRAMES


def test_a_region_overhanging_the_source_is_written_at_the_size_it_clamped_to(
    tmp_path: Path,
) -> None:
    # The clamp is the tool's, and the file inherits it: a region drawn against
    # a larger frame than the decoder returns is written as the part that
    # exists, rather than refused at the encoder for a shape mismatch.
    overhang = ROI(x=SOURCE_WIDTH - 10, y=SOURCE_HEIGHT - 4, width=64, height=48)
    path = tmp_path / "crop.mkv"

    write_ffv1(path, iter(crops(colour=False, region=overhang)), fps=RATE)

    with VideoReader(path, luma=True) as reader:
        assert (reader.metadata.width, reader.metadata.height) == (10, 4)


def test_a_source_that_changes_size_mid_run_is_refused_rather_than_written(
    tmp_path: Path,
) -> None:
    """One crop node over two frame sizes is not an artifact, and must not become one.

    The tool clamps per frame, so a source whose frames changed geometry — a
    reader falling back to a proxy, a concatenated clip — yields two crop sizes
    from one unchanged parameter. The writer is where that stops: a file whose
    dimensions changed halfway cannot be indexed by frame number, so nothing
    downstream could read it correctly and the refusal is the only outcome that
    does not produce a silently unusable dataset.
    """
    params = CropParams(region=ROI(x=0, y=0, width=64, height=48))
    full = source_frame(0, colour=False)
    narrow = Frame(data=full.data[:, :40], index=1, channels=ChannelSpec.GRAY)
    frames = [run(params, FrameSpan((frame,)), None).data for frame in (full, narrow)]

    with pytest.raises(CropWriteError, match="geometry cannot change mid-file"):
        write_ffv1(tmp_path / "crop.mkv", iter(frames), fps=RATE)
