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

**Four declarations are params-derived rather than constants**, because the
quantity they describe *is* a parameter: a decimator's factor, a downsampler's
scale, a trailing window's length, a span's bounds. `output_rate`,
`frame_bytes_ratio`, `warmup_frames` and `selected_frames` are therefore methods
on `ParamsBase`, not (only) fields on `FilterSpec`. They stay pure — data in,
exact number out, no kernel, no codec — so `dag.py` and the executor can
evaluate them on a machine with nothing installed, which is the property the
whole split exists to preserve.

They are params-derived in three different *shapes*, and the difference is
about what a wrong answer costs. `output_rate` and `selected_frames` are
cross-checked against a spec flag, because forgetting to declare a decimation or
a selection is silent and wrong. `frame_bytes_ratio` is cross-checked against
nothing, because it feeds a prediction and never a result. `warmup_frames` sits
between them: the spec field is the *bound* — the worst case over the legal
parameter range, which is what `sieve inspect` can print without a configuration
in hand — and the method is this configuration's actual need, which may refine
the bound downward but never exceed it. `node_warmup_frames` enforces that, and
the asymmetry is the point: a refinement that is too small under-warms a filter
silently, and a bound that is too large only wastes decode.
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

from sieve.core.types import NO_FRAMES, WORK_UNIT_ANCHOR, ChannelSpec, FrameCount, WorkUnits

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


class ElementKind(StrEnum):
    """What one value of a frame *is a value of*.

    `ArraySpec` says a frame is float32 and single-channel, which is enough to
    reject a graph that cannot run and is what it was built for. It does not
    say whether one of those floats describes a pixel or a 64x64 block of them,
    and nothing needed the difference while the only consumer was the executor,
    which moves arrays without interpreting them. A consumer that *counts*
    elements does need it: `sieve detect` reports how many of a frame's values
    fell inside a value band, and the noun in that sentence comes from here or
    it is invented.

    Two members, and the second is not speculative padding: `block_signal`
    emits one float per block and `downsample` emits one per pixel, both under
    `ArraySpec(dtypes=("float32",))`. A third member arrives with the filter
    that needs it and not before.
    """

    #: One value per pixel of the frame it was measured from. What a decoded
    #: source frame carries, and therefore where every graph's walk starts.
    PIXEL = "pixel"
    #: One value per block of a grid the frame was divided into.
    BLOCK = "block"
    #: One value describing the source frame as a whole.
    FRAME = "frame"


@dataclass(frozen=True, slots=True)
class ElementNames:
    """Column-safe names for one emitted array element.

    `ElementKind` is a type-level answer: a count over blocks is different from
    a count over pixels. `ElementNames` is the interop vocabulary that leaves
    the process: CSV headers, README dictionaries, and count axes all read it
    instead of deriving English from the enum or from a widget's local copy.

    Both forms are required because singular and plural are not a rule the
    writer can safely invent. They follow the filter-id spelling rule so a name
    can be composed into a stable column without quoting or case folding.
    """

    singular: str
    plural: str

    def __post_init__(self) -> None:
        bad = [name for name in (self.singular, self.plural) if not FILTER_ID_PATTERN.match(name)]
        if bad:
            raise ValueError(
                f"element names must match {FILTER_ID_PATTERN.pattern!r}, got {sorted(bad)}"
            )


#: What the decoded source contributes before any filter has redefined it.
#: Roots that preserve their input read this value; filters that redefine
#: elements declare their own `element_names`.
SOURCE_ELEMENT_NAMES = ElementNames("pixel", "pixels")


