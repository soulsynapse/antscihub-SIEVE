# FINDINGS

Lessons from the second implementation, recorded so each conclusion can be
rederived without reading that tree again. Not a defect register: v2 is being
replaced, so a problem matters here only insofar as it generalizes into a rule the
third implementation must satisfy. Each entry states what was observed and where,
the lesson with v2's specifics stripped out, and the *class* of solution — the
shape of the fix, not the fix.

Entries are grouped by solution class, so one lesson often carries several
observations that turned out to want the same remedy. References are to the
pre-rewrite tree. Where v2 was right, that is recorded too; several of its
mechanisms should be carried forward rather than reinvented.

---

# Principles

The lessons below are instances of a smaller number of rules. Each of these is
derivable from at least two of them, and each is worth applying to a decision that
has no finding attached to it yet.

1. **Capability lives in the invocation protocol, not in the declarations.** If the
   call shape cannot express something, declaring it is a lie that stays hidden until
   something important needs it. Add axes as fields of one signature, never as new
   signatures. (1, 2)
2. **Everything that determines a value belongs in its key, and nothing else does.**
   Missing terms make different results collide; surplus terms — like the route taken
   to identical bytes — discard reuse the system was built to get. (3, 4)
3. **Key the hazard rather than forbid the capability it endangers.** v2's most
   expensive decision was making a whole class of operator uncacheable to compensate
   for one missing key term. (3)
4. **One declaration, many generated presentations.** Anything a human maintains in
   parallel with a declaration will drift, and a test that pins the copy against
   itself makes the drift pass. (13, 15, 18)
5. **One owner per contended resource, one entry point per capability.** Cores,
   memory, artifact writing, and orchestration each ended up with several owners, and
   in every case the second owner was added because the first was not reachable. (7,
   12, 17)
6. **Derived quantities are engine-owned and keyed; a component that computes owns a
   result it cannot share.** This is why boundaries, histograms, and completeness
   state ended up inside widgets. (6, 18)
7. **Answer "what changed" once.** Undo, invalidation, provenance, and view refresh
   are one question, and v2 answered it four times. (8)
8. **The interface must express everything the engine can, and nothing it cannot.**
   Capability the interface cannot author does not exist; capability it can author and
   the engine rejects is a broken promise. (14, 15, 16)
9. **State what is trustworthy, and verify where it is read.** Completeness boundaries
   and read-back checks are the same instinct: never let a consumer assume. (6, 12)
10. **An extension point needs a migration story, not just a version number.**
    Otherwise every addition either retains dead code forever or breaks saved work.
    (19)

---

# Part I — the operator contract and the data it produces

## 1. One invocation signature must cover every capability axis

*Observed, three ways.*

`backend/dispatch.py` defines three call protocols — `Kernel(frame, params)`,
`MergingKernel(frames_by_port, params)`, `StatefulKernel(frame, params, state)` —
policed by three decorators (`:146`, `:169`, `:193`). The fourth cell of the matrix
does not exist and says so: `:195` "no stateful merging protocol exists yet — the
filter that needs one should bring its signature." An operator cannot both carry
state and take two inputs.

`pipeline/executor.py:107-117` `_bind` refuses any node that is not
`Mode.STREAMING` ("one frame in, one frame out — a windowed filter needs a span")
or that is `rate_changing` ("no way to emit nothing for an input frame") — while
`filter_base` declares `Mode`, `rate_changing`, and `output_rate() -> Fraction`, and
`input_warmup_frames` already converts warmup across rate changes. Declared,
unimplemented.

Consequently `detect/detector.py:36` `detect(series, fps, settings, ...)` consumes
the **whole time series** outside the DAG: a Morlet CWT over the time axis
(`core/wavelet.py:77`), a windowed mean over cumulative sums
(`core/detection.py:29`), a gate, interval extraction. With
`DetectorSettings.centered`, `core/detection.py:16` `window_bounds` reads *future*
frames (`hi = t + (window - window//2)`), which no per-frame protocol can express.

*Lesson.* The kernel protocol is the real contract regardless of what declarations
say, and encoding each capability axis as its own signature multiplies the protocol
count — two axes already give four cells with one missing, and adding lookahead
windows and rate changes would give sixteen, most unwritten. Anything the protocol
cannot express gets built beside the pipeline, and what got built beside it was the
product's centerpiece. This is CHARTER 7.1c, and it is the single most likely way a
third implementation repeats the second.

