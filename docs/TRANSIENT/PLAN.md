# PLAN

Ordered work. STRATEGY, ARCHITECTURE, and ORGANIZATION are meant to stay true;
this document is meant to be finished and deleted. It is derived from those
three and from nothing else — no part of it is shaped by what the current
implementation happens to contain.

**This document has not been rewritten against STRATEGY and is known to be behind
it.** What follows is a correctness pass, not the rewrite: the places where PLAN
stated something the normative set has since decided against are fixed, and the
places where it is merely incomplete are not. Its phase numbering is still its
own, and STRATEGY §8 now states ordering constraints in its own terms — over the
first operator, the first key, the first key trusted, the first engine decision,
the first generated surface — which this document is responsible for mapping onto
an order. That mapping has not been redone. Where STRATEGY and PLAN disagree,
STRATEGY is right.

## Ordering principle

Phases are ordered by verification dependency, not by layer. Several rules in
ARCHITECTURE are prerequisites for *checking* other rules, and that is what
fixes the sequence: the cost model must be measurable before the engine can be
judged, keys must exist before anything derived can be invalidated, and
declarations must be complete before a generated interface can prove they are.

Each phase states the check that can fail. A phase is done when that check runs
in CI, and the next phase does not start before it does. If a phase's check
cannot be written, the phase is misspecified — that is a signal to re-cut it,
not to proceed on judgment.

The rule for deciding what a phase must contain: anything appearing in an
operator's contract or in a key belongs in Phase 1, because changing either
rewrites every operator and invalidates every artifact. Anything that is an
engine implementation choice belongs wherever it is convenient, because it can
be replaced later at no cost to anything else. Most of the early phases are
therefore contract work with very little behavior, and that is the intended
shape rather than a sign of over-planning.

## The standing deferral

No graphical interface before Phase 8. This has been attempted twice by
building the GUI first, and the failure mode is structural rather than
accidental: parameter controls written before operator declarations are complete
must be written by hand, hand-written controls become the only place some state
lives, and the tab that owns them becomes the de facto system of record. That is
ARCHITECTURE §5.5 and §6.1 being violated at the earliest possible moment, and
no later discipline recovers from it.

STRATEGY §0's disclosure obligation — no capability is silently unreachable — is a
completeness condition on shipped features, not a claim about build order. It is
satisfied by Phase 8 generating controls from declarations, and it is
*unsatisfiable* if the controls are written before the declarations they are
supposed to be generated from. Note that the obligation is no longer scoped to a
graphical interface: ARCHITECTURE §6 makes the surface any generated authoring
surface, precisely because a GUI-scoped reading makes every phase before the last
one unconstitutional.

The sanctioned outlet for the intervening phases is the CLI, which is a user
contract in its own right and discharges the disclosure half in full. It is not throwaway: its argument
surface generates from the same declarations Phase 8 consumes, so building it
at Phase 3 is building part of Phase 8.

## Phase 0 — Organizational tooling

Lands: the import-direction and acyclicity check (ORGANIZATION §5.3); the
package surface check, requiring a purpose line and a declared export list per
package (§4.4); the generated module guide (§8), which is the same walk over
packages as the surface check; and the two computable bin signals from §3.3 —
members with no importers in common, and a member with exactly one caller —
emitted as warnings from the same import graph.

Verified by: CI fails on an import cycle, on a package that states no secret,
and on a guide that will not generate. The bin warnings do not fail the build;
they exist so that ORGANIZATION §1 is applied by something other than good
intentions.

Not yet: any inventory of folders written by hand. The guide is generated or it
does not exist.

Rationale for going first: it depends on nothing, and it constrains every commit
after it. Retrofitting an import-direction check onto a finished codebase means
discovering the cycles when they are load-bearing.

## Phase 1 — Contracts and the key algebra

