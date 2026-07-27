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

The per-frame series is now drawn. `gui/graph_hud.py` plots what each frame of
the working window cost — source index on x, milliseconds on y, the playhead as
its cursor — sits in the filter tab's left column under the D row, clears on
`render_started` rather than deciding staleness for itself, throttles its own
repaint to one trailing flush per burst, and is the first thing to draw the
bus's whole-render verdicts, red on a miss. It is `BandPlot` with the handle
machinery suppressed, so a drag on a cost spike scrubs to it. See
`docs/completed-todo/2026.07.26-the-graph-hud.md`.

The step composite — what was left of the tuning loop VISION step 4 describes —
is drawn. Clicking a card in the chain stack selects that step, and the pane at
the top of the filter tab's left column draws the step's output over its input
at one opacity: the tail selected *is* the full current state, the first step at
full opacity *is* the source, so the three-way overlay stayed collapsed to one
view. The pair is grabbed out of `FrameResult`s the render already produced —
never a second render, never fed back into the graph — and playhead refreshes
are suppressed while a window render is outstanding so they can never displace
the graphs' render from the runner's one pending slot. The napari question
closed with it: two layers and one slider is QPainter. See
`docs/completed-todo/2026.07.26-the-step-composite.md`.

---

# The temporal chain

The four items below are what REFINED-VISION's closing section — "Temporal
signal-amplification-of-kind" — decomposes into once it is read as a specification
rather than as a sketch. That reading is written up beneath the vision itself, in
`docs/REFINED-VISION.md` under **What "signal amplification of kind" is, and what
has to be built for it**; each item below points at its lettered section there
rather than restating the argument.

They are ordered, and the order is not the order of appeal. Reasoning is in that
document's closing **Build order** section, but the short form is: the stateless
discriminant comes first because it may make the stateful one unnecessary for the
flagship example, the artifact-touching change comes early because migrations get
worse with age, and the units come before the filter whose thresholds are
denominated in them.

The stateless discriminant that led this section is built: `block_signal` now
emits `coherence` — how much of a block's change one translation explains, in
[0, 1] — so "high `change_energy`, low `coherence`" is a grooming detector
with no state and no time constants. The scalar shipped is *not* the one the
spec drafted: `((λ₁-λ₂)/(λ₁+λ₂))²` fails its own translation test, and the
correct pair is the smaller two — see
`docs/findings/2026.07.26-the-specs-coherence-formula-fails-its-own-test.md`
and `docs/completed-todo/2026.07.26-coherence-as-a-third-block-signal.md`.
Whether it makes the motion history filter unnecessary for the flagship
example is now a question real footage can answer from the quick-switch.

## Multi-upstream kernels

**Gated on: nothing, and it gates everything else in this section.** Promoted
from `LATER.md`'s "A kernel protocol that is not one frame in, one frame out" on
2026.07.26 — that entry asked for "a filter that actually needs one" as the
trigger, and REFINED-VISION's temporal section is nothing but combinations. The
other two shapes in that entry, `Mode.WINDOWED` and `rate_changing`, stay
deferred: they have separate triggers and no reason to arrive together.

**Why it is unavoidable rather than convenient.** Every kind-amplifier worth
building is a combination of channels — that is what makes it a discriminant
rather than a filter. "High energy AND low coherence", "accumulated signal gated
against its own baseline", "score compared against its null" are all two-input
nodes. `pipeline/executor.py` raises `UnrunnableNodeError` on any node with more
than one upstream, so the whole section is currently unbuildable.

**What it involves.** `core/filter_base.py`'s `StreamSpec` docstring already
prices the central change: **named ports on `Edge`**, which touches the saved
artifact and every edge ever written, so it wants a migration path decided rather
than discovered. Then a second `Kernel` signature taking a mapping of port name
to `Frame`; `dag.py`'s edge type-check running per port rather than per node;
`plan.py`'s lead-in becoming a backward max over *all* upstreams of a node rather
than the one; and `executor.py` holding a frame from each upstream until every
port for an index has arrived — which is the first place in the executor where
two streams have to be *aligned by index* rather than consumed in order, and is
the part most likely to be got subtly wrong when the two upstreams have different
`warmup_frames`.

