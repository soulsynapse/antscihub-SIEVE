# SIEVE rewrite — design session record

2026-07-31, the day before implementation starts. A conversation between Kendrick
and Claude (Opus 5) working out the architecture of the rewrite from first
principles, starting from nothing but a description of the pipeline and GUI.

Kendrick's prompts are reproduced verbatim in [DESIGN-BRIEF.md](DESIGN-BRIEF.md)
and referenced here by number rather than duplicated. This document records the
reasoning on both sides, including the two places where a proposed design was
rejected and rebuilt, because the rejected versions explain why the final shape
looks the way it does.

Nothing here is code. It is the argument that determines the code.

---

## Exchange 1 — Contracts that can survive being changed

**Prompt 1.** SIEVE is a pipeline of steps plus a GUI. Every part depends on
every other part playing nice. How do you make the contracts updatable without
hand-writing everything forever as new functionality lands?

**Diagnosis.** Contract changes turn into codebase-wide sweeps because the
contract exists in five places at once: the GUI form, the file validator, the
executor's argument binding, the cache key, and the docs. Change it once, edit
five. The fix is to make it exist once and derive the rest.

```python
class BandpassParams(BaseModel):
    schema_version: ClassVar[int] = 2
    low_hz:  float = Field(0.5, ge=0, le=30, title="Low cutoff",  unit="Hz")
    high_hz: float = Field(8.0, ge=0, le=30, title="High cutoff", unit="Hz")
    order:   int   = Field(4, ge=1, le=8)

class Bandpass(Step):
    params   = BandpassParams
    consumes = ("timeseries",)
    produces = ("timeseries",)
    def run(self, ctx, params, inputs): ...
```

The GUI form is a walk over `model_fields` picking a widget per type and
constraint. The validator is `model_validate`. The cache key is the serialized
params. Adding a step is one file and zero edits anywhere else.

**The rule that makes it hold, stated early because it gets violated first:**
the GUI may know about field *types*, never about *steps*. The moment
`if step.type == "bandpass"` appears in the renderer, the property is gone. When
a step needs a widget the generic renderer can't produce — an ROI drawn on a
frame, a threshold picked off a live histogram — you add a new *field type* that
the renderer learns once and every future step can use. Field types grow slowly
and deliberately; steps grow fast and for free. That asymmetry is the design.

**Versioning the file on disk.**

- `schema_version` per step, never one global version — a global number entangles
  every step's migration with every other step's.
- Migrations are an append-only registry of pure `dict → dict` functions keyed
  `(step_type, from_version)`. Load = read raw dict → run the chain → *then*
  validate. Never validate first; an old file by definition won't validate
  against the new model.
- **Additive-only discipline** (the protobuf lesson): new fields carry defaults,
  a removed name is never reused for a different meaning, and a rename is
  add-new + migrate + deprecate.
- **A fixture corpus**: one real pipeline file per historical version checked in,
  with a test that loads all of them. Migration chains break silently otherwise —
  you write v3→v4 correctly and don't notice it broke v1→v2 six months later.
- **Unknown-field preservation**: an older build opening a newer file must
  round-trip fields it doesn't understand. Without this, opening a colleague's
  file and hitting save destroys their data with no error. Refuse to *execute* a
  file whose version exceeds what you know, but still display it.

**Conformance suite.** One parametrized test over the step registry: every step
round-trips its params, has defaults that validate, has resolvable port types,
and migrates cleanly from every historical version. Register a step, it's
covered.

**Flag raised on the premise.** "The pipeline file owns the complete or
incomplete steps the user chose" fuses two different objects. *Intent* (which
steps, what params, what order) is durable, user-edited, diffable, belongs in
version control. *Progress* (what ran, when, producing what) is derived and
disposable. Fused, every run mutates the config file, you can't diff two
pipelines to ask whether they're the same recipe, and every schema migration has
to reason about run-state semantics too.

Split them. `pipeline.yaml` is intent only. Run state is a sidecar ledger keyed
by a content hash of each step's *resolved* inputs: params, plus upstream output
hashes, plus an `impl_version` on the step class. "Complete" stops being a stored
boolean and becomes a query. Resumption comes free, and so does correct
invalidation — change a param, the hash changes, downstream steps become
incomplete automatically with nobody writing dirty-propagation logic. Snakemake,
Nextflow and DVC all landed here independently.

The catch: `impl_version` must be in the hash and must be bumped by hand, or
you'll serve cached results from a filter you've since fixed. Hashing source text
is fragile — whitespace churn invalidates everything and it misses changes in
imported helpers.

