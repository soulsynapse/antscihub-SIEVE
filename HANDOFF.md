# SIEVE — build handoff

You are writing SIEVE from scratch. This is the only document you need. It is
short on purpose: everything in it either changes what you write in the first
week or records a measurement that cost real time to obtain. Two previous
implementations exist and both are described below, with a warning about how to
read them.

## 1. What it is

A video file holds a signal that, extracted cleverly, identifies a behaviour of
an animal. SIEVE is a list of operations over that video, shown to the user, who
tunes them against a small sample and then runs the tuned pipeline over the whole
set. The tuned pipeline is a file. Outputs are reingestible, so one run's result
scopes the next run's input — a pass that narrows six hours to forty seconds is
not an answer, it is the input parameter for the next session.

Every operation declares what it consumes and what it produces, which is what
lets a user name a target output and have the system enumerate what could
produce it. New outputs become targetable by writing operations that emit them.

The user's alternative, and the bar to clear: a few ffmpeg or cv2 commands, a
prebuilt analysis script, a plot to find thresholds, and a detection window. SIEVE
has to be faster to build a pipeline with, faster to tune, and not slower to run.

**The property that matters most: an agent with no context can be asked to write
something for SIEVE and will produce the right list of steps in the right places.**
Everything structural in §2 and §3 exists to make that true. If you find yourself
trading it away for convenience, you have made the wrong trade.

### What it must never do

SIEVE holds no opinion about the biology. It does not know what an event is, does
not need to, and any feature requiring it to know is refused however reasonable
the request. Two worked refusals, so the rule has referents: **no statistics or
analysis over the detections SIEVE produces**, and **no recommendations about how
to record better footage**. A pipeline works with what it receives. Also refused:
any parameter default presented as *recommended* rather than merely *preset*,
quality scores, did-this-work verdicts, automatic threshold selection, and
ranking of results.

The test is mechanical. Name the decision, then name what would make it wrong. If
the answer involves the user's animals, it is out of scope. Cost, scheduling and
numerical tolerance are decisions about computation, not interpretation, and are
in scope.

SIEVE owes **integrity** — an artifact is what it claims to be, an output matches
its declared schema, a written file reads back as what was written. It owes the
user nothing on **validity** — whether a threshold is right, whether the events
are real — except the speed to iterate on it.

## 2. The contract — get these right on day one

These are the things that cannot be added to code written without them. Everything
else in this document is advice; this section is the build.

**Registration is the only way an operation enters the system.** A decorator and a
registry. There is no second path and no review-time equivalent. This is what
makes "the list of operations" a query rather than a file someone maintains, and
it is what makes generation possible at all. Registration *refuses* anything the
engine cannot actually run — that is a stronger test than refusing a malformed
declaration, and it is the one that matters, because a declaration the runtime
cannot honour stays hidden until something important needs it.

**One call signature. Capability axes are fields of it, never separate protocols.**
Arity, statefulness, rate change, window extent: an operation implements one call
shape and varies within it. The counting argument is the whole justification —
two axes give four combinations and a per-combination protocol set will be missing
one, found by whoever first needs it; four axes give sixteen. A field an operation
ignores costs it nothing; a method it must stub out is a lie. The previous
implementation defined three protocols, and the missing fourth cell is exactly
where its detection work went — built beside the pipeline instead of in it,
unkeyed, unschedulable, carrying its own threading, invisible to every rule.

**Windows are declared on both sides — history and lookahead, as separate
fields.** This is the single most expensive omission in the last implementation. A
centred window reads frames *after* the one it is emitting for; its detection code
computed `t + (window - window // 2)`, which no one-sided declaration can express,
so detection was built outside the graph and stayed there. Each side is a bound
plus a function of resolved parameters: the bound admits the operation, the
resolved value sizes the actual lead-in or read-ahead, and a resolved value
exceeding its own bound is a registration error.

A shortfall at either boundary — fewer frames of history than declared at the
start of a source, less lookahead than declared at the end — is **legal and
recorded in the artifact's identity**, never an error and never a sentinel. The
lead-in actually supplied is part of what names the result, so a frame computed
with a full window and the same frame computed cold do not collide. Refusing
instead would make every windowed operation unusable across the first *w* frames
of every source. A sentinel standing in for history that was not there is the one
thing that stays forbidden, because it reads downstream as a real value.

**State is passed explicitly in the call, never captured in a closure at bind
time.** Created at a named offset, serializable to bytes, restorable from bytes.
How often to snapshot is the engine's decision; *being* snapshottable is the
operation's obligation. The previous implementation bound state in a closure, so
nothing could ask what offset a given state corresponded to, and every form of
random access into a stateful stream was therefore unavailable. Four of its seven
filters carried state.

