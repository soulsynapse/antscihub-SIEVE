# To Do

## Rules

1. Todo items are given a short (<5) word name.
2. Todo items are written so you don't have to load all the docs, when possible.
3. Todo items scope target is <150k context window
4. When todo items are done, do the commit and let the user know they can clear.
5. **Completion is atomic.** A finished item is *moved*, not marked: delete its
   section here and write one file at `docs/completed-todo/YYYY.MM.DD-name.md`
   from `docs/completed-todo/_TEMPLATE.md`. One file per item. This file
   therefore only ever contains work that is not done.
6. **Measurements go to `docs/findings/`, not into the completed entry.** A
   completed entry says what was built; a finding says what is true about the
   system and outlives the code that prompted it. Write the finding, link to
   it. Then `uv run nox -s docs` to rebuild both `.index.md` files.
7. **Test the load-bearing claim, not the surface.** Two or three tests per
   item that would each fail for a distinct real reason, not a sweep of every
   accessor. A property or benchmark earns its place when it pins something an
   example cannot state; otherwise an example is the better test.

---

# Build order

The items below are ordered by the layer stack in `ARCHITECTURE.md`, not by
appeal. Everything unbuilt sits above `core/`, and two of the five
non-negotiables each gate on one core module: #2 "pipeline is a data structure"
needs `core/pipeline_model.py`, and #3 "filter = one class + one markdown"
needs `core/filter_base.py`. Nothing above them — DAG, cache keys, executor,
CLI — can be written first without being rewritten after.

Items under **Independent of the stack** gate nothing and can be taken whenever.

## Filter contract

`core/filter_base.py` and `core/filter_registry.py`. The contract as *data*:
`FilterSpec`, `ParamsBase`, `ArraySpec`, `Mode`. Nothing here executes — that
is the point, and it is what lets a saved DAG validate structurally with no
filters installed and no codec present.

The spec carries: one pydantic params model (the single source of truth that
GUI widgets, CLI flags, YAML, and the cache key all read), `accepts`/`emits`
array specs, `warmup_frames`, streaming-vs-windowed, `deterministic`,
`backend_agnostic`, a cost estimate, and explicit semver.

Two flags, not one: `deterministic` means same backend, same input, same
output, and gates whether the node may be cached at all. `backend_agnostic`
means CPU and GPU kernels agree bit for bit, and gates whether backend identity
leaves the cache key. The second is false for essentially every float kernel;
default it false and make claiming it require an equivalence test.

The registry is a container and a lookup, populated from above by decorators at
import time. Core defines the shelf; `filters/` puts things on it.

Read: `docs/ARCHITECTURE.md` Extension Pattern, `docs/SCAFFOLD.md` `core/`.

## Pipeline artifact

`core/pipeline_model.py` (pydantic v2 → YAML). Nodes store `filter_id`,
`version`, and a params dict; edges store the DAG. Deliberately *not*
registry-aware: id resolution and type-chaining are `pipeline/dag.py`'s job, so
the artifact loads even when a filter it names is absent.

Replicates are the first real nodes (VISION step 2) and currently die with the
window, so this is also what makes them persist. Needs a decision on where a
project file lives relative to the source video. Guardrail to honour: no
GUI-only state in the artifact.

Read: `docs/AUTO-GUARDRAILS.md` §2, `src/sieve/core/replicates.py`.

## First filter and discovery

`sieve/filters/` — above `core/`, below `pipeline/`, free to import `cv2` and
`cupy`. One module per filter: the spec plus its kernels, colocated, one
`@kernel` per backend. A filter with no GPU kernel is complete; the dispatcher
falls back rather than the filter branching.

Kernels colocate rather than living in a shared `backend/cpu.py` for a specific
reason: if adding a filter meant editing a shared file, non-negotiable #3 is
already broken. `backend/` holds device policy, namespace resolution, and a
backend identity string — never an implementation.

Ship exactly one filter: downsample. Trivially checkable, actually useful,
exercises params, declared I/O, and streaming mode. Discovery is a `pkgutil`
scan over the package at import; guidance markdown is found by convention as
`<module>.md`.

Three tests, no more: params round-trip through JSON, cache key stable across
process restarts (this is what catches an accidental `hash()` or object id),
and every discovered filter has its markdown — the machine-checked form of
guardrail §3.

Read: `docs/AUTO-GUARDRAILS.md` §3, `.importlinter`.

## Cache key

`pipeline/cache_key.py`. `H(upstream_hash, filter_id, version,
canonical_params_json, backend_id unless backend_agnostic)`, with decoder
identity entering at the root node only. Canonical means `model_dump(mode=
"json")` with sorted keys.

Guardrail §5 belongs here: changing a parameter on one branch must not
invalidate a sibling branch.

Read: `docs/AUTO-GUARDRAILS.md` §5, `src/sieve/decode/identity.py`.

