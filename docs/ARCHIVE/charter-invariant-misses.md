# What the two invariant derivations missed

*Discharged. This file's job was to hold open a set of contradictions until the
documents carrying them were amended, and they now have been. It is kept because
the reasoning is the record of why several rules read the way they do, and it is
archive-safe because everything it cites — CHARTER, the two derivations, and the
pre-amendment text of ARCHITECTURE and PLAN — is now frozen or superseded.*

*Its §6 was the sharpest thing in it: ARCHITECTURE §3.1 said a warmup shortfall
was an error, FINDINGS 3 said it was legal and keyed and explicitly corrected
§3.1, and PLAN Phase 6 still verified that it raised — "three documents, two
positions, nothing propagated." ARCHITECTURE §3.1 now keys it and PLAN Phase 6
now checks that a cold frame and a warm frame resolve to different keys. The
other two amendments it identified as unpropagated are also in: the settled
boundary is ARCHITECTURE §4.4, and §5.4 now separates settledness from freshness
while holding frame identity open with a trigger.*

*Its §2 named four invariant-grade properties neither derivation had — keying and
therefore reproducibility, the log as system of record, preview/run equivalence,
and the generation biconditional — and its §5 named five contract-shaped items
with no invariant home. Of those five, the invocation protocol is now
ARCHITECTURE §2.7, migration is §2.9, addressing is §8.5, verification at the
point of consumption gained the one-facility rule at §9.4, and element meaning
was already §8.4. Its §3 corrections to both derivations' proposed checks —
projection, threading, memory, statistics — hold and are why ARCHITECTURE §7 says
what it says.*

*Nothing in it is outstanding.*

---

Both `charter-invariants.md` and `charter-invariants2.md` state up front that they
read only CHARTER, and deliberately so. This file is the other half: what ARCHITECTURE,
ORGANIZATION, PLAN, and FINDINGS already say that changes their conclusions. It is not a
correction of method — the charter-only pass was worth doing, and several of its results
survive contact with the rest of the corpus. It is an accounting of three things: which
of their open questions are already closed, which invariant-grade properties neither file
named, and where a check one of them proposes is weaker than a check already written.

References are to the file that decides the point, not to the charter.

---

## 1. Everything both files flag as blocked is already decided

`charter-invariants.md` closes on two blockers and one dependency. All three are resolved
elsewhere in the corpus.

**The weak/strong responsiveness call.** ARCHITECTURE §3.3 requires every
producer/consumer edge to name its policy — backpressure, bounded buffering, or load
shedding — and §3.4 assigns them: interactive paths shed, export paths backpressure.
PLAN Phase 6 lands this with a check (a saturated interactive edge sheds and reports
shedding; an export edge drops nothing under the same load; no edge grows without
bound). Adaptation is not a separate strong form to be adopted or declined; it is engine
placement in Phase 5, made from Phase 4 cost shapes. The scope decision the file says the
constitution cannot be written without has been made.

**The video-generalization call.** Decided twice. ARCHITECTURE §1.4: the source assets
being video is a property of the operators we have, not of the system of record, and
nothing outside an operator's own input declaration may assume a decodable video exists.
PLAN's amendment clause lists "making video the first source operator" among five moves
that are reversions rather than amendments, and Phase 3 proves the non-video path with a
synthetic-array source before video decode exists as an operator. The file's *Candidate,
pending a scope decision* is a ratified invariant with an exit condition.

**I.a, round-trip fidelity.** ARCHITECTURE §5.2 makes save/load the serialization of the
edit log, so a tuned pipeline is redeployable by construction, and PLAN Phase 2 verifies
that a round-trip changes no key. The file's instinct that this deserves its own ID
because it is guarded by a different mechanism is right; the mechanism already exists.

---

## 2. Four invariant-grade properties neither file names

### Keying, and therefore reproducibility

