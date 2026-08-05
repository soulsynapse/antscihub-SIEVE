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

import json
import math
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Self
from uuid import uuid4

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from sieve.core.filter_base import (
    DEFAULT_PORT,
    FILTER_ID_PATTERN,
    PORT_PATTERN,
    SEMVER_PATTERN,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

#: Bumped when a saved document stops being readable by this code unchanged. A
#: reader refuses a document from the future rather than guessing at it: the
#: failure mode of guessing is a run that completes and is wrong.
#:
#: 2: `Edge` gained `port` (2026-07-26, multi-upstream kernels). A version-1
#: document loads unchanged — the field defaults to `DEFAULT_PORT`, which is
#: exactly what every edge meant before ports existed — but every save now
#: writes `port` on every edge, and a version-1 build's `extra="forbid"` would
#: report that as a stray field. The bump turns that parse error into the
#: message this constant exists to give.
#:
#: 3: `Project` gained `detector` and `Replicate` gained `detector_overrides`
#: (2026-07-27, replicates remember their settings). A version-2 document
#: loads unchanged — no detector was ever tuned, which is exactly what the
#: defaults say — but every save now writes both fields, and a version-2
#: build would report them as stray for the same reason as above.
#:
#: 4: `Project` gained `visited` (2026-07-28, the geometry lock). A version-3
#: document loads unchanged — no replicate had ever been recorded as opened in
#: the filter tab, which is what the empty default says, and the consequence is
#: that a project written before this build comes back with every replicate
#: unlocked until it is looked at again. Every save now writes the field, and a
#: version-3 build would report it as stray for the same reason as above.
#:
#: 5: `Project` gained `crops` (2026-07-28, the replicate crop artifact). A
#: version-4 document loads unchanged — nothing had ever been written at rest,
#: which is what the empty default says — but every save now writes the field,
#: and a version-4 build would report it as stray for the same reason as above.
SCHEMA_VERSION = 5

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


def as_project_path(path: Path) -> Path:
    """`path` renamed to end in `.sieve.yaml`, for a caller handed a typed name.

    `project_path_for` is a convention other code reads back — `history_directory`
    appends to it, the snapshot filename grammar parses it, and a video's project
    is found beside it — so a project saved as `arena.yaml` is a file nothing
    looks for. Coercing is what makes a name a user typed obey the convention.

    The double suffix is why `with_suffix` cannot do this: it would replace
    `.yaml`, leaving `arena.sieve` behind.
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

    `ser_json_inf_nan="constants"` is not a formatting preference. Pydantic
    leaves a non-finite float alone in a *typed* field under
    `model_dump(mode="json")` but nulls it in an `Any`-typed one, and the
    per-replicate pins (`Replicate.overrides`, `Replicate.detector_overrides`)
    are `Any` by necessity — a filter owns its parameter model, and the
    detector's fields are validated one layer up. Under the default the two
    halves of one band disagreed: `value_band: [51206.8, .inf]` on the
    baseline, `[51206.8, null]` on the arena that pinned it, and `null` is not
    a float on the way back in. YAML can write an infinity; this makes the
    serializer hand it one to write.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", ser_json_inf_nan="constants")


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


class DetectorSettings(_Artifact):
    """The detection suffix's tuned values: bands, count threshold, window D.

    The temporal filter and detection steps are not pipeline nodes — they are
    derivation over the extracted series (`gui/chain_model.py` holds the live
    twin of this model) — so their tuning cannot ride `Node.params` and needs
    its own home in the artifact. It gets one because these values decide what
    is *claimed as an event*: two machines agreeing about the graph but not
    the thresholds are not agreeing about the run.

    This is `Node.params`' analog, not a GUI snapshot: it is the *default for
    replicates that have not been configured*, it moves on every edit (see
    `edited_detector`), and a replicate deviates from it field by field
    through `Replicate.detector_overrides`. What is deliberately absent is
    anything about *looking* — the soloed block, the playhead — for the module
    docstring's reason.

    Bands are stored in the units the plots drag them in, edges permitted
    infinite (YAML `.inf`), and the count threshold is a fraction of the
    region's blocks or None for disarmed — None is "nothing is claimed", not
    "everything passes", and it must survive a save as itself.
    """

    #: Frequency band in Hz over the Morlet bank; handles clamp to the bank.
    freq_band: tuple[float, float] = (0.0, math.inf)
    #: Value band over band power, in the extracted signal's own units.
    value_band: tuple[float, float] = (-math.inf, math.inf)
    #: Count threshold as fractions of region blocks, or None = disarmed.
    count_frac: tuple[float, float] | None = None
    #: Detection window D, in frames.
    window_frames: int = 30
    centered: bool = True

    @model_validator(mode="after")
    def _bands_ordered(self) -> Self:
        for name in ("freq_band", "value_band", "count_frac"):
            band: tuple[float, float] | None = getattr(self, name)
            if band is not None and band[0] > band[1]:
                raise ValueError(f"{name} must be ordered, got {band}")
        if self.freq_band[0] < 0:
            raise ValueError(f"freq_band must be non-negative, got {self.freq_band}")
        if self.window_frames < 1:
            raise ValueError(f"window_frames must be at least 1, got {self.window_frames}")
        return self

    @classmethod
    def default_for(cls, fps: float) -> Self:
        """The untuned state: wide-open bands, disarmed, D of one second.

        The one field a default cannot be written down for without the frame
        rate is D — "one second" is a frame count only once a source says how
        long a second is — which is why this exists as a constructor rather
        than as field defaults alone.
        """
        return cls(window_frames=max(1, round(fps)) if fps > 0 else 30)


def resolved_detector(
    settings: DetectorSettings, replicate: Replicate | None = None
) -> DetectorSettings:
    """The detector values `replicate` actually runs with.

    `resolved_params`' twin, and the only definition of "effective detector"
    for the same reason: the GUI shows this, a headless run will gate on this,
    and a second merge anywhere is how the two stop agreeing.

    Validated rather than merely merged, because the pins are an opaque
    mapping from a file: a pin naming a real field but carrying nonsense (a
    reversed band, a zero window) must fail here, at the one place every
    reader passes through, not wherever the value is first used.

    Raises:
        ValidationError: if a pinned value does not fit its field.
    """
    if replicate is None or not replicate.detector_overrides:
        return settings
    return DetectorSettings.model_validate(
        {**settings.model_dump(), **replicate.detector_overrides}
    )


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


def edited_params(
    node: Node, replicate: Replicate, params: Mapping[str, Any]
) -> tuple[Node, Replicate]:
    """One parameter edit's two writes: the pin, and the moved default.

    The mechanism `Project.with_param_edit` documents, extracted so a caller
    holding the pieces rather than a `Project` — the GUI document — performs
    the identical edit rather than a paraphrase of it. Only the parameters
    that actually changed against what `replicate` resolved to are pinned;
    everything submitted moves the baseline.

    A caller should submit only the fields the user touched. Submitting a
    deviated replicate's *whole* resolved view would drag its previously
    pinned values into the baseline and change every following replicate for
    fields nobody edited.
    """
    before = resolved_params(node, replicate)
    changed = {
        name: value for name, value in params.items() if name not in before or before[name] != value
    }
    updated = node.model_copy(update={"params": {**node.params, **params}})
    return updated, replicate.with_override(node.node_id, changed)


def edited_detector(
    settings: DetectorSettings, replicate: Replicate, changes: Mapping[str, Any]
) -> tuple[DetectorSettings, Replicate]:
    """`edited_params` for the detector: pin the diff, move the baseline.

    Same two writes, same sparsity rule, same caveat about submitting only
    what was touched. The moved baseline is validated as a whole, so an edit
    that would leave it inconsistent fails before either write lands.

    Raises:
        ValidationError: if `changes` names no such field or misfits one.
    """
    moved = DetectorSettings.model_validate({**settings.model_dump(), **changes})
    before = resolved_detector(settings, replicate)
    changed = {name: value for name, value in changes.items() if getattr(before, name) != value}
    return moved, replicate.with_detector_pins(changed)


class Edge(_Artifact):
    """`upstream`'s output feeds one of `downstream`'s input ports.

    `port` names which one, in the downstream filter's own vocabulary — a
    merging filter declares its ports on `FilterSpec.accepts`, and whether this
    name is one of them is `dag.py`'s check, for the module docstring's reason:
    this document must stay readable where the filter is not installed. What
    *is* checked here is spelling, and structurally on `Pipeline`, that no two
    edges feed one port.

    The default is what makes schema version 1 documents load unchanged: every
    edge written before ports existed fed the one input a single-input filter
    has, and `DEFAULT_PORT` is that input's name.
    """

    upstream: str
    downstream: str
    port: str = DEFAULT_PORT

    @field_validator("port")
    @classmethod
    def _known_shape_port(cls, value: str) -> str:
        if not PORT_PATTERN.match(value):
            raise ValueError(f"port must match {PORT_PATTERN.pattern!r}, got {value!r}")
        return value

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


#: Which decode format an artifact holds, spelt as `source_key` spells it. Not a
#: `bool`, because the two names appear in file names and in a cache key's
#: payload, and `luma=False` is not a thing anyone can read off a directory
#: listing. Two artifacts, never one that serves both: a luma read of a
#: colour-coded file is the wrong-pixels trap the codec finding measured.
CropFormat = Literal["luma", "bgr"]


class CropArtifact(_Artifact):
    """One replicate's crop, written to a file that is then a source in itself.

    **The artifact is a child source with its own identity, not the parent's.**
    A run against it roots off `source_identity(<the artifact file>)` with
    `roi=None`, exactly as it would for any video a user opened — so `plan`,
    `executor`, and `cache_key` need no notion that this file was cut from
    anything, and no decoder upgrade can orphan a file at rest by breaking a
    byte-parity claim nobody depends on. What it costs is that descending onto
    the artifact re-keys: downstream entries from source-side tuning are
    recomputed once, and two replicates with identical ROIs stop sharing
    entries once each is backed by its own file. Both were accepted knowingly
    (2026-07-28); `docs/todo/crop-artifact-writer.md` holds the reversal this
    revised, and `docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md` the
    measurements.

    Rule 7 therefore stays clean, and it is worth being precise about which
    side each field falls on: every field here is *location* — where an
    artifact lives and what it was cut from. The identity that enters a key is
    computed from the file itself at run time. A record cannot make a stale
    file look fresh, because nothing here is trusted for identity: a replaced
    or truncated file changes what `source_identity` returns by construction.

    `cut_from` and `decoder` are provenance, and they differ in what they are
    used for. `cut_from` is *matched* (see `backs`) — a re-exported source must
    not silently keep serving crops of the old one. `decoder` is deliberately
    **not** matched: the artifact is expected to outlive decoder upgrades, and
    refusing it after one would throw away a file whose pixels are on disk and
    correct in favour of a 46-second re-cut.
    """

    #: POSIX, relative to the project file's directory — `Sink.path`'s rule,
    #: for `Sink.path`'s reason: an absolute path makes the project unopenable
    #: the moment the folder moves, and the folder moving is how footage
    #: reaches a cluster.
    path: str
    #: The geometry it was cut at, in source pixels. The *replicate's* ROI as
    #: recorded, not the frame-clamped one the writer applied: clamping is a
    #: function of the decoded frame and the executor applies the identical
    #: `ROI.clamped_to(...).crop(...)`, so storing the clamped result would
    #: make a replicate whose box overhangs the frame edge never match its own
    #: artifact.
    roi: ROI
    format: CropFormat
    #: Source frames `[start, end)` covered. Artifact frame 0 is source frame
    #: `span.start`; nothing else translates between the two index spaces.
    span: ClipRange
    #: The parent's `source_identity` at write time.
    cut_from: str
    #: `decoder_identity()` at write time. Provenance only — see the docstring.
    decoder: str

    @field_validator("path", "cut_from", "decoder")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("crop artifact fields must not be empty")
        return value

    @property
    def luma(self) -> bool:
        """Whether this artifact holds the luma plane rather than colour."""
        return self.format == "luma"

    def resolve(self, project_dir: Path) -> Path:
        """The artifact file, given where the project file was read from."""
        return _resolved(Path(project_dir, self.path))

    def identity(self) -> tuple[str, ROI, CropFormat, ClipRange]:
        """What makes two records the same record.

        Not the path: writing the same cut twice to two names is one artifact
        recorded twice, and the second write is the one that should replace the
        first rather than accumulate beside it.
        """
        return (self.cut_from, self.roi, self.format, self.span)

    def backs(self, replicate: Replicate, *, source: str, luma: bool, project_dir: Path) -> bool:
        """Whether this record can serve `replicate` right now.

        **The matching rule, stated once here and read by whatever serves it.**
        Three conditions, and each fails in the direction that recomputes
        rather than the direction that serves the wrong pixels: the parent must
        still be the footage this was cut from (`cut_from`), the box must still
        be where it was when the cut was made (`roi`), the session must want
        the format that was written (`format`), and the file must be there. A
        moved ROI or a re-exported source misses by construction.

        The span is deliberately absent from the test. A record whose span no
        longer covers what is being asked for is a record that serves part of
        the request, and deciding what to do about a partial cover belongs to
        the caller that knows which frames it wants — not to a predicate that
        can only answer yes or no.
        """
        return (
            self.cut_from == source
            and self.roi == replicate.roi
            and self.luma == luma
            and self.resolve(project_dir).is_file()
        )


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
        # One producer per port, and it subsumes the old duplicate-edge check:
        # two identical edges collide here too. Feeding one downstream twice on
        # *different* ports stays legal — a stream compared against itself is a
        # graph someone will legitimately draw. Whether the port exists on the
        # filter is dag.py's question; that two streams cannot share one input
        # is true of every filter that will ever be installed.
        fed: set[tuple[str, str]] = set()
        for edge in self.edges:
            target = (edge.downstream, edge.port)
            if target in fed:
                raise ValueError(f"two edges feed {edge.downstream!r} on port {edge.port!r}")
            fed.add(target)
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


def _params_fingerprint(
    nodes: Sequence[Node],
    replicate: Replicate | None,
    detector: DetectorSettings | None,
) -> str:
    """Canonical text standing for everything `replicate` runs the graph with.

    Two replicates are in the same equivalence group exactly when this string
    matches, so it is a key rather than a digest — the string *is* what gets
    compared, and there is no collision to reason about. Canonical in the same
    sense `cache_key.py` will use: JSON with sorted keys, so `{"a": 1, "b": 2}`
    and `{"b": 2, "a": 1}` are one value and not two groups.

    Not `hash()`: it is salted per process on `str`, so a group number derived
    from it would be stable within a session and different in the next one.
    Nothing here may be stored, but a number that changes on restart is a
    number that shows up as a spurious diff the moment anyone screenshots or
    logs a table.

    Raises:
        TypeError: if a parameter value cannot enter JSON — which is the same
            failure `Project.to_yaml` would give it, named at the same place.
    """
    resolved = resolved_detector(detector or DetectorSettings(), replicate)
    return json.dumps(
        [
            [[node.node_id, resolved_params(node, replicate)] for node in nodes],
            resolved.model_dump(),
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def equivalence_groups(
    pipeline: Pipeline,
    replicates: Sequence[Replicate],
    detector: DetectorSettings | None = None,
) -> tuple[int, ...]:
    """Group number per replicate, positionally, counting from 1.

    Walk in order and assign the next unused integer on first sight of a set of
    resolved parameters: the first replicate gets 1, everything matching it gets
    1, the first that differs gets 2, everything matching *that* gets 2. The
    result is as long as `replicates` and lines up with it index for index.

    **Derived on every read, never stored.** A cached group number is a number
    that goes stale — every parameter edit anywhere in the graph can move any
    replicate into or out of any group, so the invalidation rule would be "on
    everything", which is the same thing as recomputing.

    **The numbers are positional labels, not identities.** They are stable for a
    given document, because `Project.replicates` is ordered and that order is
    meaningful, and they are *not* stable across edits: pinning a parameter on
    replicate 1 renumbers every group below it. Nothing durable may reference
    one. Output paths, sink names, and report keys use `replicate_id`.

    Node order is the graph's declaration order, and the choice is genuinely
    free: every replicate is fingerprinted under the same order, so reordering
    the nodes changes each fingerprint and changes no *grouping*. The TODO item
    asked for topological order, which would buy nothing here and would put a
    `dag.py` dependency underneath a function that is pure arithmetic over
    `resolved_params`.

    A replicate that pins a parameter to the value it was already inheriting
    stays in its group, because `with_param_edit` diffs before it pins and so
    stores nothing — the group tracks what a replicate *runs with*, not whether
    a user has visited it.

    `detector` enters the fingerprint alongside the graph, because a pinned
    count threshold makes two arenas claim different events from identical
    series — "run the same thing" has to mean detection too, or the table
    says "same" about arenas whose outputs will differ. `None` fingerprints
    every replicate against the field defaults, which groups correctly: with
    no baseline to deviate from, only the pins can differ.
    """
    groups: dict[str, int] = {}
    numbers: list[int] = []
    for replicate in replicates:
        fingerprint = _params_fingerprint(pipeline.nodes, replicate, detector)
        numbers.append(groups.setdefault(fingerprint, len(groups) + 1))
    return tuple(numbers)


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
    #: The detection suffix's tuned baseline, or None while nothing has been
    #: tuned. None is `clip`'s distinction one section over: a project saved
    #: before anyone touched the detector must not come back claiming
    #: wide-open bands were *chosen* — and the untuned window D is derived
    #: from the frame rate (`DetectorSettings.default_for`), which only the
    #: bound source knows.
    detector: DetectorSettings | None = None
    #: Node ids whose output is materialized to disk — VISION step 4's "save
    #: that representative few seconds to the child layer". A run without them
    #: produces identical results and merely recomputes more, which is why they
    #: are recorded here and never hashed: the HPC wizard turns them off for a
    #: cluster with the memory to skip them (VISION step 6), and that must not
    #: change a single cache key.
    checkpoints: tuple[str, ...] = ()
    outputs: tuple[Sink, ...] = ()
    #: Crops written to disk, each a source in its own right. Here rather than
    #: on `Replicate` for `checkpoints`' reason two fields up, and it is the
    #: same test: an artifact is a faster route to pixels the graph would have
    #: computed anyway, so it changes where a result lives and never what it
    #: is. Rule 7 admits no third place. A record naming a replicate is
    #: deliberately *not* how they are associated either — `CropArtifact.backs`
    #: matches on geometry and parentage, so a record survives a rename and
    #: correctly stops matching a box that moved.
    crops: tuple[CropArtifact, ...] = ()
    #: Replicates that have been opened in the filter tab, by `replicate_id`.
    #: The geometry lock's whole state: a replicate named here has been tuned
    #: *against*, so moving its box is refused until the user accepts what the
    #: move costs (`gui/document.py`, `finish_roi_gesture`).
    #:
    #: Here rather than on `Replicate` for `checkpoints`' reason one field up,
    #: and it is the same test: whether the GUI interposes a dialog changes
    #: nothing about what a result *is*, so this must not reach a cache key.
    #: Rule 7 admits no third place — a field is hashed or it is not — and
    #: visitation is plainly the second kind.
    #:
    #: Not derived from non-empty `overrides` / `detector_overrides`, which
    #: would have needed no field at all: a replicate can be opened, looked at,
    #: and used to validate the shared baseline without ever taking a pin of
    #: its own, and the derived version would leave exactly those unlocked.
    visited: tuple[str, ...] = ()

    @field_validator("schema_version")
    @classmethod
    def _readable(cls, value: int) -> int:
        """Refuse a document from the future; restamp everything else as ours.

        The check is the field's whole reason to exist. The restamp is what
        keeps it honest over a project's life: the GUI saves by copying the
        `Project` it opened, so without this the stamp of the oldest file in
        the history is carried forever, and a document carrying v3's
        `detector` while claiming v2 sends a v2 build into `extra="forbid"`
        instead of into the message this constant exists to give. A document
        this build accepted *is* a document in this build's schema: every field it
        did not carry took the default that field was given precisely so the
        older document would mean the same thing.
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
                # Same class of staleness as a checkpoint's, and the same
                # remedy. A deviation on a node that has been deleted is a
                # parameter set nothing will ever read, and it would survive
                # every save until a new node happened to be given the id.
                if node_id not in self.pipeline:
                    raise ValueError(
                        f"replicate {replicate.replicate_id!r} overrides no such node: {node_id!r}"
                    )
            for field_name in replicate.detector_overrides:
                # The detector twin of the check above: a pin on a field that
                # does not exist is a value nothing will ever read.
                if field_name not in DetectorSettings.model_fields:
                    raise ValueError(
                        f"replicate {replicate.replicate_id!r} pins no such detector "
                        f"field: {field_name!r}"
                    )
            # And that the pinned *values* resolve, not only that they are
            # spelt right. This used to be left to `resolved_detector` on the
            # argument that spelling is structure and values are not, and that
            # split cost a session: a pin serialized as `null` by the bug this
            # model_config now fixes loaded clean here and raised later, inside
            # whichever Qt slot first asked what the selected arena runs with.
            # A raise there aborts one slot — the table went on selecting rows
            # over a document whose every tuning path was dead, which is rule 6
            # in its mirror direction. A document that cannot answer "what does
            # this arena run with" is not a document, so it is refused at the
            # one place every reader passes through, where the caller still has
            # a file name to put in the message.
            try:
                resolved_detector(self.detector or DetectorSettings(), replicate)
            except ValidationError as error:
                raise ValueError(
                    f"replicate {replicate.replicate_id!r} pins a detector value that "
                    f"does not fit its field: {error}"
                ) from error
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
        # answer yes for both. Refused here rather than deduplicated silently,
        # because the way to get one is to hand-edit the document and the
        # honest response to that is to say so. `with_crop` is the path that
        # cannot produce one.
        cuts = [artifact.identity() for artifact in self.crops]
        if len(set(cuts)) != len(cuts):
            raise ValueError("two crop artifacts record the same cut")
        known = set(ids)
        for replicate_id in self.visited:
            # A checkpoint's staleness rule applied to the lock: an id naming
            # no replicate is a lock nothing can engage, and it would survive
            # every save waiting for a generated id to collide with it.
            if replicate_id not in known:
                raise ValueError(f"visited names no such replicate: {replicate_id!r}")
        if len(set(self.visited)) != len(self.visited):
            raise ValueError("duplicate visited replicate")
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

        def rebase_crop(artifact: CropArtifact) -> CropArtifact:
            return artifact.model_copy(
                update={"path": _posix_relative(artifact.resolve(from_dir), to_dir)}
            )

        return self.model_copy(
            update={
                "source": SourceRef.relative_to(self.source.resolve(from_dir), to_dir),
                "outputs": tuple(rebase(sink) for sink in self.outputs),
                "crops": tuple(rebase_crop(artifact) for artifact in self.crops),
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

    def with_crop(self, artifact: CropArtifact) -> Self:
        """Copy that records `artifact`, replacing any earlier record of that cut.

        Replacement rather than append, keyed on `CropArtifact.identity`: a
        second write of the same cut is the same artifact written again — after
        a deleted file, or a part file left by a crash — and appending would
        produce the pair the document validator refuses. The replacement holds
        the original's position, so re-cutting one arena does not reorder the
        list.
        """
        existing = [candidate.identity() for candidate in self.crops]
        if artifact.identity() in existing:
            index = existing.index(artifact.identity())
            crops = (*self.crops[:index], artifact, *self.crops[index + 1 :])
        else:
            crops = (*self.crops, artifact)
        return self.model_copy(update={"crops": crops})

    def with_crops(self, crops: Iterable[CropArtifact]) -> Self:
        """Copy whose crop records are exactly these, in this order.

        `with_crop`'s wholesale twin, for the caller that holds the whole set
        rather than one new record — the GUI document, which owns crops the way
        it owns `visited` and writes them back on save. Validated rather than
        assigned, because "two records for one cut" is refused in the model and
        a caller assembling a tuple can produce one where `with_crop` cannot.
        """
        return self.model_validate(self.model_copy(update={"crops": tuple(crops)}))

    def without_crop(self, artifact: CropArtifact) -> Self:
        """Copy with any record of `artifact`'s cut dropped.

        Keyed on `CropArtifact.identity` for `with_crop`'s reason: what is being
        discarded is a *cut*, and the path it happens to be recorded under is
        convenience. The file itself is not touched here — deleting it is the
        caller's separate act, and a record dropped while the file survives is
        exactly the "never registered" state `materialize.py` already treats as
        safe.
        """
        wanted = artifact.identity()
        return self.model_copy(
            update={
                "crops": tuple(
                    candidate for candidate in self.crops if candidate.identity() != wanted
                )
            }
        )

    def with_visited(self, visited: Iterable[str]) -> Self:
        """Copy whose geometry locks are exactly these replicates.

        Kept in `replicates` order rather than in the caller's, and deduplicated
        on the way: the field is a set the artifact has to spell as a tuple, and
        letting the order follow the caller would make two documents that lock
        the same arenas differ byte for byte in YAML — the stability `to_yaml`
        exists to protect.

        Filtering is what makes this safe to assign without revalidating, and
        it has to be — `with_pipeline` is the validating one *because* the
        graph is written last, and a check here would fire on the intermediate
        document a save passes through, where the replicates are already in
        place and the nodes their overrides name are not yet. So an id that
        matches no replicate is dropped rather than refused: this is the path a
        deleted arena's lock leaves the file by.
        """
        wanted = set(visited)
        kept = tuple(
            replicate.replicate_id
            for replicate in self.replicates
            if replicate.replicate_id in wanted
        )
        return self.model_copy(update={"visited": kept})

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

    def equivalence_groups(self) -> tuple[int, ...]:
        """Group number per replicate, in `replicates` order.

        A lookup around the module function, for the same reason `params_for`
        is one around `resolved_params`: the caller holds a document, and
        pairing the graph with the replicate set itself is the step where a
        second answer gets invented.
        """
        return equivalence_groups(self.pipeline, self.replicates, self.detector)

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
        updated_node, edited = edited_params(node, target, params)
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

    def with_detector(self, detector: DetectorSettings | None) -> Self:
        """Copy carrying a different detector baseline, including none."""
        return self.model_copy(update={"detector": detector})

    def with_detector_edit(self, replicate_id: str, changes: Mapping[str, Any]) -> Self:
        """Configure the detector for one replicate, moving the default with it.

        `with_param_edit` for the detection suffix — the same two writes with
        the same consequences, through `edited_detector`. A project whose
        detector was never tuned edits against the field defaults; a GUI
        holding a frame rate should seed the baseline first so "one second of
        D" diffs as itself rather than as a deviation from 30.

        Raises:
            KeyError: if `replicate_id` names nothing.
            ValidationError: if `changes` names no such field or misfits one.
        """
        target = self.replicate(replicate_id)
        moved, edited = edited_detector(self.detector or DetectorSettings(), target, changes)
        replicates = tuple(edited if r is target else r for r in self.replicates)
        return self.model_copy(update={"detector": moved, "replicates": replicates})

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
