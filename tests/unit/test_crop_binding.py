"""Which of the four states a reader is looking at.

`CropRecord.backs` is pinned by `TestCropRecords` in `test_pipeline_model.py`;
nothing here re-tests whether a record backs a box. What this file pins is the
part `backs` refuses to answer, and it is four separable claims:

**Absent and stale are different claims.** A record that was cut and then
orphaned must not read as one that was never cut, or the user cuts it again. So
each way a record can near-miss gets its own case flipping exactly that clause —
a single "the mismatch shows as stale" case would pass with three of the four
clauses deleted, and the deleted ones would silently report ABSENT.

**An orphan is attributed geometrically, and a tie is attributed to nobody.**
The overlap rule's whole content is the case where it declines to answer.

**Evidence comes off the entry, and an unreadable entry refuses.** `stat` is the
only way a claim about a file can be wrong in a direction the record cannot show,
so `evidence_for` is pinned on both halves: that the numbers are the file's, and
that a missing one is `None` rather than a zero.

**The twin and this module cannot disagree.** `resolve` and `backing_for` walk
the same clauses over the same records, and the failure that would follow from
their drifting is silent in both directions — a run served by a file nothing
reports, or a report about a file no run opens. The last case here is the join.

Nothing below opens a video: the only thing a file is asked is whether it exists
and what `stat` says about it.
"""

from __future__ import annotations

from glob import glob
from pathlib import Path

import pytest

from sieve.core.pipeline_model import (
    CropRecord,
    Edge,
    Node,
    Pipeline,
    Project,
    SourceSpan,
)
from sieve.core.types import ROI
from sieve.pipeline.crop_binding import (
    CropBacking,
    CropState,
    backing_for,
    evidence_for,
)
from sieve.pipeline.crop_serving import serving_edit
from sieve.pipeline.source_home import SourceHome
from sieve.tools import discover
from tests.projects import rooted_on

ARENA = ROI(x=100, y=100, width=64, height=48)
CUT = "cut"
SPAN = SourceSpan(start=10, end=20)
#: Strictly inside the record's span, so widening it is a one-number edit.
WANT = SourceSpan(start=12, end=18)
SOURCE = "footage|123|456"


@pytest.fixture
def record(tmp_path: Path) -> CropRecord:
    """A record whose file exists and which backs `ARENA` over `SPAN`."""
    crop = tmp_path / "arena-1-luma-10-20.mkv"
    crop.write_bytes(b"not really a video")
    return CropRecord(
        path=crop.name,
        region=ARENA,
        format="luma",
        span=SPAN,
        cut_from=SOURCE,
        decoder="decoder|1",
    )


def _pinned(region: ROI) -> dict[str, dict[str, int]]:
    """A crop node's own box, as the document spells one."""
    return {
        "region": {
            "x": region.x,
            "y": region.y,
            "width": region.width,
            "height": region.height,
        }
    }


def _home(tmp_path: Path, source: str = SOURCE) -> SourceHome:
    return SourceHome(video=tmp_path / "arena.MP4", project_dir=tmp_path, identity=source)


def _backing(
    crops: tuple[CropRecord, ...],
    tmp_path: Path,
    *,
    regions: tuple[ROI, ...] = (ARENA,),
    index: int = 0,
    source: str = SOURCE,
    luma: bool = True,
    window: SourceSpan | None = WANT,
) -> CropBacking:
    return backing_for(
        crops,
        index,
        regions,
        home=_home(tmp_path, source),
        luma=luma,
        window=window,
    )


