# Session: the shape algebra's edges

Status: Frozen
Date: 2026-08-03

The occasion: PAR-0005 landed as a distillation of the design session,
and a skeptic pass over the fresh record found holes the primary had
carried unnamed. Ten exchanges, closing with the record redrawn around
the representation rather than the form vocabulary. Frozen there: the
redraw is settled, and the record's acceptance — or a deliberate attack
on it — is a fresh sitting that files its own primary.

## Exchange 1 — the closure claim, and what the five shapes cover

The agent's distillation opened by saying every primitive takes one of
the five shapes "and nothing else is expressible." Kendrick: "dunno how
that maps to the 5 as listed, did you overstate"

Overstated. The closure is trivially true because `Opaque` is total —
frames in, frames out — so the sentence says nothing. The real claim is
narrower: four shapes classify the computations the algebra can reason
about, and `Opaque` exists because they do not close over what people
will write. Of the six kernel primitives the record itself lists, five
map cleanly; the wavelet transform maps only if it is temporal, since
`Window` is indexed by frame. Standalone spatial-neighborhood ops —
Sobel, blur, erosion on a mask — have no shape but `Opaque`, which the
primary never named.

## Exchange 2 — what the algebra buys before anything calls for it

Kendrick: "I am curious what the argument is for this needing to exist
prior to something deliberately calling for it. what's the shared
algebra doing that saves time later?"

The agent's answer separated two claims the record had fused. The
two-layer split — tools returning an op value rather than owning
`run()` — is genuinely expensive to retrofit: it is a contract every
tool and every stored recipe hash depends on. The five-shape vocabulary
is not, by the record's own additive-revision policy: adding `Fold`
when the tracker is written is the same work as declaring it now, minus
the risk of guessing a signature at n=0 — a risk already realized,
since `(state, frame) → (state, output)` has nowhere to put background
subtraction's second input.

The smallest version that keeps the insurance: the boundary is data not
behavior, `Resample` and `Opaque` exist in code, the other three arrive
with their first instance. What that would cost is the one thing the
vocabulary does at n=0 that code cannot — telling a contributor what
the intended factoring is, so the first tracker is not written as an
`Opaque` holding a global. That benefit is a record's, not a module's,
so the record keeps all five while the kernel implements two.

Kendrick: "your argument for the smallest version with insurance is
good." Ruled in. The "expensive to retrofit" half of the agent's
reasoning for it is corrected in Exchange 5; the ruling does not
depend on it.

The evidence question underneath it was settled separately. Asked
whether the 10× decode waste on decimated pipelines was a number from
the session or a measured loss, Kendrick: "yes the loss is measurable."
The two-layer split's existence proof stands on measurement, not on the
retrofit argument alone.

## Exchange 3 — `Resample` is an invertible affine

The record used "coordinate map," "one matrix," and "invertible affine"
interchangeably, inheriting the conflation from the design session
itself (Exchange 5's table says coordinate map; Exchange 3 says one
matrix; Exchange 4 says invertible affines). A general coordinate map
composes into no matrix and inverts only numerically, and two payoffs
are priced off the affine reading: fusion into one correctly-filtered
sample via the total Jacobian, and PAR-0013's annotation reprojection.

Kendrick: "don't have the answer for resample. it should be a
guarantee, no? lens undistortion is likely an opaque, but not a
priority right now. per SIEVE convention, if they select a tool that
voids a previous layer's guarantee it should be part of the tool
contract to begin with so it surfaces for the user."

Settled: `Resample` is an invertible affine, and reprojection is a
guarantee rather than a subset property. Non-affine geometry — lens
undistortion, rolling-shutter correction — is `Opaque`, costing fusion
and reprojection but nothing else, and is not a priority. The general
convention stated here and owed to the tool contract: a tool that voids
a guarantee a previous layer provides declares that voiding as part of
its contract, so the loss surfaces to the user at selection rather than
being discovered when an ROI lands in the wrong place.

## Exchange 4 — `Window`'s bound, and the cost of complexity

The skeptic pass raised four further items. Kendrick: "yeah they're
important but lets focus on what is expensive to retrofit later, this
is a PAR and it's becoming way too complicated for a bunch of stuff
that hasn't been built out."

