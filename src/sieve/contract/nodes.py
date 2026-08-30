"""Node contracts. One per tool type; a source is the first.

Everything here is a record of data and callables — SIEVE never holds an
instance of a tool's own class. A listed position may be undeliverable; a
refusal names the kind so the caller knows whether to remember, re-form,
or retry.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sieve.contract import forms
from sieve.contract.edges import FRAME, KINDS, PIXELS, Edge, Extent
from sieve.contract.forms import Form


class Refusal(str, Enum):
    """Why a listed position did not come back. Closed, like edge kinds."""

    GONE = "gone"     #: permanent hole — remember it, asking again costs the same
    FORM = "form"     #: position exists but not in the form asked — ask differently
    LATER = "later"   #: deliverable but not yet — ask again, do not record as a hole


@dataclass(frozen=True)
class Answer:
    """What an edge delivered, or a typed refusal — a record so `is None` checks become AttributeError.

    `payload` and not `frame`: one `Output.read` serves every kind, so what
    arrives here is a frame, a field, or the float a value edge answers with.
    It was named for pixels while a source was the only producer, and a float
    travelling under that name is the kind of quiet lie a rename is cheaper
    than.
    """

    payload: Any | None = None
    refusal: Refusal | None = None

    def __post_init__(self) -> None:
        # `is None`, not falsiness: 0.0 is an answer a value edge gives.
        if (self.payload is None) == (self.refusal is None):
            raise ValueError("an answer is a payload or a refusal, never both or neither")

    @property
    def delivered(self) -> bool:
        return self.refusal is None


@dataclass(frozen=True)
class Fingerprint:
    """A source's identity. None from a source with no durable identity (a camera)."""

    algorithm: str
    token: str


@dataclass(frozen=True)
class Output:
    """One edge a source offers, with the functions that serve it.

    `extent` is None when the edge is unpositioned. A source refuses with
    FORM *before* decoding, so `read_form`'s fallback costs nothing.
    `starts` None means every listed position is alike, not "unknown".
    """

    edge: Edge
    read: Callable[[int | None, Form], Answer]
    extent: Callable[[], Extent] | None = None
    #: positions that decode without reference to another (keyframes, stills)
    starts: Callable[[], tuple[int, ...]] | None = None


@dataclass(frozen=True)
class Opened:
    """A source that is open. Not thread-safe; a second reader opens its own."""

    address: str
    outputs: Mapping[str, Output]
    close: Callable[[], None]
    fingerprint: Callable[[], Fingerprint | None] = lambda: None


@dataclass(frozen=True)
class Source:
    """A node with no inputs. The role a tool fills to bring a file in.

    `offers` is a floor: open may return more edges, but a declared kind
    that never arrives is a bug. `patterns` are file-chooser hints;
    `handles` decides.
    """

    handles: Callable[[str], bool]
    open: Callable[[str], Opened]
    offers: tuple[str, ...]
    patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for kind in self.offers:
            if kind not in KINDS:
                raise ValueError(f"{kind!r} is not an edge kind")


@dataclass(frozen=True)
class Wanted:
    """What a step consumes: a kind, and — for a frame — the form of the crop.

    The want was implied twice and declared nowhere: `form_for` built the
    wanted `Form` and `pipeline/binding.py` hardcoded the kind, two statements
    that could not disagree because neither was one. Made a record, the kind is
    checked before the form, which is what lets a step want something that is
    not pixels.

    **Only a frame want names its own form.** A step fed a field or a mask
    takes the geometry it is handed: the producer measured where it measured,
    and a consumer that re-crops or resamples a measurement has made a
    different measurement rather than read the same one differently. So a
    field want is matched by form equality rather than by `forms.grade`, and
    what a frame want names is the crop.
    """

    kind: str
    form_for: Callable[[tuple[int, int, int, int]], Form] | None = None

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"{self.kind!r} is not an edge kind")
        if self.kind == FRAME and self.form_for is None:
            raise ValueError("a frame want names the form it wants the crop in")
        if self.kind != FRAME and self.form_for is not None:
            raise ValueError(f"a {self.kind} want does not choose its own form")


