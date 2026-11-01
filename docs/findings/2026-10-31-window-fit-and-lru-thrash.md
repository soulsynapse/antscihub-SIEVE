# The stores against the window: LRU thrash, and where a scrub's cost lands

2026-10-31, on v5-performance-monitor at efd1fe10, read off the first dev monitor, discarded and
rebuilt as `sieve_player/dev/monitor.py` in 295ac684, polling the runtime and chaining consumers onto
the probe, not off a dump. The file is
`video-tests/rep3_intermittent_crop.MP4`, 456×462 at 59.94 fps, 30579 rows; the document
`video-tests/test.json`, video → gray → rescale → threshold → motion; the window 600 rows. Limits at
the time: decoder cache 256 MB, memo 512 MB. Numbers are one run each, offscreen, and vary by a
few percent between runs.

## What one row costs, and what the window needs

| per row | this clip | 1080p, extrapolated |
|---|---|---|
| raw frame (decoder cache) | 0.60 MB | 5.9 MB |
| gray + rescale + threshold + motion (memo) | 0.35 MB | ~3.5 MB |
| 600-row window: cache / memo | 361 / 211 MB | 3.5 / 2.1 GB |

So at the limits above the memo holds this window (2.4 windows) and the decoder cache does not
(0.7 windows). A chain with flow in it puts eight bytes per pixel in the memo per row against the
frame's three, and neither store holds a window on real footage at any limit so far considered.

## A store the window does not fit serves a rewalk nothing

Rewalks after clearing one store and keeping the other, counted from the probe's read kinds while
serving the walk:

| rewalk | decodes | cached reads | runs | s |
|---|---|---|---|---|
| memo cleared, cache kept at 256 MB (0.7 windows) | 585 | 0 | 2353 | 0.51 |
| cache cleared, memo kept | 0 | 0 | 0 | 0.19 |
| cold, cache raised to 400 MB (1.1 windows) | 586 | 1 | 2359 | 0.48 |
| memo cleared, cache at 400 MB | 0 | 587 | 2359 | 0.29 |

The cache at 70% of the window answered zero reads on a rewalk. The walk is a sequential scan over
the window, and LRU on a cyclic scan larger than itself evicts each row just before it is wanted
again; the hit rate is zero at anything under 100% and near-complete at anything over. This is the
textbook buffer-management result and it holds here exactly. The coverage view made it visible: the
cache holds the last 424 rows of the window, the rewalk starts at row 0.

Two consequences. Sizing is a binary per store, the window fits or it does not, so the natural unit
is rows of the window, derived at load from the frame size and the first row's per-node bytes, not
a byte figure chosen once. And for a window that does not fit, LRU is the worst policy for the walk;
keeping the rows nearest the window and playhead, as Blender's frame caches evict farthest-from-
playhead and Houdini's Cache SOP bounds in frames, would give a partial hit rate instead of none.

## Where a scrub's cost lands

The window shows a row from the memo when it can (`goto` peeks first) and asks the worker only on a
miss. Timing `goto` from outside, playback inside a walked window showed 58–60 rows a second, every
one from the memo, the slowest 0.2–0.3 ms. A row the walk has not reached cost video 15–18 ms (a
seek) plus 1–3 ms unprobed (wait behind the walk, and the draw). So inside a walked window the scrub
is free, and a node that feels slow, an overlay say, costs on the walk: it runs once per walked row
and shows as walk time and as how long the window takes to cover, not as scrub latency. The felt lag
cases are a row ahead of the walk and the draw, and only the first is in the stream.

## What a rewalk costs by trigger

With the memo holding the window, a change on threshold reran threshold and motion only, 2.0 runs
per row, 0 decodes, 0.23 s; a cold walk is 4.0 runs per row with a decode each, 0.45–0.75 s. The
trigger is readable from the sync events' key diff. A change on gray, which reads the video, would
also redecode while the cache does not hold the window.

## For the display, when it is specced

The three things that read directly, and that bytes held or mean ms per node do not: which rows of
the window each store holds, as lanes; each store stated in windows; and per node, what a change
there costs over the window (the node and everything downstream, plus the decode when a video-
reading node reruns under a short cache). A per-row attribution of the scrub is not useful inside a
walked window, for the reason above.
