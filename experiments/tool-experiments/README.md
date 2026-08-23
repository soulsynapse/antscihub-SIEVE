# tool-experiments

Where SIEVE finds out what happens to the frame stack when the player stops
being the only thing asking. `decode-experiments` settled what a frame costs
to get; `storage-experiments` settled what it costs to keep, and measured the
tuning loop end to end with one consumer and its own background fill. This
folder measures the layer both of those deferred: **many consumers, many
forms, one store** — and the second half of the same question, what a tool
leaves *behind*.

## Why this exists

The session explorer's store is keyed by frame index alone, and the form —
the crop rect, the scale, the pixel format — is a module-level global. That
is correct for one consumer: `_apply_crop` stops the fill, drops the windows,
replaces the RAM tier and wipes the chunks, because a stored small frame
cannot become a different one. It stops being correct the moment a tool wants
the full frame while the loop shows the crop, or wants half resolution, or
wants colour where the loop caches luma. Then "hit" no longer names anything,
and a miss that was unavoidable and a miss that was a bookkeeping failure are
indistinguishable.

The product claim this folder has to make true is narrow and testable:
*a frame is fetched when it is needed, and refetched only when there was no
way of knowing it would be needed.* Everything below is an attempt to turn
half of that sentence into a measured number and the other half into a rule.

## The architecture under test

Four things, each of which the storage stack currently does not do, or does
exactly once by hand:

1. **A request is `(pts, form)`, and serving is a domination test.** Form is
   a declared, comparable descriptor — source-pixel rect, scale, pixel
   format — and the store answers a request from anything on hand that
   *derives* to it without decoding. A crop slices out of a full frame at the
   same scale; a downscale derives from a larger one; luma derives from
   colour; none of those reverse. Coverage is already explicit per span
   (chunk files on disk, not inferred from a gap); it becomes explicit per
   `(form, span)`. Whether the derivation is cheap enough to be worth
   preferring over a re-decode is the form-key experiment's to settle, not
   an assumption.

2. **Byproducts are admitted, not recomputed.** The session explorer does
   this once, on the kf route: a full frame decoded for hunting has its crop
   sliced out and admitted to RAM, because bytes that already exist are never
   refused. Generalising it needs a place to put what falls out and a rule
   for what is worth computing while a frame is hot. The analysis-cost shelf
   already suggests the shape of the rule — absdiff, background subtraction
   and reductions are in the noise class beside decode, dense flow is a
   thousand times it, and motion vectors and packet sizes need no decode at
   all — so the free-while-hot experiment is measuring where that boundary
   actually falls under load, not discovering it.

3. **A reduced series is a stored thing; a field never is.** A tool
   produces two outputs per frame with completely different economics — a
   field, image-sized, which is what the overlay draws, and a reduction, a
   scalar, which is what the graphs read. Storing fields means another
   video's worth of bytes per tool per parameter setting, so tier 4 of the
   storage plan holds series and the field is recomputed every time it is
   drawn. That is what makes the two halves of this folder one thing, and
   it runs the opposite way round from the obvious guess: the overlay is
   not a *reader* of the sweep's cache, it is a second *writer* to it. The
   field was computed to be drawn, the frame was hot, and the number that
   falls out is the same number a sweep would have written — so a tool's
   series fills by being looked at, and the sweep exists to cover the
   ground nobody looked at. Tier 4 is the one tier never built and never
   felt: the session explorer computes DIS over the covered run on every
   debounce and throws it away, which was honest as an instrument and
   leaves the time-columnar half of the plan with nothing behind it.

4. **A consumer the user launched can be made to yield.** The one priority
   inversion that exists — flow preempts fill — is hard-wired between two
   named parties, both of which the app started for itself. A full run is
   different in kind: the user asked for it, so it is allowed to make the
   loop worse, and what it is not allowed to do is keep making it worse
   after they have gone back to tuning.

