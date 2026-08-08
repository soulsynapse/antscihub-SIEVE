"""Schema v1: the saved document a run is reproducible from.

Given this document and the source video it names, any executor — CLI, GUI, or
a batch job on a cluster — performs the same run and writes the same files.
That is the whole contract, and it is why nothing here may depend on anything
that exists in only one of those three: no widget geometry, no zoom, no scrub
position, no cache directory, no thread count. `extra="forbid"` throughout is
the machine-checked form of it — stashing front-end state in the artifact
requires editing this file, which is the review the rule exists to force.

**Everything a pipeline does is a node.** There is no `Project` field for the
cut, the tuning span, or the detector: cropping is the `crop` tool, the
representative stretch is the `span` tool, and detection is a node whose settings
are that node's params (`adr/detector-is-a-node.md`). v2 grew a bespoke field
for each thing that could not be a graph step and bespoke carry logic behind
each one; a replicate's geometry is now a per-replicate override on the crop
node's region parameter, which is the ordinary mechanism rather than a second
one.

**Deliberately not registry-aware.** Nothing here asks whether a tool named by
a node exists, what parameters it takes, or whether an edge's types chain.
Those are `pipeline/dag.py`'s job, against the registry. The split is what lets
a project open on a machine where a tool is missing: the user gets "no tool
`wavelet_bands` at version 2.1.0", which names the thing to install, rather
than a parse error that names nothing. It is also what lets a front end draw a
graph it cannot execute. What *is* checked here is structural — ids unique,
edges pointing at nodes that exist, `tool_id`/`version` syntactically able to
enter a cache key, `node_id` able to be a file name. Cycle detection is not, because it needs a traversal, it is
the first thing `dag.py` does, and two implementations means two answers.

Registry-blindness is also why the crop record's `backs` takes a region rather
than a replicate: which node is the crop is a registry question, so a document
that answered it would have to know what a tool is.

**The identity line.** Everything on `Node` feeds the cache key and nothing
else here does, which is what governs what may be added to it: a field that
does not change a node's output does not belong on the node. `checkpoints`,
`outputs` and `crops` are therefore recorded on `Project`, keyed by node id —
each changes where a result lives and never what it is, and turning a
checkpoint off for a cluster with the memory to skip it must not move a single
key or the handoff stops being the same run. Keeping them off the node makes
that mistake unavailable rather than merely documented.

The line reads one clause longer under per-replicate deviation: `Node.params`
is the *default for replicates that have not been configured*, and what a key
is built from is `resolved_params`. Hashing `Node.params` on its own would
invalidate all twelve entries every time a thirteenth edit moved it, including
for replicates that pin every parameter and never read it.

**No measurements live here.** A timing is a fact about one machine, and this
is the one artifact two machines are required to agree about. What the document
owes `bench/` is addressability — `node_id` and `sink_id` are stable, so a run
report keys against them from outside — and that is all it owes.
"""

from __future__ import annotations

import os
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Self
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sieve.core.tool_base import SEMVER_PATTERN, TOOL_ID_PATTERN
from sieve.core.types import ROI

#: Bumped when a saved document stops being readable by this code unchanged. A
#: reader refuses a document from the future rather than guessing at it: the
#: failure mode of guessing is a run that completes and is wrong. v1 is the
#: floor — there is no earlier v3 document and no importer for a v2 one
#: (`adr/v2-does-not-import.md`), so nothing here migrates.
SCHEMA_VERSION = 1

#: Project files are named `<video stem>.sieve.yaml` and live *beside* the
#: video they describe: a source in a folder, its derivatives in child folders,
#: and the project file is what names those children. The practical consequence
#: is that copying the folder copies the project, which is how footage reaches
#: a cluster.
PROJECT_SUFFIX = ".sieve.yaml"

#: Sink formats and tool ids share a spelling rule for the same reason: both are
#: resolved by name at run time, and both appear in paths and CLI arguments
#: where case folding and shell quoting are not to be relied on.
_SINK_FORMAT_PATTERN = TOOL_ID_PATTERN

