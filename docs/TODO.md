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

*The last clause of that paragraph was wrong and is left standing rather than
edited: `pipeline/preview.py` cannot inherit anything from `gui/coalescer.py`,
because the layers contract puts `sieve.gui` above `sieve.pipeline`. The
extraction is still load-bearing and the beneficiary is the GUI's preview panel,
which will coalesce renders the way `player.py` coalesces frame requests —
reasoning in
`docs/completed-todo/2026.07.26-the-representative-clip-preview.md`.*

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

The application now cuts time as well as space, and does it from one place. A
full-width band below the tabs spans the whole asset and carries the working
window and the playhead; the window holds its length under every edit, bounds
playback, and is the only thing `player.py` will let the playhead be inside.
`ReplicateDocument.clip` is still where a *chosen* span lives and `SetClip` is
still the only thing that writes it — `window` is the derived view that falls
back to ten seconds until the user chooses, so a project saved before they do
still carries no clip at all. The arithmetic is Qt-free in
`gui/timeline_model.py`. `pipeline/preview.py` therefore has a span to be given
when it is built, and does not have to invent one. See
`docs/completed-todo/2026.07.26-the-timeline-replaces-the-transport.md`.

A timing now has somewhere to go. `bench/metrics.py` is the Qt-free collection
bus — publishers hand it `(budget key, elapsed_ms)`, consumers subscribe, and
the sample is judged against `BUDGETS` on the way past — and `gui/player.py` is
its first producer. Nothing below needs to invent a callback to report through
or a place to compare a duration against a ceiling. See
`docs/completed-todo/2026.07.26-the-metric-bus.md`.

