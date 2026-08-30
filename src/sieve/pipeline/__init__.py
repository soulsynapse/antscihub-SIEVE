"""The chain: which node's output satisfies which node's want.

**The secret.** How the user's chain is spelled, and how a declared want is
matched to something that can answer it. Downstream of this package a
consumer holds a producer that answers at a position in a form, and cannot
tell whether that is the recording, a step's recorded output, or a constant
satisfying a port. Adding a step, reordering two, rebinding one's input,
retuning a knob: all of it is an edit to this package's records and to
nothing else's shape. Before it existed, the whole of that decision was
`session.steps[0]`.

**What it is responsible for.** The node set and the bindings between them;
whether a binding is legal — kind, form, and the positioning a producer can
serve against the offsets a consumer admits; deriving what a node could not
declare about its own output (`bind.py` names every field and where it comes
from); the composed durable key, since a node's upstream prefix is the one
part of a key no tool can spell for itself; and emitting the demand a
scheduler can act on without asking anything further.

**What it must not own.** Scheduling and eviction (ADR-0006, and the graph
the orchestrator experiments measured). Which tier answers a fetch
(`serve.py`). Running the arithmetic, and the threads it runs on
(`gui/frame/stepwork.py`). Cost class, which belongs to the pairing and is
measured where it runs (ADR-0007). Finding and loading tools (`registry.py`,
which needs the settings, and would drag the application in behind it).
Drawing. A binding says what is needed and what answers it; every one of
those decides *when*, and this package never does.

**What it does not yet hold, deliberately.** Parameter values — a port that
declares what it needs and names a document to be satisfied from — and with
them fan-out axes and the persistent form: identity, schema version, and the
split between what travels and what stays on this machine.
`docs/architecture-leads.md` argues all four and says they want deciding
together. This package is the in-memory chain, and its shape is meant to take
them as additions rather than as a rewrite.
"""

from sieve.pipeline.bind import Bound, Demand, bind
from sieve.pipeline.chain import Binding, Chain, Node

__all__ = ["Binding", "Bound", "Chain", "Demand", "Node", "bind"]
