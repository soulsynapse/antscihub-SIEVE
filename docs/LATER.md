# Later

Work that is real, understood, and deliberately not being done yet.

## What this file is for

`TODO.md` holds what is takeable now: items scoped to a context window, written
so the work can start without reading the whole doc tree. This holds the
opposite — things whose *timing* is the decision, where writing them down is
the point and starting them would be the mistake.

## Rules

1. **An entry must say what would make it the right time.** A list of things
   that would be nice is a list nobody ever acts on. A trigger — a filter that
   needs it, a measurement that hurts, a user who is blocked — is what turns
   this from a wish into a thing that gets picked up on the day it should be.
2. **An entry must say why not now.** Not "no time"; the actual reason. Usually
   one of: nothing exercises it yet, the design question needs a workload to
   answer, or it is downstream of parity work that has not happened.
3. **This is not a second `SCAFFOLD.md`.** That file already names every module
   the architecture intends. A file that does not exist yet is not an entry
   here. An entry here is a *deferred decision with reasoning*, and if the
   reasoning is only "not written yet", it belongs in SCAFFOLD and nowhere else.
4. **Measurements go to `docs/findings/`, extrapolations stay here.** Where an
   entry rests on arithmetic rather than on a number somebody took, it says so
   in the entry. The first step of acting on such an entry is taking the
   measurement, and an unflagged extrapolation is how a guess becomes a
   premise.
5. **Promotion is a move, not a copy.** When an entry becomes takeable, delete
   it here and write the `TODO.md` item. Two homes for one piece of work is two
   descriptions that drift.

---

## GPU execution

**Why not now.** There are zero GPU kernels and two filters. The product is not
at feature parity with what VISION describes on the backend that already works,
and adding a second backend before the first one carries a real workflow means
maintaining two of everything to make nothing new possible.

**What would make it the right time.** A filter whose CPU kernel is measurably
the bottleneck of a tuning session — not a kernel that is merely slow, but one
where `bench/budgets.py` is being missed because of it and the profile says so.
VISION's detection and tracking steps are the likely first candidates;
`downsample` is not.

**`background_ema` is the first filter for which the arithmetic below no longer
refuses.** At 9.9 ms/MP it is ~30x `downsample`, so on the reference source a
frame costs order 200 ms on CPU against ~10 ms of round trip — the transfer is
now 5% of the work rather than double it. That does *not* promote this entry:
the trigger is a missed budget with a profile behind it, and no in-pipeline
budget can be missed until `pipeline/preview.py` exists to publish one. What it
does mean is that the answer to "would a GPU kernel pay?" has flipped from
"provably not, for the only filter we have" to "probably, and somebody should
measure it" — and that measurement is step one of acting on this entry.

**What it involves, so the size is not a surprise:**

- `backend/namespace.py`, which SCAFFOLD reserves and nothing implements:
  Array-API namespace resolution (numpy vs cupy) and host/device transfer.
- **Frame residency.** `Frame.data` is `NDArray[Any]` — host, by annotation and
  by every consumer. Nothing in the system knows where a frame lives, so a GPU
  kernel doing its own `asarray`/`asnumpy` round-trips per node. See the
  arithmetic below.
- **Automatic backend selection.** `ExecutionPlan.backends` already carries a
  backend per node and the keys are derived from it, so a mixed graph runs and
  keys correctly today — see
  `docs/completed-todo/2026.07.25-per-node-backend.md`. What is missing is
  anything that *chooses*: a caller must state the mapping, and nothing walks
  the kernel shelf against `DEFAULT_PREFERENCE` to build one. That resolution
  needs a policy — fastest available per node, or fewest transfers across the
  graph — and the second is the right answer only once residency below exists.
- **Cache locality.** Does `FrameStore` hold device arrays or host arrays?
  Device exhausts VRAM over a tuning session; host makes every hit an upload.
  This has no obvious answer and should not be given one without a workload.
