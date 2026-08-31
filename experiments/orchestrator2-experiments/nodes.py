"""The consumers, as activations synthesised around what each declared.

Every node in this folder is a callable of `(Reason, Request)` and nothing
else, and none of them is a thread. What each is, is the thing V1 spelled as
a thread plus a polling loop:

| V1 | here |
|---|---|
| `Sweep`, a declaration | `Sweep`, a declaration. Unchanged — it had no loop to remove. |
| `ToolRunner`, a thread that declares, sleeps 5 ms, and gives up at 10 s | `StepNode`, an activation, plus `Pass` to advance rows |
| `OrchestratorExplorer._serve`, the Qt thread spinning at 2 ms | `Viewer`, an activation whose second call hands the frame back |

**A tool never sees a `Request`.** This is the whole of what ADR-0009 costs
the port, and it is enforced here by construction rather than by comment:
`StepNode` reads `tool.offsets` to issue the requests, calls `tool.field` and
`tool.reduce` with plain arrays, and calls `Request.release` itself. Nothing
a tool author writes is handed the context, so nothing a tool author writes
can hold a frame past its release, decide when a value is recorded, or reach
the store. A VapourSynth filter does all three; that is the difference
between a plugin compiled against a core and a measurement somebody wrote.

**Where the values and fields go.** `sieve/series.py`'s `Sinks` and
`sieve/pipeline/binding.py`'s `Held`, imported rather than reimplemented.
V1's `ToolRunner` kept `self.values` and a local `derived` dict, both of which
died with the thread — so a window revisited recomputed values that were
still correct, and the crop derivations were thread-local by accident rather
than scoped by anything. `Sinks` keys by source, step and form (ADR-0010), so
a knob moved and moved back is a lookup; `Held` scopes crops to one node and
releases by `keep_from`, which is what V1's hand-written `derived.pop` loop
was approximating.

**`Pass` is `vspipe --requests`, not a thread.** Something has to decide which
rows of a window a step computes, and in V1 that was a `for` loop inside the
worker. Here it is a bounded number of activations in flight: issue `depth`
of them, and issue the next as each completes, on whichever recorder thread
completed it. The depth is a real knob rather than a tuning artefact — it is
how much work the dispatcher is allowed to have queued for one node, and a
result that names its core shape names this too.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

import numpy as np

from dispatcher import Dispatcher, Reason, Request
from graph import Envelope, Graph, Need, Urgency
from pool import Pool

import forms as forms_mod
import tools as tools_mod

from sieve.pipeline.binding import Held
from sieve.series import Series


class Sweep:
    """A node that wants a whole window, in attention-first order.

    Carried from V1 unchanged, including the reasoning: it is a declaration
    and not a thread, it declares its window as offsets rotated so the anchor
    comes first, and the declaration is also the hold that keeps the pool
    from sweeping the window out from under a step.

    It is the one consumer here with no activation, because it has no
    arithmetic and wants nothing to happen when its rows land — it wants them
    held. A node that only holds has nothing to be re-entered for.

    `NODE_ID` is one node for the whole session, not one per landing:
    `declare` replaces a node's previous declaration and releases only the
    difference, so re-declaring onto an overlapping window keeps the overlap
    held for free. Minting a node per window made the overlap nobody's, and
    V1 measured that at 72 decodes where 36 were already in RAM.
    """

    NODE_ID = "fill"

    def __init__(self, start: int, end: int, anchor: int,
                 form_key: str, graph: Graph) -> None:
        self.node_id = self.NODE_ID
        self.start, self.end = start, end
        self.anchor = max(start, min(anchor, end - 1))
        self.form_key = form_key
        self.graph = graph
        self.declared_at = time.perf_counter()

    def declare(self) -> None:
        span = list(range(0, self.end - self.start))
        first = self.anchor - self.start
        order = tuple(span[first:] + span[:first])
        self.graph.declare(Need(self.node_id, self.start, order,
                                self.form_key, Urgency.DEFERRED))

    def release(self) -> None:
        self.graph.release(self.node_id)


class Viewer:
    """The GUI, as one activation per position it wants to show.

    Declares INTERACTIVE and one row, and that is the entire declaration —
    urgency is the only scheduling fact a consumer is placed to state, and
    where it ranks against everything else in flight is `pressure_queue`'s to
    derive.

    **The second call is what replaces the spin.** V1's `_serve` sat on the Qt
    thread for up to `EXACT_WAIT_S`, sleeping 2 ms and pumping events, which
    is the interactive thread polling for a frame the fetch thread already
    knew it had. Here `show` is called from a recorder thread the moment the
    row lands, and what the caller does with that — a queued signal, for Qt —
    is the caller's business and not the dispatcher's.

    Supersession is the point of `get_frame(..., supersedes=True)`: a drag
    issues an activation per tick, and the ones overtaken are cancelled
    before they are re-entered rather than being decoded and discarded after.
    V1 could only count that afterwards, as `stale`; both counts are kept, and
    they measure different halves of the same waste.
    """

    def __init__(self, dispatcher: Dispatcher, form_key: str,
                 show: Callable[[int, Any], None],
                 node_id: str = "gui") -> None:
        self.dispatcher = dispatcher
        self.form_key = form_key
        self.show = show
        self.node_id = node_id
        self.shown = 0

    def want(self, row: int, then=None) -> Request:
        return self.dispatcher.get_frame(
            self.node_id, row, self._activate, Urgency.INTERACTIVE,
            self.form_key, supersedes=True, then=then)

    def _activate(self, reason: Reason, ctx: Request) -> None:
        if reason is Reason.INITIAL:
            ctx.request(ctx.row)
            return
        frame = ctx.get(ctx.row)
        self.shown += 1
        self.show(ctx.row, frame)
        #: the GUI does not release: its declaration *is* the hold on the row
        #: it is showing, and it holds until it declares somewhere else.
        #: A viewer that released here would drop the frame on screen.


class StepNode:
    """One step, as an activation. What `ToolRunner` was, without the thread.

    INITIAL requests the rows `tool.needs(row)` names, at the source form, and
    returns. ALL_FRAMES_READY derives the crops, runs `field` and `reduce`,
    writes the value to the series, offers the field if the step offers one,
    and releases. That second call is ADR-0005's recorder in the most literal
    reading the ADR admits: the value is written on the thread that observed
    its inputs land, at the moment they landed, and nothing that draws is
    anywhere near it.

    **The derivation is inside the envelope on purpose.** It is the step's
    cost and not the dispatcher's, and a graph that hid it would report a step
    as free that is paying a crop-sized memcpy per row. V1 made the same
    choice for the same reason.

    **Declares DEFERRED, and says nothing about where it ranks.** A step's
    rows sit inside the sweep's declared window, so outranking the sweep buys
    by seek what was already arriving by sequential read and stalls the
    producer doing it — measured, and the reason `pressure_queue` derives rank
    (`docs/findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks`).
    """

    def __init__(self, tool: tools_mod.Tool, source_form: forms_mod.Form,
                 crop_rect: tuple[int, int, int, int],
                 dispatcher: Dispatcher, series: Series | None = None,
                 offers_field: bool = False) -> None:
        self.tool = tool
        self.source_form = source_form
        self.source_key = source_form.key()
        self.crop_form = tool.form_for(crop_rect)
        self.dispatcher = dispatcher
        self.graph = dispatcher.graph
        self.pool = dispatcher.pool
        self.series = series
        self.node_id = f"tool-{tool.name}-{id(self)}"
        #: what this step offers downstream, if anything. A field put into
        #: the pool is requestable by another step's activation on exactly
        #: the terms a decoded row is — same key shape, same refcount, same
        #: re-entry — because the pool does not ask what a payload is. That
        #: is README question 2.
        self.offers_field = offers_field
        self.field_key = f"field:{tool.key()}:{self.crop_form.key()}"
        #: crops kept between the demands that share them — `binding.Held`,
        #: scoped to this one node, which is what makes a row a key.
        self.held = Held()
        self.values: dict[int, float] = {}
        #: the rows the arithmetic actually ran in, in the order it ran them.
        #: Not a diagnostic: for a step carrying state across rows this *is*
        #: the input, and a node that cannot say what order it saw cannot be
        #: checked against one that ran in order.
        self.order: list[int] = []
        #: how many of this node's activations were inside the arithmetic at
        #: once. `order` alone cannot see this: it is appended at the end, so
        #: two activations that overlapped completely still record an
        #: ascending pair. For a node carrying state, concurrency corrupts it
        #: independently of order, and only this number tells them apart.
        self.peak_concurrent = 0
        self._in_arithmetic = 0
        self.computed = 0
        self.derive_ms = 0.0
        self._lock = threading.Lock()

    def want(self, row: int, then=None) -> Request:
        return self.dispatcher.get_frame(
            self.node_id, row, self._activate, Urgency.DEFERRED,
            self.source_key, supersedes=False, then=then)

    def _activate(self, reason: Reason, ctx: Request) -> None:
        if reason is Reason.INITIAL:
            for needed in self.tool.needs(ctx.row):
                ctx.request(needed)
            return

        with self._lock:
            self._in_arithmetic += 1
            self.peak_concurrent = max(self.peak_concurrent,
                                       self._in_arithmetic)
        env = Envelope(self.node_id, ctx.row, self.source_key,
                       "field").open()
        frames = {}
        for needed in self.tool.needs(ctx.row):
            crop = self.held.get(needed)
            if crop is None:
                t0 = time.perf_counter()
                crop, _how = forms_mod.derive(
                    ctx.get(needed), self.source_form, self.crop_form)
                self.derive_ms += (time.perf_counter() - t0) * 1000.0
                self.held.put(needed, crop)
            frames[needed] = crop

        field = self.tool.field(frames, ctx.row)
        value = self.tool.reduce(field)
        env.close()
        self.graph.record(env)

        # `keep_from` rather than a hand-written pop loop: no admitted offset
        # can still name a row below this one.
        self.held.keep_from(ctx.row - self.tool.reach)

        if self.offers_field:
            #: what this row's arithmetic cost, for the same reason the fetch
            #: thread reports its decode: a field that took 30 ms to make is
            #: worth more to keep than one that took 0.2 ms, and the pool
            #: cannot know which unless the producer says.
            self.pool.put(ctx.row, self.field_key, field, by=self.node_id,
                          cost_ms=env.ms)
        if self.series is not None:
            self.series.put(ctx.row, value)
        with self._lock:
            self.values[ctx.row] = value
            self.order.append(ctx.row)
            self._in_arithmetic -= 1
            self.computed += 1
        ctx.release()


class ChainedStepNode:
    """A step fed another step's field, requested through the dispatcher.

    The consumer half of README question 2. Where `StepNode` requests source
    rows and derives its own crops, this requests the *producer's field* at
    each admitted offset — `ctx.request(row, producer.field_key)` — and is
    re-entered only when every one of them has been put by the producer's
    activation. Nothing here waits on the producer, checks whether it has run,
    or knows that it exists beyond the key.

    The producer is driven independently. If it never computes a row this one
    admits, this node is never re-entered for that row, which is the honest
    behaviour: a consumer whose input was not produced has no value to write,
    and V1's answer to the same situation was a ten-second deadline and a
    `starved` counter.
    """

    def __init__(self, tool: tools_mod.Tool, field_key: str,
                 dispatcher: Dispatcher, series: Series | None = None) -> None:
        self.tool = tool
        self.field_key = field_key
        self.dispatcher = dispatcher
        self.graph = dispatcher.graph
        self.series = series
        self.node_id = f"chained-{tool.name}-{id(self)}"
        self.values: dict[int, float] = {}
        self.computed = 0
        self._lock = threading.Lock()

    def want(self, row: int, then=None) -> Request:
        return self.dispatcher.get_frame(
            self.node_id, row, self._activate, Urgency.DEFERRED,
            self.field_key, supersedes=False, then=then)

    def _activate(self, reason: Reason, ctx: Request) -> None:
        if reason is Reason.INITIAL:
            for needed in self.tool.needs(ctx.row):
                ctx.request(needed, self.field_key)
            return
        env = Envelope(self.node_id, ctx.row, self.field_key, "field").open()
        fields = {n: ctx.get(n, self.field_key)
                  for n in self.tool.needs(ctx.row)}
        value = self.tool.reduce(self.tool.field(fields, ctx.row))
        env.close()
        self.graph.record(env)
        if self.series is not None:
            self.series.put(ctx.row, value)
        with self._lock:
            self.values[ctx.row] = value
            self.computed += 1
        ctx.release()


class Pass:
    """Drives a node's rows through a range at a bounded request depth.

    VapourSynth's `vspipe --requests`, and the thing that replaces V1's
    `for pos in range(start + reach, end)` inside a worker thread. It owns no
    thread: `start` issues `depth` activations, and each completion issues the
    next from whichever recorder thread completed it.

    The depth is the knob that says how much work one node may have queued.
    Too shallow and the fetch thread runs out of declared rows to serve ahead
    of the arithmetic; too deep and a node holds declarations over rows it
    will not reach for a long time, which is a hold and therefore memory. It
    is reported with every result for that reason, not tuned to a number.

    **Stopping is a flag and not a join**, because there is no thread to join.
    A stopped pass issues nothing further; activations already in flight run
    to completion, which is correct — their inputs are resident and their
    arithmetic is cheap beside having fetched them.
    """

    def __init__(self, node: Any, start: int, end: int,
                 depth: int = 8) -> None:
        self.node = node
        self.start, self.end = start, end
        self.depth = max(1, depth)
        self._next = start
        self._stopped = False
        self._lock = threading.Lock()
        self.issued = 0
        self.done = threading.Event()
        self._in_flight = 0

    def run(self) -> None:
        """Issue the first `depth` rows. Returns at once."""
        for _ in range(self.depth):
            if not self._issue():
                break

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
        self.done.set()

    def _issue(self) -> bool:
        with self._lock:
            if self._stopped or self._next >= self.end:
                if self._in_flight == 0:
                    self.done.set()
                return False
            row = self._next
            self._next += 1
            self.issued += 1
            self._in_flight += 1
        self.node.want(row, then=self.advanced)
        return True

    def advanced(self) -> None:
        """One activation finished; issue the next. Called by the driver."""
        with self._lock:
            self._in_flight -= 1
            finished = (self._in_flight == 0
                        and (self._stopped or self._next >= self.end))
        if finished:
            self.done.set()
            return
        self._issue()
