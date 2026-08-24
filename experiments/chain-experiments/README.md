# chain-experiments

Where SIEVE finds out what happens when a tool's output is another tool's
input. `decode-experiments` settled what a frame costs to get,
`storage-experiments` what it costs to keep, and `tool-experiments` what one
tool costs when it rides along on a fetch. All three measured a *single*
consumer. This folder is the layer all three deferred.

**What it has settled is ADR-0009**, which caps what SIEVE is: an analysis is a
node in a graph SIEVE evaluates, and adding a way to measure something is never
a change to SIEVE. Six of the ten goals below carry the evidence for it and are
marked done. Read the ADR for what was decided; read here for what it cost and
which answers could have gone the other way.

The rest is still a plan, and the ADR names three of them as things it
deliberately does not decide.

## The name is a guess and is one of the questions

The tree already says "the chain" (`docs/tuning/plan.md`) and "pipeline"
(ADR-0003), and both words presume a line — one thing after another, walkable
in order. What is actually being proposed is a directed graph: a mask combined
with an image is two inputs meeting at a node, which a line cannot express. The
folder keeps the inherited word so that nothing has to be renamed twice, and
G8 below is whether the word survives.

## What is already true, so it is not re-derived

Read before proposing anything here. Each of these was measured or argued once
and the numbers live in the result files rather than in this paragraph.

**Tools are a flat bank today, not a chain.** `residency(active, rows)` in
`src/sieve/analysis/tool.py` takes a *list* of `(Tool, Form)` and unions what
they need — independent readers of one store, each fetching the source at its
own form. There is no place in the type system where one tool's output reaches
another.

**A tool has exactly two outputs and they have different fates.** A field is
image-sized, computed where it is drawn and discarded there; `tool.py` refuses
to store one and gives the reason. A reduction is one float per row into a
series, written by whoever admitted the inputs (ADR-0005). Nothing else leaves
a tool.

**The crop is not a tool.** It is a single rect on the session that every
`Tool.form_for(crop)` reads, and `gui/frame/window.py` sets it directly. It has
no field and no reduction, which is why it ended up as an attribute rather than
a step.

**A form is three degrees of freedom and that is load-bearing.** Rect, output
size, pixel format, built by crop → resize → convert in that order.
`frame/form.py`'s EXACT grade is defined as reproducing that construction byte
for byte, and the hunt tier's admission rule rests on it. Anything that cannot
be spelled as those three cannot be a form without re-arguing `grade`.

**Cost class is measured, never declared** (ADR-0007), and it lands differently
against the two input regimes the loop runs in. Any claim here about whether an
intermediate is cheap has to say which regime it was taken in.

**Derivation's answer already inverted once.**
`tool-experiments/02-form-derivation.py` found that deriving a wanted form from
a held one pays only where decode is expensive — the opposite of the intuition
that a warm cache always wins. That is the precedent for expecting an inversion
here rather than a constant.

## The goals

Ordered by what can falsify the idea soonest and cheapest, not by what is most
interesting. Each says what would count as a no, because a goal that cannot come
out negative is a description rather than a question.

### G1 — Can the proposed vocabulary express what already runs? — done

`01-the-explorer-as-a-graph.md`. Passed, with one addition to the vocabulary
(a per-recording/per-row rate axis), one constraint it produced that argument
had not (a reduce node must be co-scheduled with its field node or fields
become storable), and one thing it could not reach at all (masks, because
nothing working produces one). It also moved G6 and G7, noted below.

No code. Take the tool explorer, which works and has been measured, and write
what it does as typed nodes: the table, the fetch at a form, `absdiff` over its
two admitted rows, the field, the resize-then-colour-map, the canvas, and the
separate path through the reduction to a series and the band.

*A no looks like:* the re-expression drops something the explorer does, or needs
a node whose type is not in any proposed base set, or cannot say where the crop
attaches. Every ambiguity it exposes is one the base type set has to answer —
whether the colour map is a node or a display property, whether the reduction is
its own node or a second output, whether the series band is a node or a
primitive.

First because it costs an afternoon, and because the experiments below cannot be
written until the nodes have names.

