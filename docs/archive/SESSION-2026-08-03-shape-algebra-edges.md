# Session: the shape algebra's edges

Status: Open
Date: 2026-08-03

The occasion: PAR-0005 landed as a distillation of the design session,
and a skeptic pass over the fresh record found holes the primary had
carried unnamed. Four exchanges, of which two moved the decision. The
argument stays open until the record's acceptance sitting.

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
