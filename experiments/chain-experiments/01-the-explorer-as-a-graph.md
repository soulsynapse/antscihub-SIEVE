# 01 — the explorer as a graph

G1. No code and no measurement: take the tool explorer, which works and has been
measured, and write what it does as typed nodes. The question is whether the
proposed vocabulary can say a thing that already runs, and every ambiguity the
re-expression exposes is one the base type set has to answer.

Read from `experiments/tool-experiments/tool-explorer.py`, `tools.py`,
`forms.py`, `surfaces.py` and `series.py` as they stand, not from memory of
them. Line references are to the state this was written against and are meant to
be re-found rather than trusted.

## The finding that changes the rest

**The explorer already contains a two-node chain, and it already keys it the way
G6 says a graph must.**

`Rig.set_tool` takes a blur setting, and when it is non-zero it wraps the tool's
own `field` in a closure that Gaussian-blurs every admitted frame first — then
folds `blur` into `tool.params`, which is what reaches `tool.key()`. So there is
a `blur → absdiff` pipeline in the running application, implemented as a
decorator, whose downstream key carries the upstream parameter.

That is the depth-1 case of the subgraph-key rule, arrived at independently by
somebody solving a smaller problem. G6 is therefore not a new idea to be argued
for; it is the generalisation of something this tree already does and already
depends on. What it is not is a mechanism that survives depth — see the gaps
below.

**ROI propagation also already exists, and is spelled `form_for`.** G7 asks
whether a downstream node's region of interest can travel back to the fetch
without changing `Form`. It already does: `Tool.form_for(crop)` is the tool
declaring what form it wants, `Rig.form()` resolves it, and the store is asked
for that form rather than for whole frames. The direction of that call is
upstream. The thing G7 proposes to test is running in production, for the
one-node case.

Both of these mean the graph idea is less speculative than it looked, and that
the interesting risk has moved: not *can a node declare upward*, but *does the
declaration compose when there are two of them*.

## The nodes

Written as `name : (rate, extent) inputs → (rate, extent) output`, where rate is
per-recording or per-row and extent is scalar, rect, or image. The rate axis is
an addition — nothing in the current vocabulary has it, and the exercise needed
it in three places before it could finish.

**source** — the root, not a node. Identified by name, which is the first field
of every series key.

**fetch** `(per-recording, rect) crop + (per-row, image) source → (per-row,
image) frame`. This is `forms.build`: crop, resize, convert, in that order,
keyed `(row, form_key)`. It is not written as a node anywhere in the explorer —
**the store is this node**, and its cache is the node's cache.

**blur** `(per-row, image) → (per-row, image)`, param `blur`. Present only when
the setting is non-zero. The chain described above.

**field** — `absdiff`, `dis_flow`, `lag_mhi`. `(per-row, image) × offsets →
(per-row, image)`. Declares which rows it admits; the declaration is a fetch
plan (ADR-0006), and `Rig.horizon` defers to `tools.residency` to union it over
a look-ahead.

**reduce** `(per-row, image) → (per-row, scalar)`. Today a second output of the
field node rather than a node — `Rig.evaluate` returns both from one call.

**series** `(per-row, scalar) → (per-recording, array) + (per-recording,
coverage)`. Keyed `source | tool.key() | form.key()`, written on admission by
the fill thread and never by anything that draws (ADR-0005). Durable: `save`,
`load`, `restore`.

**ceiling** `(per-recording, scalar)`, keyed by the same three-part key, set by
the first honest field or by the user. Display-only, and held rather than
autoscaled because an overlay that renormalises per frame makes a still scene
look as active as a moving one.

**overlay** `(per-row, image at display form) + (per-row, image at analysis
form) + (per-recording, scalar ceiling) → (per-row, image at display form)`.
Resize the field, then colour-map — the cheaper order and the only one whose
colour bar is honest.

**to_columns** `(per-recording, array) + (per-recording, coverage) +
(display width) → three (per-recording, arrays at display width)`.

**canvas / band** — draws. Not nodes.

## The ambiguities, and what the exercise answers

**Is the colour map a node or a display property?** A node — it takes three
inputs and produces a value. But it must be a node the graph knows is
*terminal*, because ADR-0005 forbids anything downstream of it from being
recorded, and `surfaces.py` splits the live surface from the report surface for
the same reason. So the graph needs a notion of a display region past which
nothing may be admitted to a store. That requirement falls straight out of an
existing ADR rather than being invented here.