class TestTheGoalState:
    def test_a_matching_record_covering_the_window_is_at_rest(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """At rest carries the record and says nothing."""
        backing = _backing((record,), tmp_path)

        assert backing.state is CropState.AT_REST
        assert backing.record is record
        assert backing.reason == ""

    def test_no_records_at_all_is_absent(self, tmp_path: Path) -> None:
        """The status quo, and the path every project takes until one is cut."""
        backing = _backing((), tmp_path)

        assert backing.state is CropState.ABSENT
        assert backing.record is None


class TestEveryNearMissReportsStaleWithTheClauseThatMissed:
    """One case per clause. Each asserts the state *and* the sentence's substance.

    A clause that fell through to `_orphan_for` would still report STALE — with a
    sentence about a region that moved, which for a box that did not move is a
    true-sounding lie.
    """

    def test_a_file_that_is_gone(self, tmp_path: Path, record: CropRecord) -> None:
        """The record outliving its file: a thing the user can go and look for."""
        record.resolve(tmp_path).unlink()

        backing = _backing((record,), tmp_path)

        assert backing.state is CropState.STALE
        assert backing.record is record
        assert record.path in backing.reason

    def test_a_re_exported_source(self, tmp_path: Path, record: CropRecord) -> None:
        """A crop of yesterday's footage stops backing, and says so."""
        backing = _backing((record,), tmp_path, source="footage|999|999")

        assert backing.state is CropState.STALE
        assert "re-exported" in backing.reason

    def test_a_chain_that_now_decodes_the_other_format(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """The wrong-pixels trap the codec finding measured, named in the reason."""
        backing = _backing((record,), tmp_path, luma=False)

        assert backing.state is CropState.STALE
        assert "luma" in backing.reason and "colour" in backing.reason

    @pytest.mark.parametrize(
        ("start", "end"),
        [(SPAN.start - 1, WANT.end), (WANT.start, SPAN.end + 1)],
        ids=["reaching-before", "reaching-after"],
    )
    def test_a_window_widened_past_what_was_cut(
        self, tmp_path: Path, record: CropRecord, start: int, end: int
    ) -> None:
        """Both directions, because only one is caught by the obvious comparison.

        This clause is the one `backs` does not evaluate at all — the record
        still matches on parentage, geometry, and format, and it is the window
        underneath it that moved. Reported as stale rather than served, and stale
        rather than absent: the file is still on disk and re-cutting it wider is
        the remedy on offer.
        """
        backing = _backing((record,), tmp_path, window=SourceSpan(start=start, end=end))

        assert backing.state is CropState.STALE
        assert backing.record is record


class TestAnOrphanIsAttributedByOverlapOrNotAtAll:
    """The case with no answer in the model: a record whose box moved."""

    def test_a_record_overlapping_exactly_one_region_is_shown_there(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """The box moved a little; the file it orphaned is still worth naming."""
        moved = ROI(x=110, y=100, width=64, height=48)

        backing = _backing((record,), tmp_path, regions=(moved,))

        assert backing.state is CropState.STALE
        assert backing.record is record
        assert "moved" in backing.reason

    def test_a_record_two_regions_overlap_is_shown_on_neither(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """A reader that guesses is worse than one that stays quiet.

        Both boxes are asked, because attribution failing in one direction only
        would put the orphan on whichever was checked first — which is a guess
        wearing the overlap rule's clothes.
        """
        one = ROI(x=110, y=100, width=64, height=48)
        two = ROI(x=130, y=100, width=64, height=48)

        for index in (0, 1):
            backing = _backing((record,), tmp_path, regions=(one, two), index=index)
            assert backing.state is CropState.ABSENT

    def test_a_record_touching_nobody_is_shown_on_nobody(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """Absent is the honest answer for a file no box can claim."""
        elsewhere = ROI(x=500, y=500, width=64, height=48)

        assert _backing((record,), tmp_path, regions=(elsewhere,)).state is CropState.ABSENT


class TestEvidenceIsReadOffTheEntryOrRefused:
    def test_the_numbers_are_the_files_and_not_the_records(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """Size and mtime come from `stat`, which is the whole point of asking.

        A record carries a span and a format and nothing about the bytes, so an
        implementation that answered from the model would have to invent both —
        and would agree with this assertion only by accident.
        """
        written = (tmp_path / record.path).stat()

        evidence = evidence_for(record, tmp_path)

        assert evidence.readable
        assert evidence.size_bytes == written.st_size
        assert evidence.written_at == written.st_mtime
        assert evidence.path == tmp_path / record.path

    def test_a_file_that_is_gone_refuses_rather_than_reading_as_empty(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """Absent must not render as zero.

        This is the case a caller cannot avoid — `backs` proved the file existed
        at an earlier instant, and nothing stops it being deleted between then
        and the report being drawn — so a zero here would put "0.0 MB" under a
        record the user is being told is serving.
        """
        (tmp_path / record.path).unlink()

        evidence = evidence_for(record, tmp_path)

        assert not evidence.readable
        assert evidence.size_bytes is None
        assert evidence.written_at is None


class TestTheTwinsCannotDisagree:
    def test_writing_is_the_callers_state_and_is_never_derived(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """The one state with no record behind it, asserted where it is claimed.

        `CropState.WRITING` is in the enum so that a display has one state input
        rather than a state plus a flag that can contradict it — which only holds
        while this function cannot return it. Every clause is walked here, so a
        `WRITING` leaking out of any of them would show up.
        """
        elsewhere = ROI(x=500, y=500, width=64, height=48)
        walked = [
            _backing((record,), tmp_path),
            _backing((), tmp_path),
            _backing((record,), tmp_path, source="footage|999|999"),
            _backing((record,), tmp_path, luma=False),
            _backing((record,), tmp_path, window=SourceSpan(start=1, end=99)),
            _backing((record,), tmp_path, regions=(elsewhere,)),
        ]

        assert {backing.state for backing in walked} == {
            CropState.AT_REST,
            CropState.ABSENT,
            CropState.STALE,
        }

    def test_the_record_reported_at_rest_is_the_file_the_edit_wires_in(
        self, tmp_path: Path, record: CropRecord
    ) -> None:
        """The join between the twins, on the one input they both take.

        Drift between them is silent in both directions: a project wired to a
        file nothing reports, and a report about a file no graph reads. Asserted
        on `AT_REST` rather than on a near miss because that is the direction
        where both answers are non-trivial — a stale record makes both say
        "nothing to offer", which two independently broken implementations would
        also manage.
        """
        discover()
        project = (
            Project()
            .with_pipeline(
                rooted_on(
                    Pipeline(
                        nodes=(
                            Node(
                                node_id=CUT,
                                tool_id="crop",
                                version="1.0.0",
                                params=_pinned(ARENA),
                            ),
                            Node(node_id="down", tool_id="downsample", version="1.0.0"),
                        ),
                        edges=(Edge(upstream=CUT, downstream="down"),),
                    ),
                    tmp_path / "arena.MP4",
                    tmp_path,
                )
            )
            .with_crop(record)
        )

        backing = _backing((record,), tmp_path)
        wired = serving_edit(project, _home(tmp_path))

        assert backing.state is CropState.AT_REST
        assert backing.record is record
        assert wired is not None
        assert wired.pipeline.node(CUT).tool_id == "footage"
        assert glob(wired.pipeline.node(CUT).params["path"]) == [str(record.resolve(tmp_path))]