- **The equivalence test that `backend_agnostic` requires.** `FilterSpec` says
  claiming it "requires an equivalence test"; there is no such test and no
  harness for one. `KernelRegistry.select`'s one-element preference tuple exists
  precisely so a test can drive both sides, and has no caller doing that.
  `@pytest.mark.cuda` is declared in `pyproject.toml` and used by nothing.

**The arithmetic that says this is not free — not a measurement.** On the
reference source (5312x2988 BGR, ~47 MB a frame), a PCIe round trip is order
5 ms each way, against `downsample`'s declared 0.35 ms/MP — about 5 ms for that
frame on CPU. So a GPU downsample that transfers per node is *slower* than the
CPU kernel it replaces, and GPU pays only when frames stay resident across
consecutive GPU nodes. This is arithmetic from a declared cost and a bandwidth
figure, not something anybody has measured on this hardware; measuring it is
step one of acting on this entry, and the result belongs in `docs/findings/`.

Read: `docs/SCAFFOLD.md` `backend/`, `src/sieve/backend/dispatch.py`,
`docs/completed-todo/2026.07.25-executor.md`.

## A kernel protocol that is not one frame in, one frame out

**Why not now.** Two node shapes are valid graphs that the executor refuses at
run time, and both refuse for one reason: `Kernel` takes a frame and returns a
frame. `dispatch.py` declines to invent the second signature before a filter
needs one, and that reasoning has not changed — a signature designed against zero
instances is a signature every kernel written afterwards is stuck with.

**The third shape's trigger has fired and it has been moved.** Multi-upstream
nodes were the third entry in this list until 2026.07.26, when REFINED-VISION's
temporal section was read as a specification: every kind-amplifier it describes
is a *combination* of channels, which is what makes it a discriminant rather than
a filter, so the trigger this entry asked for — "a filter that actually needs
one" — is satisfied several times over. See `TODO.md` **Multi-upstream kernels**,
and `docs/REFINED-VISION.md` **G** for why it gates the rest of that section.
Per rule 5, it is gone from here rather than duplicated.

**What would make it the right time** for the two that remain. A filter that
actually needs one. Each has a different trigger and they are unlikely to arrive
together:

- `Mode.WINDOWED` — a filter needing a span before it can emit, e.g. a temporal
  median for background subtraction. This is the likeliest to arrive first.
- `rate_changing` — a decimator. The warmup arithmetic already handles rate
  exactly and is property-tested, so only the *call* is missing. **One thing to
  record before it lands**, because discovering it afterwards means invalidating
  results rather than a design: a decimator must carry its own temporal
  anti-alias lowpass, or high-frequency behaviour folds into the measured band
  and arrives disguised as something slower — grooming at 8 Hz sampled at 12 fps
  reads as 4 Hz. `wavelet.default_freqs`' 0.45·fps cap does not cover this; it
  stops the *analysis* asking for a frequency that is not there, not the
  *decimation* from manufacturing one. The anti-alias belongs inside the filter
  rather than as a separate node a user can forget to place, by the same
  reasoning that `downsample` offers no un-anti-aliased mode. See
  `docs/REFINED-VISION.md` **E**.

**A fourth shape was never deferred and is now built.** A *stateful streaming*
filter — one frame in, one frame out, carrying what it learned from the last
frame — needed no new arity, only somewhere to keep the state. `StatefulKernel`
and `KernelBinding.start` are that, and `background_ema` is the filter; see
`docs/completed-todo/2026.07.26-a-kernel-that-can-remember.md`. The three shapes
above stay here, and the precedent it sets for them is worth naming: the state
lives on the *binding*, made once per `execute`, so whatever a windowed or
merging kernel needs to be handed, it will be handed by `start` and not by a
registry entry.

One consequence for the WINDOWED trigger specifically. A temporal median was
named above as the likeliest first windowed filter, on the grounds that it is
what background subtraction wants; there is now an EMA background model that
does the job streaming. That does not remove the trigger — a median is robust to
transient occlusion in a way an EMA is not — but it does mean the first windowed
filter has to earn its place against something that already works, rather than
being the only way to get a background.

