"""Which record backs a box right now, and why one stopped.

The reporting twin of `crop_serving.py`, beside it because the two walk the same
clauses over the same records and a clause added to `CropRecord.backs` is owed to
both. `serving_edit` answers whether the substitution can be wired into the
document and declines quietly; this answers which of the four states a reader is
being shown, and names the clause that missed. Neither is a copy of the
predicate — both call `backs` — and everything here is the part `backs` refuses
to answer.

**What the states now mean.** They were about a run: `AT_REST` said the next
render would be served from the file. Under
`adr/a-users-file-wires-in-like-any-other-input.md` serving is a document edit,
so `AT_REST` says the edit is *offerable* for this box and `STALE` says why it
is not. The facts are the same facts about the same records; who acts on them
moved from the planner to whoever holds the project.

Not under `gui/`, on two counts. A `sieve run` that falls back to the parent and
says nothing about the artifact sitting next to it is making the same underclaim
a card would, and it would have no way to reach the sentence from a layer above
it; and `gui-computes-nothing` means a widget may not derive these states in the
first place — they are facts about records, so they land with their subject.

**Absent and stale are different claims.** A crop that was cut and then orphaned
— by a re-exported source, a deleted file, a graph that grew a chroma reader, a
window widened past what was cut — is not the same thing as a crop that was never
cut. Rendering both as "not at rest" would make an artifact sitting on disk look
like a decision nobody has taken yet, and the user would take it again. So a
near-miss is found and reported with the clause that missed.

**Attribution of an orphan is geometric, because association is.** A record
carries no replicate id, on purpose (`CropRecord`): records are associated with
boxes by parentage and geometry, so a renamed arena keeps its artifact and a
moved one correctly stops matching. That leaves one case with no answer — a
record whose box moved out from under it — and this module resolves it the only
way that model allows, by overlap: an unmatched record is reported against a box
when it overlaps that box and no other. When two boxes overlap the orphan, it is
reported against neither, because a reader that guesses is worse than one that
stays quiet about a file the user can still see in the folder.

**The record is a claim; `evidence_for` is the evidence.** `backs` reduces the
file to a boolean because that is all a resolver needs, and every question past
that — how big it is, when it was written, whether it can be read at all — is a
`stat` this module takes rather than a number a caller invents from the document.

**Nothing here refuses an edit.** This module reports; it does not hold anything
still. Freezing the box a record was cut at, or the window it was cut over, would
be an artifact that refuses the tuning it exists to make faster. Both edits
already fail safe without a gate: a moved box misses `backs` on the region and
no edit is offered, so an un-wired project goes on cutting from the parent with
the same pixels under the same keys. What is left for the user is a `STALE`
reading naming the clause that missed, which is the report this module owes
them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sieve.core.pipeline_model import CropRecord, SourceSpan
from sieve.core.types import ROI
from sieve.pipeline.source_home import SourceHome


class CropState(Enum):
    """The four states a source reading can be in.

    `WRITING` is not derivable from any record — it is a caller holding a write
    pass open — and it is in this enum anyway so that a display has one state
    input rather than a state and a flag that can disagree.
    """

    #: No record for this box. The crop is re-cut from the source every render,
    #: and materializing is offered.
    ABSENT = "absent"
    #: A write pass is running for this box right now.
    WRITING = "writing"
    #: A record matches and covers the window. The goal state.
    AT_REST = "at rest"
    #: A record exists and no longer backs the box. `reason` says which clause
    #: missed.
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class CropBacking:
    """What one box's source boundary is, in one value.

    Carried whole rather than unpacked: a caller
    that read `record` without `state` would offer a discard for a record it had
    just been told is serving, and one that read `state` without `reason` would
    render every staleness identically.
    """

    state: CropState
    #: The record this is about — the one serving, or the one that stopped.
    #: `None` only for `ABSENT` and `WRITING`.
    record: CropRecord | None = None
    #: Why a `STALE` record no longer backs the box, as a sentence a display
    #: shows verbatim. Empty in every other state.
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ArtifactEvidence:
    """What is behind a record, as the directory entry has it rather than as the
    document remembers it.

    Everything here comes from one `stat`, so a folder someone has been tidying
    shows up as a refusal instead of as a confident number.
    """

    path: Path
    #: File size. `None` is the refusal, never a zero: an entry that could not be
    #: read is unexamined, not empty.
    size_bytes: int | None
    #: Seconds since the epoch, from the mtime. Nothing stamps a time into a
    #: crop, and how a time reads is the caller's. `None` exactly when
    #: `size_bytes` is.
    written_at: float | None

    @property
    def readable(self) -> bool:
        """Whether the entry was read at all."""
        return self.size_bytes is not None


def evidence_for(record: CropRecord, project_dir: Path) -> ArtifactEvidence:
    """What is actually on disk behind `record`.

    Deliberately not folded into `backing_for`. That answers whether a record
    serves, which is a question about the record; this answers what the file is,
    and the two are taken at different instants and must be able to disagree — an
    `AT_REST` backing and a file deleted a moment later is an ordinary race, not
    an inconsistency to be resolved by asking once.
    """
    path = record.resolve(project_dir)
    try:
        stat = path.stat()
    except OSError:
        return ArtifactEvidence(path=path, size_bytes=None, written_at=None)
    return ArtifactEvidence(path=path, size_bytes=stat.st_size, written_at=stat.st_mtime)


def backing_for(
    crops: Sequence[CropRecord],
    index: int,
    regions: Sequence[ROI],
    *,
    home: SourceHome,
    luma: bool,
    window: SourceSpan | None,
) -> CropBacking:
    """The state of `regions[index]`'s source boundary.

    Args:
        crops: The document's records, in document order. The first match wins,
            exactly as `crop_serving.serving_edit` takes it.
        index: Which box is being asked about.
        regions: All of them, in the order their replicates appear — every
            replicate's resolved region at the crop node. Needed whole for orphan
            attribution, which is a question about whether any *other* box claims
            the record.
        home: What the records are read against — the same value `resolve` takes,
            so a report and a run cannot disagree about which parent they are
            talking about.
        luma: Whether the current graph decodes luma. `not Dag.needs_chroma`,
            derived by the caller for the reason `materialize_crop` makes it an
            argument: a format is a consequence of the chain, never a choice.
        window: The frames the artifact has to cover — the run's span widened by
            the graph's window, which is what a render actually reads and what
            `resolve_source` matches against, so a report judged on the span
            alone would say `AT_REST` about a record no run would open. `None`
            when no span is bound, in which case there is nothing to judge
            coverage against and the clause is skipped.

    Returns:
        `ABSENT`, `AT_REST`, or `STALE` with the clause that missed. Never
        `WRITING`; that state belongs to the caller holding the write open.
    """
    region = regions[index]
    for record in crops:
        if not record.backs(region, source=home.identity, luma=luma, project_dir=home.project_dir):
            continue
        if window is not None and (
            record.span.start > window.start or record.span.end < window.end
        ):
            return CropBacking(
                CropState.STALE,
                record,
                f"the window now runs [{window.start}:{window.end}) and this crop holds "
                f"[{record.span.start}:{record.span.end})",
            )
        return CropBacking(CropState.AT_REST, record)

    near = _near_miss(crops, region, source=home.identity, luma=luma, project_dir=home.project_dir)
    if near is not None:
        return near
    orphan = _orphan_for(crops, index, regions, source=home.identity)
    if orphan is not None:
        return CropBacking(
            CropState.STALE,
            orphan,
            f"cut at {orphan.region.width}x{orphan.region.height} at "
            f"({orphan.region.x}, {orphan.region.y}); the region has moved since",
        )
    return CropBacking(CropState.ABSENT)


def _near_miss(
    crops: Sequence[CropRecord],
    region: ROI,
    *,
    source: str,
    luma: bool,
    project_dir: Path,
) -> CropBacking | None:
    """A record cut at this exact box that has stopped matching, and why.

    Clause order is by how concrete the remedy is, not by `backs`'s evaluation
    order: a missing file is a thing the user can go and look for, a re-exported
    source is a thing they did, and a format mismatch is a consequence of the
    chain they can read off the graph.
    """
    for record in crops:
        if record.region != region:
            continue
        if not record.resolve(project_dir).is_file():
            return CropBacking(CropState.STALE, record, f"the file is not at {record.path}")
        if record.cut_from != source:
            return CropBacking(
                CropState.STALE, record, "the source has been re-exported since this was cut"
            )
        if record.luma != luma:
            written = "luma" if record.luma else "colour"
            wanted = "luma" if luma else "colour"
            return CropBacking(
                CropState.STALE, record, f"written in {written}; the chain now decodes {wanted}"
            )
    return None


def _orphan_for(
    crops: Sequence[CropRecord],
    index: int,
    regions: Sequence[ROI],
    *,
    source: str,
) -> CropRecord | None:
    """The unclaimed record this box — and only this one — overlaps."""
    claimed = set(regions)
    for record in crops:
        if record.cut_from != source or record.region in claimed:
            continue
        touching = [
            position for position, other in enumerate(regions) if _overlaps(record.region, other)
        ]
        if touching == [index]:
            return record
    return None


def _overlaps(one: ROI, other: ROI) -> bool:
    """Whether two regions share a pixel."""
    return (
        one.x < other.right
        and other.x < one.right
        and one.y < other.bottom
        and other.y < one.bottom
    )
