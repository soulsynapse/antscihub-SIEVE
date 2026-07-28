"""Which of the four states a card is looking at, and what the freeze follows.

`test_resolve_source.py` already pins the match rule itself; nothing here
re-tests whether a record backs a replicate. What this file pins is the part
`backs` refuses to answer, and it is three separable claims:

**Absent and stale are different claims** (rule 6). A record that was cut and
then orphaned must not render as one that was never cut, or the user cuts it
again. So each way a record can near-miss gets its own test flipping exactly
that clause — a single "the mismatch shows as stale" test would pass with three
of the four clauses deleted, and the deleted ones would silently report ABSENT.

**An orphan is attributed geometrically, and a tie is attributed to nobody.**
The overlap rule's whole content is the case where it declines to answer; a
card that guesses which replicate a moved record belonged to is worse than one
that stays quiet about a file the user can still see in the folder.

**The frozen span is an intersection that is allowed to be empty.** Freezing to
an impossible span would refuse every clip edit including the ones that fix it,
so the empty case must return None rather than a reversed range.

Nothing here opens a video, for `test_resolve_source.py`'s reason: the only
thing a file is asked is whether it exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.core.pipeline_model import ClipRange, CropArtifact, Project, SourceRef
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.crop_binding import CropBacking, CropState, backing_for, frozen_span

ARENA = ROI(x=100, y=100, width=64, height=48)
SPAN = ClipRange(start=10, end=20)
#: Strictly inside the record's span, so widening it is a one-number edit.
WANT = ClipRange(start=12, end=18)
SOURCE = "footage|123|456"


@pytest.fixture
def record(tmp_path: Path) -> CropArtifact:
    """A record whose file exists and which backs `_replicate()` over `SPAN`."""
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
    """One arena, no crops yet — the state a discard gesture starts from."""
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
    def test_a_matching_record_covering_the_window_is_at_rest_and_freezes(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:
        """At rest carries the record, says nothing, and binds the freeze."""
        backing = _backing((record,), tmp_path)

        assert backing.state is CropState.AT_REST
        assert backing.artifact is record
        assert backing.reason == ""
        assert backing.frozen

    def test_no_records_at_all_is_absent_and_freezes_nothing(self, tmp_path: Path) -> None:
        """The status quo, and the path every project takes until one is cut."""
        backing = _backing((), tmp_path)

        assert backing.state is CropState.ABSENT
        assert backing.artifact is None
        assert not backing.frozen


class TestEveryNearMissReportsStaleWithTheClauseThatMissed:
    """One test per clause. Each asserts the state *and* that a reason exists.

    A clause that fell through to `_orphan_for` would still report STALE — with
    a sentence about a region that moved, which for a box that did not move is
    a true-sounding lie. So each test also pins the substance of the sentence.
    """

    def test_a_file_that_is_gone(self, tmp_path: Path, record: CropArtifact) -> None:
        """The record outliving its file: a thing the user can go and look for."""
        record.resolve(tmp_path).unlink()

        backing = _backing((record,), tmp_path)

        assert backing.state is CropState.STALE
        assert backing.artifact is record
        assert record.path in backing.reason

    def test_a_re_exported_source(self, tmp_path: Path, record: CropArtifact) -> None:
        """A crop of yesterday's footage stops backing, and says so."""
        backing = _backing((record,), tmp_path, source="footage|999|999")

        assert backing.state is CropState.STALE
        assert "re-exported" in backing.reason

    def test_a_chain_that_now_decodes_the_other_format(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:
        """The wrong-pixels trap the codec finding measured, named on the card."""
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
        """Both directions, because only one is caught by the obvious comparison.

        This clause is the one `backs` does not evaluate at all — the record
        still matches on parentage, geometry, and format, and it is the window
        underneath it that moved. Reported as stale rather than served, and
        stale rather than absent: the file is still on disk and re-cutting it
        wider is the remedy the card offers.
        """
        backing = _backing((record,), tmp_path, window=ClipRange(start=start, end=end))

        assert backing.state is CropState.STALE
        assert backing.artifact is record
        assert not backing.frozen

    def test_a_stale_record_never_freezes_the_edits_that_would_fix_it(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:
        """Rule 6's mirror direction, and the reason `frozen` is AT_REST only.

        A stale record is already orphaned. Freezing the box to protect a file
        that has stopped serving would trap the user in the one state they most
        need to edit their way out of.
        """
        record.resolve(tmp_path).unlink()

        assert not _backing((record,), tmp_path).frozen


class TestAnOrphanIsAttributedByOverlapOrNotAtAll:
    """The case with no answer in the model: a record whose box moved."""

    def test_a_record_overlapping_exactly_one_replicate_is_shown_there(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:
        """The box moved a little; the file it orphaned is still worth naming."""
        moved = _replicate(ROI(x=110, y=100, width=64, height=48))

        backing = _backing((record,), tmp_path, replicates=(moved,))

        assert backing.state is CropState.STALE
        assert backing.artifact is record
        assert "moved" in backing.reason

    def test_a_record_two_replicates_overlap_is_shown_on_neither(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:
        """A card that guesses is worse than one that stays quiet.

        Both replicates are asked, because attribution failing in one direction
        only would put the orphan on whichever card happened to be checked
        first — which is a guess wearing the overlap rule's clothes.
        """
        one = _replicate(ROI(x=110, y=100, width=64, height=48), "a")
        two = _replicate(ROI(x=130, y=100, width=64, height=48), "b")

        for index in (0, 1):
            backing = _backing((record,), tmp_path, replicates=(one, two), index=index)
            assert backing.state is CropState.ABSENT

    def test_a_record_touching_nobody_is_shown_on_nobody(
        self, tmp_path: Path, record: CropArtifact
    ) -> None:
        """Absent is the honest answer for a file no card can claim."""
        elsewhere = _replicate(ROI(x=500, y=500, width=64, height=48))

        assert _backing((record,), tmp_path, replicates=(elsewhere,)).state is CropState.ABSENT


class TestTheFrozenSpanIsAnIntersection:
    def _record(self, tmp_path: Path, roi: ROI, span: ClipRange, name: str) -> CropArtifact:
        path = tmp_path / name
        path.write_bytes(b"not really a video")
        return CropArtifact(
            path=path.name,
            roi=roi,
            format="luma",
            span=span,
            cut_from=SOURCE,
            decoder="decoder|1",
        )

    def test_two_backed_replicates_freeze_the_overlap(self, tmp_path: Path) -> None:
        """Not the union, and not the first one found: the common span."""
        first_roi = ROI(x=100, y=100, width=64, height=48)
        second_roi = ROI(x=300, y=100, width=64, height=48)
        crops = (
            self._record(tmp_path, first_roi, ClipRange(start=10, end=30), "one.mkv"),
            self._record(tmp_path, second_roi, ClipRange(start=20, end=40), "two.mkv"),
        )
        replicates = (_replicate(first_roi, "a"), _replicate(second_roi, "b"))

        span = frozen_span(crops, replicates, source=SOURCE, luma=True, project_dir=tmp_path)

        assert span == ClipRange(start=20, end=30)

    def test_records_with_no_common_span_freeze_nothing(self, tmp_path: Path) -> None:
        """An impossible freeze would refuse the edits that resolve it.

        No clip preserves both records, so the honest state is not a reversed
        range and not the first record's span — it is no freeze at all, leaving
        the user free to edit their way out of a project only hand-editing
        could have produced.
        """
        first_roi = ROI(x=100, y=100, width=64, height=48)
        second_roi = ROI(x=300, y=100, width=64, height=48)
        crops = (
            self._record(tmp_path, first_roi, ClipRange(start=10, end=20), "one.mkv"),
            self._record(tmp_path, second_roi, ClipRange(start=30, end=40), "two.mkv"),
        )
        replicates = (_replicate(first_roi, "a"), _replicate(second_roi, "b"))

        assert (
            frozen_span(crops, replicates, source=SOURCE, luma=True, project_dir=tmp_path) is None
        )

    def test_nothing_backed_freezes_nothing(self, tmp_path: Path, record: CropArtifact) -> None:
        """A record that does not back anything contributes no span."""
        elsewhere = (_replicate(ROI(x=500, y=500, width=64, height=48)),)

        assert (
            frozen_span((record,), elsewhere, source=SOURCE, luma=True, project_dir=tmp_path)
            is None
        )


class TestTheDocumentOwnsTheWholeSet:
    """`with_crops` and `without_crop`, which the card's discard gesture needs."""

    def test_replacing_the_set_wholesale_is_validated_not_assigned(
        self, project: Project, record: CropArtifact
    ) -> None:
        """The refusal `with_crop` cannot produce but a caller with a tuple can.

        Two records for one cut is the state the model refuses; a wholesale
        setter that assigned rather than validated would let the GUI write a
        document that `Project` itself would decline to load back.
        """
        twice = (record, record.model_copy(update={"path": "written-again.mkv"}))

        with pytest.raises(ValueError, match="same cut"):
            project.with_crops(twice)

    def test_a_record_is_dropped_by_its_cut_not_by_its_path(
        self, project: Project, record: CropArtifact
    ) -> None:
        """Keyed on identity, for `with_crop`'s reason: the cut is the thing.

        The path a cut happens to be recorded under is convenience, so discard
        must not depend on the caller holding the same spelling the document
        stored.
        """
        held = project.with_crops((record,))
        renamed = record.model_copy(update={"path": "some-other-name.mkv"})

        assert held.without_crop(renamed).crops == ()
