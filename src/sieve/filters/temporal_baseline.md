# Temporal baseline

Estimates each cell's own quiet-period statistics over a trailing window and
re-expresses the signal as deviation from them: `(x − median) / (1.4826 × MAD)`.
Put it after `block_signal` and before anything that compares a number to a
threshold.

## When to use it

**Use it whenever a threshold has to survive a second replicate.** A
`change_energy` value is in squared intensity units per frame, so it moves with
illumination, camera gain, exposure, and how dark the animal is against the
substrate. Tune `0.03` on the arena under the good backlight and it is a number
about that backlight — the arena at the end of the rack has different pixels and
the same behaviour reads differently. A threshold of "4 deviations above this
block's own baseline" is a claim about the block, and it transfers.

This is also what makes per-replicate parameter overrides mean what they are
supposed to mean. An override should say *this arena is different*; without a
baseline it ends up saying *this arena is lit differently*, and the two are
indistinguishable in the artifact.

**Leave it out when the quantity is already dimensionless.** `coherence` is in
[0, 1] by construction and a threshold on it already transfers; standardizing it
would replace a meaningful scale with a relative one.

**Leave it out when you want absolute magnitudes** — a flow speed in px/s that
is going to be reported as px/s, or any output whose units are the result.

## Parameters

### `window_seconds`

The trailing span the baseline is estimated over, and the parameter with no
correct value. It is a straight tension:

- **Too short** and a sustained behaviour becomes its own baseline. An animal
  that grooms for longer than the window has, by the end of it, a median that
  includes the grooming — and the deviation falls back to zero while the
  behaviour is still happening. The detector goes quiet in the middle of the
  event it was built for.
- **Too long** and the baseline stops tracking drift. A light that warms over
  ten minutes, a camera that re-exposes, a substrate that gets dusty: all of
  these move the null, and a window that spans them measures against an average
  of two conditions rather than the current one.

The rule of thumb that follows: **several times the longest single bout you
want to detect, and shorter than the slowest change in the recording
conditions.** If those two constraints cross, no window is right and the fix is
upstream — `normalize` for global illumination, or a shorter clip.

**Set `emit` to `baseline` to check it.** This is the whole reason the mode
exists. A window set too short shows the animal *in* the baseline, moving with
it; a window set right shows a quiet field that does not react to behaviour.
The deviation output cannot show you this, because its failure mode is to show
nothing, which looks exactly like nothing happening.

### `fps`

The source frame rate, used only to convert `window_seconds` into frames. The
filter tab writes it from the video metadata. It is a parameter for the same
reason `block_signal.fps` is: a kernel is pure and cannot ask the graph what
the container's rate was.

### `emit` (`deviation` | `baseline`)

`deviation` is the standardized signal and the thing to threshold. `baseline`
is the per-cell median in the input's own units — a diagnostic, not a signal.

## What it does not do

**It does not centre the window on the frame being measured.** A centred window
would need frames from the future, which is `Mode.WINDOWED`, which the executor
refuses. The consequence is worth knowing: the baseline lags, so a step change
in conditions reads as an event for about one window's length before the
baseline absorbs it.

**It does not use the mean and standard deviation**, and the difference is the
point rather than a detail. The events are in the sample. A block that grooms
for a fifth of the window inflates the standard deviation by roughly the size of
the events themselves, so each event is measured against a spread it created —
a detector that gets less sensitive exactly where there is more to detect. The
median and MAD are unmoved by a minority of large values, which is why spike
sorting thresholds at k·MAD rather than k·σ.

**It does not estimate a per-cell spread when there is none to estimate.** A
cell whose samples are more than half identical has a MAD of exactly zero, and
that cell borrows the frame's median nonzero spread instead. It is the one place
a cell's output depends on its neighbours. Where the whole frame is static there
is nothing to borrow and the output is zero, which is correct: no variation
anywhere is no evidence anywhere.

**It does not hold the whole window.** At most 256 samples are kept, taken at a
fixed stride across the span. The span is what tracks drift; the sample count
only stabilizes the estimate, and a median's standard error falls as `1/√n`, so
the 256th sample is already buying about a percent.

## Cost

Two per-cell medians, recomputed when a sample is admitted rather than every
frame. On `block_signal`'s default grid from 1080p footage: **4.9 ms/frame at
the default 5 s window**, 8.0 ms at 8.5 s, and 1.1 ms at 30 s.

That is not a typo — **cost rises with the window and then falls.** Below about
8.5 s (at 30 fps) every frame is admitted and every frame pays for a median over
a longer ring. Above it the stride exceeds one, the medians run on one frame in
two or one in four, and the per-frame cost drops. The step is visible if you
sweep the slider across it.

Memory is up to 512 copies of one input frame — trivial on a block grid, which
is where this filter belongs, and gigabytes on a full-resolution frame, which is
why it accepts float input only and expects to sit downstream of extraction.

## Warmup

`window_seconds × fps − 1` source frames, which the planner decodes ahead of the
requested span. It is the largest lead-in any filter in this repo asks for and
it is charged per configuration rather than as a worst case — the declared bound
of 7199 frames is what a 30 s window at 240 fps would need, and no run pays it
unless it asked for it.