**Open fork left at the end.** If the GUI is a separate process from the
executor, the step declaration is also a wire format, which pushes toward JSON
Schema as canonical with Pydantic as one consumer rather than Pydantic as the
source of truth.

---

## Exchange 2 — What the GUI owns, what a step is called, and how fan-out works

**Prompt 2.** Left pane is a context viewer (project info, or a video player);
right pane is configuration owned by the step. The step passes display
information leftward and receives user interaction — drawn crop boxes — back as
saved parameters. It also takes SIEVE preferences. It declares outputs, which may
be pure information (coordinates) or actual work (running the crops), and
downstream steps declare which they accept. Navigation: up/down between steps,
left/right between equivalents at the same DAG level. Pressing down offers only
steps whose requirements are fulfilled. Also: what should "steps" be called?

Three pushbacks.

### The coordinates-vs-execute fork doesn't need to exist

Make the output a handle: `CroppedVideo = (source_handle, roi, transform)`. It
satisfies the `Video` type. Downstream steps don't know or care whether frames
exist on disk; whether they do is a *materialization* decision made by the
executor from a preference, a size heuristic, or the user hitting "bake." That
deletes the flavor picker, the downstream `accepts` variants, and the swap UI.

It also fixes a leak: "subsequent steps don't know anything other than what
they're given" is false in the coordinates flavor, because coordinates alone
can't render — the step also needs the source video from *somewhere*. Either you
smuggle in ambient context and the isolation claim quietly stops being true, or
every handoff becomes a bundle. Values carrying their own lineage keeps the claim
literal.

Where users genuinely should pick between outputs is when a step produces things
not derivable from each other — a tracker offering centroid trajectories *and*
segmentation masks. Two named ports, both always present; the user chooses what
to connect, not what the step should bother computing. Derivable relationships
are adapters the framework inserts, never questions posed to the user.

### Fan-out is arity mismatch, not a special power

Crop doesn't "produce replicates" as a capability. It consumes one `Video` and
produces one `ROISet` whose length follows the boxes drawn. The next step
declares it consumes `Video`, is handed a set of six, and the framework maps it —
six tasks, six sibling results. Left/right navigates the map index. Fan-out is
one rule in the executor instead of a concept every step author must learn, and
any future step that happens to return a list gets branching without opting in.

**The biggest open question this exposes:** configuring a step while sitting on
replicate 3 must apply to all six siblings, not just that one. One step
definition, mapped. Otherwise the user configures N times and the pipeline file
grows combinatorially. Left/right then means "preview this same configuration
against a different branch," with per-branch override as a deliberate, visibly
marked exception. If it defaults to per-branch, you can never go back.

Secondary: down opens a picker of eligible steps and left/right means siblings,
so the two want the same axis when a level is empty. Decide now whether the
picker is a mode or gets its own keys.

### The left pane is bound fields, not an event channel

Do not build "the step receives interaction events from the canvas and turns them
into parameters." Build: **overlays are editors bound to a param field**, exactly
like the widgets on the right. `regions: list[Rect]` gets an `ROIField` on the
right and a `RectOverlay` on the left; drawing a box and typing coordinates are
the same mutation at the same path. Undo, validation, dirty-tracking and
serialization all work with no step-author code. If the canvas instead emits
events the step handles, every step owns its own state reconciliation and the
left pane loses the derive-everything property the same way `if step == "crop"`
would lose it on the right.

The canvas knows a small vocabulary — rectangle, polygon, point, polyline,
timeline span, mask brush — and steps compose from it. A step never ships
rendering code.

### Naming: Tool / Step / Task

The discomfort is diagnostic: one word is naming three things, which is also why
"what any given step does varies pretty wildly" feels true.

| Term | What it is |
| --- | --- |
| **Tool** | The installed type. Crop. Param schema, right-pane workspace, declared ports, a `run`. This is what gets versioned and migrated. |
| **Step** | A tool placed at a level in a particular pipeline with its params filled in. What the pipeline file stores; what up/down navigates. |
| **Task** | One realized execution: a step × one branch index × resolved inputs. What the executor runs and what the content hash keys. |

Beyond taste, the split lands exactly on the intent/state boundary from
Exchange 1 without being forced to: schema versions live on Tools, the pipeline
file is a list of Steps, the run ledger is keyed by Tasks. Two independent lines
of reasoning producing the same seams is evidence the decomposition is right.

### One boundary to fix on day one

**If it can change an output value it is a param** — pipeline file, task hash.
**If it can only change presentation or performance it is a preference.**
Anything ambiguous is a param. Otherwise the same pipeline file produces
different results on two machines and finding out why takes a very long time.