Lands: `contracts/` at level 0, importing nothing of ours (ORGANIZATION §5.1).
Keys as the transitive closure of operator identity and version, resolved
parameters, requested geometry, and input keys (ARCHITECTURE §1.1). The DAG
admission test as executable code, run at registration (§1.2). Declared
determinism classes, bitwise and tolerant, with the class part of the key
(§1.5) — decided here because it costs a field now and costs the rule if
discovered at Phase 5, when the first threaded reduction stops reproducing
bitwise and the only remaining options are a universal bypass flag or keys
weakened to approximate equality.

Four more contract decisions land here for the same reason, none of them
producing behavior yet. An artifact for a stateful operator is a frame range
plus the state it began from, with the start offset in the key (§1.6) —
otherwise output that depends on where a run started is indistinguishable from
output that does not. State is declared checkpointable, serializable at an offset
and restorable from one (§3.5), which is unretrofittable: operators written
without it cannot be made snapshottable afterwards, and every form of random
access depends on it. Parameters are separated from execution context, so source
properties and upstream geometry are supplied by the engine rather than declared
as tunables (§2.5) — a signature-level split. And keys accommodate multi-input
nodes with differing rates and geometries (§2.6), which is nearly free now and a
rekey later.

Two fields land here for the same reason and buy nothing immediately, which is why
they will be skipped if they are not written down: a declared addressing descriptor
for regions and elements, so that mapping an element to a source region is a
declaration rather than an assumed rectangle or uniform grid (FINDINGS 20); and a
declared migration between operator versions, stating whether a version supersedes
an earlier one and how parameters convert, so that saved work can be upgraded and
retired code can actually be removed (FINDINGS 19). Both are contract-shaped, so
both are Phase 1 by the ordering principle. Both are now stated as rules —
ARCHITECTURE §8.5 and §2.9 — rather than only as findings.

Four more land here because STRATEGY §8 constrains them to the first operator or
the first key, and this is the phase that has both. Windows are declared on both
sides, history and lookahead as separate fields (ARCHITECTURE §3.1), which is the
one contract field FINDINGS nominates as the most likely way this implementation
repeats the last. Every capability axis is a field of one invocation signature
rather than a new signature (§2.7), so an operator cannot declare what the engine
cannot run. Determinism is an open registry closed by policy at two, propagating
infectiously with tolerant artifacts pinned, and a declared tolerance derives from
a stated numerical argument naming its source of non-determinism (§1.5, §1.7,
§1.8). And measurements are keyed derived artifacts, so refitting a cost shape is
invalidation and the machine profile is a key term (§1.9) — which is a Phase 1
field even though Phase 4 is the first phase to produce one.

This phase was once also where the two questions ARCHITECTURE §1.5 left open would
be settled — whether determinism class propagates, and what makes a declared
tolerance falsifiable — on the reasoning that writing the key algebra is what
makes them concrete. Both were settled on paper instead, and §1.5's argument that
neither should be was wrong in one specific way: both had already been decided by
what the checks downstream needed, and deferring them meant Phase 5 and Phase 7
would have been written against an answer nobody had stated. What remains here is
implementing them, not choosing.

Also lands here: the test-authoring discipline, because it depends on keys and
on nothing else. Tests assert on keyed artifacts and observable outputs rather
than internals (ARCHITECTURE §9.2), and golden fixtures are keyed like anything
else and regenerable from their keys (§9.3). A suite that survives refactoring is
a consequence of keying rather than a separate discipline — the thing the tests
assert on is the thing §1 already holds stable — and it is a property of how the
first test is written, not something achievable later by rewriting all of them.

Verified by: an operator that reads wall-clock time, machine state, or an
unseeded RNG is refused at registration; two runs sharing a key produce
byte-identical output; every fixture regenerates from its key; no test imports
past a package surface (ORGANIZATION §4.3).

Not yet: operators worth running, or an engine to run them.

## Phase 2 — The edit log

Lands: ordered edits, deterministic replay, key-diffing across log positions,
and spec serialization — which is what makes a tuned pipeline redeployable
(ARCHITECTURE §5.2) — a pipeline built to be reused being worth exactly the rate
at which it is redeployed.

Verified by: replay of a log is deterministic; a save/load round-trip changes no
key; an edit invalidates exactly the predicted set of keys and no others; any
key resolves to the log position and parameter state that produced it.

