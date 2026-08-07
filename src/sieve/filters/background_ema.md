# Background EMA

Maintain a running model of what the arena looks like with nothing moving in it,
and emit either that model or the difference from it. Frame rate, dtype, and
channel layout are unchanged; the output is the same size as the input.

The model is updated once per frame:

```
background <- background + alpha * (frame - background)
```

seeded with the first frame the run sees.

## When to use it

**When what you are looking for moves and the arena does not.** Ants on a
uniform substrate, under fixed lighting, with the camera bolted down. The
difference from the background is then the animals plus whatever else moved, and
the "whatever else" is the thing that decides whether this works: a lid
reflection that shifts when someone walks past the rig is foreground, and no
value of `alpha` makes it not be.

**Not as a first pass on footage with a moving camera or changing light.** A
handheld clip, a rig near a window, or a session that spans a light timer will
put the entire frame into the foreground at every transition. The model will
recover — that is what `alpha` is — but it recovers over tens of seconds and the
frames in between are unusable rather than merely noisy.

**Put a downsample in front of it.** The model is float32 whatever the input
was, so this filter is the largest thing a run holds in memory: at 1080p BGR the
model alone is 6 MB and the working set is around 14x the input frame. A 4x
downsample before it cuts that sixteenfold, and a background model is one of the
few things that loses almost nothing to resolution — you are estimating a
per-pixel level, not a shape.

## Parameters

### `alpha` (0.05–1.0, default 0.05)

How much of the newest frame goes into the model. This is the whole tuning
question and it has no correct answer in the abstract — it is a statement about
**how long the animals in your footage hold still**.

The number to reason with: after `n` frames, a thing that stopped moving has
been absorbed into the background to within 1% when `(1 - alpha)^n < 0.01`.

| `alpha` | frames to absorb | at 30 fps |
| ------- | ---------------- | --------- |
| 0.05    | 90               | 3.0 s     |
| 0.10    | 44               | 1.5 s     |
| 0.25    | 17               | 0.6 s     |
| 0.50    | 7                | 0.2 s     |
| 1.00    | 1                | one frame |

Read that table as: **an ant that stops for longer than this disappears.** If
your animals rest for twenty seconds at a time and you need them detected while
resting, `alpha` has to be low enough that twenty seconds is under the absorb
time — which at 30 fps means below about 0.008, and this filter's lower bound is
0.05. That is not an oversight; see *What it does not do* below.

If instead you are measuring *activity* — where movement happened, not where
animals are — a high `alpha` is the right choice and the failure mode inverts:
at `alpha = 1.0` the model is simply the previous frame and the output is a
frame difference, which shows the leading and trailing edges of anything that
moved and nothing at all about anything that did not.

The symptom of `alpha` too high is animals that fade out while they groom. The
symptom of `alpha` too low is a background that still carries a ghost of where
the animals were ten seconds ago, which reads as a second, dimmer colony.

### `emit` (`foreground` or `background`, default `foreground`)

- **`foreground`** is `|frame - background|`. This is what you feed a threshold
  or a blob detector.
- **`background`** is the model itself. Switch to it while tuning `alpha` and
  look at it directly. The foreground shows the model only indirectly, and a
  background that has absorbed the animals looks exactly like one that never saw
  them — both give an empty foreground, and only the model tells you which
  happened.

## Warmup

This filter declares **90 frames of warmup**, and it is the first in this repo
that declares any. The pipeline decodes that many frames before the start of
your clip, runs them through the model, and throws the outputs away.

Two consequences you will actually see:

**A clip that starts less than 90 frames into the source cannot be warmed.**
`sieve run` warns and names the shortfall; the first outputs come from a model
that is still partly the seed frame. Move the clip later if you can.

**The 90 is a worst case, not your case.** It is computed at `alpha = 0.05`,
because the declaration is static and cannot read your parameters. At `alpha =
0.5` the model is settled in 7 frames and the other 83 are decoded for nothing.
That is the price of a lead-in that is never too short, and too short is the
failure that is silent — an unsettled model produces a perfectly plausible
foreground, and the tuning you do against it is wrong rather than absent.

## What it does not do

**It does not cache.** Every other node in a graph writes its output to the
frame cache and is served from it on a re-run; this one is recomputed every
time. A re-run of a graph containing this filter costs a full pass over the clip
even when nothing upstream changed, which — see *Cost* — is not cheap.

The reason is not that this filter's results vary. Given the 90 frames of warmup
above they do not, and that is tested. It is that the pipeline decides what may
be cached from a filter's *declarations*, and no declaration distinguishes a
filter whose warmup number is honest from one whose is not. Rather than serve
cache entries on the strength of an unverifiable claim, anything that remembers
across frames is excluded. The full argument is in
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.

**It does not go below `alpha = 0.05`.** Lower values are legitimate and are
what footage with long rest bouts wants, but the warmup they need grows fast —
`alpha = 0.01` needs 459 frames — and a lead-in that long is a decision about
the shape of a run rather than a slider position. It belongs to a future version
of this filter that declares it, not to this one.

**It does not threshold, label, or count.** The output is a difference image
with the same dtype as the input. Turning that into detections is the next
filter's job.

## Cost

Declared as **6 work units per input megapixel**, anchored to copying one
megapixel of a frame. That is relative work, not seconds: an
uncalibrated machine can compare it to other filters, but cannot turn it into
wall time until calibration measures the anchor.

The work comes from widening the frame, updating the float model, deriving the
requested output, and narrowing the result. This is still the filter the "put a
downsample early" advice in `downsample.md` was written for: downsampling lowers
the pixel count before the model and scratch buffers are allocated and before
the repeated frame traversals run.

Emitting the background is cheaper than the foreground by one difference and
absolute-value pass, but the static declaration takes the default foreground
path. `alpha` does not affect per-frame work.

It is also recomputed on every run, because it does not cache — see *What it
does not do*. A graph you re-run while tuning something downstream pays this
work every time, which is the other reason to keep the frames small.
