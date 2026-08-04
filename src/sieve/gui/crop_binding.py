"""Which record backs a replicate right now, and what that freezes.

The GUI half of the match rule, and deliberately a *reading* of the same
predicate the pipeline serves from rather than a second copy of it:
`CropArtifact.backs` is called here exactly as `pipeline/resolve_source.py`
calls it, and everything this module adds is the part `backs` refuses to
answer — which of the four states the user is looking at, and why a record
that does not match no longer does.

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


def backing_for(
    crops: Sequence[CropArtifact],
    index: int,
    replicates: Sequence[Replicate],
    *,
    source: str,
    luma: bool,
    project_dir: Path,
    window: ClipRange | None,
) -> CropBacking:
    """The state of `replicates[index]`'s source boundary.

    Args:
        crops: The document's records, in document order. The first match wins,
            exactly as `resolve_source.resolve` takes it.
        index: Which replicate is being asked about.
        replicates: All of them — needed for orphan attribution, which is a
            question about whether any *other* box claims the record.
        source: `source_identity` of the parent footage.
        luma: Whether the current graph decodes luma. `not
            graph_needs_chroma(pipeline)`, derived by the caller for the same
            reason `sieve materialize` derives it: a format is a consequence of
            the chain, never a choice.
        project_dir: What `CropArtifact.path` is relative to.
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
        if not artifact.backs(replicate, source=source, luma=luma, project_dir=project_dir):
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

    near = _near_miss(crops, replicate, source=source, luma=luma, project_dir=project_dir)
    if near is not None:
        return near
    orphan = _orphan_for(crops, index, replicates, source=source)
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