*Solution class.* One invocation signature taking a context: inputs by port,
resolved parameters, a state handle, the range and offset being computed, execution
context. A new capability axis adds a field, never a protocol. Windows are declared
two-sided — history and lookahead. Admission rejects any operator the engine cannot
actually run, so declaration and capability cannot drift.

## 2. State needs a declared lifecycle, not a closure created at bind time

*Observed.* `backend/dispatch.py:61` `KernelBinding.start()` calls `state_factory()`
and returns `lambda frame, params: stateful(frame, params, state)`. The state is an
anonymous object captured in a closure at bind time; nothing can ask what offset it
corresponds to, serialize it, or restore one. `pipeline/executor.py:52` binds once
per `execute()` call, so state always begins fresh at whatever frame that run
started on.

*Lesson.* Checkpointing is not a missing feature of such a protocol, it is
unrepresentable — which is why every form of random access into a stateful stream
(scrubbing, resuming, replaying a range) was out of reach. Retrofitting is
impossible because the operators were written against a signature with nowhere to
put it.

*Solution class.* State is a first-class protocol participant with a declared
lifecycle: created at a named offset, snapshot to bytes, restored from bytes.
Snapshot *frequency* stays an engine decision; the operations belong in the contract
from the first operator.

## 3. Every input to a result is a key term, and nothing is made uncacheable to compensate

*Observed, four ways.*

`pipeline/plan.py:89-94` computes `lead_in_shortfall` and `warmed`, because near the
start of a source there is less history than an operator declared, and the run
proceeds anyway. `pipeline/cache_key.py:48` `node_key` includes none of it — not the
shortfall, the decode start, or the span. Frame N with full lead-in and frame N
computed cold share a key and differ in bytes.

`core/filter_base.py:250` `cacheable = deterministic and not stateful`;
`pipeline/cache_key.py:61` raises `NotCacheableError` for the rest;
`pipeline/dag.py:311` skips those nodes and `:293` skips any node whose parent was
skipped — so one stateful node leaves the **entire downstream graph unkeyed**. Five
of seven filters are stateful, so the cache is inert past the first one.

`backend/dispatch.py:90-95` shows the hazard was diagnosed exactly: a stateful
kernel whose spec omits `stateful=True` would let "dag.py give the node a cache key
and serve its output to a run that started somewhere else." The chosen defence was
to forbid caching for the whole class.

Conversely, `pipeline/resolve_source.py:47` puts *too much* in the key: when a
`CropArtifact` backs a replicate the source key becomes that file's
`source_identity` instead of the parent plus ROI, so the same frames key differently
depending on whether an optimization has run. Pixels do agree — crops are written
lossless (`storage/crop_writer.py:37` `write_ffv1`), which was deliberate — so the
cost is a discarded cache rather than a wrong answer.

Also relevant: `backend/identity.py:18` `backend_identity` names the numpy version
and a policy integer, but not the BLAS/LAPACK build, thread count, or SIMD path —
the things that actually decide whether a threaded reduction reproduces bitwise. A
version string is not a determinism guarantee.

*Lesson.* Defining derived data as one frame forces a choice between carrying state
and caching anything, and every serious filter carries state. Where a result depends
on something — start offset, history actually supplied, determinism class — the cheap
fix is to name it in the key; forbidding the capability is what compounds, and v2's
conservative choice cost it the whole cache. The converse rule matters equally: a key
names *what an artifact is*, never *how it was obtained*, or a cheaper route to
identical bytes invalidates everything it was meant to help.

*Solution class.* The artifact is a frame *range* plus the state it began from, with
the start offset and the supplied history in the key (ARCHITECTURE §1.6). Shortfall
is legal at a source boundary and keyed there — this corrects §3.1, which currently
makes it an error. Determinism is declared rather than inferred from versions. Path
of derivation goes to provenance, not identity.

## 4. Identity that names the machine cannot leave it

*Observed.* `pipeline/cache_key.py:34` `source_identity` is the resolved absolute
POSIX path plus size and mtime. `SourceRef`/`Project` store *relative* paths and
support `relocated()` (`core/pipeline_model.py:76`, `:448`), so v2's spec is portable
while its cache is not.

