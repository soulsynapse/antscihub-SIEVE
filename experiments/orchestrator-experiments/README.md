# orchestrator-experiments

Where SIEVE finds out whether one scheduling contract can absorb everything
that needs frames — the GUI, the tools, the proxy, the series writer — so
that what to hold and what to drop is derived from what every consumer
declared, rather than decided tier by tier.

The VapourSynth comparison is the right one. VapourSynth is a lazy-pull filter
graph: each node declares inputs and outputs, the consumer requests a frame by
index from the output end, the request propagates backward through the DAG, and
the runtime handles caching, threading, and request routing. Every node sees
one contract — "give me frame N" — and the graph decides who asks whom, in what
order, reusing what. The runtime knows when a frame's last consumer has read it,
and drops it.

SIEVE needs the same layer, and the constraints that make its version
non-trivial are already measured:

- **A seek costs 220–370 ms; a sequential read costs 10 ms.** VapourSynth
  assumes random access is free. SIEVE cannot. The orchestrator's scheduling
  decisions are dominated by this ratio, and the strategies that matter —
  attention-first fill, chunked write-behind, the proxy as a coarse tier
  over the whole extent — are all consequences of it.
- **A step's form is a function of the crop the user drew.** So the graph's
  type signature changes at interaction time, and whatever was cached under
  the old form is wrong rather than stale.
- **Cost belongs to the pairing, not the step (ADR-0007).** A step that is
  free riding along on a decode it did not request is the same step at commit
  cost when nothing else decodes that frame. The orchestrator has to know
  which regime it is in.
- **The interactive constraint is absolute.** Drag a slider, graphs refill
  faster than the video plays. Whatever the orchestrator builds must serve
  that loop, or the measurement that says it cannot is a finding about the
  loop, not about the orchestrator.

## The five questions

### 1. Can we schedule the GUI the same way as a tool?

The GUI is the hardest consumer SIEVE has. A drag asks for a frame at a
position that changes every few milliseconds, in a form the crop determines,
and may not block. A tool asks for a frame at declared offsets, in a declared
form, and may block. One is interactive and the other is batch, but the
declaration has the same shape: what form, at what positions, at what
priority.

If the GUI can be expressed as a node in the same graph — one that declares a
form, a reach of 1, and a position that tracks the cursor — then the
orchestrator never has to special-case it. The fill, the proxy, and the tier
stack become scheduling policies inside the graph rather than mechanisms
beside it. The question is whether a single declaration contract is expressive
enough to carry both the GUI's "give me this one frame right now, approximately
if you must" and a tool's "give me these offsets, exactly, whenever you can."

### 2. Can eviction be derived from declarations?

Today, frame lifetime is managed per tier: the store has a window and holds
everything in it, the proxy holds everything, and nothing coordinates between
them. A multi-step pipeline makes that untenable — not because the union
wastes memory, which ADR-0006 refuses as a justification and measurement has
since confirmed, but because no tier can say whether a frame is still owed to
anyone.

VapourSynth solves this: the runtime reference-counts frames across the graph,
and a frame is freed when its last downstream consumer has read it. The
question is whether SIEVE's declarations — the offsets a step admits, the
form it wants — carry enough information to derive a reference count, so that
a frame is dropped when every step that declared a need for it has been
served.

Settled, and not the way this section asked it. A consumer that may be
scrubbed has to declare its whole span, so retention converges on a window
rather than shrinking below one, and the derived answer comes out the same
size as the fixed one rather than smaller. The result is in `docs/findings/`
(2026.08.30, derived eviction). What the refcount buys is correctness and a
lifetime that spans tiers, which is why ADR-0006 is argued on fetches and not
on bytes; asking this as a memory question was the error, and the wording
above is left standing so the record shows which question was asked.

### 3. Can a non-frame node declare its needs the same way?

Not everything in the pipeline is frame-shaped. A series is a scalar per
position. A threshold is a single value. A geometry is a rect. But each of
these still has upstream dependencies — a series is reduced from a field, a
threshold might be read from a parameter document, a geometry comes from a
user's crop or from a detector.

The question is whether the declaration contract — "I need these inputs, at
these offsets, in this form" — is general enough to carry a node whose output
is not an image. If a series-writing node can say "I need the field from step
A at offset 0, and when I have computed my scalar, my upstream frame may be
released," then eviction works across the whole graph and not just the
frame-shaped part of it. If it cannot, the contract has a frame-shaped hole
and the non-frame consumers are back to ad-hoc lifetime management.