---

## Exchange 3 — The inefficiency between steps

**Prompt 3.** Downsampling is next. Should it be its own step or an extension of
crop? The decomposition resists basic DPP construction — the combined step
captures efficiency that is in neither, and at ten steps that compounds. Name it.

**The name.** The cost function isn't separable across the step boundary, so the
step decomposition has no optimal substructure. The optimization that recovers it
is **operator fusion**; the intermediate-elimination framing is
**deforestation**; in pipeline tools it appears as the materialization problem.

**The sharper statement:** DP doesn't fail, the state space is wrong. DP over
*fusion regions of an op graph* has perfectly good optimal substructure; DP over
user-authored steps doesn't, because steps are units of intent and UI, not units
of execution. This is why "should downsample be part of crop" is unanswerable —
no fixed step boundary works, every boundary forfeits some cross-boundary
optimization, and redrawing it only moves which optimization is lost.

**The fix is a second layer.** The logical graph the user authors is not the
physical plan the executor runs. Halide's algorithm/schedule split, a query
planner's logical→physical lowering, XLA/TVM fusion, ffmpeg's filtergraph. Steps
stay separate because the user's intent is separate; the planner fuses them
because execution shouldn't care.

**What that requires.** `run()` cannot be an opaque video→video function; if it
is, fusion is impossible forever. Steps emit **ops in a small algebra**:
geometric (affine sample), temporal (frame index map), pointwise (per-pixel), and
opaque (a fusion barrier, which is fine — it bounds the regions).

Two rewrite rules pay for the layer. Composing adjacent geometrics into one
matrix means one resample instead of two. Pushing temporal decimation *upstream*
past spatial work means never decoding a frame you're about to discard — 10×
temporal decimation is a 10× cut in crop work, and neither step can do that
alone. That second rule is the existence proof for the layer.

**Two consequences.** Hash the *logical* recipe, not the physical node, or every
planner improvement silently invalidates every cached result on disk. And
fusion changes pixels — crop-then-downsample as two resamplings is not
numerically identical to one composed affine sample. For a scientific instrument
whose premise is interpretable filtering, results must not depend on invisible
planner decisions: define semantics at the logical level, require the planner to
be semantics-preserving within a stated tolerance, and ship a preference that
disables fusion entirely so a reviewer can confirm the fast and naive paths agree.

Build the IR immediately; the planner can be two rules for a long time. The IR is
what's expensive to retrofit.

---

## Exchange 4 — Showing a multi-input, sequentially-computed result

**Prompt 4.** Background subtraction, then background-subtracted tracking.
Tracking needs two inputs and the downsampling must have happened. How does the
user scrub and see how the centroid tracking worked?

**The real obstacle isn't the two inputs.** Background subtraction and tracking
are the first ops that aren't random-access, and scrubbing is a random-access
operation. Everything prior is pure per-frame, so frame 5000 is computable from
frame 5000 of the source. An adaptive background model is sequential; tracking is
worse, because identity association across frames is irreducibly sequential.

So the op algebra needs a second axis: **random-access vs. sequential**, with
sequential ops as sweep barriers.

**The saving grace:** sequential ops produce *tiny* outputs. 100k frames of
tracking is a few MB of centroids; a background model is one plate. So sequential
ops sweep once and persist their small result, and everything downstream
collapses back to random-access because the expensive temporal state has been
reduced to a table you can index by frame.

The preview is therefore a composite of two evaluation modes: **the base image
pulled lazily through the fused geometric chain, plus overlay geometry looked up
by row from the materialized track table.** Scrubbing to frame N is one
decode-and-transform plus one array index.

**Coordinate frames — what "the downsampling needs to have happened" means.**
Centroids live in crop∘downsample space; users will want them over the
full-resolution source to check whether the tracker is on the animal or on a
reflection. Geometric ops are invertible affines, so mapping an annotation
between any two nodes is composing and inverting. The IR built for fusion pays
for reprojection for free.

**The highest-value affordance in the whole UI:** let the user swap the base
layer without touching the step's configuration. Same tracks over the raw source,
the cropped source, the downsampled video, the foreground mask, the background
plate. "The tracker lost the ant at frame 3000" gets diagnosed in seconds by
flipping between mask and source — you see immediately whether subtraction
dropped the animal or association broke. The step proposes a default base; the
user's choice is a view setting, never a param, never in the task hash.

**Honesty constraint.** A 1px centroid error at 4× downsample is 4px at full res.
Render the marker at the size of one source-space pixel, not a fixed dot. A
display that oversells resolution is a real defect in a tool selling
interpretability.

