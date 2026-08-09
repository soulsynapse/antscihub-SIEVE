"""`sieve preview` — the tuning loop's inner step, with the timings printed.

The headless form of what the GUI will do while a user drags a slider: build a
`PreviewSession` over the project's footage, render it, edit a parameter, render
it again. Existing for two reasons, one of which is not obvious.

**The obvious one: it is what makes the in-pipeline budgets observable from a
terminal.** `slider_to_preview` and `full_preview_render` are the two ceilings
that say whether tuning feels direct, and until this command they could only be
observed by a human watching a window that does not exist yet.

**The load-bearing one: it keeps the GUI from becoming a second execution
path.** Everything the preview panel will do is here first, on a machine with no
Qt — so a divergence between what a user sees while tuning and what a cluster
computes has to survive both front ends running the same
`pipeline/preview.py`, which is the same argument `sieve run` makes for
`executor.py` (`adr/one-execution-path.md`).

**`--edit` is the measurement, not a convenience.** A first render measures a
cold cache and says nothing about the thing the module is for; the number that
matters is the *second* render, after one parameter moved, because that is the
one an edit invalidating a suffix rather than the graph is supposed to make
cheap. So the edits apply from the second render onward and the per-render lines
report how much came from the store.

**One replicate, not all of them.** `sieve run` fans out over every replicate
because that is what a run produces. A preview is one viewport, so this takes
one `--replicate` and defaults to the first — and the session's store outlives
the choice, so nothing is lost by looking at one.

**Cut from v2's command, each with where it comes back.** `--backend` has no
referent (`adr/no-kernel-apparatus.md`) and neither does the lowered decode
prefix v2 rebuilt per repeat, which is why one reader covers the whole
invocation here: `Dag.needs_chroma` reads specs and not parameters, so no
`--edit` can move the format the store is keyed under. `--workers` is machine
sizing that nothing exercises, as in `run_cmd`. `--check` turned a budget miss
into an exit code, and it goes for `adr/declared-means-verified.md`'s reason
rather than for want of a use: nothing in this repo can make a real clock miss a
ceiling on demand, so the true branch would ship unexercised — the gate that
judges these two budgets is `06.3`'s benchmark against `bench/budgets.py`, and
the miss stays visible here in the `MISS by` suffix a reader sees.
`todo/a-budget-miss-is-an-exit-code-once-something-can-force-one.md` holds it.

**No source resolution, deliberately.** v2 asked `resolve_source` per repeat
which written crop could serve the arena. Under schema v1 the box is a crop
node's parameter, so the caller must derive the region from the graph and elide
the node the file already holds — one join, shared with `sieve run`, and
`todo/a-served-run-elides-the-node-its-file-already-holds.md` owns it. Until
then this reads the project's own video, exactly as `run` does.

`load_project`, `refuse`, `span_for`, `footage_end` and `frame_source` are imported from
`run_cmd` rather than respelled: two commands refusing in two spellings would be
two spellings of every error message a user sees. That module's docstring said
the second command that can fail is what moves them to a `cli/common.py`, and
this is that command —
`todo/the-second-failing-command-moves-the-shared-refusals.md`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import MetricBus, Recorder
from sieve.cli.run_cmd import footage_end, frame_source, load_project, refuse, span_for
from sieve.core.pipeline_model import Pipeline, Project, Replicate, SourceSpan
from sieve.core.tool_base import SourceFileError
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import GraphError, graph_needs_chroma
from sieve.pipeline.executor import FormatMismatchError, UnrunnableNodeError
from sieve.pipeline.preview import PreviewRender, PreviewSession
from sieve.tools import discover


def preview_project(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=True, dir_okay=False, readable=True, help="A .sieve.yaml project file."
        ),
    ],
    frames: Annotated[
        str | None,
        typer.Option("--frames", help="Window to preview, as START:END, half-open."),
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
        typer.Option("--replicate", help="Which replicate to preview. Defaults to the first."),
    ] = None,
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
) -> None:
    """Render a project's working window and report what it cost.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, an unknown replicate or node, an unparseable edit, a value
            the tool will not accept, a graph that does not resolve or cannot be
            executed, footage that cannot be read, or a source root whose pattern
            names no one file.
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
    # Before the container opens: an unresolvable graph is a message that was
    # available from the document alone, and the decode format the whole store is
    # keyed under comes off the same build.
    try:
        luma = not graph_needs_chroma(project.pipeline)
    except GraphError as error:
        raise refuse(str(error)) from error
    window = span_for(frames, footage_end(video))

    bus = MetricBus()
    recorder = Recorder()
    bus.subscribe(recorder.record)

    with frame_source(video, luma=luma) as reader:
        session = PreviewSession(
            source=source,
            reader=reader,
            window=window,
            measure=bus.measure,
            replicate=target,
            store=MemoryFrameStore(),
        )
        for attempt in range(repeat):
            edited = project if attempt == 0 else _apply(project, target, parsed)
            # Re-aimed at the replicate *as the edited document holds it*. An
            # edit pins the changed value on the replicate as well as moving the
            # node's default, so a session still holding the pre-edit replicate
            # would resolve a stale pin over the new default and render the edit
            # as if it had not happened — while reporting 100% reuse for it.
            session.set_replicate(_aim(edited, target))
            if attempt == 0:
                typer.echo(_header(edited, target, window, at=at))
            render = _render(session, edited.pipeline, at)
            typer.echo(f"render {attempt + 1}: {_describe(render, edits if attempt else None)}")

    for key in recorder.keys:
        typer.echo(_timings(recorder, key))


