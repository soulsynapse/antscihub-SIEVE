"""`sieve materialize` — cut one replicate's crop to a file and record it.

Headless because the artifact must be creatable without a GUI: the gesture that
will normally make one is a click in the chain stack, but a crop of a two-hour
source is a job someone wants to start over ssh and walk away from, and a
GUI-only writer would make the cluster path the special case again.

**Nothing here is handed what v2 was handed.** v2's command read a frame range
off the project and a region off the replicate, and schema v1 records neither: the
region is a per-replicate override of a root crop node's `region`
(`adr/detector-is-a-node.md`), and the frames are the `span` tool's parameters in
the graph. Both arrive here through `ExecutionPlan` rather than off the document,
because a plan is the one place a replicate's deviation has been resolved into a
value and the one place a selecting node has been folded into a range. The work
this command actually does is that derivation, and refusing clearly when the
document does not determine it.

**It cuts the window, not the span.** `plan.decode_range` rather than
`plan.span`: a graph with any lead-in reads frames either side of the ones it
answers for, out of whichever file serves it, so a file cut to the answer alone
is declined by `resolve` at the next run and the decode is paid twice
(`pipeline/resolve_source.py` on `want`). The span here is the whole video
narrowed by the graph, which is the widest window any narrower invocation of
`sieve run` can ask for, so one cut serves them all.

**The format is derived, never chosen.** `--format` does not exist and must not:
the artifact holds what the current graph decodes (`ExecutionPlan.luma`), and a
flag would let a user write a colour file for a luma session, which is the one
combination v2's codec finding proved reads back as plausible wrong pixels. A
project whose graph later grows a chroma-reading tool falls through to the
parent and may write a second artifact; that is a second file, not a mode.

**One replicate per invocation.** Not a limitation to be lifted later: a crop is
minutes of decode, and a command that quietly started twelve of them is a command
whose cost nobody estimated. A loop in a shell script is the honest form of "all
of them", and it prints per-artifact progress for free.

**Write and registration are one command.** An artifact nothing points at is an
artifact the next session re-cuts — minutes of decode paid again in silence — so
cutting and recording happen in the same call rather than two.

The refusals `load_project`, `refuse`, `span_for` and `footage_end` speak with are
`run_cmd`'s own rather than respelled, as in `preview_cmd`: two commands refusing
in two spellings would be two spellings of every error message a user sees.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sieve.cli.run_cmd import footage_end, load_project, read_range, refuse, span_for
from sieve.core.pipeline_model import Project, Replicate
from sieve.core.tool_base import SourceFileError
from sieve.core.types import ROI
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.materialize import (
    CropVerificationError,
    MaterializeCancelledError,
    materialize_crop,
)
from sieve.pipeline.plan import ExecutionPlan, validated_params
from sieve.pipeline.resolve_source import crop_roots, picked_identities, source_files
from sieve.storage.crop_writer import CropWriteError
from sieve.tools import discover


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
) -> None:
    """Cut one replicate's crop to a file and record it in the project.

    Raises:
        typer.Exit: code 1 for anything refused deliberately — an invalid
            document, a graph that does not resolve, no such replicate, footage
            that is not where the project says, a graph that does not determine
            one box to cut, a replicate pinning no box on it, or a write that
            failed or did not read back as what was fed to it.
    """
    discover()
    project = load_project(project_path)
    video = project.source_path(project_path)
    target = _target(project, replicate)

    try:
        dag = Dag.build(project.pipeline)
    except GraphError as error:
        raise refuse(str(error)) from error
    try:
        source = source_identity(video)
        end = footage_end(video)
    except (OSError, VideoDecodeError) as error:
        raise refuse(f"source video will not open: {video}: {error}") from error
    # The whole video before the graph has its say, which is what `span_for`
    # answers with no `--frames` — and there is no `--frames` here, because which
    # frames are in the answer is the `span` tool's to declare and a flag would be
    # a second, unrecorded way to say it.
    try:
        plan = ExecutionPlan.build(
            dag,
            source=source,
            span=span_for(None, end),
            replicate=target,
            source_end=end,
            picked=_picked(dag, target),
        )
    except ValueError as error:
        raise refuse(str(error)) from error

    region = _region(dag, plan, target)
    span = read_range(plan)
    typer.echo(
        f"{target.name}: cutting {span.frame_count} frames "
        f"[{span.start}:{span.end}) at {region.width}x{region.height}, "
        f"{'luma' if plan.luma else 'colour'}"
    )
    try:
        record = materialize_crop(
            video,
            region,
            span,
            name=target.name,
            project_dir=project_path.parent,
            luma=plan.luma,
        )
    except (VideoDecodeError, CropWriteError, CropVerificationError) as error:
        raise refuse(str(error)) from error
    except MaterializeCancelledError as error:  # pragma: no cover - no canceller here
        raise refuse(str(error)) from error
    except OSError as error:
        raise refuse(f"could not write the crop: {error}") from error

    project.with_crop(record).save(project_path)
    written = record.resolve(project_path.parent)
    typer.echo(f"{target.name}: wrote {record.path} ({written.stat().st_size / 1e6:.1f} MB)")


def _picked(dag: Dag, target: Replicate) -> dict[str, str]:
    """What identifies each source root's file, for the plan this cuts from.

    The walk `sieve run` does at run start (`pipeline/resolve_source.py`), so the
    plan derived here is keyed as the plan a run of this graph is keyed — a front
    end building one without it builds a differently-keyed description of the
    same run, and `Dag.node_keys` drops the subtree under every root it was given
    no identity for.

    Where the refusals differ, and deliberately: a cut opens the footage and
    never a picked file, so an input that does not resolve costs those nodes
    their keys and stops nothing. `sieve run` refuses the same graph, because a
    run is what reads the file.
    """
    try:
        return picked_identities(source_files(dag, validated_params(dag, target)))
    except SourceFileError:
        return {}


def _region(dag: Dag, plan: ExecutionPlan, target: Replicate) -> ROI:
    """The box this replicate's file would hold, or a refusal naming why not.

    Where `crop_bound` falls back to the parent on an ambiguous graph, this
    refuses: serving is an acceleration and guessing wrong there costs only
    speed, while guessing wrong here writes minutes of decode into a file
    recorded as a cut it is not.

    Raises:
        typer.Exit: code 1 if the graph offers no root crop node or more than
            one, or if the replicate pins no region on the one it offers.
    """
    roots = crop_roots(dag, plan.params)
    if not roots:
        raise refuse(
            "this graph has no crop node reading the source, so there is no region to cut. A "
            "written crop stands in for a crop of the footage, which is a root crop node's "
            "output; a crop of some other node's output is a crop of something no file holds."
        )
    if len(roots) > 1:
        named = ", ".join(node_id for node_id, _ in roots)
        raise refuse(
            f"this graph has {len(roots)} crop nodes reading the source ({named}), and nothing "
            "in the document says which one a written file would stand for. Leave one at the "
            "root and the box is unambiguous."
        )
    node_id, region = roots[0]
    if "region" not in target.override_for(node_id):
        raise refuse(
            f"replicate {target.name!r} overrides no region at {node_id!r}, so this would cut "
            f"the graph's own box and record it under one replicate's name. A replicate's "
            f"geometry is its override of that node's region; pin the box first."
        )
    return region


def _target(project: Project, wanted: str) -> Replicate:
    """The replicate to cut, by id or by name.

    Ids before names: an id is unambiguous, a name is not — two arenas may
    legitimately share a display name, and picking by document order would write
    an artifact for whichever was drawn first.

    Raises:
        typer.Exit: code 1 if no replicate answers to `wanted`, or if more than
            one is named it.
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
    # Ids in the message so the retry is a copy-paste, not a rename.
    ids = ", ".join(candidate.replicate_id for candidate in named)
    raise refuse(f"{len(named)} replicates are named {wanted!r}; pass one of these ids: {ids}")
