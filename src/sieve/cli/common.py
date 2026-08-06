"""The four things every command that opens a project has to do the same way.

Extracted when `sieve preview` became the second command to load a document,
parse a span, and refuse an invocation. None of these is interesting on its own;
what is interesting is that two spellings of them would be two spellings of every
error message a user sees, and one of the two would be the one that stopped
saying `--frames` when the flag was renamed. `sieve run` and `sieve preview`
refuse identically because they refuse from here.

Deliberately not a base class or a shared option set. The commands genuinely
differ in what they take — a preview is one arena and a run is all of them — and
a framework that unified them would make the next command's differences the
hard case.
"""

from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sieve.core.filter_registry import FilterRegistry
from sieve.core.pipeline_model import ClipRange, Project
from sieve.core.replicates import Replicate
from sieve.decode.ffmpeg import FfmpegLoweredFrameSource, ffmpeg_decoder_identity
from sieve.decode.lowered import LoweredPrefix
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoDecodeError, VideoReader
from sieve.pipeline.dag import Dag
from sieve.pipeline.lowering import lower_resolved_source
from sieve.pipeline.resolve_source import ResolvedSource

#: The `--workers` option, shared by every command that decodes a span.
#:
#: One definition because it is one decision: how much of this machine the run
#: may use. VISION step 6 puts machine capability on the command line rather than
#: in the project document, so this is where it lives and there is no
#: corresponding field on `Project` — a `threads:` key in the artifact would make
#: one machine's allocation part of another machine's reproducible run.
#:
#: A batch script passes `--workers $SLURM_CPUS_PER_TASK`. `resolve_workers`
#: deliberately does not read that variable itself.
WORKERS_OPTION = typer.Option(
    "--workers",
    min=1,
    help="Decode threads. Defaults to what this process is allowed, capped. "
    "1 is the sequential reader.",
)


FrameSourceContext = PrefetchFrameSource | FfmpegLoweredFrameSource


def frame_source(
    video: Path,
    workers: int | None,
    *,
    luma: bool = False,
    lowered_prefix: LoweredPrefix | None = None,
) -> FrameSourceContext:
    """The reader a span is decoded through, however many threads it gets.

    Always a `PrefetchFrameSource`, including at one worker, so that `--workers 1`
    is the same code path with an empty window rather than a second reader class
    the option switches between. `VideoReader` is what it is built out of, so the
    frames are byte-identical at any count — which is why this can be the default
    without a cache generation.

    `luma` is not an option and must never become one: it is
    `not Dag.needs_chroma` for the graph about to run, and a `--luma` flag would
    let a user pick a format the cache key says was not used. Callers derive it
    from the plan and pass it; the default is colour so that a caller which has
    not been taught to derive it is slow rather than wrong.
    """
    if lowered_prefix is None:
        return PrefetchFrameSource(video, workers=workers, luma=luma)
    if not luma:
        raise VideoDecodeError(
            "a lowered FFmpeg source emits gray frames, but this graph needs colour"
        )
    return FfmpegLoweredFrameSource(video, lowered_prefix, workers=workers)


def lower_source_contract(
    dag: Dag,
    resolved: ResolvedSource,
    replicate: Replicate | None,
    *,
    registry: FilterRegistry | None = None,
    protected_nodes: tuple[str, ...] = (),
) -> tuple[Dag, ResolvedSource]:
    """Move a safe root crop/area-scale prefix into FFmpeg, or decline."""
    if resolved.pre_cropped or dag.needs_chroma:
        return dag, resolved
    try:
        with VideoReader(resolved.path, luma=True) as reader:
            metadata = reader.metadata
        decoder = ffmpeg_decoder_identity()
    except VideoDecodeError:
        return dag, resolved
    return lower_resolved_source(
        dag,
        resolved,
        replicate=replicate,
        source_metadata=metadata,
        decoder_identity=decoder,
        registry=registry,
        protected_nodes=protected_nodes,
    )


def refuse(message: str) -> typer.Exit:
    """Print `message` to stderr and hand back the exception to raise.

    Returning rather than raising so that every refusal reads
    `raise refuse(...)` — a helper that raised would be a control-flow jump a
    reader has to know about, and one that a type checker cannot see ends the
    function.
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


def parse_span(frames: str) -> ClipRange:
    """`START:END` as a half-open range.

    Colon-separated rather than two options, because the two numbers are one
    quantity and a shell history holding `--frames 100:400` is legible in a way
    that `--start 100 --end 400` is not. Half-open, matching `ClipRange`, which
    is what the executor is written against — a CLI that took an inclusive end
    would be the one place in the system where a range means something else.

    Raises:
        typer.Exit: code 1 if it is not two integers around a colon.
    """
    start, separator, end = frames.partition(":")
    if not separator:
        raise refuse(f"--frames takes START:END, got {frames!r}")
    try:
        parsed = ClipRange(start=int(start), end=int(end))
    except ValueError as error:
        raise refuse(f"--frames {frames!r}: {error}") from error
    return parsed


def span_for(
    project: Project, frames: str | None, video: Path, *, dry_run: bool = False
) -> ClipRange:
    """Which frames to work over: the flag, else the project's clip, else the video.

    The last of those is the only one that needs the container open, which is why
    it is last and why `--dry-run` refuses instead of reaching it. A clip is what
    a project is normally run over — it is VISION step 4's tuning span — so the
    fallback is the uncommon path rather than the default.

    Raises:
        typer.Exit: code 1 for an unparseable `--frames`, or for a project with
            no clip on a path that may not open the video.
    """
    if frames is not None:
        return parse_span(frames)
    if project.clip is not None:
        return project.clip
    if dry_run:
        raise refuse(
            "this project has no clip, so the span comes from the video's length — which "
            "--dry-run does not open. Pass --frames START:END."
        )
    with VideoReader(video) as reader:
        return ClipRange(start=0, end=reader.metadata.frame_count)