The precedent `background_ema` set applies and is worth stating up front:
whatever a merging kernel needs to be handed, it is handed by
`KernelBinding.start` and not by a registry entry.

Read: `src/sieve/core/filter_base.py` `StreamSpec`,
`src/sieve/backend/dispatch.py` `Kernel`/`StatefulKernel`,
`src/sieve/pipeline/executor.py` `UnrunnableNodeError`,
`src/sieve/pipeline/{dag,plan}.py`, `docs/REFINED-VISION.md` **G**.

## Per-block temporal baseline

**Gated on: nothing to build it, but it is worth more after multi-upstream
lands**, because the natural consumer is a node that takes the signal and its
baseline as two ports rather than one that recomputes the baseline internally.

**The problem.** `change_energy` is in (intensity)²/frame, so its magnitude
depends on illumination, gain, exposure, and animal-substrate contrast. A
threshold tuned on one replicate under one backlight is a number about that
lighting rig — which collides directly with the two things SIEVE promises
hardest: replicates sharing a pipeline, and an artifact that reproduces.
`normalize` does not solve this and is not meant to: it removes the *global*
per-frame illumination component and gives no per-block baseline over time.

**The fix.** Estimate each block's own null over a trailing or centered window
and emit the signal in units of deviation from it. **Robust statistics —
median and MAD, not mean and standard deviation** — because the events are in the
sample and would inflate the spread they are being measured against. This is the
standard procedure in spike sorting (thresholding at k·MAD of the filtered trace)
and the same instinct behind fMRI reporting percent signal change rather than
scanner units. A threshold of "4 MADs above this block's baseline" transfers
across replicates and lighting; "0.03 energy units" never will.

**The parameter that has no correct value, and is therefore primary:** the
baseline window. Too short and a sustained behaviour becomes its own baseline and
vanishes; too long and it stops tracking drift. Same shape of argument as
`background_ema`'s `alpha`, and the same conclusion.

Read: `src/sieve/filters/normalize.md` (what it does *not* do),
`src/sieve/filters/background_ema.py` (the warmup argument this will reuse),
`docs/REFINED-VISION.md` **A**.

## The motion history filter

**Gated on: nothing structurally** — it is single-upstream, streaming,
rate-preserving and stateful, which is the shape `background_ema` already
established, down to the buffer discipline and the worst-case `warmup_frames`
argument. It is ordered last because its thresholds want the units from
**Per-block temporal baseline** and its output wants somewhere to be combined,
and building it first means tuning it twice.

**What it is.** The vision's "exponential decay function and a blooming touch
function", which is `a[t] = λ·(K ⊛ a[t−1]) + (1−λ)·s[t]` — the semi-implicit
Euler step of `∂a/∂t = −a/τ + D∇²a + s`. VISION step 3 category C already names
MEI and MHI, and this is them: Bobick & Davis's Motion History Image is the same
operator with a linear decay law. Name it for them so a user can find the
literature.

**Four decisions the item has to make, all argued in REFINED-VISION C:**

- **Decay and coupling are one node, two parameters.** Blurring the output of a
  leaky integrator is a different operator — in the recursion the coupling
  compounds through the feedback path.
- **Parameters in physical units.** `tau_seconds`, not λ; `reach_blocks`, not κ.
  `fps` plumbs in exactly as `block_signal`'s does and for the same reason.
- **Two coupling modes.** `diffuse` (linear, conservative, spreads the peak
  *down* and fights the threshold) and `dilate` (grayscale morphological,
  sustains support without lowering peaks). Expect `dilate` to win; ship both,
  because this is one of the things "much testing" is about.
- **Group delay is declared or removed.** A causal integrator lags its event by
  order τ, and mixing it with `windowed_mean`'s `centered` mode biases reported
  onsets late by an amount nothing writes down. Either run forward-and-backward
  for zero phase (legitimate offline) or declare the delay. Not neither.

**The stability bound is the test worth writing.** With `reach` unbounded the
dilation form propagates one detection outward at one block per frame until it
fills the arena. A test that runs a single-block impulse through a long run and
asserts the support stops growing is the one that would catch a beautiful demo
that is wrong.