Neither document contains the word *key*, *determinism*, or *reproducible*. ARCHITECTURE
§1.2 states the admission test both files were reaching for: **membership in the DAG *is*
deterministic keyability**, checked at registration rather than by review. An operator
that reads wall-clock time, machine state, or an RNG it does not declare and seed fails
it. Two runs sharing a key must agree to the operator's declared determinism class
(§1.5), and §1.3 completes it — nothing derived is authoritative, so any cache, proxy, or
materialized intermediate can be deleted with recomputation cost as the only consequence.

This is stronger and far more checkable than either file's admission property (Closure's
"registration rejects non-conforming components"; INV-1's "admitted by contract rather
than by convention"), and it supplies the discriminating replacement for the
non-invariant `charter-invariants.md` correctly rejects. The property that discriminates
is not that the pipeline executes; it is that it *reproduces*. PLAN Phase 5's check —
wipe every cache, proxy, and materialized intermediate, recompute, and require agreement
to each operator's declared class — is a test that only a correct system passes.

FINDINGS 3 is the evidence that this is the load-bearing one. v2 set
`cacheable = deterministic and not stateful` (`core/filter_base.py:250`), raised
`NotCacheableError` for the rest, and skipped any node whose parent was skipped
(`pipeline/dag.py:293`), so one stateful node left the entire downstream graph unkeyed.
Five of seven filters were stateful; the cache was inert past the first one. The remedy is
FINDINGS principle 3 — key the hazard rather than forbid the capability it endangers — and
neither file's invariants can generate that rule, because neither has the concept the rule
is about.

### The log as the single system of record

ARCHITECTURE §5.5: no state that determines a result lives outside the log, with exactly
two named legitimate exceptions — view-local state (zoom, scroll, hover), which changes
nothing computed, and machine-local preferences, which change what is *requested* but
never what an artifact *is*. §5.1 collapses undo, invalidation, and provenance into one
mechanism: undo is truncating the log, invalidation is diffing keys across log positions,
provenance is the log itself.

`charter-invariants2.md` quotes the charter's god-object admission and treats it as a
boundary dispute between three invariants, proposing an ownership split (INV-1 owns graph
mutation, INV-2 the numbers, INV-3 the display). The corpus answers it mechanically, and
mechanically is checkable — PLAN Phase 2 verifies that replay is deterministic and that an
edit invalidates exactly the predicted set of keys and no others. FINDINGS 8 shows v2
answering "what changed" four separate times (whole-`Project` snapshots, one hand-written
`QUndoCommand` inverse per editable thing, gesture coalescing, and twelve distinct change
signals), and FINDINGS 18 shows the result: 691 `self._` references in one tab, holding
`_filled`, `_settled`, `_series_final` because the engine declined to own them.

The consequence for `charter-invariants2.md`'s *considered and rejected as a fourth
invariant*: the tuning loop is not the conjunction of three invariants. It is a view over
the log. That is a different answer and a better one, because it names a mechanism rather
than an ownership convention.

### Preview/run equivalence

ARCHITECTURE §4.2 calls any divergence between what preview shows and what a run produces
"a bug of the highest class, because it silently breaks the user's contract." PLAN Phase 7
makes its test permanent — "the entire guard against the Lambda failure mode and the
reason the phase exists" — and constructs it to be decidable: preview's trigger policy run
at run's resolution, so exactly one thing differs and the comparison is bitwise.

This passes both files' own criteria. Universal: it touches everything the user tunes
against. Existentially loaded: a user tuning against something that is not what they will
get is worse off than one who cannot tune at all, because the failure is silent.
Checkable: bitwise, by construction.

Both files independently dissolved charter §7.1(d) into their other invariants and
concluded nothing was left over. This is what was left over.

### Generation, and the reverse direction

Both files state visibility as enumeration parity — a test comparing registered
capabilities against those reachable from the interface, failing with the unexposed list.
ARCHITECTURE §6.1 makes that test nearly vacuous by generating parameter controls from
declarations: an operator that declares a parameter gets a control for free, and a
hand-written panel means one of exactly two things, an incomplete declaration or a
semantic type with no registered widget (§6.2). Parity is then automatic and the marker
set is the exception list.

