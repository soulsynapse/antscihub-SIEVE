---
status: record
---

# REFINED VISION

> **Dated record of intent (2026.07.26).** Not maintained; its build order is
> nearly fully landed, which is a plan that worked, not staleness. Reality is
> recorded in `completed-todo/` and `findings/` — supersede this with a new
> dated document rather than editing it.

This is the vision after the wizard/setting workflow was decided on. 2026.07.26

The purpose of this is to put down in words what the workflow should be like, and what the lead-ins and lead-outs to the filter tab are.

## The project interface.

The project interface, a wizard, defines any folder with any number of video files in it as the target for SIEVE.

Any folder that already has the sieve sidecar files to define them as a project are not assumed to be sieve projects.

Any folder that The user attempts to add is evaluated for what would be needed to deploy a one video one folder rule. This is how the source video is defined for all downstream functions, but in the project interface, each individual folder that has one video in it has its own pipeline.

The project interface exists to 

1. Import video files and process folders of video so that they are ready for the sieve pipeline folder organization 
2. Quickly view the progress of a given folder so that folders marked as configured are clear to the user 
3. Browse between different projects and navigate files 

The project defining step is part of the pipeline as well; SIEVE on the CLI can accept a folder or file for ingest with the pipeline file as an argument and apply the pipeline to the video(s).

The ideal case is that the project doesn't move video files into new folders and instead accepts symbolic links to them. This maintains SIEVE as non destructive for source material.

---

## Replicates

The replicates tab has the video, the tab bottom seeker, and a replicates table spanning the bottom half.

The top half has the video on the left and settings and information on the right. 

The settings and information should be able to point to the parent as well as other information useful at the replicate stage. 

The right panel is also where the cropping tools live. The basic behavior should be a toggle between drawn and a stamp. The stamp needs to be drawn first or can be entered by dimensions.

When the user first sets a replicate, it can be dragged around by the cursor. Scrolling in or out magnifies the video so they can position it carefully, but doesn't zoom out more than the natural resizing to fit the box. While it isn't locked in, the dimensions have enterable numbers.