Read: `src/sieve/filters/background_ema.py` (the twin), `src/sieve/core/detection.py`
(the tail this feeds), `docs/REFINED-VISION.md` **C**, `docs/VISION.md` step 3
category C.

---

# The replicate tab

The two items below are REFINED-VISION's **Replicates** section read as a
specification rather than as a description. That section was written after the
wizard workflow was decided, and it asks the tab to do two things it does not
do: to be where a crop is *shaped* — a stamp, a drag, a magnifier, numbers —
and to be where a replicate is *chosen*, which is the act that sends the user
to the filter tab with that arena under them.

They are ordered, and for once the cheap one is first because it is also the
one that makes the tab mean anything. The executor has cropped per replicate
since it was written — `executor.py` takes `plan.replicate.roi`, crops each
decoded frame before any root node sees it, and `cache_key.py` folds that ROI
into the source key — and the GUI has never chosen which one. `filter_tab.py`
reads `replicates[0]` in three places. Every tool in the second item shapes a
box that, until the first item lands, nothing downstream will ever look at.

Two things that section describes are deliberately not here. The replicate
table's "progress bar for the crop, and the list of outputs defined by the DAG,
and whether they exist" is a claim about files nothing writes, and it went to
`LATER.md` under **Replicate status: crop progress and output existence** with
the trigger that would make it takeable. And the **project interface** section
above it — a folder of videos, one video per folder, symlinks rather than moves
— is a tab that does not exist yet rather than a change to this one.

## The selected replicate is the one being tuned

**Gated on: nothing, and everything about this tab is worth less until it
lands.** The vision's sentence is "Left click on a replicate is the same as
accepting it, and begins the crop, and moves the user over to the filters tab."

**What "begins the crop" turns out to mean, which is the first thing to get
straight.** Not a background job with a progress bar. The crop is applied per
frame at the graph's root, in memory, by the executor — that is settled and
argued in `docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`, and a
*materialized* crop is a `Project.checkpoints` entry that is contractually
never hashed and that nothing currently writes. So accepting a replicate is a
submit, not a job: it sets the replicate on the preview path and re-renders.
Anyone who builds a progress bar here first has built a bar for a job that does
not exist.

**What it involves.** `ReplicateTab` already knows its selected row and already
emits nothing about it. The three `replicates[0] if replicates else None` sites
in `filter_tab.py` become one selection the document or the window owns —
whichever, it is *one*, because two answers to "which arena am I looking at"
is the same failure the transport had before the timeline replaced it. The
render goes through `PreviewRunner.request_render` unchanged; the coalescing
and abandon rules are already written against a caller that submits faster than
renders finish, and a replicate change invalidates exactly as a window move
does.

**The tab switch needs plumbing that does not exist.** `main_window.py` builds
its `QTabWidget` as a *local variable* and keeps no reference, and nothing in
`src/` calls `setCurrentIndex` or `setCurrentWidget`. That is a two-line fix and
it is worth naming because it is the kind of thing that reads as already-there.

**The one judgement call.** A left click that both selects and navigates leaves
no way to select a replicate while staying on this tab — which is what the user
wants when they are drawing the next twelve. The vision says left click accepts;
the workable reading is that clicking a *row in the table* selects, and it is
the click on the **video** that accepts and navigates, which also mirrors the
filter tab's click-to-navigate gesture from the same document.

**Tests worth writing:** selecting row N renders N's pixels rather than row 0's
(the current bug, and it would pass today by accident on any single-replicate
project — so the test needs two replicates with different ROIs); and a
replicate change submits through the runner's one pending slot rather than
racing a window render, which is the discipline the step composite item
established.

