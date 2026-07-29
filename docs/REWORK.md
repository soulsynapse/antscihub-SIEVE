---
status: current
reviewed: 1793950
subjects:
  - src/sieve/core/filter_base.py
  - src/sieve/backend/dispatch.py
  - src/sieve/pipeline/executor.py
  - src/sieve/pipeline/dag.py
  - src/sieve/gui/chain_model.py
  - src/sieve/gui/detector_worker.py
  - src/sieve/bench/budgets.py
  - .importlinter
---

# REWORK — everything that touches the footage is a filter

Written 2026-07-28, from a session that took
`docs/todo/gui-cli-execution-parity.md` and found that the item, the guardrail it
came from, and the rule both of them serve were all aimed one level below the
thing that is wrong.

**The thesis:** the *executor* can run exactly one kind of filter — a frame in, a
frame out, `Mode.STREAMING` — so every transform that does anything else was built
outside it. "Outside the executor" has no home in the eight rules, so each such
transform grew a private home in the artifact, the commands, the GUI, and the CLI.

The special cases are not decisions anybody made. They are residue.

Sections 1–5 are the diagnosis. §6 is the membership criterion everything after it
applies. §7–§11 are the five pieces of work the diagnosis collapses into. This
document is `current`, not `record`: it asserts file-and-line facts, several of
which were wrong within a day of first writing (§14), and it is meant to be
corrected rather than preserved.

---

## 1. The mechanism

**The contract is not too narrow. The executor is.** The vocabulary is nearly
complete and almost none of it can run.

| Declarable today | Where | What runs it |
|---|---|---|
| `Mode.WINDOWED` | `core/filter_base.py:85` | Nothing — `pipeline/executor.py:309-313` refuses it by name |
| `rate_changing` | `core/filter_base.py:493` | Nothing — `pipeline/executor.py:314-318` refuses it by name |
| `emits=TableSpec(...)` | `core/filter_base.py:370-402` | Nothing, **and nothing refuses it** |
| More than one output | not declarable | `core/filter_base.py:412-418` calls the `emits` half "deliberately unbuilt" |

The third row is the worst. `_bind` at `pipeline/executor.py:306-322` checks `mode`
and `rate_changing` and never looks at `emits`, so a table emitter gets no named
refusal the way the other two do. It fails instead at the author's desk, because
`Kernel`, `MergingKernel`, and `StatefulKernel` all return `Frame`
(`backend/dispatch.py:78`, `:104`, `:123`) — there is no protocol a table-emitting
kernel can be written against. A spec field that can be filled in with no
implementable kernel and no error message is worse than one that is absent.

The `rate_changing` arithmetic is fully built and entirely unreachable.
`ParamsBase.output_rate` returning an exact `Fraction` (`:258-277`),
`input_warmup_frames` (`:720`), `source_warmup_frames` (`:758`), and the
monotonicity argument that lets a DAG walk avoid enumerating paths — all careful,
all reachable by no filter. Zero of the seven shipped filters declare
`rate_changing`, zero declare `WINDOWED`, zero emit a table.

**The trigger everyone is waiting for already fired inside `filters/`.**
`docs/todo/kernel-protocol-beyond-one-frame.md` is gated on "a filter that actually
needs one," and `src/sieve/filters/motion_history.py:69` says in its own docstring
that what it wants is "`Mode.WINDOWED` and a kernel protocol that does not exist."

---

## 2. Why the rules did not catch it

Two gaps that compose. Neither is a case of a rule being wrong.

**Rule 1 is scoped to the word *frame*.** "`pipeline/executor.execute` is the only
thing that computes a frame." A `(T, B)` series is not a frame, so nothing about
computing one is governed. The most expensive computation in the tuning loop runs
outside the one execution path, in full compliance with the rule protecting the one
execution path.

**`.importlinter` governs direction of dependency, not location of computation.**
`gui` sits above `core`, so `gui/detector_worker.py` importing `morlet_power` from
`core/wavelet.py`, and `gui/chain_model.py` importing `detect` from `sieve.detect`,
are legal under all four contracts. The layer contract has no vocabulary for "this
module may not *perform* a transform," only for "this module may not *reach* that
one."

This surfaced once and was diagnosed one level too shallow.
`docs/AUTO-GUARDRAILS.md` §7 records that the concurrency sum test "passed for the
whole time `gui/filter_tab.py` was running a full Morlet transform over every core
on the GUI thread." The fix — make `workers` a required argument — was correct and
stopped the starvation. Nobody asked why a transform was running in a widget,
because no rule names placement.