Read: `src/sieve/backend/dispatch.py` `Kernel` and `StatefulKernel`,
`src/sieve/pipeline/executor.py` `UnrunnableNodeError`.

## Sink writers

**Why not now.** `Sink` has been on `Project` since the artifact landed and
nothing writes one, so `sieve run` refuses a project that declares outputs
rather than running it and silently writing nothing. That refusal is the right
behaviour and it is also the whole cost of the gap, which is small. What makes
writing the writers premature is that the two formats worth having want
different things that do not exist: VISION step 1's "coordinates as a csv" is a
table sink, and no filter emits a `TableSpec` — the one filter downsamples
frames — while an array sink writing frames back out is compaction, which is
`materialize.py`'s question about Zarr layout rather than a format choice.
Writing a parquet writer now means designing a schema against zero producers.

**What would make it the right time.** Either the first filter that emits a
`TableSpec` — a detector, a thresholder producing coordinates — or
materialization landing and needing somewhere for a compacted array to go. The
first is the likelier trigger and is the one VISION step 1 is blocked on.

Read: `src/sieve/core/pipeline_model.py` `Sink`, `src/sieve/cli/run_cmd.py`
`_refuse_sinks`, `docs/SCAFFOLD.md` `pipeline/results.py`.

## Coverage and detection lanes on the timeline

**Why not now.** Nothing in this repo records what was examined or what was
found. `pipeline/` is `cache`, `cache_key`, `dag`, `executor`, `plan`; the
executor returns frames and writes cache entries, and neither is a claim about
coverage. Painting these lanes before a producer exists means inventing a
coverage model against zero data, and the one thing this layer must not get
wrong is precisely the thing an invented model would guess at — see below.

**What would make it the right time.** The executor recording, per replicate and
per frame, that it ran and under which resolved params. That is the trigger, and
it is also the smaller half of the work: the arrays are four per replicate
(`measure`, `gate`, `covered`, `current`), and everything here is a rendering of
them.

**The rule the layer exists to enforce, which is not a rendering detail.** Three
claims must never look alike:

- **unexamined** — nobody computed this stretch. A bare trough, no baseline
  rule, visibly *empty* rather than dark.
- **examined and quiet** — computed, and the answer was nothing. The baseline
  rule is lit, so "we looked" is visible independently of what was found.
- **examined under settings no longer in force** — desaturated, *not* dimmed. A
  dim red still reads as a weak detection; a gray one reads as a detection that
  is not being claimed.

V1's `detection_timeline.py` names the first two collapsing as the standing
failure of that codebase: a strip that paints unfilled regions the same colour
as a computed zero turns "nobody looked here" into "nothing happened here",
which is a false negative wearing the costume of a result.

**Two things in V1 that are decisions, not drawing.** A screen column is claimed
covered only if *every* frame in it is — `minimum.reduceat`, so a column
straddling a live frontier reads partly-unexamined rather than examined. And bar
height is `log1p` normalised over covered frames only, because the measure is a
count with a heavy tail: against a linear axis one large event sets the maximum
and every ordinary event below it draws one or two pixels tall, which is
indistinguishable from examined-and-quiet — the same collapse, arriving through
the axis instead of through the palette.

Carries a readout: "47% of the clip examined · 3 detections · 1.2 s detected ·
30 s under other settings", and a legend, because none of the above is legible
without one.

Read: V1 `gui/explorers/detection_timeline.py`, `gui/track_store.py`.

## Annotation spans on the timeline

**Why not now.** There is no marks model, no labelled-span sidecar, and no UI
that could create one. It is downstream of the coverage lanes above for a
practical reason as well as a temporal one: in V1 the way a span gets created is
"commit these detections as marks", so the detector is what makes the annotation
layer worth having rather than a drawing tool nobody uses.