**Parameter tuning is the same problem.** "Run this on frames 2000–2500 at
quarter resolution and let me scrub it" is not a separate preview system — a
subrange is a temporal op and a resolution cut is a geometric op, so it's the same
recipe with two ops prepended and the same executor path. Preview literally
cannot diverge from production output, which is a correctness property, not a
convenience. Stream sweep results into the table as they arrive with a coverage
band under the scrubber.

**Executor contract addition.** Two entry points over one IR:
`render(node, frame_index)` for pull-based single-frame evaluation, and
`sweep(node, range)` for sequential ops. Make the pull path primary and treat
batch materialization as a coarsening of it. Build batch-first and scrubbing only
works after full materialization, so you bolt on a second, subtly different
rendering path for previews — and "the preview looked fine" becomes a support
burden. Practical note: seeking compressed video is expensive and scrubbing
hammers it, so an LRU frame cache keyed on (logical value id, frame index) with
directional lookahead is required for the pull path to feel correct.

---

## Exchange 5 — Who owns execution, and the first design being rejected

**Prompt 5.** Who *owns* those two methods? The operations a user might request
explode combinatorially per feature. Can the step contract own them all? How does
the GUI know what to produce or reuse?

**Answer given:** nobody owns them per-step. A tool is a compiler front-end —
params in, op subgraph out — with no `render`, no `sweep`, no knowledge either
exists. The runtime owns both, dispatching on **op class**, never on step
identity. You never write a crop×downsample fusion or a bgsub×flow renderer.
Composition is handled by the algebra and never enumerated by a person.

This was framed as three registries — Types, Ops, Tools — with each feature
landing in exactly one, and the claim that threshold-over-change-energy costs zero
new ops, morlet-over-appearance-energy zero, and dense optical flow one op plus
one type.

Failure modes named alongside it: lowering makes the declared output type an
unchecked claim; the random-access classification is a correctness claim nobody
verifies and getting it wrong produces wrong scrub frames silently; the executor
actually has a third job (the value store, with invalidation); type-dispatch on
the GUI is where the architecture will erode when a bespoke visualization is a
two-hour job and extending the vocabulary is a two-day one; multi-input tools need
a port-binding UI that doesn't exist yet.

### Prompt 6 rejects it

> *"I suspect an agent would write spaghetti code every time... Your solution
> makes extending the repo a headache for all future edits."*

**Correct, and the tell was in the answer itself:** it required a conformance test
to check whether an op *honestly declared itself* random-access. If correctness
depends on a flag set by hand, an agent sets it wrong and the failure is
invisible. The design was a compiler, and it made every future contributor pay
compiler tax before shipping anything.

### The rebuilt version

A step becomes one file and nothing else:

```python
class Downsample(Tool):
    class Params(BaseModel):
        factor: int = Field(2, ge=1, le=16, title="Downsample factor")

    def lower(self, p) -> Op:
        return Resample(scale=(1, 1/p.factor, 1/p.factor))   # (t, y, x)

    def view(self, p, out) -> View:
        return Image(out)
```

If adding a feature ever requires touching a second file, the architecture has
failed and you stop and fix it rather than proceed.

**Classification by shape, not declaration.** Delete the flags. There is no
fusion class field and no random-access field. There are four op shapes, and
which one you implement *is* the classification because the others aren't
expressible in that signature:

| Shape | Signature | Covers | Why the class is forced |
| --- | --- | --- | --- |
| `Resample` | coordinate map over (t, y, x) | crop, scale, rotate, trim, decimate, retime | nowhere to put state |
| `PixelMap` | value → value, no neighborhood | colorspace, gain, normalize, gamma | no neighborhood access |
| `Window` | frame N from [N−a, N+b], bounded | optical flow, temporal convolution, morlet | bounded by signature |
| `Fold` | `(state, frame) → (state, output)` | adaptive background, tracking | state parameter is explicit |

Nobody can mislabel a stateful op as random-access, because to be `Resample` you
must write a function with no state parameter. The bug class is unrepresentable
rather than tested for. Unifying crop and decimate as coordinate maps over (t, y,
x) also turns "hoist decimation upstream" from a rewrite rule into plain
composition.

A bonus that separate steps can't get: composing the coordinate maps first and
deriving the anti-aliasing footprint from the *total* Jacobian gives one
correctly-filtered resample. Two passes filter twice and soften the result — the
fused path is the more correct one, which matters for output meant to be
defensible.

