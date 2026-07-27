"""The filter contract, as data: `FilterSpec`, `ParamsBase`, `ArraySpec`, `Mode`.

Nothing in this module executes a filter, and that is the point. A saved
pipeline names filters by id and version; validating its structure — that the
graph is acyclic, that each edge's types chain, that every parameter is known —
must work on a machine with no codec, no CUDA, and none of the filters
installed. Splitting the spec from the kernels is what buys that: kernels live
beside their spec in `sieve.filters`, free to import cv2 or cupy, while this
layer stays pure.

The spec is also the single source of truth for a filter's parameters. GUI
widgets, CLI flags, YAML, and the cache key all read `params_model`; none of
them carries a second copy of the field list that could drift from it.

**Three declarations are params-derived rather than constants**, because the
quantity they describe *is* a parameter: a decimator's factor, a downsampler's
scale. `output_rate` and `frame_bytes_ratio` are therefore methods on
`ParamsBase` with 1:1 defaults, not fields on `FilterSpec`. They stay pure —
data in, exact number out, no kernel, no codec — so `dag.py` and the executor
can evaluate them on a machine with nothing installed, which is the property
the whole split exists to preserve.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from typing import Any, ClassVar, TypeAlias

from pydantic import BaseModel, ConfigDict

from sieve.core.types import ChannelSpec

#: `MAJOR.MINOR.PATCH`, no pre-release or build metadata. A filter version is
#: an input to a cache key before it is a human-facing label, and `1.0.0-rc1`
#: vs `1.0.0` is an ordering question with no answer this system needs to have.
#:
#: Public because `pipeline_model` validates the same two strings on the way in
#: from YAML. That is not registry awareness — it never asks whether the filter
#: exists — but it is the same syntactic contract, and a second copy of the
#: regex is a second thing to keep in step.
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

#: Lowercase identifier. It appears in cache keys, YAML, and CLI arguments, so
#: it may not depend on case folding or shell quoting to stay itself.
FILTER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

#: The input port a single-input filter listens on, and the port an `Edge`
#: that names none feeds. One name, defined here, because it appears in three
#: places that must agree: the normalized form of `FilterSpec.accepts`, the
#: default on `Edge.port`, and every cache key's upstream fold — a second
#: spelling in any of them is a graph that validates and a key that misses.
DEFAULT_PORT = "in"

#: Port names share the filter-id spelling rule for the same reason sink
#: formats do: they enter cache keys and saved documents, where case folding
#: and quoting are not to be relied on.
PORT_PATTERN = FILTER_ID_PATTERN


class Mode(StrEnum):
    """Whether a filter can emit a frame as soon as it has consumed one."""

    #: One frame in, one frame out, in order. The executor may pipeline it.
    STREAMING = "streaming"
    #: Needs a span of frames before it can emit any of them. The executor
    #: must accumulate the window rather than hand frames through singly.
    WINDOWED = "windowed"


class StreamKind(StrEnum):
    """What sort of thing travels along an edge.

    A sibling of the shape declarations rather than a field on one, because the
    two kinds have nothing in common to declare — a table has no dtype and an
    array has no columns — and a single type carrying both field sets would be
    half-empty whichever kind it was describing.
    """

    #: Frames: an `ArraySpec` describes it.
    ARRAY = "array"
    #: Rows: a `TableSpec` describes it. VISION step 1's "coordinates of that
    #: specific color as a csv and enough information to stick it into R".
    TABLE = "table"


#: Rate `1`, allocated once. `Fraction` is immutable, so every unchanged filter
#: can share it, and `output_rate() is UNCHANGED_RATE` is a cheap fast path.
UNCHANGED_RATE = Fraction(1, 1)


class ParamsBase(BaseModel):
    """Base for every filter's parameter model.

    Frozen because a params object is an identity: something that has been
    hashed into a cache key must not then change underneath the entry. Extra
    fields are forbidden because the alternative is silent — a YAML with a
    misspelled parameter would otherwise validate, run with the default, and
    produce a cache key identical to the run the user meant to vary.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Set by `filter_registry.register_filter` when this model is decorated.
    #: `None` on a params model that was declared without one, which is legal
    #: — a test fixture, or a base another filter's params inherit from.
    __filter_spec__: ClassVar[FilterSpec | None] = None

    @classmethod
    def spec(cls) -> FilterSpec:
        """This model's registered spec, or refuse.

        The narrowing every caller was writing by hand. `__filter_spec__` is
        legitimately optional — a test fixture or a shared base has none — but
        almost nobody who reaches for it wants the `None`: a kernel decorator, a
        registry, and a test all want the spec or a clear failure, and each was
        spelling that out again with a slightly different message.

        Raises:
            TypeError: if this model carries no spec, meaning it was never
                decorated with `@register_filter`.
        """
        if cls.__filter_spec__ is None:
            raise TypeError(
                f"{cls.__name__} has no filter spec: it was never decorated with @register_filter, "
                "so it has no id, version, or declared I/O"
            )
        return cls.__filter_spec__

    def canonical_json(self) -> str:
        """Byte-stable JSON of these params, for hashing.

        `mode="json"` so enums and paths become the same strings they became in
        the artifact, sorted keys so the string does not depend on field
        declaration order, and no whitespace because a hash input is not read
        by anyone.
        """
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def output_rate(self) -> Fraction:
        """Output frames per input frame, exactly.

        `Fraction`, not `float`: this is the divisor in the warmup conversion
        below, and `ceil(5 / 0.1)` is 50 only until the day the factor is 3.
        An exact rational makes the arithmetic answer the question asked rather
        than one binary rounding away from it.

        Overridden by any filter whose output stops being indexed like its
        input — a 10:1 decimator returns `Fraction(1, 10)`. Overriding it
        obliges the spec to set `rate_changing=True`; `FilterSpec` refuses the
        pair otherwise, because the failure this closes is a decimator that
        simply forgot to say so, and that failure is silent.

        A filter that consumes frames and emits a table still has a rate: rows
        per input frame is not what this measures, and such a filter leaves it
        at 1 unless it also drops frames. Downstream of a table there is
        nothing left to warm up.
        """
        return UNCHANGED_RATE

    def frame_bytes_ratio(self) -> float:
        """Bytes of one output frame per byte of one input frame.

        The spatial half of output size, kept apart from `output_rate`'s
        temporal half so that neither has to know about the other: a
        downsampler overrides this with `1 / factor**2` and says nothing about
        rate, a decimator overrides rate and says nothing about size, and
        `FilterSpec.stored_bytes_ratio` multiplies them.

        Unlike `output_rate` this is a `float` and is deliberately not
        cross-checked against anything on the spec. It feeds VISION step 4's
        storage HUD and step 5's compaction suggestion and never a correctness
        decision, so an undeclared override is a wrong prediction rather than a
        wrong result — the asymmetry with rate is the point.
        """
        return 1.0


