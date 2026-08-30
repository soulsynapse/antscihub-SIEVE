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
from sieve.contract.edges import SPECS, Edge, Extent
from sieve.contract.forms import Form


class Refusal(str, Enum):
    """Why a listed position did not come back. Closed, like edge kinds."""

    GONE = "gone"     #: permanent hole — remember it, asking again costs the same
    FORM = "form"     #: position exists but not in the form asked — ask differently
    LATER = "later"   #: deliverable but not yet — ask again, do not record as a hole


@dataclass(frozen=True)
class Answer:
    """A frame or a typed refusal — a record so `is None` checks become AttributeError."""

    frame: Any | None = None
    refusal: Refusal | None = None

    def __post_init__(self) -> None:
        if (self.frame is None) == (self.refusal is None):
            raise ValueError("an answer is a frame or a refusal, never both or neither")

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
            if kind not in SPECS:
                raise ValueError(f"{kind!r} is not an edge kind")


#: Substrate-owned and closed, like edge kinds.
ROLES: dict[str, type] = {"source": Source}


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
    have = output.edge.spec.form
    if forms.grade(have, want) is None:
        raise ValueError(f"{have.key()} cannot answer for {want.key()}")
    answer = output.read(position, have)
    if not answer.delivered:
        return answer
    return Answer(forms.build(answer.frame, want))
