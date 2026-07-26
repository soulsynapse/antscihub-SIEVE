# Rescale

Reduce spatial resolution by a float linear scale factor. Output extents are
`round(src x scale)`; frame rate, dtype, and channel layout are unchanged.

## When to use it

**Put it first, and use it to buy speed.** Every filter downstream costs
`scale squared` of what it would have — 0.25 is a sixteenfold reduction in
compute and memory for everything after it, which is usually the difference
between a live tuning loop and a slideshow.

**The question to ask is how many pixels the thing you are measuring is.** If
an ant is 40 px across in the source, 0.25 leaves 10 px and its motion is
still a shape; at 0.1 it is 4 px and the signal starts merging with its
neighbours. Measure the target in the source, multiply, and stop where the
answer stops being a shape.

The block grid downstream is held fixed in *source* pixels (`block_signal`'s
auto block size multiplies by this scale), so changing the scale changes
compute cost, not where a detection localizes. That is the property that
makes this knob safe to turn freely while tuning.

## Parameters

### `scale` (0.05-1.0)

The linear factor for both axes. 1.0 is an exact no-op — the frame passes
through untouched, verified bit-identical. 0.25 means each axis is a quarter
of the source: 25 % linear, 6.25 % of the pixels.

## What it does not do

It does not crop. The region is chosen per replicate and applied at the root
of the graph; this filter shrinks whatever it is handed, and shrinking your
way to a region of interest throws away resolution the crop would have kept.

It does not change frame rate, and it does not shrink by integer division —
that is `downsample`, whose truncating integer factors compose exactly and
suit checkpoints. This filter exists for the live tab's continuous scale
knob, where 0.3 is a legitimate answer.

## Cost

Roughly 0.33 ms per megapixel of input (the same INTER_AREA kernel as
`downsample`'s anti-aliased path). At 1.0 it costs nothing at all — the
no-op is skipped, not computed.