#: What a node id may be spelt as. Node ids reach the filesystem — a checkpoint
#: is `<node_id>.npy`, and a manifest and a crop artifact name them too — so an
#: id holding a separator aims a write outside the folder it was meant for, and
#: a hand-edited document is all it takes to write one. Refused here rather than
#: sanitized per consumer: two ids that sanitize alike are one file, and a
#: result silently overwriting another is the failure the reviewer-rerun promise
#: cannot survive. Looser than `TOOL_ID_PATTERN`, which a generated id would
#: fail — `uuid4().hex` may start with a digit.
NODE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def project_path_for(video: Path) -> Path:
    """Where the project file for `video` belongs.

    A convention, not a lookup: the file need not exist.
    """
    return video.parent / (video.stem + PROJECT_SUFFIX)


def as_project_path(path: Path) -> Path:
    """`path` renamed to end in `.sieve.yaml`, for a caller handed a typed name.

    `project_path_for` is a convention other code reads back, so a project saved
    as `arena.yaml` is a file nothing looks for. The double suffix is why
    `with_suffix` cannot do this: it would replace `.yaml` and leave
    `arena.sieve` behind.
    """
    if path.name.endswith(PROJECT_SUFFIX):
        return path
    return path.with_name(path.stem + PROJECT_SUFFIX)


def _new_id() -> str:
    return uuid4().hex


def _resolved(path: Path) -> Path:
    """Absolute, `..` collapsed, symlinks followed.

    `Path.resolve` rather than a lexical `normpath`: collapsing `a/link/..` to
    `a` is wrong whenever `link` is a symlink, and footage reached through a
    symlinked scratch mount is ordinary on the machines this runs on. The cost
    is a filesystem call, paid once when a project opens and in no latency
    budget.
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


class FrozenMapping(dict[str, Any]):
    """A mapping that refuses every write, and is still a `dict`.

    Being a `dict` subclass rather than a `MappingProxyType` is the whole
    design. A parameter value lives in an `Any`-typed field, so it passes
    through pydantic's fallback serializer, and that serializer refuses a
    `mappingproxy` outright — `model_dump(mode="json")` raises
    `PydanticSerializationError: Unable to serialize unknown type`, which would
    make the document unsavable rather than immutable. A `dict` subclass is
    serialized as the dict it is, compares equal to the plain mapping it was
    built from, and leaves `ser_json_inf_nan="constants"` reading the same
    values it read before.

    Copy and pickle go through `__setitem__` for a `dict` subclass, so both are
    answered here: the value is immutable, so a copy of it may be itself, and
    the cluster handoff that pickles a `Project` must not trip over its own
    parameters.
    """

    def _immutable(self, *_args: Any, **_kwargs: Any) -> Any:
        raise TypeError(f"{type(self).__name__} is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    __ior__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Self:
        return self

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), (dict(self),))


class FrozenSequence(list[Any]):
    """`FrozenMapping`'s counterpart for a parameter that is a list.

    A `list` subclass for `FrozenMapping`'s reasons, and not a tuple for one
    more: a tuple round-trips through YAML as a list, so freezing to tuples
    would make a document unequal to itself across a save purely by type.
    """

    def _immutable(self, *_args: Any, **_kwargs: Any) -> Any:
        raise TypeError(f"{type(self).__name__} is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Self:
        return self

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), (list(self),))


def frozen_value(value: Any) -> Any:
    """`value` with every container inside it made unwritable.

    Applied where a parameter enters the document, so that the immutability
    `frozen=True` claims is a property of the stored value rather than of the
    discipline of each read. The alternative — deep-copying at every read path —
    leaves the guarantee one forgotten method away from being false, and pays a
    deep copy per `params_for` call, on the interactive path and again per node
    per replicate whenever a key is built.

    Scalars are returned as they are: what a document can hold is what YAML
    round-trips, and every leaf of that is already immutable.
    """
    if isinstance(value, Mapping):
        return FrozenMapping({key: frozen_value(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return FrozenSequence(frozen_value(item) for item in value)
    return value


class _Artifact(BaseModel):
    """Shared config for every model in the document.

    Frozen because a document that has been written to disk, hashed, or handed
    to an executor must not then change underneath it. Extra fields forbidden
    for the module docstring's reason.

    `frozen=True` on its own is one level deep — it stops a field being
    reassigned and says nothing about a dict nested inside one, and the crop
    node's region is exactly such a dict (`adr/detector-is-a-node.md`). The
    fields that can hold a container are therefore frozen through
    `frozen_value` as they are validated.

    `ser_json_inf_nan="constants"` is not a formatting preference. Pydantic
    leaves a non-finite float alone in a *typed* field under
    `model_dump(mode="json")` but nulls it in an `Any`-typed one, and both
    `Node.params` and `Replicate.overrides` are `Any` by necessity — a tool owns
    its parameter model, one layer up. Under the default, a band written
    `[51206.8, .inf]` on the baseline came back `[51206.8, null]` on the
    replicate that pinned it, and `null` is not a float on the way in.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", ser_json_inf_nan="constants")


