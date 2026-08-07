---
title: A checkpoint does not record which product of a tool it holds
priority: normal
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# A checkpoint does not record which product it holds

`ToolSpec.emissions` (05.4) says a node of `block_signal` can emit any of four
measurements and a node of `background_ema` either half of one model. The
manifest `storage/checkpoint_writer.py` writes records the node id, the cache
key, the span, the dtype and the shape — everything except which of those
products the file in front of the reader actually is.

Recoverable today, because the params are in the project document beside it and
the selecting parameter is one lookup away. That is the same argument v2 made
for leaving a fact out of an artifact and then had to walk back: the file is
what a reviewer opens, and a `.npy` of float32 that could be coherence or flow
speed is one a reader cannot check against the claim it was made for.

Not urgent and not sequenced: the reader that would consume it is the read-back
path, and the save screen that writes one file per checked emission is Phase 7.
Whichever arrives first is where this is answered — as a manifest field the
writer is handed, not one it derives, since the writer takes outputs and knows
nothing about tools.
