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

`footage_root` is the same ADR read from the other end. The document has no
field naming the video, so *which* of a graph's source roots a run means when it
says "the footage" is a question about the graph, and this is the one place that
answers it — the CLI's `source` and `source_end`, the window's player, and the
library card's footage line all read it here rather than each picking a root.

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

from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from sieve.core.pipeline_model import Node, Pipeline, Replicate, moved_default, resolved_params
from sieve.core.tool_base import ParamsBase, SourceFileError, ToolSpec
from sieve.core.tool_registry import REGISTRY, ToolRegistry, UnknownToolError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag


class NoFootage(ValueError):
    """A reader that needs frames was handed a graph that roots on none.

    What `adr/superseded/a-document-may-name-no-footage.md` bought, moved to
    where the graph can be seen: the state refused is a document with no decoded
    source root, which is the shape a project under construction has and is one
    `Dag.build` can already describe. Named rather than an `IndexError` off an
    empty walk, and carrying the project file rather than the graph, because the
    user is looking at a library and the actionable half of the news is which of
    those projects has no footage yet.
    """


def footage_root(
    pipeline: Pipeline, registry: ToolRegistry | None = None
) -> tuple[Node, ToolSpec] | None:
    """Which of `pipeline`'s source roots is *the footage*, with its tool.

    **The tie-break, and it is stated nowhere else.** Removing `Project.source`
    removes the field and not the question: `ExecutionPlan.build` still takes one
    `source` string and one `source_end`, `Dag.node_keys` still folds that string
    into every reader-fed root, and a window still opens one player. So a graph
    that roots on two files has to say which of them those readers mean, and the
    answer here is *the first decoded source root in document order*.

    Decoded rather than any source root, because the readers that ask are the
    ones that decode: `source_end` is a frame count out of a container, and a
    `pick` root over a background still is not the video however early it is
    written (`core/tool_base.ToolSource.decoded`,
    `adr/a-root-keys-by-its-reader.md`). Document order rather than the
    topological one, because a root has no ancestors to be sorted behind and
    document order is the order the user drew the steps in — the same tie-break
    the walk breaks its siblings on (`gui/walk.py`), and one available to a
    caller holding a `Pipeline` that will not build.

    Two roots read through the decoder is therefore a document whose *second*
    video is footage to the executor and not to the plan's span. That is
    admitted rather than refused: the graph is legal, every node computes, and
    the only thing the choice moves is which container the fallback span is
    taken from.

    Args:
        pipeline: The graph, `anchored` already if the caller wants the file
            rather than the spelling.
        registry: Where tools are looked up, for `anchored`'s reason.

    Returns:
        The node and its spec, or `None` for a graph that decodes no file of its
        own — a project under construction, or one served entirely by roots that
        read their own files with their own code.
    """
    shelf = REGISTRY if registry is None else registry

    def resolved(node: Node) -> ToolSpec | None:
        try:
            return shelf.get(node.tool_id, node.version)
        except UnknownToolError:
            # `anchored`'s treatment of a missing tool, for its reason: a window
            # drawing a document has to survive one, and a root this install
            # cannot resolve is not a root it can call the footage either.
            return None

    return _first_decoded_root(pipeline, resolved)


def footage_root_of(dag: Dag) -> tuple[Node, ToolSpec] | None:
    """`footage_root` asked of a graph that has built, against the graph's specs.

    The same tie-break and not a second one: a caller holding a `Dag` has the
    resolved spec per node already, and looking each up again could answer off a
    different shelf than the one the graph was built against.
    """
    return _first_decoded_root(dag.pipeline, lambda node: dag.specs.get(node.node_id))


def _first_decoded_root(
    pipeline: Pipeline, spec_of: Callable[[Node], ToolSpec | None]
) -> tuple[Node, ToolSpec] | None:
    """`footage_root`'s walk, over whatever answers what a node's tool is."""
    fed = {edge.downstream for edge in pipeline.edges}
    for node in pipeline.nodes:
        if node.node_id in fed:
            continue
        spec = spec_of(node)
        if spec is not None and spec.source is not None and spec.source.decoded:
            return node, spec
    return None


