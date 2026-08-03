# PAR-0005 — Ops as values, and what the executor may rewrite

Status: Proposed
Date: 2026-08-03

## Outcomes

What this system looks like working as intended: a rewrite that made
something fast is a rule in the tree with a test beside it, not a
comment in a file that the next redesign deletes. Someone writing a new
operation writes the naive thing and ships it the same afternoon,
because the architecture asks nothing of them. The executor never
changes an answer without being able to prove it didn't. And every
substitution that cannot be proved is one the user asked for, saw the
difference from, and has recorded next to the result — so a number that
gets published can be traced to the decision that produced it.

## Context

The named system: the representation an operation takes, and the
authority the executor has to rewrite a graph of them.

The occasion is measured rather than argued. v1
(`antscihub-optical-flow-detector`) runs far faster than v2
(`antscihub-SIEVE-v2`), and the reason went undiagnosed through a whole
rewrite. Reading both: v1 pushes crop, scale, greyscale conversion and
replicate packing into one FFmpeg filtergraph (`core/video.py:398-415`),
so only working-size gray16 crosses the pipe, and it records that the
*order* inside that graph is worth 10× (`video.py:232-237`: scale before
`format=gray16le` measures 0.364, reversed 3.80). Its preprocessing is
hand-fused with the arithmetic stated — the z-score collapsed to one
affine `g*a + b` because a z-score is affine, a native gray16 path that
skips the 0–255 conversion because a positive scale cancels out of a
z-score, a skipped resize when the decoder already produced the target
size, block reduction at ingest so the wavelet runs on a small grid
(`core/preprocess.py`, `core/stream_buffer.py`). v2 decodes full
resolution and shrinks afterwards (`decode/reader.py:112-118`), runs
four independent readers that each grab-forward over the same frames
(`decode/prefetch.py:130-146` with `reader.py:86-95`, so decode work
scales with worker count), and materializes a full array per node per
frame (`pipeline/executor.py:54-81`).

Two of those three are decode-path defects and are not this record's
business. The third is: every one of v1's measured wins is a rewrite
rule, and every one lived only in a person and in prose. Nothing in
either architecture could hold them, so the redesign deleted them and
left no way to find out why the result was slower. That is the failure
this record exists to prevent, and it has now happened once.

Primaries: `docs/archive/SESSION-2026-08-03-shape-algebra-edges.md` —
the closure overclaim (Exchange 1); how much is committed in code (2);
affine geometry and the guarantee-voiding convention (3); the surviving
declaration (4); the retrofit argument withdrawn (5); the v1/v2 finding
(6); subgraph offload and the TRex case (7); representation as the
opposite of runtime access, and form as authorization (8); equivalence
in a subtype and the swap test (9); the vocabulary cut to what it
proves (10). And `docs/archive/DESIGN-SESSION.md` — non-separability
across step boundaries (Exchange 3), the rejection of declared
classification (5), evidence-triggered refinement and the peephole
discipline (6).

## Decision

**An op is a value, not behavior.** A tool returns a description of
what it wants computed — a closed constructor with typed fields —
never a callable the executor invokes blindly. The guard is
serializability: an op that round-trips through a file cannot contain
code, so it cannot reach the runtime, hold a handle, or smuggle a
callback. This is not a second rule to remember, because the recipe
hash needs a canonical serialization anyway; the property that keeps
tools out of the executor and the property that makes results
addressable are the same property, enforced by machinery already being
built. `Opaque(fn)` is the sole exception and therefore the sole
barrier: it is a `run()` method with a wrapper, which is what makes
conformance free for someone who has read none of this.

**Form is an authorization, not a label.** Writing an op in a
particular form states which rewrites the executor may apply *without
telling anyone*. An affine coordinate map authorizes composition with
its neighbours, evaluation at frame N without frame N−1, and
reordering with spatial work; it forbids reordering past a temporal
filter. An op that carries state authorizes almost nothing and requires
a sweep. `Opaque` authorizes nothing at all, which is exactly why it is
always correct and always slow. Correctness-by-default is the op that
permits no rewrites.