**The naive path is the default.** `Opaque` — frames in, frames out, total
barrier, never fused — is a fifth shape for when you don't want to think. Always
correct, always slow. A contributor who has read nothing about the algebra ships
a working step in an afternoon; later someone reshapes it into a `Resample` and it
gets fast with zero change to the tool's public surface. **Performance is opt-in;
correctness is default.** The rejected design inverted this.

**Tools cannot reach the runtime.** `lower()` and `view()` are pure functions. No
executor handle, no context object, no callbacks, no mutable state outside
`Params`. The strongest lever against agent-written spaghetti, because the wire
that would create coupling doesn't exist to be grabbed. Registries become
*derived* — scan the tools package at import — so nobody maintains a table and
nobody forgets to update one.

**Delete invalidation rather than owning it.** Content-address every value by its
recipe hash, store by hash, never invalidate. A param change doesn't invalidate a
result; it produces a different hash that isn't in the store yet. Old entries age
out under a size budget, undo is free, and the hardest bug category stops
existing.

**The view vocabulary is closed, not extensible.** Image, mask, points, paths,
vectors, regions, series strip. Framing it as an extension point is what
guarantees erosion, because extension points advertise that extending is the
intended move.

**Testing becomes closed too.** One property test asserts any chain of
`Resample`s is bit-identical fused and unfused; one asserts `Window` ops give the
same frame N cold as during a sweep. Two tests covering every op that will ever
be written.

---

## Exchange 6 — It was a maintainability problem all along

**Prompt 6, second half.** Steps are derivative of the executor; the executor is
coupled to the kernel; kernel capability grows → executor offerings grow →
possible steps grow. And: even if every combination is possible, why aren't most
utilized? Why are all products reachable?

**Both questions have the same answer — the constraint lives at authoring time,
so the executor never faces the explosion.**

*Why most combinations aren't utilized:* the space of possible pipelines and the
space of built pipelines differ by orders of magnitude, and the second is
concentrated to near-enumerable. Behavioral video analysis has maybe a dozen real
idioms. A general planner optimizes a *space*; you only ever need to optimize a
*trace*. That's the maintainability difference: a planner must be **complete**,
so every rule interacts with every other and none can be removed without
reasoning about the whole. A peephole set must only be **correct** — each rule is
a few lines, independently justified, independently tested against the naive
path, independently deletable. Add them when profiling says a path is hot.

*Why all products are reachable:* construction is incrementally validated and
nothing is destroyed. A step can only be placed where its requirements are already
satisfied, so every constructible pipeline is well-formed by construction — no
validation pass, because an invalid pipeline can't be typed into existence. And
since everything is content-addressed and retained with lineage, no earlier
product becomes unavailable. "Threshold change energy to isolate blocks, then
bg-sub track on those" isn't novel machinery; it's branching from an existing
product and attaching a step whose inputs it satisfies. Navigation, not
engineering.

So the executor is a catalog plus a naive evaluator plus a handful of peephole
rules. Not a planner.

**Reconciling "steps request from the executor" with "tools are pure":** they're
compatible provided requests are **declarative**. A step naming a capability from
the catalog is not a step holding a runtime handle. The first gives an agent one
document to read and compose from; the second couples them permanently.

**Four conditions for this holding up.**

1. **Instrument from day one.** The peephole approach is evidence-driven and the
   evidence can't be reconstructed later. Log which pipelines get built and where
   wall-clock goes.
2. **Give the catalog an admission rule** — see below.
3. **Show ineligible steps, greyed, with the missing requirement named.** If only
   valid continuations are offered and everything else is hidden, a user who wants
   something unoffered can't learn why and concludes SIEVE can't do it.
   Authoring-time constraint is right; authoring-time invisibility is its failure
   mode.
4. **Don't let fast paths become the only paths.** The head is where engineering
   effort belongs, but the users are scientists and the tail is where research is.
   Morlet over appearance energy is a tail pipeline a grad student runs twice and
   publishes from. The naive evaluator isn't a fallback for those cases — it's the
   product surface.

### The catalog admission rule

The catalog's value is not coverage; it's that *checking it is cheaper than
reinventing*. That depends on size and nothing else. An unbounded catalog produces
exactly the reinvention it exists to prevent.

The growth mechanism: writing crop, you need to clamp coordinates to frame
bounds, it feels obviously general, into the catalog it goes. Nobody else ever
needs it. Now there's a one-caller entry at the same visual weight as fifty-caller
entries. Agents do this far more aggressively than people, because "add a
capability to the executor" reads as architecturally correct.

