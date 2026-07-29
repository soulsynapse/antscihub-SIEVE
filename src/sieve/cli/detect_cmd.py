







































from __future__ import annotations

from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from numpy.typing import NDArray

from sieve.backend.dispatch import Backend, NoKernelError
from sieve.cli.common import WORKERS_OPTION, frame_source, load_project, refuse, span_for
from sieve.core.filter_base import ArraySpec, ElementKind
from sieve.core.pipeline_model import DetectorSettings, Project, resolved_detector
from sieve.core.replicates import Replicate
from sieve.core.wavelet import ALL_CORES
from sieve.decode.reader import VideoDecodeError
from sieve.detect import detect
from sieve.detect.detector import DetectorUpdate
from sieve.detect.tables import DetectionExport, TableVerificationError, write_tables
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
        source = source_identity(video)
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


        raise refuse(
            f"{node_id} ({spec.filter_id}) emits rows, not frames, so there is no per-frame "
            "series to detect over"
        )
    if not dag.source_indexed[node_id]:




        raise refuse(
            f"{node_id} ({spec.filter_id}) is downstream of a filter that changes rate, so a "
            "row of its output is not a source frame and every timestamp this would write "
            "would be wrong by the rate"
        )
    element = dag.elements[node_id]
    if element is None:




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







    if settings is None:
        return None
    return detect(
        series, fps, resolved_detector(settings, target), start_index=start, workers=ALL_CORES
    )


def _export(directory: Path, exports: list[DetectionExport], element: ElementKind) -> str:






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






    if not replicate_ids:
        return
    known = {rep.replicate_id for rep in project.replicates}
    missing = set(replicate_ids) - known
    if missing:
        raise refuse(f"no such replicate: {', '.join(sorted(missing))}")
