# PAR-0005 — Silent substitution: ops as values, and what the form proves

Status: Accepted
Date: 2026-08-03

## Outcomes

What this system looks like working as intended: a rewrite that made
something fast is a rule in the tree with a test beside it, not a
comment in a file that the next redesign deletes. Someone writing a new
operation writes the naive thing and ships it the same afternoon,
because the architecture asks nothing of them. The executor never
changes an answer without being able to prove it didn't — under a
stated definition of what the answer is. And every substitution that
cannot be proved is one the user asked for, saw the difference from,
and has recorded next to the result — so a number that gets published
can be traced to the decision that produced it.

## Context

The named system: the representation an operation takes, and the
authority the executor has to rewrite a graph of them. The seam with
PAR-0008: this record owns what a form *authorizes* — the property
carried by the value; when and whether the executor exercises an
authorization — the peephole discipline, the naive evaluator, the
evidence threshold for adding a rule — is the executor's own record.

The name is the seam stated. Every rewrite, fusion, and offload is a
substitution of one computation for another, and the full substitution
system deliberately spans four records: this one grants the *silent*
portion — what proof under the defined semantics can back — while
admission by measurement is PAR-0012's, selection among the admitted
is PAR-0011's, and the timing of exercise is PAR-0008's. The moment a
substitution stops being silent it has left this record. "Silent"
also carries the stakes: the named failure mode is a silent rewrite
that changes an answer, the one thing this instrument must never do.
("Comparison authority" was considered and rejected: the word already
does statistical work in this record's own orbit — the
multiple-comparisons safeguard — and a name cannot serve two senses
in one file.)

The occasion is measured, and what it measures must be stated
carefully. v1 (`antscihub-optical-flow-detector`) runs far faster than
v2 (`antscihub-SIEVE-v2`), and the gap's dominant term is the decode
path: v1 pushes crop, scale, greyscale conversion and replicate packing
into one FFmpeg filtergraph (`core/video.py:398-415`), so only
working-size gray16 crosses the pipe — ~8% of a 5.3K frame — while v2
decodes full resolution and shrinks afterwards (`decode/reader.py:112-118`),
runs four readers that each grab-forward over the same frames
(`decode/prefetch.py:130-146` with `reader.py:86-95`), and materializes
a full array per node per frame (`pipeline/executor.py:54-81`). Those
decode defects are conceded and are not this record's business; a
working-size sequential reader recovers most of the gap with no
representation at all.

What the gap evidences for this record is its *diagnosis cost*: it went
undiagnosed through a whole rewrite, because every rule that made v1
fast lived in a person and in comments. The z-score collapsed to one
affine `g*a + b` because a z-score is affine (2.3–3× measured), a
native gray16 path that skips the 0–255 conversion because a positive
scale cancels out of a z-score, a skipped resize when the decoder
already produced the target size, block reduction at ingest so the
wavelet runs on a small grid (`core/preprocess.py`,
`core/stream_buffer.py`) — each is a rewrite rule, and each was
untestable in principle, not merely unrecorded: a rule is a pair of
expressions asserted equivalent, and welded code contains only one of
them, so verifying any of these meant reverting the code. A benchmark
pin would have bought the alarm — slower — but not the rule; v1 had
the numbers in comments, and detection was never the failure.
Portability was. The same comments also record that what an engine
does *inside* an offloaded graph changes answers: scale before
`format=gray16le` measures 0.364 RMS grey-levels against a float
reference, reversed 3.80 — a 10× accuracy difference from ordering
alone (`video.py:232-237`), which is evidence for the authorization
half of this record, not the speed half.

The boundary this record places is free at n=0 — `Opaque(fn)` is a
`run()` method with a wrapper — and is a contract rewrite at any later
moment, because the return type of the tool contract is the one thing
not retrofittable per-tool. That timing asymmetry, plus the rules'
need for a representation to be about, is the necessity argument in
full; speed alone is not, since v1 proves speed is achievable by
welding.