`docs/AUTO-GUARDRAILS.md` §2 is misfiled for the same reason. Rule 1 *is* enforced:
`execute` has exactly three call sites (`cli/run_cmd.py:204`,
`cli/detect_cmd.py:266`, `pipeline/preview.py:378`). The unchecked guardrail is not
the loop. It is everything on either side of the loop.

---

## 3. What the residue costs

Every row is a facility a node has and a non-node had to forge.

| Site | What it is |
|---|---|
| `gui/chain_model.py:174-253` | `DetectorState`, a second representation of `DetectorSettings`, with the field list hand-typed twice — `:218-224` and `:246-253` |
| `gui/chain_model.py:208` vs `core/pipeline_model.py:316-324` | Two spellings of one documented default that disagree: at `fps=0` the GUI's is `1`, the artifact's is `30` |
| `pipeline/cache_key.py`, `pipeline/plan.py` | Zero references to `DetectorSettings`. The values deciding what is claimed as an event are in no key |
| `cli/detect_cmd.py:4-5` | Asserts the detector is "hashed into what the run is." It is not |
| `gui/filter_tab.py` `reuse_band_power` | A one-boolean hand-rolled cache, standing in for what `cache_key.py` does generically, and unable to do better because there is no key |
| `gui/chain_model.py` `ChainKind` | A **redundant** reimplementation of a type system the contract already has — §14, correction 3 |
| `gui/detector_worker.py:161-173` | `settled_for` / `gate_to`. Rule 6's frontier implemented **only** in the GUI |
| `gui/detector_worker.py:171-183` | `derive` returns results (`update`, `settled`) and presentations (`pooled_power`, `density`, `density_ms`) from one function |
| `cli/detect_cmd.py:300` vs `gui/detector_worker.py:155` | The same `detect` reached with `ALL_CORES` on one side and `resolve_worker_split().detector` on the other |
| `pipeline/executor.py:144-154` | `FrameResult.source` and `source_cropped` — two fields existing only because the crop is a special case |
| `cli/run_cmd.py:227-247` | The baseline as `replicate=None`, propagating `Replicate \| None` through `ExecutionPlan.build`, `plan.replicate`, `resolved_params`, `resolved_detector`, `_target`, `_targets`, `_label` |
| `core/filter_base.py:524` | `primary_params` — GUI presentation policy declared in `core/`, which may not import Qt |
| `core/filter_base.py:441-445` | `CostEstimate.seconds_per_megapixel` — a hand-typed constant "on the reference CPU," consumed only by `cli/inspect_cmd.py`, which prints it |
| `gui/chain_model.py` `caption_for`, `SIGNAL_LABELS` | A switch on `filter_id` and a hand-typed label map, in a widget — the enumeration rule 3 forbids |

The detector is not a corner of the app. Twenty-two modules reference it, and
fifteen of the twenty-six files in `docs/todo/` name it, including both items under
aspiration A3 — and A3 is "SIEVE navigates the parameter space itself," which needs
that space **enumerable**. An optimizer reading `DetectorSettings.model_fields` and
a GUI reading a hand-typed list of five names are searching two different spaces.

---

## 4. The deadlock

`docs/todo/the-gui-holds-the-filter-enumeration.md` is gated on "the temporal chain
becoming real nodes — two of the five enumerated steps have no filter module to be
discovered *from*." Those two steps are the detector.
`docs/todo/kernel-protocol-beyond-one-frame.md` is gated on "a filter that actually
needs one." Each item's trigger names the other item's blocker.

Naming it as a deadlock is the unlock: write the protocol against the detector as
its motivating case rather than waiting for a filter that by construction cannot
appear.

`backend/dispatch.py:74-75` cautions against inventing a signature before a filter
needs one. That caution has already been tested and discharged here:
`MergingKernel` at `:81-104` is "the second signature `Kernel`'s docstring declined
to invent early, arrived with the filter class that needs it," and adding it proved
additive — `Kernel` and `MergingKernel` coexist, and `_bind` dispatches on
`input_ports` length. Protocols here extend; they do not lock. Four consumers are
waiting: a decimator for `rate_changing`, a coordinate-emitting detector for
`TableSpec` in `docs/todo/sink-writers.md`, `flow_direction`'s circular signal in
`docs/todo/block-signal-free-measures.md`, and `motion_history.py:69`.

