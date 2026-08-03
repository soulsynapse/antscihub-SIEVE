# PAR-0005 — Shape algebra and classification by form

Status: Proposed
Date: 2026-08-03

## Outcomes

What this system looks like working as intended: a contributor who has
read nothing about the algebra ships a correct op in an afternoon, and
the op is classified correctly anyway, because the signature they wrote
is the classification. Nobody hand-labels an op random-access; nobody
audits such a label. An op earns a faster shape when a measurement says
the path is worth it, and that reshaping changes nothing a tool's user
can see. The vocabulary grows only when a new *kind* of computation
arrives, never as a new convenience.

## Context

The named system: the shape algebra — the small set of signatures an
operation may be written as, and the rule that the signature written
*is* the operation's classification. The kernel (the body of
primitives — resample, threshold, wavelet transform, optical flow,
background model, tracker) is written in it.

The occasion was a decomposition question with no answer: should
downsampling be its own step or an extension of crop? Neither, and the
question is unanswerable as posed. Crop-then-downsample as two
resamplings is both slower and *less correct* than one composed sample,
so the saving is in neither step and belongs to their boundary. The
cost function is not separable across step boundaries, so the step
decomposition has no optimal substructure — every boundary forfeits
some cross-boundary optimization, and redrawing it only moves which one
is lost. At ten steps that compounds.

Primaries: `docs/archive/DESIGN-SESSION.md` — the non-separability and
the two-layer fix (Exchange 3); the first design's rejection, the
shapes, and classification by form (Exchange 5); evidence-triggered
refinement (Exchange 6). And
`docs/archive/SESSION-2026-08-03-shape-algebra-edges.md` — the closure
overclaim (Exchange 1); how much is committed in code (2); `Resample`
as an invertible affine and the guarantee-voiding convention (3);
`Window`'s surviving declaration (4); refinement as standing debt, and
the agent's claimed contradiction in the design session withdrawn (5).

## Decision

