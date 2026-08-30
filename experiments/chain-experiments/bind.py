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
"""

from __future__ import annotations

from typing import Any, Protocol

from sieve.contract import forms
from sieve.contract.edges import Access, Edge, Extent, Positioning
from sieve.contract.forms import Form
from sieve.contract.nodes import Answer, Output, Refusal, Step, read_form
from sieve.serve import Ordinals


class Sink(Protocol):
    """Whatever holds what a step wrote. `series.Series` is one."""

    def get(self, row: int) -> float | None: ...


def bind(step: Step, upstream: Output, rect: tuple[int, int, int, int],
         sink: Sink) -> dict[str, Output]:
    """The `Output`s a step offers, once it is known what feeds it.

    Built here rather than by the tool: serving a product needs the tier
    stack and the store, which a tool may not import, and a tool that
    returned its own `Output` would be a tool deciding when a value is
    recorded (ADR-0005).
    """
    want = step.form_for(rect)
    have = upstream.edge.form
    if forms.grade(have, want) is None:
        raise ValueError(f"{have.key()} cannot answer for {want.key()}")
    if upstream.extent is None:
        raise ValueError("a positioned step wants a positioned input")

    up = upstream.edge.at
    at = Positioning(timebase=up.timebase, origin=up.origin,
                     access=Access.RANDOM, window=None)
    rows = Ordinals(upstream.extent().listed)

    def extent() -> Extent:
        got = upstream.extent()
        return Extent(got.listed[step.reach:], got.closed)

    def read(position: int | None, _form: Form | None = None) -> Answer:
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

    return {
        product.name: Output(
            edge=Edge(product.name, product.kind, dtype=product.dtype, at=at),
            read=read, extent=extent, starts=None,
        )
        for product in step.produces
    }


def inputs_for(step: Step, upstream: Output, rect: tuple[int, int, int, int],
               row: int, listed: tuple[int, ...]) -> dict[int, Any] | None:
    """The frames one row needs, or None if any is unreachable.

    The shape `session.step_inputs` has, with the tiers taken out: this
    folder is asking what a binding derives, not what a cache holds. Through
    `read_form`, so a source that refuses the wanted form is answered by the
    canonical construction rather than read as a missing position.
    """
    want = step.form_for(rect)
    frames: dict[int, Any] = {}
    for needed in step.needs(row):
        if needed < 0 or needed >= len(listed):
            return None
        answer = read_form(upstream, listed[needed], want)
        if not answer.delivered:
            return None
        frames[needed] = answer.frame
    return frames
