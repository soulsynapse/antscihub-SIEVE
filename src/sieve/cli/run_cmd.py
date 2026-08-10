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

**Declared sinks are refused rather than ignored.** No writer for a *declared*
`Sink` exists yet, and a `run` that computed every frame, reported success, and
wrote none of the outputs the project declares would be a silent wrong answer of
exactly the kind `cache_key.py`'s asymmetry rule spends effort avoiding. It
refuses with the sinks named. `Project.checkpoints` is the other half of that
field pair and is not refused, because this command now writes them
(`storage/checkpoint_writer.py`) — which is the whole difference between a
declaration with machinery under it and one without.

**A checkpoint is written per replicate and reported.** The writer is fed from
the result stream this loop already consumes, so nothing about the executor knows
what a checkpoint is; and a run that cannot write one refuses rather than
finishing, for `_refuse_sinks`' reason.

**`--dry-run` opens no video.** It stats the footage — a cache key is a fact
about which file, and a plan that omitted it would be a plan for a different
run — but nothing decodes, so it answers on a login node with the footage on a
mount and no codec in the environment. What it therefore cannot do is learn the
video's length, and both of the things that length is for go with it: schema v1
records no span of its own (`adr/detector-is-a-node.md`) so a dry run needs
`--frames`, and the plan it prints is unclamped at the trailing end, so a graph
that reads ahead is described over a span a real run would narrow.

**The external files are named before anything else happens.** VISION's
reviewer is told by name what is missing before a run starts, and `_external_
inputs` is where. The list is walked out of the graph rather than read off the
document (`resolve_source.source_files`), so it cannot come to disagree with the
nodes it describes; it runs beside the "source video is not where the project
says" refusal above, before the container is opened and before any key is built,
and it reports every absent input rather than the first. What it buys is naming
and absence *plus* identity, which is one clause more than the derived list
alone: a recorded `Project.input_hashes` entry is compared here too, so a file
swapped for another at the matching name is refused rather than run over. A node
the document records nothing about is still only named, not recognised.

**A written crop is not this command's business, and that is the point.** v2
resolved a source per replicate here — which artifact can serve this run, in
whose frame numbering — and so did this command, in two passes, until
`adr/a-users-file-wires-in-like-any-other-input.md` settled that the
substitution is an edit the project holds (`pipeline/crop_serving.py`). A served
project's graph roots on a `footage` node over the written file and holds no crop
node, so this command plans it exactly as it plans anything else and the file it
reads is found by the same source-root walk above. What that bought is not
brevity here: a preview session and a render worker never had the route, and
under the edit they no longer need one.

**Cut from v2's command, each with where it comes back.** `--backend` has no
referent (`adr/no-kernel-apparatus.md`). `--replicate` and `--workers` are
selection and machine sizing, and `--no-cache` measures what a cold run costs:
none is exercised by anything yet, and `adr/declared-means-verified.md` is why
they are absent rather than present and untested — the full CLI is Phase 5 and
`bench` is Phase 6.