Primaries: `docs/archive/SESSION-2026-08-03-shape-algebra-edges.md` —
the closure overclaim (Exchange 1); how much is committed in code (2);
affine geometry and the guarantee-voiding convention (3); the surviving
declaration (4); the retrofit argument withdrawn (5); the v1/v2 finding
(6); subgraph offload and the TRex case (7); representation as the
opposite of runtime access, and form as authorization (8); equivalence
in a subtype and the swap test (9); the vocabulary cut to what it
proves (10). `docs/archive/SESSION-2026-08-03-par-0005-judgment.md` —
the deliberate attack at judgment: the citations verified and the 10×
misread corrected (Exchanges 1–2); the semantics repair (3); the
offload bar (4); the necessity argument (8); the touch occasions and
how-to set (9); the acceptance conditions answered, including the
tool-suggested equivalence spec (10). And
`docs/archive/DESIGN-SESSION.md` — non-separability across step
boundaries and semantics at the logical level (Exchange 3), the
rejection of declared classification (5), evidence-triggered refinement
and the peephole discipline (6).

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
conformance free for someone who has read none of this. Because a
callable does not round-trip, an `Opaque`'s recipe identity is its
tool's identity plus a hand-bumped version — stated where the hash is
designed (PAR-0009), named here so it is not rediscovered.

**Form is an authorization, not a label.** Writing an op in a
particular form states which rewrites the executor may apply *without
telling anyone*. An affine coordinate map authorizes composition with
its neighbours, evaluation at frame N without frame N−1, and
reordering with spatial work; it forbids reordering past a temporal
filter. An op that carries state authorizes almost nothing and requires
a sweep. `Opaque` exposes no structure and authorizes nothing at all —
which is exactly why it is always correct and always slow, and why it
can rest under anything, including the reductions from frames to rows
that every pipeline terminates in. Correctness-by-default is the op
that permits no rewrites.

**The answer is defined at the logical level, and silent rewrites are
proved under that definition.** A node's meaning is the composed map
from the nearest barrier, applied once; how many sampling passes an
evaluator takes is an implementation detail, not part of the answer.
"Proof" means proof under that semantics — affine composed with affine
is the same map, an op with no state commutes — never bit-identity
between evaluation strategies, which the record's own evidence shows
is false (two resampling passes filter twice; one composed sample is
the more defensible number). The pull path already evaluates this way,
composing coordinates as it walks up the chain, so the naive and fused
paths share the sampling arithmetic by construction; the property test
is compose-order invariance, bit-exact where the affine parameters are
exact — integers and rationals, which crop, decimate and integer scale
are, and which are held exact for this reason — and bounded-ulp where
they are not. Two consequences with teeth: silently materializing a
mid-chain geometric intermediate and resampling from it changes the
answer under this semantics, so silent materialization is legal only
at barrier outputs — a `Fold`'s table and an `Opaque`'s output are
their own logical values — and baking a geometric intermediate is
user-initiated and recorded, like any other unproved substitution.
Everything that cannot be proved is user-initiated, shown, and
recorded — the swap test, where substituting one implementation for
another runs both on the user's own footage over a subrange and
reports the difference at the terminal statistic (PAR-0012). The
rewrites-off audit affordance survives with its job description
corrected: nothing privileges the multi-pass path as truth, so the
audit does not define correctness — it detects implementation bugs in
rewrite rules, compared at the terminal statistic. The planner may
never introduce, remove, or alter sampling structure at all —
sampling is the design of the measurement, and no tolerance is small
enough to license changing it.

