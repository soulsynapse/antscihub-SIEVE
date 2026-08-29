"""What may travel between nodes. Closed, and SIEVE's alone to extend.

The tool contract is open and this is not, which is the split that caps the
substrate. If a node declared its own port types, every tool would mint a
payload — tracks, trajectories, centroids — and each one is substrate work:
how it is stored, how it is keyed, how a declaration reaches over it, how it
is drawn. That is ADR-0009's accretion in the type system, where it is harder
to see. Adding a kind here is a decision; that is the point of the file.

An edge is one type. What varies is the `spec` it holds and whether it holds
a `Positioning` — composition rather than a hierarchy, so nothing subclasses
anything and a reader has one shape to learn.

Position-indexing is a property of the edge, not a kind of its own: a
constant is a value whose declaration ignores position, which is ADR-0006's
declaration in its degenerate case rather than a second mechanism beside it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from sieve.contract.forms import Form

FRAME = "frame"   #: pixels at a form
VALUE = "value"   #: a number — a threshold, a count, a rate

# TODO: geometry — a rect, point or polygon. Will be built. Not here yet
# because it has to carry its coordinate grid, and four ints that are secretly
# a rect is that convention crossing an edge undeclared.


class Access(str, Enum):
    """What a producer can be asked for — the mirror of a declaration.

    A step declares the offsets it admits (ADR-0006); this says which of them
    can be served, so neither end carries a compatibility flag that could
    disagree with its own reach.
    """

    RANDOM = "random"       #: any listed position, any order
    WINDOWED = "windowed"   #: the head, and `window` positions behind it
    FORWARD = "forward"     #: the head only, once each


class Origin(str, Enum):
    """Where a position came from."""

    CARRIED = "carried"   #: read out of the source, per ADR-0004
    MINTED = "minted"     #: synthesised, because the source had none


@dataclass(frozen=True)
class Timebase:
    """Ticks per second, as the fraction it is.

    Exact rather than a float rate: at 90 kHz over 23.976 fps a frame is
    3753.75 ticks, so frame-number arithmetic was never exact.
    """

    num: int
    den: int

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.num, self.den)

    def seconds(self, position: int) -> float:
        """Wall time, for display only — never for identity."""
        return position * self.num / self.den


@dataclass(frozen=True)
class Extent:
    """What a producer says exists, as of now.

    A query rather than a constant, and closedness declared: a file is closed
    when it opens, a directory being written into and a stream are not.
    """

    listed: tuple[int, ...]   #: positions, ascending
    closed: bool

    def __len__(self) -> int:
        return len(self.listed)


@dataclass(frozen=True)
class Positioning:
    """The facts an edge needs to be indexed by position at all."""

    timebase: Timebase
    origin: Origin
    access: Access
    window: int | None = None   #: positions retained behind the head


@dataclass(frozen=True)
class FrameSpec:
    """Pixels. The form is the vocabulary; `forms.py` is its authority."""

    form: Form


@dataclass(frozen=True)
class ValueSpec:
    """A number. Not geometry — see the TODO above."""

    dtype: str   #: "int" | "float"


#: Which spec belongs to which kind. The whole closed set, in one place.
SPECS = {FRAME: FrameSpec, VALUE: ValueSpec}


@dataclass(frozen=True)
class Edge:
    """A named thing a node offers or wants.

    The name is what a binding names — a document and a key within it, since
    one crop document holds several regions and one file may hold several
    streams (`docs/architecture-leads.md`).
    """

    name: str
    kind: str
    spec: FrameSpec | ValueSpec
    at: Positioning | None = None   #: None means the value ignores position

    def __post_init__(self) -> None:
        expected = SPECS.get(self.kind)
        if expected is None:
            raise ValueError(f"{self.kind!r} is not an edge kind")
        if not isinstance(self.spec, expected):
            raise TypeError(
                f"{self.kind} edges carry {expected.__name__}, "
                f"not {type(self.spec).__name__}"
            )

    @property
    def positioned(self) -> bool:
        return self.at is not None
