# Working backwards from the aspirations

> **Dated record of a derivation (2026.07.28).** This is the reasoning that
> produced `docs/ASPIRATIONS.md`, kept separately so the conclusions there can
> be short. It is a record, not a maintained document — supersede it with a
> second dated derivation rather than editing it. If a step here turns out to be
> wrong, the interesting artifact is *which* step, which is why the candidate
> paths are written out in full rather than summarized to their winner.

## The method, and why this one

Forward planning from where the code is produces the next commit, which the
`docs/todo/` tree already does well. It does not produce the *ordering* of a
five-year capability, because each forward step is chosen against local
evidence and the long view loses every argument to the near one. That is
observably what happened here: benchmarking has been sidelined by inference
across many sessions, not by decision.

So this document runs backwards. For each aspiration:

1. Write **3–4 independent candidate paths** that each end in the aspiration
   being met. Not four sequential steps — four *different histories*, each of
   which would count as success.
2. Take the **final step** of each path — the last thing that had to happen.
3. Ask what is **common** across those final steps, and whether the generalized
   form is **invariant** — true of every path, not merely of most.
4. Step back again: what must have existed across *all* paths for any of those
   final steps to be takeable?

The output of interest is the invariant, not the paths. An invariant is
path-independent, which means building it pays off regardless of which future
actually happens — it is the option-value argument, and it is the only kind of
long-view claim that survives contact with a repo that reprioritizes weekly.

A step is only accepted as invariant if I can state what would falsify it. Where
I could not, the section says so.

---

# A1 — a laggy session decomposes from its log

**Aspiration.** Usage logs carry enough that a session's wall clock can be
decomposed into its contributing parts after the fact, on command, by someone
who was not present — and the metrics that describe how parts interact are
*derived from* the log rather than decided before it was written.

## Candidate paths to A1

**Path 1 — the span tree.** Spans nest and carry parent links, so an interval
decomposes into a tree by construction. *Final step:* the unattributed residual
becomes an explicit node in the tree rather than the difference between two
numbers, and it is small enough to be uninteresting.

**Path 2 — contention accounting.** Decomposition is not by call structure but
by *what was waited on*: each span records which declared consumer held the
resource it wanted and how deep that queue was. Lag decomposes into shares of
contention. *Final step:* every span stamps the occupancy of the resource it
contended for at the moment it ran.

**Path 3 — replay.** The log records inputs, not durations: gestures, parameter
commits, seeks, plus the environment. Decomposition is done by re-running the
session headlessly under a profiler. *Final step:* a session log that replays to
the same work.

**Path 4 — offline query.** The log is append-only, richly dimensioned samples;
"why was it laggy" is a query — slice, group, roll up — rather than a report
fixed at write time. *Final step:* an aggregation surface over a durable sample
store.

## What is common at the final step

Paths 1, 2 and 4 obviously want richer samples, so the interesting test is path
3, which does not: replay shifts the burden from sample richness onto
*determinism plus input completeness*. It is the path that could falsify a
"log everything" invariant, and it is worth noting that replay is unusually
cheap in SIEVE specifically — rules 1 and 2 mean the work is fully described by
a serializable artifact through a single execution path, which is exactly the
precondition replay needs and which most applications lack.

What survives all four is narrower and sharper than "log more":

> **Every sample must be joinable to the thing that produced it.**

Path 1's tree is meaningless if a child cannot be tied to a parent's work. Path
2 cannot attribute contention to a filter without knowing which node was in
flight. Path 3's replay must be checkable against the original, which requires
a common key. Path 4's slices are exactly the join dimensions. In every case the
requirement is a *join key*, not a volume of data.

And SIEVE already computes the right join key. The cache key
(`pipeline/cache_key.py`) is a content address for a unit of work — it folds
source identity, decoder identity, replicate ROI, filter id and semver, resolved
params, and ancestry. Two samples with the same node key describe the *same
computation*, which is what makes them comparable across sessions, across
machines, and across code revisions. Nothing else in the system has that
property.

**The invariant at A1−1:** *a sample carries the identity of the work that
produced it, and that identity is the cache key.*

**Falsifier.** If the load-bearing question turns out to be about work the cache
key cannot name — GUI event handling, Qt paint, decode of an uncached seek —
then the key is the wrong join and the invariant is a spine, not a rule. This is
partially true today and the honest form is that the key covers pipeline work
and something else must cover interaction work; see the residual discussion at
A1−2.

## Stepping back: A1−2

For a sample to carry an identity, two things must exist that do not:

