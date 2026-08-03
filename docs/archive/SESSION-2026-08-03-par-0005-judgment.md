# Session: PAR-0005 at judgment — the deliberate attack

Status: Frozen
Date: 2026-08-03

The occasion: PAR-0005 sits Proposed, rewritten in one sitting by the
same agent that dismantled its predecessor, never read by anyone who did
not also author it. A deliberate attack was convened at judgment
(PAR-0001: "arriving holding the answer and trying to break the draft"),
by fresh eyes with the charge to verify the empirical claim rather than
accept it. Kendrick's convening words: "Its necessity argument rests on
one empirical claim, and you should verify it yourself... If you
conclude the gap is mostly two decode-path bugs plus a person who moved
on, say so — the Context loses its footing and the Decision is left
standing on much narrower ground." And: "Do not soften the verdict to
be agreeable, and do not manufacture objections to look rigorous."

Frozen at the ruling: the attack ran, the conditions were answered,
and the rewrite was cleared and executed (Exchange 12). The record's
acceptance — or a fresh attack on the rewritten form — is a fresh
sitting that files its own primary.

## Exchange 1 — the v1 citations verified, and the one that misreads

Every v1 citation resolves to what the record says is there.
`core/video.py` ~383–417 builds the split/crop/scale/format/pad/vstack
filtergraph and ships gray16le over the pipe;
`ReplicateVideoSource`'s docstring states the 48 MB BGR frame avoided
to retain ~8% of 5.3K footage. `core/preprocess.py` holds the z-score
collapsed to `g*a + b` with "2.3–3x" measured (lines 234–253), the
`accepts_native_gray16` path skipping the 0–255 conversion because a
positive scale cancels from a z-score (112–142), and the skipped
resize at scale 1 with "610 us per call" (153–159).
`core/stream_buffer.py` is the block-grid ring the wavelet reads.

One citation is misread, in the PAR and in the frozen primary it
inherits from (SESSION-2026-08-03-shape-algebra-edges.md, Exchange 6).
`video.py:232-237`'s 0.364 vs 3.80 are **RMS error in grey-levels
against a float reference** — an accuracy measurement. "It records
that the *order* inside that graph is worth 10×," placed in a
paragraph explaining why v1 runs faster, reads as speed and is not.
The frozen record keeps its error; the correction lands in the PAR.
The misread does not kill the sentence's use — scale-before-format is
still a rewrite rule that lived only in a comment — but it is evidence
of the opposite kind than claimed: an ordering rewrite that *changes
the answer* 10-fold, which is Exchange 4's problem below, not a speed
win.

## Exchange 2 — the v2 citations verified, and the attribution

Every v2 citation resolves. `decode/reader.py:112-118` (`_downscale`)
shrinks after a full-resolution decode; `reader.py:86-95`
(`_position_at`) grab-forwards; `decode/prefetch.py` opens up to four
`VideoReader`s (`INFERRED_WORKER_CAP = 4`), each thread claiming
interleaved indices, so each reader grabs through the frames the
others claimed and decode work scales with worker count;
`pipeline/executor.py:54-81` materializes a full `Frame` per node per
frame in DAG order with no fusion.

Attribution, formed independently and then compared with the record's:
the dominant term of the gap is the decode path. v1 runs one
sequential FFmpeg process and crosses the pipe at working size; v2
runs ~4× the decode work, materializes full-resolution BGR in Python,
and resizes per frame. A working-size FFmpeg reader with one
sequential decoder recovers most of the gap with no representation at
all — which the record's own primary already concedes (Exchange 6:
"Two of the three are decode-path defects, not architecture gaps").
The Python-side wins the comments record (z-score affine 2.3–3× of
the preprocess span, 610 µs resize skips, the gray16 path) are real,
measured, and second-order against the decode term.

So the prompt's suspicion is confirmed in substance but was already
half-conceded in the text. What the Context still owes: its framing —
"The occasion is measured rather than argued" followed by the speed
gap — lets a reader believe the *magnitude* evidences the rewrite-rule
system. It does not. The magnitude evidences a decode-path design; what
evidences this record is the *diagnosis cost* — the gap "went
undiagnosed through a whole rewrite" because every rule lived in a
person and in comments, and finding them again took reading both repos
side by side. The narrower ground the Decision actually stands on:
serializability is required by the recipe hash regardless (PAR-0009),
conformance costs nothing (`Opaque(fn)`), and rules that are values
with tests survive redesigns where comments do not. That ground is
sufficient. The Context should claim it and not the speed.

