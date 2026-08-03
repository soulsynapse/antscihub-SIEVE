# PAR-0005 — Shape algebra and classification by form

Status: Proposed
Date: 2026-08-03

## Outcomes

What this system looks like working as intended: a contributor who has
read nothing about the algebra ships a correct op in an afternoon, and
the op is classified correctly anyway, because the signature they wrote
is the classification. Nobody hand-labels an op random-access; nobody
audits such a label. Speed arrives later as a reshaping that changes
nothing a tool's user can see. The vocabulary stays at five shapes for
a long time, and each addition to it is argued as a new *kind* of
computation rather than a new convenience.

## Context

The named system: the op algebra the kernel is written in — the small
closed set of shapes every primitive takes, and the rule that an op's
shape is its classification.

The occasion was a decomposition question with no answer: should
downsampling be its own step or an extension of crop? Neither, and the
question is unanswerable as posed. Crop-then-downsample as two
resamplings is both slower and *less correct* than one composed sample,
so the saving is in neither step and belongs to their boundary. The
cost function is not separable across step boundaries, so the step
decomposition has no optimal substructure — every boundary forfeits
some cross-boundary optimization, and redrawing it only moves which one
is lost. At ten steps that compounds.

Primary: `docs/archive/DESIGN-SESSION.md` — the non-separability and
the two-layer fix (Exchange 3); the first design and its rejection, the
five shapes, and classification by form (Exchange 5). Exchange 4's
random-access/sequential axis is the reason `Fold` exists and is cited
here for that; the executor's use of it is PAR-0008's.

## Decision