class SourceRef(_Artifact):
    """The video a project is about, named relative to the project file.

    `path` is *not* resolved against the working directory — it means nothing
    without the directory holding the project file, which is why every reader
    goes through `resolve`. An absolute path would make a project unopenable the
    moment the folder moved.
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
        first caller comparing two resolved paths would be comparing spellings.
        """
        return _resolved(Path(project_dir, self.path))


class SourceSpan(_Artifact):
    """A half-open run of source frames, `[start, end)`.

    Frame indices, not timestamps: container timestamps drift, and a span that
    means a different stretch on reload is a span that invalidates whatever was
    done against it.

    The document carries one of these only as part of a crop record — which
    frames a written file covers. What the user tunes against is the `span`
    tool's parameters, in the graph like everything else.
    """

    start: int
    end: int

    @model_validator(mode="after")
    def _ordered_and_nonempty(self) -> Self:
        if self.start < 0:
            raise ValueError(f"span start must be non-negative, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"span must cover at least one frame, got [{self.start}, {self.end})")
        return self

    @property
    def frame_count(self) -> int:
        """Frames covered."""
        return self.end - self.start


class Replicate(_Artifact):
    """A named subdivision of the source, stable across renames and edits.

    One arena, one dish, one trial. `replicate_id` is what downstream artifacts
    reference, so identity is a generated id rather than the display name: a
    rename must not invalidate an entry keyed on it.

    Where the geometry went: a replicate's region is a per-replicate override of
    the crop node's region parameter, so this type carries no `ROI` of its own
    (`adr/detector-is-a-node.md`). One consequence is worth stating because
    nothing else states it — a replicate's box now enters the cache key through
    the ordinary params path, so two replicates at different positions are
    correctly two different runs rather than a special case the key had to be
    taught.
    """

    name: str
    replicate_id: str = Field(default_factory=_new_id)
    #: Per-node deviation, `{node_id: {param_name: value}}`, sparse in *both*
    #: levels. A node absent from the mapping runs the node's own parameters; a
    #: parameter absent from a node's entry is inherited even when a sibling
    #: parameter is pinned. That second level is what lets one arena hold its
    #: own threshold while still following every later edit to a blur radius
    #: nobody varied — and an override storing every parameter could not tell
    #: "the user set this to the value it already had" from "the user never
    #: touched it", so sparsity is a construction rule and not a storage
    #: optimization.
    overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def _unwritable(cls, value: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return frozen_value(value)

    def renamed(self, name: str) -> Self:
        """Copy carrying a new display name and the same identity."""
        return self.model_copy(update={"name": name})

    def override_for(self, node_id: str) -> dict[str, Any]:
        """This replicate's deviation at `node_id`, empty when it follows.

        The mapping handed back is a plain one the caller may build on, and
        every value in it is frozen, so a write through it lands nowhere rather
        than in a document that has already been hashed.
        """
        return dict(self.overrides.get(node_id, {}))

    def with_override(self, node_id: str, changes: Mapping[str, Any]) -> Self:
        """Copy whose deviation at `node_id` is merged with `changes`.

        Merged, not replaced, because an edit names only the parameters it
        touched. Replacing would silently un-pin every other parameter the
        replicate had been configured with.

        `model_copy` runs no validator, so the freeze is applied here: what
        `changes` carries is the caller's own mapping, and storing it as it
        stands would leave that caller holding a writable handle into a frozen
        model.
        """
        if not changes:
            return self
        merged = dict(self.overrides)
        merged[node_id] = {**merged.get(node_id, {}), **changes}
        return self.model_copy(update={"overrides": frozen_value(merged)})

    def without_override(self, node_id: str) -> Self:
        """Copy that follows `node_id`'s baseline again.

        The way back from a pin. Without it a parameter set once could only ever
        be re-pinned to a new value and never returned to inheriting.
        """
        if node_id not in self.overrides:
            return self
        kept = {key: value for key, value in self.overrides.items() if key != node_id}
        return self.model_copy(update={"overrides": FrozenMapping(kept)})

    def with_overrides_limited_to(self, node_ids: Collection[str]) -> Self:
        """Copy keeping only the deviations that still name a real node.

        The prune a structural edit performs: a pin on a node the graph lost is
        a parameter set nothing will ever read, and `Project` refuses to hold
        one. Returns `self` unchanged when nothing is stale, so an identity
        check can tell "pruned" from "already clean".
        """
        kept = {key: value for key, value in self.overrides.items() if key in node_ids}
        if kept == self.overrides:
            return self
        return self.model_copy(update={"overrides": FrozenMapping(kept)})


class Node(_Artifact):
    """One tool application, named but not resolved.

    Every field here enters the cache key, with the module docstring's one
    qualification: `params` enters it only after `resolved_params` has been
    applied, because a replicate may deviate from it.

    `params` is an opaque mapping, not a parsed `ParamsBase`. The tool's
    parameter model is the only thing that knows what shape it should be, and it
    lives in `sieve.tools`, above this layer — validating here would either
    invert the layer stack or keep a second copy of the field list.
    """

    #: Stable across reorderings and parameter edits, because edges,
    #: checkpoints, sinks and overrides all reference it. Generated rather than
    #: derived from the tool id: two `downsample` nodes in one graph is
    #: ordinary. Spelt within `NODE_ID_PATTERN`, which is also the rule for what
    #: a user may type where an id is typed — `Node` carries no display name, so
    #: until a surface wants one there is nothing else for a rename to write on.
    node_id: str = Field(default_factory=_new_id)
    tool_id: str
    version: str
    #: Not "the parameters" — "the default for replicates that have not been
    #: configured". See the module docstring's identity line.
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def _unwritable(cls, value: dict[str, Any]) -> dict[str, Any]:
        return frozen_value(value)

    @field_validator("node_id")
    @classmethod
    def _known_shape_node_id(cls, value: str) -> str:
        if not NODE_ID_PATTERN.match(value):
            raise ValueError(
                f"node_id must match {NODE_ID_PATTERN.pattern!r}, got {value!r} — it becomes a "
                "file name, so it may not depend on case folding or shell quoting to stay itself"
            )
        return value

    @field_validator("tool_id")
    @classmethod
    def _known_shape_id(cls, value: str) -> str:
        if not TOOL_ID_PATTERN.match(value):
            raise ValueError(f"tool_id must match {TOOL_ID_PATTERN.pattern!r}, got {value!r}")
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
    hashes this, the executor configures kernels from it, and a front end shows
    it. A second implementation anywhere is how a preview and a batch run stop
    agreeing about what they computed, and the disagreement would be invisible,
    because both would report success against caches keyed on their own answer.

    A key-wise merge, deliberately: the override supplies only what is pinned on
    this replicate and everything else follows `node.params` as it moves.

    `replicate=None` is the node's baseline — what a graph inspected outside any
    fan-out shows, and what a project with no replicates runs.

    The mapping returned is a fresh outer dict of frozen values, so a caller may
    build the next edit on top of what it read and still cannot write through it
    into a document that has been hashed.
    """
    if replicate is None:
        return dict(node.params)
    return {**node.params, **replicate.overrides.get(node.node_id, {})}


def edited_params(
    node: Node, replicate: Replicate, params: Mapping[str, Any]
) -> tuple[Node, Replicate]:
    """One parameter edit's two writes: the pin, and the moved default.

    The mechanism `Project.with_param_edit` documents, extracted so a caller
    holding the pieces rather than a `Project` performs the identical edit
    rather than a paraphrase of it. Only the parameters that actually changed
    against what `replicate` resolved to are pinned; everything submitted moves
    the baseline.

    A caller should submit only the fields the user touched. Submitting a
    deviated replicate's *whole* resolved view would drag its previously pinned
    values into the baseline and change every following replicate for fields
    nobody edited.
    """
    before = resolved_params(node, replicate)
    changed = {
        name: value for name, value in params.items() if name not in before or before[name] != value
    }
    updated = node.model_copy(update={"params": frozen_value({**node.params, **params})})
    return updated, replicate.with_override(node.node_id, changed)


class Edge(_Artifact):
    """`upstream`'s output feeds `downstream`'s input.

    One input stream per node, so an edge names no port. v2 grew ports for a
    merging step it never built; the protocol is cut from the tool contract
    (`core/tool_base.py`) and the day a two-input tool lands is the day this
    document has to learn which input an edge feeds. Adding the field before
    then would be a schema carrying a distinction nothing can make.
    """

    upstream: str
    downstream: str

    @model_validator(mode="after")
    def _not_a_self_loop(self) -> Self:
        if self.upstream == self.downstream:
            raise ValueError(f"edge from {self.upstream} to itself")
        return self


class Sink(_Artifact):
    """A declared output: which node's result is written, where, and how.

    Sinks are what make the document a runnable thing rather than a description
    of one — a graph with no sinks computes nothing anyone can look at. They
    live on `Project` rather than on `Node` because an output location is not
    part of a node's identity: two projects writing the same computation to
    different folders must share cache entries.

    `path` names a *directory* relative to the project file, because a sink
    under replicate fan-out produces one output per replicate.
    """

    #: Addressable so a handoff can toggle one output without rewriting the list
    #: positionally.
    sink_id: str = Field(default_factory=_new_id)
    #: The node whose output is written. Checked against the graph by `Project`.
    node_id: str
    #: Resolved by whatever writes it, exactly as `tool_id` is resolved by the
    #: registry. Not an enum: the writer set is open, and an enum in `core/`
    #: would be the manual wiring a tool never needs, reintroduced one layer
    #: down.
    format: str
    path: str
    #: Writer options — codec, frame rate, column selection. Opaque here for
    #: `Node.params`' reason.
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def _unwritable(cls, value: dict[str, Any]) -> dict[str, Any]:
        return frozen_value(value)

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


#: Which decode format a written crop holds, spelt as a source key spells it.
#: Not a `bool`, because both names appear in file names and in a cache key's
#: payload, and `luma=False` is not a thing anyone can read off a directory
#: listing. Two artifacts, never one that serves both: a luma read of a
#: colour-coded file is the wrong-pixels trap v2's codec finding measured.
CropFormat = Literal["luma", "bgr"]


class CropRecord(_Artifact):
    """One region's crop, written to a file that is then a source in itself.

    **The file is a child source with its own identity, not the parent's.** A
    run against it roots off that file's own identity, exactly as it would for
    any video a user opened, so `plan`, `executor` and `cache_key` need no
    notion that it was cut from anything. What it costs is that descending onto
    the file re-keys: downstream entries from source-side tuning are recomputed
    once, and two replicates with identical regions stop sharing entries once
    each is backed by its own file.

    Every field here is *location* — where a file lives and what it was cut
    from. The identity that enters a key is computed from the file itself at run
    time, so a record cannot make a stale file look fresh: a replaced or
    truncated file changes what that identity returns by construction.

    `cut_from` and `decoder` are both provenance and differ in what they are
    used for. `cut_from` is *matched* (see `backs`) — a re-exported source must
    not silently keep serving crops of the old one. `decoder` is deliberately
    **not** matched: the file is expected to outlive decoder upgrades, and
    refusing it after one would throw away pixels that are on disk and correct
    in favour of a re-cut.
    """

    #: POSIX, relative to the project file's directory — `Sink.path`'s rule for
    #: `Sink.path`'s reason.
    path: str
    #: The geometry it was cut at, in source pixels: the region as *recorded*,
    #: not the frame-clamped one the writer applied. Clamping is a function of
    #: the decoded frame and the executor applies the identical clamp, so
    #: storing the clamped result would make a region overhanging the frame edge
    #: never match its own file.
    region: ROI
    format: CropFormat
    #: Source frames covered. File frame 0 is source frame `span.start`; nothing
    #: else translates between the two index spaces.
    span: SourceSpan
    #: The parent source's identity at write time.
    cut_from: str
    #: The decoder's identity at write time. Provenance only — see the
    #: docstring.
    decoder: str

    @field_validator("path", "cut_from", "decoder")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("crop record fields must not be empty")
        return value

    @property
    def luma(self) -> bool:
        """Whether this file holds the luma plane rather than colour."""
        return self.format == "luma"

    def resolve(self, project_dir: Path) -> Path:
        """The written file, given where the project file was read from."""
        return _resolved(Path(project_dir, self.path))

    def identity(self) -> tuple[str, ROI, CropFormat, SourceSpan]:
        """What makes two records the same record.

        Not the path: writing the same cut twice to two names is one cut
        recorded twice, and the second write should replace the first rather
        than accumulate beside it.
        """
        return (self.cut_from, self.region, self.format, self.span)

    def backs(self, region: ROI, *, source: str, luma: bool, project_dir: Path) -> bool:
        """Whether this record can serve a run over `region` right now.

        **The matching rule, stated once here and read by whatever serves it.**
        The parent must still be the footage this was cut from, the box must
        still be where it was when the cut was made, the session must want the
        format that was written, and the file must be there. Each fails in the
        direction that recomputes rather than the direction that serves the
        wrong pixels, so a moved box or a re-exported source misses by
        construction — and by geometry and parentage rather than by name, which
        is what lets a record survive a rename.

        A region rather than a replicate, because which node holds it is a
        registry question and this layer does not ask them.

        The span is deliberately absent from the test. A record whose span no
        longer covers what is being asked for serves *part* of the request, and
        deciding what to do about a partial cover belongs to the caller that
        knows which frames it wants, not to a predicate that can only answer yes
        or no.
        """
        return (
            self.cut_from == source
            and self.region == region
            and self.luma == luma
            and self.resolve(project_dir).is_file()
        )


class Pipeline(_Artifact):
    """The graph itself: no source video, no replicates, no output locations.

    Separate from `Project` because that is the boundary `dag.py` works at.
    Validating that a graph chains does not need to know what footage it runs
    on, and keeping the two apart is what stops a validator quietly growing a
    dependency on a decoded frame.
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
        # One producer per node, which subsumes a duplicate-edge check: two
        # identical edges collide here too. Whatever the tool turns out to be,
        # its one input carries one stream — that is true of every tool that
        # will ever be installed, so it is structural rather than dag.py's
        # question.
        fed: set[str] = set()
        for edge in self.edges:
            if edge.downstream in fed:
                raise ValueError(f"two edges feed {edge.downstream!r}")
            fed.add(edge.downstream)
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
    """A source video, what runs on it, and what comes out.

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
    pipeline: Pipeline = Pipeline()
    #: Node ids whose output is written to the project folder. A run without
    #: them produces identical results and merely recomputes more, which is why
    #: they are recorded here and never hashed.
    checkpoints: tuple[str, ...] = ()
    outputs: tuple[Sink, ...] = ()
    #: Crops written to disk, each a source in its own right. Here rather than
    #: on `Replicate` for `checkpoints`' reason, and it is the same test: a
    #: written crop is a faster route to pixels the graph would have computed
    #: anyway, so it changes where a result lives and never what it is. A record
    #: naming a replicate is deliberately not how they are associated either —
    #: `CropRecord.backs` matches on geometry and parentage.
    crops: tuple[CropRecord, ...] = ()

    @field_validator("schema_version")
    @classmethod
    def _readable(cls, value: int) -> int:
        """Refuse a document from the future; restamp everything else as ours.

        The restamp keeps the check honest over a project's life: a front end
        saves by copying the `Project` it opened, so without it the stamp of the
        oldest file in the history is carried forever. A document this build
        accepted *is* a document in this build's schema.
        """
        if value > SCHEMA_VERSION:
            raise ValueError(
                f"project uses schema version {value}; this build reads up to {SCHEMA_VERSION}"
            )
        return SCHEMA_VERSION

    @model_validator(mode="after")
    def _references_resolve(self) -> Self:
        ids = [replicate.replicate_id for replicate in self.replicates]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate replicate_id")
        for replicate in self.replicates:
            for node_id in replicate.overrides:
                # A deviation on a deleted node is a parameter set nothing will
                # ever read, and it would survive every save until a new node
                # happened to be given the id.
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
        # Two records for one cut are two files claiming to be the same thing,
        # and nothing downstream could choose between them — `backs` would
        # answer yes for both. Refused rather than deduplicated silently,
        # because the way to get one is to hand-edit the document.
        cuts = [record.identity() for record in self.crops]
        if len(set(cuts)) != len(cuts):
            raise ValueError("two crop records describe the same cut")
        return self

    # ---- serialization ---------------------------------------------------

    def to_yaml(self) -> str:
        """The document as YAML text.

        `sort_keys=False` keeps declaration order, which is both readable and
        stable. Stability is the load-bearing half: a project whose YAML changed
        byte for byte on every save would make version control useless for the
        one file a user most wants a history of.
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
        the stored paths are meaningless without the directory they were written
        against.
        """

        def rebase_sink(sink: Sink) -> Sink:
            return sink.model_copy(update={"path": _posix_relative(sink.resolve(from_dir), to_dir)})

        def rebase_crop(record: CropRecord) -> CropRecord:
            return record.model_copy(
                update={"path": _posix_relative(record.resolve(from_dir), to_dir)}
            )

        return self.model_copy(
            update={
                "source": SourceRef.relative_to(self.source.resolve(from_dir), to_dir),
                "outputs": tuple(rebase_sink(sink) for sink in self.outputs),
                "crops": tuple(rebase_crop(record) for record in self.crops),
            }
        )

    def source_path(self, project_path: Path) -> Path:
        """The video, resolved against the project file it was read from."""
        return self.source.resolve(project_path.parent)

    def with_replicates(self, replicates: Sequence[Replicate]) -> Self:
        """Copy carrying a different set of replicates, in order."""
        return self.model_validate(self.model_copy(update={"replicates": tuple(replicates)}))

    def with_pipeline(self, pipeline: Pipeline) -> Self:
        """Copy carrying a different graph.

        Validated rather than assigned: `checkpoints`, `outputs` and every
        replicate's overrides name nodes, and replacing the graph is precisely
        when those names go stale.
        """
        return self.model_validate(self.model_copy(update={"pipeline": pipeline}))

    def with_crop(self, record: CropRecord) -> Self:
        """Copy that records `record`, replacing any earlier record of that cut.

        Replacement rather than append, keyed on `CropRecord.identity`: a second
        write of the same cut is the same file written again — after a deletion,
        or a part file left by a crash — and appending would produce the pair the
        document refuses. The replacement holds the original's position, so
        re-cutting one region does not reorder the list.
        """
        existing = [candidate.identity() for candidate in self.crops]
        if record.identity() in existing:
            index = existing.index(record.identity())
            crops = (*self.crops[:index], record, *self.crops[index + 1 :])
        else:
            crops = (*self.crops, record)
        return self.model_copy(update={"crops": crops})

    def with_crops(self, crops: Iterable[CropRecord]) -> Self:
        """Copy whose crop records are exactly these, in this order.

        `with_crop`'s wholesale twin, for a caller holding the whole set rather
        than one new record. Validated rather than assigned, because "two
        records for one cut" is refused in the model and a caller assembling a
        tuple can produce one where `with_crop` cannot.
        """
        return self.model_validate(self.model_copy(update={"crops": tuple(crops)}))

    def without_crop(self, record: CropRecord) -> Self:
        """Copy with any record of `record`'s cut dropped.

        Keyed on `CropRecord.identity` for `with_crop`'s reason: what is being
        discarded is a *cut*, and the path it happens to be recorded under is
        convenience. The file itself is not touched here — deleting it is the
        caller's separate act.
        """
        wanted = record.identity()
        return self.model_copy(
            update={
                "crops": tuple(
                    candidate for candidate in self.crops if candidate.identity() != wanted
                )
            }
        )

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
        been configured resolves to the most recently configured values, and the
        next region the user opens shows the last one's settings. Twelve arenas
        are configured once unless one of them needs to differ.

        The cost is real and was accepted knowingly: editing replicate 2
        silently changes the ten replicates nobody was looking at. What it buys
        is that inheritance needs no record of what was clicked in what order —
        an un-overridden replicate resolves to a value stored in the document,
        so the artifact stays reproducible without a visit log.

        Only the parameters that actually *changed* are pinned, against what
        this replicate resolved to before the edit, which is why a form may
        submit its whole field set here without every edited replicate acquiring
        a full override.

        Raises:
            KeyError: if either id names nothing.
        """
        node = self.pipeline.node(node_id)
        target = self.replicate(replicate_id)
        updated_node, edited = edited_params(node, target, params)
        return self._replacing(node, updated_node, target, edited)

    def with_param_reset(self, node_id: str, replicate_id: str) -> Self:
        """Drop one replicate's deviation at `node_id`, so it follows again.

        The way back from a pin, and it moves nothing else — resetting is not an
        edit, so the default stays where the last real edit left it.

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
        in, so rebuilding either by selection and append would reorder the run.
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
