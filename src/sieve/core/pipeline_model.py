"""The pipeline artifact: the serialized form a run is reproducible from.

Given this document and the source video it names, any executor — CLI, GUI, or
a batch job on a cluster — performs the same run and writes the same files.
That is the whole contract, and it is why nothing here may depend on anything
that exists in only one of those three: no widget geometry, no zoom, no scrub
position, no cache directory, no thread count. `extra="forbid"` throughout is
the machine-checked form of that rule (AUTO-GUARDRAILS §2) — stashing GUI state
in the artifact requires editing this file, which is the review the rule exists
to force.

**Deliberately not registry-aware.** Nothing here asks whether a filter named
by a node exists, what parameters it takes, or whether an edge's types chain.
Those are `pipeline/dag.py`'s job, against a `FilterRegistry`. The split is what
lets a project open on a machine where a filter is missing: the user gets "no
filter `wavelet_bands` at version 2.1.0", which names the thing to install,
rather than a parse error that names nothing. It is also what lets the GUI draw
a graph it cannot execute. What *is* checked here is structural — ids unique,
edges pointing at nodes that exist, `filter_id`/`version` syntactically able to
enter a cache key. Cycle detection is not, because it needs a traversal, it is
the first thing `dag.py` does, and two implementations means two answers.

**The identity line.** Everything on `Node` feeds the cache key; nothing else in
this module does, apart from the source and the replicate geometry at a root.
That is why `checkpoints` and `outputs` are lists on `Project` keyed by node id
rather than flags on `Node` itself: materializing an intermediate changes where
a result lives, never what it is, and a `materialize` field sitting next to
`params` would be one refactor away from being hashed with it. Keeping it off
the node makes that mistake unavailable rather than merely documented.
`tests/unit/test_pipeline_model.py` pins `Node`'s field set for the same reason.

**No measurements live here.** VISION steps 4, 5, and 7 want cost feedback per
operation, compaction suggestions driven by it, and a processing report at the
end. None of that belongs in this document: a timing is a fact about one
machine, and this is the one artifact two machines are required to agree about.
What the artifact owes benchmarking is addressability — `node_id` and `sink_id`
are stable, so a run report can key against them from outside — and that is all
it owes. A `measured_ms` on `Node` would break the identity line above.

**The HPC handoff is a derived document, not a config section.** VISION step 6
splits it correctly: machine capability (threads, memory, GPU) reaches the run
as command-line options, while what the wizard *tidies* is this document with
`checkpoints` emptied and `clip` dropped — a cluster with the memory to skip
compaction runs the same graph without it, and over the whole video rather than
the tuning span. Both are one field, which is the shape that split argues for.

**Replicates are a source-level fan-out.** One pipeline runs once per
replicate, which keeps the ordinary case (one chain, twelve arenas) a single
graph rather than twelve subgraphs the GUI has to generate and keep in step.
The alternative considered and rejected was one root node per replicate.

*This paragraph used to continue "every replicate is processed with identical
parameters, so a dim arena needing its own threshold is not expressible", and
called that consequence deliberate. It was not, and the sentence is recorded
rather than deleted so what follows reads as a reversal rather than as
something nobody had thought about.*

**Lateral inheritance from a moving default.** A replicate inherits a node's
parameters and may pin any subset of them (`Replicate.overrides`), appearing
identical until adjusted. The fan-out above survives that unchanged; what does
not survive is the assumption that `Node.params` is the whole of what gets
hashed. It is now the *default for replicates that have not been configured*,
`resolved_params` is what a cache key is built from, and every edit performs
two writes — see `Project.with_param_edit`, which is the only place the second
one happens.

The identity line above therefore reads one clause longer: everything on
`Node` feeds the cache key, but `params` feeds it only after resolution
against the replicate being processed. `Node.params` hashed on its own would
invalidate all twelve entries every time a thirteenth edit moved it, including
for replicates that pin every parameter and never read it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Self
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sieve.core.filter_base import FILTER_ID_PATTERN, SEMVER_PATTERN
from sieve.core.replicates import Replicate

#: Bumped when a saved document stops being readable by this code unchanged. A
#: reader refuses a document from the future rather than guessing at it: the
#: failure mode of guessing is a run that completes and is wrong.
SCHEMA_VERSION = 1

#: Project files are named `<video stem>.sieve.yaml` and live *beside* the
#: video they describe. VISION step 1 fixes the layout — a source in a folder,
#: its derivatives in child folders — and the project file is what names those
#: children, so it belongs at the root of that tree rather than in a
#: user-global application directory. The practical consequence is that copying
#: the folder copies the project, which is how footage reaches a cluster.
PROJECT_SUFFIX = ".sieve.yaml"

#: Sink formats and filter ids share a spelling rule for the same reason: both
#: are resolved by name at run time, and both appear in paths and CLI arguments
#: where case folding and shell quoting are not to be relied on.
_SINK_FORMAT_PATTERN = FILTER_ID_PATTERN


def project_path_for(video: Path) -> Path:
    """Where the project file for `video` belongs.

    A convention, not a lookup: the file need not exist.
    """
    return video.parent / (video.stem + PROJECT_SUFFIX)


def _new_id() -> str:
    return uuid4().hex


def _resolved(path: Path) -> Path:
    """Absolute, `..` collapsed, symlinks followed.

    `Path.resolve` rather than a lexical `normpath`: collapsing `a/link/..` to
    `a` is wrong whenever `link` is a symlink, and footage reached through a
    symlinked scratch mount is ordinary on the machines this runs on. The cost
    is a filesystem call, which is paid once when a project opens and is in no
    latency budget.
    """
    return path.resolve()


def _posix_relative(target: Path, base: Path) -> str:
    """`target` as a POSIX path relative to `base`, or absolute if it cannot be.

    No relative path exists across Windows drives, and there is no third
    option: such a project is still correct, it is merely no longer movable.
    """
    resolved = _resolved(target)
    try:
        relative = os.path.relpath(resolved, _resolved(base))
    except ValueError:
        return PurePosixPath(resolved).as_posix()
    return PurePosixPath(relative.replace(os.sep, "/")).as_posix()


class _Artifact(BaseModel):
    """Shared config for every model in the artifact.

    Frozen because a document that has been written to disk, hashed, or handed
    to an executor must not then change underneath it. Extra fields forbidden
    for the reason in the module docstring.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceRef(_Artifact):
    """The video a project is about, named relative to the project file.

    `path` is *not* resolved against the working directory — it means nothing
    without the directory holding the project file, which is why every reader
    goes through `resolve`. An absolute path would make a project unopenable
    the moment the folder moved.
    """

    path: str

    @field_validator("path")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source path must not be empty")
        return value

    @classmethod
    def relative_to(cls, video: Path, project_dir: Path) -> Self:
        """Reference `video` from a project file living in `project_dir`."""
        return cls(path=_posix_relative(video, project_dir))

    def resolve(self, project_dir: Path) -> Path:
        """The video's location, given where the project file was read from.

        Normalized, so that two references to one file compare equal. Returning
        the raw join instead would leave `..` segments in the result, and the
        first caller to compare two resolved paths would be comparing spellings.
        """
        return _resolved(Path(project_dir, self.path))