The triage that followed: of the items raised, only `Resample`'s
affinity was expensive, because other records already spend the
invertibility. `Window`'s `[N−a, N+b]` bound is a hand-set number and
therefore a real exception to classification-by-form — but a per-op
one, guarded by the cold-vs-sweep property test, and changing it
produces a different recipe hash rather than an invalidation. It costs
one honest sentence, not a debt entry. Spatial neighborhood and the
absence of any ratchet moving an `Opaque` toward a real shape both
dissolve under Exchange 2's ruling: when most ops are `Opaque` until
one earns a shape, `Opaque` is the resting state rather than debt.

The multi-marker grammar (rule v3) was inspected here and stays
deferred. `_scan_text` already collects every column-0
marker; the one-per-file grain is enforced downstream by the
`(path, qualname)` key, which is why the deferred fix is a rekey to
`(path, stamp)`. It was nearly triggered by the filings this session
seemed to owe, and was not needed once the filings collapsed.

## Exchange 5 — the retrofit argument overruled

The agent had argued that the two-layer split, unlike the vocabulary,
was expensive to retrofit — a contract every tool and every stored
recipe hash depends on. Kendrick: "you overstated it, not every tool
has to own run, worst case everything lives as opaque and gets refined
as is useful with some measurable metric for doing so, and the
convenience of doing the split arrives as long standing debt to be
realized."

Correct on the substance. `Opaque(fn)` is a `run()` method with a
wrapper, so a naively written tool is already inside the contract and
conversion is a per-tool refinement rather than a migration.

The agent then overreached, claiming this exposed a contradiction
inside the design session: that Exchange 3's "`run()` cannot be an
opaque video→video function, because if it is, fusion is impossible
forever" was undercut by Exchange 5 inventing `Opaque` as exactly that
function. Kendrick: "are you sure all of that is true? it seemed pretty
sound in the initial design session, and the idea of fusion being
impossible forever is scary. but as-is it doesn't really sound like
that's the case, only in the instance where tools own run, which was
never going to be the case."

The claim is withdrawn. Exchange 3's "forever" is about the contract,
not about an op: if a tool's only expressible output is a video→video
function, no tool ever written can expose structure and gaining the
ability means changing what every tool implements. `Opaque` is a value
*in* the op vocabulary — the op is unfusable, the system is not. The
agent collapsed the two levels, and priced a retrofit of a contract
that was never a live option after Exchange 5.

Kendrick: "if you check out the design session the reasoning for this
is pretty well laid out." It is — Exchange 6, which the agent had not
cited. The executor is a catalog plus a naive evaluator plus a handful
of peephole rules, each of which must only be correct rather than
complete, added when profiling says a path is hot (condition 1:
instrument from day one, because the evidence cannot be reconstructed
later; condition 4: the naive evaluator is the product surface, since
the tail pipelines are where the research is).

Settled: the op boundary is not deferred, but the reason is that it
costs nothing to conform to rather than that it is insurance against an
expensive retrofit. Everything above it — the shapes, the fusion
rules — is evidence-triggered: every unreshaped op is standing debt
with a measurable trigger, and what must exist early is the
instrumentation that produces the measurement, already held in
`DEFERRED.md` with its own trigger, not the optimizer that consumes
it. Exchange 3 stands as written; what it does not license is the
agent's stronger reading, that the vocabulary above the boundary is
owed the same urgency as the boundary itself.

## Exchange 6 — why v1 outruns v2

Kendrick: "v1 works a *lot* faster than v2 and I wasn't able to figure
out why. the shape algebra speed up argument was borne up that, plus
the intrinsic fusing of functions."

Read side by side, three causes. v1 pushes crop, scale, greyscale and
replicate packing into one FFmpeg filtergraph and streams only
working-size gray16 over a pipe (`core/video.py:398-415`), recording
that filter order inside that graph is worth 10× (`video.py:232-237`).
Its preprocessing is hand-fused with the arithmetic stated: the z-score
collapsed to one affine because a z-score is affine, a gray16 path
skipping the 0–255 conversion because a positive scale cancels out of a
z-score, a skipped resize when the decoder already produced the target
size, block reduction at ingest (`core/preprocess.py`,
`core/stream_buffer.py`). v2 decodes full resolution and shrinks
afterwards (`decode/reader.py:112-118`); its prefetcher opens four
readers that each grab-forward across the same frames
(`decode/prefetch.py:130-146`, `reader.py:86-95`), so decode work scales
with worker count for parallelism that mostly cancels it; and its
executor materializes a full array per node per frame
(`pipeline/executor.py:54-81`).