- **`Sample` must be dimensioned.** It is `(Budget, elapsed_ms)` today, with
  derived `over_ms` and `within_budget`. It has no timestamp, no key beyond the
  budget's own, and no room for one. Every question above needs at minimum:
  when, which node key, which mode, which resolved allocation.
- **Something must write it down.** `Recorder` is an in-memory dict that dies
  with the process, and the process dying is the single most likely
  circumstance under which somebody wants the log. The only thing in the tree
  that appends to disk during a session is `bench/retention_trace.py`, which is
  off by default, scoped to ring access, and has no clock.

So A1−2 is: **a dimensioned sample and a durable sink that survives a kill.**
That is `docs/todo/ledger-producers.md` plus the persistence half of
`docs/todo/slow-path-surfacing.md`, which is where the backward chain lands on
work the repo already has open — the first evidence that this derivation is not
fantasy.

---

# A2 — robust self-balancing on unknown hardware

**Aspiration.** On hardware SIEVE has never seen, running a filter chain SIEVE
has never seen, the division of the machine is chosen from in-app measurement
rather than from constants, it is at least as good as the best fixed split, and
SIEVE can say why it chose it. Robust in the dynamic-systems sense: it does not
oscillate, and it degrades gracefully when its model of the machine is wrong.

## Candidate paths to A2

**Path 1 — plant identification.** Fit a cost model per kernel online
(throughput against resolution, workers, block size), then solve allocation as a
constrained program against the identified plant. *Final step:* the solver, over
a model whose fit error is known.

**Path 2 — model-free feedback.** No model. Observe pool utilization and queue
depth, move the split by a law with a proven stability margin, deadband, and
anti-windup. *Final step:* the control law, plus the argument that it cannot
oscillate under the observed disturbance spectrum.

**Path 3 — in-app experiments.** Allocation candidates are arms. The program
runs cheap randomized trials during naturally repeated work and selects by
best-arm identification under a safety constraint. *Final step:* an experiment
scheduler that can perturb allocation without hurting the user, and attribute
the outcome.

**Path 4 — fingerprint and lookup.** Classify the machine, look the split up in
a profile corpus accumulated across installs and calibration runs. *Final step:*
the classifier, plus a corpus with enough coverage that an unseen machine lands
near a seen one.

## What is common at the final step

Every one of these fails identically if the same thing is missing. Path 1 cannot
fit a model without clean paired observations. Path 2 chases noise — this is not
speculative, it is `docs/todo/budget-checks-under-ambient-load.md` already
happening at the CI gate, where a 100 ms budget failed by 1.7 ms because of
ambient load and passed on rerun. Path 3 *is* this requirement. Path 4 cannot
build a corpus entry without it.

> **The invariant at A2−1: a counterfactual must be measurable in-app.** SIEVE
> must be able to run the same work under two allocations and say whether the
> difference is real.

This is the formal content of the "load-balancing hypothesis testing engine"
intuition, and the backward chain makes it much smaller and much more buildable
than a general engine: the requirement is *hold the work identical, vary exactly
one placement field, and adjudicate the difference against the ambient noise*.

**And rule 7 is what makes it possible.** Allocation lives on the non-identity
side of the identity line, so two runs under different splits produce the *same
cache key by construction*. They are comparable because of the schema, not
because somebody argued they were comparable. In most systems a performance A/B
is confounded by the fact that you cannot prove the two runs did the same work;
here it is a structural property that already has a test. This is the single
most valuable thing this derivation found, and it was not visible looking
forwards.

The second common requirement, which all four paths need and none of them
supply: **the disturbance must be observed.** Ambient load — another process, a
browser, a shared cluster node — is non-stationary, and every path degrades to
noise-chasing without a reading of it. It is also the reason the naive remedy
(average more) is insufficient and the correct one is *blocked, interleaved
comparison* (ABBA rather than AABB), which is the standard defence against drift
in psychophysics and in online experimentation alike.

## Stepping back: A2−2

- **Placement must be a runtime object with a history, not a startup constant.**
  `resolve_worker_split()` runs once and returns a value nothing records. You
  cannot A/B a variable you cannot set, and you cannot interpret last week's
  sample without knowing what it was set to.
- **Every sample must be tagged with its mode.** `docs/todo/ledger-producers.md`
  already names this trap concretely: the 2026-07-28 session read as total
  throughput failure (0 ring hits) purely because ring mode was not engaged. A
  controller reading that would have tuned hard against a mode that was not
  running. Mode is not a nice-to-have dimension; it is the confounder that
  will actually bite.
- **A single reading must never be treated as a measurement.** Repetition, and
  a stated uncertainty, at the point of comparison.

