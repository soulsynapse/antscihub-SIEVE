# chain-experiments

Where SIEVE finds out what happens when a tool's output is another tool's
input. `decode-experiments` settled what a frame costs to get,
`storage-experiments` what it costs to keep, and `tool-experiments` what one
tool costs when it rides along on a fetch. All three measured a *single*
consumer. This folder is the layer all three deferred, and it is still a plan:
nothing here is settled yet, and the sections below are what it is for rather
than what it found.

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

### G1 — Can the proposed vocabulary express what already runs?

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

### G3 — Does the interactive loop survive depth?

The product constraint is the tuning loop: drag a slider, graphs refill faster
than the video plays. It holds today with one tool reading the store. Whether it
holds with three nodes deep is unmeasured and is the single thing that can kill
the whole idea.

*A no looks like:* a three-deep graph cannot hold rate on the machine this is
built for. If that is the answer, an unopinionated substrate is unaffordable and
SIEVE has to be opinionated — a fixed pipeline with fused operations — and the
plugin vision goes with it. Better to hit that before a plugin API exists than
after.

### G4 — Do offsets compose, and does the residency set stay affordable?

Chained offsets compose transitively: a node admitting `(-1, 0)` of a node
admitting four lags needs the union walked down to the source. The arithmetic is
checkable without running anything; what it costs to *hold* is not.

*A no looks like:* the residency set for a realistic graph does not fit the
budget, so a fetch plan that is correct is one nothing can honour. `lag_mhi` is
the load for this — it is already the only tool whose admitted set is not its
reach, which is the property that makes composition non-trivial.

### G5 — Does recompute-versus-store invert between the two regimes?

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

### G6 — Is a value stored under a subgraph key reproducible from that key?

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