**What would make it the right time.** A detector whose output is worth
correcting by hand, or a labelling task that needs ground truth before one
exists. VISION's classification work is the likely trigger.

**The design constraint worth recording now**, because it is the one V1 got
wrong first and fixed at cost: a mark belongs to a **replicate**, not to the
video. A span is one region's answer. V1 wrote every region into one
`Foo.marks.json` keyed by label, so saving a label from region 3 replaced region
2's provenance for that label. The palette is the exception and stays per-clip —
one behaviour label should be one colour across every replicate in a source,
which is a display contract about the clip and not about the region.

Read: V1 `gui/marks_store.py`.

## Surrogate calibration for the detection threshold

**Why not now.** It calibrates a chain whose final shape is still being decided —
`TODO.md`'s temporal section has four items that each change what is being
thresholded, and a null distribution computed for a chain that then grows a node
is a number that quietly stops meaning anything. It is also genuinely useless
before the accuracy question below has *any* answer: a calibrated threshold that
nobody can check against a labelled event is rigour pointed at an unknown.

**What would make it the right time.** The temporal chain settling — concretely,
the first parameter set somebody wants to run over a whole video and report.
That is the moment the threshold stops being a slider position and becomes a
claim.

**The problem it solves**, which is easy to not notice because it looks like a
result. Thresholding a few hundred blocks across a few thousand frames is on the
order of a million tests, so the expected false-positive count is proportional to
blocks × frames: **the same settings on a longer clip, or on a finer grid,
produce more detections for no biological reason.** A user comparing a 10-minute
recording against a 30-minute one under identical settings sees more behaviour in
the longer one and has no way to tell how much of that is arithmetic. This is the
same class of failure the coverage lanes entry above exists to prevent, arriving
through the threshold instead of through the palette.

**The remedy is already half-built.** The size-and-duration filter REFINED-VISION
describes is cluster-extent inference — the instrument fMRI settled on (Worsley
and Friston's random field theory; Benjamini–Hochberg FDR is the other branch).
What is missing is its null distribution, without which "size threshold 12" is
tuned until the output looks right, which is exactly the circularity the method
exists to avoid.

**Why it is cheap here, which is the argument for eventually doing it.**
Circularly shift each block's time series by an independent random offset (or
phase-randomize it): real spatiotemporal events are destroyed while each block's
marginal distribution and the spatial correlation structure survive. Run the
*existing* gate and attribute filter on the surrogate, take the largest cluster,
repeat a few hundred times, read the threshold off the 95th percentile. The
surrogate is just a different input array, so this reuses the entire detection
chain — the implementation is a loop and a percentile, not new mathematics.

This is the single item in the doc tree most likely to make SIEVE's output
defensible in review, which is why it is written down now rather than when
somebody asks for it.

Read: `src/sieve/core/detection.py`, `docs/REFINED-VISION.md` **D**.

## Accuracy feedback in the tuning loop

**Why not now.** It needs labelled spans and there is no marks model — this is
strictly downstream of **Annotation spans on the timeline** above, and shares its
trigger.

**Why it is worth an entry anyway**, rather than being a line in that one: it is
the deepest gap between VISION as written and a tool that produces defensible
results, and naming it separately is what stops it being read as a rendering
detail of the annotation layer. VISION steps 4 and 5 build an elaborate feedback
loop about **cost** — the benchmark summary, the graph HUD, the per-operation
expense, the compaction prompt when memory climbs. There is nothing anywhere
about whether a parameter change made detection *better*. A user drags a
threshold and learns exactly what it cost and nothing about what it caught.

**What would make it the right time.** A marks model plus one hand-labelled
window. Not a corpus — one window is enough to make the curve below draw, and the
gap between "no accuracy signal" and "a noisy accuracy signal" is far larger than
the one between noisy and good.