def footage_file(
    pipeline: Pipeline,
    project_path: Path,
    registry: ToolRegistry | None = None,
    replicates: Sequence[Replicate] = (),
) -> Path:
    """The file the footage root reads, resolved.

    **The baseline first, then the fan-out, because a path parameter is an
    ordinary parameter.** `Replicate.overrides` is sparse over arbitrary names
    and asks nothing about what a parameter means, so a document may deviate its
    footage root per arena and leave the node's own `path` empty — a folder of
    already-cut files is exactly that project. The callers of this each want one
    video for the whole invocation (a span's end, a checkpoint folder's name),
    which is what the departed schema field gave them, so the answer is the
    first target that resolves one: the baseline where there is one, and
    otherwise the first replicate in document order. Every *key* is still the
    per-replicate walk's (`source_files`), so nothing about what a run computes
    reads this.

    Args:
        pipeline: The graph, `anchored` against the project file's directory —
            a relative parameter read against the process's directory here would
            be the anchoring undone one call later.
        project_path: The project file, named in the refusal because that is the
            actionable half of it.
        registry: Where tools are looked up.
        replicates: The document's replicates, in order, for the fan-out clause
            above. Omitting them asks the baseline alone.

    Raises:
        NoFootage: if the graph roots on no decoded source.
        SourceFileError: if no target's parameters name one file — the
            baseline's message when there are no replicates, and the last
            replicate's otherwise.
        ValidationError: if its parameters are not valid for its tool.
    """
    found = footage_root(pipeline, registry)
    if found is None:
        raise NoFootage(
            f"{project_path} names no footage: add a source to its pipeline before running it"
        )
    node, spec = found
    assert spec.source is not None  # `footage_root` is defined by it
    absent: SourceFileError | None = None
    for target in (None, *replicates):
        params = spec.params_model.model_validate(resolved_params(node, target))
        try:
            return spec.source.file(params)
        except SourceFileError as error:
            absent = error
    assert absent is not None  # the loop runs at least once
    raise absent


def named_footage(pipeline: Pipeline, registry: ToolRegistry | None = None) -> str:
    """What the footage root's path parameter names, as written; `""` for none.

    `footage_file` for a caller that must not touch the filesystem — a library
    card drawing forty projects, and a window handing a path to the decode
    thread whose answer about whether the file is there is the one that counts
    (`gui/app.open_project`). It reports the spelling and asks nothing of disk,
    so a source nobody has chosen a file for and a graph with no source root
    both come back empty, which is one state to the person looking at the shelf.
    """
    found = footage_root(pipeline, registry)
    if found is None:
        return ""
    node, spec = found
    for name in spec.path_params:
        if isinstance(held := node.params.get(name), str) and held:
            return held
    return ""


def anchored(
    pipeline: Pipeline, project_dir: Path, registry: ToolRegistry | None = None
) -> Pipeline:
    """`pipeline` with every relative path parameter read against `project_dir`.

    **Where a source tool's path is anchored, and it is here rather than in the
    tool** (`adr/a-document-names-footage-only-through-a-tool.md`). The property
    the schema's own footage field existed for — a path meaningless without the
    directory holding the project file, so that a folder can move and the project
    still open — is every source node's path param's now, and a param cannot
    carry it on its own:
    the tools resolve a pattern with no idea what document it came out of, and
    one taught the project directory would be `pipeline` resolving a second time
    (`tools/footage.FootageFile.file`).

    So the anchoring is a rewrite of the graph on the way into a run, before
    anything is keyed. That ordering is the ADR's — "resolution happens before
    the key" — and preceding the build is precisely what would put this rewrite's
    product *into* the build's input, so it is not what leaves
    `adr/a-users-file-wires-in-like-any-other-input.md`'s exclusion rule
    untouched. What leaves that rule untouched is `cache_key.node_key` dropping a
    source tool's path parameter from its digest, which is where the argument
    lives; until it did, this function's product was the project's own directory
    inside every key below a source
    (`findings/2026.08.10-anchoring-puts-the-project-directory-into-the-node-key.md`).

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
