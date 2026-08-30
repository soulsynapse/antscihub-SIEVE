# orchestrator2-experiments

The orchestrator rewritten around VapourSynth's activation model from the
first line, rather than having it retrofitted onto a graph that already had
threads.

## What this supersedes, and what it does not

`orchestrator-experiments/` asked five questions and answered them. Two of
its five are settled and stay settled — declaration-derived eviction
reproduces the fixed window, and preempting a sequential fill costs a seek
pair rather than a rank error — and both are in `docs/findings/`. Nothing
here re-measures either.

What this folder supersedes is the *mechanism*, not the results. V1 has the
declaration half of VapourSynth's contract and none of the re-entry half:

| V1 | what it is |
|---|---|
| `ToolRunner._work` | a thread per tool that declares, then sleeps 5 ms in a loop against a ten-second deadline, counting `starved` |
| `Dispatcher._run` | a thread that sleeps 4 ms when nothing is pickable, counting `idle_polls` |
| `OrchestratorExplorer._serve` | the Qt thread spinning at 2 ms with `processEvents` for an exact frame |

Three polling loops for one question — "is it here yet?" — that the thing
doing the decoding already knows the answer to. VapourSynth never asks it. A
filter there implements `GetFrame(n, activationReason, ctx)`: on `arInitial`
it calls `requestFrameFilter` for the frames it needs and returns without
computing; the core owns the threads and the caches, produces those frames,
and *re-enters the same call* with `arAllFramesReady` once they are resident.
A filter never waits on anything, because a filter is never running while
it would have to.

V1's explorer stays runnable, and **this folder does not edit it** — which
is not the same as it being frozen. Other sessions are still working in it:
it has since grown three preemption policies behind flags, and the two
findings that came out of those (`a-second-cursor-makes-preemption-free`,
`the-remaining-wall-is-decode-and-a-reader-that-does-not-overlap`) both bear
on V2 and one of them corrected it. So a comparison against V1 names the log
it compares to, not "V1" — the numbers move under both of us. V1 retires when
V2's walk reproduces its numbers leg for leg, and not before; four published
findings cite its logs by filename and two give `explorer.py --walk` as their
how-to-recreate.

## The apparatus

`dispatcher.py` is the whole of the new thing, and it keeps V1's name because
it is V1's job: the one thing that owns threads and decodes. What changes is
the direction the question travels. A consumer is no longer a thread that
declares and waits; it is a callable the dispatcher invokes twice:

```
    dispatcher.get_frame(node_id, row, activate, urgency)
        -> activate(Reason.INITIAL, ctx)          # declares; returns at once
           ctx.request(row) x N                   # == requestFrameFilter
        ... the fetch thread decodes, by pressure, into the pool ...
        -> activate(Reason.ALL_FRAMES_READY, ctx) # on a recorder thread
           ctx.get(row)                           # resident by construction
           ...arithmetic...
           ctx.record(value) ; ctx.release()
```

The second call is ADR-0005's recorder, and it is now literally what that
ADR says: a value is recorded at the point its inputs landed, on the thread
that observed them land, and never on the cadence of anything that draws.
The pipeline mints the callable and the dispatcher calls it — VapourSynth's
split, where the filter supplies `GetFrame` and the core supplies the thread.

Nothing here is called a core. `gui/frame/panes.py` already spends that word
on the centre region a subpane strip attaches to, and a second sense of it
naming a scheduler is a homonym nobody asked for. VapourSynth's vocabulary is
borrowed one level down, where this tree has no words at all: activation
reason, request, filter mode.

### Why two phases, and what the real alternative is

The obvious defence of this design is that nothing sleeps, and it is the
wrong one. It only distinguishes V2 from V1. **The competitor that matters is
a suspending scheduler** — a consumer written as a coroutine that awaits each
input as it needs it:

```
    async def activate(row):
        frames = {n: await pool.get(n) for n in tool.needs(row)}
        record(tool.reduce(tool.field(frames, row)))
```

That has no polling, no interval, no deadline and no `starved` counter
either, and the consumer is plainly nicer to write than a two-call callback
with a context object. Against it, "nothing sleeps" argues for nothing, and
any measurement of re-entry against *polling* — including this folder's
question 1 — is a measurement about V1 rather than about the design space.