*Lesson.* Portability of derived data is decided once, by the identity function, and
nothing downstream recovers it. A spec that relocates cleanly proves nothing about
the artifacts keyed off it.

*Solution class.* Content-derived, or at minimum path-independent, source identity —
required for ARCHITECTURE §10 and the off-box half of Phase 5.

## 5. Frame index is a pure function of the source only if the decoder guarantees it

*Observed.* `decode/reader.py:86` `_position_at` grabs forward for deltas up to
`GRAB_FORWARD_LIMIT = 40`, else `capture.set(cv2.CAP_PROP_POS_FRAMES, index)`.
OpenCV's frame-accurate seek is unreliable for some container/codec combinations, so
pixels for index N may depend on how the decoder reached N. `decode/identity.py:12`
`decoder_identity` captures the OpenCV version and a policy integer, not the seek
path. Whether v2's sources actually seek exactly is untested here — the point is that
nothing establishes it.

*Lesson.* Every key rests on "frame N of source S is a fixed array." That is an
assumption about a third-party decoder, not a property of the design, and it is
cheap to test and expensive to discover late.

*Solution class.* Frame-exactness is a source-layer obligation verified by test
before any key schema is committed: read a range sequentially, read the same indices
after seeks, compare bytes. If it fails, the source layer owes an index built at open
time or a decoder that guarantees exactness. The fixture for this already exists —
see the mechanisms section.

## 6. A derived view must report what it is and how complete it is

*Observed.* `detect/detector.py:70` `settled_for(..., final: bool)` returns, when not
final, `min(settled_after_coi, settled_after_window)` — how much of the trailing
series is trustworthy given wavelet cone-of-influence and a possibly centered window
— and `:82` `gate_to` truncates the gate to that settled prefix. Separately,
`gui/player.py` displays a frame from either the render ring (`_display_from_ring`,
pipeline output) or the proxy/decode path (`_display_cached`), chosen at runtime by
`render_fed`/`set_render_filling`, with `is_scrub_degraded` as separate state, and
nothing in the frame records which path produced it (`core/types.py:120` `Frame` is
data, index, channels — no identity).

*Lesson.* v2 worked out the settled-prefix boundary itself and computed it rather
than hiding it, which is right and follows from any lookahead window rather than
being a detector quirk. What it lacks is the other half: the same viewport shows
filtered output or raw decode depending on availability, and the user cannot tell
which. With more views and more feed paths, provenance of what is on screen becomes
a correctness property.

*Solution class.* A derived view reports both the key of the artifact it is showing
and its settled boundary. This restores provisional-versus-settled to ARCHITECTURE §4
— without event-time machinery, since watermarks and out-of-order arrival still have
no referent here — and extends §5.4 from freshness to identity.

## 7. One owner per contended resource, with named budgets against one pool

*Observed, in cores and in memory.*

Cores: four independent interface threads, one per concern
(`gui/preview_runner.py:304`, `gui/detector_worker.py:140`, `gui/decode_worker.py`,
`gui/materialize_worker.py`). Inside them the detector takes all cores
(`core/wavelet.py:127`, `ThreadPoolExecutor` at `:162`), decode opens 2–4 readers and
threads them (`decode/prefetch.py:21` `resolve_workers`, reading `core/machine.py:27`
`available_cpus`), and filter execution is single-threaded per frame
(`pipeline/executor.py:54`). Allocation is static: `core/shares.py:8-14`
`PLAYER_WORKERS=1`, `PREVIEW_WORKERS=2`, `DETECTOR_WORKERS=2`.

Memory: three caches with incompatible properties. `pipeline/cache.py:15`
`MemoryFrameStore` is an unbounded dict keyed `(key, index)` holding numpy frames;
`gui/proxy_cache.py:11` `ProxyFrameCache` is byte-capped LRU keyed by **index alone**
holding `QImage`; `gui/render_ring.py:22` `RenderFrameRing` wraps the latter with a
budget from `core/shares.py` `RENDER_RING_SHARE`. The only caches with eviction are
interface-side, keyed without reference to what produced the frame, holding
interface-native images no engine can reuse.

