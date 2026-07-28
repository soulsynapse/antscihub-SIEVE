---
status: current
reviewed: e3d044c
subjects: [src/sieve/bench/, src/sieve/gui/concurrency.py, src/sieve/core/machine.py]
---

# Aspirations

Three endstate capabilities SIEVE is being built toward, each with a **done
condition** stated so it can fail. They are not scheduled and they are not
promises; they are the long view that near-term items are supposed to be walking
toward, written down because inference has repeatedly walked away from it.

`docs/VISION.md` and `docs/REFINED-VISION.md` are dated records of *workflow*
intent. This file is different in kind: it states capabilities that no current
item completes, and it is maintained rather than superseded. The derivation
behind it — four candidate paths per aspiration, the common final step of each,
and the invariants that survived — is `docs/WORKING-BACKWARDS.md`. Read that
before arguing with a conclusion here; the argument is there, not here. The
brief these were derived from is preserved verbatim at the end of this file.

---

## Why the instrument is the product, not scaffolding under it

`ARCHITECTURE.md` opens with the question SIEVE exists to answer: *how much
economy can the user buy back without losing signal?* Rule 7 splits every field
into what a result **is** and where it **lives**. So economy is bought in two
currencies, and they are not interchangeable:

- **Placement-side economy is free of signal loss, by rule 7.** Worker split,
  ring capacity, checkpointing, the materialized crop. These *cannot* change a
  result — that is the rule, mechanically.
- **Identity-side economy costs signal.** Decimation, downsampling, block size,
  thresholds. These change what the answer is.

That yields a principle stronger than a preference: **exhaust the free economy
before spending any signal.** Never trade accuracy for speed that was available
for nothing — O2 over O1, arriving in a new place. And there is no way to know
when the free economy is exhausted except by measuring it.

The measurement is therefore one of the two coordinates the product's own
question is asked in, not support work under it. **An agent that deprioritizes
instrumentation as scaffolding has deleted an axis of the question.** That has
happened repeatedly, by inference rather than by decision, which is why this
paragraph exists.

---

## A1 — A laggy session decomposes from its log

A session's wall clock can be attributed to its contributing parts after the
fact, by someone who was not there, from a file. The metrics that describe how
parts interact are *derived from* the log on demand, not chosen before it was
written.

**Done when:** a session is deliberately made slow by a known cause; a second
person, with only the log and no access to the machine, names that cause and
states how much of the wall clock it accounts for — and states the residual that
nothing accounts for.

**Fails if:** the log answers only questions somebody anticipated. A fixed report
is not this aspiration; a log that can be asked a new question is.

## A2 — SIEVE divides an unknown machine, and can say why

On hardware SIEVE has never seen, running a chain SIEVE has never seen, the
division of the machine is chosen from in-app measurement rather than from
constants tuned on one reference box — and SIEVE can state the effect size and
the uncertainty behind its choice. Robust in the dynamic-systems sense: bounded
under model error, non-oscillating, degrading gracefully when its model of the
machine is wrong.

The range is deliberate and wide: a Raspberry Pi running a trivial chain over
field footage before upload, and a cluster grinding hundreds of thousands of
hours of clips, are the same program making the same kind of decision from
different readings.

**Done when:** on a machine where the reference constants are known to be wrong,
the resolver finds the better split from its own measurements — *and*, on a
machine where the difference is not separable from ambient load, declines to
move and says so.

**Fails if:** it moves when it should not. A twitchy allocator is worse than a
fixed constant that is wrong by 20%, and the second half of the done condition
is the load-bearing half.

## A3 — SIEVE navigates the parameter space itself

Given footage, SIEVE searches the filter and parameter space for candidate
signals, trading storage, speed, and accuracy explicitly rather than by the
user's hand.

**Done when:** on footage with known events, the returned candidate set contains
a parameter point a human would have reached by hand, at a fraction of the
human's search cost — *and*, on footage containing no events, it returns an
empty set rather than a plausible one.

**Fails if:** it always finds something. An optimizer without a null always
returns a winner, and a confident wrong answer is the most expensive thing this
system can produce (O2).

**Depends on A2, not the reverse.** A search's budget is denominated in
evaluations, so the cost model is the search's currency. Building A3 first means
searching with no idea what a step costs.

---

## The three invariants everything passes through

Derived in `docs/WORKING-BACKWARDS.md` by taking the final step of four
independent candidate paths per aspiration and keeping only what was common to
all of them. These are what to cite when arguing that a piece of work does or
does not serve the long view.

**I1 — A sample carries its context, and the context is closed.** Identity (node
key, project revision), placement (resolved split, declared shares, mode),
environment (machine reading, ambient load), and time. *Closed* means no fact
needed to explain a sample lives outside the record.

**I2 — The same work can be re-run with exactly one thing varied.** Placement
for A2, identity for A3. Rule 7 is what makes this sound rather than merely
plausible: vary a placement field and the cache key is unchanged *by
construction*, so two runs are comparable because of the schema and not because
somebody argued they were. This is the strongest thing the derivation found, and
it is not visible looking forwards.

**I3 — A difference that cannot be distinguished from noise is neither acted on
nor shown.** Rule 6 at the instrument. It binds the HUD, the allocator, and the
optimizer identically, and it is what "robust" reduces to when made checkable.

### Two consequences worth stating separately

**The controller is the last step on every path, not the first.** Every
candidate path to A2 ends in a decision rule — a solver, a control law, an arm
selector, a classifier — and not one of those is the invariant. The invariant is
underneath, in measurement. `docs/todo/adaptive-worker-allocation.md` reached
the same ordering forwards, from control theory; two methods agreeing is the
best evidence available that the ordering is right.