A kernel can now keep state across frames, so the warmup arithmetic has a
consumer. `KernelBinding.start` mints one state per `execute` — the lifetime is
the generator's, which is what makes two concurrent previews two models — and
`background_ema` is the second filter and the first declaring a nonzero
`warmup_frames`. A stateful node is deliberately uncacheable, and the reason is
not the obvious one: see
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md` before
assuming a cache key could carry it. Also see
`docs/completed-todo/2026.07.26-a-kernel-that-can-remember.md`.

The in-pipeline regime now runs. `pipeline/preview.py` re-renders the working
window on a parameter edit and pays only for the nodes below the edit — 3.3 ms
where the cold render was 1350 ms — and `sieve preview` is its headless caller,
so both in-pipeline budgets have a producer and `--check` is an exit code.
Nothing below needs to invent a re-render, a store lifetime, or a way to
publish a span: it takes `PreviewSession`. Two things it settled that the two
items below inherit — the coalescing belongs to the GUI panel rather than to
`pipeline/` because `gui/coalescer.py` is above that layer, and the 3 s ceiling
is met by the *store* rather than by anything being fast, since a warm re-render
after an edit is 3.3 ms against a cold render's 1350 ms. See
`docs/completed-todo/2026.07.26-the-representative-clip-preview.md`.

Measuring that put a number on the cold render, and chasing why it was 22 ms per
frame took the reader as far as it goes. `decode/prefetch.py` reads a span on N
threads for a measured 1.61x — 24.50 ms/frame to 15.25 — and `--workers` on both
commands is where a cluster sets it, absent from the project document because
machine capability is not part of a reproducible artifact. What the same
investigation established is that the *remaining* 6x is not a threading problem:
the wall past four workers is a 47.6 MB BGR array allocated and freed per frame,
so the routes that would reach ffmpeg's 2.95 ms are the ones where the frame gets
smaller — cropping before the convert, or the luma plane alone — and each of those
changes what a pixel is and needs a cache generation. Nothing below should treat
decode speed as an open question without reading
`docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-stops.md` and
`docs/findings/2026.07.26-the-convert-is-single-threaded-not-expensive.md` first;
that work is deliberately not an item, because taking it means choosing a route
and no measurement chooses one.

The GUI now computes a frame. `gui/preview_runner.py` holds a `PreviewSession`
on a thread of its own, renders the document's graph over the working window,
and emits what each frame cost keyed by its source index;
`gui/executor_adapter.py` is the one place that knows both `bench/metrics.py`
and Qt, and gets a `Sample` from a publishing thread to the GUI thread by queued
signal. `filter_to_first_tick` therefore has a producer for the first time —
armed when a non-empty graph is first submitted, published when the first frame
has crossed to the GUI thread, which is what makes it a number about what the
user waited for rather than about what the render did. Nothing below needs to
invent a render thread, a cancellation, or a per-frame series: it takes
`PreviewRunner`. See
`docs/completed-todo/2026.07.26-the-first-live-graph-tick.md`.

The two items below are what is left of the tuning loop VISION step 4 describes.
Both were gated on the preview and neither is any longer.

## The graph HUD

**Gated on: nothing.** The producer it draws exists.
`gui/preview_runner.py` renders the working window on the render thread and
emits `frame_cost(source index, ms)` per frame on the GUI thread, plus
`render_started(revision)` when a series is about to be replaced and
`render_finished(PreviewRender)` when it is complete. `gui/executor_adapter.py`
carries the bus's whole-render samples across the same boundary. Both are
tested; neither is drawn anywhere. See
`docs/completed-todo/2026.07.26-the-first-live-graph-tick.md`.

`gui/graph_hud.py` is the pyqtgraph view. **x is the source frame index across
the working window and y is milliseconds for that frame** — not sample arrival
order, which is the axis a naive HUD over `MetricBus` would have and which
cannot carry the next paragraph. `pyqtgraph` is in the `gui` extra and imported
by nothing; this is where it is adopted or dropped, and leaving it installed and
unused a third time is not an option.

VISION asks for a vertical bar showing where in the clip the graph is currently
at, and with that axis it is the playhead: `gui/timeline_bar.py` already draws
it over a span and `gui/timeline_model.py` holds the arithmetic Qt-free, so the
graph's cursor is `VideoPlayer.frame_changed` in a second view rather than a
second source of truth.

Two things the runner settled that this inherits. **The series is replaced, not
appended to** — `render_started` carries a revision and a superseded render's
frames never arrive, so the HUD holds one window's worth of points and clears on
that signal rather than deciding for itself what is stale. And **the repaint
must be throttled here**, not upstream: a cold render delivers six hundred
frames and a HUD repainting per point would spend the GUI thread on paint while
the render thread waits behind it on the event queue.

`filter_to_first_tick` (2 s) now has a producer and `slider_to_graph` (200 ms)
does not — it is gated on a parameter control existing at all, and is written up
in `docs/LATER.md` rather than left here.

Read: `src/sieve/gui/preview_runner.py` signals,
`src/sieve/gui/{timeline_bar,timeline_model}.py`, `docs/SCAFFOLD.md`
`gui/graph_hud.py`, `docs/VISION.md` step 4.

## The three-way overlay

**Gated on: nothing.** It is a view over previewed frames, and
`PreviewSession.render_window` delivers them one at a time to a consumer the
caller passes in — which is the shape a viewport wants. The demand this item
makes that nothing else does is two frames from *different nodes* at the same
source index: `FrameResult` already carries every node's output for one frame,
so the demand is satisfied by indexing it rather than by a second render.

VISION step 4 asks the viewport to switch between three things: the raw video,
the full current state with every operation applied, and the contribution of
the *current* operation relative to the one immediately before it. The third is
the one that carries the product's argument — it is how a user sees what a
filter bought — and it is also the one that needs two frames from different
nodes at the same source index, which is a demand on the preview's cache rather
than on the painter.

This is where the napari question under **Deferred decisions** below gets
answered rather than re-asked. The present viewport is a `QWidget` +
`QPainter`, and the entry says napari earns its place when the preview needs
layered overlays with independent opacity. That is this item. Adopt it here or
drop it from the `gui` extra — either is fine, and leaving it installed and
unused a third time is not.

Read: `src/sieve/gui/video_view.py`, `docs/VISION.md` step 4, the napari entry
under **Deferred decisions** below.

---

# Independent of the stack

These gate nothing below them and can be taken at any point. The three small
GUI fixes that sat here are done — see
`docs/completed-todo/2026.07.26-three-small-gui-fixes.md`, which also records
why the preferences one could not be tested the obvious way.

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
  switch). Adopt it there or drop it from the extra. That moment now has an
  item — **The three-way overlay** above — so this bullet is answered there
  rather than deferred a third time.
- **`pyqtgraph` is in the `gui` extra and imported by nothing**, for the same
  reason and with the same resolution: **The graph HUD** above is where it is
  used or dropped. That item is no longer waiting on anything to plot — the
  series exists and is emitted — so the next pass at it either adopts the
  dependency or writes the view with `QPainter` and drops it from the extra.
- **`gui/state.py`** from SCAFFOLD was not created. Scrub position and playing
  state live in `VideoPlayer`; a separate object would duplicate them. Create
  it when there is UI state with no natural owner (panel layout, zoom).
- **`ARCHITECTURE-TREE.md`** does not exist, and no longer obviously should.
  `docs/findings/` now holds the measurement-driven decisions one file at a
  time, and `docs/completed-todo/` holds what was built. Revisit only if
  something needs saying that neither of those can carry.
- **`hypothesis` is now used by four property modules under `tests/property/`.**
  Rule 7 above narrows what earns one going forward; the existing four stay.