So A2−2 is the same sensor work as A1−2 plus one thing: **allocation becomes
settable and recorded.**

## What this derivation says about the controller, which is not what I expected

Every candidate path's *final* step is a decision rule — a solver, a control
law, a selector, a classifier. Not one of them is the invariant. The invariant
sits one layer down, in measurement. That is a real result, and it independently
reproduces the position `docs/todo/adaptive-worker-allocation.md` already
argues from the other direction: *"a loop closed around an unobserved plant does
not converge on the right split, it oscillates, and an oscillating allocator is
worse than a fixed constant that is wrong by 20%."*

Two methods, forwards and backwards, landing on the same ordering is the
strongest evidence available here that the ordering is right. **The controller
is the last step, not the first, on every path.**

It also sharpens rule 6 into a form the load balancer can be held to:

> A controller must not act on a difference it cannot distinguish from noise.

That is the honest bound on the engine's scope, and it is what makes "robust"
mean something checkable rather than aspirational. Note also that this is a
legitimate, pre-authorized revision rather than a rule violation: rule 5's own
falsifier in `docs/ARCHITECTURE.md` reads *"the declared split leaves cores idle
while a user waits... The revision is a split that adapts to which consumers are
live."* A2 is that falsifier firing, on schedule.

## The causal-attribution question, answered as screening

"How does the program know which measures are causal to a load-balancing
problem?" is the hardest question in the original framing, and it has a mature
answer that is not model fitting.

The situation is: many candidate factors (worker counts per pool, ring capacity,
proxy width, block size, mode, cache bounds, chain length), few of which matter,
and each measurement is expensive because it costs a user-visible second. That
is precisely the regime **screening designs** were built for — fractional
factorial and Plackett–Burman designs identify which of *k* factors carry
first-order effects in O(k) runs rather than O(2^k), under the effect-sparsity
assumption that a small number of factors dominate (Box, Hunter & Hunter,
*Statistics for Experimenters*, is the foundational treatment).

The reason to believe effect sparsity holds *here* is not faith, it is the
findings tree:

- `capacity beats policy in the render ring` — one factor bought 42 points of
  hit rate; the other bought 0.69.
- `threading the reads buys 1.6x and stops` — the assumed factor (cores)
  plateaued at 4 and *reversed*; the real factor was memory bandwidth.
- `decode is a bandwidth wall` — 32 cores idle while the binding resource was
  something nobody was measuring.
- `scipy.fft's workers argument does nothing in this build` — a declared factor
  that was inert, undetected until somebody looked directly at it.

Four times the assumed causal variable was wrong, and each time one unassumed
factor dominated. That is textbook effect sparsity, and it is also a warning:
a system that fits a model over the factors it *declares* would have missed the
binding resource in three of those four cases. Screening asks which factors
move the outcome; it does not require a correct model of why, which is the
property that matters when the true cause has repeatedly been off the list.

The practical consequence for what gets built: **the engine's first job is
screening, not optimization.** Rank factors by effect, report the ranking with
uncertainty, and only fit or control the survivors. The repo has already run one
such screening by hand — the free-block-measures pass that promoted two of seven
candidates — so the shape is familiar; what is missing is that it was done by a
person, once, and not by the program, continuously.

---

# A3 — SIEVE navigates the parameter space itself

**Aspiration.** Give SIEVE footage and it searches the filter and parameter
space for candidate signals, trading storage, speed, and accuracy explicitly.

## Candidate paths to A3

**Path 1 — null-calibrated search.** The objective is defensibility: surrogate
nulls (circular shift, phase randomization) give a per-point significance, and
search maximizes detected signal subject to a calibrated false-positive rate.
*Final step:* the optimizer over a null-calibrated objective.

**Path 2 — label-driven active learning.** Labelled spans exist; the objective
is F1; the loop asks the user to label the most informative window. *Final
step:* the acquisition function that decides what to ask about.

**Path 3 — Pareto front.** No scalarization. SIEVE returns a front over
(storage, time, detection yield) and the user picks the knee. *Final step:* the
front, and an interface for walking it.

**Path 4 — unsupervised separability.** No labels, no null. Rank parameter
regions by how structured the response distribution is — bimodality, contrast
against the block's own baseline. *Final step:* the ranking, and the argument
that it correlates with real events.

## What is common at the final step

All four reduce to the same primitive: **a parameter point must be scorable,
cheaply, with an error bar, by the one execution path.**

The three clauses each do work:

- *Cheaply* — the search's budget is denominated in evaluations, so the cost
  model from A2 is not a nicety here, it is the currency. **A3 depends on A2,
  not the reverse.**
