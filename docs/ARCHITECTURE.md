# ARCHITECTURE

SIEVE is a data-intensive application. A filter chain over video emits many
multiples of the source in derived data — one intermediate per node per frame
per replicate — and the design problem is how that derived data is keyed,
materialized, invalidated, and thrown away, not how any one filter computes.

The vocabulary is Kleppmann, *Designing Data-Intensive Applications*, named so
that design discussions start from a shared word rather than reinvent one. It
covers the interactions — state, windows, joins, backpressure, keying, skew —
and does not cover cost estimation or performance modeling. Where §2 and §7 need
a cost model with calibrated, parameter-dependent constants, the reference is
query optimization (Selinger-style estimation; Volcano/Cascades for structure);
where §7 needs an estimate for a machine we are not running on, it is analytical
performance modeling. Named here so a cost discussion does not go looking in the
wrong book.

This document is normative: each section states a rule, the mechanism that
enforces it, and the failure mode it forbids. It covers runtime data only. How
the codebase is organized — toolbags, contracts, package surfaces — is a
separate argument and is not answered here.

One dividing line runs through all of it. What appears in an operator's contract
or in a key must be right from the beginning, because changing either rewrites
every operator and invalidates every artifact. What is an engine implementation
choice can be replaced whenever, which is the whole point of §2.

## 1. Keying admits things to the DAG

The system of record is the source assets and the pipeline spec. Everything
else — filter output, preview frame, crop artifact, detection table — is
derived: recomputable, disposable, and keyed by the derivation that produced it.

1. A key is the transitive closure of what the output depends on: operator
   identity and version, its resolved parameters, the geometry it was asked
   for, and the keys of its inputs. Two runs with the same key must agree to the
   operator's declared determinism class (§1.5), or it is not admissible.
2. Membership in the DAG *is* deterministic keyability. This is the admission
   test for pipe sections, and it is checked at registration, not by review.
   An operator that reads wall-clock time, machine state, or an RNG it does not
   declare and seed fails the test.
3. Nothing derived is authoritative. Any cache, proxy, or materialized
   intermediate can be deleted at any point and the only consequence is
   recomputation cost.
4. The source assets being video today is a property of the operators we have,
   not of the system of record. Nothing outside an operator's own input
   declaration may assume a decodable video exists.
5. Determinism is declared, in one of two classes, and the class is part of the
   key. *Bitwise* operators reproduce byte-identically and may be freely
   recomputed, compared, and discarded. *Tolerant* operators — threaded
   reductions, GPU kernels with float atomics, any library whose summation order
   varies by build — reproduce only within a declared numeric tolerance, so
   their artifacts are materialized once per key and reused rather than
   recomputed and compared. An operator that declares no class is bitwise, and
   failing to reproduce is then a failure rather than a discovery. Two things are
   deliberately unsettled here, because both become concrete the moment the key
   algebra exists and neither should be decided on paper: whether the class
   propagates — whether an artifact computed from a tolerant input can itself be
   bitwise, which interacts with §1.3's claim that anything derived is freely
   deletable — and what discipline governs a declared tolerance, since a bound
   chosen to make its own test pass is not a check. Phase 1 settles both against a
   test.
6. An artifact is whatever a key names, and for an operator carrying state
   across frames that is a frame range together with the state it began from —
   not a frame. The starting offset is part of the key. Without this, output
   that depends on where a run happened to start keys as though it does not, and
   nothing can detect the difference.

Forbids: artifacts that cannot be reproduced, and therefore cannot be
invalidated with confidence or thrown away without fear — and equally, an escape
hatch bolted on the first time a threaded kernel fails to reproduce bitwise.

## 2. Operators declare; the engine decides

An operator declares a pure transform, its I/O shape, and its cost model. The
engine decides fusion, materialization, parallelism, placement, and
scheduling.

1. Declared I/O shape covers input arity and dtype, output arity and dtype,
   geometry transform (does it change frame extent), and temporal extent (how
   many frames of history it needs — see §3). Parameters are declared with a
   semantic type — region of interest, curve, threshold-over-histogram, bounded
   scalar — not merely a primitive shape. §6 generates controls from these, and
   nothing can recover "this is a crop rectangle" from `tuple[int, int, int,
   int]`.
2. An operator never chooses its own thread, process, buffer size, or cache
   location, and never reads a machine-capability probe. Asking for those is
   the engine's job and the engine is allowed to answer differently per
   machine.
3. Cost is declared as a *shape*, not a constant: which declared inputs the
   work scales with, and how. Constants are fitted by the benchmark harness on
   the machine it runs on. A filter author writes "linear in output megapixels,
   linear in window length"; nobody hand-writes milliseconds. A shape may take
   measured properties of the data as terms — blob count, scene activity — when
   the work is content-dependent. That makes estimation two-pass, sampling the
   source before estimating, which is strictly better than an honest interval so
   wide it answers nothing.
