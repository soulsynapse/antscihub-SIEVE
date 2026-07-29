














from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sieve.core.pipeline_model import ClipRange, Project
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoReader











WORKERS_OPTION = typer.Option(
    "--workers",
    min=1,
    help="Decode threads. Defaults to what this process is allowed, capped. "
    "1 is the sequential reader.",
)


def frame_source(video: Path, workers: int | None, *, luma: bool = False) -> PrefetchFrameSource:














    return PrefetchFrameSource(video, workers=workers, luma=luma)


def refuse(message: str) -> typer.Exit:







    typer.echo(message, err=True)
    return typer.Exit(1)


def load_project(path: Path) -> Project:









    try:
        return Project.load(path)
    except ValidationError as error:
        raise refuse(f"{path} is not a valid project:\n{error}") from error


def parse_span(frames: str) -> ClipRange:











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