The larger omission is direction. §6's Forbids is a biconditional: "capability that exists
in the pipeline and is invisible in the product, **and the reverse — a control whose
behavior the engine does not know about**." FINDINGS principle 8 states it outright, and
FINDINGS 14–15 is the case: v2's engine supported branching, named multi-input ports,
merges, and fan-out while `gui/chain_model.py:87` built edges with `itertools.pairwise`,
and two independent validators checked one property — `ChainKind`/`grade()` in the
interface, `ArraySpec.admits`/`ElementKind` in the engine — with nothing forcing
agreement. `tests/unit/test_chain_model.py:173` then pinned the hand-written catalog
against itself, which makes drift *pass*. Neither invariant file has the reverse
direction, and it is a distinct failure with a distinct check.

---

## 3. Checks already written more strictly than either file proposes

**The projection check.** `charter-invariants.md` proposes "a projection test asserts that
estimates for a target machine profile are produced and are bounded, not that they are
accurate." PLAN Phase 4 anticipates that exact check and rejects it: the fitted shape must
predict a re-run within its interval *and* the interval must be narrow enough to separate
the cheap and expensive ends of a parameter's range on one machine — "without the second
clause the check buys its way to a pass by widening, and 'somewhere between 2 and 200
seconds' counts as a correct prediction." Declining to demand accuracy does not require
abandoning discrimination.

**The threading check.** "A test that no registered component executes on the UI thread"
is satisfied by v2, which had four independent interface threads and still froze, because
each brought its own pool and the split was static (`core/shares.py:8`: `PLAYER_WORKERS=1`,
`PREVIEW_WORKERS=2`, `DETECTOR_WORKERS=2`). The property is ARCHITECTURE §2.2, and it is
the inverse of what the file wrote: an operator never chooses its own thread, process,
buffer size, or cache location, and never reads a machine-capability probe. FINDINGS 17
supplies the placement half — one engine entry point taking requests that carry priority,
deadline, and a shed-or-wait disposition — because N views each holding a private
coalescer compete for one engine with no arbitration, and every surface that re-derives the
orchestration gets it subtly different.

**Memory.** Both files' measurement invariant is entirely about time. ARCHITECTURE §7.5
makes peak working set a declared and measured dimension precisely because exceeding it is
what freezes an interface or ends a run on a smaller machine, "and a time-only model
reports health while that happens." FINDINGS 9 sharpens it: available memory is not
physical memory — v2 already reads cgroup v1/v2 limits and `SLURM_MEM_PER_NODE` — so on a
scheduler-managed machine the ceiling is an allocation, not the hardware. The
laptop-versus-HPC comparison that `charter-invariants.md` correctly identifies as the
existential claim is exactly where a physical-memory model fails.

**Statistics.** Also missing from both: the two questions get two statistics and never one
number — percentile latency for responsiveness, throughput with an uncertainty interval
for feasibility, means not reported (§7.1–7.2); fan-out waits take the maximum, since
wall-clock is set by the largest replicate and per-task progress looks healthy right up
until it does not (§7.3); and cost is computed per *task* from that task's resolved
parameters, never one estimate scaled by task count, because replicates carry their own
parameter overlays and detector pins (FINDINGS 11).

---

## 4. File-specific errors

**`charter-invariants2.md`, INV-2.** "Every unit of work has a measured cost **on the
machine it is actually running on**" is one of PLAN's five named reversions — treating the
machine profile as a label on local measurements rather than a portable descriptor. The
differentiator is estimating for a machine SIEVE is *not* running on, and Phase 4's exit
condition is that the estimator accepts a profile it did not measure and returns an
estimate for it. `charter-invariants.md`'s third clause has this right. Where the two
files disagree, this is the sharpest case, and it resolves in file 1's favour.