---

## 5. What everything is

Four buckets, and everything is in exactly one.

**A filter.** Anything that takes the decoded footage, or anything derived from it,
and emits a product. Crop is a filter. The span is a filter. The Morlet temporal
step is a filter. Detection is a filter. A filter declares what it consumes and
what it emits, lives in one module with one markdown beside it, is discovered
automatically, has its parameters hashed into identity, dispatches per backend,
caches, and refuses up front.

**Settings.** A value that changes what a result *is*. Every one is a parameter of
some filter, resolved per replicate through `Replicate.overrides`, merged in
exactly one place.

**Output.** A product a filter emitted, together with what is derived from it *for
drawing only*. The test for the second half is whether anything downstream depends
on the value. The moment anything exports, stores, keys on, or cites it, it is a
product and must be a filter.

**View state.** Where the user is looking. `core/pipeline_model.py`'s module
docstring already names this bucket and its members: "anything about *looking* —
the soloed block, the playhead." Never saved, never hashed, never an input to a
result. Without this bucket the trichotomy forces view state into settings, which
is how `DetectorState` came to carry `solo_block` beside five values that decide
what is claimed as an event.

**"No crop" is still crop.** An identity crop is a full-frame ROI, not a `None`.
The baseline stops being `replicate=None` and becomes a replicate whose ROI is the
whole frame, and `Replicate | None` collapses out of every consumer in §3.

**The span is a filter; the decode range is an optimization.** Which frames are in
the answer is *what the result is*; pushing the predicate down to the reader is
*how fast it arrives*. `ExecutionPlan` already performs this pushdown —
`decode_range` is the span widened by `lead_in`.

---

## 6. What belongs in core

**The criterion: would two independent implementations have to agree on this to
interoperate, or is sharing merely convenient?**

Purity is a consequence, not the test. A vocabulary item that needed a codec would
force every layer that speaks it to require a codec — which is *why* the
declarations in `core/filter_base.py` are pure. `filter_base.py:15-21` states the
purity requirement and gives the downstream reason for it.

The second implementation is not hypothetical. It is this codebase across a version
boundary, which `filter_base.py:637-641` commits to: "an old pipeline that names
1.0.0 must keep reproducing 1.0.0's output after 1.1.0 ships."

### The failure this detects

A name two layers must agree on, living in neither's shared vocabulary, so one of
them invents a private copy. Two instances in the tree, and they are one bug:

- **The string-literal hack.** `pipeline/` may not import `bench/`, so it spells its
  budget keys as string literals, patched by an AST check.
- **The CSV labels.** The filter contract emits no column names, so
  `detect/tables.py` hand-authors them downstream.

`ElementKind` at `core/filter_base.py:104-127` is this bug already fixed once: a
filter declares what one value *is a value of*, so a count has a noun that came from
the graph. The column it lands in is still hand-authored. Half the fix shipped.

**The two instances want opposite cures.** The CSV labels want the name *promoted*
into the shared vocabulary (§8). The budget keys want it *eliminated*: under §11 the
ceiling becomes work units and `pipeline` publishes a number rather than naming a
key. Promoting `BUDGETS` keys into core would be the wrong cure for the right
diagnosis.

### What passes

The artifact schema — `Project`, `Node`, `Edge`, `Pipeline`, `Sink`, `ClipRange`,
`Replicate`, `ROI`. The identifier spelling rules — `SEMVER_PATTERN`,
`FILTER_ID_PATTERN`, `PORT_PATTERN`, `DEFAULT_PORT`, the last of which argues this
criterion verbatim at `filter_base.py:65-70`: "a second spelling in any of them is a
graph that validates and a key that misses." The filter declaration and the stream
algebra — `FilterSpec`, `StreamKind`, `ArraySpec`, `TableSpec`, `ElementKind`,
`ElementRelation`, `Mode`, `ChannelSpec`, `Frame`. The pure derivations both sides
must compute identically — `admits`, `node_element`, the warmup fold,
`resolved_params` / `resolved_detector` / `edited_*`. And, per §11, `TargetProfile`:
`bench` produces it and both front ends consume it, so its shape is agreed
vocabulary even though its *values* are machine-specific.

### What fails

