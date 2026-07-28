"""`sieve preview` — the tuning loop's inner step, with the timings printed.

The headless form of what the GUI does while a user drags a slider: build a
`PreviewSession` over the project's clip, render it, edit a parameter, render it
again. Existing for two reasons, one of which is not obvious.

**The obvious one: it is what makes the in-pipeline budgets measurable from a
terminal.** `slider_to_preview` and `full_preview_render` are the two ceilings
that say whether tuning feels direct, and until this command they could only be
observed by a human watching a window. `--check` turns the observation into an
exit code, which is what a budget being a defect rather than a tradeoff
(ARCHITECTURE.md non-negotiable #4) requires of something.

**The load-bearing one: it keeps the GUI from becoming a second execution
path.** Everything the preview panel will do is here first, on a machine with no
Qt — so a divergence between what a user sees while tuning and what a cluster
computes has to survive both front ends running the same
`pipeline/preview.py`, which is the same argument `sieve run` makes for
`executor.py`.

**`--edit` is the measurement, not a convenience.** A first render measures a
cold cache and says nothing about the thing the module is for; the number that
matters is the *second* render, after one parameter moved, because that is the
one an edit invalidating a suffix rather than the graph is supposed to make
cheap. So the edits apply from the second render onward and the per-render lines
report how much came from the store.

**One arena, not all of them.** `sieve run` fans out over every replicate
because that is what a run produces. A preview is one viewport, so this takes
one `--replicate` and defaults to the first — and the session's store outlives
the choice, so nothing is lost by looking at one.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

import typer

from sieve.backend.dispatch import Backend, NoKernelError
from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import MetricBus, Recorder
from sieve.cli.common import WORKERS_OPTION, frame_source, load_project, refuse, span_for
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
            exists=True, dir_okay=False, readable=True, help="A .sieve.yaml project file."
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
        typer.Option("--replicate", help="Which arena to preview. Defaults to the first."),
    ] = None,
    backend: Annotated[
        Backend, typer.Option("--backend", help="Where every node runs.")
    ] = Backend.CPU,
    repeat: Annotated[
        int, typer.Option("--repeat", min=1, help="Render this many times, reusing one store.")
    ] = 1,
    edits: Annotated[
        list[str] | None,
        typer.Option(
            "--edit",
            help="NODE:PARAM=VALUE applied from the second render onward. Repeatable.",
        ),
    ] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Exit non-zero if any render missed its budget.")
    ] = False,
    workers: Annotated[int | None, WORKERS_OPTION] = None,
) -> None:
    """Render a project's representative clip and report what it cost.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, an unknown replicate or node, an unparseable edit, a graph
            that does not resolve or cannot be executed, footage that cannot be
            read — and, under `--check`, for a budget miss.
    """
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

    # `--edit` rewrites parameters, never the shelf a node names, so no edit can
    # move the answer: the format is the project's and holds for every repeat.
    # Which is also why the source resolves once, before the loop — an edit
    # cannot make a crop artifact stop backing this arena.
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
            edited = project.pipeline if attempt == 0 else _apply(project, target, parsed).pipeline
            render = _render(session, edited, at)
            typer.echo(f"render {attempt + 1}: {_describe(render, edits if attempt else None)}")

    for key in recorder.keys:
        typer.echo(_timings(recorder, key))
    missed = recorder.misses()
    if missed and check:
        raise refuse(
            f"{len(missed)} of {len(recorder)} samples missed their budget, worst "
            f"{max(sample.over_ms for sample in missed):.1f} ms over"
        )


def _render(session: PreviewSession, pipeline: Pipeline, at: int | None) -> PreviewRender:
    """One render, with every deliberate refusal turned into an exit.

    The exception list is the one `sieve run` catches and for the same reason:
    each of these names something about the project or the machine that a user
    can act on, and a traceback would bury it.
    """
    try:
        if at is None:
            return session.render_window(pipeline)
        return session.render_frame(pipeline, at)
    except (GraphError, UnrunnableNodeError, NoKernelError, VideoDecodeError) as error:
        raise refuse(str(error)) from error


def _target(project: Project, replicate_id: str | None) -> Replicate | None:
    """The arena to preview: the named one, else the first, else the baseline.

    The default is the first replicate rather than the baseline, because a
    project with arenas drawn has no baseline anyone wants to look at — the
    whole frame is twelve arenas and the background between them.

    Raises:
        typer.Exit: code 1 if `replicate_id` names nothing.
    """
    if replicate_id is None:
        return project.replicates[0] if project.replicates else None
    try:
        return project.replicate(replicate_id)
    except KeyError as error:
        raise refuse(f"no such replicate: {replicate_id}") from error


def _parse_edits(project: Project, edits: Sequence[str]) -> tuple[tuple[str, str, Any], ...]:
    """`NODE:PARAM=VALUE` triples, with the node checked and the value JSON.

    JSON so that `factor=2` is the integer a parameter model wants rather than
    the string `"2"`, and so that a bare word still works: an unparseable value
    is taken literally, which makes `mode=fast` mean what it looks like without
    requiring shell-quoted JSON strings. Validation of the *value* is not done
    here — `ExecutionPlan.build` does it against the filter's model, which is the
    one place that knows what the field is.

    Raises:
        typer.Exit: code 1 for a malformed edit or a node the graph lacks.
    """
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
    """The project with every edit applied to the arena being previewed.

    Through `Project.with_param_edit` when there is an arena, because that is
    the one place the two writes a parameter edit performs happen — pin it on the
    replicate, move the node's default with it — and a command that wrote
    `Node.params` directly would be previewing something the GUI would never
    produce. With no arena there is nothing to pin, so the node's params are the
    whole of what it runs with and are edited in place.
    """
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
            edited = edited.with_param_edit(node_id, target.replicate_id, {param: value})
    return edited


def _header(
    project: Project,
    target: Replicate | None,
    window: ClipRange,
    *,
    at: int | None,
    resolved: ResolvedSource,
) -> str:
    """One line naming what is being previewed, before anything is rendered.

    Printed first so that a run that then fails has already said which arena and
    which frames it was working on — the two things that make a refusal
    actionable, and the two the flags most easily get wrong.

    The artifact is named when there is one, for `sieve run --dry-run`'s reason:
    the timings this command exists to report differ by two orders of magnitude
    between a crop-served render and a parent-served one, and a number that did
    not say which it measured would be the wrong kind of measurement.
    """
    arena = "whole frame" if target is None else target.name
    span = f"frame {at}" if at is not None else f"window {window.start}:{window.end}"
    nodes = len(project.pipeline.nodes)
    served = "" if resolved.artifact is None else f", served by {resolved.artifact.path}"
    return f"{arena}: {span}, {nodes} node{'' if nodes == 1 else 's'}{served}"


def _describe(render: PreviewRender, edits: Sequence[str] | None) -> str:
    """One render's line: what it covered, what it cost, and what it reused.

    The reuse share is the number this command exists to show. A second render
    reporting 0% is the whole failure mode `pipeline/preview.py` is written
    against, and it is invisible in the frames.
    """
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
    """One budget's line: the median against the ceiling, and the worst sample.

    Median for `Recorder.median_ms`' reason — one scheduler decision should not
    be what a report leads with — and the worst alongside it, because a preview
    that is usually fast and occasionally 400 ms is a preview a user calls janky
    and a median calls fine.

    Keyed by `Budget.key` rather than by the human `label`, which reads like the
    lesser choice and is not: the labels are copied from ARCHITECTURE.md and
    contain an arrow and an en dash, and a Windows console on a cp1252 codepage
    raises `UnicodeEncodeError` on them — so the command that reports the
    budgets would crash on the machines this is developed on. The key is ASCII,
    is what a call site references, and is what a user greps for.
    """
    budget = BUDGETS[key]
    worst = recorder.worst(key)
    verdict = "" if worst.within_budget else f"  MISS by {worst.over_ms:.1f} ms"
    return (
        f"{budget.key}: median {recorder.median_ms(key):.1f} ms of {budget.limit_ms:.0f} ms "
        f"({_sequence(recorder, key)}){verdict}"
    )


#: Renders past which the per-sample sequence stops being readable and the
#: summary is all there is room for.
_SEQUENCE_LIMIT = 8


def _sequence(recorder: Recorder, key: str) -> str:
    """The samples in arrival order, while there are few enough to read.

    The *order* is the finding, not a detail: the first render of a window
    decodes it and every render after it does not, so `221.1, 0.1` says what
    this command is for and `median 110.6, worst 221.1` says almost nothing.
    Past `_SEQUENCE_LIMIT` renders the sequence is a wall of numbers and the
    worst sample is the useful summary.
    """
    samples = recorder.samples(key)
    if len(samples) > _SEQUENCE_LIMIT:
        return f"{len(samples)} samples, worst {recorder.worst(key).elapsed_ms:.1f} ms"
    listed = ", ".join(f"{sample.elapsed_ms:.1f}" for sample in samples)
    return f"{len(samples)} samples: {listed} ms"
