"""Which external file each source root reads, and what identifies it.

One question, asked of the graph and answered before anything is keyed: a source
tool is a root whose file is a path parameter, so the document already names
every external file a run opens. `source_files` walks that out and
`picked_identities` turns it into what the keys want.

`resolved_sources` is the same walk with a front end asking rather than a run:
the whole ordering a parameter names instead of the one file a reader takes, and
lenient where the run refuses.

`anchored` is the step before either of them, and it is here because it is the
half of the resolution the tools cannot do: a path stored relative to the
project file means nothing to a tool that never saw the document
(`adr/a-document-names-footage-only-through-a-tool.md`).

**What used to be here, and where it went.** This module was also the plan-time
route that decided, per run, whether a written crop could serve it — a match
against `CropRecord`, a graph with the crop node dropped, and a reader wrapped
in the artifact's numbering offset.
`adr/a-users-file-wires-in-like-any-other-input.md` settles that the
substitution is a document edit rather than a route, so the match now happens
once and its product is a `Project` (`pipeline/crop_serving.py`); the file is
read by a `footage` node like any other source root (`tools/footage.py`), and the
numbering offset is that tool's `first_index`. Nothing routes here any more,
which is why the two front ends that never learned the route — a preview session
and a render worker — are now served by exactly the same walk `sieve run` uses.

**Nothing below this module learns that artifacts exist**, and that claim is now
structural rather than maintained: `cache_key.py`, `plan.py` and `executor.py`
are handed a graph in which a written crop is a source root, and a source root
is a thing they already had.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from pydantic import ValidationError

from sieve.core.pipeline_model import Node, Pipeline, moved_default
from sieve.core.tool_base import ParamsBase, SourceFileError, ToolSpec
from sieve.core.tool_registry import REGISTRY, ToolRegistry, UnknownToolError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag


def anchored(
    pipeline: Pipeline, project_dir: Path, registry: ToolRegistry | None = None
) -> Pipeline:
    """`pipeline` with every relative path parameter read against `project_dir`.

    **Where a source tool's path is anchored, and it is here rather than in the
    tool** (`adr/a-document-names-footage-only-through-a-tool.md`). The property
    `SourceRef` existed for — a path meaningless without the directory holding
    the project file, so that a folder can move and the project still open — is
    the source node's path param's now, and a param cannot carry it on its own:
    the tools resolve a pattern with no idea what document it came out of, and
    one taught the project directory would be `pipeline` resolving a second time
    (`tools/footage.FootageFile.file`).

    So the anchoring is a rewrite of the graph on the way into a run, before
    anything is keyed. That ordering is the ADR's — "resolution happens before
    the key" — and it is what leaves
    `adr/a-users-file-wires-in-like-any-other-input.md`'s rule untouched: the
    pattern still never enters a key, and what is hashed is still the resolved
    file's own identity (`cache_key.picked_key`).

    A *rewrite* and not a load step, because the document keeps the relative
    spelling that makes it movable. Nothing here is saved back — a session
    anchors what it runs and holds what it read, and a build that wrote this
    product to disk would have replaced the portability it was derived to serve.

    Absolute parameters are handed through untouched, which is every parameter a
    file picker and `pipeline/crop_serving.py` write today, so this changes the
    meaning of relative ones alone.

    Args:
        pipeline: The document's graph, as it was read.
        project_dir: The directory holding the project file.
        registry: Where tools are looked up, for `Dag.build`'s reason.

    Returns:
        The graph with each `ToolSpec.path_params` entry made absolute. A node
        whose tool this install does not have is passed through rather than
        refused — resolving is not where a missing tool is reported
        (`pipeline/dag.py`), and a window drawing a document has to survive one.
    """
    shelf = REGISTRY if registry is None else registry
    rewritten: list[Node] = []
    for node in pipeline.nodes:
        try:
            spec = shelf.get(node.tool_id, node.version)
        except UnknownToolError:
            rewritten.append(node)
            continue
        moved = {
            name: str(Path(project_dir, held))
            for name in spec.path_params
            # An unset param stays unset: a source nobody has chosen a file for
            # is a document state, and joining `""` onto the project directory
            # would turn it into a run over that folder's contents
            # (`tool_base.named_files`).
            if isinstance(held := node.params.get(name), str)
            and held
            and not Path(held).is_absolute()
        }
        rewritten.append(moved_default(node, moved) if moved else node)
    return pipeline.model_copy(update={"nodes": tuple(rewritten)})


def source_files(dag: Dag, params: Mapping[str, ParamsBase]) -> dict[str, Path]:
    """The external file each source root reads, or every one that is not there.

    **The derived list VISION's reviewer is owed, and it is derived on every
    call.** A source tool is a root whose file is a path parameter, so the graph
    already names every external file a run opens; a field on `Project`
    repeating them would be a second copy that can disagree with the nodes it
    describes and would need a migration this has nothing to migrate. A rewired
    graph is answered for the moment it is rewired.

    Nothing here knows what a picked file is. The tool resolves its own pattern
    (`ToolSource.file`), which is what keeps `pipeline` from globbing a second
    time and disagreeing, and what keeps this walk from branching on a tool id.

    Every root is asked before any refusal is raised, because the promise is
    that a reviewer with three unmounted inputs learns about three. `ToolSource.
    file` refuses one file at a time and cannot know there is a second.

    Args:
        dag: The graph about to run.
        params: Resolved parameters per node id — `plan.validated_params`, so a
            replicate that deviated its own pattern resolves its own file.

    Returns:
        `node_id` to the file it reads, for the source roots only. `{}` for a
        graph with no source tool, which owes nothing and is the shape every
        project had before one existed.

    Raises:
        SourceFileError: naming every source root whose pattern names no file or
            several, rather than the first. Raised rather than skipped: a run
            that cannot say which file it is reading cannot be keyed *or*
            executed, and the executor would reach the same refusal one decode
            later — after the reviewer has waited for it.
    """
    files: dict[str, Path] = {}
    faults: list[str] = []
    for node in dag.source_roots:
        spec = dag.specs[node.node_id]
        assert spec.source is not None  # `source_roots` is defined by it
        try:
            files[node.node_id] = spec.source.file(params[node.node_id])
        except SourceFileError as absent:
            faults.append(f"{node.node_id}: {absent}")
    if faults:
        raise SourceFileError("\n".join(faults))
    return files


def resolved_sources(
    nodes: Iterable[Node], specs: Mapping[str, ToolSpec]
) -> dict[str, tuple[Path, ...]]:
    """What each source root's parameter names on disk right now, ordered.

    `source_files` asked of a document rather than of a run, and the two
    differences are the two callers. This one is *lenient* — a source with
    nothing chosen, a parameter that will not validate, a folder that is not
    there — because a window has to draw whatever document was opened and none
    of those is a reason to refuse to draw it, where a run cannot start without
    an answer. And it returns the whole ordering rather than one file, because
    what a folder names is what a front end shows: VISION's scenario has "two
    files now show in the source tool" and there is no reading of that where the
    window was told about one.

    The rule itself is not restated. Both walks call the tool's own resolution
    (`ToolSource.files`, `ToolSource.file`), so a folder means the same thing to
    the window and to the run, and there is nowhere for the two to drift apart.

    **This is a filesystem read, and it is therefore a fact with a lifetime.** A
    file dropped into a folder between two calls changes the answer with the
    document untouched, which is what makes a held copy of this go stale and
    what its holder has to invalidate on (`gui/app.py`).

    Args:
        nodes: The document's nodes, in any order — one node's answer does not
            depend on another's.
        specs: The spec behind each node id, leniently: `gui/app.resolved_specs`
            skips a tool this install does not have, and a node with no entry is
            one nothing can be resolved for.

    Returns:
        `node_id` to the ordered files it names, for the source roots only, and
        `()` for a source root whose parameter names nothing that is there.
    """
    resolved: dict[str, tuple[Path, ...]] = {}
    for node in nodes:
        spec = specs.get(node.node_id)
        if spec is None or spec.source is None:
            continue
        try:
            params = spec.params_model.model_validate(node.params)
            resolved[node.node_id] = tuple(spec.source.files(params))
        except (ValidationError, SourceFileError, OSError):
            # Three shapes of "no answer yet", and the window draws all three
            # the same: a document may hold a source nobody has chosen a file
            # for, and a folder that is not mounted is that document again with
            # a drive missing rather than a project that is wrong.
            resolved[node.node_id] = ()
    return resolved


def picked_identities(files: Mapping[str, Path]) -> dict[str, str]:
    """What identifies each source root's file, for the run's keys.

    Here rather than in `plan.py` for the reason `source` is a string there: a
    plan is derivable where nothing is mounted, and this stats a file.

    Takes `source_files`' answer rather than re-walking the graph, so the file a
    run is keyed on is the file it reported present. The two questions a run
    start asks of an external input — is it there, and is it the one that was
    recorded (`Project.check_input_hashes`) — read from that same walk for the
    same reason.

    One identity per root and no flavour: which key a root's identity is folded
    into follows the *reader* and is `Dag.node_keys`' to decide off the tool's
    declaration (`adr/a-root-keys-by-its-reader.md`). A caller choosing here
    would be choosing for a file it has only statted.

    Args:
        files: `source_files`' mapping of source root to the file it reads.

    Returns:
        `node_id` to `cache_key.source_identity`. Hand it to
        `ExecutionPlan.build` as `picked`.

    Raises:
        OSError: if a file that resolved cannot then be statted.
    """
    return {node_id: source_identity(file) for node_id, file in files.items()}