`shares.py`, `machine.py`, `pool_meter.py`. Two implementations with different
worker splits produce identical results at different speeds. They sit low because
`decode/prefetch.py:105` and all of `gui/` both need them — a dependency fact, not
an agreement requirement. Call that half **mutual**; `.importlinter:5-7`'s
parenthesised-layer idiom declares it before it exists.

`FilterSpec.cost` and `FilterSpec.primary_params` also fail: two implementations
disagreeing about either predict or present differently and compute identically.
They are *filter-owned* but not *interop vocabulary*, which is a third category and
is exactly the open question §8 refuses to close.

### Files the criterion splits

| File | Contract half | Not |
|---|---|---|
| `core/wavelet.py` | `coi_edge_samples`, `settled_frames` — they support a `warmup_frames()` declaration | `morlet_power` — an implementation, and the mechanism for agreeing on those is a **version** in the contract with the code above it, as every kernel already does |
| `core/detection.py` | `count_band_to_counts` — `gui/chain_model.py:181` calls it "the one denomination point," and disagreement means the same document claims different events | the gate computation, which is a kernel |

### Two things migrate in

`pipeline/cache_key.py` — two implementations must derive the same key or they
poison each other's store, and the store is already durable
(`pipeline/materialize.py` writes crop artifacts that `resolve_source.py` reads
back). And the at-rest column names in `detect/tables.py` — rule 8 says what SIEVE
writes reads back without SIEVE running, which makes every column name an agreement
with an implementation that is not SIEVE.

### The guard

A string literal appearing in two layers is the smell, and it is AST-checkable —
the same instrument `tests/bench/test_budget_producers.py` already points at
module-level `*_BUDGET` constants, aimed instead at literals duplicated across a
layer boundary.

---

## 7. Derive what is currently declared

`warmup_frames` stops being a hand-typed decorator argument and becomes a function
of the filter's own parameters. The mechanism already exists:
`ParamsBase.warmup_frames()` at `core/filter_base.py:279-304` is exactly this, with
`node_warmup_frames` at `:703` detecting the override by identity and refusing a
refinement that exceeds the spec's bound.

| Filter | Derivation |
|---|---|
| `motion_history` | exactly τ, the history duration it already takes as a parameter |
| `background_ema` | `log(ε) / log(1−α)`, analytic |
| `temporal_baseline` | `N` if it is a rolling window. If it is adaptive, this one stays declared and is **the only unverifiable case** |

**This dissolves the caching finding in full.** `FilterSpec.cacheable` at
`core/filter_base.py:644-654` returns `deterministic and not stateful`, and its own
docstring already knows these are different in kind: "A non-deterministic filter
cannot reproduce its output at all. A stateful one reproduces it exactly... but only
if a number it declared about itself is true." One is a permanent fact about the
operation; the other is contingent on verification. Fusing them into one boolean
means the policy cannot change without the fact becoming a lie — you would have to
un-declare `stateful` to get a key, which is precisely the incentive the declaration
exists to remove. **The spec declares facts; the planner decides policy.**

Once warmup is derived, the correctness hazard the exclusion was defending against —
a wrong hand-typed number silently producing wrong cached output — is gone at the
source rather than routed around.

The epsilon is the one thing still hand-typed. `core/filter_base.py:470-472` says a
nonzero warmup is "a settled-to-within-epsilon choice and the filter's docstring
says which epsilon." Prose. A test cannot assert against a sentence, so it becomes a
field — and its value is a scientific call per filter, not a default. Then one
property test over `discover()` closes it: run from two start points, compare output
at frame `i ≥ warmup`, require agreement within the declared epsilon. Filters nobody
has verified live in a set that only shrinks.

**Statefulness was never a cost of this rework.** `background_ema` is
`y[i] = α·x[i] + (1−α)·y[i−1]` whether it lives in `filters/`, in a loop body, or in
someone's head. Inline it and the recursion does not vanish; it stops having a name.
The declarations at `background_ema.py:161`, `block_signal.py:159`,
`motion_history.py:299`, `temporal_baseline.py:198` are what make it visible.

That generalizes into the test for whether any claimed cost here is real:
**de-filter it and does the problem go away?** De-filter the crop — still an ROI,
still per-replicate, now a loop branch and a boolean on `FrameResult`. De-filter the
detector — still parameterized, still needing a settled frontier, and now its
parameters have no home so they grow a twin. Every case loses information and gains
nothing.

### Two things to check while here