- *With an error bar* — rule 6. An optimizer with no uncertainty estimate will
  always return a winner, including on footage containing nothing. The failure
  mode is not a slow search, it is a confident wrong answer, which is the most
  expensive thing this system can produce.
- *By the one execution path* — rule 1. If search runs an approximation of the
  chain, the optimum it finds is optimal for a program the user will never run.

**The invariant at A3−1:** *an evaluation is the real pipeline, priced before it
is run, and scored with its own uncertainty.*

## Stepping back: A3−2

An evaluation must be **addressable and bulk-executable**: "run this chain, with
these params, over this window, headlessly, and give me back a record." Two
consequences:

- The record store is the same store A1 needs. A sweep is a session log with
  many samples and no human. This convergence is not a coincidence — it is the
  reason A1 is worth building first even though A3 is the more exciting goal.
- Neighbouring points in parameter space share a DAG prefix and therefore share
  cache keys, so the cache is not an optimization for search, it is what makes
  search affordable at all. Rule 7 again: the search over identity-side fields
  is exactly the search that invalidates keys, and the search over
  placement-side fields is exactly the one that does not.

---

# The cross-aspiration result

Placing the three −1 invariants side by side:

| | Invariant at −1 |
|---|---|
| A1 | A sample carries the identity of the work that produced it |
| A2 | The same work can be re-run with exactly one placement field varied |
| A3 | The same work can be re-run with identity fields varied, and scored |

These are one instrument pointed at three questions. A1 is **observation** —
what happened. A2 is **intervention on the non-identity side** — what would
happen if the machine were divided differently, with the result held fixed by
construction. A3 is **intervention on the identity side** — what would happen if
the analysis were different, where the result is what changes.

That is the association/intervention distinction, and rule 7's identity line —
already load-bearing for caching — turns out to be exactly the axis that
separates the two kinds of intervention. Being precise about the borrowed
framing: A1 and A2/A3 sit on the observational and interventional rungs
respectively; nothing here reaches genuine counterfactual inference, and it does
not need to. What is unusually strong in SIEVE's case is that A2's intervention
is *paired* — the same content-addressed work is re-run — which most systems
cannot arrange and which removes the confounding that normally makes performance
A/B testing weak.

**Why the benchmark is first-class, stated as an argument rather than an
assertion.** `ARCHITECTURE.md` opens with the product question: how much economy
can the user buy back without losing signal? Rule 7 splits every field into what
a result *is* and where it lives. Therefore economy is bought in two currencies:

- **Placement-side economy is free of signal loss, by rule 7** — checkpointing,
  worker split, ring capacity, the materialized crop. It *cannot* change a
  result.
- **Identity-side economy costs signal** — decimation, downsampling, block size,
  thresholds.

The product question decomposes exactly along that line, and it yields a
principle that is stronger than a preference: **exhaust the free economy before
spending any signal.** Never trade accuracy for speed you could have had for
nothing — which is O2 over O1 arriving in a new place. And you cannot know when
the free economy is exhausted without measuring it.

So the instrument is not scaffolding under the product. It is one of the two
coordinates the product's own stated question is asked in. An agent that
deprioritizes it as support work has deleted an axis of the question SIEVE
exists to answer — which is, precisely and mechanically, what has been
happening.

## The three things the whole chain lands on

Every path to every aspiration passes through these, and nothing else is
common to all of them:

**I1 — A sample carries its context, and the context is closed.** Identity
(node key, project revision), placement (resolved split, shares, mode),
environment (machine reading, ambient load), and time. Closed means: no fact
needed to explain a sample lives outside the record.

**I2 — The same work can be re-run with exactly one thing varied.** Placement
for A2, identity for A3. Rule 7 is what makes the comparison sound rather than
merely plausible.

**I3 — A difference that cannot be distinguished from noise is neither acted on
nor shown.** Rule 6 at the instrument. It binds the HUD, the controller, and the
optimizer identically, and it is what "robust" reduces to when made checkable.

The −2 layer under all three is buildable now and is mostly one item:
`Sample` gains dimensions, something durable writes it, the resolved allocation
is recorded, and comparison is repeated rather than single-shot. Three of those
four are `docs/todo/ledger-producers.md`,
`docs/todo/slow-path-surfacing.md`, and
`docs/todo/budget-checks-under-ambient-load.md`, all of which already exist and
two of which are already open.

The derivation's most useful output is therefore not a new roadmap. It is that
the items already at the front of the queue are the ones the long view needs
first, and the reason to take them is much larger than the reason currently
written on them.