What earns the split is that **INITIAL's output is a scheduling input.**
`Graph.pressure_queue` cannot rank a need it has not seen whole: subsumption
asks whether one declaration's rows sit inside a wider one's, urgency ranks
across every node in flight, and ADR-0006 makes the declaration itself the
hold, so a refcount needs the complete set at the moment it is taken. A
coroutine reveals its demand lazily, one `await` at a time. At the moment the
dispatcher chose what to serve it would know the consumer wanted row *n* and
not that it also wanted *n−30*, *n−20* and *n−10* — so it would serve *n*,
learn the rest, and seek back for them. That is not a hypothetical failure:
it is the shape `2026.08.30-the-pressure-dispatcher-preempts-into-seeks`
measured, a consumer buying by seek what was already arriving sequentially.

So the honest statement of the design is **the declaration is complete before
anything is served**, and the two phases are where that completeness is
enforced. The corollary is worth stating because it bounds how much the shape
matters: *a coroutine that gathers its whole demand set in one await has
re-invented INITIAL.* The split is a constraint on when demand becomes known,
not a commitment to callbacks, and an implementation is free to become
`async` later without giving anything up — as long as the first thing a
consumer does is hand over the whole set. What could not be kept is a
consumer that discovers its inputs by running.

Three consequences follow, and each is one of the questions below:

- Nothing sleeps. The fetch thread blocks on a condition the graph notifies
  when a declaration changes; the recorder threads block on a condition the
  pool notifies when a key lands. There is no interval anywhere. This is a
  property of V2 and not an argument for it — see above.
- A step's output is requestable. A field or a value is a thing the
  dispatcher can be asked for and can hold, wired to
  `sieve/pipeline/binding.py`'s `Held` and `sieve/series.py`'s `Sinks`,
  rather than to a local `derived` dict and a `self.values` that die with the
  thread that made them.
- Ordering is the dispatcher's to enforce, so a step that cannot be reordered
  has to say so. In V1 sequentiality was implicit in there being one thread
  per tool walking a range upward; there was nothing to declare because the
  thread *was* the declaration.

## What does not port, and must not be quietly assumed

VapourSynth's model is homogeneous in two ways SIEVE is not, and an
experiment here that forgets either is measuring VapourSynth.

**A filter is code the core calls; a tool is not.** A VapourSynth plugin
implements `GetFrame` and issues its own `requestFrameFilter`, because it is
compiled against the core and handed its pointers. A SIEVE tool may not
import the store, may not decide when a value is recorded, and never sees a
request context (ADR-0009, ADR-0005). The activation is *synthesised around*
a tool from `wants`, `offsets` and `produces`; the tool supplies arithmetic
and nothing else, and the wrapper — not the arithmetic — releases.

This is why question 3 is a question about a *field* rather than about a
method. VapourSynth's filter mode is something a filter announces because a
filter is callable code; `sequential` has to be a declared field because a
tool has no context to announce anything through. The two arrive at the same
place from opposite directions, and only one of them can be wrong about it.

**A dependency is not always a frame, and the store must not guess what one
is.** VapourSynth has one kind of thing a filter asks another for, indexed by
`n`. This tree has four — `contract/edges.py`'s `KINDS` — so the request path
is written for a key and an opaque payload, and `Pool` holds whatever it is
handed without asking.

What this folder must **not** do is enumerate classes of dependency and give
each its own handling. There is one payload kind anything in this tree
actually produces and one key shape; a taxonomy written now would have rows
with no instance in them, and a later reader takes an untested guess for a
decision somebody made. That is the same defect as `sequential` — a field
with one legal value — and the general form of it is already settled twice:
ADR-0007 falsified a step declaring its own cost class, because that class is
a ratio against a fetch the step cannot see; ADR-0009 names the failure mode
as accretion, each accommodation small and justified, their sum a substrate
shaped by the history of requests. `KINDS` is the closed set, SIEVE alone
extends it, and it grows when a real tool presses rather than when an
orchestrator anticipates one.

The one thing about non-frame inputs this tree *has* decided: a parameter is
not a dependency. A threshold or the crop the user drew has no row, is never
requested, and travels in the **key** (ADR-0010) — changing one names a
different series, which `sieve/series.py`'s `Sinks` makes a lookup rather
than a re-run. A node that appears to want one is a node whose key is wrong.

That is also where V1's withdrawn question 6 left a real gap: after a
parameter change every held frame is still correct and every scalar computed
under the old parameters is wrong. The key closes that for values. Whether it
closes it for a held *field* is not established, and this folder does not
close it either — it is named here so a later reader does not mistake the
activation model for an answer to it.

## Carried over intact

