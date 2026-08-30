"""Binding a step to what feeds it: the facts a step is not allowed to declare.

`nodes.Step.produces` says a name, a kind and a dtype, and stops there. This
is the other half — the claim that everything it stopped short of is derivable
from the thing upstream plus the step's own offsets, and therefore that no
step ever has to state a fact it cannot check. `01-derived-binding.py` is what
tries to break that claim; this is only the derivation it runs against.

Where each field comes from:

  timebase   the input's, carried. A step never sees one (`nodes.Step`).
  origin     the input's, carried. Where positions came from is the source's
             business and passes through untouched.
  access     RANDOM, and *not* the input's. This is the one that looks wrong
             and is the point: a step's output is read out of where it was
             kept, not recomputed on the way past, so a forward-only input
             still yields randomly-readable output once ADR-0005 has done the
             recording. If this is wrong, a step over a live camera cannot be
             scrubbed, and everything downstream of one inherits FORWARD for
             no reason anybody chose.
  window     None. The series is the retention; there is no head to sit behind.
  listed     the input's, less the first `reach` — a step admitting -30 has no
             honest answer for the first thirty positions, which is
             `series.first_honest` said about an extent instead of a row.
  closed     the input's. A step over an open extent is open.
  starts     None: "every listed position is alike". Reading back one row
             depends on no other row.

The ordinals are snapshotted at bind, for the reason `serve.Ordinals` is
snapshotted rather than living on the store: an extent that grows would
otherwise renumber rows already written.

## The consumer side, proposed

`02-chained-field.py` asks what happens when the thing upstream is another
step. Three records here are proposals for `contract/`, held out here until a
measurement says whether they survive:

`Wanted` is what `nodes.Step` currently implies and never says. Today the want
lives in two places that cannot disagree because neither is a declaration:
`form_for` builds the wanted `Form`, and `pipeline/binding.py` hardcodes
`upstream.edge.kind != FRAME`. Made a record, the kind is checked before the
form, which is what lets a step want something that is not pixels.

`FIELD` is the kind that reopens `edges.KINDS`. `nodes.Step` refuses to offer
the field today on a stated ground: a float32 image-sized field carrying a
`Form` would grade EXACT against a uint8 gray frame over the same rect, and
`forms.grade` and `store.Frames.dominator` would both wave it through. The
proposal is that the sample format is spelled in `Form.pix` — so the collision
closes inside `grade`, where the mistake would be made, and inside `Form.key`,
which is what `chain.key` folds into the durable key a sink is filed under.

`Product` is `nodes.Produced` with that spelling: a pixel kind says its sample
format, a value kind says its dtype. Neither says a rect, because the geometry
is still the binding's — a field is measured at the analysis form it was
handed, so its form is that form wearing its own sample format.

**A field is not derived from another field.** `grade` exists because chroma
can be dropped and pixels can be resampled and the result is still the same
picture. Neither is true of a measurement: resampling a flow field averages
quantities, which is a different measurement rather than a coarser view of
the same one, and `surfaces.overlay` already does its own resize on the way
to the screen where the result is show-only anyway. So a field want is matched
by form *equality*, and `_FROM` gains no entry.

## What holds a field

Serving a field product means running the producer's arithmetic, because
nothing image-sized is durable here. `Held` is the hold-and-release of
ADR-0006 pointed at fields instead of frames: the consumer's own declaration
says which upstream rows are still admitted, so eviction is derived rather
than a window somebody sized. `02` prices it against recomputing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from sieve.contract import edges
from sieve.contract import forms
from sieve.contract.edges import FRAME, MASK, Access, Edge, Extent, Positioning
from sieve.contract.forms import Form
from sieve.contract.nodes import Answer, Output, Refusal, Step, read_form
from sieve.serve import Ordinals

#: Proposed for `edges.KINDS`: a measurement per pixel, which is neither a
#: picture nor a classification. Carries a form because it is pixels.
FIELD = "field"

# `edges.KINDS` is closed and SIEVE's alone to extend, so `Edge` refuses this
# kind until the file says otherwise. Opened here rather than there because
# what the experiment is testing is whether the kind is worth the decision —
# and an experiment that could not name the cost of its own proposal in one
# line would be hiding it. This is that line, and it is the whole of what
# `contract/edges.py` changes if the answer is yes.
edges.KINDS = edges.KINDS | {FIELD}

#: The kinds that are pixels, and therefore the ones a product spells a sample
#: format for. A value says a dtype instead; the properties are flat on the
#: edge and two kinds that share one share the type (`contract/edges.py`).
PIXELS = frozenset({FRAME, MASK, FIELD})


class Unreachable(LookupError):
    """A row whose inputs are not all there. Raised where a cache would cache."""


class Sink(Protocol):
    """Whatever holds what a step wrote. `series.Series` is one."""

    def get(self, row: int) -> float | None: ...


@dataclass(frozen=True)
class Wanted:
    """What a step consumes. `form_for` belongs to pixel kinds and nothing else.

    A field want carries no `form_for` deliberately: a step fed a field takes
    the form it is handed, because the producer measured at a geometry the
    consumer had no say in. Only a frame want gets to name a form, and what it
    names is the crop.
    """

    kind: str
    form_for: Callable[[tuple[int, int, int, int]], Form] | None = None

    def __post_init__(self) -> None:
        if self.kind == FRAME and self.form_for is None:
            raise ValueError("a frame want names the form it wants the crop in")
        if self.kind != FRAME and self.form_for is not None:
            raise ValueError(f"a {self.kind} want does not choose its own form")


@dataclass(frozen=True)
class Product:
    """`nodes.Produced` with the sample format a pixel kind has to spell."""

    name: str
    kind: str
    dtype: str | None = None   #: a value is a number
    pix: str | None = None     #: a frame, mask or field is pixels

    def __post_init__(self) -> None:
        if (self.kind in PIXELS) != (self.pix is not None):
            raise ValueError(f"a {self.kind} product spells pix, or does not")


@dataclass(frozen=True)
class Declared:
    """A step whose want is a declaration instead of a hardcoded FRAME.

    `nodes.Step` with `wants` added and `form_for` moved onto it. Everything
    else is unchanged and deliberately so: what a step admits, what it
    computes and what it reduces to were never the part in question.
    """

    wants: Wanted
    offsets: tuple[int, ...]
    field: Callable[[Mapping[int, Any], int], Any]
    reduce: Callable[[Any], float]
    produces: tuple[Product, ...]
    params: Mapping[str, Any] | None = None

    def needs(self, row: int) -> tuple[int, ...]:
        return tuple(row + off for off in self.offsets)

    @property
    def reach(self) -> int:
        return -min(self.offsets)


def wants_of(step: Step | Declared) -> Wanted:
    """What *step* consumes — declared, or the frame want the tree implies.

    The fallback is the statement of what `contract/nodes.py` says today: a
    step is "a node with frame inputs", and its `form_for` is the frame want
    with the record taken off.
    """
    declared = getattr(step, "wants", None)
    return declared if declared is not None else Wanted(FRAME, step.form_for)


def wanted_form(step: Step | Declared, upstream: Output,
                rect: tuple[int, int, int, int]) -> Form:
    """The form *step* reads its input in, or raise saying why it cannot.

    The kind is checked before the form, which is the whole of what making the
    want a record buys: a frame cannot answer a field want by being the same
    size, and a field cannot answer a frame want by being pixels.
    """
    want = wants_of(step)
    have = upstream.edge
    if have.kind != want.kind:
        raise ValueError(f"a {want.kind} want cannot be fed {have.name!r}, "
                         f"which is a {have.kind}")
    if want.kind == FRAME:
        asked = want.form_for(rect)
        if forms.grade(have.form, asked) is None:
            raise ValueError(f"{have.form.key()} cannot answer for {asked.key()}")
        return asked
    # Equality, not `grade`: a measurement resampled is a different
    # measurement, so a field either is the one asked for or is not.
    if have.form is None:
        raise ValueError(f"{have.name!r} is a {have.kind} carrying no form")
    return have.form


class Held:
    """Fields kept because some declaration downstream still admits them.

    ADR-0006's hold-and-release with a field in it instead of a frame. What
    is released is derived from the consumer's own offsets — `keep_from` is
    called with the oldest row anything can still ask for — rather than from
    a window size somebody chose, which is the arrangement
    `orchestrator-experiments/02-derived-eviction.py` measured for frames.

    **Keyed by row, which is narrower than it looks.** `pool.py` keys by
    position and form together, because two consumers at different forms
    need different arrays of one instant and a pool keyed by one of them
    thinks either satisfies the other — the lesson `store.py` learned first
    and the pool learned again. This holds one producer's fields at one
    form, so a row is a complete key here and nowhere else. Anything that
    grows a second producer or a second crop wants the pool, not this.

    Counts are kept because the reuse is the result: a consumer at lags 30,
    20 and 10 asks for each upstream row four times, thirty rows apart, so a
    cache that spans less than the consumer's reach captures none of it and
    reports the same wall time as no cache at all.
    """

    def __init__(self) -> None:
        self.by_row: dict[int, Any] = {}
        self.computed = 0
        self.reused = 0
        self.peak_rows = 0
        self.peak_bytes = 0

    def get_or(self, row: int, make: Callable[[int], Any]) -> Any:
        got = self.by_row.get(row)
        if got is not None:
            self.reused += 1
            return got
        got = self.by_row[row] = make(row)
        self.computed += 1
        self.peak_rows = max(self.peak_rows, len(self.by_row))
        self.peak_bytes = max(
            self.peak_bytes, sum(held.nbytes for held in self.by_row.values()))
        return got

    def keep_from(self, row: int) -> None:
        """Drop every row below *row* — nothing admits them any more."""
        for stale in [held for held in self.by_row if held < row]:
            del self.by_row[stale]


def bind(step: Step | Declared, upstream: Output,
         rect: tuple[int, int, int, int], sink: Sink,
         held: Held | None = None) -> dict[str, Output]:
    """The `Output`s a step offers, once it is known what feeds it.

    Built here rather than by the tool: serving a product needs the tier
    stack and the store, which a tool may not import, and a tool that
    returned its own `Output` would be a tool deciding when a value is
    recorded (ADR-0005).

    *held*, when given, is where this step's field products are kept between
    the demands that share them. Absent, every read recomputes.
    """
    want = wanted_form(step, upstream, rect)
    if upstream.extent is None:
        raise ValueError("a positioned step wants a positioned input")

    up = upstream.edge.at
    at = Positioning(timebase=up.timebase, origin=up.origin,
                     access=Access.RANDOM, window=None)
    rows = Ordinals(upstream.extent().listed)
    listed = rows.listed

    def extent() -> Extent:
        got = upstream.extent()
        return Extent(got.listed[step.reach:], got.closed)

    def read_value(position: int | None, _form: Form | None = None) -> Answer:
        # The form is taken and ignored: a value has no pixels to shape. It
        # stays in the signature because `Output.read` is one shape for every
        # kind, and a value edge quietly taking a different one would be a
        # second protocol nobody declared.
        row = rows.rank(position) if position is not None else None
        value = None if row is None else sink.get(row)
        # LATER, never GONE: an uncovered row is covered after a run. Only the
        # input going missing is permanent, and that refusal is the input's.
        return (Answer(value) if value is not None
                else Answer(refusal=Refusal.LATER))

    def compute(row: int) -> Any:
        inputs = inputs_for(step, upstream, rect, row, listed)
        if inputs is None:
            raise Unreachable(row)
        return step.field(inputs, row)

    def read_field(shape: Form) -> Callable[..., Answer]:
        def read(position: int | None, form: Form | None = None) -> Answer:
            # A form the producer did not measure at refuses FORM rather than
            # being built: `read_form`'s fallback is `forms.build`, which
            # crops and resamples, and neither is a thing to do to a
            # measurement without saying so.
            if form is not None and form != shape:
                return Answer(refusal=Refusal.FORM)
            row = rows.rank(position) if position is not None else None
            if row is None or row < step.reach or row >= len(listed):
                return Answer(refusal=Refusal.LATER)
            try:
                value = (compute(row) if held is None
                         else held.get_or(row, compute))
            except Unreachable:
                # An admitted row the input could not answer for. LATER, not
                # GONE: what is missing is upstream's to call permanent, and
                # it did not.
                return Answer(refusal=Refusal.LATER)
            return Answer(value)
        return read

    offered: dict[str, Output] = {}
    for product in step.produces:
        if product.kind == FIELD:
            # The field is measured at the form the step read its input in,
            # wearing its own sample format. The step said the format; the
            # geometry was never the step's to say.
            shape = Form(want.rect, want.out, product.pix)
            offered[product.name] = Output(
                edge=Edge(product.name, FIELD, form=shape, at=at),
                read=read_field(shape), extent=extent, starts=None,
            )
            continue
        offered[product.name] = Output(
            edge=Edge(product.name, product.kind, dtype=product.dtype, at=at),
            read=read_value, extent=extent, starts=None,
        )
    return offered


def inputs_for(step: Step | Declared, upstream: Output,
               rect: tuple[int, int, int, int], row: int,
               listed: tuple[int, ...]) -> dict[int, Any] | None:
    """What one row needs from upstream, or None if any of it is unreachable.

    The shape `session.step_inputs` has, with the tiers taken out: this
    folder is asking what a binding derives, not what a cache holds.

    A frame want goes through `read_form`, so a source that refuses the
    wanted form is answered by the canonical construction rather than read as
    a missing position. A field want does not: there is no construction that
    turns one measurement into another, so it asks for what it was promised
    and takes a refusal as a refusal.
    """
    want = wants_of(step)
    asked = wanted_form(step, upstream, rect)
    inputs: dict[int, Any] = {}
    for needed in step.needs(row):
        if needed < 0 or needed >= len(listed):
            return None
        answer = (read_form(upstream, listed[needed], asked)
                  if want.kind == FRAME
                  else upstream.read(listed[needed], asked))
        if not answer.delivered:
            return None
        inputs[needed] = answer.frame
    return inputs