**Is the reduction its own node or a second output?** It can be a node, but it
may never be *scheduled* as one. `Rig.evaluate` computes the field and its
reduction in one call, on the fill thread, at the moment of admission — and it
must, because splitting them means the field has to survive between two
schedulable units, which is precisely the storage `tool.py` refuses by name. So
the rule is fusion: **a reduce node is always co-scheduled with the field node
it reads, or fields become storable.** This is the first real constraint the
exercise produced and it was not visible from the type list.

**Where does the crop attach?** At the fetch node, as the rect half of a `Form`
— not as a node between fetch and tool. Which resolves the collision that
started this: crop is neither a session global nor an awkward `Tool`, it is a
parameter of the fetch node that downstream nodes declare upward into. That is
what `form_for` already is.

**Is a series a node or an edge?** A store on an edge, keyed, exactly like the
frame store on the fetch edge. The graph has two stores of the same kind at
different rates, which is a symmetry worth keeping rather than two mechanisms.

**Is the band's column count a parameter?** It is a window width, and ADR-0005
names window size among the things a recorded value may not depend on. It
doesn't reach one — `to_columns` is downstream of the terminal line. The
exercise finds the rule already respected, which is the useful kind of
confirmation.

**Are `frame` and `field` the same type?** No, and the distinction is
load-bearing rather than nominal. A frame can be derived from a dominating frame
exactly (`forms.grade`), which is what the hunt tier's admission rule rests on.
A field cannot: `surfaces.overlay`'s docstring states that a flow taken on a
downscaled image is not the downscale of the one taken at full size. So one is
resample-derivable and the other is not, and a base type set that merged them
would let the store answer a field request with an approximation.

## What it could not express, and what that costs

Three honest negatives. The first two are gaps in the vocabulary; the third is a
limit on what this exercise can settle at all.

**The blur mechanism does not survive depth.** Folding an upstream param into
the downstream tool's `params` works at depth one and is wrong at depth two:
`blur` has no offsets of its own, and an upstream node that admitted rows — a
temporal smooth rather than a spatial one — would have its reach silently
dropped from the fetch plan, because only the downstream tool's `offsets` are
ever read. The existing mechanism is therefore evidence *for* the subgraph-key
rule and not an implementation of it. Composition of offsets is untested and is
G4.

**Nothing distinguishes per-recording from per-row.** The ceiling, the series
and its coverage are all per-recording; every frame, field and scalar is
per-row. The exercise could not be written without the axis, and the storage
consequence is the reason it matters: a per-recording image is one array, a
per-row image is one per row. That is the difference between a cached value that
is free and one that is another recording's worth of bytes, and it currently
lives nowhere in the type system.

**There is no mask in the explorer, so this exercise cannot validate one.** The
mask type — a per-pixel selector that combines with other masks and restricts a
reduction's domain — is the thing the whole discussion started from, and no
working code in this tree produces one. Naming it in the base type set on the
strength of this exercise would be arguing from a tool that does not exist,
which is the folder's standing rule and the thing it has already been burned by
twice. So the base set below omits it deliberately, and the first real mask
producer is what earns its place.

## What G2 can take from this

The types the substrate demonstrably has to understand, because something
working already schedules, caches, displays or routes an interaction to each:

- `rect`, per-recording — the crop; the thing a drag edits and a fetch reads
- `frame`, per-row, image, carrying a `Form` — resample-derivable, admissible
- `field`, per-row, image, carrying a ceiling — not derivable, never stored
- `scalar`, per-row — what a reduction emits
- `series`, per-recording, array plus coverage — durable, keyed, restorable
- `scalar`, per-recording — a held ceiling, a calibration

Not in the set on this evidence: mask, points, table. Each may well belong and
none is earned yet.

## Verdict

G1 passes, with one addition, one constraint and one thing it cannot answer.

The vocabulary expresses everything the explorer does once the rate axis is
added. It produced a constraint that was not visible from argument — field and
reduce must be co-scheduled or fields become storable. And it found two of the
proposed rules already running in production code at depth one, which moves the
risk from *whether they are right* to *whether they compose*, which is what G4
and G6 are for.

What it cannot do is tell us anything about masks, and that is the half of the
original question this exercise was never able to reach.