@dataclass(frozen=True)
class Produced:
    """An edge a step will offer — as much of one as a step can honestly say.

    Not an `Edge`, and the difference is the point. An edge carries a form
    and a `Positioning`, and a step can fill in neither: its form follows
    the crop it was handed, its timebase and origin are its input's, and its
    access is a property of where its output is kept rather than of the
    arithmetic. A record that carried those fields and then refused them
    would permit in its type exactly what it forbids in its checks. So the
    step says the name, the kind and the dtype, and the binding says the
    rest.

    The name is the step's own — two crops of one tool both produce
    `"flow"` — and qualifying it across a chain is the pipeline's job.

    A pixel kind spells its sample format and a value kind spells its dtype:
    the format is the one thing about a field's form the step *does* know,
    because it is a property of the arithmetic rather than of the crop.
    """

    name: str
    kind: str                #: one of `edges.KINDS`
    dtype: str | None = None   #: a value is a number
    pix: str | None = None     #: a frame, mask or field is pixels

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a produced edge is named or nothing can bind it")
        if self.kind not in KINDS:
            raise ValueError(f"{self.kind!r} is not an edge kind")
        if (self.kind in PIXELS) != (self.pix is not None):
            raise ValueError(f"a {self.kind} product spells pix, or does not")


@dataclass(frozen=True)
class Step:
    """A node with declared inputs. The role a tool fills to process them.

    `wants` says what it must be fed, and for a frame want the form the crop
    is wanted in. `offsets` names which listed positions relative to the one
    being computed must be resident — non-positive, 0 included; the scheduler
    resolves them against the listing, so a step never sees a timebase.
    `field` produces the image-sized result; `reduce` compresses it to the
    scalar a series stores. `produces` is what the step offers downstream —
    the declaration only, never the serving: what serves it needs the tier
    stack and the series store, neither of which a tool may import, and a
    tool that returned its own `Output` would be a tool deciding when a
    value is recorded (ADR-0005).

    **A step may offer its field, and what that costs is measured.** The
    ground this was refused on — that a float32 field would grade EXACT
    against the gray frame it was measured on — is closed in `forms.Form.pix`,
    where the mistake would have been made. A step that offers one is
    declaring the thing it already computes, and what holding it costs a
    consumer against recomputing it is in `docs/findings/`.

    Output positions are the input's, one for one. A step that resamples
    time — decimation, a rolling summary — is the trigger for a declared
    relation, and it is absent until then rather than present with a single
    legal value nothing reads.
    """

    wants: Wanted
    offsets: tuple[int, ...]
    field: Callable[[Mapping[int, Any], int], Any]
    reduce: Callable[[Any], float]
    produces: tuple[Produced, ...]
    sequential: bool = False
    params: Mapping[str, Any] | None = None

    def needs(self, row: int) -> tuple[int, ...]:
        return tuple(row + off for off in self.offsets)

    @property
    def reach(self) -> int:
        return -min(self.offsets)

    def __post_init__(self) -> None:
        if not self.offsets:
            raise ValueError("a step admits at least the position it computes")
        if len(set(self.offsets)) != len(self.offsets):
            # `needs` would return a multiset and every refcount would overcount
            raise ValueError(f"{self.offsets} names a position twice")
        if any(offset > 0 for offset in self.offsets):
            # `first_honest` trims a head; nothing in the tree trims a tail
            raise ValueError(f"{self.offsets} reaches ahead; offsets are non-positive")
        if 0 not in self.offsets:
            # a value about a position computed without it is about another one
            raise ValueError(f"{self.offsets} omits 0, the position being computed")
        if not self.produces:
            raise ValueError("a step that offers nothing is not a node")
        names = [product.name for product in self.produces]
        if len(set(names)) != len(names):
            raise ValueError(f"{sorted(names)} names one product twice")


#: Substrate-owned and closed, like edge kinds.
ROLES: dict[str, type] = {"source": Source, "step": Step}


def role_kind(role: object) -> str | None:
    """Which contract this role satisfies, or None if it satisfies none."""
    for kind, contract in ROLES.items():
        if isinstance(role, contract):
            return kind
    return None


def read_form(output: Output, position: int | None, want: Form) -> Answer:
    """Read at *want*: tries the source first; on FORM refusal, falls back to canonical construction."""
    answer = output.read(position, want)
    if answer.refusal is not Refusal.FORM:
        return answer
    have = output.edge.form
    if forms.grade(have, want) is None:
        raise ValueError(f"{have.key()} cannot answer for {want.key()}")
    answer = output.read(position, have)
    if not answer.delivered:
        return answer
    return Answer(forms.build(answer.payload, want))
