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
8. **Start by building a checklist.** Before the first edit, read what the item
   points at and put the steps in the task list, one per file or gate — the
   module, the tests, the contract change, the gate run, the completed entry.
   It is what makes the work visible while it is happening rather than only in
   the diff, and an item whose steps cannot be listed up front is an item whose
   scope has not been read yet.
9. **Work that is real but not yet timely goes to `docs/LATER.md`.** Rules 2
   and 3 are what this file is: an item here is scoped and startable. Something
   understood, wanted, and deliberately deferred fails both and would sit here
   growing stale — so it is written there instead, with the trigger that makes
   it takeable, and *moved* here when the trigger fires.

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
writes — see
`docs/completed-todo/2026.07.25-per-replicate-parameter-deviation.md`. The
replicate table renders which arenas that deviation has actually separated,
derived on every read, so the GUI is no longer silent about it.

Neither `sieve.filters`, `sieve.backend`, nor `sieve.pipeline` is parenthesised
in `.importlinter` any more. One filter exists and is found by a `pkgutil` scan
that names nothing, so `cache_key.py` had a real params model to canonicalize
and a real `backend_identity` to include, and it is now written: nothing further
needs to decide what a key is made of — see
`docs/completed-todo/2026.07.25-cache-key.md`.

The walk that folds those keys into a graph is written too. `pipeline/dag.py`
resolves every node against the registry, rejects cycles and edges whose
declared types cannot chain, and produces the topological order — one order per
document, not per traversal — that the executor is to schedule in and that
`node_keys` already walks. Nothing below needs to sort a graph again; it takes
`Dag.order`. See `docs/completed-todo/2026.07.25-dag-validation.md`.

The per-replicate threshold-spread probe that sat at the top of this list is
gone, not deferred: it would have measured one rack under one backlight, and the
scope-of-edit control it was meant to choose a default for is required whether
arenas cluster or spread. Reasoning in
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.

The coalescer that gated the two items below is extracted:
`gui/coalescer.py` holds the two slots, the rank rule, the display ordering,
and the source stamp, Qt-free and tested by feeding it calls, so
`pipeline/preview.py` inherits that discipline rather than reimplementing it.
See `docs/completed-todo/2026.07.25-qt-free-coalescer.md`.

The graph now runs. `pipeline/plan.py` derives everything about a run that is
knowable before a frame is decoded — resolved params, keys, and the source
lead-in as a backward max over `Dag.order` — `pipeline/cache.py` holds the store
protocol, and `pipeline/executor.py` is the one loop all three front ends call.
Nothing below needs to invent an execution path, a warmup arithmetic, or a
cache lookup; it takes these. `Mode.WINDOWED`, rate-changing, and multi-upstream
nodes are refused at run time until `Kernel` grows a second signature. See
`docs/completed-todo/2026.07.25-executor.md`.

The CLI that had to precede further GUI work exists. `sieve inspect` prints a
filter's declaration and its guidance, `sieve run` executes a YAML project
through `pipeline/executor.py`, and `sieve.cli` is no longer parenthesised in
`.importlinter` — it is bound by the headless and opencv-containment contracts
as well as by the layer stack. The executor now has a caller that cannot reach
a frame any other way, which is what the SCAFFOLD ordering was for. Three of
SCAFFOLD's five command modules are deliberately unwritten: each wraps a
`pipeline/` module that does not exist, and they arrive with it. See
`docs/completed-todo/2026.07.25-build-the-cli.md`.

The tab now cuts time as well as space. In and out points are marked at the
playhead, painted on a strip under the transport, and clamped to the source;
`ReplicateDocument.clip` is where they live and `SetClip` is the only thing
that writes it. `pipeline/preview.py` therefore has a span to be given when it
is built, and does not have to invent one. See
`docs/completed-todo/2026.07.25-representative-clip-range.md`.

No item in the build order remains. What is left is under **Independent of the
stack** below — those gate nothing and can be taken whenever — and in
`docs/LATER.md`, whose triggers are what promote work back to this file.

---

# Independent of the stack

These gate nothing below them and can be taken at any point.

## The timeline replaces the transport

**The standard.** One full-width band across the bottom of the window, below
the tabs and outside them, is the user's anchor: it spans the whole asset, it
carries the working window, the playhead, and — as they arrive — what has been
examined and what was found. It is present in every tab and says the same thing
in each, so the answer to "where am I and what is the state of this clip" never
depends on which tab is showing. It **supersedes** the per-video seeker: the
slider and `ClipStrip` under the viewport go away, and `replicate_tab.py`'s
left pane becomes the picture and nothing else.

**What is buildable now** — navigation and the window. The layers that paint
results are in `LATER.md`, gated on there being results to paint.

1. **The clip is a window, not two marks.** Mark-in / mark-out are two
   independent indices, so `mark_clip_in` past the out point releases the out
   point to the end of the source and the span's *length* changes. The user's
   gesture is "keep the ten seconds, move them", which the current model cannot
   express. Origin plus held length replaces it.
2. **The window bounds playback.** `[start, stop)` loops, the last frame shown
   before looping is `stop - 1`, and the playhead is always inside it.
   `player.py` has never heard of the clip.
3. **The strip is the position control.** Click inside the window: seek. Click
   outside: move the window so the clicked frame is in it, preserving length
   and clamping at the ends, then seek. Drag scrubs continuously but decodes
   coalesce to the newest position — press, move, and release are three
   different claims and V1 emits three signals for that reason.
4. **The row above it** carries Play, window start, window length, and the
   timestamp — hard right, per the reference. Full width, with the strip under
   it.
5. On open there is **always** a window: 10 s, or the whole asset if shorter,
   playhead at its start, paused.

`ClipRange(start, end)` stays as it is. `(start, end)` and `(start, length)`
carry identical information and `frame_count` is already `end - start`, so
which one is held constant under an edit is an interaction rule and not a
storage one: no schema change, and `pipeline/plan.py` keeps reading a half-open
span. Point 5 is a *tuning-session* rule and must not become a document rule —
`Project.clip = None` meaning "the whole video" is what `plan.py` falls back on
and what the HPC handoff produces by dropping the field.

**Geometry goes in a Qt-free model**, tested by feeding it calls, the way
`gui/coalescer.py` is. Frame↔column mapping, the window-move rule, and the
clamp are arithmetic, and they are the part that is wrong at the first and last
frame of every video if it is written inline in a `paintEvent`.

Read: `src/sieve/gui/{document,clip_bar,replicate_tab,player,coalescer}.py`,
and in V1 `gui/explorers/detection_timeline.py` — `_Strip` for the paint and
scrub contract, `DetectionNavigator` for the readout around it.

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