**Every operation declares its I/O shape**: input arity and dtype, output arity
and dtype, whether it changes frame extent, and temporal extent on both sides. This
declaration is not bookkeeping — it *is* the feature where the user names a target
and the system fills in the gaps.

**Parameters carry a semantic type, not a primitive shape.** Region of interest,
curve, threshold-over-histogram, bounded scalar — not `tuple[int, int, int, int]`.
Nothing recovers "this is a crop rectangle" from four integers, so a type declared
late is a type whose control gets hand-written, and a hand-written control is
where state goes to become unsavable.

**Anything derived carries a content hash** over the operation's identity and
version, its resolved parameters, the geometry it was asked for, and the hashes of
its inputs — and nothing else. The hash names *what a result is*, never *how it
was obtained*. Do not include which optimisation ran, where bytes were staged, or
what path the source sat at: a cheaper route to identical bytes must not
invalidate everything it was meant to help. Twenty lines of code. It is what makes
compounding outputs work, and it is why deleting any cache is safe.

**Source identity is content-derived, or at minimum path-independent.** The hash
chain terminates at sources, so a source named by its current path makes every
artifact non-portable while leaving the spec perfectly portable — the spec
resolves on another machine, every artifact misses, and it looks like a cold cache
rather than a defect.

**One place owns each contended resource, and one entry point per capability.**
One threading owner, one cache, one facility that writes artifacts. Surfaces
submit requests; they never assemble stages themselves. Two owners of one resource
never conflict visibly — each is correct in isolation and the machine is
oversubscribed by their sum.

## 3. The surface

**Parameter controls are generated from declarations. They are never written per
operation.** An operation that declares a parameter gets a control for free. A
hand-written panel means exactly one of two things: the declaration is incomplete,
or the semantic type has no registered widget — and the second is fixed by
registering a widget, never by writing the panel. Rich controls (dragging a crop
on the frame, editing a curve, picking a threshold off a histogram) are widget
classes registered against a semantic type; they are members of a bag, not
exceptions to generation.

The previous implementation hand-wrote its filter catalogue, and the test that
should have caught the divergence asserted the hand-written catalogue against
itself — which does not merely fail to catch drift, it certifies it. Never write a
test that pins a hand-maintained copy against its own source.

**Generation covers more than widgets:** which operations may connect to which,
where a node may be placed, and the message explaining why a connection was
refused all derive from declared I/O. Each is a statement about what the runtime
will accept, and the declarations are where that is written. A surface that
refuses something the engine would have run is indistinguishable, to the user,
from a capability that does not exist.

**Authoring is graph-shaped from the start.** Branches, merges, fan-out,
multi-input nodes. A surface modelling a pipeline as a list expresses a proper
subset of what the runtime can do, and it cannot be widened later — placement and
connection rules written against adjacency in a list do not survive the change of
relation. The previous implementation built edges with `itertools.pairwise` and
its engine's branching was never reachable.

**Backward chaining is the answer to "I want this output."** Given a target,
enumerate the operations whose declared output admits it, recurse on their declared
inputs, terminate at sources. The relation is *derived from declared I/O and never
authored beside it*, or it becomes a second source of truth about connectivity and
drifts. The enumeration is unordered, or ordered only by a declared cost the user
can see — a ranked list of candidates is a recommendation, and those are refused.

A pipeline with unsatisfied precursors is a **legal state**, not an error. The user
assembles in any order; the runtime executes the valid subgraph and reports what is
unreached and why.

**Parameter edits are an ordered, replayable log.** Undo is truncating it,
invalidation is diffing hashes across positions, provenance is the log itself —
one mechanism, not three. The log *is* the pipeline spec, so saving is serializing
it. No state that determines a result lives outside it. Two things sit outside
legitimately: view-local state (zoom, scroll, hover), which changes nothing
computed, and machine-local preferences, which change what is *requested* but never
what a result *is*. The previous implementation held 154 distinct attributes on one
interface tab across 817 references, in 1,629 lines, including a source frame rate
baked into an interface default.

**Every derived quantity is owned by the engine and hashed, not computed inside a
view.** Histograms, aggregates, completeness boundaries. A quantity computed in a
view cannot be cached, reused, or compared against the same quantity computed
elsewhere — so the second consumer computes it again and one number acquires two
definitions.

**Preview and run are one code path at different resolutions or frame ranges,
never two implementations.** Downsampling and proxy resolution are legitimate
preview differences precisely because they change the hash — the preview is a
different identity, not different logic. Any divergence between what preview shows
and what a run produces is the highest-severity class of bug.

## 4. How an agent adds a new operation

