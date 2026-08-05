"""Which record backs a replicate right now, and why one stopped.

The reporting twin of `resolve_source.py`, beside it because the two walk the
same clauses over the same records and a clause added to `CropArtifact.backs`
is owed to both. `resolve` answers which file to open and declines quietly;
this answers which of the four states a reader is being shown, and names the
clause that missed. Neither is a copy of the predicate — both call `backs` — and
everything here is the part `backs` refuses to answer.

It lived under `gui/` until it was moved, on the reading that only a card wants
these sentences. A `sieve run` that falls back to the parent and says nothing
about the artifact sitting next to it is the same underclaim the card would be
making, and it had no way to reach the sentence from a layer above it.

**Absent and stale are different claims, and rule 6 is why they are.** A crop
that was cut and then orphaned — by a re-exported source, a deleted file, a
graph that grew a chroma reader, a clip widened past what was cut — is not the
same thing as a crop that was never cut. Rendering both as "not at rest" would
make an artifact sitting on disk look like a decision nobody has taken yet, and
the user would take it again. So a near-miss is found and reported with the
clause that missed.

**Attribution of an orphan is geometric, because association is.** A record
carries no replicate id, on purpose (`CropArtifact`): records are associated
with replicates by parentage and geometry, so a renamed arena keeps its
artifact and a moved one correctly stops matching. That leaves one case with no
answer — a record whose box moved out from under it — and this module resolves
it the only way that model allows, by overlap: an unmatched record is shown on
a replicate's card when it overlaps that replicate's region and no other. When
two replicates overlap the orphan, it is shown on neither, because a card that
guesses is worse than one that stays quiet about a file the user can still see
in the folder.

**The record is a claim; `evidence_for` is the evidence.** `backs` reduces the
file to a boolean because that is all a resolver needs, and every question past
that — how big it is, when it was written, whether it can be read at all — was
answerable only in `gui/filter_tab.py`, where it was formatted straight into a
card. `sieve run` prints `served by <path>` and can say nothing about the file
it names, which is the same underclaim this module moved down here to fix.

**Nothing here refuses an edit.** This module reports; it does not hold
anything still. An earlier version froze the box a record was cut at and the
window it was cut over, on the reasoning that either edit orphans a file — but
an artifact exists to make tuning faster, and one that refuses the tuning has
inverted its own purpose. Both edits already fail safe without a gate: a moved
box misses `backs` on the ROI, a window outside the span misses in
`resolve_source`, and the render falls back to the parent with the same pixels
under the same keys. What is left for the user is a `STALE` card naming the
clause that missed, which is the report this module owes them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.pipeline.source_home import SourceHome


class CropState(Enum):
    """The four states the source card renders.

    `WRITING` is not derivable from any record — it is the tab holding a write
    pass open — and it is in this enum anyway so that the card has one state
    input rather than a state and a flag that can disagree.
    """

    #: No record for this replicate. The crop is recut from the source every
    #: render, and materializing is offered.
    ABSENT = "absent"
    #: A write pass is running for this replicate right now.
    WRITING = "writing"
    #: A record matches and covers the clip. The goal state.
    AT_REST = "at rest"
    #: A record exists and no longer backs the replicate. `reason` says which
    #: clause missed.
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class CropBacking:
    """What one replicate's source boundary is, in one value.

    Carried whole rather than unpacked, for `ResolvedSource`'s reason: a caller
    that read `artifact` without `state` would offer a discard for a record it
    had just been told is serving, and one that read `state` without `reason`
    would render every staleness identically.
    """

    state: CropState
    #: The record this is about — the one serving, or the one that stopped.
    #: None only for `ABSENT` and `WRITING`.
    artifact: CropArtifact | None = None
    #: Why a `STALE` record no longer backs the replicate, as a sentence the
    #: card shows verbatim. Empty in every other state.
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ArtifactEvidence:
    """What is behind a record, as the directory entry has it rather than as the
    document remembers it.

    Everything here comes from one `stat`, so a folder someone has been tidying
    shows up as a refusal instead of as a confident number.
    """

    path: Path
    #: File size. `None` is the refusal, never a zero (rule 6): an entry that
    #: could not be read is unexamined, not empty.
    size_bytes: int | None
    #: Seconds since the epoch, from the mtime — `history.Snapshot.written_at`'s
    #: unit and for its reason: nothing stamps a time into a crop, and how a
    #: time reads is the caller's. `None` exactly when `size_bytes` is.
    written_at: float | None

    @property
    def readable(self) -> bool:
        """Whether the entry was read at all."""
        return self.size_bytes is not None


def evidence_for(artifact: CropArtifact, project_dir: Path) -> ArtifactEvidence:
    """What is actually on disk behind `artifact`.

    Deliberately not folded into `backing_for`. That answers whether a record
    serves, which is a question about the record; this answers what the file is,
    and the two are taken at different instants and must be able to disagree —
    an `AT_REST` backing and a file deleted a moment later is an ordinary race,
    not an inconsistency to be resolved by asking once.
    """
    path = artifact.resolve(project_dir)
    try:
        stat = path.stat()
    except OSError:
        return ArtifactEvidence(path=path, size_bytes=None, written_at=None)
    return ArtifactEvidence(path=path, size_bytes=stat.st_size, written_at=stat.st_mtime)


def backing_for(
    crops: Sequence[CropArtifact],
    index: int,
    replicates: Sequence[Replicate],
    *,
    home: SourceHome,
    luma: bool,
    window: ClipRange | None,
) -> CropBacking:
    """The state of `replicates[index]`'s source boundary.

    Args:
        crops: The document's records, in document order. The first match wins,
            exactly as `resolve_source.resolve` takes it.
        index: Which replicate is being asked about.
        replicates: All of them — needed for orphan attribution, which is a
            question about whether any *other* box claims the record.
        home: What the records are read against — the same value `resolve`
            takes, so the card and the run cannot disagree about which parent
            they are reporting on.
        luma: Whether the current graph decodes luma. `not
            graph_needs_chroma(pipeline)`, derived by the caller for the same
            reason `sieve materialize` derives it: a format is a consequence of
            the chain, never a choice.
        window: The working window the artifact has to cover — the document's
            effective window, not its clip, because that is what a render
            actually asks for and it is what `resolve_source` matches against.
            None when no source is bound, in which case there is no span to
            judge coverage against and the clause is skipped.

    Returns:
        `ABSENT`, `AT_REST`, or `STALE` with the clause that missed. Never
        `WRITING`; that state belongs to the caller holding the write open.
    """
    replicate = replicates[index]
    for artifact in crops:
        if not artifact.backs(
            replicate, source=home.identity, luma=luma, project_dir=home.project_dir
        ):
            continue
        if window is not None and (
            artifact.span.start > window.start or artifact.span.end < window.end
        ):
            return CropBacking(
                CropState.STALE,
                artifact,
                f"the window now runs [{window.start}:{window.end}) and this crop holds "
                f"[{artifact.span.start}:{artifact.span.end})",
            )
        return CropBacking(CropState.AT_REST, artifact)

    near = _near_miss(
        crops, replicate, source=home.identity, luma=luma, project_dir=home.project_dir
    )
    if near is not None:
        return near
    orphan = _orphan_for(crops, index, replicates, source=home.identity)
    if orphan is not None:
        return CropBacking(
            CropState.STALE,
            orphan,
            f"cut at {orphan.roi.width}x{orphan.roi.height} at ({orphan.roi.x}, {orphan.roi.y}); "
            "the region has moved since",
        )
    return CropBacking(CropState.ABSENT)


def _near_miss(
    crops: Sequence[CropArtifact],
    replicate: Replicate,
    *,
    source: str,
    luma: bool,
    project_dir: Path,
) -> CropBacking | None:
    """A record cut at this exact box that has stopped matching, and why.

    Clause order is by how concrete the remedy is, not by `backs`'s evaluation
    order: a missing file is a thing the user can go and look for, a
    re-exported source is a thing they did, and a format mismatch is a
    consequence of the chain they can read off the stack above the card.
    """
    for artifact in crops:
        if artifact.roi != replicate.roi:
            continue
        if not artifact.resolve(project_dir).is_file():
            return CropBacking(CropState.STALE, artifact, f"the file is not at {artifact.path}")
        if artifact.cut_from != source:
            return CropBacking(
                CropState.STALE, artifact, "the source has been re-exported since this was cut"
            )
        if artifact.luma != luma:
            written = "colour" if not artifact.luma else "luma"
            wanted = "luma" if luma else "colour"
            return CropBacking(
                CropState.STALE,
                artifact,
                f"written in {written}; the chain now decodes {wanted}",
            )
    return None


def _orphan_for(
    crops: Sequence[CropArtifact],
    index: int,
    replicates: Sequence[Replicate],
    *,
    source: str,
) -> CropArtifact | None:
    """The unclaimed record this replicate — and only this one — overlaps."""
    claimed = {other.roi for other in replicates}
    for artifact in crops:
        if artifact.cut_from != source or artifact.roi in claimed:
            continue
        touching = [
            position
            for position, other in enumerate(replicates)
            if _overlaps(artifact.roi, other.roi)
        ]
        if touching == [index]:
            return artifact
    return None


def _overlaps(one: ROI, other: ROI) -> bool:
    """Whether two regions share a pixel."""
    return (
        one.x < other.right
        and other.x < one.right
        and one.y < other.bottom
        and other.y < one.bottom
    )
