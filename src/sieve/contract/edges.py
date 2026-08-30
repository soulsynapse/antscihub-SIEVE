"""What may travel between nodes. Closed, and SIEVE's alone to extend.

The tool contract is open and this is not, which is the split that caps the
substrate. If a node declared its own port types, every tool would mint a
payload — tracks, trajectories, centroids — and each one is substrate work:
how it is stored, how it is keyed, how a declaration reaches over it, how it
is drawn. That is ADR-0009's accretion in the type system, where it is harder
to see. Adding a kind here is a decision; that is the point of the file.

An edge is one kind, and it composes the properties it needs from a shared
vocabulary. A frame and a mask both carry a form because both are pixels; a
value carries a dtype because it is a number. The properties are flat on the
edge, not inherited through a spec hierarchy, so two kinds that share a
property share the type and nothing else.

Properties are optional per instance: a kind does not mandate which properties
are present. The tool and the substrate check at the point of use.

FIELD is the fourth kind and the one that had to be argued for. A measurement
per pixel is neither a picture nor a classification, and the ground `nodes.Step`
refused to offer one on was that a float32 field would grade EXACT against a
uint8 gray frame over the same rect. That closes where the mistake would be
made, in `forms.Form.pix`, rather than here — which is why the kind is
admissible at all. What a chained field costs held against recomputed is a
measurement, and it is in `docs/findings/`.

Position-indexing is a property of the edge, not a kind of its own: a
constant is a value whose declaration ignores position, which is ADR-0006's
declaration in its degenerate case rather than a second mechanism beside it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from sieve.contract.forms import Form

FRAME = "frame"   #: pixels at a form — an image
MASK = "mask"     #: pixels at a form — a classification per pixel
VALUE = "value"   #: a number — a threshold, a count, a rate
FIELD = "field"   #: pixels at a form — one measurement per pixel

KINDS: frozenset[str] = frozenset({FRAME, MASK, VALUE, FIELD})

#: The kinds that are pixels, and so the ones that carry a form and spell a
#: sample format. A value says a dtype instead.
PIXELS: frozenset[str] = frozenset({FRAME, MASK, FIELD})


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
class Edge:
    """A named thing a node offers or wants.

    The name is what a binding names — a document and a key within it, since
    one crop document holds several regions and one file may hold several
    streams (``docs/architecture-leads.md``).

    Properties are composed, not inherited: each edge carries the properties
    its kind needs, and two kinds that share a property share the type. All
    properties are optional per instance; the tool and the substrate check
    at the point of use.
    """

    name: str
    kind: str
    form: Form | None = None       #: pixel shape — frame and mask carry this
    dtype: str | None = None       #: "int" | "float" — value carries this
    at: Positioning | None = None  #: None means the value ignores position

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"{self.kind!r} is not an edge kind")

    @property
    def positioned(self) -> bool:
        return self.at is not None