Cited, not re-measured. Where any of these is spelled differently here than
in V1, the difference is a defect in this folder.

- **`Need` and `Urgency`.** Urgency is the only scheduling fact a consumer is
  placed to state — whether a person is waiting. Where it ranks against
  declarations it cannot see is derived. `2026.08.30-the-pressure-dispatcher-preempts-into-seeks`
  falsified declared rank and the reasoning is ADR-0007's, applied to
  scheduling instead of to cost.
- **`pressure_queue`'s three keys**, subsumption especially: a DEFERRED need
  whose rows sit inside a wider declaration yields to it, because the wider
  one is a producer that will arrive there sequentially and jumping the queue
  buys by seek what was already coming by read. Its cost is settled and is
  not a thing to optimise: `the-remaining-wall-is-decode-and-a-reader-that-
  does-not-overlap` measured the dispatcher's whole per-decode bookkeeping at
  a fraction of a millisecond, having named it as the hypothesis for a gap it
  turned out to be two orders of magnitude too small to explain.
- **A reader per band, above one reader.** `a-second-cursor-makes-preemption-
  free` shows a preemption's cost is one cursor being taken from the sweep
  rather than the price of serving a person, and that the extra reader is
  free because it is idle unless something interactive is pending. V2 makes
  the count a parameter and partitions the bands so reader 0's cursor is
  never moved by a person; what V1 could not do, and what that finding's
  companion prices at about a third of a filled window, is let the two
  overlap.
- **Refcounted holds keyed by `(row, form_key)`**, and a `Need.row` is an
  ordinal against one listing snapshot while only the fetch converts to a pts
  (ADR-0004).
- **The `_gen` / `plan_changed_since` discriminator**, which is what makes
  ADR-0008's named re-fetch countable rather than merely deplored.
- **`Envelope` instrumentation, left on.** V1's question 4 measured the
  wrapping cheap enough for the interactive loop.
- **The pool's byte ceiling as a backstop**, not a policy. It never fired in
  any V1 run; a run here where it fires is a result about the topology, not
  a tuning opportunity.
- **The `_by` sharing counts.** "Decode once, serve many" is the claim the
  graph is built on, and an uncounted claim is an assertion.

## Do not regress these

Each was bought by a defect, and each has a fingerprint a log can be checked
against.

1. **A decode is attributed to `dispatch:<role>`, never to the node that
   declared it.** Otherwise a duration bar claims the GUI spent half its time
   computing, when what it spent was a seek somebody else performed for it.
   Fingerprint: `duration_bars` keys begin `dispatch:`.
2. **The stale count after `still_wants`.** A decode that landed after its
   asker moved on is the price of per-frame preemption, and only the count
   says how often the trade was bad. V2 adds `superseded`, which counts the
   same waste before it is paid for rather than after; both are kept, because
   they are different halves and a scrub produces both.
3. **The `refetched` / `predicted` pair.** `refetched` alone is not an
   accusation — coming back to a window is a fetch. `predicted` is the number
   ADR-0008 targets at zero.
4. **The deadline under `pressure_queue`.** Ranking for locality is what
   starves whoever ranks last, and the queue's subsumption rule is
   anticipatory scheduling (prior art: Iyer & Druschel, SOSP 2001) carried
   without the anti-starvation half that literature always pairs it with. An
   ORDERED node behind a person scrubbing without pause computed 1 of 60
   armed rows; with an expiry queue keyed on last service and drained in a
   batch it computed 60, taking 5.6% of picks to do it. `05-starvation.py`,
   and `expired_picks` is the counter — zero means the ranking never starved
   anybody over that run, and it is zero in every uncontended experiment
   here.
5. **`closeEvent` releases the sweep before the log is saved**, which is why
   `graph_holds` reads 1 in a V1 log while a window is live. The
   derived-eviction finding documents it under "how to recreate"; a V2 log
   that repeats it without saying so is a log that will be misread the same
   way.

## The three questions, both outcomes pre-registered

### 1. Does re-entry beat polling, and on what axis?

Two axes, and they are not the same result.

*Structural.* Threads that exist to wait, and rows abandoned because a wait
timed out, should both go to zero: there is no `starved` counter to keep
because there is no deadline to exceed, and no `idle_polls` because there is
no interval. Consumer threads go from one per tool plus one dispatcher to a
fixed pool that does not grow with the graph.

