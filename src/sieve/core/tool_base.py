"""The tool contract, as data: `ToolSpec`, `ParamsBase`, `ArraySpec`, `Mode`.

Nothing in this module executes a tool, and that is the point. A saved
pipeline names tools by id and version; validating its structure — that the
graph is acyclic, that each edge's types chain, that every parameter is known —
must work on a machine with no codec and none of the tools installed. Splitting
the spec from the kernels is what buys that: a tool's `run` lives beside its
spec in `sieve.tools`, free to import cv2, while this layer stays pure. The
spec *points* at that function (`ToolSpec.run`, `adr/no-kernel-apparatus.md`)
and this module imports none of them — a pointer set by the tool module on its
way onto the shelf costs this layer nothing, and it is what lets the executor
call a node without knowing which tool it is.

The spec is also the single source of truth for a tool's parameters. GUI
widgets, CLI flags, YAML, and the cache key all read `params_model`; none of
them carries a second copy of the field list that could drift from it.

**Four declarations are params-derived rather than constants**, because the
quantity they describe *is* a parameter: a decimator's factor, a window's
length, a span's bounds. `output_rate`, `warmup_frames`, `lookahead_frames` and
`selected_frames` are therefore methods on `ParamsBase`, not (only) fields on
`ToolSpec`. They stay pure — data in, exact number out, no kernel, no codec —
so `dag.py` and the executor can evaluate them on a machine with nothing
installed, which is the property the whole split exists to preserve.

They are params-derived in two different *shapes*, and the difference is about
what a wrong answer costs. `output_rate` and `selected_frames` are cross-checked
against a spec flag, because forgetting to declare a decimation or a selection
is silent and wrong. `warmup_frames` is looser: the spec field is the *bound* —
the worst case over the legal parameter range, which is what `sieve inspect` can
print without a configuration in hand — and the method is this configuration's
actual need, which may refine the bound downward but never exceed it.
`node_warmup_frames` enforces that, and the asymmetry is the point: a refinement
that is too small under-warms a tool silently, and a bound that is too large
only wastes decode.

How many frames is only half of what a warmup declares. `warmup_kind` is the
other half — whether those frames *determine* the output or only settle it —
and it is a constant on the spec rather than a method because no parameter
changes the answer: a window is exact at every length and an EMA is
approximate at every alpha. `pipeline/cache_key.py` is its consumer
(`adr/cache-admission-is-bounded-warmup.md`).

`lookahead_frames` is `warmup_frames`' shape on the other side of the frame
being emitted, and the two together are the first statement of a window this
contract can make: a centred window of length `2k+1` is `k` of lead-in and `k`
of lookahead. v2 could say only the first half, which is why the detector —
tuned against a centred result — could not be a node at all
(`adr/detector-is-a-node.md`). It carries `warmup_frames`' bound/refinement
discipline through `node_lookahead_frames`, plus one cross-check warmup does not
need: `Mode.STREAMING` and a nonzero lookahead contradict each other outright,
since a node that emits on consumption has no later frame to have read.

`param_stereotypes` is the one declaration here whose consumer does not exist
yet: how each parameter is populated, read by Phase 7's widget generator and by
nothing before it. It is admitted early under the single shape
`adr/declared-means-verified.md` licenses — the vocabulary is closed, the map is
total over `params_model`, and both are refused by name at registration, so the
check is the consumer until the generator is.

`emissions` is the one declaration here that says something `emits` cannot:
which *products* a tool can be configured to compute, where `emits` types the
single stream one node produces. VISION's save screen offers all the possible
outputs of a graph, so the list has to be over the legal parameter range rather
than over the run that has just finished — by then the screen has been drawn.
It is checkable because a product is something a user picks: a multi-product
tool names the parameter that picks it, and the list must be exactly that
parameter's values, both directions refused. `sieve inspect` prints it, which
is the reader that keeps it from being a Phase-7 declaration nobody has read
(`adr/declared-means-verified.md`).

v2's fourth params-derived declaration, `frame_bytes_ratio`, is cut here with
`CostEstimate` and `backend_agnostic`: each fed machinery v3 has not built, and
a declaration with no consumer is refused rather than stored
(`adr/declared-means-verified.md`). So is the merging protocol — `accepts` is
one stream, not a mapping of ports — which returns with the first two-input
tool.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from typing import Any, ClassVar, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

from sieve.core.types import NO_FRAMES, ChannelSpec, Frame, FrameCount, FrameSpan

#: `MAJOR.MINOR.PATCH`, no pre-release or build metadata. A tool version is
#: an input to a cache key before it is a human-facing label, and `1.0.0-rc1`
#: vs `1.0.0` is an ordering question with no answer this system needs to have.
#:
#: Public because `pipeline_model` validates the same two strings on the way in
#: from YAML. That is not registry awareness — it never asks whether the tool
#: exists — but it is the same syntactic contract, and a second copy of the
#: regex is a second thing to keep in step.
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

#: Lowercase identifier. It appears in cache keys, YAML, and CLI arguments, so
#: it may not depend on case folding or shell quoting to stay itself. The
#: *values* it admits are v2's unchanged — only the field's name renamed
#: (`adr/tools-not-filters.md`).
TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class Mode(StrEnum):
    """Whether a tool can emit a frame as soon as it has consumed one."""

    #: One frame in, one frame out, in order. The executor may pipeline it.
    STREAMING = "streaming"
    #: Needs a span of frames before it can emit any of them. The executor
    #: must accumulate the window rather than hand frames through singly.
    WINDOWED = "windowed"


class WarmupKind(StrEnum):
    """What a tool's declared `warmup_frames` is a claim *about*.

    `warmup_frames` says how many frames must precede a trustworthy output. It
    does not say whether those frames are the whole of what the output depends
    on, and that is a different question with a different consumer: the first is
    how much lead-in to decode, the second is whether the output may be stored
    and handed to a run that started somewhere else
    (`adr/cache-admission-is-bounded-warmup.md`).

    v3 read `stateful` for the second question until 06.5, and one bit was
    standing for both properties — `block_signal` keeps a frame of state and is
    exactly determined by two frames, while an EMA keeps the same kind of state
    and is determined by all of them. This axis is the one that separates them,
    and it is declared rather than inferred for `stateful`'s own reason: the
    policy is decided on a machine that may have no tools installed.
    """

    #: Output at frame `N` is fully determined by the last `warmup_frames + 1`
    #: input frames (plus `lookahead_frames` after it, where a window has a far
    #: side). Two runs that both reach `N` with that window filled agree
    #: exactly, so an entry keyed on the node and the frame index stands.
    BOUNDED = "bounded"
    #: The dependence on where the run began decays rather than ending, and
    #: `warmup_frames` is where it drops below `settling_epsilon`. Two runs
    #: agree to within that tolerance and not bit-for-bit, so nothing may serve
    #: one run's frame to another.
    EPSILON = "epsilon"


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
    `ArraySpec(dtypes=("float32",))`. A third member arrives with the tool
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
    writer can safely invent. They follow the tool-id spelling rule so a name
    can be composed into a stable column without quoting or case folding.
    """

    singular: str
    plural: str

    def __post_init__(self) -> None:
        bad = [name for name in (self.singular, self.plural) if not TOOL_ID_PATTERN.match(name)]
        if bad:
            raise ValueError(
                f"element names must match {TOOL_ID_PATTERN.pattern!r}, got {sorted(bad)}"
            )