**Warmup does not affect live tuning on a fixed clip.** Output there is a pure
function of `(clip, params)` regardless of warmup. The problem exists only for
scrubbing to arbitrary offsets and for HPC chunking, where the derived warmup
becomes the chunk pad. Any argument for this work that leans on tuning-loop latency
is aimed at the wrong scenario.

**Cache value is not measured by counting filter types.** "Four of seven are
uncacheable" is not a number about anything. If a real figure is wanted, measure hit
rate by DAG position under a typical parameter drag.

---

## 8. What the spec carries that the GUI currently knows

Three kinds, and only the first is settled.

### Channel labels — settled, goes on the spec

A filter declares what it emits, by name. This is the CSV bug, the plot-axis
problem, and detection column naming, all one fix.

The test it passes: if the CSV writer and the plotter invented separate schemes,
they would be **wrong about each other**, not merely redundant. That is §6's
criterion exactly, and it is what distinguishes this from the next item.

### Presentation hints — the open question, not a deliverable

`caption_for`'s per-filter switch, `SIGNAL_LABELS`, and `FilterSpec.primary_params`
are **one item, not three**. All are filter-owned — only the author knows them — and
none is interop vocabulary, because two front ends with different wording are not
wrong about each other.

Either they get a declared presentation channel on the spec, or they stay in the
GUI. **Decide once, for all three together.** Flagging `primary_params` as scope
creep while treating `caption_for` as a gap to be filled was inconsistent: they are
the same question.

`FilterSpec.cost` (§11) is in this category too — filter-owned, not interop — so
whatever channel resolves the three should be checked against it.

### `Stage` — derive before declaring

The chain's grouping (spatial prep, extraction, temporal filter, detection) is used
by the stack and the wizard and declared by no filter. Before adding a field, check
whether it is a function of properties the spec already has:

- **temporal** correlates exactly with the `stateful` set as it stands today;
- **detection** is intrinsic once detection is a filter;
- **spatial prep** versus **extraction** looks positional — `rescale` is prep unless
  it is not.

Declare only the residue that is not derivable. A declared copy of derivable state
will drift, which is the same failure as `ChainKind` in §3.

---

## 9. Name the fold

There are now four instances of *declare per-node → compose over an axis → judge*:

- `stored_bytes_ratio` over the graph (`core/filter_base.py:656-671`)
- `warmup_frames` over the chain (`input_warmup_frames` / `source_warmup_frames`)
- plan cost over the graph (§11)
- detection intervals over time

Four is enough that it should be a **named reduction in `pipeline` with the
composition rule as a parameter**, not four ad-hoc folds.

**The critical detail: the composition function is not a graph property.**
Sequential execution sums along the path. Parallel branches take the critical path.
Frame-pipelined execution is bounded by the max over stages and cares about
throughput rather than latency. So the combining rule belongs to whatever fixes the
execution strategy. If `ExecutionPlan` fixes it, that is the right home. **If the
executor decides later, the fold is in the wrong layer and will be correct only for
the sequential case** — which is the specific way an earlier draft of this document
overreached by calling cost composition "the same fold `source_warmup_frames` gets."

### The open question, and the real price of "everything is a filter"

Does the detection filter emit a **per-frame channel** or **intervals directly**?

A channel and all of the above works — the fold composes, the DAG stays uniform,
and intervals are derived downstream. Intervals directly and you have a node whose
output is not frame-shaped, which breaks the uniform contract that makes the DAG
compose in the first place.

That is the genuine cost of this rework, and it is the one an early draft went
looking for and did not find — substituting a protocol-lock-in worry that
`MergingKernel` had already disproved (§4).

---

## 10. Diagnostics, not a second validator

`Dag.validate() -> list[Diagnostic]` with per-node verdicts. `Dag.build()` becomes
validate-then-raise-on-first. One definition of edge legality, two consumption
modes.

This is what `gui/chain_model.py`'s `grade` is doing today, and its own comment
states the need: "`Dag.build` raises on the first bad edge, which is right for
execution and useless for a stack that must draw a chain a removal or a loaded file
broke."

**It is not GUI-private filter knowledge.** It is a fail-fast-versus-collect-all API
shape, and a batch linter over saved chain files would want the same thing. Do not
bundle it with §8's presentation-hint question: different layer, different kind, and
this one is settled while that one is not.

---

## 11. Units, targets, ceilings

### The conflict that forces the type change