**`charter-invariants.md`, Closure.** "Not 'is validated on the way in' but 'cannot be
built wrong'" collides with FINDINGS 16: interactive authoring means the spec is invalid
much of the time it is being edited, and useful work still happens on the valid part. v2's
`runnable_prefix` truncating at the first non-OK step was correct behaviour. The solution
class is that an edit invalidating the graph is a legal log entry, the engine executes the
valid subgraph, and what is unreached is reported. The strongest reading of Closure
forbids that.

**`charter-invariants.md`, invariant V.** The proposed asymmetry — adding a thing inside
an existing type is free, adding a *new type* requires naming the existing type that
cannot hold it — is a gate ORGANIZATION §6 deliberately declines. Proposing a folder is
cheap and stays cheap, "including for agents working without much context," made safe by
§3's dissolve remedy, on the argument that a premature folder is a visible, locatable
mistake with a known remedy while a bespoke function hiding in an unrelated module is
invisible and gets reimplemented. The file's version reintroduces the bureaucracy §6
rejects.

It also misses ORGANIZATION §7's actual anti-reinvention mechanism, which is not
`__init__.py` alone: each bag holding a kind of thing carries a minimal reference member,
in tree and exercised by CI, because "prose instructions for adding a filter drift
silently; a reference filter breaks the build." §7.2 requires the set to cover the hard
shapes — one member carrying state across frames, one taking more than one input, one
changing rate — since a single easy member demonstrates only the easy contract.

**Both files, visibility scoped to the GUI.** CHARTER §43 makes the GUI *and CLI* a
contract with the user, and PLAN makes the CLI the sanctioned surface through Phase 7,
generating its argument surface from the same declarations Phase 8 consumes. Under INV-3
as written — "reachable by the user from the GUI" — Phases 0 through 7 are
unconstitutional. This one was derivable from the charter alone.

---

## 5. Contract-shaped items with no invariant home in either file

PLAN Phase 1 collects the decisions that are cheap now and unpayable later, on the rule
that anything appearing in an operator's contract or in a key belongs there. Five of them
appear in neither invariant file.

*The invocation protocol.* FINDINGS 1 — which calls itself "the single most likely way a
third implementation repeats the second" — records that v2 had three call protocols
policed by three decorators, with the fourth cell of the matrix missing and documented as
missing, so an operator could not both carry state and take two inputs. Meanwhile
`filter_base` declared `Mode`, `rate_changing`, and `output_rate()` and the executor
refused all of them. The consequence is that the detector, the product's centerpiece, was
built beside the pipeline rather than in it. The property is that a capability axis is a
*field of one signature*, never a new signature, and that admission rejects any operator
the engine cannot actually run — so declaration and capability cannot drift. Both files
say components meet their contract by construction; neither notices that a contract can be
satisfiable and unrunnable.

*Checkpointability.* FINDINGS 2: state captured in a closure at bind time cannot be asked
what offset it corresponds to, serialized, or restored. This is not a missing feature but
an unrepresentable one, and it cannot be retrofitted onto operators written against a
signature with nowhere to put it. Neither file makes any claim about ordering — that some
contract fields must be in the first operator or can never be added.

*Migration.* FINDINGS 19 and principle 10: keys include the operator version, versions
churn *because* keys include them, and multi-version coexistence without declared
migration leaves two options — retain every version's code forever, or break saved work.
`charter-invariants.md`'s I.a is round-trip fidelity *within* a version. Charter §58's
"exactly as useful as the rate of the redeployment," which the file quotes, is about a
saved pipeline surviving the code moving forward, and neither file states that property.

*Addressing.* FINDINGS 20: rectangles and uniform grids are baked into the source crop,
the artifact-matching logic, and every view that maps a click to an element, so any
irregular region or irregular element breaks all three at once and none can be fixed
independently. A declared addressing descriptor is Phase 1 contract work.

