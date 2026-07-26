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

What remains is the in-pipeline regime, which has budgets, a plan, an executor,
a metric bus, and no code that can reach any of it. The four items below are the
tuning loop VISION step 4 describes, in dependency order: each says what it is
gated on, so an item can be taken out of order when its gate is already clear
rather than because it is next in the list.

## The representative-clip preview

**Gated on: nothing.** `bench/metrics.py` exists, so this is born instrumented
rather than retrofitted — publish `slider_to_preview` and `full_preview_render`
to a `MetricBus` the caller passes in, the way `gui/player.py` publishes
`scrub_to_repaint`. See `docs/completed-todo/2026.07.26-the-metric-bus.md`.

`pipeline/preview.py` is the last unwritten module in the layer stack and three
things in this repo were already built pointing at it. `gui/coalescer.py` was
extracted Qt-free so preview inherits the two slots, the rank rule, and the
source stamp rather than reimplementing them. `pipeline/plan.py`'s docstring
says preview needs the same lead-in arithmetic and that `source_warmup_frames`
is the only thing that should compute it. `ReplicateDocument.window` is the
span, and it exists so preview does not have to invent one.

What it is: a run of `execute` over the working window that can be re-run on a
parameter edit without re-decoding what did not change, coalesced so a slider
drag discards the renders nobody would have seen. `slider_to_preview` (100 ms)
and `full_preview_render` (3 s) are its budgets and are what say whether it
works.

The thing to get right, because it is the reason this is a module and not a
loop in the GUI: **a parameter edit invalidates a suffix of the graph, not the
graph.** `cache_key.py` already derives keys that include upstream hashes, so
the nodes above an edited one keep their entries and the nodes below lose
theirs. A preview that re-runs from the source on every edit will meet the 3 s
budget on the one filter that exists and miss it on the third.

`cli/preview_cmd.py` arrives with this. SCAFFOLD's five command modules were
deliberately left at three because each wraps a `pipeline/` module that does
not exist yet, and `sieve preview` is the headless run of exactly this — which
is also what keeps the GUI from becoming a second execution path.

Read: `src/sieve/pipeline/{plan,executor,cache,cache_key}.py`,
`src/sieve/gui/coalescer.py`, `docs/completed-todo/2026.07.25-executor.md`,
`docs/completed-todo/2026.07.26-the-timeline-replaces-the-transport.md`.

## A kernel that can remember

**Gated on: nothing, but worth little before the preview above can show it.**

`core/filter_base.py` carries the most carefully built arithmetic in the repo:
`warmup_frames` converted sink-to-root through each node's `output_rate`,
monotone in its second argument, property-tested in
`tests/property/test_warmup.py`, with `ExecutionPlan.lead_in_shortfall`
reporting a window too near the start of the source to warm. `plan.py` decodes
the lead-in and `executor.py` discards it.

No filter declares a nonzero `warmup_frames`, and none can use one if it did:
`Kernel` is `(frame, params) -> Frame`, positional-only, with nowhere to put
state. A warmup exists to settle state across frames. So the lead-in is
currently decoded and thrown away on behalf of state the protocol cannot hold,
and every test of that arithmetic is a test of a function with no consumer.

`LATER.md`'s "A kernel protocol that is not one frame in, one frame out" names
three shapes — `Mode.WINDOWED`, rate-changing, and multi-upstream — and this is
not one of them. A stateful streaming filter *is* one frame in, one frame out.
It only needs somewhere to keep what it learned from the last one, which is the
cheapest of the four changes and the only one that validates work already paid
for.

Two halves, and the second is what stops the first being designed against
nothing:

1. Somewhere for per-run kernel state to live. It belongs to the *run*, not to
   the kernel object — two replicates previewing the same node concurrently are
   two states, and a kernel that closes over its own would silently mix them.
   That is the constraint the shape has to satisfy; `dispatch.py`'s reasoning
   about not inventing a signature before a filter needs one applies here as
   much as it does to WINDOWED, so this item writes the filter too.
2. One temporal filter declaring a nonzero `warmup_frames`. An exponential
   moving-average background model is the smallest honest one: it is VISION
   step 3's category C, its warmup is nominally infinite so it must declare a
   settled-within-epsilon number and say which epsilon in its docstring —
   exactly the case `filter_base.py` describes and nothing exercises — and
   background subtraction is what VISION step 1 names first.

This is also the second filter, which most of `LATER.md` is waiting on: several
entries there trigger on "a filter that needs it", and one filter that is
stateless, rate-preserving, single-upstream, and float-free triggers none of
them.

Read: `src/sieve/backend/dispatch.py` `Kernel`,
`src/sieve/core/filter_base.py` `warmup_frames`/`source_warmup_frames`,
`src/sieve/pipeline/plan.py` `lead_in_shortfall`,
`src/sieve/filters/downsample.py`, `docs/LATER.md` kernel-protocol entry.

## The first live graph tick

**Gated on: the preview.** The metric bus half of this gate is clear —
`bench/metrics.py` exists and `MetricBus.subscribe` is the shape the adapter
wraps. What is still missing is anything publishing an in-pipeline span, which
is the preview.

`gui/executor_adapter.py` is defined in ARCHITECTURE as the *only* coupling
point between the executor and Qt: a QObject that subscribes to the bus and
re-emits as signals. `Subscriber` is called on the publishing thread, so the
adapter's job is specifically to get from there to the GUI thread — a queued
signal emission, which is the reason the bus does not try to do it itself. Everything else in `gui/` learns about a run through it.
`gui/graph_hud.py` is the pyqtgraph view — `pyqtgraph` is already in the `gui`
extra and imported by nothing.

`filter_to_first_tick` (2 s) and `slider_to_graph` (200 ms) are the budgets,
and the first of them is the one that has never been measurable: it is the
whole "you get feedback on how expensive this is getting" claim in VISION step
4, and until something ticks, that claim has no implementation.

VISION also asks for a vertical bar showing where in the clip the graph is
currently at. `gui/timeline_bar.py` already draws a playhead over a span and
`gui/timeline_model.py` holds that arithmetic Qt-free; the graph's cursor is
the same value in a second view, not a second source of truth.

Read: `src/sieve/gui/{timeline_bar,timeline_model}.py`,
`src/sieve/bench/budgets.py` in-pipeline entries, `docs/SCAFFOLD.md`
`gui/graph_hud.py` and `gui/executor_adapter.py`, `docs/VISION.md` step 4.

## The three-way overlay

**Gated on: the preview.** It is a view over previewed frames and has nothing
to show without them.

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
  reason and with the same resolution: **The first live graph tick** above is
  where it is used or dropped.
- **`gui/state.py`** from SCAFFOLD was not created. Scrub position and playing
  state live in `VideoPlayer`; a separate object would duplicate them. Create
  it when there is UI state with no natural owner (panel layout, zoom).
- **`ARCHITECTURE-TREE.md`** does not exist, and no longer obviously should.
  `docs/findings/` now holds the measurement-driven decisions one file at a
  time, and `docs/completed-todo/` holds what was built. Revisit only if
  something needs saying that neither of those can carry.
- **`hypothesis` is now used by four property modules under `tests/property/`.**
  Rule 7 above narrows what earns one going forward; the existing four stay.
