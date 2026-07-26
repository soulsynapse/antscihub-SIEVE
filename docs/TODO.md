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
appeal. Neither of the two non-negotiables that gated on a core module still
does: #3 "filter = one class + one markdown" has `core/filter_base.py` and
`core/filter_registry.py`, and #2 "pipeline is a data structure" now has
`core/pipeline_model.py`. The filter contract can express rate, stream kind,
and output size, so `dag.py`'s edge check and the executor's warmup arithmetic
both have declarations to be written against.

No `core/` item remains. Per-replicate parameter deviation, the last one, has
landed: `Replicate.overrides` holds the deviation, `resolved_params` is the one
definition of effective params, and `Project.with_param_edit` performs the two
writes. `cache_key.py` therefore has something to hash that is not `Node.params`
— see `docs/completed-todo/2026.07.25-per-replicate-parameter-deviation.md`.
The replicate table renders which arenas that deviation has actually separated,
derived on every read, so the GUI is no longer silent about it.

`sieve.filters` and `sieve.backend` are no longer parenthesised in
`.importlinter`: one filter exists, registers itself by being importable, and is
found by a `pkgutil` scan that names nothing. So the cache key below has a real
params model to canonicalize and a real `backend_identity` to include — see
`docs/completed-todo/2026.07.25-first-filter-and-discovery.md`.

The per-replicate threshold-spread probe that sat at the top of this list is
gone, not deferred: it would have measured one rack under one backlight, and the
scope-of-edit control it was meant to choose a default for is required whether
arenas cluster or spread. Reasoning in
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.

Items under **Independent of the stack** gate nothing and can be taken whenever.

## Cache key

`pipeline/cache_key.py`. `H(upstream_hash, filter_id, version,
canonical_params_json, backend_id unless backend_agnostic)`, with decoder
identity entering at the root node only. Canonical means `model_dump(mode=
"json")` with sorted keys.

`canonical_params_json` is the *resolved* params for this node and replicate,
not `Node.params`: build it from `pipeline_model.resolved_params`, never from
the node's dict, which is now only the default unconfigured replicates inherit.

Guardrail §5 belongs here: changing a parameter on one branch must not
invalidate a sibling branch.

Read: `docs/AUTO-GUARDRAILS.md` §5, `src/sieve/decode/identity.py`,
`src/sieve/backend/identity.py`.

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

Warmup accumulates along the path, not per node, and does not simply sum —
`core.source_warmup_frames` converts across rate-changing nodes and is the only
thing that should. Decode `[start − total, end]`, discard the lead-in.

The root consumes the replicate's ROI crop on every frame, whether or not a
materialized crop exists on disk. The materialized one is a checkpoint and a
performance decision; letting its presence decide what the graph is handed
would make a cache question into a semantic one and break the rule that
checkpoints are never hashed.

Read: `docs/SCAFFOLD.md` `pipeline/`,
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.

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
tuning runs against. In/out points on the transport bar. Storage is settled —
`ClipRange` is on `Project`, half-open frame indices — so what is left is the
transport-bar UI and feeding `pipeline/preview.py`.

Read: `docs/VISION.md` step 4, `src/sieve/gui/replicate_tab.py`.

---

# Independent of the stack

These gate nothing below them and can be taken at any point.

## Open and save a project

`core/pipeline_model.py` exists, so replicates *can* persist; nothing in the
GUI yet does it, and they still die with the window. Needs File > Open Project
/ Save / Save As, a dirty flag driven off `QUndoStack.cleanChanged`, and a
prompt on close. Opening a video offers its `project_path_for` neighbour when
one exists.

This is independent of the CLI despite SCAFFOLD's "CLI before further GUI
work". That rule exists so the executor stays the single execution path, and
reading and writing a document touches no execution path at all.

The awkward part is `bind_source`, which clears replicates and history on every
open because geometry in one video's pixel space cannot carry to another.
Loading a project has to populate the set *after* that clear without pushing
undo commands, so it needs a load path beside the command-facing primitives
rather than through them.

Read: `src/sieve/gui/{document,main_window}.py`, `src/sieve/core/pipeline_model.py`.

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