*Element meaning.* ARCHITECTURE §8.4: a schema says what one value *is*, not only how wide
it is, and there is no safe default, "because the symptom of guessing wrong is a
correct-looking number read under the wrong noun by whatever consumes it next." PLAN
Phase 3 enforces it at registration from the first operator. Neither file has the interop
claim either — outputs readable without reading our source, readers validating rather than
inferring (§8.1–8.2) — which is what actually makes the charter's vague gesture at output
shape into the extensibility ceiling it claims to be.

*Verification at the point of consumption.* ARCHITECTURE §9: an artifact is verified by
reading it back through the same path a consumer would use, and an encoder's success code
is not evidence. FINDINGS 12 records v2 arriving at write–read-back–compare–commit twice
independently, in `detect/tables.py:339` and `pipeline/materialize.py:120`, differing in
strength and in error quality because no bag owned "write an artifact." This generalizes
to every guard either file proposes.

It is also the answer `charter-invariants2.md` looks for and does not find on charter
§Sixth. Its instinct is right — §Sixth is the enforcement substrate that makes every
`Guarded by` line fillable, not a peer crosscutting concern — and ARCHITECTURE §9.2
supplies the mechanism: tests assert on keyed artifacts and observable outputs, and they
survive refactoring *because* §1 already guarantees keys are stable. Test durability is a
consequence of keying, not a separate discipline.

---

## 6. One contradiction inside the corpus itself

ARCHITECTURE §3.1 states that a warmup shortfall is an error, "never a sentinel value
standing in for history that was not there." FINDINGS 3's solution class states that
shortfall is legal at a source boundary and keyed there, and says explicitly that this
"corrects §3.1, which currently makes it an error." PLAN Phase 6 still verifies that a
warmup shortfall raises. Three documents, two positions, nothing propagated.

FINDINGS amends ARCHITECTURE in at least three places — §3.1 above, §4 (restoring
provisional-versus-settled without event-time machinery, finding 6) and §5.4 (extending
views-must-announce from freshness to identity, so a viewport reports the key of what it
is showing rather than silently swapping between pipeline output and raw decode). None of
those amendments are reflected in ARCHITECTURE. Neither invariant file could have caught
this, having read only the charter, but any constitution drafted from this corpus inherits
it, and the `Guarded by` lines are where it will surface.

---

## 7. What survives

From `charter-invariants.md`: the checkability criterion, added to the charter's stated
two, and the refusal to promote the mirror thesis on the grounds that an uncheckable
constitutional rule teaches agents that constitutional rules are decorative. The diagnosis
that §7.1(d) contains invariants 2 and 3 entire, which PLAN Phase 8 confirms independently
from the other end when it admits that generation makes capability *visible* without
making the load→measure→tune→load loop *sequenced*, and calls that "the one weakness
CHARTER names that has no architectural answer yet." And the clause that Attribution is
satisfied by a slow operator with an honest cost model and violated by a fast one with
none, which is worth carrying verbatim into the constitution to stop it reading as a
performance mandate.

From `charter-invariants2.md`: the derivation rule — an invariant is a property whose loss
takes away something the *user* can no longer do, and anything whose loss is "the codebase
gets harder to work in" is a means — which is the right test and the reason its routing of
sections one through six to crosscutting is correct. Its treatment of §Sixth. And minting
no IDs in a draft, given that IDs are permanent.

Both files' disclosure reading of §65 is right, and both arrived at it independently:
the invariant is not parity but that the gap between what the pipeline can do and what the
user can reach is enumerable and loud. ARCHITECTURE §6.1 makes it cheaper to hold than
either file assumed.

What the corpus does not support is `charter-invariants2.md`'s count. Its own loss test,
applied to ARCHITECTURE rather than to CHARTER, admits at least four more: reproducibility
under keying, the log as system of record, preview/run equivalence, and the generation
biconditional. Each passes universality, each names a concrete user loss, and each already
has a check written for it in PLAN.