#: What the decoded source contributes before any tool has redefined it.
#: Roots that preserve their input read this value; tools that redefine
#: elements declare their own `element_names`.
SOURCE_ELEMENT_NAMES = ElementNames("pixel", "pixels")


class ElementRelation(StrEnum):
    """What a tool does to the element meaning it was handed.

    A sibling of `ElementKind` rather than more members on it, because these
    are not answers to "what is one value of" — they are relations between a
    tool's input and its output, and a tool that preserves has no constant
    to declare. `temporal_baseline` is why this axis exists at all: it accepts
    any array and estimates per cell, so it emits blocks over `block_signal`
    and pixels over a raw frame, and any constant it declared would be a lie in
    one of the two positions.
    """

    #: One output element is one input element, whatever that was. The per-cell
    #: and per-pixel tools: `normalize`, `background_ema`, `motion_history`,
    #: `temporal_baseline`.
    PRESERVED = "preserved"
    #: One output element is *many* input elements, spatially. `downsample` and
    #: `rescale`. Kind-dependent rather than simply destructive, and the
    #: asymmetry is the point: a mean of pixels is still a sample of the scene
    #: at a coarser spacing, so `PIXEL` survives; a mean of blocks is not a
    #: block, because a block is already an aggregate and re-aggregating it
    #: leaves a quantity no count threshold is denominated in.
    AGGREGATED = "aggregated"


#: What a tool declares about its output's elements: a kind outright, or a
#: relation to its input's. A union rather than one enum with four members so
#: that the *resolved* answer has a type of its own — `ElementKind | None` is
#: what a walk produces and what a consumer may read, and `PRESERVED` must not
#: be assignable to it. The narrowing goes through `isinstance`, which is what
#: a type checker can follow, exactly as `StreamSpec`'s does.
type ElementDeclaration = ElementKind | ElementRelation


def node_element(
    declaration: ElementDeclaration | None, upstream: ElementKind | None
) -> ElementKind | None:
    """One node's element meaning, given its input's. `None` is *undeclarable*.

    The single-node conversion, kept here beside the declaration that defines
    it while the walk that supplies `upstream` lives in `pipeline/dag.py` —
    `input_warmup_frames` and `plan.py`'s fold are the same split for the same
    reason, and a second implementation of the conversion is what that
    arrangement exists to prevent.

    `None` propagates and never recovers: a tool downstream of a node whose
    elements have no meaning cannot give them one back by preserving them.

    **`AGGREGATED` defaults over `ElementKind`, and the polarity is the whole
    reason that is allowed.** `ToolSpec.element` refuses a default because an
    omission there resolves to a confident wrong noun; the branch below names
    `PIXEL` and sends every other kind to `None`, so a third `ElementKind`
    member added tomorrow is *refused* under aggregation until somebody decides
    what a mean of one means. Fails closed rather than open, which is the only
    kind of default this file has any business carrying.

    Args:
        declaration: `ToolSpec.element`. `None` only for a table emitter,
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

    A tool that declares a concrete `ElementKind` introduces the noun beside
    that declaration. A preserving tool preserves the noun it was handed. An
    aggregating tool keeps names only in the same case `node_element` keeps
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


#: Rate `1`, allocated once. `Fraction` is immutable, so every unchanged tool
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
#: be one name with two homes and nothing to show for it.
ALL_FRAMES = range(UNBOUNDED_FRAME)


class ParamsBase(BaseModel):
    """Base for every tool's parameter model.

    Frozen because a params object is an identity: something that has been
    hashed into a cache key must not then change underneath the entry. Extra
    fields are forbidden because the alternative is silent — a YAML with a
    misspelled parameter would otherwise validate, run with the default, and
    produce a cache key identical to the run the user meant to vary.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Set by `tool_registry.register_tool` when this model is decorated.
    #: `None` on a params model that was declared without one, which is legal
    #: — a test fixture, or a base another tool's params inherit from.
    __tool_spec__: ClassVar[ToolSpec | None] = None

    @classmethod
    def spec(cls) -> ToolSpec:
        """This model's registered spec, or refuse.

        The narrowing every caller was writing by hand. `__tool_spec__` is
        legitimately optional — a test fixture or a shared base has none — but
        almost nobody who reaches for it wants the `None`: a registry and a test
        both want the spec or a clear failure, and each was spelling that out
        again with a slightly different message.

        Raises:
            TypeError: if this model carries no spec, meaning it was never
                decorated with `@register_tool`.
        """
        if cls.__tool_spec__ is None:
            raise TypeError(
                f"{cls.__name__} has no tool spec: it was never decorated with @register_tool, "
                "so it has no id, version, or declared I/O"
            )
        return cls.__tool_spec__

    def canonical_json(self) -> str:
        """Byte-stable JSON of these params, for hashing.

        `mode="json"` so enums and paths become the same strings they became in
        the artifact, sorted keys so the string does not depend on field
        declaration order, and no whitespace because a hash input is not read
        by anyone.
        """
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def presentation_values(self) -> Mapping[str, str]:
        """Parameter display values that need tool-owned derivation.

        Most parameters render from their stored value, optionally through the
        spec's `param_value_labels`. A tool overrides this only when the
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

        Overridden by any tool whose output stops being indexed like its
        input — a 10:1 decimator returns `Fraction(1, 10)`. Overriding it
        obliges the spec to set `rate_changing=True`; `ToolSpec` refuses the
        pair otherwise, because the failure this closes is a decimator that
        simply forgot to say so, and that failure is silent.

        A tool that consumes frames and emits a table still has a rate: rows
        per input frame is not what this measures, and such a tool leaves it
        at 1 unless it also drops frames. Downstream of a table there is
        nothing left to warm up.
        """
        return UNCHANGED_RATE

    def selected_frames(self) -> range:
        """Which frames this configuration keeps, half-open, in its input space.

        `output_rate`'s treatment for the other way a tool can emit fewer
        frames than it consumed. A rate change is uniform and reindexes — every
        tenth frame, and the tenth output *is* the hundredth input — so it is
        arithmetic the warmup fold has to cross. A selection is neither: the
        frames that survive keep their numbering, and what changes is only which
        of them are in the answer at all.

        Overriding it obliges the spec to set `selecting=True`, which
        `ToolSpec` refuses the pair without, for `output_rate`'s reason: a
        tool that narrows the answer and forgets to say so would be run over
        the whole video and its declaration would be the only evidence.

        **Denominated in this tool's input space, which is the source's** for as
        long as no runnable kernel changes the rate. A selection downstream of a
        decimator stops meaning the same thing as one at the root, and
        `plan._selected` is what has to convert on the day one exists.

        Returns:
            The kept range. `ALL_FRAMES` — the default, never overridden by most
            tools — is "all of them", a value rather than an absence, so no
            `range | None` propagates into the plan.
        """
        return ALL_FRAMES

    def warmup_frames(self) -> FrameCount:
        """Frames *this configuration* must consume before its output is good.

        A refinement of `ToolSpec.warmup_frames`, which is the worst case over
        the whole legal parameter range. Overriding is optional and the default
        here is never read — `node_warmup_frames` takes the spec's number unless
        an override exists — so a tool whose warmup is genuinely a constant
        declares it once, on the spec, and nothing else.

        **What it buys, and why it is not a nicety.** A static declaration has
        to be true for every setting of every parameter, so a tool whose
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

        `ToolSpec.warmup_frames` is derived from this class-level answer
        because the bound changes with the parameter model's own legal range.
        The instance method above refines the same quantity for one
        configuration.
        """
        return NO_FRAMES

    def lookahead_frames(self) -> FrameCount:
        """Frames *after* its target this configuration must have in hand.

        `warmup_frames` on the other side of the frame being emitted, and the
        two together are the whole of a window's shape: a centred window of
        length `2k+1` is `k` of lead-in and `k` of lookahead, which is what
        v2's trailing-only contract had no way to say. The detector was tuned
        against the centred result (`adr/detector-is-a-node.md`), so the
        missing half was not a refinement of the contract but the thing that
        kept the tool out of the graph.

        Refines `ToolSpec.lookahead_frames` exactly as `warmup_frames` refines
        its bound, and `node_lookahead_frames` picks between the two. Costs
        latency rather than decode: the executor cannot emit the frame at `i`
        until it has read `i + lookahead`, so a bound charged to every run
        would delay every preview by the widest window the model admits.
        """
        return NO_FRAMES

    @classmethod
    def max_lookahead_frames(cls) -> FrameCount:
        """Worst-case lookahead over this params model's legal range.

        `max_warmup_frames`' treatment for the other half of the window, and
        for its reason: the bound is a fact about the parameter model's legal
        range, so the model states it and the decorator reads it rather than a
        tool author writing it a second time in the decoration.
        """
        return NO_FRAMES