*Lesson.* "The engine decides placement" needs a component that *is* the engine and a
rule that nothing else may probe capability; absent both, policy distributes itself
across whoever needed a thread or a cache, and the result is a static split tuned to
one machine — the fragility CHARTER names. Each new consumer brings its own pool, so
N consumers means no global bound in either resource.

*Solution class.* One scheduler owning cores and one artifact store owning memory,
with capability probes reachable only from the engine (ARCHITECTURE §2.2 has no
enforcement point today). The store takes uniform keys and backend-neutral arrays,
with a byte budget and eviction. Keep the *shape* of `shares.py` — named shares with a
floor and a fraction of what is actually available — but as budgets against one pool
rather than separate pools.

## 8. One log with transactions; undo, invalidation, provenance and refresh are reads of it

*Observed, four mechanisms for one question.*

`gui/history.py:14` writes whole `Project` snapshots per step, `SNAPSHOT_LIMIT = 50`.
`gui/commands.py` is one `QUndoCommand` subclass per editable thing —
`AddReplicate`, `RemoveReplicate`, `RenameReplicate`, `SetReplicateROI`,
`SetReplicateROIs`, `EditTuningParams`, `EditDetector`, `ResetTuning`, `SetClip` —
each with a hand-written `redo`/`undo` pair and several with `id()`/`mergeWith()`
coalescing. `gui/document.py:65` `_Gesture` and `:424` `finish_roi_gesture` exist so
one drag is one undo step, with `:343` `_would_change` suppressing no-ops. And
`gui/document.py:71` `ReplicateDocument` broadcasts twelve distinct change signals —
structure, replicate, grouping, clip, source, tuning, detector, pipeline, crops,
selection, added, refused — each consumer subscribing selectively and deciding for
itself what to recompute.

*Lesson.* Undo, invalidation, provenance, and view refresh are one question — what
changed between two states — answered four times. Snapshots answer it only for the
newest pair; hand-written inverses make correctness a per-feature obligation that
fails silently when wrong; broadcast signalling costs (change kinds × view types),
which is much of why one tab reached 1629 lines. All three costs grow exactly where
v3 intends to grow.

*Solution class.* An ordered edit log with transaction boundaries opened and closed by
the interaction, keys derived from log positions, and key-diffing between positions.
Undo is truncation plus replay, so no inverse is ever written; invalidation is the
diff; provenance is the log; a view declares the keys it depends on and the diff says
whether it must recompute — a cost that does not grow with view count.

One caveat the log must accommodate: `gui/preferences.py` reads machine-local
settings from `QSettings` (`adaptive_scrub`, `coarse_interval_seconds`) that change
*which* frames get requested without changing what any frame *is*. That is a
legitimate third category — machine-local, affects scheduling, never a key term — and
it should be named as such so it does not drift into either the spec or a key.

## 9. A machine is not one number, and available memory is not physical memory

*Observed.* `core/machine.py` reads CPU affinity, per-CPU efficiency classes (Windows
`GetSystemCpuSetInformation`, Linux `cpu_capacity`), cgroup v1/v2 memory limits, and
SLURM `SLURM_MEM_PER_NODE` / `SLURM_MEM_PER_CPU`.

*Lesson.* v2 is ahead of the plan here, and it settles two things a cost model must
accommodate from the start: heterogeneous cores mean cost and placement need
per-core-class terms, and on a scheduler-managed machine the ceiling is an allocation,
not the hardware.

*Solution class.* Portable machine descriptor with per-core-class capacity and a
memory *budget* rather than a memory size, with ARCHITECTURE §7.5 stated against the
budget. Carry this module's substance forward.

## 10. Responsiveness is best specified as named interactions with deadlines

*Observed.* `bench/budgets.py:31` defines twelve named budgets with millisecond
ceilings — `open_to_first_frame` 500, `scrub_to_repaint` 100, `slider_to_preview` 100,
`knob_to_graphs` 3000, and others — split into `PRE_PIPELINE` and `IN_PIPELINE`
regimes, published through `bench/metrics.py` `MetricBus`, with `IN_DEBT`
(`budgets.py:133`) recording accepted misses and why in prose.
`pipeline/preview.py:23` measures two of them around the real render path.
`bench/metrics.py:88` reports median and worst with no percentile between.