### G2 — What must the substrate understand, and what may it not care about?

The claim being tested is that SIEVE ships a small closed set of base types —
the things it has to schedule, cache, display, or route an interaction to — and
that anything else is an opaque value two tools agree on privately. Falls out of
G1 rather than being decided ahead of it.

*A no looks like:* the closed set cannot be written down without a member that
exists only to make one imagined tool work, which is arguing from a tool that
does not exist; or a value SIEVE plainly must schedule turns out not to be
expressible in the set. Adding to this set later is the expensive kind of
change, which is why it is a goal and not an implementation detail.

### G3 — What does depth cost that the same work fused would not? — done

`03-joints-and-reuse.py`. Affordable, and priced in bytes rather than in calls.
An edge costs the *intermediate it names*, not the call that names it — the
figure scales with the array rather than staying flat, which is the opposite of
what dispatch overhead would do. At the analysis form a graph ten edges deep
spends a small single-digit percentage of a frame period on joints. Generality
is not what a graph costs; the arithmetic in it is.

Two mistakes of my own are recorded in the file rather than smoothed away. The
first version asserted that fused must beat staged and failed on a run where
noise put staged ahead — below the noise floor is a legitimate answer, so the
case now measures the floor and reports against it. The second read the 64x64
per-edge figure as if it held at any size, which says joints are free and is
true only at 64x64.

The overhead of generality, isolated from the work: per-edge dispatch, a copy at
each boundary, a cache lookup per node. Measured as the same arithmetic run as
one fused function against the same arithmetic run as three nodes, so the
difference is the architecture and nothing else.

*A no looks like:* that overhead is large relative to the node work and does not
amortise, so being general is itself what costs. Then the substrate can only
afford fused pipelines and an open plugin surface is unaffordable.

**The first version of this goal asked whether a three-deep graph holds rate,
and called that the single thing that could kill the idea. That was wrong on two
counts and is corrected rather than deleted, because the wrong version is the
more appealing one.** A graph that is slow is not an architecture that is
unaffordable: ADR-0007 already has a COMMIT class for a step that does not fit
the period — it shows what exists and says where none — and ADR-0008 says cost
is a fact. A slow graph degrades through machinery that already exists. Depth is
also not the variable: a chain containing `dis_flow` failing to hold rate says
only that flow is expensive, which
`docs/findings/2026.08.21-optical-flow-dominates-the-analysis.md` settled
already, and says nothing about three cheap nodes. What can implicate the
architecture is the cost of the joints, not the cost of the work.

### G4 — Do offsets compose, and does the residency set stay affordable? — done

`02-offsets-compose.py`. Yes to both, and the second answer is stronger than the
question expected: over a moving playhead the working set grows by the *added
reach* per node rather than by the multiplying point set, so depth is bounded by
the horizon plus the total reach. The numbers are in `results/` beside the run
that took them. It also priced what a lazy plan costs — planning by span instead
of by set over-fetches at depth, and that gap is what ADR-0008 calls a bug
rather than a price.

The `--broken` mode is the defect G1 found in running code rather than an
invented one, and two cases still pass under it, which is the finding underneath
the finding: an under-fetching plan is *cheaper*, so every instrument that asks
whether the working set is affordable reports an improvement. This class of
defect is invisible to cost measurement, which is the same shape as the overlay
that wrote its own series.

Still open from this goal: whether a node exists whose needs are not expressible
as offsets at all. That is the *no* that would take the plan away entirely, and
it cannot be settled without knowing what the downstream tools are.

**This is the one that can actually kill it, and it was ranked too low.** The
product constraint is not that graphs are fast, it is that they refill faster
than the video plays — which is only reachable by prefetching, which needs a
fetch plan computable before anything runs (ADR-0006). If a general graph can
only say what it needs once it gets there, the loop is demand-driven, prefetch
is impossible, and no amount of speed recovers it. That is architectural in a
way slowness is not.

Chained offsets should compose transitively: a node admitting `(-1, 0)` of a
node admitting four lags needs the union walked down to the source. The
arithmetic is checkable without running anything; what it costs to *hold* is
not.