@dataclass(frozen=True, slots=True)
class ArraySpec:
    """What a tool consumes or produces, declared narrowly enough to reject.

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
    enough information to stick it into R" as a first-class output, so this is a
    stream the graph carries rather than only a thing a sink writes.

    `columns` is conjunctive where `ArraySpec`'s sets are disjunctive, and the
    difference is not an oversight. A tool listing `("uint8", "float32")`
    accepts *either*; a tool listing `("x", "y")` needs *both*, because a
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
#: One input stream and one output stream per node. v2 grew input *ports* for a
#: merging step; that protocol is cut here and returns with the first two-input
#: tool, which is also when the artifact has to learn which port an edge feeds.
type StreamSpec = ArraySpec | TableSpec


@dataclass(frozen=True, slots=True)
class Emission:
    """One product a node of this tool can be asked to keep.

    `emits` types the single stream a node produces; this names the products
    *behind* it, which is the list VISION's save screen offers — all the
    possible outputs, over the whole legal parameter range rather than the one
    a given run happened to compute. Nothing else in the spec can state it: a
    run knows which product it made, and by then the screen has been drawn.

    The test a tool author repeats is whether two settings compute different
    things or one thing two ways. `block_signal`'s four signals are four
    measurements of one tensor and are four emissions; `downsample`'s area and
    stride are one downsampled frame reached differently and are one.

    `selected_by` names the parameter whose value chooses among them, and
    `name` *is* that value rather than a second spelling of it — a separate
    label is a thing that can disagree with the enum the user actually sets,
    and the human reading of it already lives in `param_value_labels`. `None`
    on a tool with a single product, which has nothing to choose.
    """

    name: str
    selected_by: str | None = None

    def __post_init__(self) -> None:
        if not TOOL_ID_PATTERN.match(self.name):
            raise ValueError(
                f"emission name must match {TOOL_ID_PATTERN.pattern!r}, got {self.name!r} — "
                "it becomes a file name and a CSV column, so it may not depend on case folding "
                "or shell quoting to stay itself"
            )


@dataclass(frozen=True, slots=True)
class CaptionPart:
    """One piece of a collapsed tool caption."""

    param: str | None = None
    label: str = ""
    text: str = ""
    format_spec: str = ""

    def __post_init__(self) -> None:
        if (self.param is None) == (self.text == ""):
            raise ValueError("a caption part names exactly one of param or text")
        if self.param is None and (self.label or self.format_spec):
            raise ValueError("static caption text cannot carry a label or format_spec")


class ParamStereotype(StrEnum):
    """How a parameter is populated — the vocabulary a widget generator reads.

    Qt-free by construction: a stereotype names the *kind of population* a value
    has, not a control. Phase 7's generator maps a kind to a widget and a
    handoff surface — a `REGION` gets the canvas draw, a `SPAN` gets timeline
    handles — and it is that one mapping, rather than a branch on `tool_id`,
    that lets a tool arrive with no GUI code at all
    (`adr/gui-knows-kinds-not-tools.md`).

    The vocabulary is closed, and closing it is the whole asymmetry: tools grow
    fast because kinds grow slowly, so a sixth member is a deliberate decision
    forced by a tool that cannot be expressed in five, not a place to put a
    tool's own presentation. Until that generator exists, `ToolSpec` refusing an
    unknown kind by name is what stands in as the consumer
    (`adr/declared-means-verified.md`).
    """

    #: One number within declared bounds. Spinbox, slider, or both.
    SCALAR_RANGE = "scalar-range"
    #: One of a fixed set of choices, read through `param_value_labels`.
    ENUM = "enum"
    #: A half-open interval of frames or time.
    SPAN = "span"
    #: A rectangle in the frame the node is handed, e.g. `crop`'s `ROI`.
    REGION = "region"
    #: A single location in the frame — what a stamp tool would declare.
    POINT = "point"


#: Contravariant because a `run` is *consumed* with params: a function written
#: against `DownsampleParams` is a legal `ToolRun` wherever one taking a narrower
#: params type is expected, and a spec stores them all as `ToolRun[Any, Any]`.
ParamsT_contra = TypeVar("ParamsT_contra", bound=ParamsBase, contravariant=True)

#: Whatever a stateful tool's factory returns. Unbounded on purpose: nothing
#: outside the tool inspects it, and requiring a base class would make every
#: tool's private scratch space a public type in this module.
StateT_contra = TypeVar("StateT_contra", contravariant=True)


class ToolRun(Protocol[ParamsT_contra, StateT_contra]):
    """The one signature (`adr/no-kernel-apparatus.md`): params, window, state.

    One shape for every tool, so that which shape a node gets is not a thing the
    executor decides per tool. v2 had four protocols and used three of them, and
    the three differ only in which of these three arguments they read
    (`findings/2026.08.06-v2-kernel-shape-census.md`); the variability was
    designed capacity rather than observed need, and what it cost was a dispatch
    layer between the spec and the call.

    `window` is a `FrameSpan` even where it holds one frame. A streaming tool
    reads `window.target` and is handed exactly that; a windowed tool is handed
    the frames its declared window reaches, oldest first.

    **The frame a windowed tool emits for is not always `window.target`.** With
    a declared `lookahead_frames` of `k` the executor hands over a window whose
    last `k` frames are *past* the target, so the target sits at
    `window[len(window) - 1 - k]` — the tool knows `k`, because `params` is the
    configuration it was derived from. `target` stays the last frame because a
    span is also what a trailing window is, and the executor checks the index
    that comes back either way.

    `state` is `None` for a tool that keeps none, and otherwise whatever
    `ToolSpec.state_factory` made for *this run* — never something the tool
    closes over, since two concurrent previews of one node are two runs.

    Positional-only: the executor calls every tool identically, and parameter
    *names* would otherwise become part of a contract every tool author has to
    match.
    """

    def __call__(
        self, params: ParamsT_contra, window: FrameSpan, state: StateT_contra, /
    ) -> Frame: ...


def _empty_param_value_labels() -> Mapping[str, Mapping[str, str]]:
    return {}


def _empty_param_stereotypes() -> Mapping[str, ParamStereotype]:
    return {}


def _closed_values(annotation: object) -> set[str] | None:
    """The values a parameter can take, or `None` if it has no closed set.

    A `StrEnum` is the only annotation this asks about, because it is the only
    one whose members are both enumerable and *stored* as the strings a saved
    document and an emission name are written in.
    """
    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        return {member.value for member in annotation}
    return None


def _check_emissions(
    tool_id: str, emissions: tuple[Emission, ...], params_model: type[ParamsBase]
) -> None:
    """Refuse an emission list that does not describe what the tool produces.

    The list's whole value is that a save screen reading it cannot lie, so both
    directions are errors: an emission no setting of the tool produces would put
    a checkbox in front of a user that never fills, and a product the list omits
    is an output they are never offered. Neither has a symptom anywhere else —
    the run computes what it was configured to compute either way.

    Checkable only against a parameter with a closed set of values, which is why
    a multi-product tool must name one. That is not a restriction on tools so
    much as a restatement of what a product *is* here: something a user selects,
    saves in the document, and can therefore be offered.

    Raises:
        ValueError: for an empty list, a repeated name, more than one selecting
            parameter, several products with nothing selecting between them, a
            selector that is not a field or not an enumerated one, or a list
            that is not exactly that selector's values.
    """
    if not emissions:
        raise ValueError(
            f"{tool_id}: declares no emission — name every product a node of this tool can be "
            "asked to keep, which for most tools is the one thing it computes. There is no "
            "default on purpose: a tool computing four signals that inherited one would still "
            "register, and the only symptom is a save screen offering three outputs fewer than "
            "the tool has"
        )
    seen: set[str] = set()
    for emission in emissions:
        if emission.name in seen:
            raise ValueError(f"{tool_id}: declares emission {emission.name!r} twice")
        seen.add(emission.name)
    selectors = {emission.selected_by for emission in emissions}
    if len(selectors) > 1:
        named = sorted(str(selector) for selector in selectors)
        raise ValueError(
            f"{tool_id}: emissions are selected by {named} — one parameter chooses which product "
            "leaves the node, and two would make the emission set their cross product, which "
            "nothing declares and a screen would have to invent"
        )
    selector = selectors.pop()
    if selector is None:
        if len(emissions) > 1:
            raise ValueError(
                f"{tool_id}: declares {len(emissions)} emissions and nothing chooses between "
                "them — a node emits one stream, so name the parameter whose value selects the "
                "product, or declare the one product this tool has"
            )
        return
    field = params_model.model_fields.get(selector)
    if field is None:
        raise ValueError(f"{tool_id}: emissions name no such field: {selector!r}")
    values = _closed_values(field.annotation)
    if values is None:
        raise ValueError(
            f"{tool_id}: emissions are selected by {selector!r}, which is not a closed set of "
            "values — a product is something a user picks and saves, so the parameter that "
            "picks it enumerates its choices or the list is checkable against nothing"
        )
    never = sorted(seen - values)
    if never:
        raise ValueError(
            f"{tool_id}: declares {never}, which this tool never produces — the list is exactly "
            f"the values {selector!r} can take"
        )
    unoffered = sorted(values - seen)
    if unoffered:
        raise ValueError(
            f"{tool_id}: {selector!r} can be set to {unoffered}, which is offered by no emission "
            "— the screen shows all the possible outputs, so a product missing from the list is "
            "one nobody can ask to keep"
        )


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Everything about a tool that is knowable without running it."""

    tool_id: str
    version: str
    summary: str
    params_model: type[ParamsBase]
    accepts: StreamSpec
    emits: StreamSpec
    #: Every product a node of this tool can be asked to keep, in the order a
    #: reader should meet them. Required, with no default, for `element`'s
    #: reason: a default of one emission would be right for every single-product
    #: tool on the shelf today and would turn the next `block_signal`'s omission
    #: into a save screen offering one output where the tool has four — a list
    #: short by three, which is exactly the lie the declaration exists to close
    #: and the one nothing downstream can detect.
    #:
    #: Both ways it can stop being true are refused below: an emission no
    #: setting produces, and a product the list does not offer.
    emissions: tuple[Emission, ...]
    #: What computes this tool's output, or `None` for a spec nothing can run.
    #: The spec points at the function and the executor calls it, which is what
    #: keeps the executor from growing a branch per tool
    #: (`adr/no-kernel-apparatus.md`).
    #:
    #: Optional because a spec is legitimately declarable without one — every
    #: graph test in this repo builds specs it never executes, and `sieve
    #: inspect` reads a shelf on a machine where the reason to have loaded a
    #: `run` does not exist. What makes that safe rather than silent is that the
    #: executor refuses the node by name before it reads a frame: a spec with no
    #: `run` is unrunnable in exactly the way a table emitter is, and both are
    #: answered up front.
    #:
    #: 01.2 cut this field and was right to on its own terms — its only reader
    #: is the executor, and `adr/declared-means-verified.md` refuses a
    #: declaration whose consumer is two phases out. The reader exists now, and
    #: the alternative to the field is the executor finding a tool's `run` by
    #: its id, which is the file-that-grows-with-the-tool-count ADR-2 exists to
    #: prevent.
    run: ToolRun[Any, Any] | None = None
    mode: Mode = Mode.STREAMING
    #: Frames the tool must consume before its output is trustworthy, counted
    #: in this tool's *input* frames — "must consume" is the unit. Warmup
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
    #: prints. A tool whose warmup *is* a parameter refines it downward by
    #: overriding `ParamsBase.warmup_frames`; `node_warmup_frames` picks between
    #: the two and refuses a refinement that exceeds this.
    #:
    #: Usually paired with `stateful` below, and deliberately not *required* to
    #: be. The claim this makes is "my first N outputs are untrustworthy", and
    #: kernel state is one way to have such outputs rather than the only one — a
    #: `WINDOWED` tool has them too.
    warmup_frames: FrameCount = NO_FRAMES
    #: What that warmup is a claim about — see `WarmupKind`. Required of any
    #: tool that has something to settle (a nonzero warmup, or state), refused
    #: of one that has not, and read by `pipeline/cache_key.cache_policy` to
    #: decide whether the node may be keyed at all.
    #:
    #: No default in either direction, for `element`'s reason. `BOUNDED` by
    #: default would key the next EMA that forgot to say so, and its output at a
    #: frame would be served to a run that started somewhere else — a
    #: well-formed key, a plausible frame, and no symptom. `EPSILON` by default
    #: would be safe and silently uncacheable, which is the failure this whole
    #: axis exists to stop being invisible.
    warmup_kind: WarmupKind | None = None
    #: Absolute tolerance for comparing two runs once this tool's warmup has
    #: elapsed. `None` means the tool has no settling claim; any nonzero
    #: `warmup_frames` must declare a value here so the generic gate can assert
    #: against data rather than a docstring sentence.
    settling_epsilon: float | None = None
    #: Frames past its target this tool must have in hand before it may emit,
    #: counted in this tool's *input* frames — `warmup_frames`' unit, on the
    #: other side of the frame. A bound over the legal parameter range for
    #: `warmup_frames`' reason, refined per configuration by
    #: `ParamsBase.lookahead_frames`, and chosen between by
    #: `node_lookahead_frames`.
    #:
    #: Refused below on a spec whose `mode` has no window. A `STREAMING` node
    #: emits a frame as soon as it has consumed one, so there is no later frame
    #: it could have read and nothing for the executor to delay — the pair
    #: would declare a centred window and run trailing, which is precisely the
    #: silence this field was added to break.
    lookahead_frames: FrameCount = NO_FRAMES
    #: This tool's output is not indexed like its input — a decimator. Must
    #: agree with whether `params_model` overrides `output_rate`, and the
    #: agreement is checked below. Declaring it is not redundant with the
    #: override: the override is what computes the conversion, and this is what
    #: makes forgetting to write one an error at registration rather than a
    #: preview that renders, is under-warmed by the decimation factor, and
    #: looks entirely plausible.
    rate_changing: bool = False
    #: This tool keeps only some of the frames it is handed, and its
    #: `params_model` overrides `selected_frames` to say which. The agreement is
    #: checked below, and it is `rate_changing`'s flag for `rate_changing`'s
    #: reason: a tool that narrows the answer and forgets to declare it runs
    #: over the whole video and nothing contradicts it.
    #:
    #: **Not an axis of the declarable shape space.** `Mode` and the stream
    #: kinds decide which call shape a node needs; this decides nothing about
    #: the call, because a selecting node's `run` is handed exactly the frames
    #: every other node is handed. Which of them reach the answer is
    #: `ExecutionPlan.span`, folded before a frame is read.
    selecting: bool = False
    #: Same input, same output. Cache policy reads this fact, but the decision
    #: about whether to key the node lives in `pipeline/cache_key.py`.
    deterministic: bool = True
    #: This tool's `run` carries state across frames — a background model, an
    #: IIR, a tracker. Declared here rather than discovered from the kernel
    #: because cache policy is decided from declarations on a machine that may
    #: have no tools installed.
    #:
    #: **It does not decide the cache**, and reading it that way is the mistake
    #: `adr/cache-admission-is-bounded-warmup.md` names: whether a run may be
    #: handed another run's frame is a question about how far back the output
    #: depends, and keeping state is one way to have a short dependence as well
    #: as the only way to have an unbounded one. `warmup_kind` is that question;
    #: this one is read by the executor, which mints a state per run from
    #: `state_factory` and re-settles it over `warmup_frames` when a served
    #: range leaves it behind.
    stateful: bool = False
    #: How to make one run's state, or `None` for a tool that keeps none. The
    #: executor mints state per run from this rather than the tool closing over
    #: it, so two concurrent previews of one node are two independent runs
    #: (`adr/no-kernel-apparatus.md`).
    #:
    #: Refused below on a spec that does not declare `stateful`, which is what
    #: gives this field a consumer at registration time rather than only in the
    #: executor. A tool that kept state behind a spec that did not say so would
    #: be run by a loop that never re-settles it, so a range served from the
    #: store would leave the state having seen everything except the frames the
    #: store answered for — and the frame after it would be computed from that.
    state_factory: Callable[[], Any] | None = None
    #: The one to three parameters the GUI shows before "Advanced". Names must
    #: exist on `params_model`; that is checked below, because the failure mode
    #: of a stale name is a widget that silently stops appearing.
    primary_params: tuple[str, ...] = field(default_factory=tuple)
    #: The collapsed caption a front end shows for a configured node.
    caption: tuple[CaptionPart, ...] = field(default_factory=tuple)
    #: Human labels for parameter values, keyed by parameter name then stored
    #: value. This is how enum choices read on buttons and captions without a
    #: GUI-side map of a tool's parameter space.
    param_value_labels: Mapping[str, Mapping[str, str]] = field(
        default_factory=_empty_param_value_labels
    )
    #: How each parameter is populated, one entry per field of `params_model`.
    #: Total rather than optional, and checked below: an omitted field is one
    #: the Phase-7 generator emits no widget for, which is `primary_params`'
    #: failure mode — a control that silently is not on the panel — reached by
    #: forgetting rather than by a rename.
    #:
    #: A mapping on the spec rather than metadata on the pydantic field, for
    #: `SPEC_CHANNELS`' reason: presentation policy in `core` is only checkable
    #: while it is a `ToolSpec` field the partition can name. A hint tucked into
    #: `Field(json_schema_extra=...)` would be invisible to it.
    param_stereotypes: Mapping[str, ParamStereotype] = field(
        default_factory=_empty_param_stereotypes
    )
    #: What one value of an emitted frame is a value of — a kind outright, or a
    #: relation to what arrived. Required of every array emitter and refused of
    #: every table emitter; `__post_init__` enforces both, which is what makes
    #: the default of `None` a spelling of "this emits rows" rather than a
    #: tool that forgot.
    #:
    #: **Defaulting this to `PRESERVED` is the shortcut to refuse.** It costs
    #: nothing today — every tool on the shelf that preserves would be
    #: correct by accident — and it converts the *next* element-redefining
    #: tool's omission into a silent wrong noun on a CSV column, which is the
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
        if not TOOL_ID_PATTERN.match(self.tool_id):
            raise ValueError(
                f"tool_id must match {TOOL_ID_PATTERN.pattern!r}, got {self.tool_id!r}"
            )
        if not SEMVER_PATTERN.match(self.version):
            raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {self.version!r}")
        if self.settling_epsilon is not None and (
            not math.isfinite(self.settling_epsilon) or self.settling_epsilon < 0.0
        ):
            raise ValueError(
                f"{self.tool_id}: settling_epsilon must be a finite non-negative number, "
                f"got {self.settling_epsilon!r}"
            )
        if self.warmup_frames.frames > 0 and self.settling_epsilon is None:
            raise ValueError(
                f"{self.tool_id}: warmup_frames={self.warmup_frames.frames} declares a "
                "settling claim, so settling_epsilon must be declared too"
            )
        settles = self.warmup_frames.frames > 0 or self.stateful
        if settles and self.warmup_kind is None:
            raise ValueError(
                f"{self.tool_id}: has a warmup to declare (warmup_frames="
                f"{self.warmup_frames.frames}, stateful={self.stateful}) and no warmup_kind — "
                "say whether those frames fully determine the output "
                "(WarmupKind.BOUNDED) or only settle it to within settling_epsilon "
                "(WarmupKind.EPSILON). Cache admission reads this and nothing else, so an "
                "omission is a node that is either wrongly served across runs or wrongly "
                "recomputed on every one"
            )
        if not settles and self.warmup_kind is not None:
            raise ValueError(
                f"{self.tool_id}: declares warmup_kind={self.warmup_kind.value} with nothing to "
                "settle — a tool with no warmup and no state is determined by the frame in front "
                "of it, and a kind here would be a claim with no subject"
            )
        _whole_lookahead(self.tool_id, self.lookahead_frames, "lookahead_frames")
        if self.lookahead_frames.frames > 0 and self.mode is not Mode.WINDOWED:
            raise ValueError(
                f"{self.tool_id}: declares lookahead_frames={self.lookahead_frames.frames} but "
                f"mode is {self.mode.value} — a streaming node emits a frame as soon as it has "
                "consumed one, so there is no later frame it could have read; declare "
                "mode=Mode.WINDOWED if this tool's output at a frame depends on frames after it"
            )
        if self.state_factory is not None and not self.stateful:
            raise ValueError(
                f"{self.tool_id}: declares a state_factory but not stateful=True, so "
                "cache_key.py would give the node a key and serve its output to a run that "
                "started somewhere else"
            )
        if isinstance(self.emits, ArraySpec) and self.element is None:
            # The message carries the argument because this is where somebody
            # meets the rule: a test fixture author who wanted to register a
            # tool and got a raise wants to know why it cannot simply default,
            # and that answer lives in a completed-item entry nobody is going
            # to go and read.
            raise ValueError(
                f"{self.tool_id}: emits an array and declares no element meaning — pass "
                "element=ElementKind.PIXEL/BLOCK if this tool decides what one value is, or "
                "element=ElementRelation.PRESERVED/AGGREGATED if it relates to what it was "
                "handed. There is no default on purpose: a tool that redefines its elements "
                "and inherited PRESERVED would still register, and the only symptom is a count "
                "written to a CSV under a noun nothing checked"
            )
        if not isinstance(self.emits, ArraySpec) and self.element is not None:
            raise ValueError(
                f"{self.tool_id}: emits rows and declares element {self.element!r} — a table "
                "has columns, not elements"
            )
        if isinstance(self.element, ElementKind) and self.element_names is None:
            raise ValueError(
                f"{self.tool_id}: declares element {self.element!r} but no element_names — "
                "a tool that redefines what one value is must also declare the noun that "
                "CSV columns and plot axes use for counts over it"
            )
        if not isinstance(self.element, ElementKind) and self.element_names is not None:
            if self.element is None:
                raise ValueError(
                    f"{self.tool_id}: emits rows and declares element_names "
                    f"{self.element_names!r} — a table has columns, not element names"
                )
            raise ValueError(
                f"{self.tool_id}: declares element_names {self.element_names!r} for "
                f"{self.element!r} — relation declarations read names from their upstream"
            )
        _check_emissions(self.tool_id, self.emissions, self.params_model)
        known = set(self.params_model.model_fields)
        unknown = [name for name in self.primary_params if name not in known]
        if unknown:
            raise ValueError(
                f"{self.tool_id}: primary_params names no such field: {sorted(unknown)}"
            )
        caption_unknown = [
            part.param
            for part in self.caption
            if part.param is not None and part.param not in known
        ]
        if caption_unknown:
            raise ValueError(
                f"{self.tool_id}: caption names no such field: {sorted(caption_unknown)}"
            )
        label_unknown = [name for name in self.param_value_labels if name not in known]
        if label_unknown:
            raise ValueError(
                f"{self.tool_id}: param_value_labels names no such field: {sorted(label_unknown)}"
            )
        stereotype_unknown = [name for name in self.param_stereotypes if name not in known]
        if stereotype_unknown:
            raise ValueError(
                f"{self.tool_id}: param_stereotypes names no such field: "
                f"{sorted(stereotype_unknown)}"
            )
        undeclared = known - set(self.param_stereotypes)
        if undeclared:
            raise ValueError(
                f"{self.tool_id}: declares no stereotype for {sorted(undeclared)} — every "
                "parameter says how it is populated, because a field the map skips is one the "
                "widget generator has nothing to emit for and the symptom is a missing control"
            )
        for name in sorted(self.param_stereotypes):
            kind = self.param_stereotypes[name]
            if not isinstance(kind, ParamStereotype):
                # `TypeError` for `_whole_lookahead`'s reason: the neighbouring
                # refusals take a value that is legal for its type and wrong for
                # the tool, while a kind outside the vocabulary is not a
                # `ParamStereotype` at all — including one spelled right as a
                # bare string, since a member is what the generator dispatches
                # on.
                raise TypeError(
                    f"{self.tool_id}: param_stereotypes[{name!r}] is {kind!r}, which is not a "
                    f"stereotype — the vocabulary is closed to "
                    f"{[member.value for member in ParamStereotype]}, and a sixth kind is a "
                    "decision about what the GUI can generate rather than a field a tool fills in"
                )
        # Comparing the function objects, not calling them: a params model with
        # required fields cannot be instantiated here, and the question is
        # whether an override exists at all rather than what it returns.
        overrides = self.params_model.output_rate is not ParamsBase.output_rate
        if self.rate_changing and not overrides:
            raise ValueError(
                f"{self.tool_id}: rate_changing is set but {self.params_model.__name__} does not "
                "override output_rate, so nothing can convert a downstream warmup into source "
                "frames"
            )
        if overrides and not self.rate_changing:
            raise ValueError(
                f"{self.tool_id}: {self.params_model.__name__} overrides output_rate but the "
                "spec does not declare rate_changing"
            )
        selects = self.params_model.selected_frames is not ParamsBase.selected_frames
        if self.selecting and not selects:
            raise ValueError(
                f"{self.tool_id}: selecting is set but {self.params_model.__name__} does not "
                "override selected_frames, so nothing can say which frames it keeps and the node "
                "would narrow the answer by ALL_FRAMES — that is, not at all"
            )
        if selects and not self.selecting:
            raise ValueError(
                f"{self.tool_id}: {self.params_model.__name__} overrides selected_frames but "
                "the spec does not declare selecting, so the plan never asks and the run covers "
                "the whole video the node was written to cut down"
            )

    @property
    def emission_names(self) -> tuple[str, ...]:
        """What this tool can be asked to keep, as the names a screen lists."""
        return tuple(emission.name for emission in self.emissions)

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        """Version as integers, so `1.10.0` sorts above `1.9.0`."""
        match = SEMVER_PATTERN.match(self.version)
        assert match is not None  # guaranteed by __post_init__
        major, minor, patch = match.groups()
        return (int(major), int(minor), int(patch))

    @property
    def key(self) -> tuple[str, str]:
        """Registry key: a tool is identified by id *and* version.

        Two versions of one tool coexist deliberately — an old pipeline that
        names 1.0.0 must keep reproducing 1.0.0's output after 1.1.0 ships.
        """
        return (self.tool_id, self.version)