@dataclass(frozen=True, slots=True)
class ArraySpec:
    """What a filter consumes or produces, declared narrowly enough to reject.

    Both fields are *allowed sets*, and an empty tuple means "any" — a
    downsample kernel that indexes with a stride genuinely does not care about
    dtype or channel layout, and forcing it to enumerate every combination
    would make the declaration a lie the first time a new dtype appeared.

    There is no `ndim`: a frame's rank is determined by its channel layout, and
    a second field that can contradict the first is a field that eventually
    will.
    """

    kind: ClassVar[StreamKind] = StreamKind.ARRAY

    #: NumPy dtype names, e.g. `("uint8", "float32")`.
    dtypes: tuple[str, ...] = ()
    channels: tuple[ChannelSpec, ...] = ()

    def admits(self, produced: StreamSpec) -> bool:
        """Whether an upstream node emitting `produced` may feed this one.

        Deliberately permissive: it is false only when the two sets are
        provably disjoint. A wildcard on either side admits, because the DAG's
        static check exists to reject graphs that *cannot* work, and rejecting
        one that merely cannot be proven to work would make declaring `dtypes`
        at all a liability.

        A kind mismatch is the one thing that is never a wildcard. Rows are not
        frames under any parameterization, so a table upstream of an array
        input is provably disjoint no matter what either side left unstated.
        """
        if not isinstance(produced, ArraySpec):
            return False
        return self._compatible(self.dtypes, produced.dtypes) and self._compatible(
            self.channels, produced.channels
        )

    @staticmethod
    def _compatible(required: tuple[Any, ...], produced: tuple[Any, ...]) -> bool:
        if not required or not produced:
            return True
        return bool(set(required) & set(produced))