Clutter is the mild version. The real damage is that with one caller you don't
know the shape, so you generalize from n=1 and get the parameters wrong. The
second caller then either reshapes the entry (touching the first caller) or adds
`clamp_to_bounds_padded` beside it. They add the second one every time, and that's
how APIs reach twelve near-identical variants. Waiting for the second caller means
designing the abstraction with two examples in hand — the jump from n=1 to n=2 is
the difference between deriving a shape and guessing one.

Entries are also effectively permanent, since removal means auditing callers you
can't enumerate. Growth is monotonic and readability decays with it.

**Make it a test, not a convention:** fail the build when a catalog entry has
fewer than two call sites. Same principle as classifying ops by shape — the wrong
thing becomes hard rather than discouraged. With a waiver annotation, because
genuine kernel primitives legitimately arrive with one caller, and without the
escape hatch people satisfy the rule by writing throwaway second callers.

---

## Exchange 7 — The unifying mechanism

**Prompt 7.** The fast path exists conditionally — change energy over morlet, or
over appearance energy, or LK as a derived result. Name the approaches that
capture the fast path automatically once it exists, without crippling the slow
path, and that unify every boundary: pipeline↔step, step↔GUI, user↔new step,
kernel↔executor, executor↔step. Two decent candidates.

### Candidate 1 — multiple dispatch, with provenance in the type

```python
def change_energy(x: Tensor)           -> CE:   ...  # general, always works
def change_energy(x: MorletTensor)     -> CE:   ...  # fused, exists because someone wrote it
def change_energy(x: AppearanceEnergy) -> CE:   ...
def derive_lk(x: ChangeEnergy[Morlet]) -> Flow: ...  # fast because the source is known
```

Adding a fast path is adding a method. No caller changes, no registration, no
planner, no `if`. The general method is the floor and never goes away, so the slow
path can't be crippled. The executor doesn't *prefer* the fast path by policy — it
calls `change_energy(x)` and most-specific-wins does the preferring.

**The provenance-in-the-type move is what reaches the conditional case.** A fast
path for "change energy over morlet" is a property of how the tensor was *made*,
not of its values. If Morlet's output is `Tensor`, dispatch can't see it; if it's
`MorletTensor`, the specialization is free. That is the planner, replaced by the
type lattice — and it's why nobody could point at the file where the optimization
decision happens. There isn't one.

Every boundary is the same mechanism: kernel→executor and executor→step are
methods called generically; step→GUI is `view(value)` dispatching on value type;
pipeline→step eligibility is "does an applicable method exist for these argument
types," so the dispatch table *is* the eligibility check; adding a step is
defining a type and methods, with no registry because the method table is built by
writing code. This also dissolves the catalog problem — the catalog becomes the
set of generic functions, discoverable by asking the runtime, unable to drift from
reality because it *is* reality.

### Candidate 2 — one algebra, many interpreters

Reify the request as data and let each consumer interpret it (tagless final, or a
plain op AST with a fold). The executor is an interpreter, the GUI is an
interpreter, the hasher is an interpreter, the eligibility checker is an
interpreter, the pipeline-file printer is an interpreter. Five behaviors from one
description, and a sixth — a cost model, a provenance report for a methods
section — touches nothing existing. The fast-path story is a second interpreter or
one overridden case, which is how a GPU path lands without a single step file
changing.

### Recommendation and costs

Use both, split the obvious way: reify the request as data, dispatch on its type
to select the implementation. Dispatch handles *selection*; interpreters handle
*the several things you do with one description*. Start with dispatch, since
that's what makes fast paths accrete without central edits.

Dispatch's failure mode is action at a distance — a method in a file you've never
opened changes what runs here, ambiguities between equally-specific methods are
real, local reasoning is lost. Mitigations: shallow type lattice, ambiguity as a
build-time failure, and a total fallback on every generic function. Python has no
native multiple dispatch (`singledispatch` is single-argument), so it's `plum` /
`multimethod` or ~100 hand-rolled lines of type-tuple dispatch — the latter is
defensible and gives you the ambiguity check.

The interpreter approach's failure mode is that the algebra becomes unchangeable,
since a new case means updating every interpreter. Keep it to the four op shapes
plus the opaque escape hatch; let it reach thirty cases and it's the god-object
catalog with extra steps.

Rewrite rules / equality saturation over an e-graph was named as a third
candidate and set aside: it buys fast paths that depend on *patterns across
multiple nodes* rather than the type of one value, which provenance-in-the-type
covers at a fraction of the machinery. Reaching for an e-graph in a repo this size
is the road back to Mathematica.

---

## Exchange 8 — Kendrick's answer, and why it's the better core