This is the "step by step guide" and it is not prose, because prose drifts
silently. **Each bag holding a kind of thing carries a minimal reference member,
in tree, exercised by CI.** The reference set must cover the hard shapes — one
carrying state across frames, one taking more than one input, one changing rate,
one declaring a two-sided window — because a single easy member demonstrates only
the easy contract, and the hard contracts are exactly where someone reinvents
instead of reusing. A reference member breaks the build when it goes stale; a
document does not.

Adding an operation touches its own folder — declarations, kernel, fixture — and
nothing else. If it touches the interface, the engine, or a catalogue, the design
is wrong and that is the defect to fix.

## 5. Performance

What is cut is **prediction for a machine you are not running on**: portable
machine descriptors, per-operation declared cost shapes with fitted constants,
factorial sweeps over core sets and worker counts. A user who wants to know how
long a job takes runs it on a sample of their footage and measures, which is how
they would do it without SIEVE and what they expect.

Two things survive that cut, and both are small.

**Time remaining, from the sample the user already ran.** The tuning loop is a
run over a subset, so it has already produced an observed rate on this machine,
this footage and these parameters. Elapsed time over frames processed, scaled by
the frames remaining, refined as the full run proceeds. No cost model, no
declaration per operation, nothing fitted — the measurement is a by-product of
work the user was doing anyway, and it is more honest than a model because it
carries the actual machine and the actual content. One caveat, from the numbers
below: this extrapolates cleanly when the pass is math-bound, because tensor cost
is content-independent, and it is **confounded at low scale where decode
dominates**, since decode cost does vary with content. Say which regime the
estimate came from rather than hiding it.

**A latency number on the interactive path, kept and checked.** Preview
responsiveness is the one place where slow is a correctness problem rather than a
cost, so time it, keep the number, and fail when it regresses. Report it as a
**percentile, never a mean** — an average frame time looks healthy while the
worst tenth is what the user actually feels, and averaging is how a progress
indicator lies. This is a regression check on one path, not a benchmark harness.

Throughput and latency are two questions and get two statistics; do not collapse
them into one number.

What follows was measured on real footage during the first implementation. **Do not
re-derive these and do not optimise against intuition — two of them refute what a
span table appears to say.** Footage was 5312×2988 at 23.976 fps, 479 frames, 7
replicates, unless stated.

- **Decode-bound at low scale, math-bound at full scale, and it flips.** H.264
  decode is whole-frame and crop is a post-decode filter, so the decode floor is
  ~3.8 s per 479 frames *regardless of crop or scale*. At scale 0.245 a full
  extraction pass was 4.69 s against 3.82 s for pure ffmpeg decode with output
  discarded — everything the tool does added **13%**, and a span table reading
  "block_reduce 31%" was an artifact of the loop waiting on frames. At scale 1.0
  the same pass is 19.41 s and the math is **80%**. Both halves are easy to get
  wrong from a span table alone.
- **Prefetch on a producer thread: 15.14 s → 10.21 s (~33%).** It hides decode
  behind the math. Consumer spans read slightly *higher* with it on, from GIL
  contention, and it is still a clear win. Join the producer on close with no
  timeout — the caller releases the capture the instant close returns.
- **Block reduce as a reshape-and-view, not pad-transpose-nanmean: 3.46 ms →
  1.01 ms (3.4×)** on 730×1300 at block 16. Reshape to (ny, block, nx, block) and
  reduce axes 1 and 3; no copy, even for ragged tiles. Fall back to the nanmean
  route when the field holds NaN, to preserve masked-input semantics.
- **ROI decode: 10.41 s → 4.10 s (2.54×)**, and it is also ~3× *more accurate*
  than the full-frame path it replaced, which was not expected. Two traps, both
  load-bearing and both easy to "tidy" wrong: `format=gray16le` must come **after**
  `scale` in the filter graph — before it, swscale converts first and the error is
  far worse than plain 8-bit; and **seek must read the container's own frame rate,
  never a caller-supplied fps** — 24.0 standing in for 24000/1001 lands three
  frames early by frame 11000, silently.
- **Multiprocess does not help decode.** One ffmpeg already spreads decode across
  the whole box (`-threads 1` is 40.3 s against 3.8 s on auto). Aggregate decode
  throughput is flat past 2–4 workers. Math-bound work does scale further, but
  plateaus at **8 workers on a 32-core box at 3.6×**, and 16 workers deliver the
  same aggregate with every job taking twice as long. The suspected constraint is
  memory bandwidth — `tensor_blur` at ~53% and `tensor_products` at ~28% are large
  elementwise passes with low arithmetic intensity. That is a hypothesis consistent
  with the curve, not a measured attribution.