**This question compares V2 against V1, not against the alternatives.** A
suspending scheduler would remove the same interval, so whatever this
measures is the cost of the arrangement V1 actually had rather than evidence
for two-phase activation. The argument for the split is the one above, and it
is about `pressure_queue` seeing a whole declaration, not about sleep.

*Felt.* Foreground latency during a scrub is the real question. Preemption
granularity in V1 was already one decode, and the pressure-dispatcher finding
shows the wall is a two-term cost model in seeks — so re-entry removes the
sleep that sat *between* decodes, not the seek that dominates them.

- **If scrub latency does not move**: the result is that re-entry is a
  structural win and not a performance one. That is worth writing, because it
  says the polling loops were never the term that mattered, and it retires the
  idea that the felt loop is waiting on the orchestrator's own bookkeeping.
- **If it moves**: the term is the handoff — a frame landing and the consumer
  noticing it up to one poll interval later. Then the interval was in the
  interactive path and the size of the win is the size of the intervals.

Either way the structural claim is checked separately and does not depend on
the felt one.

**Half answered, on the uncontended fill.** `01-reentry.py` and
`docs/findings/2026.08.30-re-entry-removes-the-poll-interval-and-not-the-wall`:
the handoff is the poll interval and nothing else, and re-entry removes it by
about ten times; the wall does not move, because the fetch thread is the
bottleneck and the waiting it deleted overlapped decode nobody was blocked
on. That is the structural outcome above, for the case where nothing is
waiting. The felt half is still open and is the explorer's, because the
handoff is only visible when a person is behind the row.

Two things that experiment settled in passing. The request depth this folder
introduced — how many activations of one node may be in flight — costs
handoff and buys no wall while a step's arithmetic is a few percent of its
row's decode, so it is 1, measured rather than assumed. And a single run per
arm read session drift as an effect and said the opposite; arms are
interleaved and repeated here for that reason.

### 2. Should every node's output be cached and requestable?

`2026.08.30-holding-a-chained-field-pays-above-a-producer-crossover` already
establishes the crossover in producer cost below which holding a chained
field is a pessimisation, and which of this tree's steps fall either side of
it. **That number is not re-derived here.** What is unmeasured is whether
routing the hold *through the core* — so a consumer's field want is a
`request_frame` like any other, waiting on an activation rather than reading
a dict — costs anything on top of the plain `Held` it was measured with.

- **If core-mediated holding reproduces the held case within noise**: the
  crossover is a property of the arithmetic and not of the machinery, every
  node's output can be requestable without a second decision, and where to
  hold becomes one rule read off one measurement.
- **If the activation bookkeeping is a measurable fraction of a consumer
  row**: the crossover moves, upward, by the bookkeeping — and "requestable"
  becomes a per-node choice with a threshold, which is a worse arrangement
  and has to be said so.

The topology is the chained one and is stated in the result: two steps, the
consumer admitting sparse lags against the producer's field, at the small
analysis form. Frames resident by construction in both cases, as in the
finding, so decode is in neither number.

**Answered: the second branch.**
`docs/findings/2026.08.30-making-a-field-requestable-costs-about-what-the-crossover-is`.
The dispatcher costs about 0.33 ms per activation over a plain `Held` dict —
the same figure the re-entry finding measured as the handoff, arrived at from
a different experiment — and the chained-field crossover it would be judged
against is the same order. So requestability is a threshold and not a policy:
free for a frame, where a decode is 6–10 ms, and not free for a chain of cheap
steps. That is a measured argument for the separation `binding.py` already
asserts when it says its `Held` is not to be grown into a pool.

One thing the experiment does **not** establish, and the README overclaimed by
implying: demand does not propagate backwards. A consumer asking for a
producer's field row waits for it rather than causing it, and the producer is
driven by its own `Pass`. VapourSynth's `requestFrameFilter` propagates
through the DAG, and that half is not built — so "requestable" here means
"held and served under a key", which is weaker than the word suggests.

### 3. Does a node have to declare how it may be scheduled?

`contract/nodes.py`'s `Step.sequential` and `tool-experiments/tools.py`'s
`Tool.sequential` both exist and nothing consults either. VapourSynth has
filter modes for exactly this: `fmParallel`, `fmParallelRequests`, and
`fmFrameState` for a filter carrying state that forces frames to be processed
in order.

**Stated plainly: the tree does not currently contain a sequential step, and
`tools.py` argues it should not until something real needs one.** So this
question cannot be answered by finding a case; it is answered by building the
minimal one that `lag_mhi`'s own docstring names as the sequential twin of
what it does — a motion history carrying a decayed accumulator, offsets
`(0,)`, bounded state, replay on every jump — and running it under a core
that reorders.