4. A new filter is benchmarked through the engine. There is no per-filter,
   per-machine stress ritual, and a filter that can only be validated by
   running the GUI and watching for lag is not finished.
5. Parameters are what the user tunes. Properties of the source — frame rate,
   extent, duration — and the resolved geometry produced by upstream nodes are
   execution context, supplied by the engine and never declared as parameters. A
   parameter that duplicates a source property can disagree with it, and the
   disagreement is silent, because the declared parameters remain perfectly
   consistent with each other while every quantity derived from them is wrong.
6. Operators may take more than one input, and the interesting ones do — a node
   joining a full-resolution stream to a reduced one is a join across differing
   rates and geometries (Ch. 11). Reconciling them is the engine's job, and both
   are part of the key. Multi-input keying is cheap to allow now and expensive
   at the moment the first two-input node needs it.

This is the one place the architecture adds a requirement the product did not
ask for: declaring a cost shape is real work per filter. It is accepted because
without it the engine cannot place work, and SIEVE cannot answer "how long on
*your* machine" — the question that justifies the tool.

Forbids: bespoke filters, each tuned to the author's machine, with no runbook
and no comparable numbers.

## 3. Windows are declared; pressure policies are named per path

Filters that carry state across frames are stateful windowed operators.

1. History requirement is declared as a bound plus a function of resolved
   parameters: the bound is what admits the operator, the resolved value sizes
   the actual lead-in, and a resolved value exceeding its own bound is a
   registration error. Lead-in is window warmup and the engine supplies it. An
   operator never reaches backwards for frames it did not declare, and a warmup
   shortfall is an error — never a sentinel value standing in for history that
   was not there, which is indistinguishable from a real result downstream.
2. Retuning is reprocessing, not mutation. A parameter change replays the
   affected window; it never patches state in place.
3. Every producer/consumer edge names its policy: backpressure, bounded
   buffering, or load shedding. Chosen per path, never left to chance, and
   never "whatever the queue does when it fills."
4. Interactive paths shed; export paths backpressure. Dropping a preview frame
   is correct behavior and must be reported as such (§5.4). Dropping a frame
   from a run is a failure.
5. State is checkpointable: serializable at a frame offset and restorable from
   one. Random access into a stateful stream — scrubbing across a long window —
   is restore the nearest snapshot and replay forward (Ch. 11). Never recompute
   from the beginning, and never fabricate a starting state. How often to
   snapshot is an engine tuning decision; *being* snapshottable is an operator
   contract, and it cannot be added later to operators written without it.

Forbids: a crop or a parameter change that makes the workspace slower than not
doing it, because some unnamed edge grew without bound.

## 4. One implementation, two trigger policies

Preview and run are the same operator graph under different completeness
policies. Preview triggers early on partial input and may be superseded; run
triggers once on complete input.

1. Trigger policy is engine configuration, not a branch inside an operator. An
   operator that asks "am I in preview?" is misfactored.
2. Any divergence between what preview shows and what a run produces is a bug
   of the highest class, because it silently breaks the user's contract (§6).
3. Sampling, downsampling, and proxy resolution are legitimate preview
   differences precisely because they are *keyed* differences (§1) — the
   preview is a different key, not different logic.

Forbids: the Lambda failure mode — the same logic maintained twice, drifting.
No event-time machinery is implied here: SIEVE has no watermarks, no late
arrivals, no accumulation modes. Only the trigger.

## 5. Edits are a log; everything else is a view over it

Parameter edits form an ordered, replayable log. The preview, the caches, the
provenance record, and the GUI are materialized views maintained over it.

1. Undo, cache invalidation, and provenance are one mechanism, not three. Undo
   is truncating the log; invalidation is diffing keys across log positions;
   provenance is the log itself.
2. The log is the pipeline spec. Saving and loading a pipeline is serializing
   the log, so a tuned pipeline is redeployable by construction.
3. Every edit must be representable as data and replay must be deterministic —
   the same requirement as §1.
4. Views may lag, and must say so. A stale view announces staleness rather
   than blocking the UI to stay current. "Working" and "stale" are display
   states, not exceptions.
5. No state that determines a result lives outside the log. Two categories sit
   outside it legitimately and are named rather than tolerated: view-local state
   (zoom, scroll, hover), which changes nothing computed, and machine-local
   preferences, which change what is *requested* but never what an artifact *is*.
   Anything else held only in a widget cannot be saved, undone, or reproduced,
   and is therefore not a feature.