class Channel(StrEnum):
    """Which of three questions a `ToolSpec` field answers.

    One line — hashed or not — cannot say why `mode` is unhashed: it is not
    *placement*, it is how the one path runs. So the non-identity side splits in
    two, and the split is what makes "core carries no GUI policy" checkable at
    all. `primary_params` is a field and not an import, so no `.importlinter`
    contract can see it; a declared partition can.
    """

    #: What the result *is*. The hashed side. Only `tool_id` and `version` reach
    #: the digest literally — `version` stands proxy for the rest, since a tool
    #: that changes what it accepts, emits, means by an element, or computes and
    #: keeps its version is already a defect `register_tool` cannot catch. The
    #: channel is the claim; the digest is one enforcement of it.
    IDENTITY = "identity"
    #: How the one path runs it — scheduling, lead-in, whether the answer may be
    #: reused. Never hashed, and not placement either: two builds that disagreed
    #: here would produce the same result at different cost, or refuse to
    #: produce it at all.
    EXECUTION = "execution"
    #: What a front end shows about it. Never hashed, never read by the
    #: executor, and the declared home for captions, signal labels, and
    #: `primary_params`.
    PRESENTATION = "presentation"


#: Every `ToolSpec` field, in exactly one channel. Totality and exactness are
#: both tested, in both directions, so a field added without a row here fails at
#: the moment it is written — which is what catches the next `primary_params`.
#:
#: A dict literal rather than per-field metadata on the dataclass, because the
#: property being asserted is about the *partition* and a reader checking it
#: wants the three groups side by side, not field annotations to collate.
SPEC_CHANNELS: Mapping[str, Channel] = {
    "tool_id": Channel.IDENTITY,
    "version": Channel.IDENTITY,
    "params_model": Channel.IDENTITY,
    "accepts": Channel.IDENTITY,
    "emits": Channel.IDENTITY,
    # Beside `emits` rather than with the presentation fields the save screen
    # also reads: what a tool can produce is what the result is, and the label a
    # checkbox shows for one of those products is `param_value_labels`. A tool
    # that changes this set and keeps its version is `run`'s defect, and
    # `version` stands proxy for it in the digest the same way.
    "emissions": Channel.IDENTITY,
    "element": Channel.IDENTITY,
    "element_names": Channel.IDENTITY,
    # The channel's own sentence names it: a tool that changes what it *computes*
    # and keeps its version is a defect `register_tool` cannot catch. So `run` is
    # what the result is, and `version` is the position that stands proxy for it
    # in the digest — hashing the function would key a run on a build's memory
    # layout and miss the edit that matters.
    "run": Channel.IDENTITY,
    "mode": Channel.EXECUTION,
    "rate_changing": Channel.EXECUTION,
    # Beside `rate_changing` and for its reason, though what the *parameters*
    # behind it decide — which frames are in the answer — is squarely identity.
    # Neither flag reaches a digest: each exists so that omitting the override it
    # names is refused at registration, which is this channel's second sentence
    # ("or refuse to produce it at all"). The hashed half is `params_model`.
    "selecting": Channel.EXECUTION,
    "warmup_frames": Channel.EXECUTION,
    # Execution rather than identity, and it is the second placement worth
    # arguing. It decides whether a result may be *reused*, which is this
    # channel's own third clause — two builds disagreeing here compute the same
    # frame at different cost, and the frame itself is what `params_model`,
    # `run` and `version` already stand for.
    "warmup_kind": Channel.EXECUTION,
    "lookahead_frames": Channel.EXECUTION,
    "settling_epsilon": Channel.EXECUTION,
    "stateful": Channel.EXECUTION,
    # Execution rather than identity, and it is the one placement worth arguing.
    # What the state accumulates plainly shapes the result — but the factory
    # decides *when a run starts over*, not what the run computes, and the thing
    # it starts is already outside the digest: `stateful` is what denies the node
    # a key at all.
    "state_factory": Channel.EXECUTION,
    "deterministic": Channel.EXECUTION,
    "primary_params": Channel.PRESENTATION,
    "caption": Channel.PRESENTATION,
    "param_value_labels": Channel.PRESENTATION,
    "param_stereotypes": Channel.PRESENTATION,
    "summary": Channel.PRESENTATION,
}


