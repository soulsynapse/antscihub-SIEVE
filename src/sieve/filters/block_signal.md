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
- **`coherence`** measures how much of a block's change one translation
  explains, on a fixed 0-1 scale. A block whose texture moves as a piece
  scores near 1; a block changing in place — grooming legs, antennal
  flicker, anything oscillating — scores near 0. It carries no magnitude at
  all, which is the point: pair it with `change_energy`, and "high energy,
  low coherence" is a grooming detector with no state and no time constants.
  Being a pure ratio, it is also the one signal whose thresholds transfer
  across lighting and gain unchanged.
- **`flow_agreement`** measures whether the pixels that moved moved the *same
  way*, on a fixed 0-1 scale: 1 when the block translates as a piece, 0 when
  its motion cancels. It is coherence's question asked of the flow field
  instead of the eigenspectrum, and on the reference clip the two disagree
  far more than they agree — coherence counts all change against a single
  translation, agreement ignores everything that never resolved into a
  vector, so a block that is half featureless floor reads on the half that
  moved. Choose it when the event is a group of pixels turning together —
  or a group failing to, which is what a struggle looks like next to a walk.

Blocks with no resolvable texture report `flow_speed` of exactly zero, and
`flow_agreement` of exactly zero — the honest answer under the aperture
problem, not noise. A smooth arena floor scoring zero means "nothing
measurable here", not "nothing happened"; for agreement in particular it does
*not* mean "these pixels disagreed".

## Parameters

### `signal` (`change_energy` | `flow_speed` | `coherence` | `flow_agreement`)

Which read of the tensor leaves the node. Swapping it changes the *units*
of everything downstream (energy vs px/s vs a dimensionless ratio), so
thresholds tuned on one do not mean anything on another.

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

`coherence` does not detect on its own. It answers "what kind of change",
not "how much": a nearly static block with a whisper of sensor noise can
legitimately read high, because whatever negligible change is there may well
be consistent with one translation. Blocks with exactly zero change report
0 rather than that vacuous 1, but the working rule is to gate coherence
against `change_energy`, never to threshold it alone.

## Cost

Dominated by the Gaussian blur of the tensor products (the blur is the
tensor's spatial window). `change_energy` blurs one plane; `flow_speed`
blurs five and solves a 2x2 system per pixel; `coherence` blurs six and
eigendecomposes one 3x3 matrix per block (a few hundred tiny solves — not
the cost); `flow_agreement` is `flow_speed`'s five blurs and the same solve,
plus two more block reductions, so it is free in the tier sense — there is no
cost argument for preferring one of those two over the other. The last three
sit at ~4x `change_energy`, and all are ~realtime at
a typical working resolution, which is why this step is recomputed rather
than cached (it carries the previous frame as state, and stateful nodes are
uncacheable by contract).
