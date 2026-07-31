# Charter invariants — derivation

Scope of this pass: name the invariants the charter actually asserts, state each as a
property of the running system, and name the loss when it breaks. Rules are not
written here. IDs are permanent once minted, so this file mints none — the obligations
listed under each invariant are the drafting queue for the real files, not rules.

Derivation rule used: an invariant is a property of SIEVE that, if it stops holding,
takes away something the *user* can no longer do. Anything whose loss is "the codebase
gets harder to work in" is a means, not an invariant, and is routed to crosscutting.
By that test the charter asserts exactly three, and they are the three it says it
asserts in §Seventh. Sections one through six are the means.

`Guarded by` is `none — reviewer judgment` throughout because this pass read only the
charter. Every one of those is a real hole to fill against the tree, not a considered
verdict that no guard exists.

---

# INV-1 — Pipeline

**Holds:** Every pipeline is a DAG whose nodes were admitted by contract rather than by
convention — each declares what it consumes, what it produces, and what it costs — so
any pipeline that has run can be written down, read back, and run again to the same
result.

**Breaks if violated:** A node that enters the DAG without declaring its contract cannot
be scheduled by the executor, cannot be priced by the cost model, and cannot be
round-tripped by save/load. The user tunes a pipeline they cannot hand to anyone else,
and every new filter is a bespoke integration rather than an instance of a known kind
(charter, programming limitation 1; fragility 1).

**Guarded by:** none — reviewer judgment.

**Scope:** provisional — the pipeline core and node registry (`src/sieve/core/**`), plus
whatever admits a node to the DAG and whatever serializes a pipeline. Needs pinning
against the tree.

**Surface this governs,** mapped from charter §Seventh.1:

- (a) execution — the DAG runs from an input and produces outputs that can be reingested.
- (b) persistence — a pipeline is a durable artifact, not a session's worth of hand-tuning.
- (c) admission — "filter" is too narrow a word; the contract is on *any* section of a
  pipeline, and it is met by construction, not checked after the fact.
- (d) tuning — the load→measure→tune→load loop. Contested ownership, see *Boundaries*.
- (e) outputs — the shape of an output determines what can consume it downstream.

**Obligations to draft as rules:**

- A node declares inputs, outputs, and cost before it can be registered.
- Registration is the only path into the DAG; there is no direct construction path.
- Save/load round-trips to an identical graph, and this is tested per node kind, not
  once for a sample pipeline.
- The output contract is a declared type, not the ad-hoc shape a particular consumer
  happens to accept.

**Open, from the charter's own admission:**

- (e) says outputs are "basically afterthoughts" and that video-as-required-input is "a
  known limitation." So the invariant must be stated over *sources*, not over video —
  the moment a rule says "the input video," background subtraction as a pipe section is
  excluded by wording. Nothing above assumes video; keep it that way when drafting.
- "Something that doesn't enable something for the pipeline is outside the scope of
  SIEVE" is a scope boundary, and it is the sharpest exclusion in the charter. It reads
  as a rule under this invariant rather than as its own invariant, but it is the only
  claim in the document that can *reject* work, so it deserves a rule of its own.

---

# INV-2 — Measurement

**Holds:** Every unit of work has a measured cost on the machine it is actually running
on, and that cost is available before the user commits to the work.

**Breaks if violated:** SIEVE cannot answer "will this run on my laptop, and how long
will it take." That question is the whole differentiator — the charter is explicit that
without it there are other tools that do the same image processing. Losing it means
feasibility is guessed rather than estimated, load cannot be balanced against anything
real (charter, fragility 2), and a performance regression is invisible until the GUI
stutters on someone else's hardware (charter, programming limitation 2).

**Guarded by:** none — reviewer judgment.

**Scope:** provisional — every node, plus the benchmark harness (`tests/bench/**`) and
whatever surfaces an estimate to the GUI. Effectively universal; the charter calls it
"the universal tool that every single part of SIEVE touches," which means scope here is
"everything that does work," not a directory.

**Obligations to draft as rules:**

- No node without a cost measurement; adding one without it fails a gate.
- Cost is measured per-machine, not inherited from the dev machine. A number carried
  over from the author's hardware is worse than no number, because it is trusted.
- A change that regresses cost is reported at the change, not discovered by a user.
- An estimate shown to the user carries its provenance — measured here, extrapolated
  from elsewhere, or unknown.