**Causal attribution is a screening problem before it is a modelling problem.**
Which factors are causal to a load imbalance is answered by fractional-factorial
screening under effect sparsity, not by fitting a model over the declared
factors. The reason to believe effect sparsity holds here is the findings tree:
four separate times the assumed causal variable was wrong and one unassumed
factor dominated — the render ring (capacity 42pp vs. policy 0.69pp), threaded
reads (plateau at 4, reversal after), the decode bandwidth wall (32 cores idle),
and `scipy.fft`'s inert `workers` argument. A model fitted over declared factors
would have missed the binding resource in three of those four. **Rank by effect,
report the ranking with uncertainty, and only fit or control the survivors.**

---

## What is true today, so the gap is not restated as progress

As of `e3d044c`:

- `Sample` is `(Budget, elapsed_ms)`. No timestamp, no node key, no mode, no
  allocation. **I1 has no vehicle.**
- Nothing writes a metric to disk on any default path. `Recorder` is an
  in-memory dict that dies with the process, and the process dying is the
  circumstance under which somebody most wants the log.
- `ExecutorAdapter.missed` — the signal that means *this session was slow,
  here* — is emitted and connected to nothing.
- `resolve_worker_split()` runs once at startup and its result is recorded
  nowhere. **Placement is neither observable nor settable, so I2 is unavailable
  for A2.**
- 4 of 11 budgets have no runtime producer (`WITHOUT_PRODUCER`); 3 of 11 have a
  GUI surface.
- `MemoryFrameStore` is the declared unbounded consumer (`UNBOUNDED`), and
  `memory_reserve()` is provisional — a finding has already shown it models the
  wrong variable.

**Nothing here has been started.** The nearest work is
`docs/todo/ledger-producers.md`, which is I1's first producer.

---

## How this stays in front of a session

A document nobody opens is what failed before, so the routing is mechanical
rather than hortatory:

- `CLAUDE.md`'s *Where to look* table routes here for the long view.
- A `docs/todo/` item may declare `serves: [A1]` in its frontmatter, and
  `docs/.state.md` — the primer the work loop already forces every session
  through — renders each aspiration with the items serving it, **and renders the
  ones with nothing serving them.** An aspiration going unserved becomes visible
  in the one file every session reads, instead of being discovered three months
  later.
- It is deliberately *not* a test failure. A gate that fails when an aspiration
  has no open item would manufacture busywork and teach people to tag items
  falsely, which is worse than the drift it prevents. Visibility is the right
  strength here; if drift recurs despite it, that is the evidence for
  escalating, and this paragraph is the record of the choice.

---

## Appendix — the brief, verbatim

Kept unedited because the aspirations are a reading of it, and a reader who
thinks the reading is wrong should be able to check it against the source.

> We've been building out SIEVE's self monitoring tools over the last few
> sessions, and we need to set concrete endstate goals so that opus can build
> them out autonomously. I think the minimum for this is likely: 1. Usage
> metrics (how different things interact with each other) need to be able to be
> derived from usage logs; the logs should have enough information so that we
> can decompose a laggy session into the contributing parts. 2. The usage
> metrics are necessary (and are essentially the benchmarking feature that has
> been a critical part of this application from the start of this entire
> rewrite), because they both feed into the automatic SIEVE loadbalancing for
> unknown spec dev/user/hpc machines that range from everything from a raspberry
> pi doing a very simple SIEVE pipeline implementation prior to uploading
> research footage all the way to having to process hundreds of thousands of
> hours of clips. The axes of this need to be outlined and the most important
> parts that we need to absolutely nail down are: 1. how to log sufficient
> information so that it can be derived on command 2. how to automatically know
> which measures to distill as causal to a load balancing problem in order to
> fix the load balancing in real time - the user could pick any combination of
> filters and the software needs to have a ROBUST (in the dynamic systems sense,
> so this is a system or engine-building problem) way of solving it. I suspect
> this is some kind of load-balancing hypothesis testing engine that is in the
> program itself. 3. how to optimize these parameters, because SIEVE is about
> figuring out how to *optimally* filter out signals, so the entire software
> itself is quite literally built around this. A potential end goal here is to
> give SIEVE footage and it navigates the parameter space itself to find the
> candidate signals, optimizing for storage/speed/accuracy. This wasn't in the
> vision docs because we needed the capability first, but the capability to move
> things around is nearly here now, and the benchmarking / load balancing system
> has to catch up. The downstream effect of this is that as we write the program
> itself, properly written, the logs can automatically surface the
> inefficiencies or inadequate load balancing for different steps. This gives
> two additional, very important goals: how to write this into the docs so that
> the long-view aspirations are constantly being worked towards (lets make an
> ASPIRATIONS.md), and how to keep the plan coherent in how we get to those
> aspirations. The formal approach I want to use is for you to work backwards.
> We have aspirations; what are the 3-4 likely potential steps *right before*
> the aspiration is met that was achieved? Not 4 sequential steps before.. 3-4
> separate candidate paths that end in the aspiration being met, what was the
> final step of those candidate paths. That's the last step of it. Then we need
> to evaluate what was common between those 3-4 'end state -1' steps, and figure
> out if the generalized version of that is invariant between them. Then we go
> -1 steps again; what must have existed across all of those paths to get to the
> step after? I've added aspirations.md and working-backwards.md. If the only
> purpose of the software was to pull out things without much work then there
> are other ways to do it; what SIEVE is currently is a necessary intermediate,
> and the way it has been written opens up those other possibilities, but
> setting the long view in front of agents hasn't worked. The reason I'm
> bringing it in now is because the long view (and importance of benchmarking)
> has been sidelined by agent inference due to it's inferred importance, when I
> strongly suspect that it is a first-class, equally as important component of
> SIEVE as the capability for signal processing itself.