**Ops are values; the executor interprets them.** The graph the user
authors is not the graph the executor runs — steps are units of intent
and UI, ops are units of execution. DP over user-authored steps has no
optimal substructure; DP over fusion regions of an op graph does, so
the state space was wrong rather than the method. This is the standard
split (Halide's algorithm/schedule, a query planner's logical→physical
lowering, XLA and TVM fusion, ffmpeg's filtergraph). A tool therefore
returns an op rather than running one. If instead a tool owned a
`run(video) -> video`, fusion would be impossible *forever* — not for
one op but for the system, because no tool written against that
contract could ever expose structure and gaining the ability means
changing what every tool implements. The boundary is nonetheless free
to conform to: the cheapest honest op is `Opaque(fn)`, which is a
`run()` method with a wrapper around it.

**Five shapes.** `Resample` is an invertible affine coordinate map over
(t, y, x); `PixelMap` is value → value; `Window` computes frame N from
a bounded [N−a, N+b]; `Fold` is (state, frame) → (state, output);
`Opaque` is frames in, frames out. Unifying spatial and temporal
indexing under one coordinate map is what turns "hoist decimation
upstream" from a rewrite rule into plain composition. `Opaque` is
total, so the vocabulary is closed trivially and the real claim is
narrower: four shapes classify the computations the algebra can reason
about, and the fifth exists because they do not close over what people
will write.

**Classification is the shape, not a flag.** There is no fusion-class
field and no random-access field, because which shape you implement
*is* the classification: the others are not expressible in that
signature. A stateful op cannot be mislabelled random-access, because
to be a `Resample` you must write a function with no state parameter —
the bug class is unrepresentable rather than tested for. This is the
record's load-bearing rejection. The first design carried declared
classifications, and its tell was that it required a conformance test
to check whether an op had *honestly declared itself* random-access;
correctness resting on a hand-set flag is correctness an agent gets
wrong silently, here as plausible-looking wrong scrub frames. Kendrick's
rejection named the broader cost: that design taxed every future
contributor with compiler work before they could ship anything.

One declaration survives it. `Window`'s bound is two numbers the
contributor writes, and a wrong one makes frame N cold differ from
frame N during a sweep. It is guarded rather than made impossible: the
cold-vs-sweep property test reds on it, and a corrected bound produces
a different recipe hash rather than an invalidation. Stated here
because the invariant reads as absolute and is not.

**Refinement is measured, and owed rather than pre-paid.** `Opaque` is
the resting state: always correct, always slow, never fused. An op
earns a real shape when instrumentation says its path is hot — the
peephole discipline, where each rule must only be correct rather than
complete, and is independently justified, tested against the naive path
and deletable (Exchange 6). The naive evaluator is the product surface,
not a fallback, because the tail pipelines are where the research is.
The op boundary above is the one thing not deferred this way, and it is
not deferred because it costs nothing rather than because it is
insurance: every unreshaped op above it is standing debt with a
measurable trigger, and what must exist early is the instrumentation
that produces the measurement, not the optimizer that consumes it.

**Five shapes on paper, two in code.** The kernel implements `Resample`
and `Opaque`; `PixelMap`, `Window`, and `Fold` arrive with their first
instance. Adding a shape later is the same work as declaring it now,
minus the risk of guessing a signature at n=0 — a risk already
realized, since `(state, frame) → (state, output)` has nowhere to put
background subtraction's second input. What the unbuilt three do at
n=0 is tell whoever writes the next op what the intended factoring is,
so a tracker is not written as an `Opaque` holding a global. That is a
record's job rather than a module's, which is why they are stated here
and not stubbed there.

**Guarantees are declared where they are voided.** `Resample` is an
invertible affine, so composing a chain gives one matrix, the
anti-aliasing footprint follows from the total Jacobian, and mapping an
annotation between any two nodes is composing and inverting — a
guarantee the layers above may spend, not a property of some subset.
Non-affine geometry — lens undistortion, rolling-shutter correction —
is `Opaque`, which costs fusion and reprojection and nothing else, and
is not a priority. Because that choice voids a guarantee a previous
layer provides, the voiding is declared in the tool contract
(PAR-0007) and surfaces to the user at selection, rather than being
discovered when an ROI lands in the wrong place on the source.

**Semantics are defined at the logical level.** Fusion changes pixels:
two resamplings filter twice and soften, while one composed sample
filtered from the total Jacobian is the more correct result. That the
fast path is the more defensible one is the happy case, not a
guarantee — for an instrument whose premise is interpretable filtering,
results must not depend on invisible planner decisions. So semantics
are stated over the logical graph, the planner is required to be
semantics-preserving within a stated tolerance, and a preference
disables fusion entirely so a reviewer can confirm the two paths agree.
That preference changes speed and not values, which is why it is a
preference and not a param (PAR-0006).

## Consequences

- The design debt (stamp `20260802T225556Z`) discharges with this
  record. `Status: Proposed` carries the remaining acceptance-and-
  hardening debt, as it does for PAR-0003 and PAR-0004.
- Acceptance amends `ARCHITECTURE.md` in the same commit: invariant 3
  and the five-shape table cite this record, the table notes which two
  shapes exist in code, and `src/sieve/kernel.py`'s placeholder marker
  narrows to `Resample` and `Opaque`.
- PAR-0007 gains the guarantee-voiding declaration as part of the tool
  contract; the convention is general, and `Opaque`'s loss of
  reprojection is its first instance.
- Two property tests close testing for the whole op space: any chain of
  `Resample`s is bit-identical fused and unfused, and a `Window` op
  gives frame N the same cold as during a sweep. Every op is one of the
  five shapes, so every op is covered. Enforcement's home is PAR-0017's.
- Content-addressing hashes the *logical* recipe, never the physical
  node, or every peephole rule added silently invalidates every cached
  result on disk. The store is PAR-0009's; this is the constraint the
  op layer imposes on it.
- `Fold` sweeps once and persists a small result, returning everything
  downstream to random access — the store's small-result
  materialization exists for it (PAR-0009).

## Challenges

- **2026-08-03 — three of the five signatures were written with no
  implementation in hand.** The known instance: `Fold` is unary and
  background subtraction consumes frame + plate. Held as provisional
  rather than as a defect — the shapes are guidance until an op needs
  them, and each is settled by its first instance. `DEFERRED.md` holds
  the arity question with that trigger.
- **2026-08-03 — "semantics-preserving within a stated tolerance"
  names no tolerance.** The fusion-disable preference is the reviewer's
  check and the measured-equivalence harness (PAR-0012) is where a
  policy would live; both are deferred, so the claim rests today on the
  fused path being analytically the more correct one rather than on a
  measured bound. Resolves when a second implementation of any op makes
  equivalence testable.
