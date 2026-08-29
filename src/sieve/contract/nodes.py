"""Node contracts. One per tool type; a source is the first.

Nodes and edges are contracted separately: `edges.py` is closed and this is
open. A node may be anything, so long as what it offers is on that list.

Everything here is a record of data and callables. A tool builds one and
hands it over; SIEVE never holds an instance of a tool's own class, which is
what keeps ADR-0009's second prohibition cheap to honour — there is no
internal to reach past, because there is no object to reach into.

**A source is how a file enters SIEVE.** Any file: a recording, a crop
document, a parameter document. A node with no inputs, opened on an address,
offering named edges of whatever kinds the file carries. That is also how a
port that the user left unset gets satisfied — the binding names an address
and an edge name, which is the document-and-a-key-within-it that
`docs/architecture-leads.md` holds the argument for.

**Listed and deliverable are different facts.** `read` returning `None` is
the producer admitting it cannot supply something its extent listed — a
coverage fact travelling to whoever records coverage, not an error. The
footage in `video-tests/` is why: cut mid-GOP, it answers "how many frames"
three ways, and a contract that cannot say so launders twenty missing frames
into twenty zeroes.

**Cost is not declared.** ADR-0007 holds that a cost class belongs to the
pairing and is measured where it runs. Access says what is *possible*, which
is the source's to state; what it costs is the machine's to answer.

Not carried yet, deliberately: a materialization — a proxy, a lossy-intra cut
— has to be proposed with a cost and accepted by the substrate (ADR-0008)
rather than performed quietly, and scratch space is granted rather than
chosen, because a tool writing beside somebody's footage is the second writer
the one-writer lead in `docs/architecture-leads.md` exists to prevent.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sieve.contract import forms
from sieve.contract.edges import SPECS, Edge, Extent
from sieve.contract.forms import Form


@dataclass(frozen=True)
class Fingerprint:
    """A source's identity, naming the algorithm that produced it.

    Named rather than implied, so a content-level fingerprint can one day
    coexist with a byte-level one instead of orphaning everything written
    under it. `None` from a source with no durable identity — a camera — is
    correct, and means no project document.
    """

    algorithm: str
    token: str


@dataclass(frozen=True)
class Output:
    """One edge a source offers, with the functions that serve it.

    `extent` is None exactly when the edge is unpositioned. `read` takes the
    position, or None for an edge that ignores it.
    """

    edge: Edge
    read: Callable[[int | None], Any | None]
    extent: Callable[[], Extent] | None = None


@dataclass(frozen=True)
class Opened:
    """A source that is open. One per address per session; not thread-safe."""

    address: str
    outputs: Mapping[str, Output]
    close: Callable[[], None]
    fingerprint: Callable[[], Fingerprint | None] = lambda: None


@dataclass(frozen=True)
class Source:
    """A node with no inputs. The role a tool fills to bring a file in.

    `handles` is the tool's opinion about an address, deliberately: a list of
    containers is a decoder's opinion, and one living in the substrate is
    ADR-0009's accretion arriving one format request at a time.

    `offers` is which edge kinds this tool serves, and it is the one question
    about a source that can be asked for free. `handles` says whether an
    address is this tool's, `open` says what is actually on offer and costs
    whatever the file costs; neither answers *what kind of thing enters here*,
    which is what a caller needs before it opens anything. A recording, a crop
    document and a parameter document are all sources, and only the first can
    be what a project is about — that distinction is `edges.py`'s frame/value
    line, read one step earlier.

    Per tool rather than per address, because it is a fact about what the tool
    does: a container decoder offers frames whatever file it is pointed at. A
    floor and not a hint — the tool may open with more edges than it declared,
    but a declared kind that never arrives is a bug in the tool, caught when
    `open` returns without it. That is the difference from `patterns` below,
    which is why there is one fact here and not two that can disagree.

    `patterns` are glob hints for a file chooser and are never the gate —
    `handles` decides. Two facts that can disagree is normally the shape to
    avoid, and it is tolerable only because the disagreement cannot hide
    anything: a chooser built from these always offers all files as well, so
    a pattern too narrow costs a click and a pattern too wide costs a refusal
    with a reason.
    """

    handles: Callable[[str], bool]
    open: Callable[[str], Opened]
    offers: tuple[str, ...]
    patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for kind in self.offers:
            if kind not in SPECS:
                raise ValueError(f"{kind!r} is not an edge kind")


def read_form(output: Output, position: int | None, want: Form) -> Any | None:
    """Read a frame edge and shape it — the one path to a form.

    Everything but a producer's own form goes through here, which is what
    makes two sources agree in the low bits. `None` passes straight through:
    a frame that could not be delivered has no form.
    """
    have = output.edge.spec.form
    frame = output.read(position)
    if frame is None:
        return None
    if want == have:
        return frame
    if forms.grade(have, want) is None:
        raise ValueError(f"{have.key()} cannot answer for {want.key()}")
    return forms.build(frame, want)
