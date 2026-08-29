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

**Listed and deliverable are different facts, and a refusal names its own
kind.** `read` handing back a refusal is the producer saying it cannot supply
something its extent listed — a coverage fact travelling to whoever records
coverage, not an error. The footage in `video-tests/` is why: cut mid-GOP, it
answers "how many frames" three ways, and a contract that cannot say so
launders twenty missing frames into twenty zeroes.

A bare `None` could not carry it. Three sources produce three different
refusals, measured in
`docs/findings/2026.08.29-what-two-more-sources-found-the-contract-cannot-say.md`:
a mid-GOP prefix cannot be decoded by anyone ever, an image of the wrong size
is a fine frame in the wrong form, and a position behind a forward-only
source's head is deliverable to somebody who asked in time. They want opposite
handling — remember it, ask differently, ask again — and one return value
collapsed them into a permanent hole. The session explorer never made that
mistake because every serve carried a *route* beside its payload and the tiers
branched on it; the route is what the port dropped and `Refusal` is it.

**Where a read may begin is the source's to state.** Walking an extent from
its head to find something deliverable costs a seek per refusal — 7.9 s on the
footage in `video-tests/`, whose first twenty listed positions are the tail of
a GOP that was cut away. The tool knew: it collected the file's keyframes at
open and used them to measure a GOP. `starts` is that fact reaching the caller
instead of being discovered by paying for it.

**A read names the form it wants.** The step side already had this: a tool's
`form_for` is a function of the crop, so the consumer names the form per
request. Fixing it on the edge instead made every read the whole frame at
source sampling — 47.6 MB on the footage in `video-tests/`, where the tier
stack this ports from never held anything but a 1 MB crop. A source may serve
`want` itself when it can do so cheaply, and must refuse with `FORM` rather
than approximate; `read_form` then falls back to the canonical construction,
which stays the one authority on what a form's bytes are.

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
from enum import Enum
from typing import Any

from sieve.contract import forms
from sieve.contract.edges import SPECS, Edge, Extent
from sieve.contract.forms import Form


class Refusal(str, Enum):
    """Why a listed position did not come back. Closed, and SIEVE's to extend.

    Closed for the reason `edges.py` is: a producer minting its own refusal
    kinds is every consumer growing a branch it cannot have anticipated. A
    source with a reason not on this list has found a defect in the list.
    """

    #: cannot be decoded, ever, by anyone — a real hole in the coverage record.
    #: Remember it; asking again buys the same answer at the same price.
    GONE = "gone"
    #: the position is here and is not in the form that was asked for. Ask
    #: differently — this says nothing about the position's availability.
    FORM = "form"
    #: deliverable, and not to you, now. A forward-only source asked for
    #: something behind its head, a tier still being written. Ask again; a
    #: consumer that files this as a hole never asks again and is wrong
    #: permanently on the strength of one moment.
    LATER = "later"


@dataclass(frozen=True)
class Answer:
    """What a read hands back: a frame, or a refusal that says which kind.

    A record rather than `ndarray | Refusal`, because the old shape returned
    `None` and every caller spelled its check `is None`. Against a bare union
    that check silently becomes False and the refusal is used as an array; a
    record turns the same mistake into an attribute error at the first use.
    """

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
    position — or None for an edge that ignores it — and the form wanted, and
    answers with one or refuses. A source that will not serve that form says
    so with `Refusal.FORM` *before* decoding, which is what makes the fallback
    in `read_form` cost nothing when it is taken.

    **`starts` is structure and not cost**, which is the line ADR-0007 draws
    and this class stays on the right side of. It says which positions stand
    on their own — a keyframe decodes without reference to another frame, a
    still in a folder has nothing to reference — and says nothing whatever
    about what any of them costs, which is measured at the pairing where it
    runs. Two of the three sources in this tree answer with their whole
    extent and one answers with a subset, which is what keeps the clause from
    being the word "keyframe" wearing an interface's clothes.

    `None` means the source draws no such distinction and every listed
    position is alike; it is not "unknown". A source that does not know which
    of its positions stand alone does not have this fact to give, and the
    caller's fallback is to treat them all as starts, which is what `None`
    already says.
    """

    edge: Edge
    read: Callable[[int | None, Form], Answer]
    extent: Callable[[], Extent] | None = None
    #: positions a read can start from without decoding through another —
    #: keyframes in a container, every position in a folder of stills. See
    #: the note in this class's docstring for why it is not a cost claim.
    starts: Callable[[], tuple[int, ...]] | None = None


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


def read_form(output: Output, position: int | None, want: Form) -> Answer:
    """Read a frame edge at *want* — the one path to a form.

    The source is asked first, because only it can be cheap: it holds the
    decoded picture and may crop before anything is copied. If it will not
    serve that form it says so without decoding, and the canonical
    construction runs here instead. `forms` stays the authority on what a
    form's bytes are either way, which is what makes two sources of one form
    agree in the low bits.

    Every other refusal passes straight through. `GONE` and `LATER` are facts
    about the position, and no change of form repairs either.
    """
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