Not yet: caches to invalidate. Build the diff, not its consumers.

Note what this closes permanently: invalidation *is* the key-diff, undo *is* log
truncation, and provenance *is* the log (ARCHITECTURE §5.1). None of the three
may be built again as its own subsystem later, and a later design discussion
proposing one has missed that this phase happened.

## Phase 3 — One operator, end to end

Lands: a synthetic source operator and a single reference transform operator,
both with complete declarations, executed once, output written with a declared
versioned schema (ARCHITECTURE §8) and verified by reading it back through a
consumer path (§9). The read-back is performed *by a source operator* consuming
that artifact, which makes reingestion — outputs that are reingested or built
upon, which STRATEGY §1.5 calls the normal shape of use rather than an
extensibility nicety — a property of the first slice rather than a later feature
(ARCHITECTURE §8.2). Element meaning is declared and enforced at
registration from the first operator (§8.4); there is no default, because a value
inheriting a meaning it should have redefined produces a correct-looking number
under the wrong noun. These are ORGANIZATION §7's reference members, in CI from
the day they exist, and the set grows to cover the hard shapes — stateful,
multi-input, rate-changing — rather than staying at one easy member (§7.2). The
CLI begins here as the interim surface, and it writes its output as viewable
image sequences — not interface work, no new dependency, and it is what makes
every phase between here and Phase 8 demonstrable to a person rather than only
to CI. A passing check is not a substitute for watching frames move, and the
standing deferral is easier to hold when something is watchable.

The source is synthetic arrays, not video decode. ARCHITECTURE §1.4 forbids
anything outside an operator's input declaration from assuming a decodable video
exists, and video-as-required-input was named as a known limitation to design out
from the beginning. Proving the non-video path with the first slice costs nothing;
introducing video first lets its assumptions leak into every phase after, which
is how the present limitation arose. Video decode is one more source operator,
added once the synthetic one passes.

Verified by: the artifact is verified by read-back rather than by the writer's
success code; a reader that does not import the writer can interpret the schema;
one pipeline's output is another pipeline's source without special-casing; no
module outside a source operator references decoding.

Not yet: fusion, materialization policy, parallelism, or placement. The engine
makes no decisions in this phase.

## Phase 4 — Benchmark harness and machine profiles

Lands: the load parameter (megapixels per second through *n* stages);
attribution of every measurement to a machine profile (ARCHITECTURE §7.4);
cost-shape fitting for the reference operators (§2.3); and the two statistics
kept separate — percentile latency for responsiveness, throughput with an
uncertainty interval for feasibility (§7.1). Means are not reported (§7.2).
Cost shapes may take measured data properties as terms for content-dependent
operators, which makes estimation two-pass — sample the source, then estimate
(§2.3). Without that, the operators users care about most get intervals too wide
to answer the feasibility question. Peak working set is measured and predicted
alongside time (§7.5), since memory is what ends a run on a smaller machine while
a time-only model still reports health.

The literature for this phase is not Kleppmann. Cost estimation with calibrated,
parameter-dependent constants is query optimization, and estimating for a machine
not being run on is analytical performance modeling.

The machine profile is a portable descriptor, not a label on local results. A
fitted cost shape plus another machine's profile must yield a runtime estimate
for a machine SIEVE is not running on. STRATEGY §0 makes laptop-versus-HPC
feasibility the question the tool exists to answer, and it is the one capability
here that cannot be approximated by measuring locally — which is why
the profile's shape is decided in this phase rather than after Phase 5 starts
consuming it.

Verified by: no reported number lacks a machine profile; the fitted cost shape
predicts a re-run within its stated interval, *and* that interval is narrow enough
to separate the cheap and expensive ends of a parameter's range on one machine —
without the second clause the check buys its way to a pass by widening, and
"somewhere between 2 and 200 seconds" counts as a correct prediction; and the
estimator accepts a profile it did not measure and returns an estimate for it. That
third check is satisfiable on one machine with a recorded profile, and it is the
phase's exit condition.