## DAG validation

`pipeline/dag.py`. Construction, cycle detection, topological sort, and the
static rejection that the declared I/O types exist to enable — resolve each
node's `filter_id` against the registry, then check that each edge's upstream
`emits` satisfies the downstream `accepts`.

Read: `docs/ARCHITECTURE.md` Pipeline Model.

## Qt-free coalescer

**Prerequisite of the executor and preview items below, not of the pure ones
above.** The earlier note said "before the first `pipeline/` commit"; that was
a proxy for "before anything decodes frames under a budget", and `cache_key.py`
and `dag.py` do neither.

`VideoPlayer._request/_issue/_drain` plus `_on_frame_ready` is ~50 lines of
cross-thread ordering — one in flight, one pending, intent-aware supersession,
monotonic display sequence — welded to `QImage` and `Signal`.
`pipeline/preview.py` needs the identical discipline against filtered frames
under `slider_to_preview`, which is the same 100 ms ceiling. Two copies will
diverge on exactly the behaviour the budget table pins.

`ScrubPolicy` is the pattern: Qt-free, tested by feeding it numbers rather
than by driving a GUI. Extract to the same shape, leave it in `gui/` until
there is somewhere lower to put it.

Read: `src/sieve/gui/{player,scrub_policy}.py`.

## Executor

`pipeline/executor.py`. The single shared execution path — CLI, GUI, and HPC
use it identically, and the GUI adds a view over it rather than a second path.
Streaming execution with cache lookup per node.

Warmup accumulates along the path, not per node: sum `warmup_frames` over the
topological path feeding a request, decode `[start − total, end]`, discard the
lead-in.

Read: `docs/SCAFFOLD.md` `pipeline/`.

## Build the CLI

`SCAFFOLD.md` calls the CLI the canonical run path, "built and tested before
GUI". It cannot literally precede a GUI that already exists, but it must
precede any further GUI work, because it is what keeps the executor honest as
the single path.

`sieve inspect` first — it proves discovery end to end in ~30 lines and turns
the layer contract's optional `sieve.cli` into a real one. Then `sieve run`
over a YAML artifact.

Read: `docs/SCAFFOLD.md` `cli/`, `.importlinter`.

## Representative clip range

The tab cuts space; the workflow also needs the 5–10 s clip that in-pipeline
tuning runs against. In/out points on the transport bar. Where it is stored is
no longer an open question once the pipeline artifact exists — it is project
state, not GUI state. Feeds `pipeline/preview.py`.

Read: `docs/VISION.md` step 4, `src/sieve/gui/replicate_tab.py`.

---

# Independent of the stack

These gate nothing below them and can be taken at any point.

## Three small GUI fixes

Each is ~10 lines, all found in the same audit, all in `gui/`.

1. `ReplicateTableModel.setData` returns `True` for a rename the document
   rejected (empty or unchanged). Qt reads that as "the model changed" and the
   user gets no feedback. The geometry path twelve lines below already returns
   `False` correctly.
2. `Preferences._store` dedupes by comparing a raw stored value against a
   typed one — the exact mismatch `_as_bool`/`_as_float` exist to absorb. Works
   on the Windows registry, always misses on INI. Route it through the same
   coercion or delete the guard and say `changed` may fire spuriously.
3. Rename `gui/frame_cache.py` -> display-proxy naming. It and the eventual
   `pipeline/cache.py` are unrelated objects (frame index vs. content hash) and
   neither name says so. Cheap now, confusing once both exist.

Read: `src/sieve/gui/{replicate_table,preferences,frame_cache}.py`.

## Drag existing boxes

Boxes can be drawn, renamed, numerically edited, and deleted, but not moved or
resized on the video. Needs corner/edge handles, hit-testing, and
`QUndoCommand.mergeWith` so one drag collapses to one undo step rather than
one per mouse-move.

Read: `src/sieve/gui/{video_view,commands}.py`.

---

## Deferred decisions

- **napari is in the `gui` extra but unused.** The viewport is a plain
  `QWidget` + `QPainter`: ~150 lines, no dependency, full control over ROI
  overlay and letterboxing. napari earns its place when the preview needs
  layered overlays with independent opacity (VISION step 4's three-way overlay
  switch). Adopt it there or drop it from the extra.
- **`gui/state.py`** from SCAFFOLD was not created. Scrub position and playing
  state live in `VideoPlayer`; a separate object would duplicate them. Create
  it when there is UI state with no natural owner (panel layout, zoom).
- **`ARCHITECTURE-TREE.md`** does not exist, and no longer obviously should.
  `docs/findings/` now holds the measurement-driven decisions one file at a
  time, and `docs/completed-todo/` holds what was built. Revisit only if
  something needs saying that neither of those can carry.
- **`hypothesis` is now used by four property modules under `tests/property/`.**
  Rule 7 above narrows what earns one going forward; the existing four stay.
