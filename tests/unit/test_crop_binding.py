
























from __future__ import annotations

from pathlib import Path

import pytest

from sieve.core.pipeline_model import ClipRange, CropArtifact, Project, SourceRef
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.crop_binding import CropBacking, CropState, backing_for

ARENA = ROI(x=100, y=100, width=64, height=48)
SPAN = ClipRange(start=10, end=20)

WANT = ClipRange(start=12, end=18)
SOURCE = "footage|123|456"


@pytest.fixture
def record(tmp_path: Path) -> CropArtifact:

    crop = tmp_path / "arena-1-luma-10-20.mkv"
    crop.write_bytes(b"not really a video")
    return CropArtifact(
        path=crop.name,
        roi=ARENA,
        format="luma",
        span=SPAN,
        cut_from=SOURCE,
        decoder="decoder|1",
    )


@pytest.fixture
def project() -> Project:

    return Project(
        source=SourceRef(path="arena.MP4"),
        replicates=(_replicate(),),
    )


def _replicate(roi: ROI = ARENA, replicate_id: str = "a") -> Replicate:
    return Replicate(replicate_id=replicate_id, name=f"Arena {replicate_id}", roi=roi)


def _backing(
    crops: tuple[CropArtifact, ...],
    tmp_path: Path,
    *,
    replicates: tuple[Replicate, ...] | None = None,
    index: int = 0,
    source: str = SOURCE,
    luma: bool = True,
    window: ClipRange | None = WANT,
) -> CropBacking:
    return backing_for(
        crops,
        index,
        (_replicate(),) if replicates is None else replicates,
        source=source,
        luma=luma,
        project_dir=tmp_path,
        window=window,
    )


class TestTheGoalState:
    def test_a_matching_record_covering_the_window_is_at_rest(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:

        backing = _backing((record,), tmp_path)

        assert backing.state is CropState.AT_REST
        assert backing.artifact is record
        assert backing.reason == ""

    def test_no_records_at_all_is_absent(self, tmp_path: Path) -> None:

        backing = _backing((), tmp_path)

        assert backing.state is CropState.ABSENT
        assert backing.artifact is None


class TestEveryNearMissReportsStaleWithTheClauseThatMissed:







    def test_a_file_that_is_gone(self, tmp_path: Path, record: CropArtifact) -> None:

        record.resolve(tmp_path).unlink()

        backing = _backing((record,), tmp_path)

        assert backing.state is CropState.STALE
        assert backing.artifact is record
        assert record.path in backing.reason

    def test_a_re_exported_source(self, tmp_path: Path, record: CropArtifact) -> None:

        backing = _backing((record,), tmp_path, source="footage|999|999")

        assert backing.state is CropState.STALE
        assert "re-exported" in backing.reason

    def test_a_chain_that_now_decodes_the_other_format(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:

        backing = _backing((record,), tmp_path, luma=False)

        assert backing.state is CropState.STALE
        assert "luma" in backing.reason and "colour" in backing.reason

    @pytest.mark.parametrize(
        ("start", "end"),
        [(SPAN.start - 1, WANT.end), (WANT.start, SPAN.end + 1)],
        ids=["reaching-before", "reaching-after"],
    )
    def test_a_window_widened_past_what_was_cut(
        self, tmp_path: Path, record: CropArtifact, start: int, end: int
    ) -> None:








        backing = _backing((record,), tmp_path, window=ClipRange(start=start, end=end))

        assert backing.state is CropState.STALE
        assert backing.artifact is record


class TestAnOrphanIsAttributedByOverlapOrNotAtAll:


    def test_a_record_overlapping_exactly_one_replicate_is_shown_there(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:

        moved = _replicate(ROI(x=110, y=100, width=64, height=48))

        backing = _backing((record,), tmp_path, replicates=(moved,))

        assert backing.state is CropState.STALE
        assert backing.artifact is record
        assert "moved" in backing.reason

    def test_a_record_two_replicates_overlap_is_shown_on_neither(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:






        one = _replicate(ROI(x=110, y=100, width=64, height=48), "a")
        two = _replicate(ROI(x=130, y=100, width=64, height=48), "b")

        for index in (0, 1):
            backing = _backing((record,), tmp_path, replicates=(one, two), index=index)
            assert backing.state is CropState.ABSENT

    def test_a_record_touching_nobody_is_shown_on_nobody(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:

        elsewhere = _replicate(ROI(x=500, y=500, width=64, height=48))

        assert _backing((record,), tmp_path, replicates=(elsewhere,)).state is CropState.ABSENT


class TestTheDocumentOwnsTheWholeSet:


    def test_replacing_the_set_wholesale_is_validated_not_assigned(
        self, project: Project, record: CropArtifact
    ) -> None:






        twice = (record, record.model_copy(update={"path": "written-again.mkv"}))

        with pytest.raises(ValueError, match="same cut"):
            project.with_crops(twice)

    def test_a_record_is_dropped_by_its_cut_not_by_its_path(
        self, project: Project, record: CropArtifact
    ) -> None:






        held = project.with_crops((record,))
        renamed = record.model_copy(update={"path": "some-other-name.mkv"})

        assert held.without_crop(renamed).crops == ()