`stored_bytes_ratio` composes because it is exact arithmetic on **dimensionless
ratios** — machine-independent, no calibration. Latency is not. A number computed
with "no kernel, no codec" on a login node **cannot be milliseconds**: wall time
depends on memory bandwidth, cache residency, SIMD width, thread count, and whether
a frame fits in L2. `CostEstimate.seconds_per_megapixel` is that conflict written
into a field — it fuses a work term and a machine term into one scalar, which is why
nothing can produce it.

The same dataclass already does it right once. `peak_bytes_per_input_byte` (`:445`)
is dimensionless, relative, composable.

### Work units, one anchor

`cost` becomes dimensionless `WorkUnits`, **anchored to a reference operation** — a
full-frame copy at reference resolution — Postgres-style: one anchor, everything
relative, and **no per-filter measured coefficient table**. Postgres declares
`seq_page_cost ≡ 1.0` and everything else relative to it, leaving conversion to
per-installation tuning; LLVM's `TargetTransformInfo` does the same. The known
failure of that design is precisely the one this section prevents — an uncalibrated
installation producing numbers that are internally consistent and externally
meaningless.

### Two time axes get two types

Suffixed floats (`_media_s`, `_wall_ms`) catch the error at review time. Types catch
it at pyright.

- **`MediaDuration`** — time in the footage. Already everywhere: τ for MHI, the EMA
  decay, detection intervals, scalogram Hz.
- **`WallDuration`** — time on a clock.
- **`WorkUnits`** — dimensionless. **It never gets a time-flavored name.** The moment
  something calls it `estimated_ms`, the anchor is gone.

No implicit conversion between any two.

**Media time is built on rational fps, not float.** 30000/1001 drifts over a
two-hour recording. The repo already has the precedent and the reason —
`ParamsBase.output_rate` returns an exact `Fraction` because "`ceil(5 / 0.1)` is 50
only until the day the factor is 3."

**Frames are a fourth thing and must not be folded into `MediaDuration`.** They are
*node-relative*: `core/filter_base.py:465-470` says warmup is "counted in this
filter's *input* frames" and that "a rate-changing node between two others makes the
two speak different index spaces."

### Placement

`TargetProfile` is **core** — `bench` produces it and both front ends consume it, so
two layers must agree on its shape, which is §6's criterion. The
`(WorkUnits, TargetProfile) -> WallEstimate` **conversion is `bench`**, not core: its
only consumers sit above `bench`, and `pipeline` is forbidden to call it anyway.

### The profile stores dispersion

Slurm `--time=` has asymmetric failure: under it and the job dies at hour eight with
partial output; over it and you queue. A mean coefficient plus a hand-tuned safety
multiplier is the fudge factor arriving through the front door. So the profile
stores the fit residual and the estimator returns a `WallEstimate` carrying
dispersion, and the caller asks for p95.

**Dispersion must not shrink with n.** If a per-frame residual is scaled as √n over
a 100k-frame job, the p95 collapses toward the mean and you have a point estimate
wearing a quantile's name — worse than the scalar it replaced, because it now looks
principled. Job-level uncertainty is dominated by *systematic* error: wrong
resolution, thermal throttling, a contended node, a codec decoding at a different
rate than the fit assumed. Those do not average out.

### Provenance, targets, fingerprints

Every displayed wall number carries two flags: predicted-versus-measured, and which
profile produced it. The realtime factor during tuning is *measured* once the clip
has run and *predicted* before; one number that is silently either costs somebody an
afternoon. This is rule 6, and `FrameResult.source_cropped` is the precedent — a
value that could be either must say which.

No implicit "current machine" default. The target is explicit at the call site and
recorded into the plan and any output artifact, **declared non-hashed** — the machine
a prediction was made for does not change what a result is, and `checkpoints` and
`outputs` living on `Project` rather than `Node` is the precedent.

Fingerprint on load: CPU model, core count, BLAS build, codec version, and the
resolution the fit was done at. A stale profile produces confidently wrong Slurm
requests, which is worse than requesting nothing — so this is a refusal, and the
graceful form is already implied by the type split: an unmatched fingerprint still
yields **work units** and says it is uncalibrated. It must not fall back to the
reference machine's constants. Absent must not render as zero, and here it must not
render as *someone else's* number.

