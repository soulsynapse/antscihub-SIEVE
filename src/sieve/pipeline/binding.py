"""Binding a chain: the facts a node is not allowed to declare about itself.

Ported from `experiments/chain-experiments/bind.py`, which measured the claim
this rests on — that everything `nodes.Produced` stops short of is derivable —
against two steps of different reach and a forward-only source.

Where each field of a bound edge comes from:

  form       the step's `form_for` against the crop, checked against what the
             producer holds with `forms.grade`
  timebase   the producer's, carried. A step never sees one.
  origin     the producer's, carried.
  access     RANDOM, and *not* the producer's. A step's output is read out of
             where it was kept rather than recomputed on the way past, so a
             forward-only input still yields randomly-readable output once
             ADR-0005 has done the recording. Copying the producer's would
             make a step over a live camera unscrubbable for no reason
             anybody chose.
  window     None. The store is the retention; there is no head to sit behind.
  listed     the producer's, less the first `reach`: a step admitting -30 has
             no honest answer for the first thirty rows, which is
             `series.first_honest` said about an extent instead of a row.
  closed     the producer's. A node over an open extent is open.
  starts     None — "every listed position is alike". Reading one row back
             depends on no other row.

**The substrate synthesizes these, never the tool.** Serving a product needs
the store, which a tool may not import (ADR-0009), and a tool that returned
its own `Output` would be a tool deciding when a value is recorded (ADR-0005).

**What this does not do is fetch.** A binding says what a node needs and what
answers it; getting the frames is the tier stack's and running the arithmetic
is the caller's. `Demand` is the whole of what crosses that line, and it is
`orchestrator-experiments/graph.py`'s `Need` without the urgency the graph
derives for itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from sieve.contract import forms
from sieve.contract.edges import FRAME, Access, Edge, Extent, Positioning
from sieve.contract.forms import Form
from sieve.contract.nodes import Answer, Output, Refusal
from sieve.ordinals import Ordinals
from sieve.pipeline.chain import Chain


class Sink(Protocol):
    """Whatever holds what a node wrote. `series.Series` is one."""

    def get(self, row: int) -> float | None: ...
    def put(self, row: int, value: float) -> None: ...


#: Builds the store one node writes into, given its id, its composed key, the
#: form its answer is about, the positions it can answer for, and the timebase
#: those are in. Supplied by the caller: what a value is kept in is storage,
#: and storage is not the pipeline's to own.
SinkFor = Callable[[str, str, Form, tuple[int, ...], str], Sink]


@dataclass(frozen=True)
class Demand:
    """What one node needs to answer one row: a form, and the positions in it.

    Positions rather than offsets, resolved against the producer's listing,
    so nothing downstream of here has to know what a step admitted. `rows`
    runs alongside, same order and same length, because a step's own
    arithmetic is keyed by row while everything that fetches is keyed by
    position — the two coordinates ADR-0004 keeps apart, carried together
    exactly where they have to be converted.
    """

    node: str
    form: Form
    positions: tuple[int, ...]
    rows: tuple[int, ...]
    row: int


@dataclass(frozen=True)
class Placed:
    """One node, bound: what it offers, what it wants, where it writes."""

    node: str
    outputs: Mapping[str, Output]
    upstream: Output | None = None
    want: Form | None = None
    sink: Sink | None = None
    offsets: tuple[int, ...] = ()
    listed: tuple[int, ...] = ()


class Bound:
    """A chain with every node's products resolved to real edges."""

    def __init__(self, chain: Chain, placed: Mapping[str, Placed]) -> None:
        self.chain = chain
        self.placed = placed

    def outputs(self, node: str) -> Mapping[str, Output]:
        return self.placed[node].outputs

    def sink(self, node: str) -> Sink | None:
        """Where *node*'s values are kept, for whoever admits its inputs."""
        return self.placed[node].sink

    def demand(self, node: str, row: int) -> Demand | None:
        """What *node* needs to answer *row*, or None if it cannot.

        None where an admitted offset falls off either end of the listing —
        the warm-up rows a step has no honest answer for, which the bound
        extent already excludes and this refuses again at the point of use.
        """
        here = self.placed[node]
        if here.want is None:
            return None
        wanted, rows = [], []
        for offset in here.offsets:
            needed = row + offset
            if needed < 0 or needed >= len(here.listed):
                return None
            wanted.append(here.listed[needed])
            rows.append(needed)
        return Demand(node, here.want, tuple(wanted), tuple(rows), row)