**Prompt 8.** Equivalence is established by testing inputs against reference
objects with a statistical test for how different any solve is from another.
Methods declare what they do and their eligible types. Signatures can be clustered
mathematically, so identical ones surface for merging or get flagged with why they
stay separate; a fast path declaring equivalence to multiple paths is checkable;
the executor picks backwards from a speed ranking. Second answer: the
handshake/plugin approach, where a fast path self-validates and is preferred
because it exists — suspected to be nice only in the short term.

**Assessment: the first answer is better than the model's, and it fixes the hole
the model kept walking past.** Three times an unverified declaration was flagged —
the random-access flag, the output type of a lowering, the catalog entry's claim —
and three times the fix was a conformance test bolted on afterward. Kendrick made
verification the *registration condition*. A method doesn't declare equivalence;
it earns membership by passing against the reference. That's the same move as
classifying ops by shape instead of by flag, applied to semantics rather than
structure.

Second improvement: ranking becomes measured rather than proxied.
"Most-specific-wins" uses specificity as a stand-in for cost and is wrong whenever
a specialization is narrower but not faster.

**The synthesis:** a generic function is an equivalence class, its members are
implementations, membership is earned against the reference member, and selection
among applicable members is by measured cost.

This dissolves dispatch's ambiguity problem. Ambiguity is only dangerous because
two equally-specific methods might behave differently; if membership requires
verified equivalence, any applicable method is substitutable by construction, so
you take the fastest and never think about it again.

It also supersedes the catalog admission rule. A build-time check on call-site
counts is a crude social proxy; behavioral clustering detects duplication
*semantically*, including duplicates that don't look alike in source.

**On the second answer:** the instinct was right, and the reason is sharper than
"short term." The handshake/plugin version is the first answer with falsifiability
removed. Each fast path self-validates, nothing validates across them, and
"preferred because it already exists" means the *first* fast path written wins
rather than the best — no comparison, so you never learn whether it's even faster.
It's the declares-itself-correct pattern that has failed at every layer of this
design already.

### Four objections raised, and their disposal (Prompt 9)

**1. Tolerance doesn't compose.** *Objection:* two ops each within 1e-6 are not
jointly within 1e-6, and through a tracker a sub-threshold pixel difference flips
a detection and tracks diverge completely.

*Kendrick:* chaos requires sensitivity **and** folding. Sufficient damping gives a
well-behaved system, and history-dependent sensitivity is known when the feature
is added — one flag in the contract.

*Resolution:* correct, and it upgrades. Most of the algebra is contracting or
neutral — anti-aliased resampling is averaging, normalized temporal convolution is
contracting, pointwise monotone maps are Lipschitz with a known constant — and
composition of contractions is a contraction, so tolerance *does* compose over
that subset with the bound being the product of the gains. It fails exactly at
thresholding (infinite gain at the boundary) and association (a discrete flip).
Better than a boolean flag: have the harness *measure* the Lipschitz constant by
perturbing inputs by ε on the reference corpus, and measure a threshold op's
*boundary mass* — the fraction of the input distribution sitting near the decision
edge. End-to-end divergence is then bounded from measured numbers rather than
declared ones, which is the same principle as everything else here. Residual:
boundary mass is a property of (op, corpus), not of the op alone.

**2. The reference corpus must be adversarial.** *Objection:* fast paths agree on
clean footage and diverge on low SNR, motion blur, compression artifacts and
near-threshold contrast — exactly where SIEVE has to be trustworthy.

*Kendrick:* this is the feature, not the problem. The same tooling the executor
uses to pick defaults is tooling the **user** runs on their own pipeline to
discover that a massive computation is equivalent to a trivial one. Frame
decimation to 1 frame per 3 minutes giving statistical equivalence to 30fps, once
detection thresholds on the channel discriminator run, is what turns SIEVE from a
convenience into a hypothesis discriminator — it's what makes a six-month video
recording study possible at all.

*Resolution:* accepted, and it is the strongest idea in the session. Two
qualifications that make it sound rather than dangerous:

- The user's test is **inferential**, not implementational. "Does this produce the
  same numbers within tolerance" and "does the statistic I care about have the
  same distribution" are different objects needing different tests (a norm on
  outputs vs. TOST or a distributional distance on the summary). Decimation to
  1/5400 frames is equivalent for *total foraging events per day* and
  catastrophically non-equivalent for *inter-arrival time distribution* — same
  footage, same decimation, opposite verdicts. The tool must make the user name
  the target statistic and must refuse to report "equivalent" unqualified. It
  must also carry the scope of the claim: equivalence established on daytime
  high-activity footage is not established for nighttime.