**The shape of the answer, which is cheaper than it sounds.** The detection
threshold is a *slider* and the score series behind it is already cached, so
sweeping the threshold across a labelled window and drawing the resulting
precision/recall or detection-error tradeoff curve is one pass over an array the
system already holds — `gui/band_plot.py`'s family draws it. The user then tunes
against a curve instead of an impression, and the parameter that maximizes F1 or
minimizes total error is *read off* rather than hunted for.

**Two constraints inherited from entries above, both of which V1 got wrong.**
Labels belong to a **replicate**, not to the video. And a curve computed over
labelled spans must never be drawn as though it covered unlabelled ones — that is
the unexamined-versus-quiet collapse the coverage lanes entry names as V1's
standing failure, arriving through a different widget.

Read: the **Annotation spans on the timeline** entry above,
`src/sieve/core/detection.py`, `docs/REFINED-VISION.md` **F**.

## Cache eviction, and spilling to disk

**Why not now.** `MemoryFrameStore` is a dict with no bound, and a bound picked
today would be picked from nothing — no measurement exists of what a tuning
session actually holds. The protocol is in place, so the executor is already
written against the thing that will grow the policy rather than against a dict
it would have to be rewritten off.

**What would make it the right time.** A tuning session that exhausts memory,
or `materialize.py` landing — compaction to Zarr is where spilling belongs, and
an eviction policy written before it would be a second answer to where a frame
goes when it stops fitting.

**Also deferred here, for a related reason:** cache-aware lead-in shortening. A
cached upstream could in principle shorten a decode range, but only if the entry
covered the lead-in span too, which the store does not record. Slow and correct
beats fast and occasionally wrong, per `cache_key.py`'s asymmetry rule. A store
that tracked coverage would reopen the question.

Read: `src/sieve/pipeline/cache.py`, `docs/SCAFFOLD.md` `pipeline/`,
`storage/`.

## Materialization, and what non-negotiable #1 currently asserts

**Why not now.** "Filesystem is truth *at rest*" is the first non-negotiable and
nothing in this repo has ever been at rest: `MemoryFrameStore` is a dict, no
sink writes, and `sieve run` refuses a project that declares one. So the rule is
presently a statement about a state the system cannot enter, which is not a
violation — during interactive tuning truth is *supposed* to live in memory —
but it does mean the rule has never been tested by anything.

VISION step 1 describes the dumbest version of the product as a folder per
transformation, and step 4's economy argument turns on "save the representative
few seconds to the child layer, and because things are deterministic it still
represents what you're trying to do". Both are `pipeline/materialize.py` plus
`storage/zarr_store.py`. Writing them now means choosing a Zarr v3 chunk and
shard layout against zero workloads, and the layout is the whole decision — a
chunking that suits sequential playback is the wrong one for random access by
replicate, and nobody has yet run the access pattern that would say which
matters.

**What would make it the right time.** A tuning session slow enough that the
user wants a compaction checkpoint — which is downstream of the preview loop in
`TODO.md`, because until previews are re-run interactively there is nothing to
buy back. The first measurement to take is what a session's intermediates
actually weigh, and it belongs in `docs/findings/`.

**Related and settled enough to record:** compaction is user-initiated, never
automatic per step. ARCHITECTURE says so and VISION's "you can save that
representative few seconds" is a user gesture. An automatic policy would be a
second answer to the eviction question above.

Read: `docs/SCAFFOLD.md` `pipeline/materialize.py` and `storage/`,
`src/sieve/pipeline/cache.py`, `docs/VISION.md` steps 1 and 4.

## Process isolation for filter execution

**Why not now.** `execute` runs in the calling process. One filter exists, it is
NumPy over a decoded array, and the failure modes it has are exceptions a
`try`/`except` already contains. `workers/` buys crash isolation, and there is
nothing yet whose crash would take anything down.

The cost is not one module: SCAFFOLD reserves four, and the reason is that a
process boundary is a serialization boundary. Frames are ~47 MB on the reference
source, so the transport has to be shared memory rather than pickle, which means
a named-segment lifecycle and a versioned protocol with negotiation at startup —
`shm_transport.py` and `protocol.py` are not incidental to `manager.py`.