v2 kept `load_project`, `refuse` and `parse_span` in a `cli/common.py`, because
two commands refusing in two spellings would be two spellings of every error
message a user sees. Here they stay in this module and the other commands import
them (`preview_cmd`, `materialize_cmd`), which buys the same one spelling without
a module whose only content is what this one already had to define. What would
move them is this command ceasing to be the natural home — a fourth caller, or a
refusal that has nothing to do with running a graph.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    ExternalInputChanged,
    Pipeline,
    Project,
    Replicate,
    Sink,
    SourceSpan,
)
from sieve.core.tool_base import SourceFileError, selected_emission
from sieve.core.types import NO_FRAMES, FrameIndex
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoDecodeError, VideoReader
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag, GraphError, InvalidParamsError
from sieve.pipeline.executor import FrameSource, UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan, validated_params
from sieve.pipeline.resolve_source import (
    NoFootage,
    anchored,
    footage_file,
    picked_identities,
    source_files,
)
from sieve.storage.checkpoint_writer import CheckpointWriteError, CheckpointWriter, Kept
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
            this executor cannot call, a document naming no footage, footage that
            is not where the project says, a span the footage cannot supply — including one lying wholly
            inside the graph's read-ahead of the last frame — or a project
            declaring outputs nothing can yet write.
    """
    discover()
    project = load_project(project_path)
    _refuse_sinks(project)
    graph = anchored(project.pipeline, project_path.parent)
    video = footage_of(graph, project_path, project.replicates)

    try:
        dag = Dag.build(graph)
    except GraphError as error:
        raise refuse(str(error)) from error
    try:
        source = source_identity(video)
    except OSError as error:
        raise refuse(f"source video is not where the project says: {video}") from error

    targets = _targets(project)
    try:
        picked = _external_inputs(project, dag, targets)
    except (SourceFileError, ExternalInputChanged, InvalidParamsError) as error:
        raise refuse(str(error)) from error

    end = None if dry_run else footage_end(video)
    span = span_for(frames, end)
    # `ValueError` rather than the `GraphError` above: what a plan refuses is a
    # span it cannot answer for, which is neither a graph nor a document and has
    # no error of its own — the message names the ranges that disagree, and a
    # traceback would be this command's only refusal a user cannot read.
    try:
        plans = [
            ExecutionPlan.build(
                dag,
                source=source,
                span=span,
                replicate=target,
                source_end=end,
                picked=identities,
            )
            for target, identities in zip(targets, picked, strict=True)
        ]
    except ValueError as error:
        raise refuse(str(error)) from error

    if dry_run:
        for plan in plans:
            typer.echo(_describe(plan))
        return

    store: FrameStore = MemoryFrameStore()
    # Before the container opens, for `_bind`'s reason: everything that can refuse
    # a checkpoint refuses on declarations alone, and discovering after a minute
    # of decoding that a node id cannot be a file name is a message that was
    # available immediately.
    try:
        writers = [_checkpoints(project, video, project_path, plan) for plan in plans]
    except CheckpointWriteError as error:
        raise refuse(str(error)) from error

    # One reader for the footage, shared by every replicate: a reader is a pool
    # of decode threads, so an open per arena is v2's reopening. Every plan here
    # runs one graph, so one format and one reader answer for all of them.
    with ExitStack() as open_files:
        reader: FrameSource = _UNFED
        if _reads_the_footage(dag):
            reader = open_files.enter_context(frame_source(video, luma=plans[0].luma))
        for plan, writer in zip(plans, writers, strict=True):
            _execute_one(plan, reader, store, writer)


def _reads_the_footage(dag: Dag) -> bool:
    """Whether any root of this graph is fed by the run's reader.

    A graph every root of which opens its own file — a project served entirely
    by written crops, or a folder of already-cut files — reads the parent
    nowhere, and opening it would be a decode pool built for a container nothing
    asks a frame of. `footage_end` still opens it once, because the span and the
    trailing clamp are facts about the source whatever the graph roots on.
    """
    return len(dag.source_roots) < len(dag.roots)


class _UnfedReader:
    """The reader a graph with no footage-fed root is handed.

    A refusal rather than `None`, so the absence cannot be threaded through
    `execute` as an optional and read back as "no frames yet". Reaching it means
    a root the walk above counted as self-opening asked for a source frame,
    which is a disagreement between two derivations rather than a missing file.
    """

    def read(self, index: int | FrameIndex) -> FrameSource:  # pragma: no cover - unreachable
        raise VideoDecodeError(
            f"frame {int(index)} was asked of the source video, but every root of this graph "
            "opens its own file, so no container was opened for it"
        )


_UNFED = _UnfedReader()


def frame_source(video: Path, *, luma: bool) -> PrefetchFrameSource:
    """The reader a span is decoded through.

    `luma` is not an option and must never become one: it is
    `not Dag.needs_chroma` for the graph about to run, and a `--luma` flag would
    let a user pick a format the cache key says was not used.
    """
    return PrefetchFrameSource(video, luma=luma)


def _external_inputs(
    project: Project, dag: Dag, targets: Sequence[Replicate | None]
) -> tuple[dict[str, str], ...]:
    """What every replicate's source roots read, checked before anything is keyed.

    One walk, three readers. It answers what the run is owed and what is absent
    (`resolve_source.source_files`), whether what is there is what the document
    recorded (`Project.check_input_hashes`), and what identifies each file for
    the keys (`resolve_source.picked_identities`) — a second walk would be a
    second answer to which file this run reads, and the third reader is the one
    that would have been keyed on it.

    Per replicate rather than once, because a path parameter is an ordinary
    parameter: `Replicate.overrides` is sparse over arbitrary names and asks
    nothing about what a parameter means, so a source root's path resolves per
    replicate whether or not any pipeline deviates it, and one walk would answer
    for the wrong file the day one does.

    The two refusals are ordered as the reports read, and each is complete
    across the fan-out before the next runs: a missing file has no hash to
    compare, so every absent input is named first, and only then is every
    recorded input that changed named. Refusing the first replicate's absence
    would leave a reviewer fixing one file per run.

    Raises:
        SourceFileError: naming every source root, in every replicate, whose
            pattern names no file or several.
        ExternalInputChanged: naming every recorded input that is not the file
            that was recorded.
        InvalidParamsError: if a replicate's resolved parameters are not valid
            for their tool. Reached here rather than at the plan because this is
            now the first thing that resolves them.
        OSError: if a file that resolved cannot then be read or statted.
    """
    files: list[dict[str, Path]] = []
    absent: list[str] = []
    for target in targets:
        try:
            files.append(source_files(dag, validated_params(dag, target)))
        except SourceFileError as error:
            absent.append(f"{_label(target)}: {error}")
    if absent:
        raise SourceFileError("\n".join(absent))
    changed = [
        f"{_label(target)}: {error}"
        for target, resolved in zip(targets, files, strict=True)
        if (error := _recorded_fault(project, resolved)) is not None
    ]
    if changed:
        raise ExternalInputChanged("\n".join(changed))
    return tuple(picked_identities(resolved) for resolved in files)


def _recorded_fault(project: Project, files: Mapping[str, Path]) -> ExternalInputChanged | None:
    """`project`'s complaint about `files`, or `None` if it has none.

    The exception caught and handed back so `_external_inputs` can collect one
    per replicate; the rule itself is the model's and is not restated here.
    """
    try:
        project.check_input_hashes(files)
    except ExternalInputChanged as error:
        return error
    return None


def _label(replicate: Replicate | None) -> str:
    """What a replicate is called in output, the baseline included.

    One spelling, because a refusal that named a replicate differently from the
    line reporting its frames would be two names for one run.
    """
    return "baseline" if replicate is None else replicate.name


def read_range(plan: ExecutionPlan) -> SourceSpan:
    """`plan.decode_range` as the span `resolve` matches records against.

    A conversion rather than a second derivation: the frames a run reads are the
    plan's to state, and this is only the shape `resolve` takes them in. Shared
    with `materialize_cmd`, which cuts exactly what this certifies — a second
    spelling of it would drift into a file that serves no run.
    """
    reading = plan.decode_range
    return SourceSpan(start=int(reading.start), end=int(reading.stop))


def _checkpoints(
    project: Project, video: Path, project_path: Path, plan: ExecutionPlan
) -> CheckpointWriter | None:
    """The writer for this plan's checkpoints, or `None` if none are declared.

    The keys come from the plan rather than being recomputed, which is what makes
    the manifest's key the key this run actually looked entries up under. A node
    the cache may not hold is carried with a `None` key rather than dropped: it
    is still a result someone asked to keep.

    The product comes from the plan too, and for the same reason: `plan.params`
    is what the kernels were called with, so the name recorded is the product
    this replicate computed rather than the one the document's baseline would
    have. This is the only site that holds both the checkpoint list and the
    resolved parameters, which is why the derivation is here and the writer is
    handed the answer (`storage/checkpoint_writer.py`).
    """
    if not project.checkpoints:
        return None
    return CheckpointWriter(
        video,
        project_dir=project_path.parent,
        kept={
            node_id: Kept(
                key=plan.key(node_id),
                emission=selected_emission(
                    plan.dag.specs[node_id], plan.params[node_id].model_dump()
                ),
            )
            for node_id in project.checkpoints
        },
        span=plan.span,
        replicate=plan.replicate,
    )


def _execute_one(
    plan: ExecutionPlan,
    reader: FrameSource,
    store: FrameStore,
    checkpoints: CheckpointWriter | None = None,
) -> None:
    """Run one replicate's plan, write its checkpoints, and print what it did.

    Counted rather than collected: the executor yields a `FrameResult` per frame
    holding every node's output, and a list of them is the whole run resident in
    memory for no reason a count does not serve. A checkpoint is fed from that
    same stream frame by frame for the same reason — see
    `storage/checkpoint_writer.py` on why it is not accumulated.

    Raises:
        typer.Exit: code 1 if the graph holds a node this executor cannot call,
            if the footage cannot supply a frame the plan asked for, or if a
            declared checkpoint cannot be written whole.
    """
    label = _label(plan.replicate)
    if not plan.warmed:
        typer.echo(
            f"{label}: warning — {plan.lead_in_shortfall.frames} of "
            f"{plan.lead_in.frames} lead-in frames are before the start of the video, "
            "so the first outputs are under-warmed"
        )
    if plan.trailing_shortfall != NO_FRAMES:
        typer.echo(
            f"{label}: warning — the last {plan.trailing_shortfall.frames} frames asked for "
            f"are not answered for, because {', '.join(plan.looks_ahead)} reads "
            f"{plan.lookahead.frames} frames past every frame it reports and the video ends; "
            f"the run covers {plan.span.start}:{plan.span.end}"
        )
    computed = 0
    hits = 0
    written: tuple[Sink, ...] = ()
    try:
        for result in execute(plan, reader, store=store):
            computed += 1
            hits += len(result.from_cache)
            if checkpoints is not None:
                checkpoints.record(int(result.index), result.outputs)
        if checkpoints is not None:
            written = checkpoints.close()
    except UnrunnableNodeError as error:
        raise refuse(str(error)) from error
    except VideoDecodeError as error:
        raise refuse(f"{label}: {error}") from error
    except CheckpointWriteError as error:
        raise refuse(f"{label}: {error}") from error
    finally:
        # After `close` this is a no-op, so the one call covers every way out —
        # a decode failure, a cancelled iterator, and the refusals above, each of
        # which would otherwise leave a part file sized for a span that never
        # arrived.
        if checkpoints is not None:
            checkpoints.abandon()
    nodes = computed * len(plan.dag.order)
    typer.echo(
        f"{label}: {computed} frames, {nodes - hits} node outputs computed, {hits} from cache"
    )
    for sink in written:
        typer.echo(f"{label}: checkpointed {sink.node_id} as {sink.format} in {sink.path}")


def _refuse_sinks(project: Project) -> None:
    """Refuse a project whose declared outputs nothing can write yet.

    Raises:
        typer.Exit: code 1 if the project declares any.
    """
    if project.outputs:
        listed = ", ".join(f"{sink.format} -> {sink.path}" for sink in project.outputs)
        raise refuse(
            f"this project declares outputs ({listed}) and nothing resolves a declared sink format "
            "to a writer yet, so a run would compute every frame and write none of them. Remove "
            "them to run the graph anyway, or checkpoint the node instead."
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
    label = _label(plan.replicate)
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


def footage_of(graph: Pipeline, path: Path, replicates: Sequence[Replicate] = ()) -> Path:
    """The video `graph` roots on, or refuse because it roots on none.

    Every command that decodes goes through this rather than picking a root of
    its own, so which root is the footage is decided once
    (`resolve_source.footage_root`) and a document under construction is a
    refusal with an exit code rather than a traceback out of a walk.

    Takes the *anchored* graph, because what a relative parameter means is the
    project file's directory and this resolves the parameter to a file.

    Raises:
        typer.Exit: code 1 if the graph roots on no decoded source, or if the
            root it does name resolves to no file or to several.
    """
    try:
        return footage_file(graph, path, replicates=replicates)
    except (NoFootage, SourceFileError) as error:
        raise refuse(str(error)) from error
    except ValidationError as error:
        raise refuse(f"{path} names footage its source tool refuses:\n{error}") from error


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


def footage_end(video: Path) -> FrameIndex:
    """One past the last frame `video` holds.

    The one fact this command opens a container to learn before it decodes
    anything, and it answers both of the questions `pipeline` cannot: where the
    fallback span ends, and where the plan's trailing window has to stop
    (`pipeline/plan.py` on `source_end`). One call, because a second open of the
    same file to ask the same question is a pool build per question.

    Raises:
        VideoDecodeError: if the container will not open.
    """
    with VideoReader(video) as reader:
        return FrameIndex(reader.metadata.frame_count)


def span_for(frames: str | None, end: FrameIndex | None) -> SourceSpan:
    """Which frames to work over: the flag, else the whole video.

    Two answers where v2 had three, and the missing one is the middle: a v2
    project recorded a tuning range on the document and this fell back to it.
    Schema v1 records none — the representative stretch is the `span` tool, in
    the graph like everything else (`adr/detector-is-a-node.md`) — so a project
    narrows a run by holding a selecting node, which `ExecutionPlan` intersects
    into `plan.span` well after this has answered.

    Takes the length rather than the path because the fallback is not the only
    thing a run needs it for, and a function that opened the container here would
    be the second opener of a file the caller already has to open anyway.

    Raises:
        typer.Exit: code 1 for an unparseable `--frames`, or for no span and no
            length to fall back on.
    """
    if frames is not None:
        return parse_span(frames)
    if end is None:
        raise refuse(
            "no span was given, so it comes from the video's length — which is not known here "
            "because nothing opened the container, and --dry-run is the invocation that does "
            "not. Pass --frames START:END."
        )
    return SourceSpan(start=0, end=int(end))