- **If the accumulator produces different values under a parallel core than
  under an ordered one**: the flag is load-bearing, the core must honour it,
  and the reset/step/checkpoint protocol `tools.py` names becomes owed rather
  than hypothetical.
- **If it does not** — because every ready activation happens to arrive in
  order anyway under a single ascending producer — then the flag has one legal
  value in this tree and the honest move is to delete it from both records
  rather than leave a field that reads as a knob. A field nothing consults and
  nothing can falsify is worse than its absence, because a later reader takes
  it for a decision somebody made.

The failure this must not commit is measuring the dispatcher's ordering
against a workload that is ordered by construction. The parallel case has to
actually reorder, and the experiment states how it forced that.

**Answered, and neither branch won as written.**
`docs/findings/2026.08.30-a-decaying-accumulator-has-a-reach-and-stops-needing-a-flag`.
The step built to need the flag dissolves into the contract the tree already
has: because the accumulator decays, its history has an effective reach, and
restated as a stateless step at bounded offsets it agrees with the unbounded
version to 2e-6 by reach 40 and needs no ordering, no state, and no flag.
`tools.lag_mhi` is that restatement and predates the question.

Two corrections the experiment forced on this folder. The first version's
parallel arm shared one tool instance across recorder threads and reported the
resulting data race as evidence that parallel dispatch breaks stateful steps;
it is evidence that shared mutable state breaks under threads. And the whole
question was posed without leaning on prior art that has mapped it: AviSynth+'s
`MT_NICE_FILTER` / `MT_MULTI_INSTANCE` / `MT_SERIALIZED` already say state
implies unshared state rather than serialization, and the recurrence is an
associative max-plus scan, so Blelloch's decomposition applies and it was never
inherently sequential. **This folder should reach for that literature first
rather than re-deriving it**: filter graphs, stream operators and prefix scans
are old, and SIEVE's novelty is the seek cost, not the scheduling.

### 4. Does a victim cache beat dropping everything unreferenced?

**The diagnosis.** `pool.py` is a database buffer pool with the pinning half
done and the replacement half missing. Pinning is the refcount — a key some
declaration still names may not be stolen, which is ADR-0006 and is correct.
Replacement is what ranks victims among the *unpinned*, and there is none:
`_sweep_locked` drops every unreferenced key unconditionally. Unreferenced
means deleted, so a 16 MB frame that cost a 300 ms seek and is about to be
scrubbed back onto is discarded on the same terms as one that cost a 10 ms
step and will never be asked for again.

**What replaces it.** Unreferenced entries stop being garbage and become a
victim cache (prior art: Jouppi 1990) ranked by GreedyDual-Size (prior art:
Cao & Irani 1997), which is the standard policy when items differ in *both*
cost and size — the case SIEVE is in and LRU is not built for. Each key
carries `H = L + cost/size`; eviction takes the minimum `H` and raises the
aging clock `L` to what it evicted, so age falls out of the arithmetic rather
than needing timestamps. Both inputs already exist and are currently thrown
away: `Envelope` records what a decode cost in milliseconds and the route it
took, and `_bytes` already tracks size.

Eviction stops being "drop everything unreferenced" and becomes "drop the
least valuable unreferenced keys until under the ceiling", which also makes
the byte ceiling load-bearing for the first time — the derived-eviction
finding records that it never fired in any V1 run.

**Where this is falsified.** The instrument exists already and nothing acts on
what it reports: `refetched` and `refetched_predicted`, the latter targeted at
zero by ADR-0008. The scenario exists too — the walk's leg 5 is *"returning to
A: the graph released it when B declared, so this is a cold refill"*. So the
test is that shape headlessly: land A, land B, return to A, with a ceiling
above one window and below two.

- **If leg 5's decode count falls**, the hand-rolled policy was leaving reuse
  on the floor, `victim_hits` says how much, and the byte ceiling becomes a
  policy knob rather than a backstop.
- **If it does not**, there are three ways that can happen and they are
  different results. The ceiling may be too small to hold a useful remnant of
  A, which is about sizing rather than ranking. A returning consumer may
  re-declare its whole window anyway, which would be the derived-eviction
  result again — a scrubbable consumer declaring its whole span — and would
  say the pool's problem is not its replacement policy. Or **fragmentation**,
  below, which is the one worth naming in advance because it is a defect in
  the policy rather than in the setup.