Forbids: a god-object tab that is the sole owner of the current pipeline state.

## 6. The GUI is a contract, and it is generated

SIEVE's usefulness equals the user's knowledge of it: functionality not
reachable from the GUI does not exist. That is a product invariant, and it has
an architectural consequence.

1. Parameter controls are generated from the operator's declared I/O shape and
   parameter declarations (§2.1). They are not hand-written per filter.
2. Therefore an operator that declares a parameter gets a control for free. A
   hand-written bespoke panel means one of exactly two things: the operator's
   declaration is incomplete, or the semantic type it declares has no registered
   widget. The second is fixed by registering a widget, never by writing a
   panel.
3. Cost and progress surfaces read the same declarations the engine reads
   (§2.3, §7), so what the user is told about performance cannot drift from
   what the engine believes.
4. Widget classes are a bag, keyed by semantic type (§2.1). Direct manipulation
   — dragging a crop on the frame, editing a curve, picking a threshold off a
   histogram — is a widget class for a declared type, not an exception to
   generation. A rich control is a new member of that bag; it is never an
   operator-specific panel, because that is how one panel becomes the only place
   some state lives.

Forbids: capability that exists in the pipeline and is invisible in the
product, and the reverse — a control whose behavior the engine does not know
about.

## 7. Performance is stated against a load parameter

"Frame" is not a fixed unit once cropping and downsampling exist. The load
parameter is megapixels per second through *n* stages.

1. Two distinct questions get two distinct statistics, never one number:
   *responsiveness* is percentile latency on interactive paths; *feasibility*
   is a throughput estimate with an uncertainty interval, which is what "how
   long will this take on my laptop" actually asks for.
2. Percentile targets are stated against the named load parameter, per path.
   Latency is reported as percentiles, never as a mean. Throughput is a rate with
   an interval — a rate is a mean, and it is the right statistic for the question
   §7.1 calls feasibility.
3. Fan-out waits take the maximum, not the mean. Replicates are parallel tasks
   over one source, wall-clock is set by the largest, and per-task progress
   looks healthy right up until it doesn't. Straggler skew is the normal case,
   not an anomaly.
4. Every measurement is attributed to a machine profile. A number without the
   machine it was taken on is not a number.
5. Memory is a declared and measured dimension, not a footnote to time. Peak
   working set relative to input size belongs in the cost declaration, because
   exceeding it is what freezes an interface or ends a run on a smaller machine,
   and a time-only model reports health while that happens.

Forbids: performance claims that only hold on the author's machine, and
progress bars that lie by averaging.

## 8. Outputs carry a declared schema

Outputs are written with an explicit, versioned schema so another pipeline —
or another tool — can read them without reading our source.

1. The schema is declared, versioned, and written with the data. Readers
   validate; they do not infer.
2. An output whose consumer is unspecified is not designed. The shape of
   outputs sets the ceiling on extensibility, because downstream pipeline
   sections ingest them.
3. The requirement is schema and interop. Column orientation is an
   implementation detail with little to offer narrow fact tables; if a columnar
   container is chosen, it is chosen for its schema, not its compression.
4. A schema says what one value *is*, not only how wide it is: what it counts
   and per what unit. An operator that redefines its element — emitting a
   per-region value where its input was per-pixel — declares that; one that
   inherits its input's meaning declares that instead. There is no safe default,
   because the symptom of guessing wrong is a correct-looking number read under
   the wrong noun by whatever consumes it next. This is not in Kleppmann; it is
   closer to dimensional analysis.

Forbids: outputs that are only interpretable by the version of SIEVE that
wrote them.

## 9. Verification happens where the consumer reads

The end-to-end argument: correctness is checked at the point of consumption,
not promised at the point of writing.

1. An artifact is verified by reading it back through the same path a consumer
   would use. An encoder's success code is not evidence.
2. Tests assert on keyed artifacts and observable outputs, not on internals.
   This is what makes them survive refactoring — the thing they check is the
   thing §1 already guarantees is stable.
3. Golden fixtures are keyed like anything else (§1); a fixture that cannot be
   regenerated from its key is a liability.

Forbids: a test suite that has to be rewritten every time the internals move,
and artifacts trusted because the writer said so.

## 10. Scope

Out of scope, permanently: replication, consensus, distributed transactions
(Ch. 5–9). A design discussion reaching for these has gone wrong.

In scope only if SIEVE submits work off-box: partitioning and straggler
handling across nodes. The boundary is **one machine per run**, not one machine
ever — invariant 2 requires comparing a laptop against an HPC, and an
architecture that forbids running elsewhere cannot estimate running elsewhere.
Nothing in §§1–9 may assume the executing machine is the machine holding the
GUI.