@dataclass(frozen=True, slots=True)
class TableSpec:
    """Rows rather than frames: detections, coordinates, per-frame summaries.

    VISION step 1 asks for "the coordinates of that specific color as a csv and
    enough information to stick it into R" as a first-class output, and duckdb
    and pyarrow are already dependencies, so this is a stream the graph carries
    rather than only a thing a sink writes.

    `columns` is conjunctive where `ArraySpec`'s sets are disjunctive, and the
    difference is not an oversight. A filter listing `("uint8", "float32")`
    accepts *either*; a filter listing `("x", "y")` needs *both*, because a
    column that is absent cannot be substituted by one that is present. Empty
    still means unconstrained on both sides.

    No dtypes per column. The reason is `ArraySpec.ndim`'s reason: the useful
    check is whether the column is there at all, and a type declaration that
    can disagree with the table actually produced is one that eventually will.
    """

    kind: ClassVar[StreamKind] = StreamKind.TABLE

    #: Required of an upstream when this is an `accepts`; guaranteed to
    #: downstreams when it is an `emits`. Empty means unconstrained.
    columns: tuple[str, ...] = ()

    def admits(self, produced: StreamSpec) -> bool:
        """Whether an upstream node emitting `produced` may feed this one."""
        if not isinstance(produced, TableSpec):
            return False
        if not self.columns or not produced.columns:
            return True
        return set(self.columns) <= set(produced.columns)


