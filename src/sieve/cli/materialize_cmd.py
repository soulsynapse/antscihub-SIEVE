from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sieve.cli.common import load_project, refuse, span_for
from sieve.core.pipeline_model import Project
from sieve.core.replicates import Replicate
from sieve.decode.reader import VideoDecodeError
from sieve.filters import discover
from sieve.pipeline.dag import graph_needs_chroma
from sieve.pipeline.materialize import (
    CropVerificationError,
    MaterializeCancelledError,
    materialize_crop,
)
from sieve.storage.crop_writer import CropWriteError


def materialize_replicate(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="A .sieve.yaml project file.",
        ),
    ],
    replicate: Annotated[
        str,
        typer.Option("--replicate", help="Which replicate to cut, by name or id."),
    ],
    frames: Annotated[
        str | None,
        typer.Option(
            "--frames",
            help="Span to cut, as START:END, half-open. Overrides the project's clip.",
        ),
    ] = None,
) -> None:
    discover()
    project = load_project(project_path)
    video = project.source_path(project_path)
    target = _target(project, replicate)
    span = span_for(project, frames, video)
    luma = not graph_needs_chroma(project.pipeline)
    typer.echo(
        f"{target.name}: cutting {span.frame_count} frames "
        f"[{span.start}:{span.end}) at {target.roi.width}x{target.roi.height}, "
        f"{'luma' if luma else 'colour'}"
    )
    try:
        artifact = materialize_crop(
            video,
            target,
            span,
            project_dir=project_path.parent,
            luma=luma,
        )
    except (VideoDecodeError, CropWriteError, CropVerificationError) as error:
        raise refuse(str(error)) from error
    except MaterializeCancelledError as error:
        raise refuse(str(error)) from error
    except OSError as error:
        raise refuse(f"could not write the crop: {error}") from error
    project.with_crop(artifact).save(project_path)
    written = artifact.resolve(project_path.parent)
    typer.echo(
        f"{target.name}: wrote {artifact.path} ({written.stat().st_size / 1e6:.1f} MB)"
    )


def _target(project: Project, wanted: str) -> Replicate:
    for candidate in project.replicates:
        if candidate.replicate_id == wanted:
            return candidate
    named = [candidate for candidate in project.replicates if candidate.name == wanted]
    if len(named) == 1:
        return named[0]
    if not named:
        known = ", ".join(candidate.name for candidate in project.replicates) or "none"
        raise refuse(f"no replicate named {wanted!r}; this project has: {known}")
    ids = ", ".join(candidate.replicate_id for candidate in named)
    raise refuse(
        f"{len(named)} replicates are named {wanted!r}; pass one of these ids: {ids}"
    )