The calibration is not a scalar. `docs/findings/` records that the worker optimum
moves with core class — 2 workers on P-cores, 3 on E-cores, 2.33x across worker
counts — so it is at minimum per core class. Which makes the calibration file and
`docs/todo/adaptive-worker-allocation.md` the same object seen twice: that item is
deferred waiting for "pool-utilisation samples from more than one class of machine."

### Ceilings

Composable ceilings move to work units. The budget test becomes machine-independent
— predicted units against measured units, conversion never invoked — and CI stops
inheriting runner-load variance.

**Say which half this closes.** Work units measured as a deterministic count catch
*algorithmic* regression and are blind to *implementation* regression: a kernel
touching the same elements through a cache-hostile access pattern, or losing a SIMD
path, passes unchanged. So the in-pipeline budgets become CI-gated for the
algorithmic half, and the wall-clock half moves to a calibration job that is
explicitly **not** gating. Without that stated, `docs/AUTO-GUARDRAILS.md` §4 acquires
a second entry reading ENFORCED that covers less than it appears to.

Only `open_to_first_frame` and `scrub_settle` stay in wall milliseconds — the
hand-written entries that never came from the fold. And `pipeline` publishes a number
while naming no budget key, so `test_budget_producers.py`'s AST check becomes
**unnecessary rather than better**.

---

## 12. Gut the GUI

The GUI is passed everything. It owns nothing. It derives nothing.