**Silent rewrites must be answer-preserving by proof.** The executor
may rewrite only where the representation proves the answer is
unchanged: affine composed with affine is affine, an op with no state
is order-independent. Everything else is user-initiated, shown, and
recorded — the swap test, where substituting one implementation for
another runs both on the user's own footage over a subrange and reports
the difference at the terminal statistic (PAR-0012). The two failure
modes are symmetric and both nameable: a silent rewrite that changes
the answer, and a user-facing swap presented as free when it is not.
The planner may never introduce, remove, or alter sampling structure at
all — sampling is the design of the measurement, and no tolerance is
small enough to license changing it.

**A subgraph may be lowered to a foreign engine.** Because ops are
values, a pattern of adjacent nodes can be matched and emitted as one
call to something that already optimizes internally — crop and
decimation becoming a single FFmpeg filtergraph rather than two OpenCV
passes. This is the same authority as any other rewrite and is subject
to the same proof requirement; it is also, on the evidence above, the
largest available win, and the one v2 lost. Offload is why the
representation must be symbolic rather than merely typed: you cannot
pattern-match a bag of functions.

**The vocabulary is what has been proved, and no more.** Today that is
an affine coordinate map, the one bit distinguishing sequential from
random-access, and `Opaque`. A further form is admitted when a rewrite
it would license is both wanted and provable — never because an op
feels like it deserves a category. An unreshaped `Opaque` is standing
debt with a measurable trigger, not a defect, and instrumentation is
what makes the trigger observable (`DEFERRED.md`, the executor's cost
surface). This inverts the record this replaces, which fixed five forms
before any op existed and could not classify the reduction every SIEVE
pipeline terminates in.

## Consequences

- Acceptance amends `ARCHITECTURE.md` in the same commit: invariant 3
  becomes the rewrite-authority rule rather than a statement about
  flags, the five-shape table narrows to the forms that exist, and
  `src/sieve/kernel.py`'s placeholder marker narrows with it.
- The how-to layer (PAR-0003) gains this record's first residents, owed
  from `ARCHITECTURE.md` at acceptance: writing an op and choosing
  between `Opaque` and a proved form; adding a rewrite rule with its
  independent test against the naive path; offloading a subgraph to
  FFmpeg; diagnosing a slow pipeline from the cost surface.
- PAR-0007 gains the tool contract's return type — a serializable op —
  and the convention that a tool voiding a guarantee a previous layer
  provides declares that voiding, so the loss surfaces at selection.
  `Opaque`'s loss of reprojection is the first instance.
- PAR-0009 hashes the op values, never the physical plan, or every
  rewrite added silently invalidates every stored result.
- PAR-0012 holds the measured half: substitution admitted by
  measurement on the user's footage, conditional on footage type,
  version-pinned, with the result travelling in the provenance and the
  multiple-comparisons safeguard built into the swap affordance rather
  than offered as advice.
- Two property tests follow from the proofs rather than from a
  vocabulary: an affine chain evaluates identically fused and unfused,
  and a bounded-neighbourhood op gives frame N the same cold as during
  a sweep. Enforcement's home is PAR-0017's.

## Challenges

- **2026-08-03 — the operation SIEVE exists to perform has no proved
  form.** Every pipeline terminates in a reduction from frames to rows
  — mean brightness in a mask, detections per frame, the feature vector
  itself. It is stateless and random-access, so classifying it as
  sequential would falsely forbid scrubbing, and today it is `Opaque`.
  This is the first candidate for a new form and the strongest test of
  the admission rule above.
- **2026-08-03 — data-dependent domains are outside the
  representation.** "Run centroid tracking only within the detected
  windows" makes a downstream op's domain a function of an upstream
  op's result, which no static op value can express, and which the
  hash and the composition rules both assume away. It is in real use.
- **2026-08-03 — equivalence in a subtype does not obviously
  transfer.** The swap test answers for the user's footage. Carrying
  "this substitution was fine" to the next project requires the footage
  to be characterized, and nothing yet says how. Until then swap
  results are one-shot rather than cumulative.
