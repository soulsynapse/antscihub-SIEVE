"""`sieve run` — execute a saved project through the one executor.

The command SCAFFOLD calls canonical. Everything it does between reading the
YAML and printing a count is a call into `sieve.pipeline`: `Dag.build` decides
whether the graph is runnable, `ExecutionPlan.build` decides what the run
covers, and `execute` is the loop. What is genuinely left here is three
decisions the document does not make, because they are properties of an
invocation rather than of a project — which span, which replicates, and which
backend — and the printing.

**One store across every replicate, deliberately.** Two replicates in one
equivalence group whose ROIs coincide produce the same keys, so the second
finds the first's entries and computes nothing; `equivalence_groups` is the
document-level statement of the same fact. A store per replicate would make
that saving unreachable while reporting exactly the same results, which is the
kind of difference nobody notices until a cluster bill arrives. `--no-cache` is
there for the opposite need — measuring what a cold run costs — and it is a
`NullFrameStore` rather than a branch, so the loop it feeds is the same loop.

**Declared sinks are refused rather than ignored.** No writer exists yet
(`pipeline/results.py` in SCAFFOLD is unwritten), and a `run` that computed
every frame, reported success, and wrote none of the outputs the project
declares would be a silent wrong answer of exactly the kind `cache_key.py`'s
asymmetry rule spends effort avoiding. It refuses with the sinks named.

**Which file each replicate reads is resolved, not assumed.**
`pipeline/resolve_source.py` decides per replicate whether a materialized crop
can serve this span or the parent is read and the region cut at the root. It is
one call and the same call the GUI makes; what is left here is opening the
files it names, which is why the reader is no longer hoisted out of the loop.

**`--dry-run` opens no video.** It stats the footage — a cache key is a fact
about which file, and a plan that omitted it would be a plan for a different
run — but nothing decodes, so it answers on a login node with the footage on a
mount and no codec in the environment. The one thing it therefore cannot do is
infer a span from the container, so a project with no `clip` needs `--frames`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer

from sieve.backend.dispatch import Backend, NoKernelError
from sieve.cli.common import WORKERS_OPTION, frame_source, load_project, refuse, span_for
from sieve.core.pipeline_model import Project
from sieve.core.replicates import Replicate
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoDecodeError
from sieve.filters import discover
from sieve.pipeline.cache import FrameStore, MemoryFrameStore, NullFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.executor import FrameSource, UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import ResolvedSource, resolve


def run_project(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=True, dir_okay=False, readable=True, help="A .sieve.yaml project file."
        ),
    ],
    frames: Annotated[
        str | None,
        typer.Option(
            "--frames",
            help="Span to run, as START:END, half-open. Overrides the project's clip.",
        ),
    ] = None,
    replicate_ids: Annotated[
        list[str] | None,
        typer.Option("--replicate", help="Run only this replicate. Repeatable."),
    ] = None,
    backend: Annotated[
        Backend, typer.Option("--backend", help="Where every node runs.")
    ] = Backend.CPU,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print what would run, decode nothing.")
    ] = False,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Compute every frame, reuse nothing.")
    ] = False,
    workers: Annotated[int | None, WORKERS_OPTION] = None,
) -> None:
    """Run a project's pipeline over its representative clip.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, a graph that does not resolve or does not chain, a node
            this executor cannot call, a span the footage cannot supply, or a
            project declaring outputs nothing can yet write.
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

    span = span_for(project, frames, video, dry_run=dry_run)
    targets = _targets(project, replicate_ids)
    # The format the keys in `plans` are derived under — `dag.needs_chroma` is
    # what `Dag.node_keys` asks, so asking it once here is one derivation read
    # twice rather than two decisions that could differ. It also decides which
    # artifacts may serve: a colour crop cannot feed a luma session.
    luma = not dag.needs_chroma
    sources = [
        resolve(
            project.crops,
            target,
            project_dir=project_path.parent,
            parent=video,
            parent_identity=source,
            luma=luma,
            want=span,
        )
        for target in targets
    ]
    plans = [
        ExecutionPlan.build(
            dag,
            source=resolved.identity,
            span=span,
            backend=backend,
            replicate=target,
            pre_cropped=resolved.pre_cropped,
            source_start=resolved.first_index,
        )
        for target, resolved in zip(targets, sources, strict=True)
    ]

    if dry_run:
        for plan, resolved in zip(plans, sources, strict=True):
            typer.echo(_describe(plan, resolved))
        return

    store: FrameStore = NullFrameStore() if no_cache else MemoryFrameStore()
    _execute_all(plans, sources, store, workers=workers, luma=luma)


