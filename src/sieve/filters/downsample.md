# Downsample

Reduce spatial resolution by an integer factor. Output is `(h // factor,
w // factor)`; frame rate, dtype, and channel layout are unchanged.

## When to use it

**Put it early, and put it before anything expensive.** Every filter downstream
costs `1 / factor**2` of what it would have — a 4x downsample is a sixteenfold
reduction in both the time a tuning pass takes and the bytes a checkpoint
writes. If a run does not fit on disk or a preview does not meet its budget,
this is the first thing to reach for.

**The question to ask is how many pixels the thing you are measuring is.** If an
ant is 40 px across, a 4x downsample leaves 10 px and every measurement about
its body axis is still available. At 8x it is 5 px and the orientation estimate
is noise. Measure the target in the source, divide, and stop where the answer
stops being a shape.

## Parameters

### `factor` (2–64)

The integer divisor for both axes. The output is truncated, not padded: a
1920x1080 frame at `factor=4` is 480x270, and at `factor=7` it is 274x154 with
the last two columns and last row of the source dropped.

Powers of two are worth preferring when a checkpoint will be written — not for
speed, but because a chain of them composes exactly and a `factor=6` after a
`factor=4` does not divide the source in any way you can restate.

### `anti_alias` (default true)

- **True** averages each `factor`x`factor` block. This is the right choice for
  anything you will measure an *intensity* from: a mean brightness, a threshold,
  a colour. It is also the right default, because a downsample that samples
  rather than averages will alias any periodic texture in the arena — a mesh
  lid, a grid floor, a printed marker — into a pattern that is not there.
- **False** takes the top-left pixel of each block. Choose it when the signal is
  a small number of extreme pixels rather than a level: a single-pixel LED, a
  colour marker on a paint-marked ant, a binary mask you have already thresholded
  and do not want blurred into intermediate values.

The failure mode of the wrong choice is quiet in both directions. Averaging a
one-pixel marker divides its contrast by `factor**2` and it disappears below a
threshold that was tuned before the downsample; sampling a textured background
produces moiré that a blob detector reads as animals.

## What it does not do

It does not crop. The region is chosen per replicate in the Replicate tab and
is applied at the root of the graph on every frame; this filter reduces whatever
it is handed. Downsampling to reach a region of interest is the wrong tool and
throws away the resolution the crop would have kept.

It does not change frame rate. Nothing here decimates in time — that is a
separate filter, and keeping the two apart is what lets the storage prediction
multiply them.

## Cost

Declared as **2 work units per input megapixel** for the anti-aliased path: one
neighborhood read and one smaller write, relative to the copy anchor rather than
to a reference CPU.

Turning `anti_alias` off is cheaper, but that difference is almost never the
reason to choose between the settings. Choose `anti_alias` for what it does to
the pixels. If this filter is the thing you are waiting on, raise `factor`.