*A no looks like:* the composed set for a realistic graph does not fit the
budget, so a plan that is correct is one nothing can honour — or worse, a node
exists whose needs are not expressible as offsets at all, which takes the plan
away entirely. `lag_mhi` is the load: it is already the only tool whose admitted
set is not its reach, which is the property that makes composition non-trivial.

A consequence worth naming rather than discovering. ADR-0007 says cost is
measured and never declared, so a scheduler deciding where to cache and what to
prefetch has no figures for a graph it has not run. It must measure and adapt,
and the first pass through a novel graph is always uninformed. Not fatal, and
another reason the account is not optional.

### G5 — Does recompute-versus-store invert between the two regimes? — done

`03-joints-and-reuse.py`. **It inverts**, which is the third of the three
outcomes and the expensive one: the control is necessary *and* a person cannot
be expected to know which side of it they are on.

Keeping an intermediate saves compute in proportion to the reuse a node
declares, so a scheduler can predict the saving from a declaration. What it
spends is frame-cache room, and an intermediate is the same size as a frame. The
case turns that into the one figure a scheduler could act on — the fetch cost at
which the two are equal — and this machine's decode sits above it while a chunk
or proxy read sits below. So the same node should be kept when its inputs come
from a derived file and recomputed when they come from a decode.

The threshold is a ratio of two timings and moves between runs by more than
either moves within one. It is an order-of-magnitude claim about which side the
tiers sit, not a number to branch on, and the file says so.

A methodological bug is recorded with it: the first version discarded five
warm-up positions against a reach of thirty, so the keeping policy was still
filling its cache while being timed, and keeping looked barely worth doing.

For an intermediate that a downstream node consumes, is it cheaper to recompute
it per row or to keep it? Measured in both input regimes, because
`02-form-derivation`'s answer inverted between them.

This one decides whether user-controlled caching is a real control:

- recompute always wins → the cache point is decoration and should not be
  offered
- storing always wins → there is no decision to give the user; the system does
  it
- it inverts → the control is necessary *and* the user cannot be expected to
  know which regime they are in, so something has to tell them

*A no looks like:* either of the first two, which is a cheaper product than the
third and worth finding out before drawing it.

### G6 — Is a value stored under a subgraph key reproducible from that key? — done

`03-joints-and-reuse.py`'s `key` case. Two graphs differing only in an upstream
parameter, with an identical sink: the subgraph key tells them apart and the
local key does not, filing both under one name so the second reads the first's
numbers. `--broken` is the local key, and it fails this case and no other —
which is itself the point, since nothing about cost changes when a value is
filed under the wrong name.

*Moved by G1.* The explorer already keys a two-node chain the way this rule
says a graph must — `Rig.set_tool` folds an upstream blur's parameter into the
downstream tool's params, and thence into the series key. So the rule is not a
proposal to be argued for but the generalisation of something running. What G1
also found is that the existing mechanism reads only the downstream tool's
`offsets`, so an upstream node with a reach of its own would have it silently
dropped from the fetch plan. The question is therefore composition, not
correctness at depth one.

The rule being tested is that a node's cache key must fold its entire upstream
subgraph and not only its own params. `Tool.key()` folds local params today and
deliberately excludes downstream ones, which is correct for a flat bank because
there is no upstream. The moment tools feed each other, a local-only key can
serve a value computed under different upstream parameters, and
`tool-experiments/05-provenance.py`'s invariant fails without anything going
red.

*A no looks like:* the `--broken` mode — a key folding only local params —
passing, which would mean the case is not reaching the substitution and is
demonstrating nothing. This is the rule that is invisible when wrong, so it is
the one that most needs a check that has actually failed once.

It is also what makes user-controlled caching safe rather than a footgun: with
content-addressed subgraph keys, a bad cache choice wastes time and space and
can never produce a wrong number.

### G7 — Does a region of interest propagate upstream without changing `Form`?

*Moved by G1.* This already happens for one node: `Tool.form_for(crop)` is a
tool declaring upward what form it wants, and the store is asked for that rather
than for whole frames. So the mechanism is in production and the open part is
narrower than it looked — whether two nodes declaring upward can be reconciled
into one fetch, and what happens when they disagree.