**A subgraph may be lowered to a foreign engine — proof licenses the
pattern, measurement admits the engine.** Because ops are values, a
pattern of adjacent nodes can be matched and emitted as one call to
something that already optimizes internally — crop and decimation
becoming a single FFmpeg filtergraph rather than two OpenCV passes.
The two halves of that move carry different evidence classes and must
not borrow from each other. The *pattern rewrite* — several nodes
becoming one composed op — is proof territory, the paragraph above.
The *foreign implementation* of the composed op is a second
implementation of an existing op, which is invariant 4's territory:
equivalence earned by measurement at admission, version-pinned,
conditional on footage class; selection thereafter by measured cost.
Admission happens once — at registration against the corpus, or at a
swap on the user's own footage — not as a ceremony per pipeline,
which is how a v1-scale win goes default-on without ever being
silent-by-declaration. The equivalence spec the measurement judges
against — the comparator, the tolerance, the statistic that must
survive — is suggested by the tool that emitted the op, for the input
it emitted it for: the tool knows what its output means, so it
declares the yardstick, never the verdict, and declaring it in the
contract fixes the metric before any search begins, which the
multiple-comparisons safeguard requires anyway (PAR-0012). Offload is
why the representation must be symbolic rather than merely typed: you
cannot pattern-match a bag of functions. On the evidence above it is
the largest available win, and its trigger is already in the tree:
the first foreign engine is the first second implementation of any
op, which is the measured-equivalence harness's own trigger.

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
  FFmpeg; diagnosing a slow pipeline from the cost surface; and
  auditing a result with rewrites off, compared at the terminal
  statistic — the reviewer's door, owed since the design session's
  Exchange 3. Admitting a new form is deliberately not a how-to: it is
  a record edit under the admission rule, and the layer's silence
  there is the signal that the task is architecture, not use.
- PAR-0007 gains the tool contract's return type — a serializable op —
  the convention that a tool voiding a guarantee a previous layer
  provides declares that voiding so the loss surfaces at selection
  (`Opaque`'s loss of reprojection is the first instance), and the
  equivalence-suggestion surface: the comparator, tolerance, and
  target statistic a tool suggests for the ops it emits, declaratively.
- PAR-0009 hashes the op values, never the physical plan, or every
  rewrite added silently invalidates every stored result; it also owns
  `Opaque`'s identity (tool identity plus hand-bumped version) and the
  rule that a cached mid-chain geometric intermediate is never
  reusable as a logical value — only barrier outputs are.
- PAR-0012 holds the measured half: substitution admitted by
  measurement on the user's footage, conditional on footage type,
  version-pinned, with the result travelling in the provenance, the
  multiple-comparisons safeguard built into the swap affordance rather
  than offered as advice, and the tool-suggested equivalence spec
  consumed as the default yardstick.
- Two property tests follow from the proofs rather than from a
  vocabulary: an affine chain is compose-order invariant — bit-exact
  under exact parameters, bounded-ulp otherwise — and a
  bounded-neighbourhood op gives frame N the same cold as during a
  sweep. Enforcement's home is PAR-0017's.

## Challenges

- **2026-08-03 — the operation SIEVE exists to perform has no proved
  form.** Every pipeline terminates in a reduction from frames to rows
  — mean brightness in a mask, detections per frame, the feature vector
  itself. It is stateless and random-access, and today it rests as an
  `Opaque` — coherently, under the no-structure-exposed reading, but
  with nothing authorized. It is the first candidate for a new form
  and the strongest test of the admission rule above.
- **2026-08-03 — no rewrite crosses a data-dependent edge.** "Run
  centroid tracking only within the detected windows" is expressible
  as ordinary dataflow — the windows are an upstream product with its
  own hash, and the recipe hash already includes upstream output
  hashes — so expressibility and addressing hold, and a pull-based
  evaluator skips unrequested frames without any representation
  change. What stands, narrowed at judgment from a broader claim: the
  gate edge is an absolute barrier to rewrite reasoning, and nothing
  yet says whether that ever costs enough to matter. Real, unresolved,
  not rising to change.
- **2026-08-03 — equivalence in a subtype does not obviously
  transfer.** The swap test answers for the user's footage. The
  tool-suggested spec fixes the yardstick across projects, so results
  are now comparable in metric; carrying "this substitution was fine"
  to the next project still requires the footage to be characterized,
  and nothing yet says how. Until then swap results are one-shot
  rather than cumulative.
- **2026-08-03 — the record has no teeth of its own.** Raised by
  Kendrick at acceptance: as written it does not enforce anything
  per se — no test fails today because it exists. Held, and the
  ground stated with it: it enables functionality (the rules, the
  offload, the swap machinery all presuppose the representation),
  and its enforcement arrives through the property tests it derives
  (PAR-0017's home) and the serializability the hash requires;
  making sure problems are surfaced is an explicit purpose of the
  PAR system as a whole, and a record that does that while asking
  nothing of contributors is earning its keep, not failing to.
