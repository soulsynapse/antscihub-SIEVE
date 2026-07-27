# SIEVE — Minimal Architecture Reference

SIEVE is a video signal-processing tool built around one question: how much economy can the user buy back without losing signal? The architecture serves the ability to answer that question interactively for a representative clip, then execute the answer over the full dataset locally or on HPC.

This tool's value is first measured in speed. Speed has two distinct regimes, and both are load-bearing:

Pre-pipeline speed — from opening a video to having replicates cut and a clip selected. The intended feel is a video editor rather than a distributed system.

In-pipeline speed — from dragging a slider to seeing the graph update. The intended feel is direct manipulation rather than job submission.

## Layer Diagram

```
┌───────────────────────────────────────┐
│  gui/          cli/                   │  UI (Qt / terminal)
├───────────────────────────────────────┤
│  bench/                               │  Observation (latency checks)
├───────────────────────────────────────┤
│  pipeline/    (workers/)              │  Orchestration (DAG, executor, cache)
├───────────────────────────────────────┤
│  filters/                             │  Filter specs + their kernels
├───────────────────────────────────────┤
│  decode/   (storage/)   backend/      │  Decode / file I/O / device policy
├───────────────────────────────────────┤
│  core/      (types, filter contract)  │  Pure logic — no imports from above
└───────────────────────────────────────┘
```

Parenthesised packages do not exist yet. They are named here and declared in
`.importlinter` before their first commit, so the contract governs them on
arrival rather than being widened afterwards to accommodate them. `docs/SCAFFOLD.md`
lists them under **Projected**, and a test fails if one quietly lands without
the line moving.

The enforced consequences: `core/` imports nothing above it and no
Qt, Zarr, or subprocess. `pipeline/`, `bench/`, and `cli/` do not import Qt, so
headless and CLI runs can observe without a GUI toolkit — the QObject adapter
over the metric bus lives in `gui/`. This is the mechanism that makes CLI and
HPC parity real rather than aspirational; a violation is a product regression
rather than a style problem.

One thing this diagram implies that the linter does *not* yet check: that `gui/`
reaches `workers/` only through `pipeline/`. Because `pipeline/` and `(workers/)`
are siblings on one tier, the layers contract makes them mutually independent —
which forbids `pipeline → workers`, the very path the intent requires, and says
nothing about `gui → workers`, the one it forbids. Neither matters while
`workers/` does not exist, and both have to be settled in the commit that
creates it. Recorded in `docs/AUTO-GUARDRAILS.md` §1 as the open half of that
guardrail.

A filter is two things, and that split is what puts them on different tiers.
Its **spec** is data — id, semver, params model, declared I/O, warmup,
determinism, cost — and lives in `core/`, so a saved DAG loads and validates
structurally with no filters installed and no codec present. Its **kernels**
are code, one per backend, and live with the filter in `filters/`, free to
import `cv2` or `cupy`. `backend/` therefore holds device policy and
array-namespace helpers, never a filter's implementation: a new filter is one
module plus one markdown file, and if adding one required editing a shared
`cpu.py`, non-negotiable #3 would already be broken.

The rule is encoded as a machine-checked contract rather than
enforced by review.

---

## Non-Negotiables

|#|Rule|Meaning|
|---|---|---|
|1|Filesystem is truth _at rest_|Materialized artifacts are readable without SIEVE running. During interactive tuning, truth lives in memory.|
|2|Pipeline is a data structure|Serializable DAG. No GUI-only state in the pipeline artifact.|
|3|Filter = one class + one markdown|Discovery is automatic. No registration elsewhere.|
|4|No latency budget misses|A miss is a defect, not a tradeoff.|
|5|No regime tradeoffs|No consumer improves its latency at another's expense — across the two regimes or within one. See *Dividing the machine*.|

---

## Two Speed Regimes

```
PRE-PIPELINE (feels like a video editor)
  Open file → first frame:        < 500 ms
  Scrub/seek → frame repaint:     < 100 ms
  Scrub release → exact frame:    < 250 ms
  Cut confirmed → ready:          < 200 ms

IN-PIPELINE (feels like direct manipulation)
  First filter → first graph tick: < 2 s
  Slider drag → preview repaint:   < 100 ms
  Slider drag → graph update:      < 200 ms
  Full preview render (5–10s clip): < 3 s
  Band drag → graphs repaint:      < 50 ms
  Knob settle → graphs rebuilt:    < 3 s
  Knob settle → graphs start filling: < 500 ms
```

The two scrub budgets are a pair, and they are what makes non-negotiable #4
hold rather than being quietly excepted. A random seek into 5.3K H.264 costs
~68 ms of which ~47 ms is the container seek itself — irreducible through
OpenCV, and slower still on a slower machine. So *during* a drag the player is
held to 100 ms by degrading rather than by decoding faster: when sustained
scrub latency exceeds the budget it snaps targets to a coarse time grid and
serves them from a frame cache, which is a cache hit and costs nothing. On
release the exact frame under the cursor is always decoded, and that is the
second budget. Coarse mode is user-visible and can be disabled in Preferences;
the budget then stands unmet on that machine by the user's explicit choice,
which is a preference, not a silent tradeoff.