**What would make it the right time.** A kernel that can take the process down
rather than raise: `cv2` can segfault on malformed input and a CuPy kernel can
wedge a context, so the trigger is most likely the first OpenCV-heavy filter or
the GPU work above. Cooperative cancellation is the other trigger and the more
likely one in practice — a full-video run the user wants to stop mid-frame
cannot be interrupted by anything in-process short of checking a flag between
frames, which is fine until a single frame is slow.

**The thing to not get wrong when it lands:** the GUI reaches `workers/` only
through `pipeline/`, per `.importlinter`. A worker handle that surfaces in `gui/`
is how the "GUI is a view over the executor, never a second execution path" rule
fails quietly.

Read: `docs/SCAFFOLD.md` `workers/`, `.importlinter` layers contract,
`src/sieve/pipeline/executor.py`.

## HPC handoff, and review mode

**Why not now.** Both are readers of durable outputs and there are none. `sieve
run` refuses a project that declares a `Sink`, so a job that ran on a cluster
would produce nothing to bring home and a review tool would open nothing. These
are downstream of **Sink writers** above and of materialization, and are listed
together because they share that one gate.

The architectural decision they rest on is already made and does not need
revisiting: HPC is not a special path. It consumes the same serialized DAG the
CLI does, which is what non-negotiable #2 is for. So `hpc/handoff.py` is job
script generation from an artifact that already exists, not a second executor,
and its size is proportional to how many schedulers it must speak rather than to
anything about SIEVE.

**What would make it the right time.** For HPC: a dataset that does not fit in a
local session, plus at least one sink. VISION is explicit that most projects
will not need it and that the requirement is only that SIEVE be *ready* — so the
trigger is a real user with a real cluster, not a milestone. For review mode:
the first durable output worth interpreting, which is the same trigger the
coverage lanes above have.

**Worth recording now**, because it constrains the sweep design later: VISION's
HPC wizard toggles things like whether a compaction checkpoint happens, on the
grounds that a cluster's memory may make it unnecessary. That makes compaction a
*plan* property rather than a fact about the artifact, and an artifact that
hard-codes it is one the wizard cannot edit.

Read: `docs/SCAFFOLD.md` `hpc/` and `review/`, `docs/VISION.md` steps 6 and 7,
the **Sink writers** entry above.

## A pipeline editor, and whether it is a list or a graph

**Why not now.** One filter exists. Every graph anybody can currently build is a
chain of one node, and a visual editor for that is a label.

**The design question that has no answer yet, and is the actual reason to
wait.** VISION step 4 describes the user-facing object as an *operations
history* — an ordered list you add to, with the current operation selected and
its controls beside it. ARCHITECTURE and `core/pipeline_model.py` say the model
is a DAG, and `dag.py` enforces it. Both are right: a linear chain is a
degenerate DAG, and the linear presentation is what makes the tool legible to
someone who is not thinking in graphs. What is undecided is whether they are one
widget that degrades to a list or two views over one model, and that cannot be
settled by argument — it is settled by watching what a user does the first time
a graph branches.

**What would make it the right time.** A graph that is not a chain, which means
a multi-upstream filter, which means the named-port change to `Edge` in the
kernel-protocol entry above. Until then the operations list VISION asks for is
buildable as an ordinary list widget over `Dag.order` and does not need this
question answered.

Read: `src/sieve/core/pipeline_model.py`, `src/sieve/pipeline/dag.py`,
`docs/VISION.md` step 4, `docs/SCAFFOLD.md` `gui/pipeline_editor.py`.

## `slider_to_graph`, which is gated on there being a slider

**Why not now.** The budget is "Slider drag → graph update" (200 ms), and
nothing in the GUI edits a parameter. `ReplicateDocument` holds the graph and
`set_pipeline` is the one write, but every caller of it is a project load —
there is no widget anywhere that changes a node's params, so there is no drag
for the ceiling to describe. `gui/preview_runner.py` would publish it in one
line and the line would never run.

