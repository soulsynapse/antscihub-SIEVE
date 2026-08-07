"""Which file a run opens, and in whose frame numbering.

One step, called by every front end, answering one question: for *this* region
over *this* span, is there a written crop that can serve it, or does the run read
the parent and cut the region itself? `sieve run`, a preview session, and a GUI
render worker call this and nothing else — a second place deciding it would be
the "two answers to what a project computes" failure `executor.py` opens by
naming, arriving one layer higher up.

**Nothing below this module learns that artifacts exist.** `cache_key.py`,
`plan.py` and `executor.py` are untouched by this file, which is the whole
dividend of the child-source model settled with the writer: a written crop is a
source video with an identity of its own, so a run against it roots off
`source_identity(<the file>)` with no region at all, exactly as it would for any
video a user opened. v2 needed a `pre_cropped` flag on the plan and a region for
that flag to suppress; schema v1 has neither to carry (`CropRecord`,
`adr/detector-is-a-node.md`).

What the caller keeps is the other half of that trade, and it is stated here
because nothing else states it: the file already holds the crop node's output,
so a run served by one must not run that node again. `resolve` is handed a region
the caller derived from the graph, so the caller is the one holding the node id
that region came off, and eliding it is its call rather than this module's. The
item is `todo/a-served-run-elides-the-node-its-file-already-holds.md`.

**Presence is consulted once per render, never per frame.** `resolve` is called
where a run is *planned*; the result is fixed for the whole run. Asking per frame
would let one run mix artifact and parent pixels under a single root key, which
is a wrong answer served from cache — the one failure `cache_key.py`'s asymmetry
rule spends effort to avoid.

**A record that does not match changes nothing.** Every clause below fails toward
the parent: a moved box, a re-exported source, a deleted file, a colour artifact
in a luma session, a window reaching outside what was cut. The fallback is the
status quo — same paths, same keys, same pixels as before the record existed —
not an error, because a stale artifact is a storage fact and the run it would
have accelerated is still perfectly runnable. Declining quietly is this module's
job; naming which clause missed is `crop_binding.py`'s, next door, so that a
caller that wants to *say* why it fell back does not re-walk the clauses to find
out.

**The span clause is this module's, not `backs`'s.** `CropRecord.backs`
deliberately stops short of the span, because a record covering `[10, 20)` asked
for `[12, 30)` backs *part* of the request and only the caller knows whether part
is enough. Here it is not: half-serving a window would put two decoders' pixels
in one run, so a window reaching past either end of the record un-backs the
request entirely.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sieve.core.pipeline_model import CropRecord, SourceSpan
from sieve.core.types import ROI, Frame, FrameIndex
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.executor import FrameSource
from sieve.pipeline.source_home import SourceHome


@dataclass(frozen=True, slots=True)
class ResolvedSource:
    """The file one run reads, and how to plan against it.

    Frozen and carried whole rather than unpacked at the call site, because the
    fields are one decision: a caller that took `path` without `record` would
    re-cut an already-cut file, and one that took `identity` without
    `first_index` would key correctly and read the wrong frames. They travel
    together or they are a bug.
    """

    #: The video to open.
    path: Path
    #: `cache_key.source_identity(path)` — the root of every key in the run.
    identity: str
    #: Source frame index of `path`'s frame 0. Zero for the parent.
    first_index: FrameIndex
    #: The record being served, or `None` when this is the parent. Both a caller
    #: that wants to *say* what it is serving and one that has to elide the node
    #: the file already holds read it here; nothing about the arithmetic below
    #: depends on it.
    record: CropRecord | None = None

    def wrap(self, reader: FrameSource) -> FrameSource:
        """`reader` in source frame numbering, whatever its own numbering is.

        The identity function for the parent, and an offsetting view over an
        artifact. Applied by the caller that opened the reader, so that
        everything above — the plan's span, a timeline, a series collector —
        sees exactly one numbering scheme and no module has to know which file
        it came from.
        """
        if self.first_index == FrameIndex(0):
            return reader
        return OffsetFrameSource(reader, self.first_index)


class OffsetFrameSource:
    """A `FrameSource` renumbered so that its frame 0 is source frame `first`.

    The whole translation between an artifact's index space and the source's, in
    one place, so that `Frame.index` is in source numbering everywhere above it.
    `materialize.py` states the same fact from the writing end: artifact frame 0
    is source frame `span.start`, and nothing else translates.

    The frame's own `index` is rewritten rather than passed through, because
    `executor._run_node` checks a node's output index against the loop's — an
    artifact reporting its own numbering would be refused there as a tool that
    renumbered its output, which is a true message about the wrong thing.
    """

    def __init__(self, inner: FrameSource, first: int | FrameIndex) -> None:
        """Present `inner` as footage beginning at source frame `first`."""
        self._inner = inner
        self._first = FrameIndex.of(first)

    def read(self, index: int | FrameIndex) -> Frame:
        """The frame at source index `index`.

        Raises:
            VideoDecodeError: if `index` is before this footage begins. The
                caller's plan should have clamped and never asked; this is the
                guard that turns a silent wrong frame — a negative index reaching
                a reader that treats it as an offset — into the message it
                deserves.
        """
        index = FrameIndex.of(index)
        if index < self._first:
            raise VideoDecodeError(
                f"frame {index} is before this footage begins (frame {self._first})"
            )
        frame = self._inner.read((index - self._first).frames)
        return Frame(data=frame.data, index=index, channels=frame.channels)


def resolve(
    crops: Sequence[CropRecord],
    region: ROI | None,
    *,
    home: SourceHome,
    luma: bool,
    want: SourceSpan,
) -> ResolvedSource:
    """The source a run of `region` over `want` should read.

    Args:
        crops: `Project.crops`. Searched in document order and the first match
            wins; two records matching one request mean one cut written twice
            under two names, which `Project.with_crop` already de-duplicates by
            identity, so order only decides between equally correct files.
        region: The box being run, in source pixels — a crop node's resolved
            `region` parameter for the replicate being processed, which is where
            geometry lives under schema v1. `None` never resolves to an artifact:
            every record is a crop of some box, and a run with no box is the
            whole frame.
        home: What the records are read against. Its `identity` is taken rather
            than derived so a caller that has one does not stat twice, and so
            the identity a run keys on is the identity it matched on.
        luma: Whether this run decodes the luma plane — `not Dag.needs_chroma`.
            An artifact in the other format is declined, because a luma read of
            a colour file is the wrong-pixels trap the codec finding measured.
        want: The span about to be run, in source frames. A record that does not
            cover all of it is declined whole; see the module docstring.

    Returns:
        The parent, or a record that covers the request.
    """
    if region is None:
        return _parent(home)
    for record in crops:
        if not record.backs(region, source=home.identity, luma=luma, project_dir=home.project_dir):
            continue
        if record.span.start > want.start or record.span.end < want.end:
            continue
        path = record.resolve(home.project_dir)
        try:
            identity = source_identity(path)
        except OSError:
            # `backs` found the file a moment ago; losing it between the two
            # calls is a race with something outside this process, and the
            # answer is the fallback every other clause takes.
            continue
        return ResolvedSource(
            path=path,
            identity=identity,
            first_index=FrameIndex(record.span.start),
            record=record,
        )
    return _parent(home)


def _parent(home: SourceHome) -> ResolvedSource:
    """The fallback, spelt once so the clauses above cannot drift apart."""
    return ResolvedSource(path=home.video, identity=home.identity, first_index=FrameIndex(0))
