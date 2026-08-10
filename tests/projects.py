"""Building a document whose footage is where the schema now keeps it.

`adr/a-document-names-footage-only-through-a-tool.md` took `Project.source`
away, so every fixture that used to say "this project is about that video" says
it by wiring a `footage` node over the roots the run's reader used to feed. That
rewrite is one shape repeated across the corpus, and it is here rather than in
each file because the shape is the migration: a case that spelt it itself would
be asserting against its own idea of what a footage root looks like.

The node is prepended, so it is first in document order and therefore *the*
footage (`pipeline/resolve_source.footage_root`), and its path is stored
relative to the project file like every other stored path.

What a caller still owns is the arithmetic. A graph that grows a root computes
one more node per frame, reports one more output, and gives the walk one more
position — none of which this can adjust on a case's behalf.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from sieve.core.pipeline_model import Edge, Node, Pipeline, Project
from sieve.core.tool_registry import REGISTRY, UnknownToolError
from sieve.pipeline.resolve_source import anchored, footage_file, footage_root

#: The node id the wired-in root takes, fixed so a case can name it.
FOOTAGE_ID = "footage"


def relative_path(target: Path, project_dir: Path) -> str:
    """`target` as a source param stored beside a project file in `project_dir`."""
    try:
        spelt = os.path.relpath(target.resolve(), project_dir.resolve())
    except ValueError:  # no relative path exists across Windows drives
        return PurePosixPath(target.resolve()).as_posix()
    return PurePosixPath(spelt.replace(os.sep, "/")).as_posix()


def footage_node(video: Path, project_dir: Path, node_id: str = FOOTAGE_ID) -> Node:
    """A `footage` root reading `video`, spelt as a saved document spells it."""
    return Node(
        node_id=node_id,
        tool_id="footage",
        version="1.0.0",
        params={"path": relative_path(video, project_dir)},
    )


def rooted_on(
    pipeline: Pipeline, video: Path, project_dir: Path, node_id: str = FOOTAGE_ID
) -> Pipeline:
    """`pipeline` with a `footage` root over `video` feeding every reader-fed root.

    Reader-fed rather than every root: a graph that already opens its own files
    at some roots — a `pick` over a background, a written crop wired in — keeps
    those exactly as they were, because what is being replaced is the run's
    footage and not every external input. A root whose tool this build does not
    have counts as reader-fed, which is what it was before the tool went
    missing.
    """
    if footage_root(pipeline) is not None:
        # The graph already names footage (`resolve_source.footage_root`), so a
        # second decoded root would take the tie-break off the one the case
        # wired. A root that opens its own file *undecoded* — a checkpoint read
        # back — is not that, and its project still names the video it was cut
        # from, exactly as it did while the schema carried the field.
        return pipeline
    fed = {edge.downstream for edge in pipeline.edges}
    added = footage_node(video, project_dir, node_id)
    wired = tuple(
        Edge(upstream=node_id, downstream=node.node_id)
        for node in pipeline.nodes
        if node.node_id not in fed and not _opens_its_own_file(node)
    )
    return pipeline.model_copy(
        update={"nodes": (added, *pipeline.nodes), "edges": wired + pipeline.edges}
    )


def project_over(
    video: Path, project_dir: Path, pipeline: Pipeline | None = None, **fields: object
) -> Project:
    """A project whose graph roots on `video`, plus whatever else is asked for."""
    return Project(
        pipeline=rooted_on(pipeline if pipeline is not None else Pipeline(), video, project_dir),
        **fields,
    )


def footage_of(project: Project, project_path: Path) -> Path:
    """The file `project`'s graph roots on, resolved exactly as a run resolves it."""
    return footage_file(
        anchored(project.pipeline, project_path.parent), project_path, replicates=project.replicates
    )


def over(project: Project, video: Path, project_dir: Path, node_id: str = FOOTAGE_ID) -> Project:
    """`project` with its graph rooted on `video`, for a case that built the rest."""
    return project.with_pipeline(rooted_on(project.pipeline, video, project_dir, node_id))


def _opens_its_own_file(node: Node) -> bool:
    try:
        return REGISTRY.get(node.tool_id, node.version).source is not None
    except UnknownToolError:
        return False
