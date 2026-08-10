"""Wiring a written crop into the graph, as an edit the project holds.

`adr/a-users-file-wires-in-like-any-other-input.md` settles that a file standing
where a node stood is an instance of the source-tool mechanism rather than a
path beside it. This is the crop half of that: the match a resolver used to make
per run — which record can serve this box — happens once and its product is a
`Project`, not a file handed to a run already planned. Everything downstream of
the document is then ordinary. A front end builds a `Dag` and runs it; the
executed graph holds a `footage` node where the crop node was and no crop node at
all, so `sieve run`, a preview session and a render worker are served alike
without any of them learning that artifacts exist. That is the gap that used to
be real — the plan-time route existed in one command, and the other two decoded
the parent and re-cut a box already on disk.

**Whole document or nothing.** One pipeline serves every replicate, so a crop
node cannot be a `footage` node for the arena whose file exists and a crop for the
arena whose file does not. The offer is therefore made only when every target has a
record for every root crop node, and `sieve materialize` cuts one replicate per
invocation — so a twelve-arena project becomes offerable on the twelfth cut and
not before. The alternative, a per-replicate graph, is a second answer to what a
project computes and is what `adr/one-execution-path.md` refuses.

**Coverage stops being a per-run clause.** The plan-time route certified a
record against the frames a run would read and fell back to the parent when the
window reached past what was cut. There is no fallback once the file *is* the
source — that is the same position a folder of already-cut files is in, which is the
case that forced the ADR — so a run asking for frames the file does not hold is
a decode error naming the file (`tools/footage.py`). What replaces the clause is
that `materialize_cmd` cuts the whole video's read range, so the file covers
every narrower invocation, and the edit is reversible: the records stay in the
document, so re-wiring the crop node back costs nothing but the edit —
`unserving_edit`, which is the one that performs it.

**The records are not consumed.** `Project.crops` still holds them after the
edit, because they are still where the files are and what they were cut from —
`crop_binding.py` reads them to tell a user which state a box is in, and its
four states now say whether an edit is *offerable* rather than whether a run
will be served. What changed is who acts on the answer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from glob import escape

from sieve.core.pipeline_model import (
    CropRecord,
    Edge,
    Node,
    Pipeline,
    Project,
    Replicate,
    resolved_params,
)
from sieve.core.tool_base import ParamsBase
from sieve.core.types import ROI
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import validated_params
from sieve.pipeline.resolve_source import footage_root, footage_root_of
from sieve.pipeline.source_home import SourceHome
from sieve.tools.crop import CropParams

#: The tool a written crop is wired in as. Named here rather than branched on:
#: this is the one place in `pipeline` that decides a tool by id, and it does so
#: because it is *writing* a document rather than reading one — the walks that
#: read it back find the node by `ToolSpec.source`, which is the kind.
FOOTAGE_TOOL = "footage"
FOOTAGE_VERSION = "1.0.0"

#: What the reverse edit writes back. The version the node was replaced *at* is
#: not in the document any more — `_wired` stamped `FOOTAGE_VERSION` over it — so
#: an unserved node comes back at the version this build cuts with, which is the
#: version a graph drawn today would carry.
CROP_TOOL = "crop"
CROP_VERSION = "1.0.0"


def serving_edit(project: Project, home: SourceHome, *, dag: Dag | None = None) -> Project | None:
    """`project` with each root crop node replaced by a read of its written file.

    Args:
        project: The document to offer an edit for.
        home: What its records are read against — the parent's identity and the
            directory their paths resolve from, the same value `crop_binding`
            takes so a report and an offer cannot disagree.
        dag: The graph, if the caller already built it. Built here otherwise;
            the two are the same graph and this only avoids a second walk.

    Returns:
        The edited project, or `None` when the substitution is not offerable —
        no root crop node, a target with no record backing its box, or a crop
        node someone asked to checkpoint. Idempotent by construction: a project
        already served holds no crop node, so a second call answers `None`.
    """
    graph = Dag.build(project.pipeline) if dag is None else dag
    luma = not graph.needs_chroma
    targets: tuple[Replicate | None, ...] = tuple(project.replicates) or (None,)
    served: list[tuple[Replicate | None, dict[str, CropRecord]]] = []
    node_ids: tuple[str, ...] = ()
    for target in targets:
        roots = crop_roots(graph, validated_params(graph, target))
        if not roots:
            return None
        node_ids = tuple(node_id for node_id, _ in roots)
        chosen: dict[str, CropRecord] = {}
        for node_id, region in roots:
            record = _backing(project.crops, region, home=home, luma=luma)
            if record is None:
                return None
            chosen[node_id] = record
        served.append((target, chosen))
    if any(node_id in project.checkpoints for node_id in node_ids):
        # A node whose output someone asked to keep has to run. Replacing it
        # would leave the manifest naming a key nothing looked anything up
        # under, and — unlike the plan-time route, which could drop the node for
        # one run — an edit removes it from the document the checkpoint names.
        return None
    if targets == (None,):
        # No fan-out, so the one target's files are the nodes' own parameters
        # and there is no replicate to carry them.
        return project.with_pipeline(_wired(project.pipeline, node_ids, served[0][1], home))
    return project.with_pipeline(_wired(project.pipeline, node_ids)).with_replicates(
        tuple(
            _deviated(target, chosen, home)
            for target, chosen in served
            if target is not None  # every target is a replicate on this branch
        )
    )


def unserving_edit(project: Project, home: SourceHome, *, dag: Dag | None = None) -> Project | None:
    """`project` with each served `footage` node cut back into the crop it stood for.

    The inverse of `serving_edit`, and the reason this module's header can call
    that edit reversible: the records are not consumed, so the node's tool and
    every replicate's box are still readable out of them.

    **Read per node and per replicate rather than whole-document.** The offer is
    all-or-nothing because a pipeline cannot be a crop for one arena and a
    `footage` node for another; the way back has no such constraint, because
    every state it has to undo was written by the forward edit and the forward
    edit served every arena at once. What it must survive instead is the arena
    that was drawn *after* — a replicate carrying a `region` override of a node
    whose tool has no such parameter, which is the document that saves and then
    fails every plan. That replicate resolves no `path`, so nothing here matches
    it and its override is left exactly where the front end wrote it, valid
    again the moment the node is a crop node.

    `cut_from` is deliberately not matched, where `serving_edit` matches it: a
    record that no longer backs anything — the parent was re-exported, the box
    moved — is precisely the state a user needs the way out of, and a reverse
    edit that declined for it would refuse the case it exists for.

    Args:
        project: The document to unwire, served or not.
        home: What its records are read against; only `project_dir` is read, and
            the whole value is taken so the pair of edits take one argument.
        dag: The graph, if the caller already built it.

    Returns:
        The edited project, or `None` when no node in it is a written crop
        standing where a crop node stood — an unserved project, or a folder of
        files somebody else cut, which has no crop node to go back to.
    """
    graph = Dag.build(project.pipeline) if dag is None else dag
    written = {escape(str(record.resolve(home.project_dir))): record for record in project.crops}
    targets: tuple[Replicate | None, ...] = tuple(project.replicates) or (None,)
    backing: dict[str, dict[str | None, CropRecord]] = {}
    for node in graph.source_roots:
        if node.tool_id != FOOTAGE_TOOL:
            continue
        for target in targets:
            path = resolved_params(node, target).get("path")
            record = written.get(path) if isinstance(path, str) else None
            if record is not None:
                backing.setdefault(node.node_id, {})[
                    None if target is None else target.replicate_id
                ] = record
    if not backing:
        return None
    unwired = project.with_pipeline(_uncut(project.pipeline, backing))
    if targets == (None,):
        return unwired
    return unwired.with_replicates(tuple(_undeviated(target, backing) for target in targets))


def _uncut(pipeline: Pipeline, backing: Mapping[str, Mapping[str | None, CropRecord]]) -> Pipeline:
    """`pipeline` with each node in `backing` turned back into a `crop` node.

    Mirrors `_wired` on both counts: the node id and its outgoing edges survive,
    and the node's own parameters carry the box only when there is no fan-out to
    carry it — a fanned-out project's boxes differ per replicate, so the
    baseline goes back to `crop`'s own default and `_undeviated` writes the pins.

    The edge `_wired` cut is put back, which is what makes the pair an edit and
    its undo rather than two edits: a crop of the footage reads the footage
    root, and a restored crop node left as a root would be a crop of the run's
    reader in a document that no longer has one
    (`adr/a-document-names-footage-only-through-a-tool.md`). The parent is the
    graph's own footage root, which the forward edit left in place for exactly
    this.
    """
    restored = Pipeline(
        nodes=tuple(
            Node(
                node_id=node.node_id,
                tool_id=CROP_TOOL,
                version=CROP_VERSION,
                params=(
                    {"region": asdict(backing[node.node_id][None].region)}
                    if None in backing[node.node_id]
                    else {}
                ),
            )
            if node.node_id in backing
            else node
            for node in pipeline.nodes
        ),
        edges=pipeline.edges,
    )
    parent = _parent_footage(restored, backing)
    if parent is None:
        return restored
    return restored.model_copy(
        update={
            "edges": restored.edges
            + tuple(Edge(upstream=parent, downstream=node_id) for node_id in backing)
        }
    )


def _parent_footage(pipeline: Pipeline, restored: Mapping[str, object]) -> str | None:
    """The footage root the un-served crop nodes are cuts of, if the graph has one."""
    found = footage_root(
        pipeline.model_copy(
            update={"nodes": tuple(node for node in pipeline.nodes if node.node_id not in restored)}
        )
    )
    return None if found is None else found[0].node_id


def _undeviated(
    replicate: Replicate, backing: Mapping[str, Mapping[str | None, CropRecord]]
) -> Replicate:
    """`replicate` pinning each unwired node's box again instead of its file.

    `_deviated`'s inverse and its mirror image: the path and offset are dropped
    rather than left beside the region, because they name parameters `crop` does
    not have. A node this replicate was not served at is untouched — that is the
    arena drawn after the edit, which already carries the override it needs.
    """
    undeviated = replicate
    for node_id, records in backing.items():
        record = records.get(replicate.replicate_id)
        if record is not None:
            undeviated = undeviated.without_override(node_id).with_override(
                node_id, {"region": asdict(record.region)}
            )
    return undeviated


def crop_roots(dag: Dag, params: Mapping[str, ParamsBase]) -> tuple[tuple[str, ROI], ...]:
    """Every node a written file could stand for, with the box it would hold.

    Recognised by the resolved params type rather than by a tool id: the box is
    `CropParams.region`, `materialize_crop` cut it with that same tool, so the
    type *is* the claim that a file can stand where this node stands, and
    `pipeline` stays out of the business of knowing tools by name.

    **Cutting the footage, which since
    `adr/a-document-names-footage-only-through-a-tool.md` is one clause and not
    one shape.** A record is cut from the parent footage, so what qualifies is a
    crop node nothing has reshaped above — and the footage reaches the graph as
    a source node now, so that is either a root or a node whose only upstream is
    the footage root (`resolve_source.footage_root_of`). A crop of any other
    node's output is a crop of something no file on disk holds, and roots alone
    would have retired the whole mechanism the day the field left the schema.

    All of them rather than the one, and the reason narrowed when the route
    became an edit. Serving used to replace the run's whole reader, so a second
    box — or any other root the footage fed — left nothing that could be served
    and the answer had to be "none of them". A `footage` node replaces one node and
    touches no other root, so two boxes are two independent substitutions and
    the node beside them keeps reading the footage. What still reads the whole
    tuple is `cli/materialize_cmd.py`, which refuses with the nodes named rather
    than cutting a box it picked.

    Args:
        dag: The graph about to run.
        params: Resolved parameters per node id — `plan.validated_params`, so
            the box is the one the replicate being processed actually resolved
            to and nothing re-derives an override.

    Returns:
        `(node_id, region)` per crop node cutting the footage, in graph order.
    """
    found = footage_root_of(dag)
    unreshaped = () if found is None else (found[0].node_id,)
    return tuple(
        (node.node_id, resolved.region)
        for node in dag.order
        if isinstance(resolved := params[node.node_id], CropParams)
        and dag.upstreams[node.node_id] in ((), unreshaped)
    )


def _backing(
    crops: Sequence[CropRecord], region: ROI, *, home: SourceHome, luma: bool
) -> CropRecord | None:
    """The first record that backs `region`, or `None`.

    Document order and first match wins, `resolve`'s rule for `resolve`'s
    reason: two records matching one request are one cut written twice under two
    names, which `Project.with_crop` de-duplicates by identity, so order only
    ever decides between equally correct files. The span is not a clause — see
    this module's header.
    """
    for record in crops:
        if record.backs(region, source=home.identity, luma=luma, project_dir=home.project_dir):
            return record
    return None


def _wired(
    pipeline: Pipeline,
    node_ids: Sequence[str],
    chosen: dict[str, CropRecord] | None = None,
    home: SourceHome | None = None,
) -> Pipeline:
    """`pipeline` with each of `node_ids` turned into a `footage` node.

    The node id and every edge *out of* it survive, which is the whole reason
    the substitution is an edit rather than a graph rewrite: the consumers of a
    crop node are the consumers of the file that holds its output, so nothing
    below the seam moves and no checkpoint, override or sink has to be renamed.

    The edges *into* it do not survive, and since
    `adr/a-document-names-footage-only-through-a-tool.md` there is one to cut: a
    crop of the footage is fed by the footage root (`crop_roots`), and a source
    tool with an upstream is a node reading a file and a stream at once. What
    the parent root then feeds is whatever else was reading it, and nothing when
    every crop of it was served — a graph that still names the project's footage
    and no longer reads it.

    `chosen` fills the nodes' own parameters, for a project with no fan-out. In
    a fanned-out project the files differ per replicate, so the node is left at
    its empty default and `_deviated` carries them.
    """
    return Pipeline(
        nodes=tuple(
            Node(
                node_id=node.node_id,
                tool_id=FOOTAGE_TOOL,
                version=FOOTAGE_VERSION,
                params=(
                    {}
                    if chosen is None or home is None
                    else _footage_params(chosen[node.node_id], home)
                ),
            )
            if node.node_id in node_ids
            else node
            for node in pipeline.nodes
        ),
        edges=tuple(edge for edge in pipeline.edges if edge.downstream not in node_ids),
    )


def _deviated(replicate: Replicate, chosen: dict[str, CropRecord], home: SourceHome) -> Replicate:
    """`replicate` pointing each served node at its own file.

    The region override is dropped rather than left beside the new one: it names
    a parameter `footage` does not have, so a document keeping it would fail
    validation on the first run — and it would be a claim about a box nothing in
    the graph cuts any more.
    """
    deviated = replicate
    for node_id, record in chosen.items():
        deviated = deviated.without_override(node_id).with_override(
            node_id, _footage_params(record, home)
        )
    return deviated


def _footage_params(record: CropRecord, home: SourceHome) -> dict[str, object]:
    """What a `footage` node reads `record`'s file with.

    An absolute path, because a tool resolves its pattern against the process's
    directory and the record's relative-to-the-project rule has no reader inside
    one (`tools/footage.py` on `file`). The cost is a document that does not move
    with its folder the way `CropRecord.path` does; the record it was written
    from still does, so re-offering the edit after a move is what corrects it.
    """
    # `glob.escape`, because a path is a pattern here and `glob` reads `*`, `?`
    # and brackets as syntax: a folder someone named `arena[1]` would otherwise
    # resolve to no file at all, and the refusal would name a path that is
    # plainly sitting there.
    return {
        "path": escape(str(record.resolve(home.project_dir))),
        "first_index": record.span.start,
    }