When the replicate box is set (either individually or via a "set all" or clicking into a replicate, it begins processing it. Left click on a replicate is the same as accepting it, and begins the crop, and moves the user over to the filters tab.

Right click on the video in the filters tab goes back up to the source. Left click on the video in the filters tab advances forward in outputs.

Back on the replicate tab, the full width replicate table is the replicate status. It should have the progress bar for the crop, at the very least, and the list of outputs defined by the DAG, and whether they exist.

---

## Filter tab

At the top of the window, there is a breadcrumbs trail for how deep onto outputs the user is. Outputs are when the user has decided they want some kind of output, and it materializes in that replicates folder as a new folder. Going into that folder, SIEVE only works with what is in that folder and doesn't know what is above it. If there is a video of a binary mask from a detection filter, then that is all that it has to work with. Any prior resource can be passed down with symbolic links. What is passed forward is defined by what the user configures as the outputs, which is always the last item of the DAG in the filter view.

The output list is defined by what the different steps of the dag announce they can produce.

The step that is always just before the output list is the thresholded and windowed detection. inf to inf threshold always lets everything through.

Now, reasoning through temporal filters:

Temporal channel filters have at least a few kinds, traditionally: temporal filters that remove information (noise reduction techniques, frame decimation), additive (MIE and such), or both/neither (transformative, or thresholded frequencies, that kind of thing). Thinking about it this way isn't very helpful, so here is the universal case:

Seemingly all of the concrete use cases for this are either *signal-amplification-of-kind* or *economic*. Economic means that you decimate frames or do some other compute or storage saving measure because of constraints.

> **[Annotated 2026.07.26 — the economic branch has a correctness trap in it.]**
> Frame decimation is filed here as a pure cost move, and it is not one: decimating
> without a temporal anti-alias lowpass *folds* high-frequency behaviour into the
> band being measured. Grooming at 8 Hz sampled at 12 fps aliases to 4 Hz and
> arrives looking like something slower. The spatial `downsample` filter is
> anti-aliased already, and `wavelet.default_freqs` caps the bank at 0.45·fps —
> but that cap protects the *analysis* from asking for a frequency that isn't
> there, not the *decimation* from putting a false one in. An economic move that
> silently changes which behaviours are visible is not economic, it is a
> measurement error with a speedup attached. See **E** below.

Temporal signal-amplification-of-kind is a different beast. What this asks is: is there a pattern in time, across any channels, that creates at least part of a composite that isolates the behavior?

> **[Annotated 2026.07.26 — "across any channels" is the load-bearing phrase, and
> it is the one the executor currently refuses.]**
> Every kind-amplifier worth building is a *combination* of channels — that is
> what makes it a discriminant rather than a filter. "High change energy AND low
> flow coherence" is two channels meeting at one node, and
> `pipeline/executor.py` raises `UnrunnableNodeError` on any node with more than
> one upstream. So the single sentence that defines the section is sitting
> directly on top of the one structural limit in the execution layer, not off to
> the side of it. This is why **multi-upstream kernels** became a `TODO.md` item
> rather than staying deferred in `LATER.md`.

This is the true power of SIEVE. Some examples:

An ant is grooming itself. It raises its leg up to put it's antennae through the cleaning groove.

We first crop to the replicate. Then we set a low grade blur to remove the general noise. Then we set energy Jtt - where change is happening has hotspots. We threshold to known points where they groom, and create a continuous mask output to isolate all of the candidate points.

> **[Annotated 2026.07.26 — this threshold is in the wrong place.]**
> Thresholding here, *before* the temporal amplification below, discards the
> magnitude that the amplifier needs. Once the input is a binary mask the
> accumulator can only count occupancy: a block that barely crossed weighs
> exactly as much as one ten times over. The entire reason to integrate over time
> is that weak-but-consistent evidence should accumulate into a confident
> detection while strong-but-isolated evidence should not, and that requires
> graded input. Run the accumulator on the continuous signal and threshold its
> *output*. This also makes the leaky integrator a genuine matched filter for an
> exponentially-weighted temporal template, which on binary input it is not.
>
> There is a second problem with `Jtt` as the input, which is not about ordering:
> its units are (intensity)²/frame, so a threshold tuned on one replicate under
> one backlight is a number about that lighting rig. See **A** below.

We then apply temporal signal amplification of kind: Using something like temporal summing across same pixels, by a specific block size, we apply an exponential decay function and a blooming "touch" function of some kind: the active detections touch the ones around them to keep them from the exponential decay. This filters out the walking behavior, leaving only the behaviors where they are sitting in one spot but still moving.

> **[Annotated 2026.07.26 — three things about this paragraph.]**
>
> **First, the last sentence names the real discriminant and it is not
> persistence.** "Sitting in one spot but still moving" versus walking is the
> question of whether the change *advects*. A walking ant's active region
> translates; a grooming ant's support is stationary while its content
> oscillates. That is the Eulerian/Lagrangian split, and the operator that
> measures it is the material derivative — which means the 3D structure tensor
> answers it directly, without any accumulator at all. `block_signal` already
> computes five of that tensor's six components on the `flow_speed` path and the
> sixth on the `change_energy` path. See **B** below; it is the cheapest item in
> this whole section and it may make the decay-plus-touch machinery unnecessary
> *for this particular example*.
>
> **Second, decay and touch have to be one node.** It is tempting to split them
> so the chain stack shows which is doing the work, but blurring the *output* of
> a leaky integrator is a different operator: in the recursion the coupling
> compounds through the feedback path, and the two forms diverge in exactly the
> regime this paragraph cares about. One filter, two parameters.
>
> **Third, "keep them from the exponential decay" is a wavefront and it needs a
> stability bound.** Written as `a[t] = max(λ·a[t-1], κ·dilate(a[t-1])) + s[t]`,
> a `κ ≥ 1` propagates one detection outward at one block per frame forever and
> eventually fills the arena — a beautiful demo and a completely wrong result.
> `κ < 1` makes activity decay by κ per block of distance, so the reach is
> `R = log(threshold/peak)/log(κ)`. **Expose R in blocks, not κ**, for the same
> reason `background_ema` exposes `alpha` with its settling time worked out in
> the docstring: a number a scientist can put in a methods section.

Then, by filtering out events that do not meet a specific size threshold or duration threshold, we are left with mostly grooming behaviors.

> **[Annotated 2026.07.26 — this is one operator, not two, and it has a
> calibration problem.]**
> Size and duration thresholds on a gated binary field are a *connected-component
> attribute filter* on the (x, y, t) volume — an attribute opening. Treating them
> as two independent tests loses the guarantee that makes the combined form worth
> having: an attribute opening is anti-extensive, so it can only remove events,
> never create one. When the output is a scientific claim that is a property
> worth having by construction rather than by inspection. The existing
> `windowed_mean` + `detect_gate` tail covers duration for a *global* count
> series; this covers it per event, which is what the sentence actually
> describes. See **C**.
>
> The calibration problem is separate and bigger: thresholding thousands of
> blocks across thousands of frames is millions of tests, so at any fixed
> threshold there is a guaranteed harvest of false positives whose count grows
> with clip length and grid resolution — meaning a longer video *looks* like more
> behaviour. See **D**.

This is at least how I envision it working. But much testing would be needed to nail down what actually works.

> **[Annotated 2026.07.26 — this closing line is the most important sentence in
> the section, and it should be read as a specification.]**
> "Much testing would be needed" is correct and it has two distinct meanings that
> are worth separating. One is *exploration*: trying decay against coherence
> against band power to see which separates grooming from walking, which is what
> the step composite view exists to support. The other is *validation*: knowing
> whether a parameter change made detection better or worse, which nothing in
> SIEVE can currently answer — the tuning loop gives rich feedback on **cost**
> (the HUD, the budgets, the benchmark summary) and none at all on **accuracy**.
> See **F**.

---

# What "signal amplification of kind" is, and what has to be built for it

Added 2026.07.26. Everything above this line is the vision as written plus
annotations; everything below is the analysis the annotations point at. The
sections are lettered so the annotations can reference them, and each says which
`TODO.md` or `LATER.md` item it became.

## The naming problem, first

"Signal amplification of kind" is not one operator and should not become one
filter. It is a request for a **class-conditional contrast enhancer**: a
transform that raises the response ratio between a target class (grooming) and a
distractor class (walking). In detection theory that ratio has a name — the
deflection coefficient — and the important consequence is that **the optimal
transform depends entirely on what you already know about the two classes.**
There are three mature families, they answer three different states of
knowledge, and conflating them is what makes the concept feel slippery:

**You know the temporal signature.** Then the Neyman–Pearson-optimal operator is
a **matched filter** — correlate against the known template. With unknown phase
but a known band it degrades to **energy detection in a band**, which is exactly
what `core/wavelet.py`'s `morlet_band_power` already does. Grooming at 4 Hz
against walking at 1 Hz is this case, and SIEVE already owns the operator. (Van
Trees, *Detection, Estimation, and Modulation Theory*, is the foundational text
and the one worth having on the shelf when a threshold needs defending.)

**You know the spatiotemporal geometry.** Then it is the structure tensor's
eigenstructure. SIEVE nearly owns this too — see **B**.

**You know only that it persists in place.** Then it is decay-plus-touch, and
four fields have independently converged on the same equation — see **C**.

The practical upshot: SIEVE is not building *a* kind-amplifier, it is building a
**detector bank** whose outputs get combined. That is why multi-upstream is the
gating item rather than a nicety, and it is also why the individual filters below
are small.

## A. Units, and the reason a threshold does not survive a second replicate

**This is the highest-value item in this document and it is not in the vision at
all.** `change_energy` is in (intensity units)²/frame. Its magnitude depends on
illumination, camera gain, exposure, the contrast of the animal against the
substrate, and how much of the block the animal occupies. A threshold tuned on
one replicate under one backlight is a number *about that lighting rig*. This
collides head-on with the two things SIEVE promises hardest: replicates that
share a pipeline, and a project artifact that reproduces.

`normalize` does not solve this and is not meant to. It removes the *global*
illumination component per frame — a cloud passing over, an auto-exposing camera
— by pinning each frame's grayscale mean and spread. What it cannot give you is
a **per-block baseline over time**, and that is the denominator a transferable
threshold needs.

The fix is standardization against each block's own null distribution: estimate
the quiet-period statistics per block over the working window and express the
signal in units of deviation from them. Robust statistics rather than mean and
standard deviation, because the events themselves are in the sample and would
inflate the very spread they are being measured against — median and MAD, which
is the standard used in spike sorting for exactly this reason (thresholding a
filtered trace at k·MAD, per Quiroga's widely-replicated procedure). fMRI
solved the same problem the same way and reports percent signal change and
z-statistics rather than raw scanner units; astronomy detects sources at Nσ over
a locally-estimated sky background rather than at an absolute flux.

What it buys, concretely: a threshold expressed as "4 MADs above this block's own
baseline" **transfers across replicates, across lighting, and across
experiments** in a way that "0.03 energy units" never will. It also makes the
per-replicate override machinery (`Replicate.overrides`, `resolved_params`) mean
what it is supposed to mean — a deviation because *this arena is different*,
rather than a deviation to paper over a gain change.

The subtlety worth writing down before implementation: the baseline must be
estimated over a window long enough to contain quiet periods but short enough to
track slow drift, and if the window is too short a *sustained* behaviour becomes
its own baseline and vanishes. That tension has no universally correct answer,
which makes the window a primary parameter rather than a constant, and makes the
step composite view the thing that shows a user they have set it wrong.

*Correction (2026.07.26, when the item landed):* two things above were not what
shipped. The centred window is not available — it needs future frames, which is
`Mode.WINDOWED`, which the executor refuses — so the estimate is trailing and
lags a step change by about one window. And the two-port composition this
section's item was gated on multi-upstream for is not what a baseline wants:
standardizing needs the median *and* the MAD, `emits` is still one stream per
node, so the composition would be two nodes each holding the same ring and
computing the same median. It shipped as one node with an `emit` switch. See
`docs/completed-todo/2026.07.26-per-block-temporal-baseline.md`.

→ `TODO.md`, **Per-block temporal baseline** — landed 2026.07.26.

## B. The 3D structure tensor, which is already five-sixths computed

The grooming/walking separation is a question about whether change advects. The
brightness constancy equation `∂I/∂t + v·∇I = 0` is the statement "all change
here is explained by translation", so the quantity wanted per block is the
*residual* of that equation after fitting the best local **v** — change that no
translation accounts for. Grooming has a large residual; walking, ideally, near
zero.

The operator that reads this off is the eigendecomposition of the 3D
spatiotemporal structure tensor `J = G_σ * (∇₃I ∇₃Iᵀ)` with `∇₃ = (∂x, ∂y, ∂t)`
(Bigün & Granlund's orientation tensor; the treatment in Jähne's *Handbook of
Computer Vision and Applications*, and Haussecker & Spies on tensor-based
motion). Its eigenvalue spectrum classifies the local pattern directly:

- one dominant eigenvalue, two small → a single oriented structure in (x, y, t)
  → **coherent translation**. Walking.
- two comparable, one small → distributed motion, aperture-ambiguous or
  oscillating → **change in place**. Grooming.
- all three comparable → isotropic change: noise, or an occlusion event.

**`filters/block_signal.py` already forms every component it needs.**
`_flow_speed` computes `xx, yy, xy, xt, yt` — five of the six unique components —
and its docstring explicitly notes the sixth is skipped: "(The sixth component,
tt, is not read by the solve and is not formed.)" The `change_energy` path forms
exactly that one. So the full tensor is one product away from existing, and the
eigendecomposition is a **3×3 symmetric solve per block** — not per pixel —
which on a typical grid is a few hundred tiny eigensolves against six Gaussian
blurs already being paid for. It is arithmetically free.

Emit a coherence scalar, e.g. `c = ((λ₁-λ₂)/(λ₁+λ₂))²`, which lands in [0, 1] and
reads as "how much of this block's change is coherent translation". Then grooming
is *high `change_energy` and low `coherence`* — a two-channel rule with no state,
no decay, no touch, and no new time constants to defend in a methods section.

**The one ordering constraint that must not be got backwards:** block-reduce the
*tensor* (six numbers per block) and then eigendecompose. Averaging eigenvalues
across a block destroys the very anisotropy being measured. This mirrors the
constraint `block_signal` already documents for the LK solve — "the solve
precedes reduction so the aperture problem is not coupled to the user's block
size" — and it is the same class of mistake, arriving from the other direction.

I would build this **before** the accumulator in **C**, because it is smaller,
has no state, and it tests whether the harder thing is needed at all.

*Correction (2026.07.26, when the item landed):* the scalar drafted above
reads the wrong eigenvalue pair. For a translating 2-D texture both λ₁ and λ₂
are spatial energy and `((λ₁-λ₂)/(λ₁+λ₂))²` scores it ~0.16, failing this
section's own test; the signature of coherent translation is the null
direction, λ₃ ≈ 0, and the shipped scalar is Haussecker & Spies' spatial
coherency `((λ₂-λ₃)/(λ₂+λ₃))²`. Derivation and measurements in
`docs/findings/2026.07.26-the-specs-coherence-formula-fails-its-own-test.md`.

→ `TODO.md`, **Coherence as a third block signal**.

## C. The accumulator: decay, touch, and the equation underneath them

Decay-plus-touch, written continuously on the block grid, is

    ∂a/∂t = −a/τ + D∇²a + s(x, t)

the linear inhomogeneous heat equation with decay and a source. Exponential decay
is the `−a/τ` term, the blooming touch is `D∇²a`, and `s` is the input field. So
the intuition that this involves partial derivatives is right, the object is a
PDE, and it is a well-studied one. The useful consequence is **parameterization
in physical units**: τ is a persistence time in seconds and D a spread rate in
blocks²/second, both reportable; λ and a kernel width are not.

The discrete recursion is a semi-implicit Euler step,

    a[t] = λ·(K ⊛ a[t−1]) + (1−λ)·s[t],   λ = exp(−Δt/τ)

Four fields have this equation, and each contributes something the others do not:

- **Computer vision** has it as the **Motion History Image** — Bobick & Davis,
  "The recognition of human movement using temporal templates" (PAMI 2001).
  `MHI(x,t) = τ` where motion is present, else `max(0, MHI(x,t−1) − 1)`. This is
  literally the operator with a linear rather than exponential decay law, it is
  foundational and heavily replicated, and its companion Motion Energy Image is
  the binarized support. **VISION step 3 category C already names MEI and MHI**,
  so this is a re-derivation of something the original vision listed — worth
  naming the filter after them so a user can find the literature.
- **Neuromorphic vision** has it as **time surfaces** / the surface of active
  events (Lagorce et al., HOTS, PAMI 2017; Sironi et al., HATS): an
  exponentially-decaying per-pixel map read over a spatial neighbourhood.
  Structurally identical, and developed for precisely the problem of assembling
  sparse per-pixel change into a persistent local descriptor.
- **Neuroscience** has it as the **neural field equation**,
  `τ ∂u/∂t = −u + ∫w(x−x′)f(u(x′))dx′ + I(x,t)` — decay plus touch plus input.
  Amari's 1977 lateral-inhibition analysis is the load-bearing result: with a
  Mexican-hat coupling kernel the equation admits stable localized **bump**
  solutions, activity that self-sustains at a fixed location while input supports
  it and collapses otherwise, and that *cannot form under advecting input* above
  a critical speed. That is the grooming/walking separation with a stability
  theory attached, which is more than the CV formulations offer. Wilson–Cowan
  (1972) is the foundational pair.
- **Pattern formation** has it as reaction–diffusion under local-activation /
  lateral-inhibition (Turing; Gierer–Meinhardt; Meinhardt's *Models of Biological
  Pattern Formation*).

**The linear diffusive form is probably not what is wanted.** Diffusion is
conservative: it spreads the peak *down* while spreading it out, which fights the
downstream threshold — a long grooming bout smears into sub-threshold mush. The
vision's phrasing, "the active detections touch the ones around them to keep them
from the exponential decay", describes a *gating*, not a smear, and gating is
morphological: `a[t] = max(λ·a[t−1], κ·dilate(a[t−1])) + s[t]`, grayscale
dilation by a small structuring element, which sustains the support without
lowering the peaks. Ship both as a `couple` mode (`diffuse` vs `dilate`) and
expect `dilate` to win — but ship both, because "much testing would be needed" is
correct and this is one of the things to test.

**Group delay, which nothing else in this document will catch.** A leaky
integrator is causal, so a detection lags its event by order τ. `windowed_mean`
already offers `centered` versus trailing. Mixing a causal accumulator with a
centered detection window means the two latencies do not cancel and reported
event onsets are biased late by an amount nobody wrote down — which matters the
moment anyone reports onset latencies or aligns SIEVE's output to another data
stream. Two acceptable answers: run the accumulator forward-and-backward for a
zero-phase result when offline (the `filtfilt` trick, legitimate here because a
tuning session is not real-time), or run causally and *declare* the group delay
so a consumer can correct it. What is not acceptable is having neither.

→ `TODO.md`, **The motion history filter**.

## D. False positives, and why a longer video looks like more behaviour

Thresholding a few hundred blocks across a few thousand frames is on the order of
a million tests. At any fixed per-block threshold the expected number of false
positives is proportional to blocks × frames, so **the same settings on a longer
clip or a finer grid produce more detections for no biological reason.** That is
a reproducibility bug that looks like a result, and it is exactly the failure mode
the coverage-lanes entry in `LATER.md` is already worried about from the other
direction.

The size-and-duration threshold at the end of the vision *is* the standard
remedy — it is cluster-extent inference, the same instrument fMRI settled on
(Worsley and Friston's random field theory; Benjamini–Hochberg FDR as the other
branch). What is missing is its **null distribution**: cluster-extent inference
is only meaningful against a calibrated answer to "how big does the largest
spurious cluster get?", and hand-tuning the size threshold until the output looks
right is precisely the circularity the method exists to avoid.

The null is cheap to generate here and that is what makes this worth doing:
**circularly shift each block's time series by an independent random offset**, or
phase-randomize it, which destroys real spatiotemporal events while preserving
each block's marginal signal distribution and the spatial correlation structure.
Run the same gate and the same attribute filter on the surrogate, take the
largest cluster, repeat a few hundred times, and read the size threshold off the
95th percentile. It reuses the entire existing detection chain — the surrogate is
just a different input array — so the implementation is a loop and a percentile,
not new mathematics.

This converts "much testing would be needed to nail down what actually works"
from a matter of taste into a calibrated procedure, and it is the single thing
most likely to make SIEVE's output defensible in review.

→ `LATER.md`, **Surrogate calibration for the detection threshold**.

## E. Temporal anti-aliasing on the economy path

No temporal decimator exists yet, which makes this the right moment to record the
constraint rather than discover it. Decimation must be preceded by a temporal
lowpass, or high-frequency behaviour folds into the measured band and arrives
disguised as something slower. The spatial `downsample` filter is already
anti-aliased; the temporal one must be, and the wavelet bank's 0.45·fps cap does
not cover it (that cap stops the *analysis* asking for a frequency that is not
there, not the *decimation* from manufacturing one).

The consequence for the filter contract is specific: a decimator is the
`rate_changing` shape, which is one of the two node shapes still deferred in
`LATER.md`, and its declaration should carry the anti-alias as part of the
filter rather than as a separate node a user can forget to put in front of it —
the same reasoning by which `downsample` does not offer an un-anti-aliased mode.

→ `LATER.md`, folded into the existing kernel-protocol entry's `rate_changing`
trigger.

## F. The tuning loop has no accuracy feedback

VISION step 4 and step 5 build an elaborate feedback loop about **cost**: the
benchmark summary, the graph HUD, the per-operation expense, the compaction
prompt when memory climbs. There is no corresponding signal about whether a
parameter change made detection *better*. A user drags a threshold and learns
exactly what it cost and nothing about what it caught.

This is the deepest gap between the vision as written and a tool that produces
defensible results, and it is genuinely not takeable yet, because it needs
labelled spans and there is no marks model — which is what the **Annotation spans
on the timeline** entry in `LATER.md` is about. Worth recording now is the shape
of the answer, because it is cheaper than it sounds: the detection chain's
threshold is a *slider*, and the score series behind it is already cached, so
sweeping the threshold over a labelled window and drawing the resulting
precision/recall or detection-error tradeoff curve is one pass over an array the
system already holds. The user is then tuning against a curve rather than against
an impression, and the parameter that maximizes F1 or minimizes total error is
readable off it rather than hunted for.

Two constraints to not get wrong when it lands, both inherited from existing
entries: labels belong to a **replicate**, not to the video (the failure V1 fixed
at cost, recorded in the annotation entry), and a curve computed over labelled
spans must never be presented as if it covered unlabelled ones — the same
unexamined-versus-quiet collapse the coverage lanes entry names as V1's standing
failure, arriving through a different widget.

→ `LATER.md`, **Accuracy feedback in the tuning loop**.

## G. What gates all of it: multi-upstream nodes

Every discriminant above is a combination. "High energy and low coherence" is two
channels at one node; "accumulate the continuous signal, then gate it against a
per-block baseline" is two; a matched filter's output compared against its own
null is two. `pipeline/executor.py` refuses any node with more than one upstream,
and `core/filter_base.py`'s `StreamSpec` docstring already prices the fix: named
ports on `Edge`, which is a change to the saved artifact and to every edge ever
written.

This was deferred in `LATER.md` under "A kernel protocol that is not one frame in,
one frame out", bundled with `Mode.WINDOWED` and `rate_changing`. The trigger
that entry asked for — "a filter that actually needs one" — has now fired, and
the multi-upstream shape has been **moved** to `TODO.md`. The other two shapes
stay deferred; they have separate triggers and there is no reason to believe they
arrive together.

→ `TODO.md`, **Multi-upstream kernels**.

## Build order, and the reasoning behind it

1. **Coherence** (**B**) — smallest, stateless, and it tests whether the
   accumulator is needed for the flagship example at all. Building the hard thing
   first and discovering the cheap thing sufficed is the expensive order.
2. **Multi-upstream kernels** (**G**) — nothing combinable runs until this does,
   and it is the only item here that touches the saved artifact, so it wants to
   land before there are many graphs to migrate.
3. **Per-block baseline** (**A**) — gives every threshold below it units that
   survive a change of replicate. Doing it after the accumulator means retuning
   everything the accumulator was tuned with.
4. **Motion history** (**C**) — the vision's own primitive, now with graded input
   (per the threshold-ordering annotation above), transferable units from 3, and
   somewhere for its output to be combined from 2.
5. Then **D** and **F**, which are about believing the output rather than
   producing it, and which are correctly `LATER.md` until there is an output
   worth believing.