class ClipRange(_Artifact):
    """The representative five to ten seconds the user tunes against.

    VISION step 4's tuning span. Frame indices, not timestamps: `Frame.index`
    is the authoritative position for the same reason cache keys are built from
    it — container timestamps drift, and a clip that means a different span on
    reload is a clip that invalidates the tuning done against it.

    Half-open, `[start, end)`, matching `ROI.right` being one past the last
    column covered. It is project state and not GUI state because the executor
    needs it: warmup is requested as `[start - total_warmup, end)`.
    """

    start: int
    end: int

    @model_validator(mode="after")
    def _ordered_and_nonempty(self) -> Self:
        if self.start < 0:
            raise ValueError(f"clip start must be non-negative, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"clip must cover at least one frame, got [{self.start}, {self.end})")
        return self

    @property
    def frame_count(self) -> int:
        """Frames covered."""
        return self.end - self.start


class Node(_Artifact):
    """One filter application, named but not resolved.

    Every field here enters the cache key, and that is the invariant governing
    what may be added: a field that does not change the node's output does not
    belong on the node. See the module docstring — with the one qualification
    that `params` enters it only after `resolved_params` has been applied,
    because a replicate may deviate from it.

    `params` is an opaque mapping, not a parsed `ParamsBase`. The filter's
    parameter model is the only thing that knows what shape it should be, and
    it lives in `sieve.filters`, above this layer — validating here would either
    invert the layer stack or keep a second copy of the field list. `dag.py`
    resolves `filter_id` against the registry and feeds this dict to
    `params_model.model_validate`; that is the one place a parameter is checked.
    """

    #: Stable across reorderings and parameter edits, because edges,
    #: checkpoints, and sinks all reference it. Generated rather than derived
    #: from the filter id: two `downsample` nodes in one graph is ordinary.
    node_id: str = Field(default_factory=_new_id)
    filter_id: str
    version: str
    #: Not "the parameters" — "the default for replicates that have not been
    #: configured". It moves to the most recently configured values on every
    #: edit, so it must never enter a cache key on its own: a project where
    #: every replicate carries an override never reads it, and hashing it would
    #: invalidate all twelve entries every time it moved. Hash
    #: `resolved_params(node, replicate)` instead.
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("filter_id")
    @classmethod
    def _known_shape_id(cls, value: str) -> str:
        if not FILTER_ID_PATTERN.match(value):
            raise ValueError(f"filter_id must match {FILTER_ID_PATTERN.pattern!r}, got {value!r}")
        return value

    @field_validator("version")
    @classmethod
    def _known_shape_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.match(value):
            raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {value!r}")
        return value


def resolved_params(node: Node, replicate: Replicate | None = None) -> dict[str, Any]:
    """The parameters `node` actually runs with, for `replicate`.

    **The only definition of "effective params" in the system.** `cache_key.py`
    hashes this, the executor configures kernels from it, and the GUI shows it.
    A second implementation anywhere is how a preview and a batch run stop
    agreeing about what they computed, and the disagreement would be invisible,
    because both would report success against caches keyed on their own answer.

    A key-wise merge, deliberately. The override supplies only the parameters
    pinned on this replicate and everything else follows `node.params` as it
    moves, so one arena can hold its own threshold while still picking up a
    later change to a blur radius nobody varied.

    `replicate=None` is the node's baseline: what a graph inspected outside any
    fan-out shows, and what a project with no replicates runs.
    """
    if replicate is None:
        return dict(node.params)
    return {**node.params, **replicate.overrides.get(node.node_id, {})}


class Edge(_Artifact):
    """`upstream`'s output feeds `downstream`'s input, both by `node_id`."""

    upstream: str
    downstream: str

    @model_validator(mode="after")
    def _not_a_self_loop(self) -> Self:
        if self.upstream == self.downstream:
            raise ValueError(f"edge from {self.upstream} to itself")
        return self


class Sink(_Artifact):
    """A declared output: VISION step 6's "select a specific stage to output".

    Sinks are what make the artifact a runnable thing rather than a description
    of one — a graph with no sinks computes nothing anyone can look at, and
    `sieve run` over it would have nothing to write. They live on `Project`
    rather than on `Node` because an output location is not part of a node's
    identity; two projects writing the same computation to different folders
    must share cache entries.

    `path` names a *directory* relative to the project file, because a sink
    under replicate fan-out produces one output per replicate. VISION step 1's
    "the result of that lives in the child folder" is the default: a relative
    path with no `..` in it puts derivatives under the source's own folder.
    """

    #: Addressable so an HPC handoff can toggle one output without rewriting
    #: the list positionally (VISION step 6).
    sink_id: str = Field(default_factory=_new_id)
    #: The node whose output is written. Checked against the graph by `Project`.
    node_id: str
    #: Resolved by whatever writes it, exactly as `filter_id` is resolved by the
    #: registry. Not an enum: the writer set is open, and an enum in `core/`
    #: would be the manual-wiring problem non-negotiable #3 forbids for filters,
    #: reintroduced one layer down.
    format: str
    path: str
    #: Writer options — codec, frame rate, column selection. Opaque here for the
    #: same reason `Node.params` is.
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("format")
    @classmethod
    def _known_shape_format(cls, value: str) -> str:
        if not _SINK_FORMAT_PATTERN.match(value):
            raise ValueError(
                f"sink format must match {_SINK_FORMAT_PATTERN.pattern!r}, got {value!r}"
            )
        return value

    @field_validator("path")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sink path must not be empty")
        return value

    def resolve(self, project_dir: Path) -> Path:
        """The output directory, given where the project file was read from."""
        return _resolved(Path(project_dir, self.path))


class Pipeline(_Artifact):
    """The graph itself: no source video, no replicates, no output locations.

    Separate from `Project` because that is the boundary `dag.py` works at.
    Validating that a graph chains does not need to know what footage it runs
    on, and keeping the two apart is what stops a validator quietly growing a
    dependency on a decoded frame.

    A node with no incoming edge is a root: it consumes the source once per
    replicate, and what it consumes is that replicate's ROI crop — the fan-out
    has already happened by the time the graph starts, so there is no position
    in the graph from which an uncropped frame is observable. That is what makes
    a materialized crop a checkpoint rather than a mode: it is a faster source
    for the same pixels, and by the rule above it cannot change what is
    computed. See `docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.
    """

    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    @model_validator(mode="after")
    def _referential_integrity(self) -> Self:
        seen: set[str] = set()
        for node in self.nodes:
            if node.node_id in seen:
                raise ValueError(f"duplicate node_id {node.node_id!r}")
            seen.add(node.node_id)
        for edge in self.edges:
            for endpoint in (edge.upstream, edge.downstream):
                if endpoint not in seen:
                    raise ValueError(f"edge names no such node: {endpoint!r}")
        if len({(edge.upstream, edge.downstream) for edge in self.edges}) != len(self.edges):
            raise ValueError("duplicate edge")
        return self

    def __contains__(self, node_id: str) -> bool:
        return any(node.node_id == node_id for node in self.nodes)

    def node(self, node_id: str) -> Node:
        """The node carrying `node_id`.

        Raises:
            KeyError: if no node carries it.
        """
        for candidate in self.nodes:
            if candidate.node_id == node_id:
                return candidate
        raise KeyError(node_id)


class Project(_Artifact):
    """A source video, how it is cut, what runs on it, and what comes out.

    The whole reproducible unit. Everything a run needs beyond this is either
    machine configuration (where the cache lives, how many workers) or
    presentation (zoom, panel layout, which overlay is showing), and neither
    belongs in a document two machines are supposed to agree about.
    """

    schema_version: int = SCHEMA_VERSION
    source: SourceRef
    #: Ordered, and the order is meaningful: it is the order the user drew them
    #: in and the order per-replicate outputs are written in.
    replicates: tuple[Replicate, ...] = ()
    #: The span tuning runs against. `None` means the whole video.
    clip: ClipRange | None = None
    pipeline: Pipeline = Pipeline()
    #: Node ids whose output is materialized to disk — VISION step 4's "save
    #: that representative few seconds to the child layer". A run without them
    #: produces identical results and merely recomputes more, which is why they
    #: are recorded here and never hashed: the HPC wizard turns them off for a
    #: cluster with the memory to skip them (VISION step 6), and that must not
    #: change a single cache key.
    checkpoints: tuple[str, ...] = ()
    outputs: tuple[Sink, ...] = ()

    @field_validator("schema_version")
    @classmethod
    def _readable(cls, value: int) -> int:
        if value > SCHEMA_VERSION:
            raise ValueError(
                f"project uses schema version {value}; this build reads up to {SCHEMA_VERSION}"
            )
        return value

    @model_validator(mode="after")
    def _references_resolve(self) -> Self:
        ids = [replicate.replicate_id for replicate in self.replicates]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate replicate_id")
        for replicate in self.replicates:
            for node_id in replicate.overrides:
                # Same class of staleness as a checkpoint's, and the same
                # remedy. A deviation on a node that has been deleted is a
                # parameter set nothing will ever read, and it would survive
                # every save until a new node happened to be given the id.
                if node_id not in self.pipeline:
                    raise ValueError(
                        f"replicate {replicate.replicate_id!r} overrides no such node: {node_id!r}"
                    )
        for node_id in self.checkpoints:
            if node_id not in self.pipeline:
                raise ValueError(f"checkpoint names no such node: {node_id!r}")
        if len(set(self.checkpoints)) != len(self.checkpoints):
            raise ValueError("duplicate checkpoint")
        sink_ids = [sink.sink_id for sink in self.outputs]
        if len(set(sink_ids)) != len(sink_ids):
            raise ValueError("duplicate sink_id")
        for sink in self.outputs:
            if sink.node_id not in self.pipeline:
                raise ValueError(f"sink names no such node: {sink.node_id!r}")
        return self

    # ---- serialization ---------------------------------------------------

    def to_yaml(self) -> str:
        """The document as YAML text.

        `sort_keys=False` keeps declaration order — schema version, source,
        replicates, clip, graph, then what comes out of it — which is both
        readable and stable. Stability is the load-bearing half: a project whose
        YAML changed byte for byte on every save would make version control
        useless for the one file a user most wants a history of.
        """
        return yaml.safe_dump(
            self.model_dump(mode="json"),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )

    @classmethod
    def from_yaml(cls, text: str) -> Self:
        """Parse YAML text written by `to_yaml`.

        Raises:
            ValidationError: if the document is structurally invalid.
        """
        return cls.model_validate(yaml.safe_load(text))

    def save(self, path: Path) -> None:
        """Write to `path` as-is.

        Deliberately does not rebase `source`: it cannot, because a relative
        path does not carry the directory it was relative *to*, so a `save` that
        silently reinterpreted one would corrupt exactly the projects it was
        meant to help. Saving somewhere new goes through `relocated`.
        """
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Self:
        """Read the project at `path`.

        Paths in the result stay relative — resolve them against `path.parent`,
        which `source_path` does for you.
        """
        return cls.from_yaml(path.read_text(encoding="utf-8"))

    # ---- convenience -----------------------------------------------------

    @classmethod
    def for_video(cls, video: Path, project_dir: Path | None = None) -> Self:
        """An empty project for `video`, by default anchored beside it."""
        directory = project_dir if project_dir is not None else video.parent
        return cls(source=SourceRef.relative_to(video, directory))

    def relocated(self, from_dir: Path, to_dir: Path) -> Self:
        """Copy with every stored path re-expressed relative to `to_dir`.

        Both directories are arguments because rebasing genuinely needs both:
        the stored paths are meaningless without the directory they were
        written against.
        """

        def rebase(sink: Sink) -> Sink:
            return sink.model_copy(update={"path": _posix_relative(sink.resolve(from_dir), to_dir)})

        return self.model_copy(
            update={
                "source": SourceRef.relative_to(self.source.resolve(from_dir), to_dir),
                "outputs": tuple(rebase(sink) for sink in self.outputs),
            }
        )

    def source_path(self, project_path: Path) -> Path:
        """The video, resolved against the project file it was read from."""
        return self.source.resolve(project_path.parent)

    def with_replicates(self, replicates: tuple[Replicate, ...]) -> Self:
        """Copy carrying a different set of replicates, in order."""
        return self.model_copy(update={"replicates": replicates})

    def with_pipeline(self, pipeline: Pipeline) -> Self:
        """Copy carrying a different graph.

        Validated rather than assigned: `checkpoints` and `outputs` name nodes,
        and replacing the graph is precisely when those names go stale.
        """
        return self.model_validate(self.model_copy(update={"pipeline": pipeline}))

    def with_clip(self, clip: ClipRange | None) -> Self:
        """Copy carrying a different representative clip."""
        return self.model_copy(update={"clip": clip})

    # ---- per-replicate deviation -----------------------------------------

    def replicate(self, replicate_id: str) -> Replicate:
        """The replicate carrying `replicate_id`.

        Raises:
            KeyError: if no replicate carries it.
        """
        for candidate in self.replicates:
            if candidate.replicate_id == replicate_id:
                return candidate
        raise KeyError(replicate_id)

    def params_for(self, node_id: str, replicate_id: str | None = None) -> dict[str, Any]:
        """What `node_id` runs with for this replicate, by id.

        A lookup around `resolved_params`, not a second answer: it exists so a
        caller holding two ids does not have to fetch two objects and is
        therefore never tempted to merge them itself.

        Raises:
            KeyError: if either id names nothing.
        """
        node = self.pipeline.node(node_id)
        return resolved_params(node, None if replicate_id is None else self.replicate(replicate_id))

    def with_param_edit(self, node_id: str, replicate_id: str, params: Mapping[str, Any]) -> Self:
        """Configure `node_id` for one replicate, and move the default with it.

        **Two writes, and the second is the whole mechanism.** The parameters
        that changed are pinned on `replicate_id`, *and* `node.params` is
        overwritten with everything submitted — so a replicate that has never
        been configured resolves to the most recently configured values and the
        next arena the user clicks into opens showing the last one's settings.
        Twelve arenas are configured once unless one of them needs to differ.

        The cost is real and was accepted knowingly: editing replicate 2
        silently changes the ten replicates nobody was looking at. What it buys
        is that inheritance needs no record of what was clicked in what order.
        An un-overridden replicate resolves to a value stored in the document,
        so the artifact stays reproducible without a visit log and GUI
        interaction history stays out of it.

        Only the parameters that actually *changed* are pinned, against what
        this replicate resolved to before the edit. Submitting a value equal to
        the one on screen therefore pins nothing and leaves the replicate
        following the default — which is the same ambiguity `Replicate.overrides`
        documents, and the reason a form may submit its whole field set here
        without every edited replicate acquiring a full override.

        Args:
            node_id: The node being configured.
            replicate_id: The replicate the user was looking at.
            params: What the form holds. May be the node's whole parameter set
                or only the fields touched; both give the same result.

        Raises:
            KeyError: if either id names nothing.
        """
        node = self.pipeline.node(node_id)
        target = self.replicate(replicate_id)
        before = resolved_params(node, target)
        changed = {
            name: value
            for name, value in params.items()
            if name not in before or before[name] != value
        }
        edited = target.with_override(node_id, changed)
        updated_node = node.model_copy(update={"params": {**node.params, **params}})
        return self._replacing(node, updated_node, target, edited)

    def with_param_reset(self, node_id: str, replicate_id: str) -> Self:
        """Drop one replicate's deviation at `node_id`, so it follows again.

        The way back from a pin, and it moves nothing else — resetting is not
        an edit, so the default stays where the last real edit left it.

        Raises:
            KeyError: if either id names nothing.
        """
        node = self.pipeline.node(node_id)
        target = self.replicate(replicate_id)
        return self._replacing(node, node, target, target.without_override(node_id))

    def _replacing(
        self, node: Node, new_node: Node, replicate: Replicate, new_replicate: Replicate
    ) -> Self:
        """Copy with one node and one replicate substituted in place.

        Positional substitution because both collections are ordered and the
        order is meaningful — replicate order is the order outputs are written
        in, so rebuilding either by filtering and appending would reorder the
        run.
        """
        return self.model_copy(
            update={
                "pipeline": self.pipeline.model_copy(
                    update={
                        "nodes": tuple(
                            new_node if candidate is node else candidate
                            for candidate in self.pipeline.nodes
                        )
                    }
                ),
                "replicates": tuple(
                    new_replicate if candidate is replicate else candidate
                    for candidate in self.replicates
                ),
            }
        )
