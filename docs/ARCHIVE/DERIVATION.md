# DERIVATION

The derivation and evidence behind `principles_inputs_distilled.md`: a full
reading of the corpus, a verification of every FINDINGS citation against the
frozen tree, the adjudication queue, and the second pass that corrected this
file's own method. The distilled file is what survived it and is what should be
read first; this is where its claims come from.

Archive, in STRATEGY §6.4's sense. Its citations point at the frozen tree at
commit `9ed3b40` and at document sections as they stood when it was written,
which is why they cannot go stale. Nothing here is updated to match the current
corpus, and several positions it treats as live have since been amended.

Three documents it refers to no longer exist: `principles.md`, which it was
written to produce and which was deleted once its unique content was moved into
ARCHITECTURE; `CONSTITUTION/_TEMPLATE.md`, the per-invariant form, superseded by
STRATEGY §6's four document kinds and §3's in-code ledger; and `SCRATCH/HANDOFF.md`,
the build order for the constitution the template implied. All three are
recoverable from git history at `9152b38`. The "read order for drafting" below is
therefore historical — the drafting it directs no longer has a target.

Original preamble follows.

---

Working note. Produced by reading CHARTER, ARCHITECTURE, ORGANIZATION, PLAN, FINDINGS,
`CONSTITUTION/_TEMPLATE.md`, and the three scratch derivations, and by checking FINDINGS'
citations against the tree at commit `9ed3b40`. Nothing here is a principle and nothing
here resolves a contradiction. Six sections, in the order asked for.

**Update.** §§4 and 5 have since been answered by the author, and the file has grown a
second half. §7 records the decisions. §8 is the second pass, which corrects this file's own
method in one place. §9 is the adherence corollary. §10 is the assembled candidate set and is
what `principles.md` should be written from. §11 is the do-not-carry list. §12 is what is
still open.

§§1–6 are the pre-answer state and are kept so the reasoning that produced the questions
stays legible. **Three of them are superseded and each now carries an inline marker at the
exact point** — §1's clause 3 (by §8.1), §2's Part E and B19 (by §8.1 and §7.2), and §6's
mirror-thesis recommendation (by §8.3). Do not draft from an unmarked reading of those
sections.

**Read order for drafting:** §10, then §11, then §12. Everything before §10 is derivation and
evidence for it.

Three notes on the instructions this file answers, since they change how it should be read.

**On leaning hardest on FINDINGS.** True of half of it. Each FINDINGS entry interleaves an
*Observed* paragraph, which is grounded, with a *Solution class* paragraph, which is an
assertion of the same epistemic status as anything in ARCHITECTURE — a fix that has never
been built, in a tree that is being deleted. §3 below verifies the observations. It cannot
verify the solution classes, and §2 classifies them as claims rather than as evidence.

**On "check the pre-rewrite commit if a citation does not resolve."** This turned out
unnecessary and slightly misleading. HEAD *is* the pre-rewrite tree — v3 does not exist
yet, and the recent gutting commits removed comments and docstrings from v2 without moving
it. Every FINDINGS line number resolves at HEAD under a `src/sieve/` prefix; none of them
resolve at the pre-gutting commits `c2ca477` or `a45d14a`. FINDINGS' own sentence
"References are to the pre-rewrite tree" is accurate but reads as though it points
somewhere else.

**On "recommend one, but do not resolve any contradiction."** Read as: state the binary,
state what each branch costs, name a preference, and leave the decision unmade. §4 does
that. It does not pick.

---

# 1. THE DURABILITY TEST

## The candidate, and why it is the wrong instrument

> A claim is durable if it survives replacing the GUI toolkit, replacing video with any
> other source kind, replacing the numeric backend, SIEVE being pointed at a subject other
> than ants, and a fourth rewrite of the codebase.

Five substitutions. Four things are wrong with it.

