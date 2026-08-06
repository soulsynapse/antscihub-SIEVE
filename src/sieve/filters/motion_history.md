# Motion history

A leaky accumulator of per-block activity, with the neighbours holding each
other up. Each block's value decays exponentially toward the incoming signal
with a persistence time you set, and — optionally — is propped up by the blocks
around it. This is Bobick & Davis's **Motion History Image** (PAMI 2001) with an
exponential rather than linear decay law, so the literature to read is theirs;
the same operator is a *time surface* in neuromorphic vision and a *neural
field* in computational neuroscience.

Put it after `block_signal`, and after `temporal_baseline` if you are using one.
Its input is a block grid, its output is the same grid in the same units, and
its output is what you threshold.

## When to use it

**Use it when the behaviour is intermittent but the event is not.** An animal
grooming produces motion in bursts with pauses between them, and a per-frame
signal thresholded per frame reads that as ten short events. A persistence of a
second bridges the pauses and reads it as one, which is what you wanted to
count.

**Use `reach_blocks` when the animal is bigger than a block.** A grooming ant
straddles two or three blocks, and which of them carries the signal flickers
between frames. Coupling lets the block that is currently quiet be held up by
the one next to it that is not, so the detection is about the animal rather than
about where the block grid happened to fall.

**Leave it out when you are measuring an instantaneous quantity.** A flow speed
in px/s that is going to be reported as px/s is not improved by being smeared
over a second, and the group delay below becomes an error in the number you
report.

## Parameters

### `tau_seconds`

The persistence time, and the primary parameter. Concretely: how long after the
animal stops moving the accumulator still says something happened — after `τ`
seconds of silence the value has fallen to `1/e` of where it was, and after
about `4.6 τ` it is under a percent.

The tension is the same shape as `temporal_baseline`'s window and resolves the
opposite way:

- **Too short** and a bout with pauses in it reads as several bouts. The
  detector fires, drops out, and fires again while the animal never stopped.
- **Too long** and two genuinely separate bouts merge, and the reported end of
  an event drifts later by roughly `τ`.

The rule of thumb: **somewhat longer than the longest pause inside a bout, and
shorter than the shortest gap between two bouts you want to count separately.**

### `reach_blocks`

How far activity is carried from the block where it happened. Zero is a pure
leaky integrator per block — the plain MHI — and is the right setting when a
block is already bigger than an animal.

The two coupling modes agree on the *scale* and not on the profile, which is the
whole reason both ship:

- `dilate` attenuates by `1/e` per `reach_blocks` blocks of separation. Combined
  with the decay, a block driven continuously holds a neighbour at `d` blocks at
  `(λ·κ)^d` of its own value, where `λ = exp(−1/(τ·fps))` and
  `κ = exp(−1/reach_blocks)`.
- `diffuse` spreads a spot of activity to a Gaussian standard deviation of
  `reach_blocks` blocks over one persistence time — the PDE's own coefficient,
  `D = reach² / (2τ)` in blocks² per second. That is a statement about a single
  impulse. Under a *sustained* source the steady profile is a cusp rather than a
  Gaussian, so the width you can see on screen is not this number.

### `couple` (`dilate` | `diffuse`)

**`dilate` is the one to reach for.** It is a grayscale morphological dilation:
a block takes the largest of its own value and its neighbours' attenuated ones.
It *gates* — it sustains a neighbour's support without lowering this block's
peak, so the peak of a sustained event is exactly what it would have been with
no coupling at all.

**`diffuse` is the literal PDE term, and it is conservative.** It spreads the
peak *down* as it spreads it out, which fights the threshold downstream. Under a
continuously driven block at `τ = 1 s` and 30 fps, `dilate` holds the peak at the
input's own value at every reach while `diffuse` drops it to 0.39, 0.16 and 0.066
of it at `reach_blocks` of 1, 2 and 4 — so **switching to `diffuse` means
re-tuning the threshold**, and by an amount that moves with a parameter that
looks like it is only about width. See
`docs/findings/2026.07.27-dilation-creates-activity-and-diffusion-conserves-it.md`.
It ships because "much testing would be needed" is the correct answer to which
operator suits real footage, not because it is expected to win.

### `fps`

The source frame rate, used only to convert `tau_seconds` and `reach_blocks`
into per-frame quantities. The filter tab writes it from the video metadata, for
`block_signal.fps`'s reason: a kernel is pure and cannot ask the graph what the
container's rate was.

## What it does not do

**It does not run at zero phase, and it tells you the lag.** A causal leaky
integrator lags its event. The lag is `λ/(1 − λ)` frames — the centroid of the
impulse response, and the one-pole IIR's group delay at DC, which are the same
number — and it is about `τ·fps − 0.5` frames, so roughly `τ` seconds.
`MotionHistoryParams.group_delay_frames()` and `.group_delay_seconds()` return
it.

This matters the moment you report an onset time or align SIEVE's output to
another data stream. It matters *particularly* against `windowed_mean`'s
`centered` mode, which has no delay of its own: mixing the two means the
latencies do not cancel and every onset is late by this amount. The zero-phase
repair — running the accumulator forward and backward, the `filtfilt` trick,
which is legitimate offline — needs the whole record in hand, which is a kernel
protocol this repo does not have yet. So the delay is declared instead of
removed, which is the honest half of that pair.

The declaration is exact only at `reach_blocks = 0`. With coupling, a block `d`
away first hears about the activity some frames later, so the number is a lower
bound away from where the event happened.

**It does not accumulate negative signal.** The source is half-wave rectified:
`max(input, 0)`. A `temporal_baseline` deviation below baseline is *less
activity than usual*, which contributes nothing to a history of activity —
passing the sign through would let `dilate` propagate the least-negative value
outward and let a lull cancel a bout that really happened.

**It does not saturate.** MHI's convention is to set the value to `τ` where
motion is present, which puts the output in units of time. Here the source is
weighted by `(1 − λ)`, so a constant input settles to exactly that input and the
output stays in the input's units — a threshold in `temporal_baseline`
deviations is still a threshold in deviations after this node.

**It does not leak activity at the arena wall.** `diffuse` uses a reflecting
boundary, so the outward gradient at the edge is zero. The alternative — a
zero-padded stencil — would drain every edge block, which is where an animal
walking the perimeter lives.

## Cost

Declared as **4 work units per input megapixel** for the ordinary coupled
update. That is uncalibrated work, not elapsed time.

`diffuse` is the one that can get expensive, and predictably: the explicit heat
scheme is stable only up to a diffusion number of `1/4`, so a frame is split
into `ceil(reach^2 / (2 * tau * fps * 0.25))` sub-steps. That is a cost rather
than a refusal on purpose: the constraint couples three parameters, two of
which you are not thinking about while dragging the third, so a validator
rejecting the combination would land as a slider that stops responding.

`dilate`'s radius grows the same way and almost never does: it is one block
unless the requested reach outruns one block per frame, which needs
`reach_blocks > tau * fps`.

## Warmup

`ceil(ln 0.01 / ln λ)` source frames — about `4.6·τ·fps` — which the planner
decodes ahead of the requested span. 139 frames at the defaults; the declared
bound of 11053 is what a 10 s persistence at 240 fps would need, and no run pays
it unless it asked for it.

The accumulator starts at zero, which is the correct initial condition (no prior
activity, unlike a background model where zero would mean a black arena). What
that costs is that its first outputs are biased *low*, and the warmup is how
long that lasts.