This is deliberately *not* faked by publishing the key from something adjacent.
A graph re-render triggered by the working window moving is a real interval and
is not this one: the window change decodes frames the store does not have, and
the drag this budget names is supposed to decode nothing at all
(`pipeline/preview.py`). Putting window moves into the series would make a
200 ms ceiling look generous by measuring the wrong gesture.

**What would make it the right time.** A parameter control bound to a node —
VISION step 4's "information on the specific filter applied", which is the panel
beside the operations list. `core/filter_base.py` already declares
`primary_params`, which is what such a panel would build itself from, so the
gating is the widget and not the contract. `filter_to_first_tick` has a producer
as of `gui/preview_runner.py` and this is the last in-pipeline budget without
one.

**What it involves.** The panel reads `FilterSpec.primary_params` and the params
model's fields, writes through `Project.with_param_edit` so the edit lands as
the two writes that method already performs, and pushes a `QUndoCommand` like
every other document mutation. The render it triggers is
`PreviewRunner.request_render`, unchanged — the coalescing and the abandon rule
are already written against a caller that submits faster than renders finish.

Read: `src/sieve/gui/preview_runner.py`, `src/sieve/core/filter_base.py`
`primary_params`, `src/sieve/bench/budgets.py` `slider_to_graph`,
`docs/VISION.md` step 4.

## Application config, and where the boundary with Preferences falls

**Why not now.** SCAFFOLD reserves `core/config.py` for pydantic-settings with
CLI > env > file precedence, and there is nothing to put in it. The two
configuration surfaces that exist are `gui/preferences.py`, which holds machine
preferences in `QSettings` and is deliberately GUI-only per non-negotiable #2,
and Typer flags on the CLI. Neither wants a third source today.

**The decision, which is why this is an entry rather than a missing file.** The
boundary between the two is undrawn. `proxy_width` is a preference — it is a
statement about this machine's decode budget and must never travel with a
project. A cache size limit or a default backend preference is arguably the
same, and arguably app config that the CLI needs too and `QSettings` cannot
carry to a headless node. Drawing that line against zero settings would draw it
somewhere arbitrary, and the failure mode is the one preferences.py's module
docstring already warns about: a setting that travels to another machine as an
assertion about hardware it has never seen.

**What would make it the right time.** The first setting the CLI and the GUI
both need to read. Cache bounds and backend selection policy are the two
candidates, and both are downstream of entries above.

Read: `src/sieve/gui/preferences.py` module docstring, `docs/SCAFFOLD.md`
`core/config.py`, `docs/ARCHITECTURE.md` non-negotiable #2.

## Profiling as a module

**Why not now.** `viztracer` and `py-spy` are in the dev group and imported by
nothing. Every measurement in `docs/findings/` so far came from timing a named
interval directly — the seek cost, the colour conversion, the scrub round trip
— and each of those was a hypothesis with an obvious place to put a
`perf_counter`. A profiler earns its place when the question is *where did the
time go*, and that question has not been asked yet.

**What would make it the right time.** A budget miss whose cause is not obvious
from the span that reported it. Half of that is now in place: `bench/metrics.py`
publishes spans against budget keys and `Sample.within_budget` says which
missed, so a miss can arrive with a key and no explanation — which is exactly
the gap `bench/profiling.py` fills. The other half is a *nested* span worth
attributing, and today the only publisher is `gui/player.py`'s scrub round trip,
whose cause is already known (`docs/findings/2026.07.25-the-seek-is-irreducible.md`).
The trigger is therefore the preview: a `full_preview_render` miss over a
multi-node graph is the first question of the form "which node?". The two tools
are complementary and both are already declared — VizTracer for phase structure,
py-spy for sampling a process nobody instrumented — so this is wiring, not a
choice.

Read: `docs/SCAFFOLD.md` `bench/profiling.py`, `docs/findings/`,
`pyproject.toml` dev group.
