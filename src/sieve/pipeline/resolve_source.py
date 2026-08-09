"""Which external file each source root reads, and what identifies it.

One question, asked of the graph and answered before anything is keyed: a source
tool is a root whose file is a path parameter, so the document already names
every external file a run opens. `source_files` walks that out and
`picked_identities` turns it into what the keys want.

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

from collections.abc import Mapping
from pathlib import Path

from sieve.core.tool_base import ParamsBase, SourceFileError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag


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
