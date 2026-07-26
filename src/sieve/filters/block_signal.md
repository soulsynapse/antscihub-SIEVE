# Block signal

Per-block motion signal from the structure tensor of consecutive frames.
Each output frame is a small grid, one float32 value per block; the series
of those grids is what the temporal filter and the detector read.

## When to use it

This is the extraction step of the live detection chain — use it whenever
the question is "where and when is something moving", and pick the signal by
what "moving" means for the experiment:

- **`change_energy`** measures how much each block's pixels are changing,
  regardless of direction or coherence. It responds to leg movement, antennal
  flicker, a wing catching light — any temporal change. It is also the cheap
  signal (a quarter of `flow_speed`'s cost) and the right default while
  tuning everything else.
- **`flow_speed`** measures coherent translation, in pixels per second. A
  block only scores when its texture visibly moves as a piece; flicker and
  shimmer that `change_energy` counts are largely invisible to it. Choose it
  when the event is locomotion and the noise is light.

Blocks with no resolvable texture report `flow_speed` of exactly zero — the
honest answer under the aperture problem, not noise. A smooth arena floor
scoring zero means "nothing measurable here", not "nothing happened".

## Parameters

### `signal` (`change_energy` | `flow_speed`)

Which read of the tensor leaves the node. Swapping it changes the *units*
of everything downstream (energy vs px/s), so thresholds tuned on one do not
mean anything on the other.

### `block` (0-1024, default 0 = auto)

Working pixels per block. Auto means 64 *source* pixels scaled by the
upstream rescale factor, which holds the grid fixed in source coordinates —
turning the rescale knob then changes compute cost, not where a detection
localizes. Smaller blocks localize better and cost more memory downstream
(the detector holds a per-block series); bigger blocks average more texture
into each value.

### `scale`, `fps`

Plumbing, not tuning: `scale` is the upstream rescale factor (used only to
resolve an auto block) and `fps` the source frame rate (used only to express
`flow_speed` in px/s). The tab writes both from values it already owns.

## What it does not do

It does not choose a frequency. Everything rhythmic about the signal —
grooming at 4 Hz against walking at 1 — is the temporal filter's job,
downstream. This step only says how much each block changed between two
frames.

It does not track. Blocks are fixed cells, not followed animals; an ant
crossing the arena lights up a path of blocks in sequence.

It does not output an image you can watch directly. The output is a block
grid; the tab's video panel renders it as an overlay on the footage.

## Cost

Dominated by the Gaussian blur of the tensor products (the blur is the
tensor's spatial window). `change_energy` blurs one plane; `flow_speed`
blurs five and solves a 2x2 system per pixel, ~4x the cost. Both are
~realtime at a typical working resolution, which is why this step is
recomputed rather than cached (it carries the previous frame as state, and
stateful nodes are uncacheable by contract).