Crop does not transform data, it changes what gets fetched, so its parameter has
to travel backwards to the source reader. This is region-of-interest
propagation, and it is standard in image DAG engines — Nuke's performance story
is largely ROI and bounding-box propagation, and Fusion and Houdini's COPs do
the same. If it works here, crop is an ordinary node and `Form` keeps its three
degrees of freedom.

*A no looks like:* propagation needs a form the current three cannot spell — a
rotation, a polygon, a non-integer scale — at which point `grade`'s exactness
argument has to be re-opened, and that is a much larger change than a node.

### G8 — Is it a line or a graph, and does ADR-0003 survive the answer?

ADR-0003 puts the right pane's middle position on the pipeline and swipes
project → pipeline → step. A line has a next step; a graph does not, and two
inputs meeting at a node is not something a swipe can walk.

*A no looks like:* the structure G1 produces is a genuine DAG, in which case
either the swipe means something else at that position or ADR-0003 needs
revisiting. Named here so that it is a decision rather than something discovered
while building a pane.

### G9 — Where is the cost cliff, and should the graph show it?

Once a value is a float per row it is cheap — the tail is O(rows), not
O(rows × pixels). Masks are not: they are image-sized, and chained mask
operations are full-frame passes per row. So "downstream is cheap by
construction" is really "once you leave image space you are cheap", and the
moment a graph leaves image space may be the only place a user's cache decision
actually matters.

*A no looks like:* the cliff is not where this predicts, or is gentle enough
that nothing needs to show it.

### G10 — Can a person tell what they are choosing?

Not an experiment. A mockup, and it comes last because what it has to show
depends on G5: an account explaining an inversion is a different drawing from
one reporting a constant.

The prior art is discouraging and specific. Node compositors converge on a
manually placed cache node, and users are reliably bad at placing them, because
where the reuse boundary sits depends on what you are about to change rather
than on what the graph looks like. CellProfiler's model — a pipeline of modules
over image stacks, each declaring inputs and outputs, with per-module output
saving as an explicit user choice — is the closest referent on the analysis side
and has the same problem.

That does not argue against giving the control. It argues that ADR-0008's
account stops being a debugging instrument and becomes what makes the control
usable: the system cannot choose for them, but it can say what a node cost, how
many times it was fetched, and how many of those were avoidable. If that is
right, it promotes the ledger from an instrument nothing reads to the reason the
control is safe to offer.

## What this folder does not ask

**Whether a plugin API is worth having.** That is a decision, and these are
measurements that inform it.

**What the other crop-like tools are.** Naming them ahead of needing them is
arguing from tools that do not exist, which this tree's own record says has
failed twice.

**Anything about the chain's UI beyond G8 and G10.** Where a graph is edited is
a pane question and belongs with the panes.

## The rules it inherits

From `tool-experiments`, and they are the reason that folder's answers held:

**A tool that does not exist may be a workload and may never be evidence.**
Designs argued for from invented tools have failed to survive contact twice;
designs *tested* against invented tools have been useful every time. So the
graph here is built from loads that already exist — `absdiff`, `dis_flow`,
`lag_mhi` — and a threshold over `absdiff`'s output is a real minimal mask
rather than a hypothetical one. A chain experiment is exactly where this gets
violated by accident.

**A number claimed about the loop is taken in the loop**, and a number taken in
isolation says so.

**Every stored value names its writer, once, in the module that owns it.**

**Import `../decode-experiments/harness.py`,** repoint `harness.RESULTS` here,
keep every per-iteration sample, discard a stated warm-up. A case that could not
run says so in its notes; a silently absent case reads as a case that came out
equal. An invariant is checked with a `--broken` mode run alongside, because a
check that has never failed has no demonstrated power.

## Running

    uv run --group experiments python experiments/chain-experiments/<name>.py

Footage comes from `video-tests/`, gitignored. Derived files the other folders
make are inputs here; an experiment that needs one either finds it or makes it
and says which in its notes.