**Seam worth naming before drafting:** the charter loads two different mechanisms into
this one section. Prediction ("how long will this take on your machine") and
backpressure ("SIEVE must not freeze when something runs rampant") share a
measurement substrate but are different obligations — one is an estimate surfaced
before execution, the other is a scheduler responding during it. They belong under the
same invariant, since both die if measurement dies, but they will not share rules and
should not share a check. Do not let the backpressure rules hide inside the estimation
ones.

---

# INV-3 — Visibility

**Holds:** Every pipeline capability is either reachable by the user from the GUI, or is
marked in the tree as not yet reachable.

**Breaks if violated:** Capability that exists only in code is capability the user does
not have — the charter's "usefulness is exactly equal to the user's knowledge of the
tool." Worse, the codebase loses the ability to say what is finished: an unannounced
backend feature is indistinguishable from an absent one, so the work left is invisible
to whoever picks it up next, including an agent.

**Guarded by:** none — reviewer judgment.

**Scope:** provisional — `src/sieve/gui/**` and the node registry, since the marker has
to live with the capability and the check has to compare the two sets.

**Obligations to draft as rules:**

- A registered pipeline capability with no GUI surface carries an explicit
  not-yet-exposed marker; the absence of both is the failure.
- The marker is machine-readable, so "what is unfinished" is a query rather than a
  reading of the diff.
- A marker is removed by the change that closes the loop, in the same commit.

**Note on the phrasing.** The charter says this "should not be defined from the outset,
but must be detectable until the loop is closed." Taken literally that forbids the
obvious invariant ("everything is in the GUI") and asks for something else: not parity,
but *disclosure*. The statement above is written to that reading, which has the useful
side effect of being checkable — you can test that the marked set and the exposed set
cover the registered set. "All functionality must be in the GUI" is not checkable and
would block landing a backend before its UI, which the charter clearly does not want.

---

# Boundaries between the three

The three invariants are not disjoint, and the one place they collide is charter
§Seventh.1(d), the load→measure→tune→load loop. Tuning is filed under the pipeline
invariant, the thing being tuned against is measurement, and the surface it happens on
is the GUI. The charter names the consequence in the same breath — "which is why the
filter tab is a god object right now." That object is the intersection, and it grew
unbounded because nothing said which invariant owns it.

Proposed split, to be settled before rules are written: INV-1 owns the graph and its
mutation (what a tuning action does to the pipeline), INV-2 owns the numbers the tuning
decision is made against and the cost of producing them, INV-3 owns what the user is
shown and when. The tuning loop is then a composition of three governed pieces rather
than a fourth invariant.

**Considered and rejected as a fourth invariant:** the tuning loop itself. Its loss is
fully decomposed into the three above — a broken loop is a broken graph mutation, a
missing measurement, or a hidden control. An invariant that is the conjunction of three
others adds no rule that could not be filed under one of them, and gives every future
rule an ambiguous home.

---

# What the charter contains that is not an invariant

Sections one through six are the shape of the solutions, and the charter says so. Each
fails the loss test the same way: the user loses nothing directly when it breaks, they
lose it later through one of the three. They route to crosscutting.

- **One, self-announcing toolbags.** Organization. Loss is agent and human search cost.
- **Two, contracts.** The charter's own §2.5 — the GUI/CLI is a contract with the user —
  is already covered by INV-3, and the code-level half is the mechanism of INV-1 rather
  than a separate claim.
- **Three, orchestration and routing.** How contracts rely on each other. Real, but it
  is architecture serving INV-1 and INV-2, not a property the user can lose on its own.
- **Four, discoverability via `__init__`.** Anti-reinvention. Same loss as one.
- **Five, runbooks and golden fixtures.** Explicitly framed as "show how, don't forbid."
  Guidance, not invariant, and the charter is emphatic that it must not become
  bureaucracy.
- **Six, durable tests.** This one is not a peer of the others and should not be filed as
  if it were. It is the enforcement substrate — it is what makes any `Guarded by` line
  above possible to fill in. Filing it as another crosscutting concern loses that. It
  wants its own treatment: a standing requirement on how the three invariants are
  guarded, i.e. that a guard survives refactoring of the thing it guards.

The summary section ("codebase and SIEVE mirror each other") is a design aesthetic. It
names no loss and should not be turned into a rule; it is the reason the other things
are true, not a thing to check.