*Lesson.* This is the link between "measure speed" and "the interface is the product":
responsiveness stated as user-visible interactions with deadlines is testable before
any interface exists, and a debt register keeps an accepted miss honest instead of
silent. The flaw is only that ceilings are absolute milliseconds on one reference
workstation.

*Solution class.* Keep the interaction table and the debt register; re-express each
ceiling as a percentile against a load parameter, per machine profile
(ARCHITECTURE §7).

## 11. Fan-out units may differ from each other, so cost is per task

*Observed.* `core/replicates.py:30` `Replicate` carries an ROI *and* per-node
parameter overrides *and* detector pins, merged by `core/pipeline_model.py:165`
`resolved_params`. Keying accounts for this; cost does not.

*Lesson.* Parallel tasks over one source are not necessarily the same computation at
different coordinates. When each carries its own parameter overlay, cost varies per
task by construction, so straggler skew is not only data skew.

*Solution class.* Cost and scheduling computed per task from that task's resolved
parameters, never one estimate scaled by task count.

## 12. One artifact-writing facility, with read-back verification

*Observed.* `detect/tables.py:339` writes a table, re-reads the file, and compares
every row to what was written, raising `TableVerificationError`. Independently,
`pipeline/materialize.py:120` `_verify` tees the frames fed to the encoder (`:91`),
re-reads the written artifact, and compares content digests (`:148` `_digest`),
raising `CropVerificationError` — staging through a `.part` file and taking a
`cancelled()` callback.

*Lesson.* Two unrelated parts of the codebase arrived at the same mechanism — write,
read back, compare, then commit — which is the end-to-end argument discovered twice by
necessity. That it was built twice is the ORGANIZATION §7 case in miniature: no bag
owned "write an artifact," so each caller built the whole discipline itself, and the
two differ in strength (full-content compare versus digest) and in error quality.

*Solution class.* One facility owning temp staging, read-back verification, digest
comparison, cancellation, and atomic commit. Every writer gets it; no writer
reimplements it.

## 13. Unit-bearing names belong in the declaration; a prose schema is half a schema

*Observed.* `detect/tables.py:76` `series_columns(element)` derives column *names*
from the declared `ElementKind` — `f"{element.value}s_total"` becomes `pixels_total`
or `blocks_total` — and each `Column` carries a `meaning` string. `write_tables`
(`:174`) generates a `README.md` documenting every column. The data itself is
stringly-typed CSV with fixed decimals and `NA` sentinels, and the schema exists only
as prose in that README.

*Lesson.* The semantic half is right and worth copying outright: the noun in the
output derives from the operator's declared element rather than being typed by hand,
which is ARCHITECTURE §8.4 implemented. What is missing is machine-checkability — a
consumer can read the file but cannot validate against a declaration.

*Solution class.* One declaration — column, unit derived from the element, meaning —
emitting both a machine-readable schema beside the data and the human README. Readers
validate against the former; the latter is generated, never written.

---

# Part II — lessons for an interface that gets *more* capable

v3's workflow is intended to be richer than v2's. These are the places where v2's
division of labour would make that combinatorially expensive rather than merely
larger.

## 14. The authoring surface must be as expressive as the engine

*Observed.* `gui/chain_model.py:87` `runnable_prefix` builds edges with
`itertools.pairwise` — a path, never a branch — while `Pipeline`/`Dag` support
branching, named multi-input ports, merges, and fan-out (`pipeline/dag.py:168` even
has a message for a merging filter used as a root).

*Lesson.* v2's engine could express more than its interface could author, so the extra
capability might as well not have existed — CHARTER invariant 3 from the other
direction. A richer workflow needs branching immediately: one preprocessing chain
feeding both a detector and a visualization, or two variants compared side by side.

*Solution class.* Graph-shaped authoring from the start, with affordance rules defined
over a graph rather than a sequence. Must be solved together with 15, whose checker
threads a single type through a loop and has no DAG analogue.

## 15. One type system, two presentations — and a test that pins a duplicate certifies drift

