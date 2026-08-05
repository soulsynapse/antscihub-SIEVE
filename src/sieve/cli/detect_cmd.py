"""`sieve detect` — run a project's graph and print the intervals it claims.

`sieve run` proves the graph executes. This proves the *document* — a project
carries a `DetectorSettings`, resolved per replicate and hashed into what the
run is, and until `sieve.detect` existed there was no path from a saved
project to detected intervals that did not start a Qt application
(docs/todo/headless-detection.md).

**The series is the sink's output, and the sink is the graph's.** The detector
runs over a `(T, B)` stack of one node's grids, and the node that produces
them is the one nothing else consumes. Refusing a graph with two sinks is
deliberate: which of them a detection was taken over is part of what the
answer means, and a command that picked one would make the choice invisible.
`--node` is how a two-sink graph says which.

**And what the `B` columns *are* is the graph's too.** `--node` at any node
used to be admitted and the count written out as `blocks_in_band` whatever the
node emitted, which for a `downsample` node is a pixel count under an invented
noun — the numbers real, the label a lie, and the lie on disk after the session
ends. `_series_node` now asks `Dag` and refuses three answers it cannot label:
rows rather than frames, a node downstream of a rate change (where a row is not
a source frame), and a node whose elements have no declared meaning at all.
What survives names its own columns.

**A whole-clip pass is final by construction**, so none of the partial-record
frontier arithmetic applies — `settled_for(..., final=True)` is the whole
record, and the intervals printed here are the ones that will not move. That
is the difference between this and the tab, where the record is still filling.

**`--csv` is the measurement leaving the process, and stdout is not.** The
printed report is a summary — a count of intervals and their bounds — and
`docs/todo/parity-comparison-finding.md` needs the count/gate series itself to
compare a run against. `detect/tables.py` holds the two tables and the reason
they are two; this command's part is refusing the export up front when the
project has no detector, since there is then no series either and a directory
of empty files would say the opposite.

**Workers is `ALL_CORES` and says so.** `core/shares.py` is explicit that
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
from sieve.core.filter_base import ArraySpec, ElementKind
from sieve.core.ops.wavelet import ALL_CORES
from sieve.core.pipeline_model import DetectorSettings, Project, resolved_detector
from sieve.core.replicates import Replicate
from sieve.decode.reader import VideoDecodeError
from sieve.detect import detect
from sieve.detect.detector import DetectorUpdate
from sieve.detect.tables import DetectionExport, TableVerificationError, write_tables
from sieve.filters import discover
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.executor import FrameSource, UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.resolve_source import resolve
from sieve.pipeline.source_home import SourceHome


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
    csv_dir: Annotated[
        Path | None,
        typer.Option(
            "--csv",
            file_okay=False,
            help="Also write series.csv (and intervals.csv, if armed) into this directory.",
        ),
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
            call, footage that cannot be read, or `--csv` against a project
            with no detector.
    """
    discover()
    project = load_project(project_path)
    video = project.source_path(project_path)
    if csv_dir is not None and project.detector is None:
        raise refuse(
            "--csv has nothing to write: this project has no detector, so there is no "
            "series and no intervals. Tune one in the GUI and save."
        )

    try:
        dag = Dag.build(project.pipeline)
    except GraphError as error:
        raise refuse(str(error)) from error
    try:
        home = SourceHome.for_video(video, project_path.parent)
    except OSError as error:
        raise refuse(f"source video is not where the project says: {video}") from error

    series_node, element = _series_node(dag, node_id)
    series_filter = dag.specs[series_node].filter_id
    span = span_for(project, frames, video)
    targets = tuple(project.replicates) or (None,)
    luma = not dag.needs_chroma
    store = MemoryFrameStore()
    exports: list[DetectionExport] = []

    for target in targets:
        if replicate_ids and (target is None or target.replicate_id not in replicate_ids):
            continue
        resolved = resolve(
            project.crops,
            target,
            home=home,
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
        update = _detect_one(project.detector, target, rows, fps=fps, start=span.start)
        typer.echo(_report(_label(target), rows, update, fps=fps, element=element))
        if csv_dir is not None and update is not None and project.detector is not None:
            exports.append(
                DetectionExport(
                    replicate=_label(target),
                    node_id=series_node,
                    filter_id=series_filter,
                    fps=fps,
                    start=span.start,
                    update=update,
                    settings=resolved_detector(project.detector, target),
                )
            )

    if csv_dir is not None:
        typer.echo(_export(csv_dir, exports, element))
    _refuse_unknown(project, replicate_ids)


def _series_node(dag: Dag, node_id: str | None) -> tuple[str, ElementKind]:
    """The node whose per-frame output is the detector's series, and what it emits.

    A named node is checked against the graph rather than trusted, because the
    failure of a typo is otherwise a `KeyError` deep in the loop after the run
    has been paid for.

    **The element and the node id leave together.** Three of the four checks
    below are about what the node's output *means*, and a caller that admitted
    the node here and asked the graph what it emits somewhere else would be
    reading two derivations of one fact — which is how a graph gets admitted
    under one and named under the other.

    Raises:
        typer.Exit: code 1 for an unknown node, an ambiguous sink, a node
            emitting rows, a node whose elements have no declared meaning, or
            one downstream of a rate change.
    """
    sinks = tuple(node.node_id for node in dag.order if not dag.downstreams[node.node_id])
    if node_id is None:
        if len(sinks) != 1:
            raise refuse(
                f"this graph has {len(sinks)} sinks ({', '.join(sinks)}), so which series a "
                "detection is taken over is not something the document says. Pass --node."
            )
        node_id = sinks[0]
    elif node_id not in {node.node_id for node in dag.order}:
        raise refuse(f"no such node: {node_id}")

    spec = dag.specs[node_id]
    if not isinstance(spec.emits, ArraySpec):
        # Reached `_collect`'s `reshape(-1)` as an opaque numpy error before,
        # after the whole run had been paid for.
        raise refuse(
            f"{node_id} ({spec.filter_id}) emits rows, not frames, so there is no per-frame "
            "series to detect over"
        )
    if not dag.source_indexed[node_id]:
        # `Frame.frame` is `start + offset`. Behind a rate change that is wrong
        # by the decimation factor for every row — every frame number, every
        # timestamp, every interval bound — and wrong by a ratio plausible
        # enough to survive being looked at.
        raise refuse(
            f"{node_id} ({spec.filter_id}) is downstream of a filter that changes rate, so a "
            "row of its output is not a source frame and every timestamp this would write "
            "would be wrong by the rate"
        )
    element = dag.elements[node_id]
    if element is None:
        # Never "this filter did not declare": an array emitter cannot be
        # registered without a declaration, so the meaning was always lost
        # along the chain rather than never stated, and a message blaming the
        # node's own filter sends the reader to a file that is fine.
        lost = dag.element_lost_at(node_id)
        culprit = dag.specs[lost]
        raise refuse(
            f"{node_id} ({spec.filter_id}) has no element meaning, so a count over it has no "
            f"honest noun — a count labelled with an invented unit outlives the session in the "
            f"CSV. The chain lost it at {lost} ({culprit.filter_id}, declares "
            f"{culprit.element}); nothing downstream restores it. Detect over a node above that."
        )
    return node_id, element


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


def _label(target: Replicate | None) -> str:
    return "baseline" if target is None else target.name


def _detect_one(
    settings: DetectorSettings | None,
    target: Replicate | None,
    series: NDArray[np.float32],
    *,
    fps: float,
    start: int,
) -> DetectorUpdate | None:
    """The derivation, or `None` for a project that never tuned one.

    Split out from `_report` when `--csv` became a second consumer of the same
    update: printing it and writing it are two readings of one derivation, and
    running `detect` twice would let a stdout summary and a file on disk
    disagree about a run that was supposed to be one pass.
    """
    if settings is None:
        return None
    return detect(
        series, fps, resolved_detector(settings, target), start_index=start, workers=ALL_CORES
    )


def _export(directory: Path, exports: list[DetectionExport], element: ElementKind) -> str:
    """Write the tables and say what was written, naming the file left absent.

    Raises:
        typer.Exit: code 1 if a table does not read back as what was written,
            or the directory cannot be written.
    """
    if not exports:
        return f"--csv wrote nothing to {directory}: no replicate was run"
    try:
        written = write_tables(directory, exports, element=element)
    except TableVerificationError as error:
        raise refuse(str(error)) from error
    except OSError as error:
        raise refuse(f"--csv could not write to {directory}: {error}") from error
    names = ", ".join(path.name for path in written)
    if len(written) == 1:
        return (
            f"{directory}: wrote {names}. No intervals.csv — every replicate's detector is "
            "disarmed, and an empty one would read as 'found nothing'."
        )
    return f"{directory}: wrote {names}"


def _report(
    label: str,
    series: NDArray[np.float32],
    update: DetectorUpdate | None,
    *,
    fps: float,
    element: ElementKind,
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
    counted = f"{series.shape[1]} {element.value}s"
    if update is None:
        return (
            f"{label}: {series.shape[0]} frames, {counted} — this project has no "
            "detector, so it claims nothing. Tune one in the GUI and save."
        )
    if update.intervals is None:
        return (
            f"{label}: {series.shape[0]} frames, {counted} — detector disarmed "
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
