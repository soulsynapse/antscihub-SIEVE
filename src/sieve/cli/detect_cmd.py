"""`sieve detect` — run a project's graph and print the intervals it claims.

`sieve run` proves the graph executes. This proves the *document* — a project
carries a `DetectorSettings`, resolved per replicate and hashed into what the
run is, and until `sieve.detect` existed there was no path from a saved
project to detected intervals that did not start a Qt application
(docs/todo/headless-detection.md).

**The series is the sink's output, and the sink is the graph's.** The detector
runs over a `(T, B)` stack of block-signal grids, and the node that produces
them is the one nothing else consumes. Refusing a graph with two sinks is
deliberate: which of them a detection was taken over is part of what the
answer means, and a command that picked one would make the choice invisible.
`--node` is how a two-sink graph says which.

**A whole-clip pass is final by construction**, so none of the partial-record
frontier arithmetic applies — `settled_for(..., final=True)` is the whole
record, and the intervals printed here are the ones that will not move. That
is the difference between this and the tab, where the record is still filling.

**Workers is `ALL_CORES` and says so.** `gui/concurrency.py` is explicit that
policy about sharing a machine belongs to the process sharing one; a whole-clip
pass on a node is not that process, and `--workers` here caps decode, which is
the pool a job step actually contends on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from numpy.typing import NDArray

from sieve.backend.dispatch import Backend, NoKernelError
from sieve.cli.common import WORKERS_OPTION, frame_source, load_project, refuse, span_for
from sieve.core.pipeline_model import DetectorSettings, Project, resolved_detector
from sieve.core.replicates import Replicate
from sieve.core.wavelet import ALL_CORES
from sieve.decode.reader import VideoDecodeError
from sieve.detect import detect
from sieve.filters import discover
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.executor import FrameSource, UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import resolve


def detect_project(
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
    replicate_ids: Annotated[
        list[str] | None,
        typer.Option("--replicate", help="Detect only in this replicate. Repeatable."),
    ] = None,
    node_id: Annotated[
        str | None,
        typer.Option("--node", help="Node whose output is the series. Defaults to the sink."),
    ] = None,
    backend: Annotated[
        Backend, typer.Option("--backend", help="Where every node runs.")
    ] = Backend.CPU,
    workers: Annotated[int | None, WORKERS_OPTION] = None,
) -> None:
    """Detect events in a project's replicates and print the intervals.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, a graph that does not resolve or does not chain, an
            ambiguous or unknown series node, a node this executor cannot
            call, or footage that cannot be read.
    """
    discover()
    project = load_project(project_path)
    video = project.source_path(project_path)

    try:
        dag = Dag.build(project.pipeline)
    except GraphError as error:
        raise refuse(str(error)) from error
    try:
        source = source_identity(video)
    except OSError as error:
        raise refuse(f"source video is not where the project says: {video}") from error

    series_node = _series_node(dag, node_id)
    span = span_for(project, frames, video)
    targets = tuple(project.replicates) or (None,)
    luma = not dag.needs_chroma
    store = MemoryFrameStore()

    for target in targets:
        if replicate_ids and (target is None or target.replicate_id not in replicate_ids):
            continue
        resolved = resolve(
            project.crops,
            target,
            project_dir=project_path.parent,
            parent=video,
            parent_identity=source,
            luma=luma,
            want=span,
        )
        plan = ExecutionPlan.build(
            dag,
            source=resolved.identity,
            span=span,
            backend=backend,
            replicate=target,
            pre_cropped=resolved.pre_cropped,
            source_start=resolved.first_index,
        )
        with frame_source(resolved.path, workers, luma=luma) as reader:
            fps = reader.metadata.fps
            rows = _collect(plan, resolved.wrap(reader), store, series_node)
        typer.echo(_report(target, project.detector, rows, fps=fps, start=span.start))

    _refuse_unknown(project, replicate_ids)


def _series_node(dag: Dag, node_id: str | None) -> str:
    """The node whose per-frame output is the detector's series.

    A named node is checked against the graph rather than trusted, because the
    failure of a typo is otherwise a `KeyError` deep in the loop after the run
    has been paid for.
    """
    sinks = tuple(node.node_id for node in dag.order if not dag.downstreams[node.node_id])
    if node_id is not None:
        if node_id not in {node.node_id for node in dag.order}:
            raise refuse(f"no such node: {node_id}")
        return node_id
    if len(sinks) != 1:
        raise refuse(
            f"this graph has {len(sinks)} sinks ({', '.join(sinks)}), so which series a "
            "detection is taken over is not something the document says. Pass --node."
        )
    return sinks[0]


def _collect(
    plan: ExecutionPlan,
    reader: FrameSource,
    store: MemoryFrameStore,
    node_id: str,
) -> NDArray[np.float32]:
    """Run the plan and stack `node_id`'s output into `(T, B)` columns.

    Collected rather than counted, which is the one place this differs from
    `sieve run`: the transform needs the whole record at once. What is held is
    one node's grid per frame, not the `FrameResult` — the rest of the run is
    in `store` and dies with the loop.

    Raises:
        typer.Exit: code 1 for a node this executor cannot call, or a decode
            that failed.
    """
    rows: list[NDArray[np.float32]] = []
    try:
        for result in execute(plan, reader, store=store):
            frame = result.outputs[node_id]
            rows.append(np.asarray(frame.data, dtype=np.float32).reshape(-1))
    except (UnrunnableNodeError, NoKernelError) as error:
        raise refuse(str(error)) from error
    except VideoDecodeError as error:
        raise refuse(str(error)) from error
    if not rows:
        raise refuse("the span produced no frames, so there is nothing to detect over")
    return np.stack(rows)


def _report(
    target: Replicate | None,
    settings: DetectorSettings | None,
    series: NDArray[np.float32],
    *,
    fps: float,
    start: int,
) -> str:
    """One replicate's intervals, in absolute frames and in seconds.

    Two absences, distinguished rather than collapsed, which is rule 6's
    "absent must not render as zero" applied to the two fields that document a
    `None`. `Project.detector` unset is *never tuned* — the fps-derived default
    is deliberately not resolved into it, so there is no threshold to invent
    here either. `count_frac` unset is *tuned but disarmed*: bands were placed
    and no event is claimed. Neither is "found nothing", and a run that printed
    zero intervals for either would be a wrong answer that looks like a right
    one.
    """
    label = "baseline" if target is None else target.name
    if settings is None:
        return (
            f"{label}: {series.shape[0]} frames, {series.shape[1]} blocks — this project has no "
            "detector, so it claims nothing. Tune one in the GUI and save."
        )
    effective = resolved_detector(settings, target)
    update = detect(series, fps, effective, start_index=start, workers=ALL_CORES)
    if update.intervals is None:
        return (
            f"{label}: {series.shape[0]} frames, {series.shape[1]} blocks — detector disarmed "
            "(no count threshold placed), so nothing is claimed"
        )
    found = len(update.intervals)
    lines = [f"{label}: {series.shape[0]} frames, {found} interval{'' if found == 1 else 's'}"]
    lines.extend(
        f"  {first}:{last} ({first / fps:.2f}s - {last / fps:.2f}s, {last - first} frames)"
        for first, last in update.intervals
    )
    return "\n".join(lines)


def _refuse_unknown(project: Project, replicate_ids: list[str] | None) -> None:
    """Refuse a `--replicate` naming nothing, *after* the ones that exist ran.

    Deliberately last: a batch naming five arenas of which one was renamed
    should still produce the four answers, and then say what it could not do.
    Refusing up front would make a typo cost the whole run.
    """
    if not replicate_ids:
        return
    known = {rep.replicate_id for rep in project.replicates}
    missing = set(replicate_ids) - known
    if missing:
        raise refuse(f"no such replicate: {', '.join(sorted(missing))}")