*Observed.* The engine checks edges via `ArraySpec.admits`/`TableSpec.admits` and
propagates `ElementKind` (`pipeline/dag.py:201`, `:215`), raising `EdgeTypeError`. The
interface checks the same property independently with `ChainKind` = IMAGE /
BLOCK_SERIES / EVENTS graded by `gui/chain_model.py:66` `grade()`, yielding OK /
CONFLICT / UNREACHED and messages like "expects block series, receiving image".
`gui/chain_model.py:36` `Stage` (spatial prep / extraction / temporal filter /
detection) is a placement taxonomy existing only in the interface that decides what
the user may add where. `ChainKind.EVENTS` has no counterpart in the contract, because
events come from the detector and the detector is not in the DAG (finding 1).

`gui/wizard_model.py:84` `catalog()` calls `discover()` and then returns a
hand-written tuple of `CatalogEntry`, each duplicating title, stage,
`kind_in`/`kind_out`, blurb, `hidden_params`, `repeatable`. `morlet_band` and
`windowed_count` appear there with hand-written `Guidance` in `:53`
`_TAB_SIDE_GUIDANCE`, because they are detector stages with no spec to read from.

And `tests/unit/test_chain_model.py:173-174` asserts the hand-written kinds
(`normalize` is IMAGE→IMAGE, `block_signal` is IMAGE→BLOCK_SERIES) against the
interface's own catalog — pinning the duplicate rather than tying it to `ArraySpec` or
`ElementKind`.

*Lesson.* Two validators for one property, with nothing forcing agreement, produce
either a false conflict shown to the user or a chain the interface permits and the
engine rejects — and a test that asserts the duplicate against itself makes drift
*pass*, which is worse than leaving it untested. Generation must cover more than
widgets: with stage, connectivity, blurb, and guidance living in the interface, adding
an operator means editing the interface, and every added stage or kind multiplies the
divergence surface.

*Solution class.* Connectivity kind, placement, guidance, and the
reason-it-cannot-go-here message all derived from declared I/O and declared
operator metadata, validated at registration — so the interface's affordances and the
engine's admission are one check with two presentations, and the catalog is generated.

Two halves of this already work and only need joining. `filters/*.md` sidecars via
`filters/__init__.py:23` `guidance_path()` carry the prose, with `Guidance`
(`wizard_model.py:46`) as their de facto schema — summary, when to use, what it does
not do, cost. And `cli/inspect_cmd.py:111` `_parameters` already describes a filter's
parameters by reading `spec.params_model.model_json_schema()`, with `_guidance`
(`:135`) reading the sidecar — so one surface generates its whole presentation from
declarations while the other hand-maintains a catalog. The generator Phase 8 needs has
a working precedent in the CLI.

## 16. Incomplete and invalid graphs are normal states, not errors

*Observed.* `runnable_prefix` truncates at the first step that is not `Status.OK`, so
the interface runs the valid prefix of a chain the user is midway through building.

*Lesson.* Interactive authoring means the spec is invalid much of the time it is being
edited, and useful work still happens on the valid part. A batch-shaped architecture
treats this as an error and forces the interface to hide it.

*Solution class.* An edit that invalidates the graph is a legal log entry; the engine
executes the valid subgraph and reports what is unreached. Belongs in ARCHITECTURE §1
and §5.

## 17. One engine entry point, taking prioritized and deadlined requests

*Observed, three ways.*

`gui/coalescer.py` `RequestCoalescer` is good work: request kinds EXACT / SCRUB /
PLAYBACK with priority (`_outranks`), one in-flight and one pending, `generation`
counters marking superseded results stale, sequence numbers preventing an
out-of-order frame from painting. It is ARCHITECTURE §3.4's shedding, implemented in
the interface, for one view. `gui/player.py:230` `timerEvent` computes the target
index as `anchor + int(elapsed * fps * rate)`, so playback follows the clock and skips
frames it could not produce in time — a correctly built deadline-driven consumer.

Scrubbing is served by raw decode at a fixed reduced width (`gui/decode_worker.py`
`PROXY_WIDTH`, cached in the render ring), bypassing the pipeline entirely.

And there is no single "run this" entry point at all: `cli/run_cmd.py` assembles
`discover` → `Dag.build` → `resolve` → `ExecutionPlan.build` → `frame_source` →
`execute` with its own cache choice and span defaults (`cli/common.py:51` `span_for`),
while the interface assembles the same sequence independently through
`PreviewSession` and its workers. `detect` is a third assembly, as its own CLI
command.