**Fragmentation is the specific way this is expected to fail, and it is
pre-registered because it is a known limitation rather than a surprise.**
GreedyDual-Size ranks every item independently, which assumes an item's
refetch cost does not depend on which other items are resident. That
assumption is false here and its falsity is measured:
`2026.08.30-the-pressure-dispatcher-preempts-into-seeks` gives the wall as a
sequential term plus about a third of a second per seek, so a frame costs a
step if its neighbour is on hand and a seek if it is not. A policy that
retains a *scattered* half of window A therefore hands the sweep a window it
must seek through, and fewer decodes can cost more wall than more decodes in
one run. So the decode count is not the metric on its own — the return leg's
**seek count** is reported beside it, and a result where decodes fall while
seeks rise is the policy being wrong for this workload rather than the idea
being wrong.

If that is what happens, the prior art has the next move and it is not a
better ranking: it is that items are not independent, so the unit being
ranked should be a run of contiguous rows rather than a row. That is a
different algorithm and it is not being written on speculation.

**Answered, and it is fragmentation.**
`docs/findings/2026.08.30-retention-pays-only-when-what-survives-is-contiguous`.
Retention halves the return leg — but only when the survivors form one band.
GreedyDual-Size keeps the same sixty rows scattered over thirty runs and takes
the same wall as having kept nothing, so a fragmented remnant is worth zero
rather than worth less. The ranking proposed here is refused, and the cost
turned out to bill as wasted stepping rather than as seeks, because
`STEP_WITHIN` is wider than the gaps: `runs_on_arrival` predicts the wall and
the seek count does not.

The larger result is that **the lever is not the ranking at all.** On the
realistic return — offset by half a window, which is what a person does —
every implementable policy is at or below break-even against dropping
everything, and only the oracle wins, by knowing which rows the next landing
wants. That is a gap in information rather than in algorithm: the next landing
has not been declared when the eviction happens. Whatever closes it is a
prediction about a person, which the application has and a replacement policy
does not.

The default stays `DropAll`, because nothing beat it across both shapes and
changing it would be choosing one workload over the other on no evidence.

**What this deliberately does not do.** No scan resistance. The sweep is a
sequential scan that would flush an interactive consumer's frames under a
naive policy, which is the problem ARC (Megiddo & Modha 2003) and 2Q (Johnson
& Shasha 1994) exist for; the refcount currently sidesteps it, and if it ever
needs solving, 2Q or CLOCK is the thing to reach for rather than ARC, which is
patented. No min-cut partitioning of the graph (prior art:
`torch/_functorch/partitioners.py`), which is the right formulation for
recompute-versus-store across a deep chain and is premature at depth two.

## What has not moved, and why the shelf still points at V1

`docs/solutions/INDEX.md` has four entries pointing into
`orchestrator-experiments/` — the decode cursor at `fetch.py`, fetch
scheduling at `graph.py`, and both frame eviction and the held intermediate at
`pool.py`. **None of them moves here yet**, because none of those mechanisms
has moved: V1 is still the runnable explorer, still the folder the published
findings recreate from, and this folder's copies are a parallel arrangement
rather than a replacement. A shelf naming superseded code is worse than no
shelf, and so is a shelf naming code that has not superseded anything.

One entry did change content without changing where it points: the held
intermediate now carries which of the pool and a binding-scoped hold to reach
for, because that stopped being a matter of taste when question 2 measured it.

When V2's walk reproduces V1's numbers leg for leg and V1 retires, all four
move together, in the commit that retires it.

## The rule for a result

`docs/findings/` rules, plus the two this shelf inherits from V1: import
`../decode-experiments/harness.py` and repoint `harness.RESULTS` here; **a
graph experiment names its topology**, because a number from a linear chain
and a number from a diamond are different facts about the same graph code. A
silently absent case reads as a case that came out equal.

One rule this folder adds: **an activation experiment names its core shape** —
how many fetch threads, how many recorder threads, and which filter mode each
node ran under. A wall from a two-worker core and a wall from a four-worker
core are different facts, and the model under test is the one that decides
which threads exist.

## Running

    uv run --group experiments python experiments/orchestrator2-experiments/<name>.py

The explorer is a felt test and runs on the real desktop, not offscreen:

    uv run --group experiments python experiments/orchestrator2-experiments/explorer.py

Footage from `video-tests/` (gitignored). `explorer-logs/` is ground truth
for anything about how it felt; read the newest before trusting a
recollection of it.
