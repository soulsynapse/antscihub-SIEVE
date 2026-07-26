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

**Why not now.** There are zero GPU kernels and one filter. The product is not
at feature parity with what VISION describes on the backend that already works,
and adding a second backend before the first one carries a real workflow means
maintaining two of everything to make nothing new possible.

**What would make it the right time.** A filter whose CPU kernel is measurably
the bottleneck of a tuning session — not a kernel that is merely slow, but one
where `bench/budgets.py` is being missed because of it and the profile says so.
VISION's detection and tracking steps are the likely first candidates;
`downsample` is not.

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

**Why not now.** Three node shapes are valid graphs that the executor refuses
at run time, and all three refuse for one reason: `Kernel` takes a frame and
returns a frame. `dispatch.py` declines to invent the second signature before a
filter needs one, and that reasoning has not changed — a signature designed
against zero instances is a signature every kernel written afterwards is stuck
with.

**What would make it the right time.** A filter that actually needs one. Each
shape has a different trigger and they are unlikely to arrive together:

- `Mode.WINDOWED` — a filter needing a span before it can emit, e.g. a temporal
  median for background subtraction. This is the likeliest to arrive first.
- `rate_changing` — a decimator. The warmup arithmetic already handles rate
  exactly and is property-tested, so only the *call* is missing.
- Multi-upstream nodes — a filter merging two streams, which needs named ports
  on `Edge` first. That is a change to the saved artifact and to every edge ever
  written, which `filter_base.py`'s `StreamSpec` docstring already prices.

Read: `src/sieve/backend/dispatch.py` `Kernel`,
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