*Lesson.* The policies are right and the placement is wrong. Several simultaneous
views each get a coalescer with one slot, and N of them compete for one engine with no
arbitration — the resource-hog failure from a new direction, worsening with every view
v3 adds. A private fast path is a path the engine cannot schedule and nothing can
reuse. And every surface that re-derives the orchestration can get it subtly
different, which is why a third surface (batch, or off-box submit) would be a third
variant.

*Solution class.* One engine entry point taking a spec and a request, where requests
carry priority, deadline, and a shed-or-wait disposition, and the engine arbitrates
them — §3.3's per-edge policy generalized to per-request admission control. Surfaces
pass requests and never assemble stages. Proxy generation is a keyed operator served
like any other request, at a declared reduced resolution. Carry v2's request kinds,
generation semantics, and clock-anchored playback into it.

## 18. Whatever the interface computes, the interface ends up owning

*Observed.* `gui/filter_tab.py` has 691 `self._` references; its `__init__` owns the
player, document, runner, metrics, preferences, chain, defaults, series collector,
playhead, detector runner, materializer — and `_filled`, `_settled`, `_series_final`,
`_partial_published`. The settled boundary from finding 6 is a property of the
computation living in a widget. `filter_tab.py:119` `parity_chain(30.0)` bakes a
source frame rate into interface defaults.

Views compute as well as own: `gui/density_plot.py:32` and `:54` build a histogram
surface from raw band power inside the widget, with its own bin count. The plots
themselves take plain arrays and scalars rather than detector types
(`set_series(band_power, ...)`, `set_power(power, freqs, fps)`), which is the right
decoupling — but a quantity derived inside a view cannot be keyed, cached, or reused,
so a second view wanting the same surface computes it again.

*Lesson.* A god object is a symptom. State lands in the widget that first needed it
and nothing pulls it back out, so the tab accretes every derived quantity the engine
declined to own — and every derivation performed in a view is one the engine cannot
schedule or share. Both costs scale with view count.

*Solution class.* Every derived quantity — completeness boundaries, histograms,
aggregates — is an engine-owned keyed artifact that views read; the interface holds
nothing absent from the log (ARCHITECTURE §5.5), enforced by generation (§6) rather
than discipline. Views retain only view state: zoom, selection, scroll.

---

# Part III — what the extension points cost

These come from asking what it would take to add a capability rather than from
anything v2 got wrong. They are the places where the current shapes stop generalizing.

## 19. Version pinning without migration forces dead code or dead projects

*Observed.* `core/filter_registry.py` keys specs by `(filter_id, version)` and offers
`versions()` and `latest()`, so several versions of one filter can coexist —
deliberately. Projects pin exact versions (`Node.version`, resolved by
`registry.get(id, version)`, raising `UnresolvedFilterError` when absent), and the node
key includes the version, so a params change *must* bump the version to invalidate
caches correctly. But the spec is attached to its params class
(`filter_registry.py:118` `params_model.__filter_spec__`) and kernels bind to that
class, so keeping version 1.0.0 resolvable means keeping its params class and every
kernel in the tree indefinitely. Nothing declares that a newer version supersedes an
older one or how to convert parameters between them. Separately,
`core/pipeline_model.py:369` `_readable` refuses a project whose `schema_version`
exceeds the build's, and normalizes anything older to current — so older projects are
read as though current, which is right for additive changes with defaults and silent
if a field's meaning ever changed.

*Lesson.* Multi-version coexistence without migration leaves two options: retain every
version's code forever, or break saved work. Versions will churn precisely because
keys depend on them, so this decides itself early and badly. The same gap exists at
the project level, where old files are reinterpreted rather than migrated.

*Solution class.* Declared migrations as part of the extension point: a version states
whether it supersedes an earlier one and, if so, the parameter conversion — so a
project can be upgraded in place and retired code can actually be removed. Project
schema changes carry the same obligation. This is the schema-evolution argument
(Kleppmann Ch. 4) applied to operators, which ARCHITECTURE currently invokes only for
outputs.

## 20. Region and element addressing must be declared, not assumed rectangular

