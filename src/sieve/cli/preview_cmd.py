from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

import typer

from sieve.backend.dispatch import Backend, NoKernelError
from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import MetricBus, Recorder
from sieve.cli.common import (
    WORKERS_OPTION,
    frame_source,
    load_project,
    refuse,
    span_for,
)
from sieve.core.pipeline_model import ClipRange, Pipeline, Project
from sieve.core.replicates import Replicate
from sieve.decode.reader import VideoDecodeError
from sieve.filters import discover
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import GraphError, graph_needs_chroma
from sieve.pipeline.executor import UnrunnableNodeError
from sieve.pipeline.preview import PreviewRender, PreviewSession
from sieve.pipeline.resolve_source import ResolvedSource, resolve


def preview_project(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="A .sieve.yaml project file.",
        ),
    ],
    frames: Annotated[
        str | None,
        typer.Option(
            "--frames",
            help="Window to preview, as START:END, half-open. Overrides the project's clip.",
        ),
    ] = None,
    at: Annotated[
        int | None,
        typer.Option(
            "--at",
            help="Render this one source frame instead of the whole window — the slider path.",
        ),
    ] = None,
    replicate_id: Annotated[
        str | None,
        typer.Option(
            "--replicate", help="Which arena to preview. Defaults to the first."
        ),
    ] = None,
    backend: Annotated[
        Backend, typer.Option("--backend", help="Where every node runs.")
    ] = Backend.CPU,
    repeat: Annotated[
        int,
        typer.Option(
            "--repeat", min=1, help="Render this many times, reusing one store."
        ),
    ] = 1,
    edits: Annotated[
        list[str] | None,
        typer.Option(
            "--edit",
            help="NODE:PARAM=VALUE applied from the second render onward. Repeatable.",
        ),
    ] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Exit non-zero if any render missed its budget."),
    ] = False,
    workers: Annotated[int | None, WORKERS_OPTION] = None,
) -> None:
    discover()
    project = load_project(project_path)
    video = project.source_path(project_path)
    target = _target(project, replicate_id)
    parsed = _parse_edits(project, edits or ())
    if parsed and repeat < 2:
        raise refuse(
            "--edit applies from the second render onward, so it does nothing with one render. "
            "Pass --repeat 2 to measure what the edit cost."
        )
    try:
        source = source_identity(video)
    except OSError as error:
        raise refuse(f"source video is not where the project says: {video}") from error
    window = span_for(project, frames, video)
    bus = MetricBus()
    recorder = Recorder()
    bus.subscribe(recorder.record)
    luma = not graph_needs_chroma(project.pipeline)
    resolved = resolve(
        project.crops,
        target,
        project_dir=project_path.parent,
        parent=video,
        parent_identity=source,
        luma=luma,
        want=window,
    )
    with frame_source(resolved.path, workers, luma=luma) as reader:
        session = PreviewSession(
            source=resolved.identity,
            reader=resolved.wrap(reader),
            window=window,
            measure=bus.measure,
            replicate=target,
            backend=backend,
            store=MemoryFrameStore(),
            pre_cropped=resolved.pre_cropped,
            source_start=resolved.first_index,
        )
        typer.echo(_header(project, target, window, at=at, resolved=resolved))
        for attempt in range(repeat):
            edited = (
                project.pipeline
                if attempt == 0
                else _apply(project, target, parsed).pipeline
            )
            render = _render(session, edited, at)
            typer.echo(
                f"render {attempt + 1}: {_describe(render, edits if attempt else None)}"
            )
    for key in recorder.keys:
        typer.echo(_timings(recorder, key))
    missed = recorder.misses()
    if missed and check:
        raise refuse(
            f"{len(missed)} of {len(recorder)} samples missed their budget, worst "
            f"{max(sample.over_ms for sample in missed):.1f} ms over"
        )


def _render(
    session: PreviewSession, pipeline: Pipeline, at: int | None
) -> PreviewRender:
    try:
        if at is None:
            return session.render_window(pipeline)
        return session.render_frame(pipeline, at)
    except (GraphError, UnrunnableNodeError, NoKernelError, VideoDecodeError) as error:
        raise refuse(str(error)) from error


def _target(project: Project, replicate_id: str | None) -> Replicate | None:
    if replicate_id is None:
        return project.replicates[0] if project.replicates else None
    try:
        return project.replicate(replicate_id)
    except KeyError as error:
        raise refuse(f"no such replicate: {replicate_id}") from error


def _parse_edits(
    project: Project, edits: Sequence[str]
) -> tuple[tuple[str, str, Any], ...]:
    parsed: list[tuple[str, str, Any]] = []
    for edit in edits:
        target_name, separator, assignment = edit.partition(":")
        param, equals, value = assignment.partition("=")
        if not separator or not equals:
            raise refuse(f"--edit takes NODE:PARAM=VALUE, got {edit!r}")
        if target_name not in project.pipeline:
            raise refuse(f"--edit names no such node: {target_name!r}")
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = value
        parsed.append((target_name, param, decoded))
    return tuple(parsed)


def _apply(
    project: Project, target: Replicate | None, edits: Sequence[tuple[str, str, Any]]
) -> Project:
    edited = project
    for node_id, param, value in edits:
        if target is None:
            node = edited.pipeline.node(node_id)
            updated = node.model_copy(update={"params": {**node.params, param: value}})
            edited = edited.with_pipeline(
                edited.pipeline.model_copy(
                    update={
                        "nodes": tuple(
                            updated if candidate.node_id == node_id else candidate
                            for candidate in edited.pipeline.nodes
                        )
                    }
                )
            )
        else:
            edited = edited.with_param_edit(
                node_id, target.replicate_id, {param: value}
            )
    return edited


def _header(
    project: Project,
    target: Replicate | None,
    window: ClipRange,
    *,
    at: int | None,
    resolved: ResolvedSource,
) -> str:
    arena = "whole frame" if target is None else target.name
    span = f"frame {at}" if at is not None else f"window {window.start}:{window.end}"
    nodes = len(project.pipeline.nodes)
    served = (
        "" if resolved.artifact is None else f", served by {resolved.artifact.path}"
    )
    return f"{arena}: {span}, {nodes} node{'' if nodes == 1 else 's'}{served}"


def _describe(render: PreviewRender, edits: Sequence[str] | None) -> str:
    applied = f" after {', '.join(edits)}" if edits else ""
    warning = (
        ""
        if render.plan.warmed
        else f", {render.plan.lead_in_shortfall} of {render.plan.lead_in} lead-in frames missing"
    )
    return (
        f"{render.frames} frames {render.span.start}:{render.span.end}{applied}, "
        f"{render.computed} node outputs computed, {render.from_cache} from cache "
        f"({render.reuse:.0%} reuse){warning}"
    )


def _timings(recorder: Recorder, key: str) -> str:
    budget = BUDGETS[key]
    worst = recorder.worst(key)
    verdict = "" if worst.within_budget else f"  MISS by {worst.over_ms:.1f} ms"
    return (
        f"{budget.key}: median {recorder.median_ms(key):.1f} ms of {budget.limit_ms:.0f} ms "
        f"({_sequence(recorder, key)}){verdict}"
    )


_SEQUENCE_LIMIT = 8


def _sequence(recorder: Recorder, key: str) -> str:
    samples = recorder.samples(key)
    if len(samples) > _SEQUENCE_LIMIT:
        return f"{len(samples)} samples, worst {recorder.worst(key).elapsed_ms:.1f} ms"
    listed = ", ".join(f"{sample.elapsed_ms:.1f}" for sample in samples)
    return f"{len(samples)} samples: {listed} ms"