A fifth thing, stated here because it is a design fact rather than a
measurement: **fusion belongs above the invalidation line, never below it.**
Combining steps into one pass over hot memory is what makes a sequential run
fast, and it is the right treatment for form construction — crop, scale,
convert — which does not change when a knob turns. It is the wrong treatment
for anything the knobs touch, for two reasons that both bite before
performance does. A fused graph is specialised to its parameters, so every
slider move re-pays building it. And fusion consumes intermediates, while
the loop exists to *show* intermediates: fuse a difference into a threshold
into a count and the overlay has nothing left to draw. A batch run draws
nothing and may fuse freely, which is the whole of the difference.

What that leaves is the hazard worth guarding: a fused path and an unfused
path that answer differently for the same frame, so the preview lies about
the commit. It is `docs/decode/ideas.md`'s do-not-assume-bit-identical in
another costume, and the guard is cheap — run both over a span and diff the
series.

Frame identity is pts everywhere durable (ADR-0004). This folder is where
that starts costing something, because a form descriptor, a coverage record
and an analysis-cache key are all things that cross a boundary, and the
explorer is index-keyed end to end. An experiment here that keys durable
state by index is measuring a stack SIEVE will not build.

## The substrate

Four modules, written before the experiments because both halves need them
and neither can be measured without them. Each carries its reasoning in its
own docstring, which is where a wrong one gets argued with.

- `forms.py` — what a stored frame *is*, and when one on hand can answer for
  another. Holds the canonical construction (crop, resize, convert, in that
  order, always) and the admission law that falls out of it: **derived is
  for looking at, decoded is for recording.** An exact derivation
  reproduces a build-from-source byte for byte and may be kept; an
  approximate one may be shown and never stored, written to a series, or
  read by anything that commits.
- `tools.py` — what a tool declares before anything schedules or draws it:
  its form requirement, its temporal extent, its cost class, its field and
  its reduction. Extent distinguishes a map from a fold, which is the
  difference between a sweep that can be split and resumed and one that can
  only be replayed. The cost class is a *claim* — `free`, `budgeted`,
  `commit`, cut where product behaviour changes — and the free-while-hot
  experiment exists to falsify the ones that are wrong.
- `series.py` — tier 4: one float per frame per tool, coverage recorded
  rather than inferred, a pts table saying what a row means, and the
  extent's warm-up rows refused rather than written and masked.
- `surfaces.py` — drawing a tool's output at display resolution from data
  reduced to it, and nothing Qt. Holds the two presentation rules this
  folder enforces: reduce to display resolution once per data change, and
  keep the live surface and the report surface as different code.

The two tools it starts with are `absdiff` and `dis_flow`, as a pair, because
they straddle the boundary the whole design keys on: one is in the noise
beside the decode that produced the frame and one is roughly forty times it,
so every fork that reads the cost class fires at least once.

## The rule for a result

The same as the other two folders, and for the same reason: import
`../decode-experiments/harness.py`, repoint `harness.RESULTS` at this
folder's `results/`, keep every per-iteration sample, discard a stated
warm-up. Provenance — build, machine, probed footage — is attached rather
than remembered. A case that could not run says so in the notes; a silently
absent case reads as a case that came out equal.

One rule this folder adds, because it is the failure it exists to catch:
**a number claimed about the loop is taken in the loop, and a number taken
in isolation says so in its notes.** A microbenchmark is allowed and often
the right instrument — `01-paint-cost.py` is one — but it may not be quoted
as a felt cost, because the gap between the two is where every freeze in
this tree has lived. v2 measured a pipeline made 1.88x faster making
playback worse, and that finding is still open.

## What to measure, roughly in order

Ranked by how much each would change what gets built. The ordering rule that
does the work: **measure hard where the requirement is hard.** The tuning
loop is where it is hard — it is the product constraint, and the user has
asked for nothing that would excuse it being slow. A run the user explicitly
started is where it is soft: they know the machine is busy, and the
requirement there is *degraded but usable*, plus yielding when they come
back. An experiment that measures a batch job to interactive tolerances is
optimising against a budget nobody is holding it to.