### 4. Can the orchestrator instrument itself cheaply enough to drive the UI?

The tool-explorer has five clocks — serve, field, paint, surface, show — with
an explicit unattributed remainder that turned out to be the term that
mattered. That instrumentation was hand-wired, one clock per concern, and the
remainder was the surprise because it was the thing nobody had a clock on.

If the orchestrator wraps every request it dispatches — decode, derive, field,
reduce, paint — with a timing envelope, the clocks fall out of the graph
rather than being wired in by hand. Every node that runs through the
orchestrator produces a duration, and the graph knows which node it was, so
the five clocks become N clocks with no hand-wiring and the unattributed
remainder is whatever wall time the orchestrator itself consumed between them.

The question is whether that wrapping is cheap enough to leave on in the
interactive loop. If it is, the duration bars on the pipeline cards are a
direct read of the orchestrator's own bookkeeping: each step's card shows a
bar proportional to that step's time against the total, and the user sees
which step dominates, which is free, and where the budget goes — the same
picture the explorer's clocks gave, but derived from the graph rather than
from bespoke instrumentation, and updating live as the pipeline changes.

The second question is whether the timing envelope carries enough to surface
inefficiencies the user did not ask about. A step whose field takes 0.2 ms
but whose fetch took 40 ms is not a slow step — it is a step waiting for a
frame nobody else needed either, and the card should say so. A step that is
free (in the noise beside a fetch something else requested) should show that
it is free, because the user deciding whether to add another step needs to
know what it will actually cost, and the declared cost class is the pairing's
to determine (ADR-0007), not the step's.

### 5. Can we implement priority-based fill under pressure?

Today, the fill has one priority: the chunk the playhead is in, then
wrapping. The proxy has one priority: the segment attention is on. Neither
knows about the other, and a machine under load runs both at whatever rate
the OS gives their threads.

With a graph of N consumers, each declaring positions they need, the
orchestrator has the information to rank: the GUI's current frame beats a
tool's background fill, which beats the proxy's far segment. The question is
whether a priority system — where each consumer's declared need carries a
pressure, and the orchestrator fills the highest-pressure request that the
machine has capacity for — produces a better felt result than the current
fixed-order fill. "Better" means the GUI never stalls for a tool's
background work, and a tool near the cursor fills before one the user
scrolled past.

The measured constraint is contention: `07-contention` in decode-experiments
and `04-under-load` in tool-experiments both showed that a second consumer
degrades the first by a measurable factor. So the priority system is not
about ordering idle work — it is about deciding which work to *defer* when
the machine cannot do everything at once.

Measured, and the answer is that priority is the wrong axis. With the fill
declaring its window attention-first — which is what `sieve/fill.py` already
does — a cursor moving smoothly never contends at all, and every
arbitration comes out the same within noise, because the frontier outruns
the person. The policies separate only under a jumping cursor, and what
separates them is not rank: ranking the queue against round-robin bought no
seeks back, reproducing the dispatcher finding's conclusion on a second
topology. What did move the wall is the rule that finding named and left
unimplemented — do not leave a sequential run for a position that run will
reach anyway. Results in `results/05-priority-under-contention-*`, two runs
that reproduce leg for leg because the cursor's walk is seeded.

## What this folder is for

The pieces this layer composes already exist, each with its own experiments:

| piece | where it lives | what it settled |
|---|---|---|
| source contract | `contract/nodes.py` | how a file enters SIEVE |
| step declaration | `tool-experiments/tools.py` | form, offsets, reach, reduction |
| forms | `contract/forms.py` | which pixels, at what sampling, canonical construction |
| store | `store.py` | keyed frames in RAM, coverage, refusals |
| fill | `fill.py` | attention-first background fill, two stop speeds |
| proxy | `proxy.py` | coarse-form whole-extent tier |
| chunks | `chunks.py` | write-behind to lossy-intra segments |
| serve | `serve.py` | route table — which tier answers, and says so |
| series | `tool-experiments/series.py` | one float per position per step |

None of them knows about the others' scheduling. The fill does not know what
a step wants; the step does not know what the fill has; the proxy does not
know what a step could ride along on. The orchestrator is the thing that does.

This folder measures the composition, not the parts. Every experiment here
runs against the real substrate — the same source, the same forms, the same
tiers — and the question is always what the *graph* costs, not what a node
costs in isolation.

## What to measure, roughly in order

Each experiment is shaped by the questions above. Ranked by what would change
the architecture:

1. **The unified declaration.** The GUI, a tool with reach 5, a tool with
   reach 20, and the series writer, all expressed as nodes declaring {form,
   offsets, priority}. Does the declaration carry enough for the orchestrator
   to schedule all four without special-casing any? The experiment is a
   harness that builds the simplest graph — source → two consumers with
   different reaches — and runs it against the current flat tier stack. The
   null hypothesis is that the overhead is in the noise; the real question is
   whether the contract *works*, not whether it is fast.

2. **Declaration-derived eviction.** The same graph, with eviction triggered
   by "all declared consumers past this position have been served." Measure
   peak memory against the current fixed-window model over the same footage
   and the same consumers. A graph whose derived window is larger than the
   fixed one for typical reaches is a finding against the approach; one whose
   derived window tracks actual need is the result that retires the fixed
   window.

3. **Non-frame nodes in the graph.** A series writer as a graph node: it
   consumes a field, produces a scalar, and releases its upstream frame on
   write. Does the eviction still work — does the frame drop when both the
   drawing consumer and the series writer are done? The failure mode is a
   non-frame node that holds references the graph cannot see, leaking frames
   the declaration said were free.

4. **Instrumentation cost.** Every request through the orchestrator wrapped
   with a timing envelope — start, end, node identity, route. Measure the
   overhead of the wrapping against unwrapped dispatch, in the interactive
   loop under load. The null hypothesis is that `perf_counter` pairs are
   in the noise beside any real operation; if they are not, the wrapping
   needs to be optional or sampled. Then: from the collected timings, derive
   the per-step duration bars — each step's fraction of the total — and
   verify that the breakdown accounts for wall time (the unattributed
   remainder is small and stable). The tool-explorer's five hand-wired
   clocks are the baseline for whether the graph-derived breakdown says the
   same thing.

5. **Priority under contention.** Run — `05-priority-under-contention.py`,
   and the settled note is under question 5 above. Two consumers filling
   concurrently, one at
   high priority (the GUI's cursor region) and one at low (a tool's
   background sweep). Under machine load, does the high-priority consumer
   maintain its rate while the low-priority one yields? Measure against the
   current model where both fill at equal priority and contention degrades
   both. `07-contention` is the baseline.

6. **Invalidation as a graph operation.** Run — `06-invalidation.py`. A crop
   change propagated through the graph: which nodes are invalidated, which
   frames are evicted, which fills restart, measured against recomputing
   everything from scratch. The other branch's frames do survive, and
   surviving turns out not to be worth much: on a diamond fed by one decode,
   dropping the untouched branch costs nothing to put back, because the
   decode the changed branch needs was already serving both. Derived
   invalidation buys the derivation and not the decode. What changes the
   number is holding a form that dominates both branches, which makes a crop
   change a derivation rather than a decode at a memory price the result
   file states. Nothing here can invalidate a *value*: after a parameter
   change every held frame is still correct and every scalar computed under
   the old parameters is wrong, and no declaration in this tree links the
   two.

7. **Form negotiation across the graph.** Run — `07-form-negotiation.py`,
   and the graph does not make the right choice, because no pool in this
   tree asks the question. Every store here is keyed by the form's *string*,
   and string equality is strictly weaker than `forms.grade`: a held frame
   that exactly dominates the one being asked for is a miss, and the miss
   goes to a decoder. What that costs depends entirely on how many cursors
   there are — worst by a wide margin on the single dispatcher this folder's
   explorer runs, since a second consumer's miss is a re-read of the
   position the cursor is standing on, which is a seek. Holding the
   dominating plane and deriving beats both arrangements on wall and loses
   on bytes. `tool-experiments/02-form-derivation.py` priced the derivation;
   this prices the choice. The exact grade's byte-for-byte claim is verified
   against `forms.build` here rather than asserted, which nothing had done.

## The rule for a result

Import `../decode-experiments/harness.py`, repoint `harness.RESULTS` here.
Same rules as everywhere: build, machine, probed footage attached; every
per-iteration sample kept; warm-up discarded and stated. Results committed.
A silently absent case reads as a case that came out equal.

One rule this folder adds: **a graph experiment names its topology.** The
result carries which nodes, which edges, which forms, and which policy was
under test, because a number from a linear chain and a number from a
diamond are different facts about the same graph code.

## Running

    uv run --group experiments python experiments/orchestrator-experiments/<name>.py

Footage from `video-tests/` (gitignored). Substrate files from
`tool-experiments/` are inputs here; derived scratch files this folder makes
are temporary and cleaned up by the experiment that made them.