def _execute_all(
    plans: Sequence[ExecutionPlan],
    sources: Sequence[ResolvedSource],
    store: FrameStore,
    *,
    workers: int | None,
    luma: bool,
) -> None:
    """Run every plan against the file its replicate resolved to.

    **One reader open at a time, not one per file.** A backed replicate reads
    its artifact and an unbacked one reads the parent, so a project part-way
    through materialization needs both — and a reader is a pool of `workers`
    captures, which rule 5 makes a declared share rather than something to
    allocate twelve of because it saved a reopen. Runs are sequential and batch:
    reopening at each transition costs one pool build, and the alternative costs
    every pool at once for the length of the run.
    """
    reader: PrefetchFrameSource | None = None
    opened: Path | None = None
    try:
        for plan, resolved in zip(plans, sources, strict=True):
            if reader is None or opened != resolved.path:
                if reader is not None:
                    reader.close()
                reader = frame_source(resolved.path, workers, luma=luma)
                opened = resolved.path
            _execute_one(plan, resolved.wrap(reader), store)
    finally:
        if reader is not None:
            reader.close()


def _execute_one(plan: ExecutionPlan, reader: FrameSource, store: FrameStore) -> None:
    """Run one replicate's plan and print what it did.

    Counted rather than collected: the executor yields a `FrameResult` per
    frame holding every node's output, and a list of them is the whole run
    resident in memory for no reason a count does not serve. What the caller
    wants written is in `store` already.
    """
    label = "baseline" if plan.replicate is None else plan.replicate.name
    if not plan.warmed:
        typer.echo(
            f"{label}: warning — {plan.lead_in_shortfall} of {plan.lead_in} lead-in frames are "
            "before the start of the video, so the first outputs are under-warmed"
        )
    computed = 0
    hits = 0
    try:
        for result in execute(plan, reader, store=store):
            computed += 1
            hits += len(result.from_cache)
    except (UnrunnableNodeError, NoKernelError) as error:
        raise refuse(str(error)) from error
    except VideoDecodeError as error:
        raise refuse(f"{label}: {error}") from error
    nodes = computed * len(plan.dag.order)
    typer.echo(
        f"{label}: {computed} frames, {nodes - hits} node outputs computed, {hits} from cache"
    )


def _refuse_sinks(project: Project) -> None:
    """Refuse a project whose declared outputs nothing can write yet."""
    if project.outputs:
        listed = ", ".join(f"{sink.format} -> {sink.path}" for sink in project.outputs)
        raise refuse(
            f"this project declares outputs ({listed}) and no writer exists yet, so a run would "
            "compute every frame and write none of them. Remove them to run the graph anyway."
        )


def _targets(project: Project, replicate_ids: Sequence[str] | None) -> tuple[Replicate | None, ...]:
    """The replicates to run, in document order, or `(None,)` for the baseline.

    `None` is a target rather than an absence: a project with no fan-out still
    runs its graph once, over the whole frame, and `ExecutionPlan` already
    spells that case `replicate=None`. Returning an empty tuple for it would
    make "nothing to do" and "one thing to do without a crop" the same value.

    Selection preserves `project.replicates` order rather than the order the
    flags were typed, because replicate order is meaningful — it is the order
    outputs are written in — and an invocation is not the place that gets to
    change it.
    """
    if not replicate_ids:
        return tuple(project.replicates) or (None,)
    wanted = set(replicate_ids)
    selected = tuple(rep for rep in project.replicates if rep.replicate_id in wanted)
    missing = wanted - {rep.replicate_id for rep in selected}
    if missing:
        raise refuse(f"no such replicate: {', '.join(sorted(missing))}")
    return selected


def _describe(plan: ExecutionPlan, resolved: ResolvedSource) -> str:
    """What `--dry-run` prints: one plan, one block.

    Every line is something the plan already knows, and the selection is what a
    user checks before committing a cluster to it — how much gets decoded that
    is not asked for, which nodes will be looked up rather than computed, and
    where each one runs.

    Which *file* each replicate reads is printed only when it is not the
    project's source. A dry run is where a user finds out an artifact they cut
    is not being used — the fallback is deliberately silent at run time (see
    `pipeline/resolve_source.py`), and silent everywhere would make a stale
    record indistinguishable from a live one until somebody timed the run.
    """
    label = "baseline" if plan.replicate is None else plan.replicate.name
    lines = [
        f"{label}: frames {plan.span.start}:{plan.span.end}, "
        f"decoding {plan.decode_range.start}:{plan.decode_range.stop} "
        f"({plan.lead_in} frames of lead-in"
        + (f", {plan.lead_in_shortfall} unavailable" if not plan.warmed else "")
        + ")",
    ]
    if resolved.artifact is not None:
        lines.append(f"  served by {resolved.artifact.path} (crop, uncropped at the root)")
    for node in plan.dag.order:
        spec = plan.dag.spec(node.node_id)
        key = plan.key(node.node_id)
        lines.append(
            f"  {node.node_id}  {spec.filter_id} {spec.version}  "
            f"{plan.backend_for(node.node_id)}  "
            f"{'key ' + key[:12] if key is not None else 'uncacheable'}  "
            f"{plan.params[node.node_id].canonical_json()}"
        )
    return "\n".join(lines)