**It certifies what the corpus already concedes.** Each of the five axes is a contingency
some document has already named and defended against: video by ARCHITECTURE §1.4 and PLAN
Phase 3, the numeric backend by §2.2 and `backend_identity`, the toolkit implicitly by
ORGANIZATION §5.1's dependency direction. An enumerated-axis test can only test the axes
you thought of, and these are exactly the axes already thought of. It has no power at all
against the failure that actually happened: v2's `cacheable = deterministic and not
stateful` (`core/filter_base.py:250`), which cost it the entire cache. No toolkit, source,
backend, or subject swap would have flagged that rule, because it survives all five.

**"Survives a fourth rewrite" is circular.** A rewrite is defined by what it keeps. If the
principles document governs the fourth rewrite, the fourth rewrite keeps the principles by
construction and the clause can never fail. If it means "a rewrite that ignores this
document," the clause is unfalsifiable in the other direction — you cannot evaluate it
until it happens.

**It admits too much to be a filter.** "Cost is declared as a shape, not a constant"
survives all five. So does "every measurement is attributed to a machine profile." So does
"do not name a folder `utils`." Those are a contract field, a reporting rule, and a naming
convention; a test that cannot separate them is not filtering, it is passing everything
that is merely true. A principles document's scarce resource is not truth, it is
attention — every claim it holds makes every other claim less likely to be read.

**It does not test the axis that actually expires claims.** Which is scale and topology,
not substitution. "The boundary is one machine per run" (§10) survives every one of the
five swaps and is the single claim in ARCHITECTURE most obviously on a clock — §10 says so
itself. Same for "megapixels per second through *n* stages" (§7.2), which survives all five
and dies the moment an element is a tracked object rather than a pixel (FINDINGS 20 already
anticipates this).

## Proposed test: three clauses

A claim belongs in the principles document only if it passes all three.

### Clause 1 — Discrimination

*Describe, in one sentence, the system in which this claim is false, as something a
competent person would build on purpose. If you cannot, the claim is the product, not a
principle.*

This is `charter-invariants.md`'s checkability criterion, sharpened. It is what correctly
rejects CHARTER 7.1(a) — "the pipeline executes and produces outputs" — whose negation is
"SIEVE does not work," which nobody builds. It admits "nothing derived is authoritative,"
whose negation is a system where a cache is the system of record: a real design, built
often, and the one v2 drifted toward when `MemoryFrameStore` (`pipeline/cache.py:15`) and
`ProxyFrameCache` (`gui/proxy_cache.py:11`) became the only places some frames existed.

The honest prior art is not Popper. It is Lakatos: a research programme has a hard core
held immune by convention, and a protective belt that takes the falsification. A principles
document *is* a hard core — chosen, not discovered. That reframing matters, because it
changes the author's question from "which of these will remain true?" (a prediction, and
not one anyone can make) to "which of these am I willing to reject a change for?" (a
decision, which is answerable today). Every clause below is written for the second
question.

### Clause 2 — Bearer permanence

*Name the noun the claim constrains. State why that noun exists under any implementation.
If the bearer is a today-noun, the claim is contingent on that noun and must be marked.*

Every normative claim constrains something. "Every producer/consumer edge names its policy"
constrains an *edge*. "An operator declares a cost shape" constrains an *operator*. "A
folder exists because it hides a decision" constrains a *folder*. The claim expires exactly
when its bearer stops existing, so stating the bearer makes the claim carry its own expiry
date instead of needing one bolted on.

This subsumes the candidate test and generalizes it. Replacing the toolkit kills claims
whose bearer is *widget*. Replacing video kills claims whose bearer is *frame* or *decode*.
Replacing the backend kills claims whose bearer is *array*. But it also catches what the
candidate misses — claims whose bearer survives while the claim is a policy choice about
the bearer, which is the "one machine per run" case, and claims whose bearer is a word the
corpus has already outgrown, which is why CHARTER 7.1(c) is right to say that "filter" is
too narrow a word for a pipe section.

Bearers in this corpus that are permanent: *derived value*, *the call*, *contended
resource*, *declaration*, *artifact*, *consumer*, *edit*, *unit of work*, *version*,
*module*, *hazard*. Bearers that are not: *frame*, *video*, *widget*, *GUI*, *tab*,
*thread*, *filter*, *pixel*, *rectangle*, *CSV*, *`__init__.py`*.

### Clause 3 — Cost asymmetry

> **Superseded by §8.1.** As stated below, this clause measures cost *per instance*, which
> makes every repo-side claim fail and every contract-side claim pass, and it produced the
> imbalance §8.1 corrects. Read §8.1's replacement wording, not this paragraph. The argument
> below is otherwise intact and is why the clause exists.

*State what adopting the claim costs now versus what adopting it costs after the system is
built. If the ratio is small, the claim is a convention. Conventions do not go in a
permanent document; they go in a linter.*

This is the clause that does the real work and the one the candidate lacks entirely. It is
PLAN's own ordering principle generalized past Phase 1: *anything appearing in an operator's
contract or in a key belongs in Phase 1, because changing either rewrites every operator and
invalidates every artifact.* Turn that into a filter and it says: permanence is worth
spending only on claims that cannot be adopted late.

The extreme end is FINDINGS 2, checkpointability, where the honest ratio is *infinite* —
"retrofitting is impossible because the operators were written against a signature with
nowhere to put it." Next is FINDINGS 1, the invocation protocol, self-described as "the
single most likely way a third implementation repeats the second." At the other end is
ORGANIZATION §2.1's name blacklist, which passes clauses 1 and 2 and has a cost ratio of
one — renaming a folder is free forever. It is true, it is durable, and it is not a
principle.

## What the test admits and excludes

**Admits** (all three clauses): key completeness and the "and nothing else" half of it;
deterministic keyability as the admission test; the invocation-protocol singularity;
checkpointability as an ordering claim; one owner per contended resource and one entry
point per capability; declaration-generates-presentation together with its converse;
element meaning with no default; verification at the point of consumption; the ordered log
as the sole system of record; cost declared as a shape with fitted constants and attributed
to a portable machine profile; a module is a home for a decision that might change;
migration as part of an extension point; and the scope exclusion.

**Excludes:** everything measured in milliseconds; every folder name and layout specific;
phase order; the mirror thesis; every claim scoped to a named surface (GUI, CLI, tab);
`__init__.py` as a mechanism, as distinct from *package surface* as a bearer; and any
enumeration presented as exhaustive — two determinism classes, two path classes, two
trigger policies, three hard shapes.

**Leaves genuinely ambiguous,** and the document should say so rather than pretend
otherwise: claims that are durable in substance but whose only currently checkable form is
contingent. Visibility is the case. The property — the gap between what the pipeline can do
and what the user can reach is enumerable and loud — passes all three clauses. Every
written form of its check names a surface, and surfaces are contingent. The resolution is
to state the property with its bearer as *capability*, and keep the surface in the Check
field, where the template already treats staleness as expected.

## Prior art, named so it can be argued with

- **Parnas & Clements, *A Rational Design Process: How and Why to Fake It* (1986).** The
  most uncomfortable citation and the most relevant one. Their argument is that the design
  record should be written as if the process had been rational, because the rational
  document is the useful one even though the process never is. A principles document
  distilled after three implementations is exactly this, and their caution applies: the
  faked record is valuable *because* it is faked, but it must not be mistaken for a history
  of how the decisions were reached. If the author wants FINDINGS' observations preserved,
  they cannot live inside the principles document — the two documents have opposite jobs.
- **Parnas (1972),** already ORGANIZATION's criterion. Clause 2 is that criterion run
  backwards: a module hides a decision that might change; a principle asserts a decision
  that will not.
- **Lampson, *Hints for Computer System Design* (1983).** Named because it is the
  counterargument to this entire exercise, not because it supports it. Lampson deliberately
  gives hints rather than rules on the grounds that the trade-offs are contextual and a rule
  applied out of context is worse than no rule. If the author wants a document of rules that
  "won't go stale no matter what," Lampson's position is the one to beat, and clause 3 is my
  answer to it: rules are worth their rigidity only where lateness is unaffordable, and
  everywhere else Lampson is right and they should be hints.
- **Policy/mechanism separation (Levin, Cohen, Corwin, Pollack & Wulf, Hydra, 1975).** This
  is ARCHITECTURE §2 — "operators declare; the engine decides" — in its received form. Worth
  naming because it means §2 is not novel, its failure modes are documented elsewhere, and
  the corpus should use the standard vocabulary rather than reinvent it. FINDINGS 7 is the
  classic failure: policy distributed itself across `core/shares.py`, four workers, and
  three caches because no component *was* the mechanism.
- **Saltzer, Reed & Clark, end-to-end (1984),** already named by ARCHITECTURE §9, and
  independently rediscovered twice inside v2 (FINDINGS 12).

Not leaned on, and worth saying why: the RFC-2119 MUST/SHOULD apparatus the template
imports. It is a grammar for rules, not a test for durability, and it will make contingent
claims read as permanent ones because MUST has no tense.

---

# 2. CLASSIFICATION

Deduplicated by property, not by mention, as instructed. Where one property is stated in
three documents, it appears once with all three citations. A statement absent from this
table because it folds into another is marked at the fold. Statements that are about a
document rather than about the system (ORGANIZATION §9, ARCHITECTURE's preamble, PLAN's
amendment clause) are not normative claims about SIEVE and are not classified.

Verdicts: **D** durable, **C** contingent (with the condition that expires it), **S**
already stale.

## Part A — the operator contract and derived data

| # | Property | Stated at | V | Expires when |
|---|---|---|---|---|
| A1 | A key is the transitive closure of everything the output depends on | ARCH §1.1; FINDINGS P2, 3 | **D** | — |
| A2 | ...and nothing else. Route of derivation is provenance, never identity | FINDINGS P2, 3 (`resolve_source.py:47`) | **D** | — |
| A3 | Membership in the DAG *is* deterministic keyability, checked at registration | ARCH §1.2; misses §2 | **D** | — |
| A4 | Nothing derived is authoritative; any derived thing is deletable at recomputation cost | ARCH §1.3; PLAN Ph5 | **D** | — |
| A5 | Key the hazard rather than forbid the capability it endangers | FINDINGS P3 | **D** | — |
| A6 | Determinism is declared, and the declaration is a key term | ARCH §1.5; FINDINGS 3 | **D** | — |
| A7 | ...in exactly two classes, bitwise and tolerant, defaulting to bitwise | ARCH §1.5; PLAN Ph1 | **C** | a third class exists — any operator whose reproducibility is probabilistic rather than numeric (a seeded sampler, a learned model). Adjudication Q10. |
| A8 | Capability lives in the invocation protocol; a new axis is a field, never a new signature | FINDINGS P1, 1 | **D** | — |
| A9 | Admission rejects any operator the engine cannot actually run | FINDINGS 1 | **D** | — |
| A10 | State is a first-class protocol participant: created at a named offset, snapshot, restored | ARCH §3.5; FINDINGS 2; PLAN Ph1 | **D** | — |
| A11 | ...and this must be in the first operator or it can never be added | FINDINGS 2; PLAN Ph1 | **D** | — |
| A12 | An artifact for a stateful operator is a frame *range* plus the state it began from | ARCH §1.6; FINDINGS 3; PLAN Ph1 | **C** | the addressing axis stops being a totally ordered index — a source that is a set of stills, or a sensor stream keyed by timestamp with gaps. The durable core is "the artifact is the span plus its entry state"; *frame* is the today-noun. |
| A13 | An operator declares I/O shape: arity, dtype, geometry transform, temporal extent | ARCH §2.1 | **D** | — |
| A14 | Parameters carry a *semantic* type, not a primitive shape | ARCH §2.1, §6.4 | **D** | — |
| A15 | An operator never chooses thread, process, buffer, cache location, and never probes | ARCH §2.2; FINDINGS 7, 17; misses §3 | **D** | — |
| A16 | Cost is declared as a shape; constants are fitted, never hand-written | ARCH §2.3, §2.4 | **D** | — |
| A17 | A cost shape may take measured data properties as terms, making estimation two-pass | ARCH §2.3; PLAN Ph4 | **D** | — |
| A18 | Cost is per *task*, from that task's resolved parameters, never one estimate scaled | FINDINGS 11 (`replicates.py:30`) | **D** | — |
| A19 | Parameters are separated from execution context supplied by the engine | ARCH §2.5; PLAN Ph1 | **C** | the tuner stops being a human choosing by hand. The split point is drawn at "what a user turns"; a search procedure or an autotuner turns things the corpus calls context. |
| A20 | Operators may take more than one input; the engine reconciles, both inputs key | ARCH §2.6; PLAN Ph1 | **D** | — |
| A21 | Source identity is content-derived or at minimum path-independent | FINDINGS 4 (`cache_key.py:34`) | **D** | — |
| A22 | Frame-exactness is a source-layer obligation verified by test, not an assumption | FINDINGS 5 (`decode/reader.py:86`) | **D** | — |
| A23 | Elements and regions carry a declared addressing descriptor | FINDINGS 20; PLAN Ph1 | **D** | — |
| A24 | Rectangles and uniform grids are the common case of that facility, not the assumption | FINDINGS 20 | **D** | — |
| A25 | A version declares whether it supersedes an earlier one, and how parameters convert | FINDINGS P10, 19; PLAN Ph1 | **D** | — |
| A26 | The source assets being video is a property of the operators, not the system of record | ARCH §1.4; PLAN Ph3; misses §1 | **D** | — |

*Folds:* ARCH §4.3 (proxy/downsampling are keyed differences) folds into A1. FINDINGS P6
folds into A4 plus F3. PLAN Phase 1's five contract items are A6, A10, A19, A20, A23, A25
restated as ordering.

## Part B — execution, pressure, and the engine

| # | Property | Stated at | V | Expires when |
|---|---|---|---|---|
| B1 | History requirement is declared as a bound plus a function of resolved parameters | ARCH §3.1; PLAN Ph6 | **D** | — |
| B2 | Lead-in is supplied by the engine; an operator never reaches backwards for undeclared frames | ARCH §3.1 | **D** | — |
| B3 | A warmup shortfall is an error, never a sentinel | ARCH §3.1; PLAN Ph6 | **S** | contradicted by FINDINGS 3 explicitly and by the tree (`cli/run_cmd.py:134` warns and proceeds). Adjudication Q1. |
| B4 | Windows are declared *one-sided* (history only) | ARCH §3.1 | **S** | FINDINGS 1's solution class requires two-sided windows, and `core/detection.py:23` is the live case. Adjudication Q11. |
| B5 | Retuning is reprocessing, not in-place mutation | ARCH §3.2 | **D** | — |
| B6 | Every producer/consumer edge names its pressure policy | ARCH §3.3; PLAN Ph6 | **D** | — |
| B7 | Interactive paths shed; export paths backpressure | ARCH §3.4 | **C** | a third path class exists — a long-running background derivation the user watches but does not interact with has no assignment under a two-class rule. |
| B8 | A dropped preview frame is correct and must be reported as such | ARCH §3.4, §5.4; FINDINGS 6 | **D** | — |
| B9 | Random access into a stateful stream is restore-nearest-snapshot-and-replay | ARCH §3.5 | **D** | — |
| B10 | Snapshot *frequency* is an engine decision; *being* snapshottable is a contract | ARCH §3.5; FINDINGS 2 | **D** | — |
| B11 | Trigger policy is engine configuration, not a branch inside an operator | ARCH §4.1 | **D** | — |
| B12 | Preview/run divergence is a bug of the highest class | ARCH §4.2; PLAN Ph7; misses §2 | **D** | — |
| B13 | There are exactly two trigger policies, preview and run | ARCH §4 | **C** | a third completeness policy appears (a resumable partial export, a progressive refinement). The durable claim is B11 plus B12; the count is not. |
| B14 | No event-time machinery: no watermarks, no late arrivals, no accumulation modes | ARCH §4 Forbids | **C** | a source arrives out of order — live capture, or several sources joined on wall time. Also partly stale: FINDINGS 6 restores provisional-vs-settled, which §4 currently excludes by naming only the trigger. Adjudication Q3. |
| B15 | One engine entry point taking prioritized, deadlined, shed-or-wait requests | FINDINGS P5, 17 | **D** | — |
| B16 | Surfaces pass requests; they never assemble stages | FINDINGS 17 (`cli/run_cmd.py`, `PreviewSession`) | **D** | — |
| B17 | Fan-out waits take the maximum, not the mean | ARCH §7.3 | **D** | — |
| B18 | An edit that invalidates the graph is legal; the engine runs the valid subgraph | FINDINGS 16 (`chain_model.py:87`) | **D** | — |
| B19 | One machine per run; partitioning is in scope only if work goes off-box | ARCH §10 | **C** | SIEVE submits work off-box, which §10 anticipates and PLAN Phase 5 shapes an interface for. Bearer (*run*) survives; the boundary is a policy choice with a date on it. |
| B20 | Replication, consensus, distributed transactions are permanently out of scope | ARCH §10 | **D** | — |

> **B19 is corrected by §7.2.** "One machine per run" is not contingent-with-a-date. At the
> author's stated scale — 100 replicates, 100,000 video files — it is **already stale**, and
> §10's reserved off-box branch is the normal case rather than the exception.

## Part C — the log and the interface

| # | Property | Stated at | V | Expires when |
|---|---|---|---|---|
| C1 | Parameter edits form an ordered, replayable log; everything else is a view over it | ARCH §5; FINDINGS P7, 8 | **D** | — |
| C2 | Undo, invalidation, provenance, and view refresh are one question answered once | ARCH §5.1; FINDINGS P7, 8; PLAN Ph2 | **D** | — |
| C3 | The log *is* the pipeline spec; save/load is serializing it | ARCH §5.2 | **D** | — |
| C4 | Every edit is representable as data and replay is deterministic | ARCH §5.3 | **D** | — |
| C5 | Views may lag and must announce it; stale is a display state, not an exception | ARCH §5.4 | **D** | — |
| C6 | ...and must announce *which artifact* they are showing, not only freshness | FINDINGS 6 (`gui/player.py`, `core/types.py:120`) | **D** | unpropagated into ARCH §5.4. Adjudication Q3. |
| C7 | No result-determining state lives outside the log | ARCH §5.5; FINDINGS 18 | **D** | — |
| C8 | Two categories sit outside it legitimately: view-local state and machine-local preferences | ARCH §5.5; FINDINGS 8 (`gui/preferences.py`) | **D** | — |
| C9 | Every derived quantity is engine-owned and keyed; views compute nothing | FINDINGS P6, 18 (`density_plot.py`) | **D** | — |
| C10 | Parameter controls are generated from declarations, never hand-written | ARCH §6.1; PLAN Ph8 | **D** | — |
| C11 | A hand-written panel means an incomplete declaration or an unregistered semantic type | ARCH §6.2 | **D** | — |
| C12 | One declaration, many generated presentations — and a test pinning the copy makes drift pass | FINDINGS P4, 13, 15, 18 | **D** | — |
| C13 | Generation covers stage, connectivity, guidance, and the reason-it-cannot-go-here message | FINDINGS 15 | **D** | — |
| C14 | The interface must express everything the engine can, and nothing it cannot | FINDINGS P8, 14, 15, 16; ARCH §6 Forbids | **D** | — |
| C15 | Authoring is graph-shaped, with affordance rules over a graph rather than a sequence | FINDINGS 14 | **D** | absent from ARCHITECTURE and PLAN entirely. Adjudication Q7. |
| C16 | Widget classes are a bag keyed by semantic type; a rich control is a bag member | ARCH §6.4; PLAN Ph8 | **D** | — |
| C17 | Cost and progress surfaces read the same declarations the engine reads | ARCH §6.3 | **D** | — |
| C18 | Functionality not reachable from **the GUI** does not exist | ARCH §6; CHARTER 65 | **S** | PLAN makes the CLI the only surface through Phase 7; CHARTER 43 names the CLI as a contract too. Adjudication Q4. |
| C19 | The gap between engine capability and user reach is enumerable and loud | both scratch files; CHARTER 65 | **D** | — |

## Part D — measurement and outputs

| # | Property | Stated at | V | Expires when |
|---|---|---|---|---|
| D1 | Two questions get two statistics, never one number | ARCH §7.1 | **D** | — |
| D2 | ...and those two are percentile latency and throughput-with-interval | ARCH §7.1, §7.2 | **C** | a third question is asked. Memory headroom (§7.5) is arguably already a third and is filed as a dimension of the same two. |
| D3 | Latency is percentiles, never a mean; throughput is a rate with an interval | ARCH §7.2; FINDINGS 10 (`bench/metrics.py:88`) | **D** | — |
| D4 | Performance is stated against a named load parameter | ARCH §7.2 | **D** | — |
| D5 | ...and that parameter is megapixels/second through *n* stages | ARCH §7 | **C** | an element stops being a pixel in a frame — FINDINGS 20's tracked object or segment. Also expires if the real workload is sparse-event search rather than uniform processing. See §5 Q6. |
| D6 | Every measurement is attributed to a machine profile | ARCH §7.4 | **D** | — |
| D7 | The profile is a *portable descriptor*, not a label on local results | PLAN Ph4; misses §4 | **D** | — |
| D8 | The estimator accepts a profile it did not measure and returns an estimate | PLAN Ph4 exit condition | **D** | — |
| D9 | An interval must be narrow enough to discriminate, not merely correct | PLAN Ph4; misses §3 | **D** | — |
| D10 | The profile carries per-core-class capacity, and available memory is a *budget* not a size | FINDINGS 9 (`core/machine.py`) | **C** | heterogeneous CPU classes and cgroup/SLURM stop being how ceilings are imposed. The durable core is "the ceiling is an allocation, not the hardware"; the mechanisms are dated. |
| D11 | Memory is a declared and measured dimension, not a footnote to time | ARCH §7.5; FINDINGS 9; misses §3 | **D** | — |
| D12 | Responsiveness is specified as named interactions with deadlines, plus a debt register | FINDINGS 10 (`bench/budgets.py:31`, `:133`) | **C** | the interaction set changes, which it does with every surface. The debt register itself is durable; the twelve names are an inventory. |
| D13 | Attribution is satisfied by a slow operator with an honest cost model, and violated by a fast one with none | `charter-invariants.md` II | **D** | — |
| D14 | An output carries a declared, versioned schema written with the data; readers validate | ARCH §8.1 | **D** | — |
| D15 | An output whose consumer is unspecified is not designed | ARCH §8.2 | **D** | — |
| D16 | A schema says what one value *is*, not only how wide it is; there is no safe default | ARCH §8.4; FINDINGS 13; PLAN Ph3 | **D** | — |
| D17 | Column orientation is an implementation detail | ARCH §8.3 | **C** | already conditioned on narrow fact tables by its own sentence. Not a principle; a note. |
| D18 | Intervals and events are a first-class artifact type, holdable as input as well as output | FINDINGS 21 | **D** | contingent on §5 Q2's answer for whether it is *this* rewrite's work, not on whether it is true. |
| D19 | An artifact is verified by reading it back through a consumer's path | ARCH §9.1; FINDINGS P9, 12 | **D** | — |
| D20 | One facility owns staging, read-back, digest, cancellation, atomic commit | FINDINGS 12 (`tables.py:338`, `materialize.py:120`) | **D** | — |
| D21 | Tests assert on keyed artifacts and observable outputs, never internals | ARCH §9.2; PLAN Ph1 | **D** | — |
| D22 | Test durability is a *consequence* of keying, not a separate discipline | misses §5; ARCH §9.2 | **D** | — |
| D23 | Golden fixtures are keyed and regenerable from their key | ARCH §9.3 | **D** | — |
| D24 | Fixtures are synthetic, never downloaded or committed media | FINDINGS mechanisms (`tests/conftest.py`) | **D** | — |
| D25 | A derived view reports its settled boundary as well as its key | FINDINGS 6 (`detector.py:69`) | **D** | — |

## Part E — organization

> **Superseded by §8.1.** The verdicts below were produced by the uncorrected clause 3 and
> systematically demote repo claims. E12 and E14 are **durable**, not convention. The
> paragraph immediately following is the misfire itself, preserved because it is the
> symptom that identified the defect. §8.2 supplies the repo-side claims this Part is
> missing.

The whole of ORGANIZATION shares one bearer, *module*, and one criterion, Parnas 1972. It
classifies as three durable properties and a large body of convention. That is not a
criticism of the document — ORGANIZATION says up front that most of its rules are judged by
a reader — but a principles document that carries all thirty numbered items will be mostly
folder advice.

| # | Property | Stated at | V | Expires when |
|---|---|---|---|---|
| E1 | A module is a home for a decision that might change, not a step in a sequence | ORG §1.1, §1.2, §1.4 | **D** | — |
| E2 | Legitimacy is not enough; a module nobody can locate gets reimplemented | ORG §2, §3 | **D** | — |
| E3 | Dependencies point one way and do not cycle | ORG §5.1, §5.2, §5.3 | **D** | — |
| E4 | A package announces its secret and its exports at its surface | ORG §4.1, §4.2, §4.4 | **C** | Python. Bearer *package surface* is durable; `__init__.py` is not, and the CI check in §4.4 is written against the file. |
| E5 | Reaching past a surface means the surface is wrong or you depend on an internal | ORG §4.3 | **D** | — |
| E6 | Each bag holding a kind of thing carries a reference member, in tree, exercised by CI | ORG §7.1 | **D** | — |
| E7 | ...and the set covers the hard shapes: stateful, multi-input, rate-changing | ORG §7.2 | **C** | the hard shapes change. This one expires by *addition* — two-sided windows are already a fourth (Q11), and FINDINGS 1's matrix argument says the list grows combinatorially. |
| E8 | The target is the *hidden* helper, not harmless duplication | ORG §7.4; CHARTER 39 | **D** | — |
| E9 | The module guide is generated, never hand-maintained | ORG §8.1, §8.2 | **D** | — |
| E10 | An incoherent generated guide is a diagnostic of the codebase, not of the guide | ORG §8.2 | **D** | — |
| E11 | Proposing a folder is cheap and stays cheap, made safe by the dissolve remedy | ORG §6.1–6.4, §3.2, §3.4 | **D** | contested by `charter-invariants.md` V. Adjudication Q5. |
| E12 | Names state a capability; `core`, `backend`, `common`, `utils`, `helpers` do not | ORG §2.1 | **C** | convention. Passes clauses 1 and 2, fails clause 3 — a rename is free at any time. Belongs in a linter, not a principles document. |
| E13 | Many folders is the expected end state; reaching into six bags is normal | ORG §2.3; CHARTER 41 | **D** | — |
| E14 | Two computable bin signals: no common importers, exactly one caller | ORG §3.3; PLAN Ph0 | **C** | Python import graphs. Mechanism, not principle. |
| E15 | Contracts at the bottom, GUI and CLI at the top | ORG §5.1 | **C** | the direction is durable; the named endpoints are two surfaces that exist today. State it as "authoring surfaces are depended on by nothing." |

## Part F — FINDINGS' ten principles

All ten pass all three clauses. Stating that plainly rather than dressing it up: FINDINGS'
principle list is already the closest thing in the corpus to the document being written, and
its survival rate is evidence about FINDINGS, not evidence that the test is toothless. The
test *does* bite elsewhere — six items above are stale, seventeen are contingent, and ORG
§2.1 and §3.3 are demoted outright. It does not bite here because this list was distilled
under a similar filter already.

Mapping, so the principles document does not restate them: P1 → A8/A9. P2 → A1/A2. P3 → A5.
P4 → C12. P5 → A15/B15/D20. P6 → C9. P7 → C2. P8 → C14. P9 → D19/D25. P10 → A25.

The two that are stated *only* here and nowhere in ARCHITECTURE are **P1** and **P3**. P1 is
FINDINGS' own nomination for the most likely repeat failure. P3 is, by clause 3, the highest
value claim in the entire corpus: it is a rule about how to *respond* to a hazard, its bearer
is *hazard*, and it generated a decision that cost v2 its whole cache. Neither has a home in
ARCHITECTURE and neither appears in either invariant derivation.

## Part G — the 21 solution classes

Classified as claims, not as evidence. Most reduce to a property already in the tables; the
column below records only where the solution class asserts something the tables do not.

1 → A8, A9, **plus** two-sided windows (B4, stale as against ARCH §3.1). 2 → A10, A11.
3 → A1, A2, A12, A6, **plus** shortfall legal at a source boundary (B3, contradiction).
4 → A21. 5 → A22, **C** on the specific test shape (sequential-versus-seek byte compare is
video-specific; the obligation is not). 6 → C6, D25. 7 → A15, B15, **plus** "budgets against
one pool, keeping the *shape* of `shares.py`" — **C**, the shape is a v2 artifact. 8 → C1,
C2, C8. 9 → D10. 10 → D12. 11 → A18. 12 → D20. 13 → D16, D14. 14 → C15. 15 → C13, C14.
16 → B18. 17 → B15, B16, **plus** "proxy generation is a keyed operator served like any other
request" — **D**, and stated nowhere else. 18 → C9, C7. 19 → A25. 20 → A23, A24. 21 → D18.

---

# 3. FINDINGS VERIFICATION

Checked against the working tree at `9ed3b40`, prefixing `src/sieve/`. Forty-one distinct
citation sites across sixteen findings and the two closing sections, including all five the
brief named.

## Held exactly

Line-precise at HEAD unless noted. These are the load-bearing ones.

**Finding 1 — three kernel protocols.** All of it. `backend/dispatch.py:30`
`Kernel(frame, params)`, `:34` `MergingKernel(frames, params)`, `:40`
`StatefulKernel(frame, params, state)`. The three cited decorator lines `:146`, `:169`,
`:193` are not the `def` lines (134, 157, 180) but the *port-arity enforcement* inside each
— which is the more precise citation and clearly deliberate. The missing fourth cell is
quoted verbatim and sits at `:195-196`: *"declares input ports ... and no stateful merging
protocol exists yet — the filter that needs one should bring its signature."*
`pipeline/executor.py:107-117` is exact and holds both refusals verbatim: non-`STREAMING`
("one frame in, one frame out — a windowed filter needs a span") at 108-112, `rate_changing`
("no way to emit nothing for an input frame") at 113-117. `detect/detector.py:35` `detect()`
consumes the whole series. `core/wavelet.py:76` `morlet_power`. `core/detection.py:23`
`hi = np.minimum(n_frames, t + (window - window // 2))` — the lookahead, exact.

**Finding 3 — cacheable, and the downstream skip.** The strongest-verified finding in the
document. `core/filter_base.py:250` `cacheable = self.deterministic and not self.stateful`,
exact. `pipeline/cache_key.py:61` raises `NotCacheableError`, exact.
`pipeline/dag.py:311` `except NotCacheableError: continue`, exact. `pipeline/dag.py:293`
`if any(parent not in keys for parent in fed.values()): continue`, exact — one unkeyed node
does silently unkey its entire downstream. `pipeline/plan.py:89-94` `lead_in_shortfall` and
`warmed`, exact. And the negative claim checks out: `node_key`'s digest terms
(`cache_key.py:68-75`) are upstream keys, `filter_id`, `version`, canonical params, and
`backend_identity` — no shortfall, no decode start, no span, no start offset. The hazard
comment at `:90-95` of `dispatch.py` survives the gutting verbatim, including *"dag.py would
give the node a cache key and serve its output to a run that started somewhere else."*
`pipeline/resolve_source.py:47` `resolve()` returns `identity = source_identity(path)` at
`:70` when a crop backs the replicate, while `dag.py:286` drops the ROI for pre-cropped
sources — so the same frames do key differently. `storage/crop_writer.py:37` `write_ffv1`.
`backend/identity.py:17-20` names numpy version and a policy int and nothing about BLAS,
threads, or SIMD.

**Finding 7 — one owner per contended resource.** `core/shares.py:8/11/14`
`PLAYER_WORKERS=1`, `PREVIEW_WORKERS=2`, `DETECTOR_WORKERS=2` — exact, and still static.
`core/wavelet.py:127` `workers: int = ALL_CORES` and `:162` the `ThreadPoolExecutor` — exact.
`decode/prefetch.py:21` `resolve_workers` with `INFERRED_WORKER_CAP=4`/`LUMA_WORKER_CAP=2`,
reading `core/machine.py:27` `available_cpus` — exact, and this is a capability probe
reached from outside any engine, which is precisely ARCH §2.2's unenforced rule. The three
caches: `pipeline/cache.py:15` `MemoryFrameStore` is an unbounded `dict[tuple[str, int],
Frame]`; `gui/proxy_cache.py:11` `ProxyFrameCache` is a byte-capped `OrderedDict[int,
QImage]` keyed by index alone; `gui/render_ring.py:22` `RenderFrameRing` wraps it with
`RENDER_RING_SHARE`. All exact. The characterization is right: the only caches with
eviction are interface-side, keyed without reference to what produced the frame, holding
`QImage`.

**Finding 15 — the hand-written catalog and the self-pinning test.** `gui/chain_model.py:36`
`Stage` (four members, interface-only placement taxonomy), `:66` `grade()` emitting
`f"expects {step.kind_in}, receiving {current}"`, `:87` `runnable_prefix` with
`itertools.pairwise`. Engine side: `pipeline/dag.py:201` `_check_edges` calling
`accepts.admits(emits)` and raising `EdgeTypeError`, `:215` `_elements` propagating
`ElementKind`. `gui/wizard_model.py:46` `Guidance`, `:53` `_TAB_SIDE_GUIDANCE` holding
exactly `morlet_band` and `windowed_count`, `:84` `catalog()` calling `discover()` and then
returning a hand-written tuple. `ChainKind.EVENTS` at `:33` with no engine counterpart.
And `tests/unit/test_chain_model.py:173-174` are exactly the two asserted lines. The
CLI-precedent half also holds: `cli/inspect_cmd.py:111` `_parameters` reading
`spec.params_model.model_json_schema()`, `:135` `_guidance`, `filters/__init__.py:23`
`guidance_path`.

**Finding 18 — the god object.** `gui/filter_tab.py:119` `self._chain = parity_chain(30.0)`
— exact, and `:120` does it again for `_defaults`. `_filled`, `_settled`, `_series_final`,
`_partial_published` all initialized in `__init__` at `:134-138`. `gui/density_plot.py:31`
`bin_counts` with `_BINS = 96` at `:28`, `:54` `density_surface`. The 1629-line figure
FINDINGS 8 quotes is exact at HEAD.

**Everything else checked and held:** `detector.py:69` `settled_for` and `:82` `gate_to`
(finding 6); `core/types.py:120` `Frame(data, index, channels)` with no identity field
(finding 6); `pipeline/materialize.py:91` `tee`, `:120` `_verify`, `:148` `_digest`, and
`detect/tables.py:338` `_verify` doing a full row compare, the two independent
write-read-back-compare mechanisms differing exactly as described (finding 12);
`detect/tables.py:76` `series_columns(element)` deriving `unit = f"{element.value}s"`
(finding 13); `gui/coalescer.py` `EXACT`/`SCRUB`/`PLAYBACK`, `_outranks` at `:34`,
`generation`, and `gui/player.py:230` `timerEvent` computing `anchor + int(elapsed * fps *
rate)` (finding 17); `core/filter_registry.py:118`
`params_model.__filter_spec__ = spec` and `core/pipeline_model.py:369` `_readable` refusing
a newer `schema_version` and normalizing older ones (finding 19); `core/types.py:23` `ROI`
as x/y/width/height (finding 20); `core/replicates.py:30` `Replicate` carrying `roi`,
`overrides`, and `detector_overrides`, and `core/pipeline_model.py:165` `resolved_params`
merging them (finding 11); `decode/reader.py:86` `_position_at` with `GRAB_FORWARD_LIMIT =
40` and `decode/identity.py:12` `decoder_identity` capturing only the OpenCV version and a
policy int (finding 5); `core/pipeline_model.py:76` `relative_to` and `:448` `relocated`
(finding 4); `gui/document.py:65` `_Gesture`, `:71` `ReplicateDocument`, `:343`
`_would_change`, `:424` `finish_roi_gesture`, and **exactly twelve** `Signal(` declarations
(finding 8); `bench/budgets.py:31` `BUDGETS` holding **exactly twelve** budgets starting
with `open_to_first_frame`, `:133` `IN_DEBT` (finding 10); `bench/metrics.py:88`
`median_ms` and `:94` `worst` with no percentile function anywhere in the module (finding
10); `gui/resource_probe.py:36` `ResourceSample` with `over_ledger` at `:45`;
`cli/app.py:23-28` the six commands; `tests/conftest.py` with the quoted sentence and
`QT_QPA_PLATFORM=offscreen` at `:26`; `bench/metrics.py:112` `METRICS = MetricBus()`; and
all four cited `__init__.py` files containing literally the single word `pass`.

## Errors found

**(a) "Five of seven filters are stateful" (finding 3) is wrong — it is four of seven.**
`background_ema.py:58`, `block_signal.py:72`, `motion_history.py:105`, and
`temporal_baseline.py:76` declare `stateful=True`. `downsample`, `normalize`, and `rescale`
do not. The lesson is unaffected — with `dag.py:293` skipping any node whose parent was
skipped, one stateful node mid-chain still unkeys everything after it, and three of the four
are mid-chain — but the number should be corrected before it is quoted into a permanent
document.

**(b) "691 `self._` references" (finding 18) is the wrong noun for the right number.** 691
is the count of *lines containing* `self._`. The reference count is **817**, across **154
distinct attribute names**. The 154 is the figure the lesson actually wants: it is the
number of things the tab is the sole owner of.

**(c) "Four independent interface threads" (finding 7) is an undercount, and one of the four
citations points at the wrong file.** There are five `QThread()` sites:
`gui/preview_runner.py:304`, `gui/detector_worker.py:140`, `gui/materialize_worker.py:72`,
`gui/player.py:77`, and `gui/resource_probe.py:98`. `gui/decode_worker.py` creates no
thread — it is a `QObject` moved onto the thread `player.py:77` creates and names
`"sieve-decode"` at `:78`. The finding's own point is strengthened: the fifth thread is the
resource probe, which exists to watch the other four.

**(d) `gui/commands.py` has ten `QUndoCommand` subclasses, not the nine listed** —
`RestoreSnapshot` at `:285` is omitted. Immaterial to the lesson.

**(e) Off-by-small citations,** all resolving to the right construct: `core/detection.py:16`
→ 17 and `:29` → 30; `detect/tables.py:174` → 176; `gui/history.py:14` → 13 (where
`SNAPSHOT_LIMIT = 50` actually sits); `gui/density_plot.py:32` → 31;
`detect/detector.py:32` → 30 (`:32` is `band_rows`, not `intervals`).

**(f) `gui/density_plot.py` overstates the coupling.** `bin_counts` and `density_surface`
are module-level functions in the widget's module, not methods on the widget. FINDINGS says
the surface is built "inside the widget." The lesson — a quantity derived in a view cannot
be keyed, cached, or reused — holds only if the widget is the sole caller, which is likely
but is a weaker claim than the text makes. Worth a re-read before it is cited as evidence.

## The one lesson that does not follow from what is there

**Finding 15's use of the test as evidence.** Both halves of the observation are true:
`test_chain_model.py:173-174` does assert the hand-written kinds against the interface's own
catalog, and that does make drift pass. But the test carries its own rationale at
`:167-170`, and the rationale asserts the opposite of the finding. The test is named
`test_kinds_are_not_derivable_from_filter_specs`, and its comment reads: *"both an image step
and the block step emit GRAY float32 per FilterSpec, so the chain model's kinds carry a
distinction the type system cannot."*

That comment is stale, as of commit `48635fc` ("An element of a frame now says what it is,
and a count says so too"). `core/filter_base.py:199-211` now **refuses registration** of any
array-emitting filter that declares no element meaning, with an error message that is
ARCHITECTURE §8.4 nearly word for word — *"There is no default on purpose: a filter that
redefines its elements..."* And the filters comply: `block_signal.py:65` declares
`element=ElementKind.BLOCK`, `normalize.py:43` declares `ElementRelation.PRESERVED`,
`rescale.py:27` declares `ElementRelation.AGGREGATED`. The IMAGE/BLOCK_SERIES distinction
*is* derivable from the declarations today.

So the finding's conclusion is right and its evidence is stronger than it claims, but it is
citing the test for the wrong proposition. The test is not evidence that the property is
underivable. It is evidence that **a stale rationale comment kept a duplicate alive after the
thing that justified it had been built** — which is a sharper and more transferable lesson
than the one recorded, and one that no import check or type check would catch.

Two consequences worth carrying:

- ARCHITECTURE §8.4 and PLAN Phase 3 both present element meaning as new work. It exists,
  enforced at registration, with no default, in the tree being replaced. Under clause 3 of
  §1's test that makes it a **convention to port**, not a principle to spend permanence on —
  *unless* the durable claim is specifically the no-default rule, which is a different and
  narrower statement than "outputs declare element meaning," and is the one worth writing.
- The v2 `EVENTS` kind (`chain_model.py:33`) still has no engine counterpart, because the
  detector is still outside the DAG. That half of finding 15 is intact and is the same
  problem as finding 1. See adjudication Q11.

## Cannot confirm

Finding 5's central claim, and it says so itself: *"Whether v2's sources actually seek
exactly is untested here."* Everything around it verifies — `_position_at`'s
grab-forward-then-seek at `reader.py:86-92`, `GRAB_FORWARD_LIMIT = 40` at `:13`,
`decoder_identity` capturing no seek path — but I did not run a seek-versus-sequential byte
comparison, so the *hazard* is confirmed and the *defect* is not. The finding is correctly
hedged and should stay hedged.

---

# 4. THE ADJUDICATION QUEUE

> **ANSWERED. All twelve are decided. Nothing in this section is open.** It is kept as the
> statement of what each branch costs, which is the part a drafter still needs. The decisions:
>
> **Q1** shortfall legal and keyed. **Q2a** determinism infectious, tolerant artifacts pinned.
> **Q2b** bound derived from a stated numerical argument, declaration names the source of
> non-determinism. **Q3a** amend §4, restore provisional-versus-settled. **Q3b** the component
> has a named contract and is swappable; the coupling is the point, see §8.6. **Q4** visibility
> is a debt keyed to the capability it depends on, generated not written, see §8.4. **Q5**
> creation stays free, the check sits on subsequent behaviour, see §8.5. **Q6** reframed —
> freezing has already failed once, what crosses a rewrite boundary is a check, see §7.6.
> **Q7** graph-shaped authoring from the start. **Q8** one query, two lifetimes; the mirror,
> see §8.3. **Q9** false dichotomy, SIEVE does both, UI design is not an agent's concern.
> **Q10** open registry, closed by policy. **Q11** two-sided windows in Phase 1, detection is
> an operator. **Q12** measurements are keyed artifacts inside §1.
>
> Full statuses in §7.4. Where an answer changed the framing rather than picking a branch —
> Q3b, Q6, Q8 — the section below is the *superseded* framing and §§7.6, 8.3, 8.6 are the
> answers.

Twelve. Each is a binary the corpus states both sides of, or leaves genuinely open. The
recommendation on each is a preference, not a decision — **all twelve are the author's
call.**

### Q1 — Warmup shortfall: error, or legal and keyed?

ARCHITECTURE §3.1 says a shortfall is an error, "never a sentinel value standing in for
history that was not there." FINDINGS 3's solution class says shortfall is legal at a source
boundary and keyed there, and states outright that this "corrects §3.1, which currently makes
it an error." PLAN Phase 6 still verifies "a warmup shortfall raises rather than emitting a
sentinel." The tree does neither: `cli/run_cmd.py:134` prints a warning and proceeds, and
`node_key` does not include the shortfall — which is the exact defect finding 3 diagnoses.

- **Error.** Every operator with a declared window is unusable in the first *w* frames of
  every source. A user who crops the start of a recording gets a refusal rather than a
  result. Simplest key algebra; smallest contract.
- **Legal and keyed.** `lead_in_supplied` becomes a key term, and a cold frame N and a warm
  frame N are different artifacts that never collide. Costs one field in the key and one in
  the artifact descriptor, both in Phase 1. Makes §3.1's forbidden case — a sentinel
  indistinguishable downstream — impossible by construction rather than by prohibition,
  because the two results are no longer the same key.

*Preference:* legal and keyed. It is FINDINGS principle 3 applied to its own case (key the
hazard rather than forbid the capability), and the error branch forbids a capability every
real source needs. Note that adopting it requires editing §3.1, PLAN Phase 6's check, and
the ordering claim that §3.1 is settled — three edits, not one.

### Q2 — Does determinism class propagate, and what makes a tolerance falsifiable?

ARCHITECTURE §1.5 leaves both open deliberately, and PLAN Phase 1 says it settles both
"against a test." Neither document states what either answer would be. They are separate
questions and should be adjudicated separately.

**Q2a, propagation.** Can an artifact computed from a tolerant input be bitwise?

- **Yes, propagation stops at the boundary.** A tolerant operator materializes once per key;
  everything downstream reads those fixed bytes and is bitwise with respect to them. Cheap,
  and matches how §1.5 already says tolerant artifacts are handled. But it collides with
  §1.3: if the tolerant intermediate is deleted and recomputed, the "bitwise" downstream
  artifact changes, so *not everything derived is freely deletable* — a real exception to a
  rule stated without exceptions.
- **No, tolerance is infectious.** Anything transitively downstream of a tolerant operator is
  tolerant. Preserves §1.3 exactly. Costs the ability to compare downstream artifacts
  byte-for-byte, which is what PLAN Phase 5's wipe-and-recompute check and Phase 7's
  divergence test both rely on.

*Preference:* infectious, with tolerant artifacts *pinned* — deletable, but a delete is
recorded as invalidating the byte-identity claim rather than only the cost. That keeps §1.3
true and makes the §1.3 exception visible instead of silent. This is a third option, so it
needs a decision either way rather than a default.

**Q2b, tolerance discipline.** §1.5 says "a bound chosen to make its own test pass is not a
check" and stops there.

- **Bound declared by the operator author.** Fast; reproduces the exact failure §1.5 names.
- **Bound derived from a stated numerical argument** (condition number, accumulation order
  bound, documented library guarantee), with the argument in the declaration and the test
  checking the *argument's* prediction rather than the author's number.

*Preference:* the second, narrowed — require the declaration to name the *source* of
non-determinism (threaded reduction, float atomics, library build) rather than only a
number, because the source is checkable by inspection and the number is not. This is
FINDINGS 3's complaint about `backend_identity` in a different place: "a version string is
not a determinism guarantee."

### Q3 — FINDINGS' unpropagated amendments to §4 and §5.4

Two amendments, both asserted by FINDINGS 6's solution class, neither reflected in
ARCHITECTURE.

**Q3a, §4 and provisional-versus-settled.** §4's Forbids says "No event-time machinery is
implied here: SIEVE has no watermarks, no late arrivals, no accumulation modes. Only the
trigger." FINDINGS 6 restores provisional-versus-settled — the settled-prefix boundary v2
already computes at `detector.py:69-79` — arguing it follows from any lookahead window
rather than from event time.

- **Keep §4 as written.** A view shows what it has; completeness is not modeled. Whatever
  the detector's settled-prefix logic was, it becomes a detector-local concern again — which
  is how it ended up inside a widget (finding 18's `_settled`).
- **Amend.** Completeness boundary becomes part of what an artifact carries, distinct from
  freshness. §4 keeps its refusal of watermarks and out-of-order arrival, which remain
  referentless, and gains one concept.

*Preference:* amend. The boundary is a property of *the computation*, computable from the
declared window, and putting it in the artifact is what stops it living in a tab. §4's
refusal of event-time machinery survives untouched — the distinction the Forbids is
protecting is watermarks, not completeness.

**Q3b, §5.4 and identity.** §5.4 says views may lag and must say so. FINDINGS 6 extends this
from freshness to identity: a viewport must report the *key* of what it is showing, because
v2's player silently swapped between pipeline output and raw proxy decode
(`gui/player.py`, `_display_from_ring` vs `_display_cached`), and `core/types.py:120`
`Frame` has no identity field to make that visible.

- **Freshness only.** One display state. The swap stays invisible.
- **Freshness plus identity.** `Frame` (or its successor) carries the key it came from, and
  every view can say what it is showing. Costs a field on the most-copied object in the
  system.

*Preference:* amend, and note this is not free — it puts a key on every frame, which is the
one place a per-object field has real cost. Worth deciding explicitly rather than inheriting.

### Q4 — Visibility: the GUI, or the user surface?

ARCHITECTURE §6 and CHARTER both scope visibility to the GUI. CHARTER 43 separately makes
the CLI a contract with the user. PLAN makes the CLI the *only* surface through Phase 7 and
argues its argument surface generates from the same declarations. As `charter-invariant-
misses.md` notes, under the GUI-scoped reading Phases 0 through 7 are unconstitutional.

- **GUI.** The invariant is unsatisfiable for the entire duration of the plan that
  implements it. A rule that cannot be satisfied during construction gets ignored during
  construction, which is how rules become decorative.
- **User surface, defined as any generated authoring surface.** Satisfiable from Phase 3.
  Makes the CLI's completeness a real obligation rather than a convenience, which is a cost —
  every declared capability must be reachable from it. And it weakens the original claim: a
  capability reachable only from a CLI flag is not what CHARTER 35's naive user needed.

*Preference:* user surface, with the naive-user problem separated out rather than
smuggled in. They are two claims that CHARTER 65 fuses: *no capability is silently
unreachable* (durable, checkable, surface-independent) and *a new user can find the entry
point* (durable, uncheckable, and PLAN Phase 8 admits it has no architectural answer). Fusing
them is what makes the invariant read as GUI-scoped.

### Q5 — Free folder proposal, or a new-type gate?

ORGANIZATION §6 makes proposing a folder cheap and keeps it cheap "including for agents
working without much context," on the argument that a premature folder is a visible mistake
with a known remedy while a hidden bespoke function is invisible. `charter-invariants.md` V
proposes an asymmetry: adding a thing inside an existing type is free; adding a *new type*
requires naming the existing type that cannot hold it. The misses file calls this
reintroducing the bureaucracy §6 rejects.

- **Free (ORGANIZATION).** Depends entirely on §3.2's dissolve remedy actually being
  applied. §3.3 concedes the problem — "otherwise §1 stays a rule nobody schedules time to
  apply" — and routes two of five bin signals to CI as *warnings*, which nobody has to act
  on. The failure mode is a slow accumulation of legitimate-looking folders that no one
  dissolves.
- **Gated.** One sentence of justification per new folder. Cheap for a human, genuinely
  expensive for an agent with no context — which is the population §6 explicitly optimizes
  for, and the population this codebase expects.

*Preference:* free, with the gate moved to the *dissolve* side instead of the create side —
a folder that has carried a bin warning for N commits must be defended or dissolved. That
keeps creation free and gives §3.2 a trigger, which is the thing it currently lacks. This is
a third option and needs deciding as one.

### Q6 — Is v2 frozen or deleted?

PLAN's "Scope of the rewrite" states the decision is required, states that leaving it merely
available "is the option that quietly ends the rewrite," and does not make it. It is the
default if nobody chooses, and nobody has chosen.

- **Frozen.** No further changes, including fixes. The tree stays readable, which matters
  more than PLAN allows: FINDINGS' 41 citations point into it, and every one of them becomes
  unverifiable the moment it is gone. Several modules are explicitly marked for carrying
  forward — `core/machine.py`, `bench/sweep.py`, `bench/retention_trace.py`,
  `bench/budgets.py`, `tests/conftest.py` — and porting from a deleted tree means porting
  from memory.
- **Deleted.** The phases are the only path and the pressure is real. But it deletes the
  only evidence base the corpus has.

*Preference:* frozen, with the freeze made mechanical rather than intentional — the v2 tree
moved to a path CI refuses to run and the packaging refuses to ship, so "patch it quickly"
stops being available without anyone having to decline. This is the branch PLAN warns about
only if freezing means *patchable*, which is a property of the mechanism, not of the choice.

### Q7 — Is the authoring surface graph-shaped from the start?

FINDINGS 14 says yes: "graph-shaped authoring from the start, with affordance rules defined
over a graph rather than a sequence," and notes that v2's engine supported branching, named
multi-input ports, merges, and fan-out while `chain_model.py:87` built edges with
`itertools.pairwise`. ARCHITECTURE §2.6 allows multi-input operators in the engine. PLAN
Phase 8 lands generated controls and the widget bag and says nothing about graph authoring;
Phase 3's reference operator is a single transform.

- **Graph from the start.** The affordance rules, the placement taxonomy, the
  reason-it-cannot-go-here message, and the divergence between what the engine admits and
  what the interface offers are all defined over a graph once. Costs real design work in
  Phase 8 that PLAN has not scoped.
- **Path first, graph later.** This is exactly what v2 did, and finding 14 is the record of
  what it cost — capability the engine had that "might as well not have existed."

*Preference:* graph from the start, and note that this makes ORGANIZATION §7.2's
multi-input reference member load-bearing on the interface side too, not only the engine
side. FINDINGS 14 says this "must be solved together with 15," and 15 is a Phase 8 item, so
PLAN's Phase 8 is under-scoped either way.

### Q8 — Is an invalid graph a legal state?

FINDINGS 16 says an edit that invalidates the graph is a legal log entry, the engine executes
the valid subgraph, and what is unreached is reported — and says this "belongs in
ARCHITECTURE §1 and §5." It is in neither. It also directly contradicts
`charter-invariants.md`'s Closure ("not 'is validated on the way in' but 'cannot be built
wrong'"), which the misses file already flags.

- **Admission rejects.** Cleanest contract. Makes interactive authoring impossible without
  the interface hiding invalid intermediate states from the engine — which is a second place
  state lives, and is §5.5's forbidden case arriving through a side door.
- **Log accepts, engine runs the valid subgraph.** Interactive authoring is the normal case.
  Requires the log to hold entries that do not resolve to a runnable graph, and requires
  "unreached" to be a first-class reported state rather than an error.

*Preference:* log accepts. Note the consequence for §1.2: "membership in the DAG is
deterministic keyability" is then a claim about *what executes*, not about *what can be
authored*, and the two need different words. That distinction is not currently made anywhere.

### Q9 — Is frame-exactness a gate before the key algebra, or an assumption?

FINDINGS 5 says frame-exactness is "a source-layer obligation verified by test **before any
key schema is committed**." PLAN Phase 1 commits the key algebra and its verification list
does not include it — the list is registration refusal, byte-identity for shared keys,
fixture regeneration, and no imports past a package surface.

- **Assumption.** Phase 1 proceeds as planned. If a decoder turns out not to seek exactly,
  every key ever computed is wrong in a way that is invisible, because two runs that both
  seek the same way agree.
- **Gate.** One test — read a range sequentially, read the same indices after seeks, compare
  bytes — before Phase 1 exits. FINDINGS notes the instrument already exists:
  `tests/conftest.py`'s synthetic video makes frame *n* a solid field of intensity `n * 5`,
  specifically so a test can assert which frame a seek landed on.

*Preference:* gate. The cost is one test against a fixture that exists. This one may be a
straightforward oversight in PLAN rather than a real disagreement, but PLAN's own rule —
"a phase is done when that check runs in CI" — makes it an omission with teeth.

### Q10 — Is the determinism class taxonomy closed?

§1.5 says "one of two classes" and "an operator that declares no class is bitwise." A third
kind — an operator whose reproducibility is probabilistic rather than numeric, a seeded
sampler or a learned model — has no home.

- **Closed at two.** Simplest key algebra. The first operator that fits neither gets forced
  into `tolerant` with a meaningless numeric bound, which is §1.5's own named failure ("a
  bound chosen to make its own test pass is not a check").
- **Open registry, two members today.** The class is a declared name with a declared
  equivalence predicate; `bitwise` and `tolerant` are the first two entries. Costs
  indirection now, costs a rekey never.

*Preference:* open registry, closed by policy. Register exactly two, refuse a third without
an explicit decision. Cheap now under PLAN's own Phase 1 rule, and it does not require
guessing what the third one is.

### Q11 — Where does detection live, and are windows two-sided?

The sharpest unresolved item, and the one FINDINGS calls "the single most likely way a third
implementation repeats the second."

ARCHITECTURE §3.1 declares history only — "how many frames of history it needs." FINDINGS 1's
solution class requires "windows are declared two-sided — history and lookahead."
`core/detection.py:23` is the live case: with `centered`, `window_bounds` reads
`t + (window - window // 2)`, i.e. future frames, which no one-sided declaration can express.
This is why the detector was built outside the DAG (`detect/detector.py:35` consuming the
whole series), why `ChainKind.EVENTS` has no engine counterpart, and why the product's
centerpiece is not a pipeline component. PLAN's Phase 3 reference-member set covers stateful,
multi-input, and rate-changing — not two-sided. ORGANIZATION §7.2 names the same three.

- **Windows stay one-sided; detection stays outside the DAG.** The v2 arrangement, with the
  v2 consequences: the detector is unkeyed, uncacheable, unschedulable, and gets its own
  worker, its own thread, and its own CLI command.
- **Windows are two-sided; detection is an operator.** Lookahead becomes a declared field
  alongside history, the reference-member set grows a fourth hard shape, and the settled
  boundary (Q3a) becomes computable from the declaration rather than hand-derived. Costs one
  contract field in Phase 1, which is where FINDINGS 1 argues it must go.

*Preference:* two-sided, decided in Phase 1. This is the clearest case in the corpus of a
contract field that is nearly free now and a full rewrite later, and it is the one FINDINGS
nominates as the repeat-failure risk. Note that ARCHITECTURE §3.1 as written must change,
and that PLAN's Phase 3 and ORGANIZATION §7.2 both need a fourth shape.

### Q12 — Are measurements keyed artifacts?

Lower priority than the eleven above, but unstated and cheap to settle. ARCHITECTURE §1 says
the system of record is source assets and the pipeline spec and "everything else" is derived,
recomputable, and keyed. §9.3 explicitly keys golden fixtures. Benchmark results are derived
data produced by the system, and nothing says whether §1 governs them. §7.4 requires
attribution to a machine profile, which functions as a key term without being called one.

- **Outside §1.** Measurements are a separate regime with their own store. Two derived-data
  disciplines, and every argument about invalidating a fitted cost shape gets made twice.
- **Inside §1.** A measurement is an artifact keyed by operator, resolved parameters, load
  parameter, and machine profile. Refitting is invalidation. FINDINGS 9's insight — the
  memory ceiling is an allocation, not the hardware — becomes a key term rather than a note,
  which means a measurement taken under a SLURM allocation does not silently satisfy a query
  about a laptop.

*Preference:* inside §1. The machine profile is already doing key work at §7.4; calling it
a key term costs nothing and closes the question of when a fitted constant goes stale.

---

# 5. WHAT THE CORPUS DOES NOT SAY

> **ANSWERED. All ten questions below have been answered by the author.** The answers and
> what they change are in §7.2, and they are load-bearing: five of them collapse into a
> single property that *deletes* a class of prospective principles, and one of them (Q5, the
> scale numbers) invalidates ARCHITECTURE §10 outright. The section is kept because the
> stated *yield* of each question is the reasoning that connects an answer to a principle,
> and a drafter needs that connection. **Nothing here is still being asked.**

Five documents and roughly 1,400 lines, and the science appears in exactly three places:
CHARTER's two user limitations, neither of which yields anything checkable; CHARTER 63's
laptop-versus-HPC feasibility claim, which is about *whether* a project can run and not about
what it produces; and FINDINGS 21, which is filed under extension costs and is the only place
a real workflow surfaces — labelling, imported ground truth, comparing a detector's output
against a human's, several event tracks over one source. Everything else is construction
discipline.

Ten questions. Each is phrased so that the *answer* is a principle, and the yield is stated
so the author can check whether the question is worth their time.

**1. When SIEVE says an event happened and it did not, what does that cost you — and is it
the same cost as SIEVE missing one?**
*Yields:* whether asymmetric error is a system property or a detector setting. If the costs
are asymmetric, "a derived view reports its settled boundary" (FINDINGS 6, D25) stops being a
display nicety and becomes a rule about what SIEVE is permitted to *assert* — and the
provisional-vs-settled amendment in Q3a decides itself.

**2. Is SIEVE's output ever the final answer, or is it always a proposal a human accepts or
rejects?**
*Yields:* whether the durable unit is the artifact or the artifact-plus-a-human-decision.
This decides FINDINGS 21 outright. If a human always adjudicates, intervals are input as well
as output, the timeline must hold tracks regardless of origin, and "events are terminal" is a
defect rather than an extension cost. If not, 21 can wait.

**3. When you hand a tuned pipeline to someone else, what do they need before they trust its
numbers — and what makes them re-tune instead of reusing?**
*Yields:* the actual content of "redeployable." CHARTER 7.1(b) says a saved pipeline is
"exactly as useful as the rate of the redeployment," and the whole corpus reads that as
serialization fidelity (ARCH §5.2, PLAN Phase 2). If the honest answer is "they always
re-tune, their lighting is different," then round-trip fidelity is not the property that
matters and *transferable calibration* is — which nothing in the corpus addresses.

**4. Do the detector's parameters go in a methods section?**
*Yields:* whether provenance is an external obligation or an internal debugging aid. If
external, the log's serialization is a published format, and §8.1's declared-versioned-schema
rule extends to the *spec* — a claim the corpus makes only about outputs. It also makes
FINDINGS 19's migration story a claim about reproducing published work, not about not
breaking saved files, which is a much stronger reason for the same rule.

**5. Over what span does one scientific question run — one video, one recording session, one
season?**
*Yields:* the unit that must be addressable and keyed. §1.6 makes the artifact a frame range
*within one source*. If a question spans forty videos, there is a per-study unit above the
per-source one with no name anywhere in the corpus, cross-source aggregation is a first-class
operator kind rather than a downstream script, and A12's "frame range" is the wrong bearer.

**6. How much of a recording is worth looking at — are you finding rare events in mostly
empty footage, or characterizing something continuous?**
*Yields:* whether the load parameter is aimed correctly, and this is the most likely way the
whole performance section is wrong. §7's megapixels-per-second-through-*n*-stages assumes
uniform work across the source. If the real job is "find forty seconds in six hours," then
"how long to process the whole thing" is not the feasibility question, §7.1's throughput
estimate answers something nobody asked, and the durable claim is about *cost per candidate
found* rather than cost per megapixel. §2.3's content-dependent cost terms gesture at this
and stop short.

**7. When the answer looks wrong, what do you do — re-tune, re-record, or distrust the
tool?**
*Yields:* whether SIEVE owes explanation or only numbers. CHARTER's loop is
load→measure→tune→load with no diagnosis step. If the real loop has a "why did it say that"
step, intermediate artifacts are a user-facing surface, and §1.3's "anything derived is
deletable, the only consequence is recomputation cost" acquires a caveat it does not
currently have — the cost of recomputing something you were in the middle of looking at is
not only time.

**8. What has to be true before you believe a detection threshold is right?**
*Yields:* whether "verification" in §9 means artifact integrity or scientific validity. The
corpus uses one word for both. §9 is about bytes surviving a write — an encoder's success
code is not evidence. If the answer here is "I compared it against hand-scored footage," then
ground-truth comparison is in scope, it decides FINDINGS 21 alongside Q2 above, and detector
evaluation is a pipeline kind rather than a thing done in a spreadsheet.

**9. Which of CHARTER's two user limitations actually loses you a user — the fragile workflow,
or not knowing where to begin?**
*Yields:* which of two incompatible top-level claims the document leads with.
*Recoverability* — every action is undoable and nothing gets slower by doing it — is stated
nowhere as a principle but is what CHARTER 34 describes ("they initiate a crop and then their
workspace is laggy"). *Sequencing* — knowing what to do next — is CHARTER 35 and is the one
PLAN Phase 8 explicitly concedes has no architectural answer. Both cannot be the top claim,
and right now neither is stated as a claim at all.

**10. Name one thing you would refuse to add to SIEVE even though a user asked for it.**
*Yields:* the scope rule with teeth. "Something that doesn't enable something for the
pipeline, it is outside the scope of SIEVE" is the only claim in the entire corpus that can
reject work, and it has never been exercised against a real candidate. One worked example
turns it into a usable rule. Without one, an agent reading it will find that everything
adjacent enables something for the pipeline eventually.

---

# 6. WHAT MUST SURVIVE FROM CHARTER

A note on citation form first, because it affects everything below. CHARTER has no section
numbers. Both scratch derivations cite it by *line number* — "§63," "§55," "§43" — which
resolves only against `docs/CHARTER.md` as it currently stands. Those references die with the
document. Anything carried into the new document must be **quoted**, not cited; a
cross-reference into a superseded file's line numbers is unresolvable within a month and
confidently wrong rather than merely absent.

## Must survive verbatim

Four sentences. In each case rewriting loses something the paraphrase cannot carry.

**1. The existential argument for measurement (line 63).**

> "A version of SIEVE that only runs on some machines is a SIEVE that is ignored by any user
> that cannot run it."

This is the sentence that converts a performance concern into a *scope* concern, and no
paraphrase does it. Every restatement in the corpus — ARCHITECTURE §7's "performance claims
that only hold on the author's machine," PLAN Phase 4's portable profile — is downstream
machinery. The sentence is the reason the machinery exists. Carry the surrounding argument in
substance too: measurement is not a quality attribute of SIEVE, it is the differentiator, and
"there are other tools to do what it does if it is missing this."

**2. The scope exclusion (line 55).**

> "Something that doesn't enable something for the pipeline, it is outside the scope of
> SIEVE."

Ungrammatical, and worth keeping close to as-is anyway — repair the comma splice and nothing
else. The misses analysis is right that this is the only claim in the corpus that can reject
work. Every tempting rewrite inverts it: "work is in scope when it serves the pipeline"
converts a rejection into a permission and loses the entire function of the sentence. It
should be an ID'd rule, because it is the only rule an agent can cite to decline something,
and §5 Q10 exists to give it one worked example.

**3. The disclosure clause (line 65).**

> "This should not be defined from the outset, but must be detectable until the loop is
> closed."

The sentence that makes visibility implementable. Both scratch derivations independently
identified it as the reason the invariant is *disclosure* rather than parity, and PLAN's
entire standing deferral depends on this reading — without it, CHARTER invariant 3 reads as a
build-order mandate and Phases 0 through 7 are illegal. It is easy to lose in a rewrite
because it reads like a hedge. It is not a hedge; it is the operative clause.

**4. The harmless/harmful distinction (line 39).**

> "The refactoring isn't meant to suppress harmless reinvention, it's meant to prevent harmful
> reinvention and fragility."

ORGANIZATION §7.4 restates the substance more precisely — "the target is the helper that is
*hidden*" — but only CHARTER states it about *the refactoring itself*, and that is what stops
the whole document being read as a prohibition list. A principles document assembled from
this corpus will be almost entirely constraints; this sentence is the one that tells an agent
which constraints are not the point. It belongs in the preamble.

## Must survive in substance, but not in CHARTER's words

**The usefulness identity (line 65).** "SIEVE's usefulness as a tool is exactly equal to the
user's knowledge of that tool." The identity is durable and belongs near the top. The sentence
that follows it — "any functionality that is not visible to the user from the GUI might as
well not exist" — must **not** survive verbatim, because "from the GUI" is exactly the stale
scoping in Q4, and the phrase "might as well not exist" is what makes it read as parity rather
than disclosure. Carry the identity; state the property with *capability* as its bearer; put
the surface in the Check field where the template already expects it to age.

**The GUI/CLI as a contract with the user (line 43).** "How the SIEVE GUI and CLI operate is a
type of contract with the user. The ux is how that contract is made apparent." This is the
author, in their own words, already answering Q4 against the GUI-only reading. Substance must
survive because it is what makes the CLI a real surface rather than scaffolding. The wording
is loose enough to rewrite freely.

**The output-shape claim (line 61).** "The shape of them actually shapes the entirety of how
extensible the entire product is." ARCHITECTURE §8.2 states this better and checkably ("an
output whose consumer is unspecified is not designed"). Carry §8.2. The same line's
video-as-limitation concession has been superseded by something strictly stronger —
ARCHITECTURE §1.4 and PLAN Phase 3's synthetic-first source — so carry the conclusion, not
the sentence, and do not carry CHARTER's hedging ("I'm kind of vaguely gesturing at
something").

**The inheritance-of-decomposition cost (line 30).** "New future tabs, and even current
pipelines, have no proper way to inherit the decomposed complexity without huge cost." This
is the only place in the corpus that names *inheritance across surfaces* as the problem.
FINDINGS 17 and 18 are the mechanism — N views each with a private coalescer, a tab that
accretes every derived quantity the engine declined to own — but neither states the cost in
these terms. Substance is worth carrying; the wording is not.

**The description of today's feedback loop (line 17).** "The lagginess of the program tells
them to reel it in, or it was written for the author's (fairly beefy) dev machine." This is
the only description anywhere of what the user's performance feedback loop actually *is*
today, and it is what ARCHITECTURE §2.4 restates from the code side ("a filter that can only
be validated by running the GUI and watching for lag is not finished"). Worth keeping close
to verbatim if the principles document has any room for a "what this replaces" note. If it
does not, §2.4 carries it.

## Keep as preamble, with no ID and no Check

> **Reversed by §8.3.** This recommendation is wrong. The mirror thesis is checkable, the
> author supplied its operational form, and it is a rule with a mechanism rather than an
> epigraph. Carry the sentence verbatim *and* mint an ID for it. The paragraph below is left
> as the record of three passes independently getting this wrong — both scratch derivations
> and this file — which is itself worth knowing when weighing how much the derivations
> settle.

**The mirror thesis (line 69).** "The codebase and SIEVE itself organize as a mirror of each
other." Both derivations reject it as an invariant, on the correct grounds that promoting an
uncheckable claim to constitutional status teaches agents that constitutional rules are
decorative. Agreed, and worth going one step further: it should be carried *verbatim* as an
epigraph precisely because it is uncheckable. It is the only sentence in CHARTER that explains
why ARCHITECTURE and ORGANIZATION are the same project, and the danger the derivations name
applies to *rules*, not to stated intent. Stripping it removes the reason anyone would read
the rest.

## Must not survive

- **The 1(a)–(e) decomposition.** Structurally broken: (d) contains invariants 2 and 3
  entire, and (a) does not discriminate. Both derivations reached this independently and
  PLAN Phase 8 confirms it from the far end.
- **"This is the bear minimum, and SIEVE can do a lot of this today... the things that are
  not are relatively trivial" (line 10).** FINDINGS is a twenty-one-item argument that they
  are not.
- **Everything in the Second through Sixth sections** that ORGANIZATION restates with an
  enforcement point. The toolbag framing (line 41), the `__init__.py` discoverability
  argument (line 47), the runbooks-and-golden-fixtures gesture (line 49), and the
  durable-tests requirement (line 51) each have a stronger successor: ORGANIZATION §2.3, §4,
  §7.1, and ARCHITECTURE §9.2 respectively. The last of these is the important upgrade — the
  misses file establishes that test durability is a *consequence* of keying rather than a
  separate discipline, which is a claim CHARTER could not make and which retires §Sixth
  entirely.

---

# 7. ADJUDICATED

The author answered §5's ten questions and §4's twelve items. Recorded here with what each
closes, what it opens, and where it needs a second pass. Author's words are quoted;
everything unquoted is analysis and is arguable.

## 7.1 The through-line

Stated by the author under Q10 and named as the guide to most of the other answers:

> "The ability to select between different modes being announced to the user and giving them
> full knowledge of what they're selecting bypasses most of the judgements that you seem to
> think SIEVE needs to make. The main outcome of this is that however it is implemented
> eventually, the structural organization of the repo and how the code is organized makes any
> choice possible."

This is the corpus's missing top-level claim, and it is stated nowhere in CHARTER,
ARCHITECTURE, ORGANIZATION, PLAN, FINDINGS, or either invariant derivation. **SIEVE's job is
to make every choice available and legible; it is not to make the choice.** Two halves, and
the second is the organizational one: structure must not foreclose a choice, because the
choice belongs to someone else.

It subsumes four things the corpus states separately: visibility (announce), the open
registry decided at Q10 (the choice is available), the debt system invented at Q4 (announce
what is not available yet and why), and the scope exclusion (do not judge). It is also
strictly stronger than ORGANIZATION §1's Parnas criterion for the case that matters here.
Parnas says hide a decision that might change. This says do not *make* a decision that is
the user's — which is a different obligation, because a well-hidden decision is still made.

Consequences the corpus does not currently draw:

- ARCHITECTURE §1.5's "an operator that declares no class is bitwise" is a default, and a
  default is a choice SIEVE makes on the user's behalf. It survives only because it is a
  claim about *numerics*, not about the user's science — see 7.3.
- ARCHITECTURE §6's generated controls become the mechanism of the top-level claim rather
  than a consequence of §2.1. Generation is what makes "every choice available and legible"
  cheap enough to hold. That is a stronger justification than §6 currently gives itself.
- Every enumeration classified **C** in §2 (two determinism classes, two path policies, two
  trigger policies, three hard shapes) is a foreclosed choice, and the top-level claim says
  they must all be registries. That is a larger commitment than Q10 alone made.

## 7.2 Answers to §5, and what they consolidate

**1, 2, 7, 8, 9 collapse into one property.** "SIEVE gives feedback that is validated against
the user's metrics for what an event is... SIEVE doesn't know what these are and doesn't need
to know what these are." "SIEVE's output is never the final answer... almost a purely
mathematical instrument; SIEVE will produce the answer given what it was told to do." "The
tool itself will do what it says." "The user can validate it. SIEVE makes no judgement on the
validation." "SIEVE has no interest in the scientific question frankly and doesn't exert
opinion on it."

**This kills a class of prospective principles rather than generating one.** No
asymmetric-error rule. No ground-truth comparison in scope. No extension of ARCHITECTURE §9's
verification from artifact integrity to scientific validity — §9 stops at bytes, permanently,
and that is now a decision rather than an omission. FINDINGS 6's settled-boundary reporting
survives, but not as an error-cost claim: it survives because a boundary is a *fact about the
computation*, which SIEVE owns, as against a *fact about the behaviour*, which it does not.
That distinction is the one to write down.

**FINDINGS 21 survives on a different derivation than the one it gives.** It argues for
intervals as first-class from labelling and detector evaluation, both of which answer 8 puts
outside SIEVE. But answer 6 — "it's one step of SIEVE that leads into a second SIEVE session"
— makes intervals an input to SIEVE from SIEVE. So 21 reduces to reingestion, which is
ARCHITECTURE §8.2 and PLAN Phase 3's read-back-by-a-source-operator, and needs no separate
claim beyond intervals being an artifact type with a declared schema. Cleaner, and it removes
the only place the corpus implied a scientific-judgement obligation.

**Answer 5 is the most consequential thing in either round, and nothing in the corpus
survives it intact.** "Footage that spans 3 weeks, 1 week, 8 weeks, 30 hours, 10 minutes...
the 8 weeks footage is over 100 replicates and 100,000 video files."

- ARCHITECTURE §10's "the boundary is one machine per run" is not contingent-with-a-date, as
  §2 B19 classified it. At 100,000 files it is *already* expired. The off-box branch §10
  reserves is the normal case, not the exception, and PLAN Phase 5's "one local
  implementation behind it" is the temporary one.
- §1.6's frame-range artifact has no unit above it. There is no name anywhere in the corpus
  for the collection of 100,000 sources, and §5 Q5 asked for exactly this. Cross-source
  aggregation is a first-class operator kind, not a downstream script, and the addressing
  descriptor of FINDINGS 20 needs a source axis as well as a spatial one. **This is the
  largest single gap the two rounds exposed.**
- §7's load parameter survives (answer 6 declines to privilege sparse or continuous, so
  megapixels/second is not aimed wrong) but the feasibility *question* changes shape: "how
  long on your laptop" is asked about 100,000 files, and PLAN Phase 4's fitted shape must
  extrapolate across source count as well as across machines.
- §2 A12's expiry condition, as written, was the wrong one. The real expiry is not an
  unordered addressing axis; it is that there are 100,000 ordered axes and nothing names
  their union.

**Answer 3 names an operation the corpus has no word for.** "They run SIEVE on a sample of
their footage and likely tune it from SIEVE itself to work with their controlled
environment." Tuning happens on a sample; the run happens on the whole. That validates
ARCHITECTURE §7.1's two-statistic split cleanly — responsiveness is measured on the sample
loop, feasibility is estimated for the full set. What it adds is that *transferring a
pipeline tuned on a sample to a full run* is a first-class operation, and it is not the same
as save/load (§5.2), not the same as preview-versus-run (§4), and not the same as
redeployment to another user (CHARTER 7.1b). It is a third thing and it is unnamed.

**Answer 4 sharpens the differentiator.** "SIEVE is a way to do things other programs can do
but faster; it can be built faster, it can be validated faster, it can be computed faster."
Three speeds, and only the third is what ARCHITECTURE §7 and PLAN Phase 4 measure. Built
faster is ORGANIZATION's whole subject. Validated faster is ARCHITECTURE §9 plus the
generated interface. CHARTER 63's existential argument, which reads as being about compute
speed, is on this answer about all three — and that is a materially stronger claim than the
one §6 of this file recommended carrying forward. The measurement invariant should be stated
over all three or the other two lose their justification.

## 7.3 The scope exclusion now has teeth

The author doubted this: *"I don't know if this gives you enough for teeth though."* It does.
The two exclusions given —

> "it should deliberately exclude analysis of the results (stats on the detections — this is
> user decisions which SIEVE doesn't own), recommendations on how to provide good footage (it
> works with what it's given, a pipeline works with what it receives)"

— are both instances of one rule, and the rule is generated by 7.2's consolidation:

**SIEVE may not own a decision whose correctness depends on the user's scientific question.**

That rejects, without further argument: detection statistics; footage quality
recommendations; any parameter default presented as *recommended* rather than merely
*preset*; quality scores; a "did this work" verdict; automatic threshold selection; and any
ranking of results. It does *not* reject cost estimation, determinism class, pressure policy,
scheduling, or numeric tolerance, because those are decisions about **computation**, not
about **interpretation**. That is the line, and it is checkable by inspection: name the
decision, then name what would make it wrong. If the answer involves the user's animals, it
is out of scope.

This is the only rule in the corpus that can reject work, and it now has two worked examples
and a general form. It should be the first ID minted.

## 7.4 The twelve decisions

| Q | Decision | Status |
|---|---|---|
| 1 | Warmup shortfall legal and keyed; "SIEVE lets the user do the wrong thing but announces loudly where assumptions are failing" | Settled. Requires editing ARCH §3.1, PLAN Ph6's check, and §3.1's claim to be settled. |
| 2a | Determinism infectious, tolerant artifacts pinned | Settled. §1.3 gains a named exception rather than a silent one. |
| 2b | Bound derived from a stated numerical argument, and the declaration names the source of non-determinism | Settled. |
| 3a | Amend §4: provisional-versus-settled restored, watermarks still refused | Settled. |
| 3b | Unsure; "I suspect the bloat answer might prevent the tool from existing" | **Open.** See 7.5. |
| 4 | Visibility is a debt with a due date tied to build order | Settled in substance, needs a second pass on mechanism. See 7.5. |
| 5 | Not free; needs specific criteria or a check | Settled against ORGANIZATION §6. Needs a second pass on *where* the check sits. See 7.5. |
| 6 | Not answered as frozen-or-deleted; reframed | **Reframed, and the reframing is right.** See 7.6. |
| 7 | Graph-shaped authoring from the start | Settled. PLAN Phase 8 is under-scoped; ORG §7.2's multi-input reference member becomes load-bearing on the interface side. |
| 8 | Invalid graphs state the failure mode clearly; user may select any end state; the routes are debts | Settled in substance, needs a second pass on category. See 7.5. |
| 9 | False dichotomy; SIEVE must do both; UI design is not an agent's concern; "the GUI being a glorified parameter interface for the pipeline" | Settled, and it retires §6 of this file's recommendation to separate the two claims. The *capability* to build either is the principle; which one leads is not architectural. |
| 10 | Open registry, closed by policy; the user picks | Settled, and generalized in 7.1. |
| 11 | Two-sided windows, decided in Phase 1; detection is an operator | Settled. ARCH §3.1 changes; PLAN Ph3 and ORG §7.2 grow a fourth hard shape. |
| 12 | Measurements are keyed artifacts inside §1 | Settled. |

## 7.5 Three answers that need a second pass

**Q4 — a debt register with due dates is a second copy of the build order.** The author's
constraint is right and is the novel part: *"the build order must be respected or the things
that are due will be marked to be paid earlier than they can be and will result in v3 having
the same problem as v2."* But if a debt carries a phase number, PLAN and the debt register
are two representations of the same schedule and they will drift — which is ARCHITECTURE §4's
Lambda failure mode applied to documents rather than to code, and FINDINGS principle 4 ("one
declaration, many generated presentations") forbidding exactly this.

The fix is to make a debt name the **capability it depends on**, not the phase it is due in.
"This needs generated parameter controls" is stable; "this is due in Phase 8" is a copy of
PLAN. The phase is then derived, and the debt comes due automatically when its dependency
lands rather than when someone reads a number. That also makes the register queryable in the
way the author asked for — "grouped and accessible to anyone working on the repo" — because
grouping by dependency is grouping by what unblocks it.

Worth noting: **v2 already has this mechanism, in a different domain.** `bench/budgets.py:133`
`IN_DEBT` records accepted performance misses with a prose reason. The author has
independently converged on the same shape for unexposed capability. That is a point in its
favour and a candidate for FINDINGS' carry-forward list — as a *behaviour with a test*, not
as a module (see 7.6).

**Q5 — criteria at creation is the thing ORGANIZATION §6 argues against.** The author is
overriding a documented argument, which is their call, but the specific form matters. §6's
case is that a bar at creation makes an agent with no context park the thing in the nearest
folder that will accept it, and a bespoke function hidden in an unrelated module is the
expensive failure. Criteria at creation reproduces that. A *check* does not, if it sits
later:

The computable signals already exist and are already scheduled. ORGANIZATION §3.3 names two —
members with no importers in common, and a member whose only caller is one specific call site
— and PLAN Phase 0 lands both as warnings from the import graph. Turning one of them into a
gate on the folder's *subsequent* behaviour rather than on its proposal gives the author the
check they asked for without the bar: a folder that has not acquired a second importer within
N commits is defended or dissolved. Creation stays free, §3.2's dissolve remedy gains the
trigger it currently lacks, and the enforcement is mechanical rather than argued.

The author's instinct — *"stating it as a free option will make it into a target"* — is
correct and is not addressed by ORGANIZATION §6, which relies on §3 being applied and
provides no moment at which anyone must apply it.

**Q8 — an invalid graph and an unpaid debt are different kinds of thing.** The mechanism the
author names is right for both: state the failure clearly, do not block, let the user select
any end state. But a debt is repo-level, outlives sessions, and is paid by a commit. An
invalid intermediate graph is per-edit, resolves in seconds, and is "paid" by the next
keystroke. Routing the second through the first fills the register with transient user edits
and destroys its value as the work list.

What they share is the *reporting contract* — "here is what is unreached and why" — and that
is one mechanism with two lifetimes. Naming it once and instantiating it twice is the
version that survives. The author's substantive requirement is preserved either way: *"the
capability just needs to be there so that the entire thing doesn't have to be retooled for
that eventuality."*

**Q3b, left open — the cheaper mechanism the author suspected exists.** The concern is
correct: a key on every `Frame` is a per-object cost on the most-copied object in the system,
and §6 of this file was right to flag it as not free but wrong to present it as the only
shape.

Identity does not need to be per-frame. It needs to be per-*feed*: a viewport shows one
source at a time, and the thing that changes invisibly is which feed is filling it — v2's
`_display_from_ring` versus `_display_cached`. Put the key on the subscription and it is
O(1) per view rather than O(1) per frame.

The complication is out-of-order delivery, which is real: a frame from the previous feed can
arrive after the switch and paint under the wrong identity. But v2 already solved that and
paid for it — `gui/coalescer.py` carries a `generation` counter marking superseded results
stale, plus sequence numbers preventing an out-of-order frame from painting. So the shape is:
a frame carries a small opaque token (an integer, which v2 already pays for), the token
resolves to a key through a side table the engine owns, and a view reports the key it
resolves rather than one it was handed. Same guarantee, no per-frame key, and it reuses a
mechanism FINDINGS 17 already recommends carrying forward.

## 7.6 Q6 — the reframing, and a correction to this file

The author declined the binary and named a third data point that neither PLAN nor this file
had:

> "There are things that v1 does better than v2, and v1 is frozen currently, but the things
> it does better somehow didn't make it into v2. I'm not sure how to fix that."

That changes the question. It is not frozen-versus-deleted. **Freezing has already been tried
once and did not transfer the good properties**, and PLAN's framing — that freezing preserves
the option to port — is a claim with one observation against it and none for it. The real
question is what mechanism moves a known-good property across a rewrite boundary, and the
answer "keep the old tree readable" is the one that has been falsified.

What moves across a rewrite boundary is a **check**, not code. `tests/conftest.py`'s synthetic
video moves: it makes frame *n* a solid field of intensity `n * 5` so a test can assert which
frame a seek landed on, and any implementation that fails it fails visibly. A module does not
move; it sits in a frozen tree being cited.

That is a direct problem with FINDINGS' *Mechanisms worth carrying forward* section, which is
a list of five **modules** — `bench/sweep.py`, `gui/resource_probe.py`,
`bench/retention_trace.py`, `tests/conftest.py`, `cli/app.py`. Four of the five are in the
form that failed v1→v2. The transferable version of each is a behaviour with a test that
fails in v3 until the behaviour exists: a factorial sweep must derive core sets per CPU
efficiency class; a resource probe must close the loop between declared budget and measured
use; a cache must be able to record its own access trace so an eviction policy is chosen from
behaviour rather than argued. Written that way they are Phase 0 test stubs, and they cannot
be silently skipped.

**And a correction to this file.** The author's other observation is accurate and applies
here:

> "every time you look directly at v2 you praise it and then try to follow its problems,
> sometimes in ways that aren't clear to me."

§3 of this file reports 41 citations as "held exactly," which is a statement about the
accuracy of FINDINGS as a record and says nothing about whether any cited mechanism is worth
keeping — but reads as endorsement, because verification and approval use the same vocabulary.
§4's Q6 recommendation compounds it: it argued for freezing partly on the grounds that
FINDINGS' citations point into the tree. That is an argument for preserving *evidence*, and
the evidence is FINDINGS itself, which is a document and survives deletion of the code. The
recommendation does not follow from the reason given, and with the v1 observation added it
inverts: freezing has one failure on the record, and the citations do not need the tree.

The unknown that blocks the rest of this: **what v1 did better is not written down anywhere.**
FINDINGS is the v2 record; there is no v1 equivalent, and the properties that failed to
propagate are exactly the ones nobody wrote as checks. That list is worth an hour, and it is
the only input in either round that cannot be reconstructed from the repository.

---

# 8. SECOND PASS

The author's response to 7.5 corrects one thing in this file's own method, resolves Q8 in a
way that upgrades a claim §6 filed as unusable, and names a gap in ARCHITECTURE that has no
current expression. In order of how much they change.

## 8.1 The durability test is biased against the repo, and the bias is mine

The author's Q4 note:

> "just as important is the discipline that makes SIEVE's repo intuitive, easy to work in,
> clean, performant code where the targeted improvements have clear homes. That is pretty
> lacking in the principles in general."

Correct, and this file is a contributor rather than an observer of it. §2's Part E demotes
most of ORGANIZATION — E12 (naming) to a linter, E14 (bin signals) to a mechanism — and says
outright that "a principles document that carries all thirty numbered items will be mostly
folder advice." The demotions all come from clause 3, cost asymmetry, and clause 3 as written
is measured **per instance**. Renaming one folder is free forever, so naming demotes. Moving
one helper is free forever, so homing demotes. Every repo claim fails a per-instance
asymmetry test, and every contract claim passes it, so the test produces a runtime-only
document by construction.

That is wrong on its own evidence. The failures FINDINGS records are not individually
expensive; they are individually trivial and unbounded in aggregate. `gui/filter_tab.py` is
1,629 lines and 154 distinct owned attributes, and no single one of those attributes was
expensive to add. Four thread owners, three caches, two validators, one hand-written catalog
— each cheap, each locally defensible, and together the reason v2 is being replaced.

**Corrected clause 3.** *State what adopting the claim costs now versus what adopting it
costs after the system is built, measured over the accumulated class of instances rather than
over one instance. If a claim is cheap to fix once and there is no bound on how many times it
will need fixing, the aggregate ratio is what counts.*

What this changes in §2's Part E:

- **E12** (names state a capability; `core`, `backend`, `common`, `utils`, `helpers` do not)
  is **durable**, not convention. One rename is free; a decade of accumulation into a folder
  named `core` is not, and `src/sieve/core/` currently holds `detection`, `filter_base`,
  `filter_registry`, `machine`, `pipeline_model`, `pool_meter`, `replicates`, `shares`,
  `types`, and `wavelet` — a wavelet transform and a CPU-topology reader in one folder,
  which is §1.4's two-modules-wearing-one-name with the exact name §2.1 warns about.
- **E14** (the two computable bin signals) is **durable as a class**: automated detection of
  accumulation is the only thing that makes the aggregate bounded. The specific signals are
  contingent; having some is not.
- **E4** (`__init__.py` surfaces) keeps its Python contingency but rises in weight, since the
  surface is the per-instance cost that prevents the aggregate.

## 8.2 The repo half, stated

This file asked for principles that survive; it did not ask what the repo half of them is.
Filling that in, since the author names it as the gap. Four claims the corpus does not make
anywhere, each derived from something it does say about the product.

**R1 — The aggregate is the unit.** A rule whose violations are individually cheap and
unbounded in count is enforced automatically or not at all. This is the corrected clause 3
turned into a rule, and it is what makes ORGANIZATION §3.3's warnings inadequate as written —
PLAN Phase 0 lands them as warnings that nobody must act on, which bounds nothing.

**R2 — An optimization is a new operator version with identical declared semantics and a
different cost shape.** The author asks for "clean, performant code where the targeted
improvements have clear homes," and ORGANIZATION has no home for an optimization at all:
§1's test asks what change is confined to a folder, and "make this faster" is confined to
none. The answer is already built out of runtime machinery and nobody connects it. Keys make
the swap safe (two versions, same declared semantics, comparable byte-for-byte under §1.5's
class), the cost shape makes the improvement measurable (§2.3), the determinism class makes
"same answer" precise, and FINDINGS 19's declared migration is what lets the slow version
actually be deleted rather than retained forever. Stated as one claim, the repo gets a home
for performance work and a definition of when it is finished. This is the strongest single
instance of the mirror in 8.3.

**R3 — The precursor index is executable.** ORGANIZATION §7.1 already requires a reference
member per kind of thing, in tree and in CI. What it does not say is what that set *is*: it is
the repo's answer to "what can satisfy this requirement," and it is checkable precisely
because the members are executed rather than described. §7 currently justifies reference
members as anti-reinvention. Their larger job is 8.3.

**R4 — A change's cost is knowable before it is made.** SIEVE's entire justification is
telling a user how long a pipeline will take before they run it (CHARTER 63). Nothing tells a
developer or an agent what a change will cost before they make it, and the corpus does not
notice the asymmetry. Marked speculative: the import graph plus the check list is a partial
answer, and it may be that the honest version of this is much weaker than its product-side
twin. Included because the author's framing predicts it should exist, and if it does not, that
is a place the mirror genuinely breaks and is worth knowing.

## 8.3 The mirror thesis is checkable, and §6 of this file was wrong to file it as an epigraph

The author's Q8 answer:

> "what to do next is clear — for SIEVE's users, AND for any agents working in SIEVE, and how
> to get from having a desired target and filling in all the requirements to get to that
> target should be obvious and self-announcing. SIEVE can do that by categorical options for
> what can fulfill the precursors for the desired target. SIEVE's repo needs to be able to do
> that by making sure how the contracts are written aren't arbitrary... how we work in SIEVE's
> repo is almost move for move the same as SIEVE itself."

Both scratch derivations rejected CHARTER line 69's mirror thesis as uncheckable.
`charter-invariants.md` files it under *Explicitly not invariants*; `charter-invariants2.md`
calls it "a design aesthetic" that "names no loss." §6 of this file agreed and recommended
carrying it verbatim as an epigraph, on the argument that the danger of uncheckable rules
applies to rules and not to stated intent.

That was the wrong call, and this answer supplies the operational form all three passes
missed. The mirror is not an aesthetic. It is the claim that one mechanism serves both sides:

**Given a desired target, the set of things that can satisfy its precursors is enumerable, and
each candidate is announced with what it in turn requires.**

Backward chaining over a declared precursor relation. On the product side that is
type-directed search: the user wants output artifact T, the engine enumerates operators whose
declared `emits` admits T, recurses on their declared inputs, terminates at sources. v2 has
the parts already — `ArraySpec.admits` and `ElementKind` propagation at `pipeline/dag.py:201`
and `:215` — and never ran them backwards; `gui/wizard_model.py:84` hand-wrote the catalog
instead, which is FINDINGS 15. On the repo side it is the same query over the reference
members of R3: an agent needs capability C, and the enumerable candidates are the reference
members demonstrating a contract that admits C.

**Prior art, named so it can be rejected.** The product side is type-directed program
synthesis, and the repo side is Hoogle — searching a library by type signature rather than by
name. Neither is novel and both work, which is a point in the claim's favour rather than
against it: the mirror is asserting that the repo should be searchable the way the pipeline
is, and there is a working precedent for each half independently.

**Where the mirror is weaker than it looks, and this should not be smoothed over.** The two
sides are not equally checkable. The product-side precursor relation is a type relation and is
mechanical. The repo-side relation, if it runs over `__init__.py` purpose lines, is prose, and
prose does not have an `admits`. That is exactly why ORGANIZATION §8 can only promise a
generated guide and then concede it is "a diagnostic, not a document to be improved directly."
The repo side becomes mechanical only if the precursor index is the **reference members**
rather than the purpose lines, because those are executed. So the mirror holds, and holding it
costs ORGANIZATION §7 being load-bearing rather than advisory — which is a real commitment,
since §7.2's hard-shape set now has to be complete rather than illustrative.

**Q8 resolves accordingly, and 7.5's objection is withdrawn.** An invalid graph is a target
with unsatisfied precursors. A debt is a capability with unsatisfied precursors. They are one
query with two lifetimes, and 7.5 was right that the lifetimes differ and wrong that this made
them different mechanisms. The query is the mechanism; the two registers are two
materializations of it, which is ARCHITECTURE §5's "everything else is a view over it" applied
one level up.

## 8.4 The debt register is generated, not written

This falls out of 8.3 and answers the failure mode the author names:

> "it carries a hidden cost in that the way debt comes due can just as easily be a large list
> that grows forever as it can be a thousand little files that can drift into oblivion and be
> as long as whatever 'correctness-shaped' the agent determines at time of writing."

Both failures are the failure of a **hand-maintained** register, and they are FINDINGS 15
exactly — `wizard_model.py:84`'s hand-written catalog, with `tests/unit/test_chain_model.py:173`
pinning it against itself so drift passes. FINDINGS principle 4 already forbids it: anything a
human maintains in parallel with a declaration will drift.

A debt is not a file. It is the difference between declared capability and reachable
capability, which is the backward-chaining query of 8.3 run over the declaration set and
returning the empty results. An unbounded list cannot grow because it is computed; a thousand
drifting files cannot drift because there are none; and "correctness-shaped as the agent
determines at time of writing" cannot happen because no agent writes an entry. The only
hand-written part is the prose reason, which is what `bench/budgets.py:133` `IN_DEBT` already
does for accepted performance misses and is the one part that must be authored.

This also supersedes 7.5's dependency-versus-phase repair. That repair was correct against a
written register and is unnecessary against a generated one: the dependency is not recorded,
it is the query's own recursion, and the debt comes due when the query stops returning empty.

## 8.5 Q5, decided

The author deferred this to be decided against the repo goals now stated. Decided as the
later check, not creation criteria, and 8.1 strengthens rather than weakens the case.

Creation criteria make the repo *less* navigable, not more: §6's argument is that a bar at
creation causes a context-free agent to park the thing in the nearest folder that will accept
it, and a hidden bespoke function is the expensive failure. That is a direct cost to "targeted
improvements have clear homes." The author's concern — that stating it as free makes it a
target — is real and §6 does not address it, because §6 relies on §3.2 being applied and names
no moment at which anyone must apply it.

**The check sits on the folder's subsequent behaviour.** A folder that has not acquired a
second importer within N commits is defended or dissolved. Creation stays free, §3.2 gains the
trigger it lacks, the signal is already computable and already scheduled in PLAN Phase 0, and
by R1 it is a rule enforced automatically rather than by intention. N is a policy number and
is the author's to set; it is not a principle.

## 8.6 A contract must name the contracts it is only valid under

The author's Q3b answer moves the question off the mechanism, correctly, and then names
something ARCHITECTURE cannot currently express:

> "if streaming is part of the criteria and you want to change how the streaming coupling
> works, now you have to change at least two things. This is why principles feeds architecture;
> to avoid that as a potentially massive rewrite problem."

This is the real content of Q3b and it generalizes past frame identity. The identity mechanism
is only *necessary in its complicated form* because delivery is out-of-order: with strictly
ordered per-feed delivery, identity is a property of the subscription and costs nothing;
with out-of-order delivery it needs a per-frame token resolved through a side table. So
identity's contract has a silent dependency on the delivery discipline, and changing delivery
changes identity even though neither imports the other.

ARCHITECTURE has no notion of this. §§1, 3, 5 are presented as independent sections, and
several of them are not: §5.4's staleness-as-display-state is *required* by §3.4's shedding
and would be optional without it; §1.5's materialize-tolerant-artifacts-once is *required* by
§2.2's engine-owned placement and meaningless without it; §1.6's start-offset-in-key is
*required* by §3.5's checkpointing. ORGANIZATION §5 levelizes **imports**, which is Lakos's
physical design, and two contracts can have zero import dependency and total semantic
dependency — which is precisely the pair that produces a two-thing rewrite nobody predicted.

**The claim:** a contract declares the other contracts whose form it depends on, so that
changing one names the set that must change with it. Bearer is *contract*, which is permanent.
Negation is describable and common — it is what every architecture document that lists
independent sections is implicitly asserting. Aggregate cost asymmetry is large, because the
dependencies are individually obvious to whoever wrote them and collectively unrecoverable
afterwards.

This is also the sharpest available answer to what "principles feeds architecture" means
operationally. ARCHITECTURE's sections are the *nodes*; the principles document supplies the
*edges*, and an edge that is not written down is a rewrite waiting to be discovered. Worth
considering as the principles document's organizing structure rather than as one more numbered
claim inside it.

---

# 9. ADHERENCE

The author, closing:

> "everything that *can* automatically be enforced should be automatically be enforced, with
> some kind of mechanism to ensure the loop isn't 'agent writes the thing on the todo based on
> some surfacing mechanism, there's a check that says they did it wrong, and then they go
> rewrite it'... principle adherence needs to be elegant and effortless or it's a suggestion
> that gets ignored in the first lapse in context."

And: the coupled-contract graph of 8.6 is the document's organizing structure.

## 9.1 The two requirements pull against each other, and the resolution is a ladder

"Automate everything automatable" and "do not make me rewrite" are in tension, because the
cheapest automation is a CI check and a CI check is precisely the write-fail-rewrite loop.
The tension resolves by noting that automation has rungs, and that a check is the lowest one
that still counts rather than the goal.

| Rung | Mechanism | When the cost is paid | Example in this corpus |
|---|---|---|---|
| 1 | **Unrepresentable.** The wrong thing cannot be written. | Never | `core/filter_base.py:199-211` refuses to register an array-emitting filter that declares no element meaning. ARCH §1.2, admission at registration. |
| 2 | **Generated.** The thing is not written at all; it derives from a declaration. | Never | ARCH §6.1's controls, ORG §8's module guide, 8.4's debt register. |
| 3 | **Default path.** The easy way is the correct way; the wrong way costs extra. | At authoring, negative | ORG §7.1's reference members — copy the one that already passes. |
| 4 | **Checked after.** CI fails and the work is redone. | After the work | ORG §4.4, §5.3; PLAN Phase 0. |

**A rung-4 check is a placeholder for a rung-1/2/3 mechanism that has not been built.** That
is the reading of "automate everything automatable" that does not produce the loop the author
is rejecting: automate at the highest available rung, and record the rung so a rule sitting at
4 is visibly unfinished rather than visibly enforced.

## 9.2 The operative form of the corollary

The phrase that does the work is *"the first lapse in context."* The population is agents, and
an agent that has lost context will not recall a rule; it will do whatever the tooling makes
easy. So the requirement is stronger than "easy":

**A principle whose adherence requires knowing the principle has already failed.**

Rungs 1 and 2 satisfy this outright — the rule does not need to be known, because the wrong
program does not exist or the artifact is not authored. Rung 3 mostly satisfies it, since
copying the nearest working example is what a context-free agent does anyway, which is exactly
why ORGANIZATION §7.1 puts the reference member in the tree rather than in prose. Rung 4 does
not satisfy it at all: it requires the rule to be known *after* the fact, which is the loop.

**Judgment is a budget, not a fallback.** The template permits `none — reviewer judgment` and
calls it a known debt. Under the corollary that is too permissive: if every rule may fall back
to judgment, every rule will. Some genuinely cannot be mechanized — ORGANIZATION §1's "name
the change that would be confined to this folder" is irreducibly a reading — and those should
be enumerated up front as a fixed, small set that the document declares, rather than being
where rules land when nobody built the mechanism.

## 9.3 Prior art

Named so it can be argued with. **Poka-yoke** (Shingo) is the manufacturing form: design the
fixture so the part cannot be installed backwards, rather than training the operator.
**Bloch's API maxim** — easy to use correctly, hard to use incorrectly — is rung 1 and rung 3
stated together. **Lampson** again, "make it hard to use wrong." And **correct by
construction**, which CHARTER already asserts at line 59 (*"if it reaches the actual DAG, it
meets the requirements by construction"*) and which `charter-invariants.md` correctly
identifies as the load-bearing word: *"not 'is validated on the way in' but 'cannot be built
wrong.'"*

Worth resolving a tension this file recorded earlier: `charter-invariant-misses.md` rejects the
strongest reading of Closure, on the grounds that FINDINGS 16's interactive authoring means the
spec is invalid much of the time it is being edited. That objection is about **user states**
and does not touch the repo half. An invalid intermediate graph is a legal user state; a
misfactored operator is not a legal repo state. "Cannot be built wrong" is the wrong rule for
the first and the right rule for the second, and the misses file's rejection should not be
carried across the mirror.

## 9.4 Where the corpus's rules currently sit, and where they could

The useful output of the ladder is that several rules the corpus files at rung 4 have a
cheaper rung available.

- **ARCH §2.2** (an operator never chooses a thread or reads a capability probe) has no
  enforcement point today — the misses file says so, and v2 disproves the naive check, since it
  had four interface threads and still froze. Rung 4 is a registration-time reflection check.
  Rungs 1 and 3 together are cheaper and stronger: the operator's call signature receives
  nothing it could probe with, and the import-direction check of ORG §5.3 forbids an operator
  module from importing `core/machine.py`. The rule then needs no knowing.
- **ORG §4.4** (purpose line and export list per package) is specified at rung 4 — CI fails on
  a package that states no secret. ORGANIZATION §6.3 already wants it at rung 2 (*"a proposed
  folder states its secret in `__init__.py` at creation"*) and supplies no mechanism. Scaffolding
  folder creation so the file cannot exist without the line moves it to rung 2 and deletes the
  check.
- **ARCH §5.5** (no result-determining state outside the log) is the hardest and the most
  valuable to move, since it is the rule v2 broke worst. Rung 4 cannot see it — 154 owned
  attributes on one tab are individually legal. Rung 1 is a widget that binds to the log and
  has no independent setter, which is what PLAN Phase 8's check is reaching for when it says
  no parameter *state* lives in a widget.
- **ARCH §8.4** is already at rung 1 in the tree, and is the model. Note what its error message
  does: it refuses *and hands over the fix* — pass `ElementKind` if this filter decides what a
  value is, `ElementRelation` if it inherits, and there is no default on purpose. A rung-1
  refusal that teaches the alternative costs an agent nothing; one that only says no costs it a
  search. That distinction is worth stating as part of the corollary.

**The reference member is doing three jobs, which is why it should be treated as load-bearing
rather than advisory.** It is ORGANIZATION §7's anti-reinvention mechanism, R3's precursor
index, and rung 3 of this ladder. One artifact serving three claims across both halves of the
mirror is the strongest structural evidence in the corpus that §7.2's completeness requirement
is not optional.

## 9.5 Consequence for the template

`CONSTITUTION/_TEMPLATE.md` was written before 8.6 and 9.1. Each rule currently carries
**Rule / Rationale / Example / Check / Latitude**, and each invariant file carries
**Holds / Breaks if violated / Guarded by / Scope**. Three fields are missing and one is
mis-shaped:

- **Bearer** — the noun the claim constrains, per §1's clause 2. Without it a rule carries no
  expiry condition and contingent claims read as permanent, which §2 shows is the corpus's
  actual failure mode rather than a hypothetical one.
- **Depends on** — the edges of 8.6. This is what makes the document a graph rather than a
  list, and it is the field that prevents the two-thing rewrite.
- **Rung** — 1 through 4, per 9.1. A rule at rung 4 is visibly unfinished.
- **Check** and **Guarded by** collapse into rung plus mechanism. Keeping them separate invites
  the aspirational-check failure the template already warns against, because a field named
  *Check* asks to be filled with a check rather than with the truth about how the rule is held.

Ordering rules "by how often an agent will hit them" (the template's convention note) is right
and gains a second criterion under 9.2: within that, rung 4 rules first, because those are the
ones an agent must actually know.
