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

---

## Property tests or drop Hypothesis

`tests/property/` is an empty package and `hypothesis` is a dev dependency
with zero users — coverage that reads as existing and does not. Either write
the four that earn it (`ROI.clamped_to` always lands inside bounds with
positive extent, `ROI.from_corners` is corner-order-independent,
`ScrubPolicy.snap` is idempotent, `ReplicateSet.next_default_name` never
collides) or delete the directory and the dependency together.

Read: `src/sieve/core/types.py`, `src/sieve/gui/scrub_policy.py`.

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

## Qt-free coalescer

**Do this immediately before the first `pipeline/` commit, not after.**

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

## Persist replicates

Replicates live only in memory and die with the window. They are DAG nodes
(VISION step 2), so this is the first real use of the pipeline artifact.

Needs `core/pipeline_model.py` (pydantic v2 → YAML) and a decision on where a
project file lives relative to the source video. Blocks anything that has to
survive a restart. Guardrail to honour: no GUI-only state in the artifact.

Read: `docs/AUTO-GUARDRAILS.md` §2, `src/sieve/core/replicates.py`.

## Representative clip range

The tab cuts space; the workflow also needs the 5–10 s clip that in-pipeline
tuning runs against. In/out points on the transport bar, stored per replicate
or per project — decide which. Feeds `pipeline/preview.py` later.

Read: `docs/VISION.md` step 4, `src/sieve/gui/replicate_tab.py`.

## Drag existing boxes

Boxes can be drawn, renamed, numerically edited, and deleted, but not moved or
resized on the video. Needs corner/edge handles, hit-testing, and
`QUndoCommand.mergeWith` so one drag collapses to one undo step rather than
one per mouse-move.

Read: `src/sieve/gui/{video_view,commands}.py`.

## Build the CLI

`ARCHITECTURE.md` calls the CLI the canonical run path, "built and tested
before GUI". It does not exist. Typer app with `sieve inspect` at minimum, so
the layer contract's optional `sieve.cli` layer stops being hypothetical.

Read: `docs/SCAFFOLD.md` `cli/` section, `.importlinter`.

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
