





































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

    if project.outputs:
        listed = ", ".join(f"{sink.format} -> {sink.path}" for sink in project.outputs)
        raise refuse(
            f"this project declares outputs ({listed}) and no writer exists yet, so a run would "
            "compute every frame and write none of them. Remove them to run the graph anyway."
        )


def _targets(project: Project, replicate_ids: Sequence[str] | None) -> tuple[Replicate | None, ...]:












    if not replicate_ids:
        return tuple(project.replicates) or (None,)
    wanted = set(replicate_ids)
    selected = tuple(rep for rep in project.replicates if rep.replicate_id in wanted)
    missing = wanted - {rep.replicate_id for rep in selected}
    if missing:
        raise refuse(f"no such replicate: {', '.join(sorted(missing))}")
    return selected


def _describe(plan: ExecutionPlan, resolved: ResolvedSource) -> str:













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
