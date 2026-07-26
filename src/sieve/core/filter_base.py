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
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from sieve.core.types import ChannelSpec

#: `MAJOR.MINOR.PATCH`, no pre-release or build metadata. A filter version is
#: an input to a cache key before it is a human-facing label, and `1.0.0-rc1`
#: vs `1.0.0` is an ordering question with no answer this system needs to have.
_SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

#: Lowercase identifier. It appears in cache keys, YAML, and CLI arguments, so
#: it may not depend on case folding or shell quoting to stay itself.
_FILTER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class Mode(StrEnum):
    """Whether a filter can emit a frame as soon as it has consumed one."""

    #: One frame in, one frame out, in order. The executor may pipeline it.
    STREAMING = "streaming"
    #: Needs a span of frames before it can emit any of them. The executor
    #: must accumulate the window rather than hand frames through singly.
    WINDOWED = "windowed"


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

    def canonical_json(self) -> str:
        """Byte-stable JSON of these params, for hashing.

        `mode="json"` so enums and paths become the same strings they became in
        the artifact, sorted keys so the string does not depend on field
        declaration order, and no whitespace because a hash input is not read
        by anyone.
        """
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


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

    #: NumPy dtype names, e.g. `("uint8", "float32")`.
    dtypes: tuple[str, ...] = ()
    channels: tuple[ChannelSpec, ...] = ()

    def admits(self, produced: ArraySpec) -> bool:
        """Whether an upstream node emitting `produced` may feed this one.

        Deliberately permissive: it is false only when the two sets are
        provably disjoint. A wildcard on either side admits, because the DAG's
        static check exists to reject graphs that *cannot* work, and rejecting
        one that merely cannot be proven to work would make declaring `dtypes`
        at all a liability.
        """
        return self._compatible(self.dtypes, produced.dtypes) and self._compatible(
            self.channels, produced.channels
        )

    @staticmethod
    def _compatible(required: tuple[Any, ...], produced: tuple[Any, ...]) -> bool:
        if not required or not produced:
            return True
        return bool(set(required) & set(produced))


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Order-of-magnitude cost, for predicting a run before making it.

    Normalized per megapixel rather than per frame: the same kernel on 4K and
    on a 256x256 crop differ by two orders of magnitude, so a per-frame number
    would be wrong for every resolution but the one it was measured at. These
    drive HUD predictions and scheduling hints, never a correctness decision,
    so a factor-of-two error is tolerable and a missing declaration is not.
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
    accepts: ArraySpec
    emits: ArraySpec
    cost: CostEstimate
    mode: Mode = Mode.STREAMING
    #: Frames the filter must consume before its output is trustworthy. The
    #: executor sums these along the topological path feeding a request rather
    #: than applying them per node. An IIR's true warmup is infinite, so a
    #: nonzero value here is a settled-to-within-epsilon choice and the
    #: filter's docstring says which epsilon.
    warmup_frames: int = 0
    #: Same backend, same input, same output. Gates whether the node may be
    #: cached at all.
    deterministic: bool = True
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
        if not _FILTER_ID_PATTERN.match(self.filter_id):
            raise ValueError(
                f"filter_id must match {_FILTER_ID_PATTERN.pattern!r}, got {self.filter_id!r}"
            )
        if not _SEMVER_PATTERN.match(self.version):
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

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        """Version as integers, so `1.10.0` sorts above `1.9.0`."""
        match = _SEMVER_PATTERN.match(self.version)
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
        """Whether this node's output may be reused from a cache entry."""
        return self.deterministic