def _render(session: PreviewSession, pipeline: Pipeline, at: int | None) -> PreviewRender:
    """One render, with every deliberate refusal turned into an exit.

    The exception list is `sieve run`'s plus `ValidationError`, and the addition
    is this command's own doing: `--edit` is the one surface in the repo that
    hands a user's untyped value to a tool's parameter model, so a value the
    model refuses is an ordinary answer to what the user typed rather than a
    defect a traceback should announce.

    `SourceFileError` is `sieve run`'s refusal reaching a render rather than a
    run start: a session resolves its source roots to key them, so a pattern
    naming no file is refused here in the same words instead of arriving as a
    traceback out of the tool on the first frame.
    """
    try:
        if at is None:
            return session.render_window(pipeline)
        return session.render_frame(pipeline, at)
    except (
        GraphError,
        UnrunnableNodeError,
        FormatMismatchError,
        VideoDecodeError,
        ValidationError,
        SourceFileError,
    ) as error:
        raise refuse(str(error)) from error


def _target(project: Project, replicate_id: str | None) -> Replicate | None:
    """The replicate to preview: the named one, else the first, else the baseline.

    The default is the first replicate rather than the baseline, because a
    project with replicates drawn has parameters pinned on them and previewing
    the undeviated graph would show a run nobody asked for.

    Raises:
        typer.Exit: code 1 if `replicate_id` names nothing.
    """
    if replicate_id is None:
        return project.replicates[0] if project.replicates else None
    try:
        return project.replicate(replicate_id)
    except KeyError as error:
        raise refuse(f"no such replicate: {replicate_id}") from error


def _aim(project: Project, target: Replicate | None) -> Replicate | None:
    """`target` as `project` holds it now, or `None` for the baseline."""
    return None if target is None else project.replicate(target.replicate_id)


def _parse_edits(project: Project, edits: Sequence[str]) -> tuple[tuple[str, str, Any], ...]:
    """`NODE:PARAM=VALUE` triples, with the node checked and the value JSON.

    JSON so that `factor=2` is the integer a parameter model wants rather than
    the string `"2"`, and so that a bare word still works: an unparseable value
    is taken literally, which makes `mode=fast` mean what it looks like without
    requiring shell-quoted JSON strings. Validation of the *value* is not done
    here — `ExecutionPlan.build` does it against the tool's model, which is the
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
    """The project with every edit applied to the replicate being previewed.

    Through `Project.with_param_edit` when there is one, because that is the one
    place the two writes a parameter edit performs happen — pin it on the
    replicate, move the node's default with it — and a command that wrote
    `Node.params` directly would be previewing something the GUI would never
    produce. With no replicate there is nothing to pin, so the node's params are
    the whole of what it runs with and are edited in place.
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
    project: Project, target: Replicate | None, window: SourceSpan, *, at: int | None
) -> str:
    """One line naming what is being previewed, before anything is rendered.

    Printed first so that a run that then fails has already said which replicate
    and which frames it was working on — the two things that make a refusal
    actionable, and the two the flags most easily get wrong.
    """
    label = "baseline" if target is None else target.name
    span = f"frame {at}" if at is not None else f"window {window.start}:{window.end}"
    nodes = len(project.pipeline.nodes)
    return f"{label}: {span}, {nodes} node{'' if nodes == 1 else 's'}"


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
        else (
            f", {render.plan.lead_in_shortfall.frames} of "
            f"{render.plan.lead_in.frames} lead-in frames missing"
        )
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
    lesser choice and is not: the labels are copied from VISION.md and contain an
    arrow and an en dash, and a Windows console on a cp1252 codepage raises
    `UnicodeEncodeError` on them — so the command that reports the budgets would
    crash on the machines this is developed on. The key is ASCII, is what a call
    site references, and is what a user greps for.
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