What leaves `gui/`: every computation (`morlet_power`, `detect`, `settled_for`,
`gate_to`, `density_surface`, the series reductions in `detector_worker.derive` and
`series_collector`); every second representation of an artifact value
(`DetectorState`'s settings half); every type system the layers below lack
(`ChainKind`); every hand-rolled facility standing in for a node's
(`reuse_band_power`); `grade`, which becomes §10; and every rule enforced only here
(rule 6's frontier).

What stays: painting, layout, the undo stack, Qt threading — the queued-connection
hop in `gui/executor_adapter.py` is a genuine Qt concern and is the shape the rest
should look like — the view-state bucket, and widgets that render a value and emit
an intent. Plus, pending §8's decision, possibly the presentation hints.

**The mechanism that proves it is done** is a forbidden contract in `.importlinter`:
`gui` may not import `core.wavelet`, `gui` may not import `sieve.detect`. It fires
today, names every site, and cannot be satisfied by moving code around inside
`gui/`. And `core/filter_base.py:524` runs the other way — `primary_params` is GUI
policy in `core` — so the placement contract is stated in both directions or it only
fixes the half that was noticed.

---

## 13. Order

1. **Declare the placement contract** in `.importlinter`, violations listed as an
   exception set that only shrinks. The list is the work list.
2. **Fix the units** (§11): `MediaDuration` on rational fps, `WallDuration`,
   `WorkUnits`, `TargetProfile`, `WallEstimate` with non-shrinking dispersion.
3. **Split the bottom tier** (§6) into contract and mutual, declaring the second in
   `.importlinter` before it exists. Step 2's types need a home; doing this after
   means moving them twice.
4. **`Dag.validate()`** (§10). Independent of everything else and unblocks the GUI
   work early.
5. **Derive `warmup_frames`** (§7), declare the epsilon, write the property test over
   `discover()`, and let `cacheable` read the verification rather than the flag.
6. **Widen the kernel protocol.** `Mode.WINDOWED`, a signature that can return a
   `TableSpec`, and a named refusal in `_bind` for what still cannot run. Settle §9's
   channel-versus-intervals question first — it decides the signature.
7. **Channel labels on the spec** (§8), and `detect/tables.py` reads them.
8. **Crop becomes a filter.** Already `Frame → Frame`, `Mode.STREAMING`; needs no
   protocol extension. Kills `plan.roi`, the loop branch, `_crop`, `pre_cropped`,
   `FrameResult.source_cropped`, and the `Replicate | None` chain.
9. **The span becomes a filter,** pushdown preserved in the planner.
10. **Name the fold** (§9), with the composition rule owned by whatever fixes the
    execution strategy.
11. **The temporal step becomes a windowed filter.**
12. **Detection becomes a filter.** `DetectorSettings` dissolves into `Node.params`;
    `Project.detector`, `Replicate.detector_overrides`, `EditDetector`, and
    `DetectorState` die with it. The cache-identity gap in §3 closes for free, which
    is why it must **not** be fixed by adding `DetectorSettings` to the cache key in
    the meantime. No layer change needed: `.importlinter:21` already puts
    `sieve.detect` below `sieve.filters`.
13. **Rule 6's frontier moves** into the windowed execution contract.
14. **`sieve detect` collapses into `sieve run`** with a table sink
    (`docs/todo/sink-writers.md`).
15. **GUI/CLI parity becomes a consequence.** Note that item's scoping error while it
    is open: its `reads:` names `cli/run_cmd.py`, which emits nothing to diff.

**Undecided and needing an answer, not a step:** §8's presentation-hint channel, and
§8's `Stage` residue after the derivability check.

Doc corrections riding along: `cli/detect_cmd.py:4-5`'s hashing claim is false;
`docs/AUTO-GUARDRAILS.md` §2 splits into rule 1 (enforced) and resolution parity
(open); its §4 gains the algorithmic/implementation split; its §7 gains the placement
reading beside the concurrency one; `gui/chain_model.py`'s docstring claim about
`ArraySpec` is stale.

---

## 14. Corrections, and what this does not settle

### Corrections to this document

1. **"The filter contract can express exactly one emission."** False. `TableSpec` and
   `StreamKind.TABLE` exist at `core/filter_base.py:370-402`. The contract declares
   it; the executor cannot run it.
2. **"`Mode.WINDOWED` needs to be added."** It exists at `:85`. Only its execution is
   missing.
3. **"`ChainKind` is the type system the contract lacks."** Wrong since 2026-07-28.
   `ElementKind.PIXEL` / `BLOCK` at `:104-127` distinguishes an image from a block
   grid, and `TableSpec` covers events.
4. **"Making more things filters makes more things stateful."** Wrong twice. None of
   the migration candidates is stateful — `WINDOWED` is explicitly not `stateful`
   (`:484`) — and the detector currently has no cache at all.
5. **"Latency composes like `stored_bytes_ratio`."** The placement was right and the
   denomination was unexamined, which is how a fudge factor gets in. And the fold's
   *combining rule* is not a graph property at all (§9), so "the same fold
   `source_warmup_frames` gets" was wrong a second way.
6. **"`block_signal` gates the tuning loop."** Unmeasured and probably aimed at the
   wrong scenario: on a fixed clip, output is a pure function of `(clip, params)`
   regardless of warmup (§7). Counting uncacheable filter types is not a measure of
   cache value.
7. **"The target belongs on the mutual side."** The *type* is contract vocabulary —
   `bench` produces and both front ends consume — while the conversion is `bench`
   (§11).
8. **"`caption_for` is a gap to fill; `primary_params` is scope creep."** The same
   question, answered inconsistently. They are one item with `SIGNAL_LABELS` (§8).

### Unverified in this session

Whether `fps=0` is reachable at `gui/chain_model.py:208` — the callers of
`parity_chain` were never checked. `gui/filter_tab.py`'s `_set_detector` and the
whole of `_on_detector_changed` were not read, and the equality check at `:766`
includes `solo_block`, so moving that field changes echo suppression in a direction
nobody has traced. `tests/unit/test_partial_detector.py` carries
`# pyright: ignore[reportArgumentType]` at `:156-157`, on the exact constructor step
12 retypes. Whether `sieve.storage` — declared in `.importlinter` at `:21` and `:47`
— exists on disk. Whether `temporal_baseline`'s window is rolling or adaptive, which
decides whether it keeps a declared warmup.

### What is actually risky

**The channel-versus-intervals question (§9)** is the one real design risk, and it is
load-bearing on step 6's signature.

**The schema migration.** Steps 8 through 12 change what a saved graph looks like: a
crop node at every root, a span node, and the detector's parameters moving into
`Node.params`. That is v4, it touches every saved file, and it wants one migration
rather than four.

**The order is load-bearing.** Units before anything is measured, or the fits are
redone. The bottom-tier split before the units land, or they move twice.

### What this is not

Not a rewrite of the rules. Every one of the eight gets *stronger*: rule 1 covers
everything derived from the footage rather than only frames; rule 2 becomes true for
the first time once crop and span are node params; rule 3 becomes the whole
architecture rather than a directory convention; rule 4 gets producers it lacks and
an honest statement of what they cover; rule 6 reaches the CLI and the calibration;
rule 7's identity line finally reaches the values that decide what is claimed as an
event. The rules did not cause this. They under-reached, and an under-reaching rule
feels identical from the inside to an over-constraining one while the fix is the
opposite.