class ElementRelation(StrEnum):
    """What a filter does to the element meaning it was handed.

    A sibling of `ElementKind` rather than more members on it, because these
    are not answers to "what is one value of" — they are relations between a
    filter's input and its output, and a filter that preserves has no constant
    to declare. `temporal_baseline` is why this axis exists at all: it accepts
    any array and estimates per cell, so it emits blocks over `block_signal`
    and pixels over a raw frame, and any constant it declared would be a lie in
    one of the two positions.
    """

    #: One output element is one input element, whatever that was. The per-cell
    #: and per-pixel filters: `normalize`, `background_ema`, `motion_history`,
    #: `temporal_baseline`.
    PRESERVED = "preserved"
    #: One output element is *many* input elements, spatially. `downsample` and
    #: `rescale`. Kind-dependent rather than simply destructive, and the
    #: asymmetry is the point: a mean of pixels is still a sample of the scene
    #: at a coarser spacing, so `PIXEL` survives; a mean of blocks is not a
    #: block, because a block is already an aggregate and re-aggregating it
    #: leaves a quantity no count threshold is denominated in.
    AGGREGATED = "aggregated"


#: What a filter declares about its output's elements: a kind outright, or a
#: relation to its input's. A union rather than one enum with four members so
#: that the *resolved* answer has a type of its own — `ElementKind | None` is
#: what a walk produces and what a consumer may read, and `PRESERVED` must not
#: be assignable to it. The narrowing goes through `isinstance`, which is what
#: a type checker can follow, exactly as `StreamSpec`'s does.
ElementDeclaration: TypeAlias = "ElementKind | ElementRelation"


def node_element(
    declaration: ElementDeclaration | None, upstream: ElementKind | None
) -> ElementKind | None:
    """One node's element meaning, given its input's. `None` is *undeclarable*.

    The single-node conversion, kept here beside the declaration that defines
    it while the walk that supplies `upstream` lives in `pipeline/dag.py` —
    `input_warmup_frames` and `plan.py`'s fold are the same split for the same
    reason, and a second implementation of the conversion is what that
    arrangement exists to prevent.

    `None` propagates and never recovers: a filter downstream of a node whose
    elements have no meaning cannot give them one back by preserving them.

    **`AGGREGATED` defaults over `ElementKind`, and the polarity is the whole
    reason that is allowed.** `FilterSpec.element` refuses a default because an
    omission there resolves to a confident wrong noun; the branch below names
    `PIXEL` and sends every other kind to `None`, so a third `ElementKind`
    member added tomorrow is *refused* under aggregation until somebody decides
    what a mean of one means. Fails closed rather than open, which is the only
    kind of default this file has any business carrying.

    Args:
        declaration: `FilterSpec.element`. `None` only for a table emitter,
            which has no elements at all.
        upstream: The element meaning arriving at this node, or `None` if that
            was itself undeclarable. A root is handed `ElementKind.PIXEL` —
            the source is frames of pixels.

    Returns:
        What one value of this node's output is a value of, or `None` when
        nothing can honestly say.
    """
    if declaration is None:
        return None
    if isinstance(declaration, ElementKind):
        return declaration
    if declaration is ElementRelation.AGGREGATED:
        return upstream if upstream is ElementKind.PIXEL else None
    return upstream


def node_element_names(
    declaration: ElementDeclaration | None,
    declared: ElementNames | None,
    upstream: ElementKind | None,
    upstream_names: ElementNames | None,
) -> ElementNames | None:
    """One node's emitted element names, given its input's.

    A filter that declares a concrete `ElementKind` introduces the noun beside
    that declaration. A preserving filter preserves the noun it was handed. An
    aggregating filter keeps names only in the same case `node_element` keeps
    meaning: pixels stay pixels, while blocks aggregate into a value no count
    threshold has an honest name for.
    """
    if declaration is None:
        return None
    if isinstance(declaration, ElementKind):
        return declared
    if declaration is ElementRelation.AGGREGATED:
        return upstream_names if upstream is ElementKind.PIXEL else None
    return upstream_names


#: Rate `1`, allocated once. `Fraction` is immutable, so every unchanged filter
#: can share it, and `output_rate() is UNCHANGED_RATE` is a cheap fast path.
UNCHANGED_RATE = Fraction(1, 1)