---

## Dividing the machine

Non-negotiable #5 was written as a two-body rule — pre-pipeline against
in-pipeline — and stayed self-enforcing only while there were two things
competing for cores. There are three. The player decodes on a thread, the
preview decodes on a pool, and `gui/detector_worker.py` runs the Morlet
transform on a third to fill the graphs while a render is still in flight. The
two-body phrasing has no slot for the case that actually bites: a third
consumer starving *both* of the other two.

The old phrasing also could not catch the specific way it would have been
broken here. `scipy.fft` defaults to every core, so a derivation thread added
without thought takes the whole machine, and the symptom is not a failure but a
scrub that stutters — a pre-pipeline budget quietly bought with an in-pipeline
nicety, which is the exact trade #5 exists to forbid.

So the rule reads over consumers rather than over regimes, and the arithmetic
is declared in one place instead of argued in three comments.
`gui/concurrency.py` holds the split and `tests/unit/test_concurrency.py`
asserts the sum leaves the machine a core for the GUI thread. A fourth
consumer, or a raised constant, fails a test rather than degrading a budget
somebody measures three commits later.

`core/` deliberately holds none of this and defaults to every core.
A CLI run, a whole-clip pass, and a headless parity check on a cluster node
have nobody to leave room for, and a cap living in `core/` would throttle
precisely the runs that should saturate a node. Policy about sharing a machine
belongs to the process that is sharing one.

---

## Import Boundaries

- `core/` — no Qt, no Zarr, no subprocess, no imports from upper layers. Holds
  the filter *contract*, never a filter implementation, so it stays free of
  `cv2` and `cupy` without constraining what a kernel may call
- `pipeline/`, `bench/`, `cli/`, `decode/`, `filters/`, `backend/` — no Qt. CLI
  and HPC must run headless, and `cli/` needs saying separately because it sits
  on `gui/`'s tier, where the layers contract cannot reach it
- `core/`, `bench/`, `gui/`, `cli/` — no `cv2`
- `filters/` — one module per filter: spec plus its kernels, colocated. May
  import `cv2` and `cupy`; may not import `pipeline/` or anything above it
- `decode/` — the only package that may reach a *frame*. That is a narrower
  claim than "the only package that imports `cv2`", and the narrower one is the
  load-bearing one: a kernel calling `cv2.GaussianBlur` touches no container, no
  seek, and no decoder identity, whereas a second path to a frame is how decoder
  identity stops being one string and cache keys stop meaning anything. What
  keeps a filter's `cv2` honest instead is its declared spec version in the
  cache key plus `backend_agnostic = False`.

`.importlinter` is the machine-checked form of this list, contract by contract,
and it is the authority wherever the two disagree.

---

## Pipeline Model

- DAG (directed acyclic graph), not a linear list
- A linear chain is valid — it's just a degenerate DAG
- Cache keys include upstream content hashes
- Materialization is user-initiated or pressure-triggered, not automatic per step

---

## Extension Pattern

```
src/sieve/filters/
  my_filter.py      ← FilterSpec (data) + one @kernel per backend (code)
  my_filter.md      ← guidance doc (discovered automatically)
```

That's it. GUI, CLI, cache, and HPC discover it without changes elsewhere. A
filter with no GPU kernel is complete; the dispatcher falls back rather than
the filter branching.

Two declarations on the spec are easy to get wrong and expensive to fix later:

- **`deterministic`** means *same backend, same input, same output*. It governs
  whether the node may be cached at all.
- **`backend_agnostic`** means the CPU and GPU kernels agree bit for bit. It
  governs whether backend identity leaves the cache key. It is false for
  essentially every float kernel — cuFFT and NumPy's FFT do not agree, and
  neither do two OpenCV SIMD paths — so it defaults to false, and claiming it
  requires an equivalence test.

**Warmup accumulates along the path, not per node**, and it does not simply
sum. `warmup_frames` is denominated in a filter's own *input* frames, so a
rate-changing node between two others leaves them speaking different index
spaces: five frames of warmup behind a 10:1 decimator is fifty source frames,
not five. `core.source_warmup_frames` walks the path sink to root, converting
`need` to `ceil(need / output_rate)` at each node, and is the only thing that
should — the executor requests `[clip_start − total, clip_end]` from it and
discards the lead-in. A plain sum compiles, runs, and under-warms every
temporal filter behind a decimator by the decimation factor, rendering a
plausible frame while doing it.

An IIR filter's warmup is nominally infinite, so the number a filter declares
is a settled-to-within-epsilon choice, and its docstring says which epsilon.