1. **What the visual costs.** Priced first because it gates the rest rather
   than merely mattering: a paint cost that is not separately instrumented
   reads as a slow store, which is the day the freeze hunt cost, and a live
   surface expensive enough to occupy a core is a consumer in its own right.
   Overlay draw order, live graph against decimation, at the sizes the
   explorer's own geometry says it draws. `01-paint-cost.py`; the standing
   rules it produced live in `surfaces.py`.

2. **The loop with a tool on it.** One consumer, no sweep: the overlay live
   at the frame the user is on, the series filling as a side effect of
   watching, the graphs drawn off the reduced series, and the whole thing
   instrumented so paint, field and serve are three clocks rather than one.
   The questions are whether the loop still feels like the loop, whether
   each cost class fits the frame budget where it claims to, and how much of
   a timeline gets covered by watching alone. Felt, forked from the session
   explorer with its log schema intact so the existing baseline subtracts.

3. **Does form belong in the key or in a wipe?** A loop question before it
   is a batch one: if a tool's analysis form is not what the loop already
   holds, every displayed frame pays a second decode inside the frame
   budget, and that is what decides whether an overlay is affordable at all.
   Price the derivations against their re-decode — slice-a-crop-from-a-
   cached-full-frame, downscale-from-larger, luma-from-colour — at the
   regimes on the decode shelf. If deriving is in the noise class the store
   keys by form and keeps both; if it is not, a form change stays the wipe
   it is today and the tool tier gets its own store.

4. **What is free while a frame is hot.** Per op class, the marginal cost of
   riding along on a decode that was happening anyway, which is what turns
   the cost-class declarations from claims into checked ones. Includes the
   two that need no decode at all: motion vectors off the packet stream and
   per-frame packet size.

5. **The reduced-series tier.** What a per-frame series costs to write, to
   read back time-columnar, and to invalidate: layout (row-major against
   chunked/time-major), the cost of a partial span, and what a parameter
   change above the flow line re-pays against one below it. Gated on
   `05-flow-wall` in storage-experiments, which priced the re-pay; this
   prices the storing.

6. **Yielding, when the user comes back.** The demoted form of contention.
   The question is not whether a run the user started slows the loop — it
   will, and they asked for it — but whether touching the loop preempts it
   promptly, what it costs to pause a sweep mid-span, and whether a resumed
   sweep re-pays ground it had already covered. `flow preempts fill` is this
   inversion between two named parties; this is it with a party the user
   launched.

7. **A batch protocol.** A request carrying a set of indices, sorted by
   keyframe and decoded together, against the same frames requested one at a
   time — decord's technique, and the thing a sweep wants that the player's
   one-at-a-time protocol cannot express. This is throughput, so it is
   measured to throughput tolerances; most of what a full run costs is
   already on the decode shelf, and the part that is not is this.

## What this folder does not do

Re-measure decode routes or the tier stack. Both are on the shelf with
findings behind them, and an experiment here that concludes something about a
decoder configuration is one that ran the wrong experiment. The subject is
the memoisation and scheduling layer — the part with something left to buy.

## Footage

`video-tests/` at the repo root, gitignored. Probe it, never trust a figure
written down here. Derived files the other folders make — the display proxy,
its segment build, the intra cut, the per-session chunk dirs — are inputs
here rather than outputs, and an experiment that needs one either finds it or
makes it and says which in the notes.

## Running

    uv run --group experiments python experiments/tool-experiments/<name>.py

The felt version lives beside the harness experiments, as in the other two
folders: an explorer whose logs land in `explorer-logs/`, keyed by tool name.
Drive it by hand; the felt report and the harness number are two different
artifacts and the finding is usually where they disagree.