## Exchange 3 — the proof standard contradicts the record's own evidence

The main attack. The Decision's third paragraph: "The executor may
rewrite only where the representation proves the answer is unchanged:
affine composed with affine is affine." The Consequences: "an affine
chain evaluates identically fused and unfused."

Affine-compose-affine is a proof about the *map*, not about sampled
pixels. Sampling once through the composed map is not bit-identical to
sampling twice — the design session says so itself (Exchange 3:
"fusion changes pixels... define semantics at the logical level,
require the planner to be semantics-preserving within a stated
tolerance, and ship a preference that disables fusion"), then
contradicts itself two exchanges later (Exchange 5's property test:
"bit-identical fused and unfused"). PAR-0005 inherits the
contradiction without naming it, and v1's own measurements — the
record's chosen evidence — show the flagship rewrites changing answers:
one-pass sampling differs from two-pass (Exchange 5's own "filters
twice and softens" bonus paragraph), the format-order rule is a 10×
*accuracy* difference, and FFmpeg's area scaler measures 0.364 where
OpenCV's measures 0.321 against the same reference.

Read strictly, "answer-preserving by proof" forbids the very fusion
the record exists to enable. Read loosely, it licenses fusion only via
an unstated convention. The repair is to state the convention: the
answer is *defined* at the logical level — the composed map is the
semantics, and pass count is an implementation detail — which is the
design session's own Exchange 3 position. That choice has teeth and
the record must own them: the naive evaluator is then not the
semantic reference for resample chains unless it too samples once
through the composed map, and the property test restates as identity
under the logical semantics rather than identity between two
evaluation strategies. Until this paragraph is redrawn, the record's
central sentence does not support its central examples.

## Exchange 4 — offload can never clear the silent bar as written

"A subgraph may be lowered to a foreign engine... subject to the same
proof requirement; it is also... the largest available win." No
foreign engine is bit-identical to the local path — v1 measured the
divergence. So under the record's own standard, its largest win can
never be silent: every FFmpeg offload is "user-initiated, shown, and
recorded," a swap ceremony per pipeline, where v1's equivalent was
default-on. Either that is the intent — the record should say so
plainly — or the proof bar admits "equivalent under the defined
logical semantics within the pinned tolerance," which is the same
repair as Exchange 3. The paragraph currently claims a win its own
rules withhold.

## Exchange 5 — the redraw dropped a ruled-in benefit and left citations dangling

Exchange 2 of the prior session ruled in the five-shapes-on-paper
compromise for a stated benefit: "telling a contributor what the
intended factoring is, so the first tracker is not written as an
`Opaque` holding a global. That benefit is a record's, not a module's,
so the record keeps all five." Kendrick: "your argument for the
smallest version with insurance is good." The Exchange 10 redraw then
cut the vocabulary to what is proved — affine map, the sequential
bit, `Opaque` — deleting the guidance benefit without naming the
reversal. Later supersedes earlier within a session and the redraw was
requested, so this is a wobble to acknowledge, not a violation; but
the tree still carries the ghost: two `DEFERRED.md` entries cite
PAR-0005 for text it no longer contains ("stated in PAR-0005 as the
intended factoring"; "PAR-0005 states the shapes beyond `Resample`
and `Opaque` as provisional until their first instance"). A record
under judgment whose tree citations point at its previous body is a
mismatch to fix at or before acceptance — and if the guidance benefit
is still wanted, its home is now those DEFERRED entries' own text or
PAR-0003's how-to ("writing an op"), and something should say so.

## Exchange 6 — the four pipelines against the redrawn record

The method that broke the predecessor, rerun against the rewrite.
Spatial-neighborhood ops (Sobel, blur, erosion): `Opaque`, resting
state, honestly covered. TRex background subtraction: a subgraph
admitted by measurement, routed to PAR-0012, covered. The
frames-to-rows reduction: conceded as Challenge 1 — with one typing
slop: `Opaque` is stated as "frames in, frames out," and a reduction
is frames in, rows out, so the concession's own resting place doesn't
type. `Opaque` should be restated as "no structure exposed, nothing
authorized" rather than a video→video signature.

Challenge 2 (data-dependent domains) is overstated as written. "Run
centroid tracking only within the detected windows" is expressible as
ordinary dataflow: the windows are an upstream *product* with its own
hash, the tracking op consumes them as an input, and the recipe hash
already includes upstream output hashes (DESIGN-SESSION.md,
Exchange 1). Expressibility and hashing do not fail; what fails is
rewrite reasoning *across* the gate edge, which is just a barrier —
and barriers are the vocabulary's normal case. The challenge should
narrow to what actually stands: no rewrite crosses a data-dependent
edge, and a pull-based evaluator gets the skip-what's-not-requested
win without any representation change. Kendrick confirms or corrects;
if this reading holds, the record's honest-concessions section is
carrying a concession it doesn't owe.

## Exchange 7 — smaller defects, and the seam with PAR-0008

- `Opaque(fn)` holds a callable and therefore does not round-trip,
  so the serializability guard's sole exception is also a hole in the
  hashing story: an `Opaque` op's recipe hash must come from tool
  identity plus a hand-bumped version (Exchange 1's `impl_version`),
  and nothing says so. One sentence, owed to PAR-0009 or PAR-0007 at
  their drafting, named here so it isn't rediscovered.
- The record now spans the representation *and* the executor's
  authority, bordering PAR-0008. The seam that keeps both records
  revisable independently: PAR-0005 owns what a form authorizes —
  the property carried by the value; PAR-0008 owns when and whether
  the executor exercises it — the peephole discipline, the naive
  evaluator, the evidence threshold. Stating that seam in one
  sentence in each record is cheaper than the merge question
  recurring.

## Exchange 8 — the value named, and why no other route avoids a rewrite

Kendrick, after the verification half: "does it pass the criteria for
a system, and does it earn its keep? is it necessary? Name the value
explicitly, and how it cannot be gained any other way that doesn't
result in a rewrite."

**The value, named.** PAR-0005 buys exactly one thing with no
substitute: a home in the tree for the executor's speed and
correctness rules, such that a rule is an object with a test beside it
rather than a property of welded code. Everything else the record
touches is either gainable another way or free. Speed itself is
weldable — v1 proves it. The recipe hash is viable at step level —
DESIGN-SESSION.md Exchange 1 hashed params + upstream hashes +
impl_version with tools still owning `run()`; op-level hashing is an
economy (cross-tool cache sharing, rewrite-invariance), not a
necessity. The irreplaceable part is that a rewrite rule needs a
representation to be *about*: a rule is a pair of expressions asserted
equivalent, and welded code contains only one of them. v1's rules were
not merely unrecorded — they were untestable in principle, because the
naive path a rule must be tested against (Exchange 6's discipline)
did not exist as a separate object; verifying the z-score collapse
meant reverting the code. The independent-test-against-naive-path
discipline is only possible when fused and naive both derive from one
description.

**The routes that don't need the representation, priced.** (i) Welding,
v1's route: rules live as code paths plus comments; the measured
outcome is that the next redesign deletes them and the loss is
undiagnosable — the loop already run twice, and the rewrite is the
route's *consequence*, not a risk. (ii) Metadata on callables — tag
`run()` with flags the executor reads: classification becomes
assertable and therefore assertable wrongly (invariant 3's failure
mode, the exact design Prompt 6 rejected), behavior gets smuggled
through the introspected surface (prior session Exchange 8's named
risk), and offload stays impossible regardless, because no metadata
makes a closure pattern-matchable into a filtergraph. Erosion, then
rewrite. (iii) A benchmark pin — end-to-end throughput regression
tests — buys the *alarm* without the representation, and honesty
requires saying so: it would have caught v2's slowdown at rewrite
time. It does not buy the rule: the alarm says slower, not why, and
the rule still has no home to be carried in. v1 had the numbers in
comments; detection was never the failure — portability was.
(iv) Defer the boundary and add it later: the return type of the tool
contract is the one thing not retrofittable per-tool — changing it
changes every tool at once, which is a rewrite by definition. This is
consistent with Exchange 5's overruling of the insurance argument:
the sanctioned reason the boundary lands now is that at n=0 it costs
nothing (`Opaque(fn)` is `run()` with a wrapper), and n=0 is the only
moment that price is available.

**Necessity, decomposed.** The boundary is necessary in that precise
sense: free now, a rewrite later, and without it fusion is foreclosed
at the contract level (design Exchange 3, standing as written). The
authorization semantics is the necessary consequence of permitting
rewrites at all — someone must say which are legal, and the
alternatives are flags (rejected) or total conservatism (no silent
rewrites, i.e. the value forfeited). The cut vocabulary is not
necessary and doesn't claim to be — it is the null hypothesis, holding
only what is proved, and its necessity question dissolves because it
costs nothing to hold.

**The system test.** The named system is the boundary language between
tools and the executor, owned by neither — the same pattern the repo
already sanctions one level up, where `views.py` is "the language
between tools and the GUI, owned by neither" and holds its own module.
Near-decomposability holds the way it does for any interlingua: every
component touches it, but only through the value type, so coupling is
citation-shaped — reversing the decision rewrites PAR-0007/0008/0009
because they *cite* the contract, not because they contain its
reasoning, and dependency-via-citation is the sanctioned interface
between records. Dense inside (what a form authorizes, how forms
compose), sparse across. It earns ARCHITECTURE.md as what invariant 3
becomes, and its keep is cheap by construction: no contributor
obligation, one wrapper class, serializability enforced by machinery
the hash needs anyway. Where it must never claim keep: as a speed
argument — speed is weldable, and the Context correction in
Exchange 2 is what keeps that claim out.

## Exchange 9 — when the system is touched, and the how-tos it admits

Kendrick: "When is the system touched? What is the operationalizable
heuristic for when this system is picked up as a tool, when does it
indispensably live? Say we are writing how-tos about this. What do
they look like?"

**Where it indispensably lives vs. when it is picked up.** Two
different presences. It lives at the boundary — every `lower()`
return crosses it and every recipe hash serializes it — silently,
consulted by no one, load-bearing at every frame rendered. It is
*picked up as a tool* only inside two loops, both evidence-gated:
the performance loop, entered through the cost surface, and the
audit loop, entered through doubt about a number (the reviewer's
fast-vs-naive comparison, DESIGN-SESSION.md Exchange 3's
preference). The one-line heuristic: **if you arrived without a
measurement or a doubt in hand, you are in the wrong place — return
an `Opaque` and leave.** Nobody opens this system to add a feature;
a tool author touches a constructor from it, never the system. Like
a type system: always on, opened rarely.

**The touch occasions, enumerated.** (1) Writing a tool — touches a
constructor only; the null door. (2) Reshaping an `Opaque` — trigger:
the cost surface names it AND the math admits a proved form.
(3) Adding a rewrite rule — trigger: a measured hot pattern across
adjacent nodes. (4) Offloading a subgraph — same trigger, foreign
emitter. (5) Auditing a result — trigger: a reviewer's doubt, not
slowness. (6) Admitting a new form — trigger: a rewrite it would
license is wanted and provable; deliberately NOT a how-to, because it
is a record edit under the admission rule, not a routine task, and
writing a guide for it would invite the taxonomy tax back through the
how-to door. The layer's silence there is the signal that the task is
architecture, not use.

**The how-to set** (the record's first residents at acceptance,
PAR-0003 form: task-oriented, altitude that does not churn, each with
a check step):

1. *Write an op* — return `Opaque(fn)`; ship. One decision table:
   can it be written as an affine coordinate map with no state and no
   neighborhood? Then that constructor; if unsure, `Opaque`. Never
   add a form. Check: suite green. This guide is the "architecture
   asks nothing" outcome operationalized, readable by someone who
   read nothing else.
2. *Diagnose a slow pipeline* — the entry point that dispatches: rank
   per-node wall-clock; classify the top span as decode-bound (reader
   work, not this system), a hot `Opaque` (→ 3), or an unfused chain
   (→ 4/5). Check: name the node and its class before touching code.
   Unwritable until the executor's instrumentation lands (its
   `DEFERRED.md` trigger) — stated, not hidden.
3. *Reshape an `Opaque` into a proved form* — change `lower()`'s
   return; params, view, output surface unchanged. Check: blocked —
   cannot be stated until the Decision's third paragraph is redrawn,
   because bit-identity is false and the defined-semantics bar is
   unstated.
4. *Add a rewrite rule* — state the equivalence as the pair of
   expressions; write the rule over op values; write the independent
   test against the naive path (both derivable from one description,
   Exchange 8); the measured delta lands beside the rule, not in a
   comment — the v1 lesson made procedure. Check: property test
   green, naive-path test green.
5. *Offload a subgraph to FFmpeg* — matcher, emitter, engine version
   pinned in the hash. Check: blocked on Exchange 4's bar decision
   (silent under defined semantics, or swap ceremony).
6. *Audit a result against the naive path* — evaluate with rewrites
   off, compare at the terminal statistic, record the comparison.
   The reviewer's door; owed since Exchange 3 of the design session
   and missing from the record's Consequences list, which names four
   residents and not this one.

**The meta-finding.** Drafting these skeletons is itself part of the
judgment — "admits feasible how-tos" is one of the four criteria —
and it independently confirms the verdict's top two conditions: guides
3 and 5 cannot state their check steps until acceptance conditions 1
and 2 land. A how-to whose check step is unwritable is the cheapest
detector of a hole in the record it descends from.

## Exchange 10 — the acceptance conditions answered

Kendrick directed the skeleton-test technique into the debt system (a
`DEBT.md` marker, stamp `20260803T043526Z`, moving to the how-to
layer's repo-work domain at PAR-0003's acceptance) and asked for the
other three acceptance conditions answered. Mid-argument he supplied
the missing piece for the second: "The defined semantics equivalence
can be suggested by the tool that calls it for the input it calls it
for."

**Condition 1 — where the answer is defined.** The semantics of a
node is the composed map from the nearest barrier, applied once;
sampling count is an implementation detail, not part of the answer.
"Answer-preserving by proof" then means proof under that semantics —
affine∘affine is the same map; a stateless op commutes — never
bit-identity between evaluation strategies. What this costs, stated
rather than hidden: (a) the naive evaluator is not a second
semantics — the pull path already composes coordinates walking up the
chain (DESIGN-SESSION.md Exchange 4, "pulled lazily through the fused
geometric chain"), so naive and fused share the sampling arithmetic
by construction, and the property test survives as compose-order
invariance, which is provable — exactly if affine params are held
exact (integers and rationals compose without rounding), within
stated ulps if they are floats; (b) materializing a mid-chain
geometric intermediate and resampling from it IS answer-changing
under this semantics, so silent materialization is legal only at
barrier outputs (a `Fold`'s table, an `Opaque`'s frames — those are
their own logical values); baking a geometric intermediate is
user-initiated and recorded, like any unproved substitution. The
reviewer's disable-fusion preference (Exchange 3 of the design
session) survives with a changed job: it no longer defines
correctness — nothing privileges the two-pass path — it detects
implementation bugs in rewrite rules, which is Exchange 9's audit
how-to.

**Condition 2 — the offload bar.** Split offload into the two halves
it actually is, and route each to its evidence class (the prior
session's Exchange 8 already states the classes; the paragraph just
never routed them). The *pattern rewrite* — several adjacent nodes
becoming one composed op — is proof territory, same as any fusion.
The *foreign implementation* of that composed op — FFmpeg's scaler
rather than OpenCV's — is a second implementation of an existing op,
which is invariant 4's territory: equivalence earned by measurement,
selection by measured cost, version-pinned. Admission happens once,
at registration or at a swap on the user's footage class — not as a
ceremony per pipeline — which is how a v1-scale win goes default-on
without ever being silent-by-declaration. Kendrick's mid-argument
addition completes the mechanism: the equivalence spec the
measurement judges against — comparator, tolerance, the statistic
that must survive — is *suggested by the tool that emitted the op,
for the input it emitted it for*. The tool knows what its output
means; it declares the yardstick, never the verdict, which keeps
invariant 4 intact (a metric is not an equivalence claim) and fixes
the metric before any search, which is the multiple-comparisons
safeguard's own precondition (`DEFERRED.md`, the corpus entry's
refinement). The suggestion is declarative — a value in the
contract, no runtime reach — so tool purity holds. Routed: the
suggestion surface joins the tool contract (PAR-0007, beside the
guarantee-voiding declaration); the harness consumes it as the
default comparator (PAR-0012). Noted for its trigger: FFmpeg-vs-local
is the first second implementation of any op, so the largest
available win comes due exactly when the measured-equivalence
harness does — one trigger, both entries.

**Condition 3 — the Context re-grounded.** Drop the 10× sentence
from the speed paragraph. Recast the citation as what it measures:
v1's comments record engine-internal ordering as a 10× *accuracy*
difference (0.364 vs 3.80 RMS grey-levels), which is evidence for
the authorization half of the record — rewrites inside an engine
change answers, so what an offload is licensed to do must be pinned
— not for the speed half. The occasion restates on the ground
Exchange 8 named: the speed gap's dominant term is the decode path
and is conceded; what the gap evidences is diagnosis cost — a whole
rewrite could not find the loss because the rules lived in a person
and in comments, untestable in principle for want of a naive path to
test against. The necessity sentence becomes: rules as values with
tests are the only home that survives a redesign, and the boundary
that makes them expressible is free at n=0 and a contract rewrite at
any later moment.

## Exchange 11 — verdict

**The record stands, on narrower ground, and is not ready to accept as
written.** It names a real system (the op representation and the
rewrite authority it carries); the system is load-bearing (the tool
contract's return type, the hash's input, the offload surface); it
earns its place in ARCHITECTURE.md at acceptance exactly as its
Consequences plan; and three of its four claimed how-tos are
followable once code exists. Nothing in it belongs in PAR-0007,
PAR-0009, or PAR-0012 beyond what its Consequences already route.
It should not be cut further: the redraw already cut to the
load-bearing parts, and the attack found no paragraph doing no work.

What acceptance waits on, in order of weight:

1. The Decision's third paragraph redrawn to state where the answer is
   defined (the logical level, per DESIGN-SESSION.md Exchange 3),
   what "proof" then means, and what happens to the
   fused-equals-unfused property test and the reviewer's
   disable-fusion check (Exchange 3 above).
2. The offload paragraph states which bar it clears — swap ceremony
   per pipeline, or proof under the defined semantics with pinned
   tolerance (Exchange 4).
3. The Context corrects the 10× misattribution and re-grounds the
   occasion on diagnosis cost rather than speed magnitude
   (Exchanges 1 and 2).
4. `Opaque` restated as no-structure-exposed; Challenge 2 narrowed or
   defended; the `Opaque` hashing sentence routed; the two dangling
   `DEFERRED.md` citations re-anchored; the PAR-0008 seam stated
   (Exchanges 5–7).

## Exchange 12 — the ruling, and what landed

Kendrick: "Rewrite is clear to go."

Executed in the same sitting, all four conditions: PAR-0005 rewritten
whole (PAR-0001's coherence rule) — the Context re-grounded on
diagnosis cost with the 10× recast as the accuracy evidence it is,
the semantics paragraph redrawn around the composed-map definition
with exact affine parameters and the barrier-only materialization
rule, the offload paragraph split into proof-for-the-pattern and
measurement-for-the-engine with the tool-suggested equivalence spec
routed to PAR-0007 and PAR-0012, `Opaque` restated as
no-structure-exposed, its hashing sentence routed to PAR-0009,
Challenge 2 narrowed to the gate-edge barrier, Challenge 3 narrowed
by the travelling yardstick, the PAR-0008 seam stated in Context,
and the audit how-to added as a fifth resident. The two dangling
`DEFERRED.md` citations re-anchored to the admission rule, with the
retired table's intended-factoring guidance surviving in the entries'
own text — the home Exchange 5 asked to be named.

The record stays `Proposed`: the ruling cleared the rewrite, not
acceptance, so `ARCHITECTURE.md` and `kernel.py` keep reporting the
five-shape table until acceptance amends them in one commit.