#: What an edge may carry. A union rather than a base class with two subclasses:
#: there is no shared field to inherit, and the one shared operation — `admits`
#: — has no shared implementation either, since columns and dtypes are compared
#: on opposite logics. `kind` exists so a rejection can be *named* ("an array
#: cannot feed a table input"); the narrowing itself goes through `isinstance`,
#: which is what a type checker can follow.
#:
#: One *output* stream per node, still. Input ports arrived with the temporal
#: chain — `Edge.port` names which of a downstream's declared inputs an edge
#: feeds, and `FilterSpec.accepts` may be a mapping of them — but a detector
#: that wants to emit both an overlay frame and a coordinate table needs the
#: same treatment on the *emits* side, and that half is still deliberately
#: unbuilt: no filter needs it, and the artifact change it forces should wait
#: for the one that does.
StreamSpec: TypeAlias = ArraySpec | TableSpec


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Order-of-magnitude cost, for predicting a run before making it.

    Normalized per megapixel rather than per frame: the same kernel on 4K and
    on a 256x256 crop differ by two orders of magnitude, so a per-frame number
    would be wrong for every resolution but the one it was measured at. These
    drive HUD predictions and scheduling hints, never a correctness decision,
    so a factor-of-two error is tolerable and a missing declaration is not.

    Nothing here predicts *stored* bytes, and nothing here can: what a
    checkpoint costs on disk depends on the decimation factor and the
    downsample scale, which are parameters and not properties of the kernel.
    That prediction is `FilterSpec.stored_bytes_ratio`, which reads the two
    params methods. `peak_bytes_per_input_byte` below is a working set — what
    the kernel needs held at once — and the two differ by an order of magnitude
    for exactly the filters VISION step 4 puts in front of everything else.
    """

    #: Wall-clock seconds to process one megapixel on the reference CPU.
    seconds_per_megapixel: float
    #: Peak working set as a multiple of one input frame's bytes. 1.0 is an
    #: in-place kernel; 3.0 is one that holds input, output, and a scratch.
    peak_bytes_per_input_byte: float = 2.0


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """Everything about a filter that is knowable without running it."""

    filter_id: str
    version: str
    summary: str
    params_model: type[ParamsBase]
    #: What each input port consumes. A bare `StreamSpec` is the one-input
    #: case and means `{DEFAULT_PORT: spec}` — every existing filter keeps its
    #: declaration unchanged — and a mapping is a merging filter naming its
    #: ports. Read through `input_ports`, which does that normalization once;
    #: nothing downstream should branch on which form was written.
    accepts: StreamSpec | Mapping[str, StreamSpec]
    emits: StreamSpec
    cost: CostEstimate
    mode: Mode = Mode.STREAMING
    #: Frames the filter must consume before its output is trustworthy, counted
    #: in this filter's *input* frames — "must consume" is the unit. Warmup
    #: accumulates along the topological path feeding a request, but it does not
    #: simply sum: a rate-changing node between two others makes the two speak
    #: different index spaces. `source_warmup_frames` does the conversion, and
    #: is the only thing that should. An IIR's true warmup is infinite, so a
    #: nonzero value here is a settled-to-within-epsilon choice and the
    #: filter's docstring says which epsilon.
    #:
    #: Usually paired with `stateful` below, and deliberately not *required* to
    #: be. The claim this makes is "my first N outputs are untrustworthy", and
    #: kernel state is one way to have such outputs rather than the only one — a
    #: `WINDOWED` filter has them too, and its protocol does not exist yet.
    warmup_frames: int = 0
    #: This filter's output is not indexed like its input — a decimator. Must
    #: agree with whether `params_model` overrides `output_rate`, and the
    #: agreement is checked below. Declaring it is not redundant with the
    #: override: the override is what computes the conversion, and this is what
    #: makes forgetting to write one an error at registration rather than a
    #: preview that renders, is under-warmed by the decimation factor, and
    #: looks entirely plausible.
    rate_changing: bool = False
    #: Same backend, same input, same output. Gates whether the node may be
    #: cached at all.
    deterministic: bool = True
    #: This filter's kernel carries state across frames — a background model, an
    #: IIR, a tracker. Declared here rather than discovered from the kernel
    #: because the consequence is a *caching* decision and caching is settled by
    #: `pipeline/dag.py` on a machine that may have no kernels installed.
    #:
    #: What it costs is the cache, and the reason is subtler than it looks. Such
    #: a filter's output at frame `i` depends on every frame from wherever the
    #: run began — but if its `warmup_frames` is correct, that dependence has
    #: decayed below the filter's own epsilon by the time any frame is yielded,
    #: and two runs over different spans agree. Measured; see the finding.
    #:
    #: The exclusion is because *nothing can check that*. A key is derived from
    #: declarations, and a filter declaring `warmup_frames=0` over a running sum
    #: is indistinguishable here from one declaring 90 over a settled EMA. So a
    #: served entry would rest on an unverified number in a decorator, and the
    #: failure lands exactly where `cache_key.py`'s asymmetry rule says it must
    #: not: well-formed key, plausible frame, no symptom. See
    #: `docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.
    stateful: bool = False
    #: CPU and GPU kernels agree bit for bit. Gates whether backend identity
    #: leaves the cache key. False for essentially every float kernel — cuFFT
    #: and NumPy's FFT do not agree, and neither do two OpenCV SIMD paths — so
    #: it defaults false and claiming it requires an equivalence test.
    backend_agnostic: bool = False
    #: The one to three parameters the GUI shows before "Advanced". Names must
    #: exist on `params_model`; that is checked below, because the failure mode
    #: of a stale name is a widget that silently stops appearing.
    primary_params: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.accepts, Mapping):
            if not self.accepts:
                raise ValueError(
                    f"{self.filter_id}: accepts is an empty mapping — a filter with no input "
                    "port consumes nothing, and a source is not a filter"
                )
            bad = [name for name in self.accepts if not PORT_PATTERN.match(name)]
            if bad:
                raise ValueError(
                    f"{self.filter_id}: port names must match {PORT_PATTERN.pattern!r}, "
                    f"got {sorted(bad)}"
                )
        if not FILTER_ID_PATTERN.match(self.filter_id):
            raise ValueError(
                f"filter_id must match {FILTER_ID_PATTERN.pattern!r}, got {self.filter_id!r}"
            )
        if not SEMVER_PATTERN.match(self.version):
            raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {self.version!r}")
        if self.warmup_frames < 0:
            raise ValueError(f"warmup_frames must be non-negative, got {self.warmup_frames}")
        if self.backend_agnostic and not self.deterministic:
            # Bit-for-bit agreement across backends is a strictly stronger
            # claim than agreement with itself on one backend. Allowing both
            # would drop backend identity from the cache key for a filter whose
            # output nothing can reproduce.
            raise ValueError(
                f"{self.filter_id}: backend_agnostic requires deterministic — a filter that "
                "cannot reproduce its own output cannot agree with another backend's"
            )
        known = set(self.params_model.model_fields)
        unknown = [name for name in self.primary_params if name not in known]
        if unknown:
            raise ValueError(
                f"{self.filter_id}: primary_params names no such field: {sorted(unknown)}"
            )
        # Comparing the function objects, not calling them: a params model with
        # required fields cannot be instantiated here, and the question is
        # whether an override exists at all rather than what it returns.
        overrides = self.params_model.output_rate is not ParamsBase.output_rate
        if self.rate_changing and not overrides:
            raise ValueError(
                f"{self.filter_id}: rate_changing is set but {self.params_model.__name__} does not "
                "override output_rate, so nothing can convert a downstream warmup into source "
                "frames"
            )
        if overrides and not self.rate_changing:
            raise ValueError(
                f"{self.filter_id}: {self.params_model.__name__} overrides output_rate but the "
                "spec does not declare rate_changing"
            )

    @property
    def input_ports(self) -> Mapping[str, StreamSpec]:
        """`accepts`, always as port name to spec.

        The one place the bare-`StreamSpec` shorthand is expanded. `dag.py`
        checks edge types against this, the executor decides one-frame versus
        mapping call shape by its length, and both must agree on what the
        single port is called — which is why the name is `DEFAULT_PORT` and not
        a literal here.
        """
        if isinstance(self.accepts, Mapping):
            return self.accepts
        return {DEFAULT_PORT: self.accepts}

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        """Version as integers, so `1.10.0` sorts above `1.9.0`."""
        match = SEMVER_PATTERN.match(self.version)
        assert match is not None  # guaranteed by __post_init__
        major, minor, patch = match.groups()
        return (int(major), int(minor), int(patch))

    @property
    def key(self) -> tuple[str, str]:
        """Registry key: a filter is identified by id *and* version.

        Two versions of one filter coexist deliberately — an old pipeline that
        names 1.0.0 must keep reproducing 1.0.0's output after 1.1.0 ships.
        """
        return (self.filter_id, self.version)

    @property
    def cacheable(self) -> bool:
        """Whether this node's output may be reused from a cache entry.

        Two different disqualifications, and they are not the same one twice.
        A non-deterministic filter cannot reproduce its own output at all. A
        stateful one reproduces it exactly, and may well reproduce it across
        runs too — but only if a number it declared about itself is true, and
        this property is evaluated where that cannot be checked. See `stateful`
        above.
        """
        return self.deterministic and not self.stateful

    @staticmethod
    def stored_bytes_ratio(params: ParamsBase) -> float:
        """Bytes written per byte consumed, if this node were materialized.

        The two halves of output size multiplied: how many output frames there
        are per input frame, and how big one of them is. A 10:1 decimator in
        front of a 2x downsampler stores a fortieth of what it was handed, and
        neither filter had to know about the other to say so.

        A prediction for VISION step 4's storage readout and step 5's
        compaction suggestion, never an input to a cache key or a decision
        about what to compute. `static` because it reads nothing off the spec —
        it is here rather than beside the two methods it calls so that the
        composition is defined once, where a caller holding a spec will find it.
        """
        return float(params.output_rate()) * params.frame_bytes_ratio()


#: One step of a path: a filter and the parameters it was configured with. The
#: params are not optional — half of what a step contributes is params-derived.
PathStep: TypeAlias = "tuple[FilterSpec, ParamsBase]"


def input_warmup_frames(step: PathStep, output_warmup: int) -> int:
    """One node's conversion: lead-in at its input, given lead-in at its output.

    The single edge of the warmup arithmetic. `output_warmup` frames wanted at
    this node's output cost `ceil(output_warmup / rate)` at its input, and the
    node's own `warmup_frames` is already denominated there, so it adds on top.

    Extracted from `source_warmup_frames` rather than inlined in it because a
    DAG walk needs the step without the path: `pipeline/plan.py` folds this over
    a topological order, taking the maximum over a node's downstreams instead of
    over enumerated paths. Two implementations of one conversion is exactly what
    that function's docstring argues against, so there is one and both call it.

    **Monotone non-decreasing in `output_warmup`**, and that is load-bearing
    rather than incidental: `ceil` and `+` are both monotone, so the maximum
    over a node's paths equals the maximum taken node-by-node along the way.
    Without it a DAG walk would have to enumerate paths, of which a diamond
    chain has exponentially many.

    Args:
        step: The node's `(spec, params)`.
        output_warmup: Frames of lead-in wanted at this node's output.

    Returns:
        Frames of lead-in needed at this node's input.

    Raises:
        ValueError: if the node reports a non-positive output rate, which would
            mean an output frame no quantity of input could supply.
    """
    spec, params = step
    rate = params.output_rate()
    if rate <= 0:
        raise ValueError(f"{spec.filter_id}: output_rate must be positive, got {rate}")
    return math.ceil(Fraction(output_warmup) / rate) + spec.warmup_frames


def source_warmup_frames(path: Sequence[PathStep]) -> int:
    """Lead-in to decode, in *source* frames, for a path ordered root to sink.

    ARCHITECTURE says the executor "sums `warmup_frames` over the topological
    path feeding a preview, requests `[clip_start - total, clip_end]`, and
    discards the lead-in". Summing is the right idea in the wrong unit, and the
    unit only matters once something changes rate. Walking sink to root instead:
    a requirement of `need` frames at a node's output costs `ceil(need / rate)`
    at its input, and the node's own `warmup_frames` is already denominated
    there. Five frames of warmup behind a 10:1 decimator is fifty source frames,
    not five, and the error a plain sum makes is silent — the preview renders,
    an IIR that should have settled produces a plausible frame, and the tuning
    done against it is wrong rather than absent.

    Lives here rather than in `pipeline/executor.py` for two reasons: it needs
    no graph, only an order someone else established, so it is testable without
    an executor; and the conversion belongs beside the declaration that defines
    the unit, where a second copy is less likely to be written.

    A fold of `input_warmup_frames` from sink to root. The per-step conversion
    is separate because a DAG has more than one root-to-node path and the walk
    that handles that — `pipeline/plan.py` — needs the step rather than the
    path. This function is the single-path case and stays the definition the
    walk is checked against.

    Args:
        path: `(spec, params)` from the root node to the requesting node,
            inclusive. An empty path needs no lead-in.

    Returns:
        Frames to decode before `clip_start`.

    Raises:
        ValueError: if any node reports a non-positive output rate, which would
            mean an output frame the source could never supply enough input for.
    """
    need = 0
    for step in reversed(path):
        need = input_warmup_frames(step, need)
    return need