*Observed.* `core/types.py:23` `ROI` is x/y/width/height and `crop(array)` is an array
slice. Crop artifacts are rectangles, and matching a crop to a replicate is rectangle
logic (`gui/crop_binding.py:127` `_overlaps`, `:74` `_near_miss`, `:106` `_orphan_for`).
On the element side, `ElementKind` is PIXEL or BLOCK, and the composite view hit-tests
by assuming a uniform grid (`gui/composite_view.py:138` `block_at`, `:131`
`grid_edges`), while plots index elements by column position.

*Lesson.* Rectangles and uniform grids are baked into three unrelated layers — the
source crop, the artifact-matching logic, and every view that maps a click to an
element. Any irregular region (a mask, a polygon, an arena that is not a box) or any
irregular element (a segment, a tracked object, a detection treated as an element)
breaks all three at once, and none of them can be fixed independently.

*Solution class.* Elements and regions carry a declared addressing descriptor: how to
map an element index to a source region and back, and how to test a point against it.
Views hit-test through the declaration rather than recomputing a grid; the source layer
takes a region descriptor rather than a rectangle. Rectangles and grids become the
common case of a general facility, not the assumption underneath it.

## 21. Intervals and events are outputs, not data the system holds

*Observed.* Intervals exist as `DetectorUpdate.intervals`
(`detect/detector.py:32`), derived by `gate_intervals`, and reach the world as CSV rows
(`detect/tables.py` `INTERVAL_COLUMNS`). `gui/timeline_model.py` has geometry for
frames and windows — `Geometry.x_of_frame`, `frame_at`, `span`, `feed_bounds` — and no
representation of an interval, an annotation, or a track. Nothing in `Project` holds
events.

*Lesson.* Events are terminal in v2: computed, exported, never held or edited. Anything
that treats an interval as *input* — a manual label, imported ground truth, a
comparison between a detector's output and a human's, several event tracks over one
source — has nowhere to live, and the timeline that would display them has no concept
of them.

*Solution class.* Intervals as a first-class artifact type with a declared schema
(finding 13), holdable in the spec when authored and keyed when derived, and a timeline
model that renders tracks of them regardless of origin. This is the precondition for
labelling, ground-truth comparison, and any detector evaluation — none of which is
reachable while events are only ever a CSV.

---

## Mechanisms worth carrying forward

`bench/sweep.py` builds a factorial design over core sets and worker counts:
`class_core_sets` derives sets *per CPU efficiency class*, `design(cores, workers)`
enumerates cells, `_pin` sets affinity per cell, `Reading.best/typical` summarizes,
`curvature` characterizes the response. Most of the measurement apparatus finding 9
implies, already built and already aware a machine is heterogeneous.

`gui/resource_probe.py:36` `ResourceSample.over_ledger` compares measured process
memory against the declared share ledger on a timer — a real closed loop between
declared budget and actual use, which is what ARCHITECTURE §7.5 needs.

`bench/retention_trace.py` records cache access events (`PUT`, `AccessEvent`,
`TraceRecorder`, playhead-relative), so an eviction policy can be chosen from
recorded behaviour rather than argued about — the instrument for tuning the unified
store in finding 7.

`tests/conftest.py` states a rule worth keeping verbatim: synthetic fixtures rather
than committed or downloaded media, because "a fixture that has to be downloaded is a
fixture that gets skipped, and a decoder test that skips is indistinguishable from one
that passes." Its synthetic video makes frame *n* a solid field of intensity `n * 5`,
so a test can assert **which** frame a seek landed on — the instrument finding 5
requires, already built. It also pins `QT_QPA_PLATFORM=offscreen` so a local run is the
same run as CI.

`cli/app.py:23-28` exposes `inspect`, `run`, `preview`, `materialize`, `detect`,
`sweep` — a shape for PLAN Phase 3's interim surface, with the caveat from finding 17
that each command assembles its own orchestration.

## Starting condition, not a lesson

`pipeline/__init__.py`, `storage/__init__.py`, `backend/__init__.py`, and
`gui/__init__.py` are one line each — no purpose line, no exports, so
ORGANIZATION §4.4 would fail on most of the tree. `bench/metrics.py:112`
`METRICS = MetricBus()` is module-level mutable global state that both the engine and
the interface publish into.