Two of the three are decode-path defects, not architecture gaps: an
FFmpeg reader at working size with one sequential decoder would recover
most of the gap with no representation at all. The third is the
record's business, and it is the strongest evidence in the argument —
every v1 win is a rewrite rule, every one lived only in a person and in
prose, and the rewrite deleted them all while leaving no way to find
out why the result got slower.

## Exchange 7 — offload, and the tool that has no shape

Kendrick, on the intrinsic fusing of functions: "imagine theres a tool
call like crop, then another tool call like alias. knowing you can do
both in one command allows you to leverage the internal optimization
that is already built into ffmpeg, thus getting speed ups for free."

That is subgraph offload — instruction selection, or a planner pushing
a subquery into a foreign source — and it requires ops to be symbolic
data so a pattern of adjacent nodes can be matched. It does not require
a shape taxonomy.

The counterexample raised in the same breath: TRex 1.1.9 does fast,
accurate background subtraction for a small subset of footage types,
and a tool calling it is three welded stages — information dropping,
the background model, the detector. "these don't map cleanly to any
particular *shape*, they measure cleanly to a particular *outcome*, and
procedurally scanning for equivalence in outcomes doesn't sound very
algebra-shape-related to me."

Correct. The substitutable unit is a subgraph identified by the outcome
it produces, admission is by measurement, the result is conditional on
footage type and pinned to a beta version. Nothing in a form vocabulary
describes it.

## Exchange 8 — representation is the opposite of access

Kendrick: "ops as symbolic data is an oversight waiting to happen, and
sounds like giving the tools access to run with extra steps. we can't
give tools access to run because the executor has to be separate,
right? ... but you said something here that makes me think shapes are
about swappability, yeah?"

The inversion: a value holding three numbers is strictly less access
than a callable, and `Opaque(fn)` is the concession rather than the
strict case. The real risk named here is "symbolic" degrading into a
dict the executor introspects, through which behavior gets smuggled —
guarded by serializability, which the recipe hash already requires.

And yes on swappability, which became the record's frame: a form is not
a classification, it is a statement of which rewrites the executor may
perform without telling anyone. Forms and the harness answer one
question and differ only in evidence class — proof versus measurement.

## Exchange 9 — equivalence in a subtype, and the swap test

Kendrick: "it's equivalence in a subtype. that's why the user gets
access to the test *for* equivalence, which would have been some kind
of meta utility that gives them that feedback when they click 'swap'."

Better than DESIGN-SESSION Exchange 8's registration-time verification
against a versioned corpus: measured at swap time, on the user's own
footage, compared at the terminal statistic, judged by the person who
knows what they care about. It dissolves most of the corpus-composition
question held open in `DEFERRED.md`. Two riders: the
multiple-comparisons safeguard must be built into this affordance
specifically, since click-swap-and-look is the most efficient way ever
devised to overfit to one's own data; and the test result belongs in
the provenance beside the version pin.

## Exchange 10 — the vocabulary cut to what it proves

Kendrick: "are we just arguing for something that doesn't cost anything
to omit but is a repeating cost for everything else downstream?"

Largely yes, for the taxonomy. Across four real pipelines supplied this
session, the five forms failed to classify the work: spatial
neighbourhood and contours have no form, the frames-to-rows reduction
every pipeline terminates in has no form, TRex has no form,
data-dependent gating has no form, and `Fold`'s signature was already
known wrong on arity. A taxonomy charging a classification tax while
failing to classify is the worst combination. What costs nothing to
hold is smaller: ops are serializable values, and sequential-ness is
structural rather than typed by hand.

Asked what declining the record would cost, the answer was the loop
already run twice — hand-fused and fast, then clean and slow, with the
rules living only in comments a redesign deletes. Kendrick then asked
for the record redrawn around only the parts doing real work, required
to name a system, be load-bearing, and admit feasible how-tos.
PAR-0005 was rewritten in place under a new title; the form vocabulary
survives as one consumer of the representation rather than as the
record's subject.