- It is a **multiple-comparisons machine**. Sweeping decimation factors for the
  largest one still "equivalent" is p-hacking's shape with computational savings
  as the incentive instead of significance. Build in the safeguard or it won't
  happen: discover the reduction on a pilot subset, confirm on held-out footage,
  report how many configurations were tested and both results.

**3. Speed ranking isn't a scalar.** *Objection:* a path that wins at 4K loses at
480p; one that wins on a workstation GPU loses on a field laptop.

*Kendrick:* that's the third valuable use of the implementation, not a problem.

*Resolution:* correct. Per-machine, per-input-shape measurement is a performance
model users can query — how long will this pipeline take on this machine for this
footage. It composes with (2) into the actual product: *"this run will take 40
hours; here are three reductions that preserve your target statistic and take 20
minutes."*

**4. Stochastic methods break the fingerprint.** *Objection:* random
initialization makes behavioral signatures noisy, so clustering misses real
duplicates or flags false ones.

*Kendrick:* known limitation — it's why the discriminator is statistical.

*Resolution:* right; if comparison is distributional rather than pointwise,
stochasticity is the native case. Keep seed recording anyway, since
*reproducibility of a published result* is a separate requirement from
*equivalence testing*.

**One process point that survives all four:** verification must be run by the
harness on registration, never written by the contributor. People who hand-write
their own equivalence tests write ones that pass, and you end up having certified
nothing while feeling certified — worse than no verification.

---

## Exchange 9 — The signatures are also a regression baseline

**Prompt 10.** The equivalence signatures are tests, so changing how something is
written leaves a baseline in git history that can be compared automatically.

Correct, and free once the harness exists: a signature is a golden master with a
statistical comparator instead of an exact one. A refactor intended to preserve
behavior gets checked against its own history without anyone writing a test for
the occasion. The only thing that makes it meaningless is a signature not pinned
to a corpus version — `(method version, corpus version, tolerance)` or the diff
says nothing.

That closes the design. The architecture was then written up as
[ARCHITECTURE.md](../ARCHITECTURE.md): seven components, the authoring flow, the
execution flow, and five invariants stated as imperatives with the failure mode
attached to each, so it reads as something an agent consults before writing code
rather than as an explanation after the fact.

The shape of the repo — directory layout, module boundaries, packaging — was
deliberately left undecided. Only the components and their interactions are
settled.

---

## Where things stand

**Settled.**

- Tool / Step / Task as three distinct concepts, mapping onto schema versioning,
  the pipeline file, and the run ledger respectively.
- Intent and progress live in separate files; progress is a content-addressed
  ledger, and invalidation is deleted rather than implemented.
- Params vs. preferences: anything that can change an output value is a param.
- Steps are pure — `lower()` and `view()` with no runtime handle.
- Ops classified by shape (`Resample` / `PixelMap` / `Window` / `Fold` /
  `Opaque`), never by flag. `Opaque` is the always-correct default; performance is
  an opt-in later refactor with no change to a tool's public surface.
- The logical graph the user authors is not the physical plan the executor runs.
- Peephole rules, not a planner. Instrument from day one to know which paths are
  hot.
- Left-pane overlays are editors bound to param fields; the overlay vocabulary is
  closed.
- Base-layer swapping is a view setting, never a param.
- `render(node, frame)` primary, `sweep(node, range)` for `Fold` ops; batch is a
  coarsening of the pull path.
- Multiple dispatch with provenance in the type as the selection mechanism, over
  a reified op description that several interpreters consume.
- Equivalence is **earned by measurement against a reference corpus**, not
  declared. Selection among verified-equivalent implementations is by measured
  cost.

- Equivalence signatures double as a regression baseline in git history, provided
  they are pinned to a corpus version.

**Open.**

- The shape of the repo: directory layout, module boundaries, packaging. Nothing
  about it was decided here.
- Whether the GUI is in-process with the executor. If separate, the step
  declaration is also a wire format, pushing toward JSON Schema as canonical.
- Whether the eligible-step picker is a mode or gets its own keys, given
  left/right already means siblings.
- Per-branch parameter override: confirmed as the deliberate exception, but the
  UI for marking and displaying it isn't designed.
- The port-binding UI for multi-input tools — with six replicates and three
  candidate videos, type matching narrows the candidates but won't get to one.
  This is the next real UI question after crop lands.
- Composition of the adversarial reference corpus, and the tolerance policy per
  signature.

**The milestone.** Crop landing as a contracted step, working flawlessly, is the
signal that there won't be another rewrite. Downsampling immediately after is the
first real test of whether steps compose. A beer is owed at the first of those.
