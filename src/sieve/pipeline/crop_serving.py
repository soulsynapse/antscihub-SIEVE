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
document, so re-wiring the crop node back costs nothing but the edit.

**The records are not consumed.** `Project.crops` still holds them after the
edit, because they are still where the files are and what they were cut from —
`crop_binding.py` reads them to tell a user which state a box is in, and its
four states now say whether an edit is *offerable* rather than whether a run
will be served. What changed is who acts on the answer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from glob import escape

from sieve.core.pipeline_model import CropRecord, Node, Pipeline, Project, Replicate
from sieve.core.tool_base import ParamsBase
from sieve.core.types import ROI
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import validated_params
from sieve.pipeline.source_home import SourceHome
from sieve.tools.crop import CropParams

#: The tool a written crop is wired in as. Named here rather than branched on:
#: this is the one place in `pipeline` that decides a tool by id, and it does so
#: because it is *writing* a document rather than reading one — the walks that
#: read it back find the node by `ToolSpec.source`, which is the kind.
FOOTAGE_TOOL = "footage"
FOOTAGE_VERSION = "1.0.0"


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


def crop_roots(dag: Dag, params: Mapping[str, ParamsBase]) -> tuple[tuple[str, ROI], ...]:
    """Every node a written file could stand for, with the box it would hold.

    Recognised by the resolved params type rather than by a tool id: the box is
    `CropParams.region`, `materialize_crop` cut it with that same tool, so the
    type *is* the claim that a file can stand where this node stands, and
    `pipeline` stays out of the business of knowing tools by name.

    Roots only, because a record is cut from the parent footage and a crop of
    some other node's output is a crop of something no file on disk holds.

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
        `(node_id, region)` per root crop node, in graph order.
    """
    return tuple(
        (node.node_id, resolved.region)
        for node in dag.order
        if isinstance(resolved := params[node.node_id], CropParams)
        and not dag.upstreams[node.node_id]
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

    The node id and every edge touching it survive, which is the whole reason
    the substitution is an edit rather than a graph rewrite: the consumers of a
    crop node are the consumers of the file that holds its output, so nothing
    below the seam moves and no checkpoint, override or sink has to be renamed.

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
        edges=pipeline.edges,
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