Read: `src/sieve/gui/{replicate_tab,filter_tab,main_window,preview_runner}.py`,
`src/sieve/pipeline/{executor,preview}.py`,
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`,
`docs/REFINED-VISION.md` **Replicates**.

## Crop tools: the stamp, the drag, and the magnifier

**Gated on: nothing structurally.** This absorbs the "Drag existing boxes" item
that sat under *Independent of the stack* until 2026.07.26 — it was the same
work described one gesture at a time, and the vision names the rest of the
gestures it belongs with.

**What exists.** `video_view.py` draws a new box by click-drag, selects the
topmost box under a click, and paints the set. It has no zoom, no pan, no
handles, and no move: a drag that starts on top of an existing box draws a
second box over it. The right half of `ReplicateTab` is a deliberately empty
`tools_panel` waiting for exactly this.

**The four gestures the vision asks for.**

- **Draw versus stamp, as a toggle.** The stamp is the labour saver and the
  reason this is not just "drag boxes": a rack is a dozen arenas of identical
  size, so the size is drawn *once* — or typed — and then placed. Stamp
  placement must preserve width and height exactly; a stamp that rounds through
  widget coordinates and back produces twelve arenas that are almost the same,
  which is worse than one that is obviously different because
  `equivalence_groups` will happily report them as one group while the pixels
  disagree.
- **Move an existing box, with `QUndoCommand.mergeWith`** so one drag collapses
  to one undo step rather than one per mouse-move. `commands.py`'s
  `SetReplicateROI` is where that goes.
- **Resize by corner and edge handles**, which is hit-testing before
  `_replicate_at`'s containment test rather than after it — a handle inside
  another box's bounds must still win, or the top-left corner of a box drawn
  second is unreachable.
- **The magnifier, whose floor is the interesting part.** "Scrolling in or out
  magnifies the video so they can position it carefully, but doesn't zoom out
  more than the natural resizing to fit the box" — so the scale floor is
  `content_rect`'s fit scale, not 1.0 and not unbounded. Every coordinate
  mapping in the file (`to_source`, `to_widget`, the paint path) currently
  assumes fit-scale; a scale factor and a pan origin have to go through all of
  them at once, and the round-trip property test in
  `tests/gui/test_video_view.py` is the thing that says whether they did.

**Numeric entry while unlocked** is already half-built: the table's X/Y/W/H
columns write through `ReplicateDocument.set_roi` and clamp. What the vision
adds is the same fields *beside the video* while a box is being placed, which
should be the same document call and not a second edit path.

**Tests worth writing:** the zoom floor is never below fit (a wheel-out storm
leaves the frame exactly fitted, which is the invariant a naive
`scale *= 0.9` breaks); source↔widget round-trips hold under a non-fit scale
with a pan offset, extending the existing round-trip test rather than adding a
parallel one; and one drag pushes one undo command.

Read: `src/sieve/gui/{video_view,replicate_tab,commands,document}.py`,
`tests/gui/test_video_view.py`, `docs/REFINED-VISION.md` **Replicates**.

---

# Independent of the stack

These gate nothing below them and can be taken at any point. The three small
GUI fixes that sat here are done — see
`docs/completed-todo/2026.07.26-three-small-gui-fixes.md`, which also records
why the preferences one could not be tested the obvious way. "Drag existing
boxes" was moved rather than finished: it is one gesture of the crop-tools item
above, and describing it separately was describing the same work twice.

---

## Deferred decisions

- **napari and `pyqtgraph` are out of the `gui` extra, and stay out** (parity
  plan item 5, 2026.07.26; closed 2026.07.26): the filter-tab plot family
  landed as QPainter widgets over `gui/band_plot.py`, which settled the plot
  layer, and both dependencies had sat installed and unused through three
  items. The one item that still owned a napari question — the three-way
  overlay — answered it when it became **the step composite** above: two
  layers and one opacity slider is QPainter, and no vision demands N
  independent layers. Re-adding napari now requires a new demand, not a
  revisit of this one.
- **`gui/state.py`** from SCAFFOLD was not created. Scrub position and playing
  state live in `VideoPlayer`; a separate object would duplicate them. Create
  it when there is UI state with no natural owner (panel layout, zoom).
- **`ARCHITECTURE-TREE.md`** does not exist, and no longer obviously should.
  `docs/findings/` now holds the measurement-driven decisions one file at a
  time, and `docs/completed-todo/` holds what was built. Revisit only if
  something needs saying that neither of those can carry.
- **`hypothesis` is now used by four property modules under `tests/property/`.**
  Rule 7 above narrows what earns one going forward; the existing four stay.