- **Downsampling and block size are not interchangeable levers.** Block size
  16 → 64 costs 13% of compute and saves 5–13× storage; downsample 1.0 → 0.245
  saves 4.8× compute and 13× storage. Block size is close to a pure storage lever.
  Expose both separately. Cutting width below the working default bought almost
  nothing — 1300 → 650 is a 4× pixel cut for ~13% wall time — while going up is
  paid in full.
- **A container's frame count is a claim, not a measurement.** One of four test
  videos advertised 11,328 packets and decoded 11,308 frames, with the loss in the
  *source*. Never compare a claim against a measurement and report the difference
  as a defect. Resolve a decodable count per file and record which source it came
  from.
- **Detection is ~0.5% of a pass.** Extraction throughput and job throughput are
  the same number. Optimise extraction.
- **A 25× decode win was 1.06× end to end** once decode was already overlapped and
  the pass was math-bound. Measure the end-to-end effect of an optimisation, not
  the stage it targets.

Measure before optimising, and an unmeasured optimisation is a guess that has been
made expensive to remove. Honesty about cost matters more than low cost: a slow
operation with a truthful reported cost is fine, a fast one that lies is not.

## 6. Testing

Assert on hashed artifacts and observable outputs, never on internals — that is
what makes tests survive refactoring, because the thing they check is the thing the
hash already holds stable.

**Fixtures are synthetic and generated, never downloaded and never committed
media.** A fixture that has to be fetched is one that gets skipped, and a test that
skips is indistinguishable from one that passes. Make frame *n* a solid field of
intensity that is a known function of *n*, so a test can assert **which** frame a
seek landed on. Note the limit: a synthetic source has no undecodable packets, so
it cannot exercise the container-count case above — that one is verified against
real footage by hand.

Verify a written artifact by reading it back through the path a consumer would
use. An encoder's success code is not evidence. One facility owns writing —
staging to a temporary location, reading back, comparing against what was
intended, handling cancellation, committing atomically. The previous implementation
arrived at this twice independently, at differing strength, because no single
component owned it.

Write the check before the thing, and write it as a refusal where possible: the
test for a contract is that a non-conforming operation is *rejected*. Acceptance
tests pass on systems with no contract at all.

## 7. Deliberately not decided

Do not build these. Each is cheap to add later and none constrains what you write
now, so building one early is how the schedule goes.

Scheduling, fusion, and materialisation policy. Caching and eviction strategy
beyond "anything derived is disposable." Determinism classes and numerical
tolerance declarations — add them when something actually fails to reproduce.
Migration between operation versions. Pressure policies per edge, shedding versus
backpressure. Any unit above a single source: a collection of sources with
per-source parameter overlays sits *above* the graph over independent members, so
it can be added later without touching an operation. Off-box execution,
partitioning, straggler handling. Replication, consensus and distributed
transactions are permanently out of scope; a design discussion reaching for them
has gone wrong.

Irregular regions and non-rectangular addressing: rectangles and uniform grids are
fine. Just do not encode the assumption in three places — the crop, the logic
matching a result against a request, and the surface mapping a click to an element —
because then the first irregular case breaks all three and none can be fixed alone.

## 8. The two previous implementations

**v1** is at `antscihub-optical-flow-detector`. It works, it is fast, and its
`FINDINGS.md` is the source of §5 — twenty sections of measurements with the
counter-intuitive ones marked as having been reached wrongly at least once. Read
that document.

**v2** is at `antscihub-SIEVE/src/sieve`. Its `docs/ARCHIVE/FINDINGS.md` is the
record of why it is being replaced.

**Read either one for lessons and measurements. Do not read either one to decide
how something should be shaped.** Both contain genuinely well-built components —
v2's frame coalescer, its settled-prefix computation, its read-back verification —
and each sits inside the structure that is the thing being replaced. Admiring an
implementation and inheriting its placement is one motion, and it is how the
second implementation acquired the first's problems.

One measurement is missing and would be worth having early: **v1 is believed to be
faster than v2 and nobody knows why.** No number exists for both on the same
footage. If you want that answered, it is one benchmark run, not an investigation.

## 9. The rule behind most of the above

A violation that is individually cheap and unbounded in count is enforced
automatically or it is not enforced at all. **The aggregate is the unit.** No
single hand-written control, privately owned thread, or duplicated helper is
expensive enough to reject on review, and a reviewer judging them one at a time is
right every time and wrong in sum — which is how the last implementation reached
154 owned attributes on one tab, five components each creating their own threads,
three incompatible caches, and a hand-written catalogue, with no individual
decision anyone would name as the mistake.

So push each rule as far down as it goes: make the wrong thing unrepresentable if
you can, generate it if you cannot, refuse it at registration if you cannot
generate it, fail CI if you cannot refuse it. A rule that lives only in a reviewer's
judgement, or in a document like this one, is a rule that will be violated by an
agent that has never read it — which is the population this is written for.