def bind(chain: Chain, heads: Mapping[str, Mapping[str, Output]],
         rect: tuple[int, int, int, int], sink_for: SinkFor) -> Bound:
    """Resolve every node's products against whatever feeds it.

    *heads* is what the open sources actually offered, by node id — the one
    thing a chain cannot state for itself, since a source's product names come
    out of `open` rather than out of its declaration.
    """
    placed: dict[str, Placed] = {}
    for node in chain.order():
        if node.kind == "source":
            if node.id not in heads:
                raise ValueError(f"{node.id!r} is a source and nothing opened it")
            placed[node.id] = Placed(node.id, dict(heads[node.id]))
            continue
        placed[node.id] = _bind_step(chain, node, placed, rect, sink_for)
    return Bound(chain, placed)


def _bind_step(chain: Chain, node: Any, placed: Mapping[str, Placed],
               rect: tuple[int, int, int, int], sink_for: SinkFor) -> Placed:
    step = node.tool.role
    feeding = chain.feeding(node.id)
    upstream = _producing(placed, feeding)

    if upstream.edge.kind != FRAME:
        raise ValueError(
            f"{node.id!r} wants frames and {feeding.producer}.{feeding.product} "
            f"is a {upstream.edge.kind}")
    if upstream.extent is None or upstream.edge.at is None:
        raise ValueError(f"{feeding.producer}.{feeding.product} is not positioned")

    want = step.form_for(rect)
    have = upstream.edge.form
    if forms.grade(have, want) is None:
        raise ValueError(
            f"{node.id!r} wants {want.key()}, which {have.key()} cannot answer")

    up = upstream.edge.at
    at = Positioning(timebase=up.timebase, origin=up.origin,
                     access=Access.RANDOM, window=None)
    # Snapshotted for the reason `serve.Ordinals` is snapshotted rather than
    # living on the store: an extent that grows would renumber rows already
    # written under the old numbering.
    listed = upstream.extent().listed
    rows = Ordinals(listed)
    timebase = f"{up.timebase.num}/{up.timebase.den}"
    sink = sink_for(node.id, chain.key(node.id), want, listed, timebase)

    def extent() -> Extent:
        got = upstream.extent()
        return Extent(got.listed[step.reach:], got.closed)

    def read(position: int | None, _form: Form | None = None) -> Answer:
        # The form is taken and ignored: a value has no pixels to shape. It
        # stays in the signature because `Output.read` is one shape for every
        # kind, and a value edge quietly taking another would be a second
        # protocol nobody declared.
        row = rows.rank(position) if position is not None else None
        value = None if row is None else sink.get(row)
        # LATER, never GONE: an uncovered row is covered after a run. Only the
        # input going missing is permanent, and that refusal is the input's.
        return (Answer(value) if value is not None
                else Answer(refusal=Refusal.LATER))

    outputs = {
        product.name: Output(
            edge=Edge(product.name, product.kind, dtype=product.dtype, at=at),
            read=read, extent=extent, starts=None,
        )
        for product in step.produces
    }
    return Placed(node.id, outputs, upstream=upstream, want=want, sink=sink,
                  offsets=step.offsets, listed=listed)


def _producing(placed: Mapping[str, Placed], feeding: Any) -> Output:
    offered = placed[feeding.producer].outputs
    if feeding.product not in offered:
        raise ValueError(
            f"{feeding.producer!r} offers {sorted(offered)}, "
            f"not {feeding.product!r}")
    return offered[feeding.product]
