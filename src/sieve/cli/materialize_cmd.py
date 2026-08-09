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
is a file every wider run then reads past the end of. The span here is the whole
video narrowed by the graph, which is the widest window any narrower invocation
of `sieve run` can ask for, so one cut serves them all — and once the cut is
wired in there is no parent to fall back to, so what used to cost a second
decode now costs the refusal `tools/footage.py` names.

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

**Write, registration and wiring are one command.** An artifact nothing points
at is an artifact the next session re-cuts — minutes of decode paid again in
silence — so cutting and recording happen in the same call rather than two. The
wiring is the third of those for the same reason and lands the moment it can:
`crop_serving.serving_edit` is offerable only when every replicate has a file,
so the invocation that cuts the last one is the one that replaces the crop node
with a `footage` node over each. Before that it answers `None` and the document is
saved with the record alone. Cutting one replicate per invocation is what makes
that a real state rather than a formality.

The unwiring is the same sentence read backwards and lands at the other end of
the same call, in `_unwired`. A served project has no crop node, so cutting one
would otherwise be impossible — no re-cut after the parent moves, no thirteenth
arena on twelve — and the way out has to be the command that is already being
asked for the state it produces.

The refusals `load_project`, `refuse`, `span_for` and `footage_end` speak with are
`run_cmd`'s own rather than respelled, as in `preview_cmd`: two commands refusing
in two spellings would be two spellings of every error message a user sees.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sieve.cli.run_cmd import footage_end, footage_of, load_project, read_range, refuse, span_for
from sieve.core.pipeline_model import Project, Replicate
from sieve.core.tool_base import SourceFileError
from sieve.core.types import ROI
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.crop_serving import crop_roots, serving_edit, unserving_edit
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.materialize import (
    CropVerificationError,
    MaterializeCancelledError,
    materialize_crop,
)
from sieve.pipeline.plan import ExecutionPlan, validated_params
from sieve.pipeline.resolve_source import picked_identities, source_files
from sieve.pipeline.source_home import SourceHome
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
            document, a graph that does not resolve, no such replicate, a document
            naming no footage, footage that is not where the project says, a graph that does not determine
            one box to cut, a replicate pinning no box on it, or a write that
            failed or did not read back as what was fed to it.
    """
    discover()
    project = load_project(project_path)
    video = footage_of(project, project_path)

    try:
        source = source_identity(video)
        end = footage_end(video)
    except (OSError, VideoDecodeError) as error:
        raise refuse(f"source video will not open: {video}: {error}") from error
    home = SourceHome(video=video, project_dir=project_path.parent, identity=source)
    project = _unwired(project, home)
    target = _target(project, replicate)
    try:
        dag = Dag.build(project.pipeline)
    except GraphError as error:
        raise refuse(str(error)) from error
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

    recorded = project.with_crop(record)
    wired = serving_edit(recorded, home, dag=dag)
    (recorded if wired is None else wired).save(project_path)
    written = record.resolve(project_path.parent)
    typer.echo(f"{target.name}: wrote {record.path} ({written.stat().st_size / 1e6:.1f} MB)")
    if wired is not None:
        typer.echo(
            "every replicate is now backed by a written crop, so the crop node has been "
            "replaced by a read of each file — this project no longer decodes the parent"
        )


def _unwired(project: Project, home: SourceHome) -> Project:
    """`project` with any serving edit taken back out, or `project` unchanged.

    Implicit rather than a flag or a second command, and this is the invocation
    that decides it: asking to cut a served project is asking for the state in
    which there is something to cut. A `--unserve` the user had to know to pass
    would spell the refusal `_region` used to raise as an argument instead of a
    sentence, and the answer to "how do I add a thirteenth arena" would still be
    a hand edit of YAML.

    It is not a mode the command leaves the document in. The wiring below runs on
    the same invocation and re-takes the edit as soon as every replicate has a
    file again, so the visible cost of a re-cut is a re-cut. Where it does not —
    a parent that has been re-exported, so the other replicates' records no
    longer back anything — the document is left unserved deliberately: those
    files are stale, and a project that decodes the parent is the honest state to
    leave someone in.
    """
    unwired = unserving_edit(project, home)
    if unwired is None:
        return project
    typer.echo(
        "this project was reading written crops, so the crop node has been wired back in "
        "from the records it kept — it decodes the parent again until every replicate is cut"
    )
    return unwired


def _picked(dag: Dag, target: Replicate) -> dict[str, str]:
    """What identifies each source root's file, for the plan this cuts from.

    The walk `sieve run` does at run start (`resolve_source.source_files`), so the
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

    Where `crop_serving.serving_edit` declines to offer an edit for a graph it
    cannot read one box out of, this refuses with the nodes named: declining
    costs a user an offer they can still make by hand, and guessing wrong here
    writes minutes of decode into a file recorded as a cut it is not.

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