Validating an estimate against the machine it describes needs a second real
machine, and is a gate before shipping rather than before Phase 5 — otherwise the
absence of an allocation stalls the plan, while the only expensive-to-retrofit
property, the profile being portable at all, is already covered above.

Not yet: using the numbers to schedule anything. Measure first, decide in
Phase 5.

Rationale for preceding the engine: ARCHITECTURE §2.3 has the harness fitting
the constants the engine's placement decisions consume. Built in the other
order, the engine's decisions are guesses with no instrument to evaluate them,
and the measurement claim of STRATEGY §0 stops being a property of the system and
becomes a later feature.

## Phase 5 — The engine

Lands: multiple operators, a real DAG, and the decisions ARCHITECTURE §2
reserves to the engine — fusion, materialization, parallelism, placement — made
from Phase 4 cost shapes. Replicates as parallel tasks with fan-out waits taking
the maximum (§7.3), and straggler skew surfaced as the normal case rather than
an anomaly.

Also lands here, because this is the first phase with derived data worth
deleting and decisions worth reserving: deleting every cache, proxy, and
materialized intermediate changes nothing but elapsed time (ARCHITECTURE §1.3),
and operators are denied the choices §2.2 reserves to the engine — no thread,
process, buffer size, or cache location of their own, and no reading of
capability probes. Parallelism is also where determinism classes start paying:
tolerant operators are materialized once per key and reused, never recomputed
and compared (§1.5), which is a scheduling consequence, not an operator
concern.

Verified by: predicted cost for a three-node graph falls inside the measured
interval; the engine's materialization choice is observable rather than
inferred; a full wipe of derived data recomputes to output that agrees to each
operator's declared class; an operator reaching for a probe or a thread fails at
registration.

Not yet: assuming the executing machine is the machine holding the interface.
Placement's interface is shaped for off-box execution from the start
(ARCHITECTURE §10) with one local implementation behind it. Cheap now,
a rewrite later.

## Phase 6 — Streaming, windows, and pressure

Lands: stateful operators with declared history — a bound plus a
parameter-resolved value (ARCHITECTURE §3.1) — with lead-in supplied by the
engine rather than reached for; retuning as replay rather than in-place mutation
(§3.2); a named policy on every producer/consumer edge (§3.3), with interactive
paths shedding and export paths backpressuring (§3.4); and checkpoint-and-replay
made real, since Phase 1 declared the contract and this is the phase that uses it
(§3.5).

Verified by: a saturated interactive edge sheds and reports shedding; an export
edge drops nothing under the same load; no edge grows without bound; entering a
stream at an arbitrary offset by restoring the nearest snapshot and replaying
produces the same bytes as running from the beginning; and a warmup shortfall at
either boundary is keyed rather than raised — the frame computed with a full
window and the same frame computed cold resolve to different keys, and neither
is a sentinel that reads downstream as a real value (ARCHITECTURE §3.1).

Not yet: two code paths for the two behaviors. One graph, differing edge
policies.

## Phase 7 — Trigger policies

Lands: preview as an early trigger over the same operator graph — a second
policy, not a second implementation (ARCHITECTURE §4). Downsampling and proxy
resolution enter here, as *keyed* differences rather than logic differences
(§4.3).

Verified by: the divergence test, constructed to be decidable — preview's trigger
policy run at run's resolution, so exactly one thing differs and the comparison is
bitwise. "Agrees modulo the keyed difference" means nothing across a resolution
change; such a test either compares nothing or asserts something false.
Resolution and proxy differences are covered by keying alone (§4.3), which is the
point of keying them.

This test is permanent. It is the entire guard against the Lambda failure mode
and is the reason the phase exists.

Not yet: any operator that can ask whether it is in preview. An operator that
needs to know is misfactored (§4.1).

## Phase 8 — The generated interface

Lands: parameter controls generated from operator declarations
(ARCHITECTURE §6.1); the widget bag, keyed by the semantic parameter types
declared back in Phase 1 (§2.1, §6.4); every view a view over the log (§5);
staleness as a display state rather than an exception (§5.4); cost and progress
surfaces reading the same declarations the engine reads (§6.3).

