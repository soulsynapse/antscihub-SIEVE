"""Which file a replicate reads, and what happens when the record goes stale.

Two claims, and the second is the one worth the file. The first is that a
matching record is served. The second is that every way a record can stop
matching fails toward the parent *independently* — one clause quietly stuck
true would keep serving a crop of a box the user has since moved, and the pixels
would be plausible, in the right shape, for the right frames, and of the wrong
part of the arena.

So each clause gets its own test that flips exactly that clause from the same
matching baseline. A single "the mismatched record is declined" test would pass
with four of the five conditions deleted.

Nothing here opens a video: `resolve` stats files and compares records, and the
one thing it needs from a file is that it exists. That is why these are unit
tests over an empty file rather than integration tests over a real encode —
`tests/integration/test_crop_serving.py` is where real pixels come back.
"""

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
#: A window strictly inside the record's span, so that widening it in either
#: direction is a one-number edit in a test rather than a rebuild of the record.
WANT = ClipRange(start=12, end=18)
PARENT_IDENTITY = "footage|123|456"


@pytest.fixture
def parent(tmp_path: Path) -> Path:
    """A stand-in for the source video. Never opened, only named."""
    path = tmp_path / "footage.mp4"
    path.write_bytes(b"not really a video")
    return path


@pytest.fixture
def record(tmp_path: Path) -> CropArtifact:
    """A record whose file exists and which backs `_replicate()` over `SPAN`."""
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
        """The whole of what serving means, in four fields.

        The identity is the artifact's own — not the parent's — which is the
        child-source model the writer settled; `pre_cropped` is what stops the
        executor cutting a region out of a region; and `first_index` is the one
        translation between the two frame numberings there is.
        """
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
        """Every record is a crop of *some* arena; the baseline is the frame."""
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
    """One test per clause, each flipping exactly one thing from the baseline."""

    def _assert_parent(self, resolved: ResolvedSource, parent: Path) -> None:
        assert resolved.path == parent
        assert not resolved.pre_cropped
        assert resolved.first_index == 0
        assert resolved.artifact is None

    def test_a_box_that_moved(self, tmp_path: Path, parent: Path, record: CropArtifact) -> None:
        """The failure the whole predicate exists for: right file, wrong region."""
        moved = _replicate(ROI(x=17, y=8, width=64, height=48))

        self._assert_parent(_resolve((record,), tmp_path, parent, replicate=moved), parent)

    def test_a_re_exported_parent(self, tmp_path: Path, parent: Path, record: CropArtifact) -> None:
        """`cut_from` is matched so a crop of yesterday's footage stops serving."""
        self._assert_parent(
            _resolve((record,), tmp_path, parent, parent_identity="footage|999|999"), parent
        )

    def test_a_session_wanting_the_other_decode_format(
        self, tmp_path: Path, parent: Path, record: CropArtifact
    ) -> None:
        """A luma read of a colour file is the trap the codec finding measured."""
        self._assert_parent(_resolve((record,), tmp_path, parent, luma=False), parent)

    def test_a_file_that_is_gone(self, tmp_path: Path, parent: Path, record: CropArtifact) -> None:
        """A record outliving its file un-backs rather than raises."""
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
        """Partial cover un-backs the replicate rather than half-serving it.

        Both directions, because they fail for different reasons and only one of
        them would be caught by a comparison written the obvious way round: a
        window reaching *before* the cut has no frames at all there, and one
        reaching *after* it runs out partway through.
        """
        self._assert_parent(
            _resolve((record,), tmp_path, parent, want=ClipRange(start=start, end=end)), parent
        )

    def test_no_records_at_all(self, tmp_path: Path, parent: Path) -> None:
        """The status quo, and the path every project takes until one is cut."""
        self._assert_parent(_resolve((), tmp_path, parent), parent)


class TestTheFrameNumberingSeam:
    """Artifact frame 0 is source frame `span.start`, and only here."""

    class _Fixed:
        """A reader whose frames say which index they were asked for."""

        def __init__(self) -> None:
            self.asked: list[int] = []

        def read(self, index: int) -> Frame:
            self.asked.append(index)
            return Frame(
                data=np.zeros((2, 2), dtype=np.uint8), index=index, channels=ChannelSpec.GRAY
            )

    def test_a_source_index_reads_the_offset_frame_and_keeps_its_own_number(self) -> None:
        """Both halves, because getting one right and the other wrong is silent.

        Reading the wrong frame shows up as a shifted signal nobody can date.
        Returning the inner index shows up as `executor._run_node` refusing the
        *first filter* for renumbering its output — a true message about the
        wrong module.
        """
        inner = self._Fixed()

        frame = OffsetFrameSource(inner, 10).read(12)

        assert inner.asked == [2]
        assert frame.index == 12

    def test_reading_before_the_footage_begins_is_refused(self) -> None:
        """The guard behind `ExecutionPlan.source_start`.

        The plan should have clamped and never asked. If it ever does not, a
        negative offset reaching a reader is a frame from the wrong end of the
        file served as if it were the right one.
        """
        with pytest.raises(VideoDecodeError, match="before this footage begins"):
            OffsetFrameSource(self._Fixed(), 10).read(9)

    def test_the_parent_is_not_wrapped_at_all(self, tmp_path: Path, parent: Path) -> None:
        """Zero offset means the same object, not an identity wrapper.

        A per-frame indirection on the path every unbacked run takes would be
        paid by every project that has never materialized anything.
        """
        inner = self._Fixed()

        assert _resolve((), tmp_path, parent).wrap(inner) is inner
