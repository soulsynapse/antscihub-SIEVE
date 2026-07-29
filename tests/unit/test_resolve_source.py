


















from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, ChannelSpec, Frame
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.resolve_source import OffsetFrameSource, ResolvedSource, resolve

ARENA = ROI(x=16, y=8, width=64, height=48)
SPAN = ClipRange(start=10, end=20)


WANT = ClipRange(start=12, end=18)
PARENT_IDENTITY = "footage|123|456"


@pytest.fixture
def parent(tmp_path: Path) -> Path:

    path = tmp_path / "footage.mp4"
    path.write_bytes(b"not really a video")
    return path


@pytest.fixture
def record(tmp_path: Path) -> CropArtifact:

    crop = tmp_path / "arena-1-luma-10-20.mkv"
    crop.write_bytes(b"not really a video either")
    return CropArtifact(
        path=crop.name,
        roi=ARENA,
        format="luma",
        span=SPAN,
        cut_from=PARENT_IDENTITY,
        decoder="decoder|1",
    )


def _replicate(roi: ROI = ARENA) -> Replicate:
    return Replicate(replicate_id="a", name="Arena 1", roi=roi)


def _resolve(
    crops: tuple[CropArtifact, ...],
    tmp_path: Path,
    parent: Path,
    *,
    replicate: Replicate | None = None,
    parent_identity: str = PARENT_IDENTITY,
    luma: bool = True,
    want: ClipRange = WANT,
) -> ResolvedSource:
    return resolve(
        crops,
        _replicate() if replicate is None else replicate,
        project_dir=tmp_path,
        parent=parent,
        parent_identity=parent_identity,
        luma=luma,
        want=want,
    )


class TestAMatchingRecordIsServed:
    def test_the_artifact_becomes_the_source_with_no_region_left_to_cut(
        self, tmp_path: Path, parent: Path, record: CropArtifact
    ) -> None:







        resolved = _resolve((record,), tmp_path, parent)

        assert resolved.path == record.resolve(tmp_path)
        assert resolved.identity == source_identity(record.resolve(tmp_path))
        assert resolved.identity != PARENT_IDENTITY
        assert resolved.pre_cropped
        assert resolved.first_index == SPAN.start
        assert resolved.artifact is record

    def test_a_project_with_no_fan_out_never_resolves_to_a_crop(
        self, tmp_path: Path, parent: Path, record: CropArtifact
    ) -> None:

        resolved = resolve(
            (record,),
            None,
            project_dir=tmp_path,
            parent=parent,
            parent_identity=PARENT_IDENTITY,
            luma=True,
            want=WANT,
        )

        assert resolved.path == parent
        assert not resolved.pre_cropped


class TestEveryWayARecordStopsMatchingFallsBackToTheParent:


    def _assert_parent(self, resolved: ResolvedSource, parent: Path) -> None:
        assert resolved.path == parent
        assert not resolved.pre_cropped
        assert resolved.first_index == 0
        assert resolved.artifact is None

    def test_a_box_that_moved(self, tmp_path: Path, parent: Path, record: CropArtifact) -> None:

        moved = _replicate(ROI(x=17, y=8, width=64, height=48))

        self._assert_parent(_resolve((record,), tmp_path, parent, replicate=moved), parent)

    def test_a_re_exported_parent(self, tmp_path: Path, parent: Path, record: CropArtifact) -> None:

        self._assert_parent(
            _resolve((record,), tmp_path, parent, parent_identity="footage|999|999"), parent
        )

    def test_a_session_wanting_the_other_decode_format(
        self, tmp_path: Path, parent: Path, record: CropArtifact
    ) -> None:

        self._assert_parent(_resolve((record,), tmp_path, parent, luma=False), parent)

    def test_a_file_that_is_gone(self, tmp_path: Path, parent: Path, record: CropArtifact) -> None:

        record.resolve(tmp_path).unlink()

        self._assert_parent(_resolve((record,), tmp_path, parent), parent)

    @pytest.mark.parametrize(
        ("start", "end"),
        [(SPAN.start - 1, WANT.end), (WANT.start, SPAN.end + 1)],
        ids=["reaching-before", "reaching-after"],
    )
    def test_a_window_the_record_does_not_cover(
        self, tmp_path: Path, parent: Path, record: CropArtifact, start: int, end: int
    ) -> None:







        self._assert_parent(
            _resolve((record,), tmp_path, parent, want=ClipRange(start=start, end=end)), parent
        )

    def test_no_records_at_all(self, tmp_path: Path, parent: Path) -> None:

        self._assert_parent(_resolve((), tmp_path, parent), parent)


class TestTheFrameNumberingSeam:


    class _Fixed:


        def __init__(self) -> None:
            self.asked: list[int] = []

        def read(self, index: int) -> Frame:
            self.asked.append(index)
            return Frame(
                data=np.zeros((2, 2), dtype=np.uint8), index=index, channels=ChannelSpec.GRAY
            )

    def test_a_source_index_reads_the_offset_frame_and_keeps_its_own_number(self) -> None:







        inner = self._Fixed()

        frame = OffsetFrameSource(inner, 10).read(12)

        assert inner.asked == [2]
        assert frame.index == 12

    def test_reading_before_the_footage_begins_is_refused(self) -> None:






        with pytest.raises(VideoDecodeError, match="before this footage begins"):
            OffsetFrameSource(self._Fixed(), 10).read(9)

    def test_the_parent_is_not_wrapped_at_all(self, tmp_path: Path, parent: Path) -> None:





        inner = self._Fixed()

        assert _resolve((), tmp_path, parent).wrap(inner) is inner