The widget bag is what makes generation survive contact with real controls. A
crop dragged on the frame, a curve editor, a threshold picked off a histogram
cannot be derived from a primitive shape, and generating four spinboxes for a
region of interest is unusable. Each is a widget class registered against a
semantic type, so a rich control is a new member of a bag rather than a panel
belonging to one operator — which is the precise move that failed twice before.

Verified by: no parameter *state* lives in a widget — bespoke rendering and
interaction are fine, and some controls are genuinely singular (a plot that is also
a control), but every one of them binds to declared parameters and owns none of
them; and adding a declaration to the reference operator produces a control with no
edit to interface code.

The weak point of this phase: a naive user not knowing where to begin is only
partly answered by generation. Generated controls make every capability
*visible*; they do not make the load → measure → tune → load loop *sequenced*.
STRATEGY §1.6 supplies the part that is answerable — given a target, what can
satisfy its precursors is a query over declarations — and STRATEGY §2 records the
residue plainly: that answers the user who can state a target, and nothing in the
corpus answers the user who cannot. Treat the residue as unresolved design rather
than as work this phase is known to close.

Not yet — and this is the last place it can still go wrong: a bespoke panel for
the one operator whose declaration is awkward. That operator's declaration is
incomplete, and the fix is upstream in its contract (§6.2).

## Safe stopping points

Work stops mid-phase; plans that assume otherwise mislead. The phases are not
equally safe to be interrupted in, and knowing which is which is worth more
before a pause than during one.

Phases 0 through 3 are safe to stop after, and safe to stop *inside*: they leave
a substrate with no half-made decisions — checks, keys, a log, one slice that
runs. Phase 4 is safe to stop after and awkward inside, since a half-fitted cost
model reads as a real one.

Phases 5 and 6 are the dangerous ones. A half-built engine with some edges
lacking a named pressure policy is worse than no engine, because the unnamed
edges look like the named ones and only diverge under load. If work must pause
in either, pause it with every edge policy named even if some policies are
stubs, so the gap is visible.

Stopping inside Phase 7 leaves preview divergence live, which is the failure
mode ARCHITECTURE §4 exists to prevent — so if Phase 7 is started it is
finished, or its preview trigger is reverted and preview does not exist.

## Scope of the rewrite

Written from the three documents without reference to the current
implementation, deliberately. The parts of any existing code most likely to port
unchanged are the pure numeric kernels, whose entire contract is array in, array
out. Anything touching scheduling, caching, materialization, or interface state
is what these documents rewrite, and porting it would reintroduce the coupling
the phases are ordered to prevent.

This plan once required a decision it did not make — whether the existing
implementation is frozen or deleted — on the reasoning that leaving it running
and patchable removes all urgency from reaching Phase 8 and turns the rewrite
into a permanent parallel branch. STRATEGY §7 decided it: frozen, and frozen
*mechanically* rather than by intention, moved to a path CI refuses to run and
packaging refuses to ship, so "just patch it quickly" stops being available
without anyone having to decline it. The warning above was correct about freezing
that leaves the tree patchable, which is a property of the mechanism rather than
of freezing.

Consulting it is bounded to three uses (§7.2): porting a named carry-forward
module, adding an archive entry, and reading a pure numeric kernel whose whole
contract is array in, array out. Reading it to decide how something should be
shaped is forbidden, because its shape propagates most effectively where its code
is good.

## Amending this plan

Phases may be re-cut, merged, or split. Five moves are not amendments but
reversions to failure modes already paid for: pulling interface work before
Phase 8; deferring the benchmark harness past Phase 5; making video the first
source operator; treating the machine profile as a label on local measurements
rather than a portable descriptor; and deferring any contract-or-key decision out
of Phase 1. Each is cheap now and unreachable later — video-first cost SIEVE its
input generality once already, a local-only profile makes STRATEGY §0's central
objective unimplementable while every local number still looks correct, and a
contract decision deferred is paid for by rewriting every operator that was
written before it.

A phase whose check cannot be stated is misspecified and gets re-cut rather than
started.