#: One past the last frame `ALL_FRAMES` covers. A bound, not a measurement:
#: 2**32 frames is 207 days at 240 fps, which is unreachable, and it is small
#: enough that a reader meeting `4294967296` in a saved document can tell it is a
#: bound. Unbounded rather than the video's own length for `crop.WHOLE_FRAME`'s
#: reason — a graph is written by things that have not opened the video, and the
#: length is a fact about the container.
UNBOUNDED_FRAME = 1 << 32

#: Every frame there could be: the identity of the selection fold, allocated once
#: for `UNCHANGED_RATE`'s reason. A `range` rather than a range type of its own,
#: because `ExecutionPlan.decode_range` already made `range` this codebase's
#: spelling of a half-open frame interval, and a second spelling in `core` would
#: be REWORK.md R4's one-name-two-homes with nothing to show for it.
ALL_FRAMES = range(0, UNBOUNDED_FRAME)


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

    def presentation_values(self) -> Mapping[str, str]:
        """Parameter display values that need filter-owned derivation.

        Most parameters render from their stored value, optionally through the
        spec's `param_value_labels`. A filter overrides this only when the
        value shown is derived from more than one parameter, such as a block
        size whose `0` means "auto at the current scale".
        """
        return {}

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

    def selected_frames(self) -> range:
        """Which frames this configuration keeps, half-open, in its input space.

        `output_rate`'s treatment for the other way a filter can emit fewer
        frames than it consumed. A rate change is uniform and reindexes — every
        tenth frame, and the tenth output *is* the hundredth input — so it is
        arithmetic the warmup fold has to cross. A selection is neither: the
        frames that survive keep their numbering, and what changes is only which
        of them are in the answer at all.

        Overriding it obliges the spec to set `selecting=True`, which
        `FilterSpec` refuses the pair without, for `output_rate`'s reason: a
        filter that narrows the answer and forgets to say so would be run over
        the whole video and its declaration would be the only evidence.

        **Denominated in this filter's input space, which is the source's.**
        `executor._run_node` refuses any node whose output carries a different
        index from its input, and the one declaration that could legitimately
        change it — `rate_changing` — has no runnable kernel, so every node in a
        graph that runs today numbers its frames the way the reader does. That is
        an argument with an expiry date on it: `a-kernel-that-changes-the-rate`
        is where a selection downstream of a decimator stops meaning the same
        thing as one at the root, and `plan._selected` is what has to convert.

        Returns:
            The kept range. `ALL_FRAMES` — the default, never overridden by most
            filters — is "all of them", a value rather than an absence, so no
            `range | None` propagates into the plan (REWORK.md R1).
        """
        return ALL_FRAMES

    def warmup_frames(self) -> FrameCount:
        """Frames *this configuration* must consume before its output is good.

        A refinement of `FilterSpec.warmup_frames`, which is the worst case over
        the whole legal parameter range. Overriding is optional and the default
        here is never read — `node_warmup_frames` takes the spec's number unless
        an override exists — so a filter whose warmup is genuinely a constant
        declares it once, on the spec, and nothing else.

        **What it buys, and why it is not a nicety.** A static declaration has
        to be true for every setting of every parameter, so a filter whose
        warmup *is* a parameter declares the product of that parameter's bound
        with every other bound it depends on. `temporal_baseline`'s window may
        be 30 s and its footage 240 fps, so its bound is 7200 frames — a lead-in
        every run would decode, including the one asking for a 5 s window at
        30 fps that needs 150. `background_ema` has the same problem an order of
        magnitude smaller and documented the waste as the price of a true
        declaration; this is what makes the declaration true *and* tight.

        Must not exceed the spec's bound, and `node_warmup_frames` refuses the
        pair rather than trusting it. Overriding does not oblige a spec flag the
        way `output_rate` does, because the failure modes are not comparable: an
        undeclared rate change under-warms every downstream node silently, while
        a warmup that was never refined merely decodes frames nobody needed.
        """
        return NO_FRAMES

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """Worst-case warmup over this params model's legal range.

        `FilterSpec.warmup_frames` is derived from this class-level answer
        because the bound changes with the parameter model's own legal range.
        The instance method above refines the same quantity for one
        configuration.
        """
        return NO_FRAMES

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

    Normalized per megapixel rather than per frame: the same kernel on 4K and on
    a 256x256 crop differ by two orders of magnitude, so a per-frame number
    would be wrong for every resolution but the one it described. The numerator
    is `WorkUnits`, not wall time. One unit is anchored to
    `WORK_UNIT_ANCHOR`, and conversion to seconds belongs to a calibration for
    one target profile. An uncalibrated install therefore still has a relative
    cost to show and nothing to divide by.

    Nothing here predicts *stored* bytes, and nothing here can: what a
    checkpoint costs on disk depends on the decimation factor and the
    downsample scale, which are parameters and not properties of the kernel.
    That prediction is `FilterSpec.stored_bytes_ratio`, which reads the two
    params methods. `peak_bytes_per_input_byte` below is a working set — what
    the kernel needs held at once — and the two differ by an order of magnitude
    for exactly the filters VISION step 4 puts in front of everything else.
    """

    #: The one reference operation that defines a work unit.
    anchor: ClassVar[str] = WORK_UNIT_ANCHOR
    #: Relative work to process one input megapixel, anchored by
    #: `WORK_UNIT_ANCHOR`.
    work_per_megapixel: WorkUnits
    #: Peak working set as a multiple of one input frame's bytes. 1.0 is an
    #: in-place kernel; 3.0 is one that holds input, output, and a scratch.
    peak_bytes_per_input_byte: float = 2.0


class AuthoringGroup(StrEnum):
    """Stable buckets a front end can use to group operation offers.

    This is not the visible header text. The values are cache-stable slugs that
    say where an operation belongs in an authoring workflow; a GUI may translate
    or reorder them without changing what a filter computes.
    """

    #: Operations that narrow which source pixels or frames the graph sees.
    SOURCE_PREP = "source_prep"
    #: Frame-preserving image preparation before a signal is extracted.
    SPATIAL_PREP = "spatial_prep"
    #: Operations that turn image frames into measured signal streams.
    SIGNAL_EXTRACTION = "signal_extraction"
    #: Operations that shape an already-extracted signal over time.
    TEMPORAL_FILTER = "temporal_filter"
    #: Operations that turn tuned signals into event or gate products.
    DETECTION = "detection"


@dataclass(frozen=True, slots=True)
class CaptionPart:
    """One piece of a collapsed filter caption."""

    param: str | None = None
    label: str = ""
    text: str = ""
    format_spec: str = ""

    def __post_init__(self) -> None:
        if (self.param is None) == (self.text == ""):
            raise ValueError("a caption part names exactly one of param or text")
        if self.param is None and (self.label or self.format_spec):
            raise ValueError("static caption text cannot carry a label or format_spec")


def _empty_param_value_labels() -> Mapping[str, Mapping[str, str]]:
    return {}


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
    #: The stable authoring bucket that should offer this operation. It is
    #: presentation, not identity: labels and ordering belong to the shell, and
    #: moving a card between groups cannot change the filter's result.
    authoring_group: AuthoringGroup
    mode: Mode = Mode.STREAMING
    #: Frames the filter must consume before its output is trustworthy, counted
    #: in this filter's *input* frames — "must consume" is the unit. Warmup
    #: accumulates along the topological path feeding a request, but it does not
    #: simply sum: a rate-changing node between two others makes the two speak
    #: different index spaces. `source_warmup_frames` does the conversion, and
    #: is the only thing that should. An IIR's true warmup is infinite, so a
    #: nonzero value here is a settled-to-within-epsilon choice, with the
    #: epsilon declared beside it on the spec.
    #:
    #: **A bound, not necessarily the number a given run uses.** It is the worst
    #: case over the legal parameter range, which is the only thing statable
    #: without a configuration in hand and therefore the thing `sieve inspect`
    #: prints. A filter whose warmup *is* a parameter refines it downward by
    #: overriding `ParamsBase.warmup_frames`; `node_warmup_frames` picks between
    #: the two and refuses a refinement that exceeds this.
    #:
    #: Usually paired with `stateful` below, and deliberately not *required* to
    #: be. The claim this makes is "my first N outputs are untrustworthy", and
    #: kernel state is one way to have such outputs rather than the only one — a
    #: `WINDOWED` filter has them too, and its protocol does not exist yet.
    warmup_frames: FrameCount = NO_FRAMES
    #: Absolute tolerance for comparing two runs once this filter's warmup has
    #: elapsed. `None` means the filter has no settling claim; any nonzero
    #: `warmup_frames` must declare a value here so the generic gate can assert
    #: against data rather than a docstring sentence.
    settling_epsilon: float | None = None
    #: This filter's output is not indexed like its input — a decimator. Must
    #: agree with whether `params_model` overrides `output_rate`, and the
    #: agreement is checked below. Declaring it is not redundant with the
    #: override: the override is what computes the conversion, and this is what
    #: makes forgetting to write one an error at registration rather than a
    #: preview that renders, is under-warmed by the decimation factor, and
    #: looks entirely plausible.
    rate_changing: bool = False
    #: This filter keeps only some of the frames it is handed, and its
    #: `params_model` overrides `selected_frames` to say which. The agreement is
    #: checked below, and it is `rate_changing`'s flag for `rate_changing`'s
    #: reason: a filter that narrows the answer and forgets to declare it runs
    #: over the whole video and nothing contradicts it.
    #:
    #: **Not an axis of the declarable shape space.** `Mode`, `rate_changing`,
    #: and the stream kinds decide which kernel protocol a node needs; this
    #: decides nothing about the call, because a selecting node's kernel is
    #: handed exactly the frames every other node is handed. Which of them reach
    #: the answer is `ExecutionPlan.span`, folded before a frame is read — so
    #: there is no shape here for `unrunnable_reason` to refuse and none for
    #: `tests/unit/test_declarable_shapes.py` to walk.
    selecting: bool = False
    #: Same backend, same input, same output. Cache policy reads this fact, but
    #: the decision about whether to key the node lives in `pipeline/cache_key.py`.
    deterministic: bool = True
    #: This filter's kernel carries state across frames — a background model, an
    #: IIR, a tracker. Declared here rather than discovered from the kernel
    #: because cache policy is decided from declarations on a machine that may
    #: have no kernels installed.
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
    #: served entry would rest on an unverified warmup derivation, and the
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
    #: The collapsed caption a front end shows for a configured node.
    caption: tuple[CaptionPart, ...] = field(default_factory=tuple)
    #: Human labels for parameter values, keyed by parameter name then stored
    #: value. This is how enum choices read on buttons and captions without a
    #: GUI-side map of a filter's parameter space.
    param_value_labels: Mapping[str, Mapping[str, str]] = field(
        default_factory=_empty_param_value_labels
    )
    #: What one value of an emitted frame is a value of — a kind outright, or a
    #: relation to what arrived. Required of every array emitter and refused of
    #: every table emitter; `__post_init__` enforces both, which is what makes
    #: the default of `None` a spelling of "this emits rows" rather than a
    #: filter that forgot.
    #:
    #: **Defaulting this to `PRESERVED` is the shortcut to refuse.** It costs
    #: nothing today — every filter on the shelf that preserves would be
    #: correct by accident — and it converts the *next* element-redefining
    #: filter's omission into a silent wrong noun on a CSV column, which is the
    #: failure this field exists to close. `output_rate`'s treatment, and for
    #: `output_rate`'s reason: the declaration decides whether a detection is
    #: admissible at all, so forgetting it must be an error at registration
    #: rather than a plausible number nobody checks.
    element: ElementDeclaration | None = None
    #: Column-safe nouns for `element`, required exactly when `element` is a
    #: concrete `ElementKind`. Relation declarations preserve or lose their
    #: upstream names, so a constant here would be wrong on at least one legal
    #: input. Table emitters already name their columns in `TableSpec`.
    element_names: ElementNames | None = None

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
        if self.settling_epsilon is not None and (
            not math.isfinite(self.settling_epsilon) or self.settling_epsilon < 0.0
        ):
            raise ValueError(
                f"{self.filter_id}: settling_epsilon must be a finite non-negative number, "
                f"got {self.settling_epsilon!r}"
            )
        if self.warmup_frames.frames > 0 and self.settling_epsilon is None:
            raise ValueError(
                f"{self.filter_id}: warmup_frames={self.warmup_frames.frames} declares a "
                "settling claim, so settling_epsilon must be declared too"
            )
        if self.backend_agnostic and not self.deterministic:
            # Bit-for-bit agreement across backends is a strictly stronger
            # claim than agreement with itself on one backend. Allowing both
            # would drop backend identity from the cache key for a filter whose
            # output nothing can reproduce.
            raise ValueError(
                f"{self.filter_id}: backend_agnostic requires deterministic — a filter that "
                "cannot reproduce its own output cannot agree with another backend's"
            )
        if isinstance(self.emits, ArraySpec) and self.element is None:
            # The message carries the argument because this is where somebody
            # meets the rule: a test fixture author who wanted to register a
            # filter and got a raise wants to know why it cannot simply
            # default, and that answer lives in a completed-item entry nobody
            # is going to go and read.
            raise ValueError(
                f"{self.filter_id}: emits an array and declares no element meaning — pass "
                "element=ElementKind.PIXEL/BLOCK if this filter decides what one value is, or "
                "element=ElementRelation.PRESERVED/AGGREGATED if it relates to what it was "
                "handed. There is no default on purpose: a filter that redefines its elements "
                "and inherited PRESERVED would still register, and the only symptom is a count "
                "written to a CSV under a noun nothing checked"
            )
        if not isinstance(self.emits, ArraySpec) and self.element is not None:
            raise ValueError(
                f"{self.filter_id}: emits rows and declares element {self.element!r} — a table "
                "has columns, not elements"
            )
        if isinstance(self.element, ElementKind) and self.element_names is None:
            raise ValueError(
                f"{self.filter_id}: declares element {self.element!r} but no element_names — "
                "a filter that redefines what one value is must also declare the noun that "
                "CSV columns and plot axes use for counts over it"
            )
        if not isinstance(self.element, ElementKind) and self.element_names is not None:
            if self.element is None:
                raise ValueError(
                    f"{self.filter_id}: emits rows and declares element_names "
                    f"{self.element_names!r} — a table has columns, not element names"
                )
            raise ValueError(
                f"{self.filter_id}: declares element_names {self.element_names!r} for "
                f"{self.element!r} — relation declarations read names from their upstream"
            )
        known = set(self.params_model.model_fields)
        unknown = [name for name in self.primary_params if name not in known]
        if unknown:
            raise ValueError(
                f"{self.filter_id}: primary_params names no such field: {sorted(unknown)}"
            )
        caption_unknown = [
            part.param
            for part in self.caption
            if part.param is not None and part.param not in known
        ]
        if caption_unknown:
            raise ValueError(
                f"{self.filter_id}: caption names no such field: {sorted(caption_unknown)}"
            )
        label_unknown = [name for name in self.param_value_labels if name not in known]
        if label_unknown:
            raise ValueError(
                f"{self.filter_id}: param_value_labels names no such field: {sorted(label_unknown)}"
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
        selects = self.params_model.selected_frames is not ParamsBase.selected_frames
        if self.selecting and not selects:
            raise ValueError(
                f"{self.filter_id}: selecting is set but {self.params_model.__name__} does not "
                "override selected_frames, so nothing can say which frames it keeps and the node "
                "would narrow the answer by ALL_FRAMES — that is, not at all"
            )
        if selects and not self.selecting:
            raise ValueError(
                f"{self.filter_id}: {self.params_model.__name__} overrides selected_frames but "
                "the spec does not declare selecting, so the plan never asks and the run covers "
                "the whole video the node was written to cut down"
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


class Channel(StrEnum):
    """Which of three questions a `FilterSpec` field answers.

    REWORK.md R5 at the spec. ARCHITECTURE.md rule 7 draws one line — hashed or
    not — and that line alone cannot say why `mode` is unhashed: it is not
    *placement*, it is how the one path runs. So the non-identity side splits in
    two, and the split is what makes "core carries no GUI policy" checkable at
    all. `primary_params` is a field and not an import, so no `.importlinter`
    contract can see it; a declared partition can.
    """

    #: What the result *is*. Rule 7's hashed side. Only `filter_id` and
    #: `version` reach the digest literally — `version` stands proxy for the
    #: rest, since a filter that changes what it accepts, emits, or means by an
    #: element and keeps its version is already a defect `register_filter`
    #: cannot catch. The channel is the claim; the digest is one enforcement of
    #: it.
    IDENTITY = "identity"
    #: How the one path runs it — scheduling, lead-in, whether the answer may be
    #: reused. Never hashed, and not placement either: two builds that disagreed
    #: here would produce the same result at different cost, or refuse to
    #: produce it at all.
    EXECUTION = "execution"
    #: What a front end shows about it. Never hashed, never read by the
    #: executor, and the declared home for the hints decided 2026-07-29 —
    #: authoring groups, captions, signal labels, `primary_params`, `cost`.
    PRESENTATION = "presentation"


#: Every `FilterSpec` field, in exactly one channel. Totality and exactness are
#: both tested, in both directions, so a field added without a row here fails at
#: the moment it is written — which is what catches the next `primary_params`.
#:
#: A dict literal rather than per-field metadata on the dataclass, because the
#: property being asserted is about the *partition* and a reader checking it
#: wants the three groups side by side, not field annotations to collate.
SPEC_CHANNELS: Mapping[str, Channel] = {
    "filter_id": Channel.IDENTITY,
    "version": Channel.IDENTITY,
    "params_model": Channel.IDENTITY,
    "accepts": Channel.IDENTITY,
    "emits": Channel.IDENTITY,
    "element": Channel.IDENTITY,
    "element_names": Channel.IDENTITY,
    # Identity rather than execution, and it is the one placement worth arguing.
    # It reads as a fact about kernels, but what it decides is whether backend
    # identity leaves the digest — so it is a claim about when two results are
    # the same result, which is this channel's whole question.
    "backend_agnostic": Channel.IDENTITY,
    "authoring_group": Channel.PRESENTATION,
    "mode": Channel.EXECUTION,
    "rate_changing": Channel.EXECUTION,
    # Beside `rate_changing` and for its reason, though what the *parameters*
    # behind it decide — which frames are in the answer — is squarely identity.
    # Neither flag reaches a digest: each exists so that omitting the override it
    # names is refused at registration, which is this channel's second sentence
    # ("or refuse to produce it at all"). The hashed half is `params_model`.
    "selecting": Channel.EXECUTION,
    "warmup_frames": Channel.EXECUTION,
    "settling_epsilon": Channel.EXECUTION,
    "stateful": Channel.EXECUTION,
    "deterministic": Channel.EXECUTION,
    "cost": Channel.PRESENTATION,
    "primary_params": Channel.PRESENTATION,
    "caption": Channel.PRESENTATION,
    "param_value_labels": Channel.PRESENTATION,
    "summary": Channel.PRESENTATION,
}


#: One step of a path: a filter and the parameters it was configured with. The
#: params are not optional — half of what a step contributes is params-derived.
PathStep: TypeAlias = "tuple[FilterSpec, ParamsBase]"


def presented_param_value(
    spec: FilterSpec, params: ParamsBase, name: str, *, format_spec: str = ""
) -> str:
    """A parameter value as the filter wants it read in presentation."""
    custom = params.presentation_values()
    if name in custom:
        return custom[name]
    value = getattr(params, name)
    labels = spec.param_value_labels.get(name, {})
    key = value.value if isinstance(value, StrEnum) else str(value)
    label = labels.get(str(key))
    if label is not None:
        return label
    if format_spec:
        return format(value, format_spec)
    return str(key)


def caption_for_params(spec: FilterSpec, params: ParamsBase) -> str:
    """The declared collapsed caption for `params` under `spec`."""
    parts = spec.caption or tuple(CaptionPart(param=name) for name in spec.primary_params)
    rendered: list[str] = []
    for part in parts:
        if part.param is None:
            rendered.append(part.text)
            continue
        value = presented_param_value(spec, params, part.param, format_spec=part.format_spec)
        rendered.append(f"{part.label} {value}" if part.label else value)
    return " · ".join(piece for piece in rendered if piece)


def node_warmup_frames(step: PathStep) -> FrameCount:
    """One node's own lead-in: the refinement if it has one, else the bound.

    `FilterSpec.warmup_frames` is the worst case over the legal parameter range;
    `ParamsBase.warmup_frames` is what this configuration actually needs. Which
    of the two applies is decided here and nowhere else, so a caller holding a
    `(spec, params)` never has to know that there are two numbers.

    The override is detected by identity against the base method rather than by
    a flag on the spec, exactly as `__post_init__` detects an `output_rate`
    override — and unlike that one it is not cross-checked at registration,
    because a params model cannot be instantiated there and the check that
    matters needs a value rather than a signature.

    A refinement below zero is refused by `FrameCount` itself, at the return
    inside the filter that computed it, which is a better place to meet it than
    here — so the only check left is the one this function is the only place to
    make.

    Raises:
        ValueError: if the refinement exceeds the spec's bound. A bound is what
            `sieve inspect` prints and what a reader checks a filter's cost
            against, and a configuration quietly needing more lead-in than the
            declaration admits is the silent direction — the preview renders,
            the filter has not settled, and the tuning done against it is wrong
            rather than absent.
    """
    spec, params = step
    if type(params).warmup_frames is ParamsBase.warmup_frames:
        return spec.warmup_frames
    refined = params.warmup_frames()
    if refined > spec.warmup_frames:
        raise ValueError(
            f"{spec.filter_id}: {type(params).__name__}.warmup_frames() returned {refined}, "
            f"which exceeds the spec's declared bound of {spec.warmup_frames} — the bound is the "
            "worst case over the legal parameter range and a configuration may only refine it "
            "downward"
        )
    return refined


def input_warmup_frames(step: PathStep, output_warmup: FrameCount) -> FrameCount:
    """One node's conversion: lead-in at its input, given lead-in at its output.

    The single edge of the warmup arithmetic. `output_warmup` frames wanted at
    this node's output cost `FrameCount.at_input_of` at its input, and the
    node's own warmup is already denominated there, so it adds on top.

    Extracted from `source_warmup_frames` rather than inlined in it because a
    DAG walk needs the step without the path: `pipeline/plan.py` folds this over
    a topological order, taking the maximum over a node's downstreams instead of
    over enumerated paths. Two implementations of one conversion is exactly what
    that function's docstring argues against, so there is one and both call it.

    **Monotone non-decreasing in `output_warmup`**, and that is load-bearing
    rather than incidental: `at_input_of` and `+` are both monotone, so the maximum
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
            mean an output frame no quantity of input could supply; or if its
            warmup refinement is not within its declared bound.
    """
    spec, params = step
    rate = params.output_rate()
    if rate <= 0:
        raise ValueError(f"{spec.filter_id}: output_rate must be positive, got {rate}")
    return output_warmup.at_input_of(rate) + node_warmup_frames(step)


def source_warmup_frames(path: Sequence[PathStep]) -> FrameCount:
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
    need = NO_FRAMES
    for step in reversed(path):
        need = input_warmup_frames(step, need)
    return need