#: One step of a path: a tool and the parameters it was configured with. The
#: params are not optional — half of what a step contributes is params-derived.
type PathStep = tuple[ToolSpec, ParamsBase]


def presented_param_value(
    spec: ToolSpec, params: ParamsBase, name: str, *, format_spec: str = ""
) -> str:
    """A parameter value as the tool wants it read in presentation."""
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


def caption_for_params(spec: ToolSpec, params: ParamsBase) -> str:
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

    `ToolSpec.warmup_frames` is the worst case over the legal parameter range;
    `ParamsBase.warmup_frames` is what this configuration actually needs. Which
    of the two applies is decided here and nowhere else, so a caller holding a
    `(spec, params)` never has to know that there are two numbers.

    The override is detected by identity against the base method rather than by
    a flag on the spec, exactly as `__post_init__` detects an `output_rate`
    override — and unlike that one it is not cross-checked at registration,
    because a params model cannot be instantiated there and the check that
    matters needs a value rather than a signature.

    A refinement below zero is refused by `FrameCount` itself, at the return
    inside the tool that computed it, which is a better place to meet it than
    here — so the only check left is the one this function is the only place to
    make.

    Raises:
        ValueError: if the refinement exceeds the spec's bound. A bound is what
            `sieve inspect` prints and what a reader checks a tool's cost
            against, and a configuration quietly needing more lead-in than the
            declaration admits is the silent direction — the preview renders,
            the tool has not settled, and the tuning done against it is wrong
            rather than absent.
    """
    spec, params = step
    if type(params).warmup_frames is ParamsBase.warmup_frames:
        return spec.warmup_frames
    refined = params.warmup_frames()
    if refined > spec.warmup_frames:
        raise ValueError(
            f"{spec.tool_id}: {type(params).__name__}.warmup_frames() returned {refined}, "
            f"which exceeds the spec's declared bound of {spec.warmup_frames} — the bound is the "
            "worst case over the legal parameter range and a configuration may only refine it "
            "downward"
        )
    return refined


def _whole_lookahead(tool_id: str, count: FrameCount, source: str) -> FrameCount:
    """`count`, or refuse it for not being a whole number of frames.

    `FrameCount` annotates `frames: int` and enforces only the sign, so half a
    frame arrives here intact — a window length divided by two is the obvious
    way to produce one. It cannot be honored downstream: emission is delayed by
    whole frames or not at all, so rounding it wherever the delay is applied
    would leave the declared window and the window actually read differing by a
    frame, with the declaration still reading exact.

    `TypeError` where every other refusal in this file raises `ValueError`, and
    the split is the honest one: the neighbours refuse a value that is in range
    for its type and wrong for the tool, while this refuses a value that is not
    a `FrameCount`'s declared `int` at all.
    """
    if isinstance(count.frames, bool) or not isinstance(count.frames, int):
        raise TypeError(
            f"{tool_id}: {source} must be whole frames, got {count.frames!r} — a window "
            "boundary lands between two frames or on one, and only one of those is a frame "
            "the executor can wait for"
        )
    return count


def node_lookahead_frames(step: PathStep) -> FrameCount:
    """One node's read-ahead: the refinement if it has one, else the bound.

    `node_warmup_frames` for the other half of the window, sharing its
    override-by-identity detection and its one-directional refusal. Kept a
    separate function rather than a second return value because the two
    quantities are consumed by different things — warmup by the decode range
    the plan folds, lookahead by the emission delay the executor applies
    (02.3) — and a caller wanting one has no use for the other.

    Raises:
        ValueError: if the refinement exceeds the spec's bound.
        TypeError: if the refinement is not a whole count of frames.
    """
    spec, params = step
    if type(params).lookahead_frames is ParamsBase.lookahead_frames:
        return spec.lookahead_frames
    refined = _whole_lookahead(
        spec.tool_id, params.lookahead_frames(), f"{type(params).__name__}.lookahead_frames()"
    )
    if refined > spec.lookahead_frames:
        raise ValueError(
            f"{spec.tool_id}: {type(params).__name__}.lookahead_frames() returned {refined}, "
            f"which exceeds the spec's declared lookahead bound of {spec.lookahead_frames} — the "
            "bound is the worst case over the legal parameter range and a configuration may only "
            "refine it downward"
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
        raise ValueError(f"{spec.tool_id}: output_rate must be positive, got {rate}")
    return output_warmup.at_input_of(rate) + node_warmup_frames(step)


def source_warmup_frames(path: Sequence[PathStep]) -> FrameCount:
    """Lead-in to decode, in *source* frames, for a path ordered root to sink.

    Summing `warmup_frames` over the path is the right idea in the wrong unit,
    and the unit only matters once something changes rate. Walking sink to root
    instead: a requirement of `need` frames at a node's output costs
    `ceil(need / rate)` at its input, and the node's own `warmup_frames` is
    already denominated there. Five frames of warmup behind a 10:1 decimator is
    fifty source frames, not five, and the error a plain sum makes is silent —
    the preview renders, an IIR that should have settled produces a plausible
    frame, and the tuning done against it is wrong rather than absent.

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
        Frames to decode ahead of the first source frame the run asks for.

    Raises:
        ValueError: if any node reports a non-positive output rate, which would
            mean an output frame the source could never supply enough input for.
    """
    need = NO_FRAMES
    for step in reversed(path):
        need = input_warmup_frames(step, need)
    return need
