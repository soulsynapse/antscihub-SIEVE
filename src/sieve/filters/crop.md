# Crop

Take a rectangular region of every frame. The region is intersected with the
frame, so a box that overhangs an edge comes back trimmed rather than refused,
and the default box — larger than any frame — is the whole of whatever arrives.

## When to use it

**First, and before anything you are paying for.** Every filter downstream costs
the fraction of the frame you kept. An arena that is a sixth of a 4K frame makes
the rest of the chain six times cheaper, and unlike a downsample it costs
nothing in resolution: the pixels you keep are the pixels that were there.

**When the frame holds more than one experiment.** A rack of a dozen arenas in
one video is a dozen crops of the same footage, each measured on its own. That
is what the Replicate tab writes today; a crop node is the same region stated in
the graph, where a cache key can see it.

**When something outside the arena moves.** A hand reaching in at the edge, a
timestamp burned into a corner, a reflection off the lid — anything a detector
would count that is not the animal. Cropping it out is cheaper and more honest
than tuning a threshold until it stops noticing.

## Parameters

### `roi`

Four integers — `x`, `y`, `width`, `height` — in the coordinates of **this
filter's input**, with the origin at the top-left and `width`/`height` counted
from `x`/`y`. Not source pixels: a crop placed after a rescale indexes the
rescaled frame, and a second crop after a first indexes what the first emitted.
Reading a box off the replicate table and pasting it into a crop node that sits
downstream of anything spatial gives a region somewhere else entirely.

The default is `x=0, y=0, width=1048576, height=1048576` — a region larger than
any frame, which meets every frame as the whole of it. That is what "no crop"
is: a value of this parameter, not the absence of the node. It is written this
way because a full-frame box in pixels cannot be typed by anybody who has not
opened the video, and the graph is written by things that have not.

## What it does not do

It does not scale. The pixels it keeps are unchanged — same dtype, same channel
layout, same values — so a crop never trades resolution for speed the way a
downsample does. If a crop is not enough, put a downsample after it.

It does not decode less. Cropping in the graph still reads whole frames off
disk; what it saves is every filter downstream of it, not the decode. Cutting
the decode is what materializing a crop artifact does, and that is a separate
step with a file at the end of it.

It does not follow anything. The region is fixed for the whole run. A moving
subject that leaves the box is gone from the run, and there is nothing here that
notices.

## Cost

0.48 ms per megapixel kept on 1080p three-channel frames — a memory copy, and
the number is the memory bandwidth rather than anything about the operation.

The identity crop is free: a full-frame region is already contiguous and no copy
happens, 0.002 ms at any resolution. So a crop node left at its default costs
nothing measurable, which is what makes "no crop" affordable to spell as a
present node.

Against a decode of tens of milliseconds per frame this is never what a run is
waiting on. It is the thing that makes what comes after it cheap.
