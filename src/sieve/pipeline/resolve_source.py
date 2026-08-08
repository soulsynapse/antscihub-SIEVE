"""Which file a run opens, and in whose frame numbering.

One step, called by every front end, answering one question: for *this* region
over *this* window, is there a written crop that can serve it, or does the run
read the parent and cut the region itself? `sieve run`, a preview session, and a
GUI render worker call this and nothing else — a second place deciding it would
be the "two answers to what a project computes" failure `executor.py` opens by
naming, arriving one layer higher up. The window rather than the span, because
the frames a graph reads around the ones it answers for come out of whichever
file this returns; `resolve`'s `want` is where that is argued.

**Nothing below this module learns that artifacts exist.** `cache_key.py`,
`plan.py` and `executor.py` are untouched by this file, which is the whole
dividend of the child-source model settled with the writer: a written crop is a
source video with an identity of its own, so a run against it roots off
`source_identity(<the file>)` with no region at all, exactly as it would for any
video a user opened. v2 needed a `pre_cropped` flag on the plan and a region for
that flag to suppress; schema v1 has neither to carry (`CropRecord`,
`adr/detector-is-a-node.md`).

What the caller keeps is the other half of that trade: the file already holds
the crop node's output, so a run served by one must not run that node again.
`crop_bound` and `elided` below are the two halves of that spelt out — which
node a record could stand for, and the graph without it — but the decision to
take them is the caller's, because only a caller knows what else it has promised
that node's output to. `cli/run_cmd.py` is the one that takes it today.

**A plan-time route with a known expiry.**
`adr/a-users-file-wires-in-like-any-other-input.md` settles that the substitution
is a document edit — the written crop is a source tool wired to the crop node's
consumers, and there is then no node in the executed graph to drop. Everything in
this module that routes rather than reports is unwound by that migration
(`todo/crop-serving-and-checkpoint-read-back-become-source-tools.md`), which is
deferred behind the first source tool.

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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from sieve.core.pipeline_model import CropRecord, Pipeline, SourceSpan
from sieve.core.tool_base import ParamsBase
from sieve.core.types import ROI, Frame, FrameIndex
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FrameSource
from sieve.pipeline.source_home import SourceHome
from sieve.tools.crop import CropParams


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
        want: The source frames the run will *read* — its span widened by the
            graph's window, which is `ExecutionPlan.decode_range`. Not the span:
            the frames a window adds are read from whichever file this returns,
            so a record certified for the answer alone is then asked for frames
            it does not hold, at either end. A record that does not cover all of
            `want` is declined whole; see the module docstring.

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


def crop_bound(dag: Dag, params: Mapping[str, ParamsBase]) -> tuple[str, ROI] | None:
    """Which node a record could stand for, and the box it would have to hold.

    The argument `resolve` does not derive for itself, because the graph is the
    caller's. Recognised by the resolved params type rather than by a tool id:
    the box is `CropParams.region`, `materialize_crop` cut it with that same
    tool, so the type *is* the claim that a file can stand where this node
    stands, and `pipeline` stays out of the business of knowing tools by name.

    A root, because a record is cut from the parent footage and a crop of some
    other node's output is a crop of something no file on disk holds. One or
    nothing: two of them are two boxes, and choosing between them is what
    `todo/the-materialize-command-derives-what-v2-was-handed.md` is open on, so
    until that is settled the answer is the fallback every clause in this module
    takes.

    Args:
        dag: The graph about to run.
        params: Resolved parameters per node id — `ExecutionPlan.params`, so the
            box is the one the replicate being processed actually resolved to
            and nothing re-derives an override.

    Returns:
        `(node_id, region)`, or `None` when the graph offers no single box.
        `None` is what `resolve` reads as "run the parent".
    """
    bound: tuple[str, ROI] | None = None
    for node in dag.order:
        resolved = params[node.node_id]
        if not isinstance(resolved, CropParams) or dag.upstreams[node.node_id]:
            continue
        if bound is not None:
            return None
        bound = (node.node_id, resolved.region)
    return bound


def elided(pipeline: Pipeline, node_id: str) -> Pipeline:
    """`pipeline` without `node_id`, its consumers left reading the source.

    Dropped rather than neutralised at `crop.WHOLE_FRAME`. The identity crop
    would compute the same pixels, but a node still standing between the source
    key and everything below it moves every one of those keys, and
    `adr/a-users-file-wires-in-like-any-other-input.md` settles that a served
    run's keys are the keys a source tool over that file would fold.

    Not a general graph edit and not on `Pipeline` for that reason: it is legal
    only for a root whose output is already on disk, which is `crop_bound`'s
    answer and nothing else.
    """
    return Pipeline(
        nodes=tuple(node for node in pipeline.nodes if node.node_id != node_id),
        edges=tuple(
            edge for edge in pipeline.edges if node_id not in (edge.upstream, edge.downstream)
        ),
    )


def _parent(home: SourceHome) -> ResolvedSource:
    """The fallback, spelt once so the clauses above cannot drift apart."""
    return ResolvedSource(path=home.video, identity=home.identity, first_index=FrameIndex(0))
