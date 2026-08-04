"""`sieve materialize` — cut one replicate's crop to a file and record it.

Headless because O3 says the artifact must be creatable without a GUI: the
gesture that will normally make one is a click in the chain stack, but a crop of
a two-hour source is a job someone wants to start over ssh and walk away from,
and a GUI-only writer would make the cluster path the special case again.

**The format is derived, never chosen.** `--format` does not exist and must not:
the artifact holds what the current graph decodes (`Dag.needs_chroma`), and a
flag would let a user write a colour file for a luma session, which is the one
combination the codec finding proved reads back as plausible wrong pixels. A
project whose graph later grows a chroma-reading filter falls through to the
parent and may write a second artifact; that is a second file, not a mode.

**One replicate per invocation.** Not a limitation to be lifted later: a crop is
minutes of decode, and a command that quietly started twelve of them is a
command whose cost nobody estimated. A loop in a shell script is the honest
form of "all of them", and it prints per-artifact progress for free.
"""

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
            exists=True, dir_okay=False, readable=True, help="A .sieve.yaml project file."
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
    """Write one replicate's crop to disk and register it on the project.

    The project file is rewritten in place with the new record — an artifact
    nothing points at is an artifact the next session will re-cut, so the write
    and the registration are one command rather than two.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, a replicate that names nothing, a span the footage cannot
            supply, or a written file that did not read back as what was fed.
    """
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
    except MaterializeCancelledError as error:  # pragma: no cover - no canceller here
        raise refuse(str(error)) from error
    except OSError as error:
        raise refuse(f"could not write the crop: {error}") from error

    project.with_crop(artifact).save(project_path)
    written = artifact.resolve(project_path.parent)
    typer.echo(f"{target.name}: wrote {artifact.path} ({written.stat().st_size / 1e6:.1f} MB)")


def _target(project: Project, wanted: str) -> Replicate:
    """The replicate `--replicate` names, by id first and then by name.

    Ids before names because an id is unambiguous and a name is not: two arenas
    may legitimately share a display name, and a command that picked one of them
    by document order would write an artifact for whichever was drawn first. An
    ambiguous name is refused with both ids, so the retry is a copy and paste.

    Raises:
        typer.Exit: code 1 if it names nothing, or names more than one.
    """
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
    raise refuse(f"{len(named)} replicates are named {wanted!r}; pass one of these ids: {ids}")
