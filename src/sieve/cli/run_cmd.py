"""`sieve run` — execute a saved project through the one executor.

Everything this does between reading the YAML and printing a count is a call
into `sieve.pipeline`: `Dag.build` decides whether the graph is runnable,
`ExecutionPlan.build` decides what the run covers, and `execute` is the loop.
What is genuinely left here is the two decisions the document does not make,
because they are properties of an invocation rather than of a project — which
span, and whether to decode at all — and the printing.

**One store across every replicate, deliberately.** Two replicates that resolve
to the same parameters produce the same keys, so the second finds the first's
entries and computes nothing. A store per replicate would make that saving
unreachable while reporting exactly the same results, which is the kind of
difference nobody notices until a cluster bill arrives.

**Declared sinks are refused rather than ignored.** No writer exists yet
(`PLAN.md` builds them in Phase 5), and a `run` that computed every frame,
reported success, and wrote none of the outputs the project declares would be a
silent wrong answer of exactly the kind `cache_key.py`'s asymmetry rule spends
effort avoiding. It refuses with the sinks named.

**`--dry-run` opens no video.** It stats the footage — a cache key is a fact
about which file, and a plan that omitted it would be a plan for a different
run — but nothing decodes, so it answers on a login node with the footage on a
mount and no codec in the environment. The one thing it therefore cannot do is
infer a span from the container, and schema v1 records no span of its own
(`adr/detector-is-a-node.md`), so a dry run needs `--frames`.

**Cut from v2's command, each with where it comes back.** `--backend` has no
referent (`adr/no-kernel-apparatus.md`). `--replicate` and `--workers` are
selection and machine sizing, and `--no-cache` measures what a cold run costs:
none is exercised by anything yet, and `adr/declared-means-verified.md` is why
they are absent rather than present and untested — the full CLI is Phase 5 and
`bench` is Phase 6. The source resolution v2 did per replicate — which written
crop can serve this span, in whose frame numbering — is the read-back path
`PLAN.md` builds in Phase 5, so every run here reads the project's own video.

v2 kept `load_project`, `refuse` and `parse_span` in a `cli/common.py`, because
two commands refusing in two spellings would be two spellings of every error
message a user sees. There is one command, so there is no second speller and no
module to hold the agreement; the day `inspect` lands is the day these move.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from sieve.core.pipeline_model import Project, Replicate, SourceSpan
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoDecodeError, VideoReader
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.executor import FrameSource, UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.tools import discover


def run_project(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=True, dir_okay=False, readable=True, help="A .sieve.yaml project file."
        ),
    ],
    frames: Annotated[
        str | None,
        typer.Option("--frames", help="Span to run, as START:END, half-open."),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print what would run, decode nothing.")
    ] = False,
) -> None:
    """Run a project's pipeline over a span of its source video.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, a graph that does not resolve or does not chain, a node
            this executor cannot call, footage that is not where the project
            says, a span the footage cannot supply, or a project declaring
            outputs nothing can yet write.
    """
    discover()
    project = load_project(project_path)
    _refuse_sinks(project)
    video = project.source_path(project_path)

    try:
        dag = Dag.build(project.pipeline)
    except GraphError as error:
        raise refuse(str(error)) from error
    try:
        source = source_identity(video)
    except OSError as error:
        raise refuse(f"source video is not where the project says: {video}") from error

    span = span_for(frames, video, dry_run=dry_run)
    plans = [
        ExecutionPlan.build(dag, source=source, span=span, replicate=target)
        for target in _targets(project)
    ]

    if dry_run:
        for plan in plans:
            typer.echo(_describe(plan))
        return

    store: FrameStore = MemoryFrameStore()
    # One reader for the whole invocation, where v2 reopened per replicate: it
    # had to, because a replicate could be backed by its own crop file, and
    # under schema v1 every run here reads the project's source. A reader is a
    # pool of decode threads, so opening one per plan would pay for a pool build
    # per arena to read the same file.
    with frame_source(video, luma=not dag.needs_chroma) as reader:
        for plan in plans:
            _execute_one(plan, reader, store)


def frame_source(video: Path, *, luma: bool) -> PrefetchFrameSource:
    """The reader a span is decoded through.

    `luma` is not an option and must never become one: it is
    `not Dag.needs_chroma` for the graph about to run, and a `--luma` flag would
    let a user pick a format the cache key says was not used.
    """
    return PrefetchFrameSource(video, luma=luma)


def _execute_one(plan: ExecutionPlan, reader: FrameSource, store: FrameStore) -> None:
    """Run one replicate's plan and print what it did.

    Counted rather than collected: the executor yields a `FrameResult` per frame
    holding every node's output, and a list of them is the whole run resident in
    memory for no reason a count does not serve. What the caller wants written is
    in `store` already.

    Raises:
        typer.Exit: code 1 if the graph holds a node this executor cannot call,
            or if the footage cannot supply a frame the plan asked for.
    """
    label = "baseline" if plan.replicate is None else plan.replicate.name
    if not plan.warmed:
        typer.echo(
            f"{label}: warning — {plan.lead_in_shortfall.frames} of "
            f"{plan.lead_in.frames} lead-in frames are before the start of the video, "
            "so the first outputs are under-warmed"
        )
    computed = 0
    hits = 0
    try:
        for result in execute(plan, reader, store=store):
            computed += 1
            hits += len(result.from_cache)
    except UnrunnableNodeError as error:
        raise refuse(str(error)) from error
    except VideoDecodeError as error:
        raise refuse(f"{label}: {error}") from error
    nodes = computed * len(plan.dag.order)
    typer.echo(
        f"{label}: {computed} frames, {nodes - hits} node outputs computed, {hits} from cache"
    )


def _refuse_sinks(project: Project) -> None:
    """Refuse a project whose declared outputs nothing can write yet.

    Raises:
        typer.Exit: code 1 if the project declares any.
    """
    if project.outputs:
        listed = ", ".join(f"{sink.format} -> {sink.path}" for sink in project.outputs)
        raise refuse(
            f"this project declares outputs ({listed}) and no writer exists yet, so a run would "
            "compute every frame and write none of them. Remove them to run the graph anyway."
        )


def _targets(project: Project) -> tuple[Replicate | None, ...]:
    """The replicates to run, in document order, or `(None,)` for the baseline.

    `None` is a target rather than an absence: a project with no fan-out still
    runs its graph once, and `ExecutionPlan` already spells that case
    `replicate=None`. Returning an empty tuple for it would make "nothing to do"
    and "one thing to do without a deviation" the same value.
    """
    return tuple(project.replicates) or (None,)


def _describe(plan: ExecutionPlan) -> str:
    """What `--dry-run` prints: one plan, one block.

    Every line is something the plan already knows, and the selection is what a
    user checks before committing a cluster to it — how much gets decoded that is
    not asked for, and which nodes will be looked up rather than computed.
    """
    label = "baseline" if plan.replicate is None else plan.replicate.name
    lines = [
        f"{label}: frames {plan.span.start}:{plan.span.end}, "
        f"decoding {plan.decode_range.start}:{plan.decode_range.stop} "
        f"({plan.lead_in.frames} frames of lead-in"
        + (f", {plan.lead_in_shortfall.frames} unavailable" if not plan.warmed else "")
        + ")",
    ]
    for node in plan.dag.order:
        spec = plan.dag.spec(node.node_id)
        key = plan.key(node.node_id)
        lines.append(
            f"  {node.node_id}  {spec.tool_id} {spec.version}  "
            f"{'key ' + key[:12] if key is not None else 'uncacheable'}  "
            f"{plan.params[node.node_id].canonical_json()}"
        )
    return "\n".join(lines)


def refuse(message: str) -> typer.Exit:
    """Print `message` to stderr and hand back the exception to raise.

    Returning rather than raising so that every refusal reads `raise refuse(...)`
    — a helper that raised would be a control-flow jump a reader has to know
    about, and one that a type checker cannot see ends the function.
    """
    typer.echo(message, err=True)
    return typer.Exit(1)


def load_project(path: Path) -> Project:
    """Parse the project at `path`, or refuse with pydantic's own message.

    Not reformatted: `ValidationError` already names the field and the reason,
    and a summary of it would be a second, worse description of a document the
    CLI does not define.

    Raises:
        typer.Exit: code 1 if the document is invalid.
    """
    try:
        return Project.load(path)
    except ValidationError as error:
        raise refuse(f"{path} is not a valid project:\n{error}") from error


def parse_span(frames: str) -> SourceSpan:
    """`START:END` as a half-open range.

    Colon-separated rather than two options, because the two numbers are one
    quantity and a shell history holding `--frames 100:400` is legible in a way
    that `--start 100 --end 400` is not. Half-open, matching `SourceSpan`, which
    is what the executor is written against — a CLI that took an inclusive end
    would be the one place in the system where a range means something else.

    Raises:
        typer.Exit: code 1 if it is not two integers around a colon.
    """
    start, separator, end = frames.partition(":")
    if not separator:
        raise refuse(f"--frames takes START:END, got {frames!r}")
    try:
        parsed = SourceSpan(start=int(start), end=int(end))
    except ValueError as error:
        raise refuse(f"--frames {frames!r}: {error}") from error
    return parsed


def span_for(frames: str | None, video: Path, *, dry_run: bool = False) -> SourceSpan:
    """Which frames to work over: the flag, else the whole video.

    Two answers where v2 had three, and the missing one is the middle: a v2
    project recorded a tuning range on the document and this fell back to it.
    Schema v1 records none — the representative stretch is the `span` tool, in
    the graph like everything else (`adr/detector-is-a-node.md`) — so a project
    narrows a run by holding a selecting node, which `ExecutionPlan` intersects
    into `plan.span` well after this has answered.

    The fallback is the only one of the two that needs the container open, which
    is why `--dry-run` refuses instead of reaching it.

    Raises:
        typer.Exit: code 1 for an unparseable `--frames`, or for a path that may
            not open the video and was given none.
    """
    if frames is not None:
        return parse_span(frames)
    if dry_run:
        raise refuse(
            "no span was given, so it comes from the video's length — which --dry-run does not "
            "open the container to read. Pass --frames START:END."
        )
    with VideoReader(video) as reader:
        return SourceSpan(start=0, end=reader.metadata.frame_count)