**Two layers, because one cannot work.** The graph the user authors is
not the graph the executor runs. Steps are units of intent and UI; ops
are units of execution. DP over user-authored steps has no optimal
substructure, but DP over fusion regions of an op graph does — the
state space was wrong, not the method. This is the standard move
(Halide's algorithm/schedule split, a query planner's logical→physical
lowering, XLA and TVM fusion, ffmpeg's filtergraph), and adopting it is
what lets steps stay separate for the user's sake while execution
ignores the boundaries. The consequence for the tool contract
(PAR-0007) is absolute: `run()` cannot be an opaque video→video
function, because if it is, fusion is impossible forever. Tools emit
ops; the IR is built immediately even while the planner is two rules,
because the IR is the part that is expensive to retrofit.

Two rewrite rules pay for the layer on their own. Composing adjacent
coordinate maps into one matrix is one resample instead of two.
Pushing temporal decimation upstream past spatial work means never
decoding a frame that is about to be discarded — 10× temporal
decimation is a 10× cut in crop work, and no single step can do that.
The second rule is the existence proof for the layer.

**Five shapes.** `Resample` is a coordinate map over (t, y, x);
`PixelMap` is value → value; `Window` computes frame N from a bounded
[N−a, N+b]; `Fold` is (state, frame) → (state, output); `Opaque` is
frames in, frames out. Unifying spatial and temporal indexing under one
coordinate map is what turns "hoist decimation upstream" from a rewrite
rule into plain composition — the shapes are chosen so that the
optimizations fall out of the algebra rather than being enumerated
against it.

**Classification is the shape, not a flag.** There is no fusion-class
field and no random-access field, because which shape you implement
*is* the classification: the others are not expressible in that
signature. A stateful op cannot be mislabelled random-access, because
to be a `Resample` you must write a function with no state parameter.
The bug class is unrepresentable rather than tested for.

This is the record's load-bearing rejection. The first design carried
declared classifications, and its own tell was that it required a
conformance test to check whether an op had *honestly declared itself*
random-access. Correctness that depends on a hand-set flag is
correctness an agent gets wrong silently — here, wrong scrub frames
that look plausible. Kendrick's rejection was broader and named the
real cost: that design made extending the repo a headache forever,
taxing every future contributor with compiler work before they could
ship anything (primary, Prompt 6). The rebuilt version keeps the
compiler and moves the tax off the contributor: the algebra composes,
so nobody ever writes a crop×downsample fusion or a bgsub×flow renderer
by hand.

**Correctness is the default; performance is opt-in.** `Opaque` is the
fifth shape for when you do not want to think — a total barrier, never
fused, always correct, always slow. It is not a fallback, it is the
entry point: a working op lands in an afternoon and someone later
reshapes it into a `Resample`, gaining speed with zero change to the
tool's public surface. The rejected design inverted this, requiring the
algebra to be understood before anything could be shipped. Fusion
barriers also bound the fusion regions, so the escape hatch costs the
optimizer nothing it was going to get.

**Semantics are defined at the logical level.** Fusion changes pixels:
two resamplings filter twice and soften, while one composed sample with
the anti-aliasing footprint derived from the *total* Jacobian is the
more correct result. That the fast path is the more defensible one is
the happy case, not a guarantee — for an instrument whose premise is
interpretable filtering, results must not depend on invisible planner
decisions. So semantics are stated over the logical graph, the planner
is required to be semantics-preserving within a stated tolerance, and a
preference disables fusion entirely so a reviewer can confirm that the
fast and naive paths agree. That preference changes speed and not
values, which is why it is a preference and not a param (invariant 5,
PAR-0006).

**The vocabulary is v1 and revised additively.** Five shapes are a
claim about what kinds of computation exist here, not a coverage
guarantee. A sixth is admitted only for a kind the existing signatures
cannot express — never for an op that is merely awkward, which is what
`Opaque` absorbs.

## Consequences

- The design debt (stamp `20260802T225556Z`) discharges with this
  record. `Status: Proposed` carries the remaining acceptance-and-
  hardening debt, as it does for PAR-0003 and PAR-0004; restating that
  in a marker would double-state it.
- Acceptance amends `ARCHITECTURE.md` in the same commit: invariant 3
  ("classification comes from the shape of what you wrote") and the
  five-shape table under "The components" cite this record instead of
  Exchanges 3 and 5, and `src/sieve/kernel.py`'s placeholder marker is
  reworded to point here.
- Two property tests close testing for the whole op space: any chain of
  `Resample`s is bit-identical fused and unfused, and a `Window` op
  gives the same frame N cold as during a sweep. They are stated as
  consequences of the algebra — every op that will ever be written is
  covered by them because every op is one of the five shapes. Where
  that enforcement lives is PAR-0017's.
- `Fold`'s existence is what makes the store's small-result
  materialization necessary (sequential ops sweep once and persist a
  tiny result, returning everything downstream to random access);
  the store itself is PAR-0009's.
- Content-addressing hashes the *logical* recipe, never the physical
  node, or every planner improvement silently invalidates every cached
  result on disk. Stated here because it is a constraint the two-layer
  split imposes on the store; the store's design is PAR-0009's.
- Coordinate maps are invertible affines, so reprojecting an annotation
  between any two nodes is composing and inverting. The IR built for
  fusion pays for the GUI's base-layer swapping for free (PAR-0013).

## Challenges

- **2026-08-03 — the unary-looking signatures do not say how a second
  input enters.** Background subtraction consumes frame + plate and is
  treated as a `Fold`, but the signatures as stated are unary. Held in
  `DEFERRED.md` with its trigger: `src/sieve/kernel.py`'s first real
  code, when the signatures become executable. Not breaking — it is a
  gap in what the shapes state, not a case they get wrong — but it is
  the first thing that will bend the vocabulary.
- **2026-08-03 — "semantics-preserving within a stated tolerance"
  names no tolerance.** The fusion-disable preference is the reviewer's
  check, and the measured-equivalence harness (PAR-0012) is where a
  tolerance policy would live; both are deferred, so today the claim
  rests on the fused path being analytically the more correct one
  rather than on a measured bound. Resolves when the first second
  implementation of any op makes equivalence testable.
