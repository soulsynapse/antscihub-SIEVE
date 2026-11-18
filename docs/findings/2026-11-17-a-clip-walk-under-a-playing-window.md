# A clip walk under a playing window

2026-11-17, on `v5-what-a-node-declares`. Kendrick saw the monitor's ms a row climb steadily for
most tools over a clip walk of `B-20250101-021609-1735722969014-7.json`: 3840x2160 footage, video,
region, hsv, inrange, detect, then size, track, travel and two smooths, region shown, a window of
250 rows, the memo and the decoder's cache at 4 GB each.
`docs/findings/experiments/2026-11-17-a-clip-walk-under-a-playing-window.py <document> <seconds> <rows a bucket>`
opens a copy of the document in a player on the screen, starts the clip walk and prints what is
below. Every figure is one run on a machine in use, and runs differ by a third in their rate.

## What rose, and why

The window opens playing. Both stores let go of what was least lately read, and a clip walk puts
every row it computes into both, so once they were full it discarded the window's rows and the
worker computed each again as the playhead came to it. Ms a row in buckets of 250 of the walk's
rows, 42 s, playing:

```
rows from    detect       hsv   inrange    region     track     video   gui ms/row
        0     4.370     1.709     2.821     1.952     0.455     2.059   1.935
      250     3.466     1.574     3.007     3.309     0.457     5.104   4.198
      500     3.533     1.643     2.957     3.488     0.441     4.910   5.126
     1000     3.948     1.718     3.024     3.547     0.474     5.384   5.790
     1750     3.730     1.810     2.963     3.510     0.454     5.091   5.202
```

From row 250 on, each 250 rows had about 360 decodes of the video, 114 `rowReady` slots and 230
paints of the frame; every ask of the worker for a display row came from `PlayerWindow._tick`.
It is a step where the stores fill, in video and region, region being the shown node, and no
climb: hsv, inrange, detect and the stepped nodes are level through 2,300 rows. The monitor's
figure is a node's ms over the walk's rows done, so the step reads there as a slow climb, video
1.88 at row 256 and 3.80 at row 2188. Paused, 10 s: video 1.5 to 2.1, region 2.2 to 2.3, the GUI
thread 0.03 to 0.15, and 767 rows against 619 playing.

A headless walk of the document, and a player offscreen over a copy with no held file, showed no
rise over 600 to 900 rows.

## The stores let go by an order

`Memo.order` and `Decoder.order` are a function the store asks, once it is past its limit, for a
ranking of its keys; `Graph` hands both one. A row outside what `Graph.holds` was told, the
window, goes before one inside; of two on a side the one further from every row something is at,
the display's by `Graph.looks_at` and each lane's walk's; in the memo an entry under a key no
node has goes before all, and inside the window a node the display does not read goes before one
it does. A store clears a sixteenth of its limit at a time, so the ranking is taken once for
many discards.

The last clause is there because this window does not fit the memo: region, hsv and inrange over
250 rows are about 7 GB, region alone about 3 GB. Ranked by row alone the walk was level from row
250 to 500 and computed display rows again past it, 97 `rowReady` in the next 250.

Playing, 20 s, with the order:

```
rows from    detect       hsv   inrange    region     track     video   gui ms/row
        0     4.819     1.859     3.086     2.080     0.504     2.221   2.232
      250     4.215     2.961     3.282     2.983     0.606     2.482   1.790
      500     3.652     2.322     3.020     2.809     0.531     2.327   1.624
      750     4.504     2.723     3.581     3.058     0.712     2.643   2.402
```

From row 250 on each 250 rows had 247 to 252 decodes and no `rowReady`. A run of 25 s from a
fresh copy of the document, whose held file did not spare the window, was the same past row 250,
and every node in it was slower from its first bucket, track at 1.1 against 0.45, which the stores
do not explain and which was not looked into.

## Not measured

- What taking the ranking costs a row: a sort of the store's image entries under its lock, once
  for a sixteenth of its limit.
- hsv and region read a half to one ms a row higher with the order than paused without it; one
  run each, not told from the machine.
- A window that does not fit the decoder's cache, a clip walk with the playhead outside the
  window, and a document whose shown node is not on the walked path.
- v5 was not run: that the rise is not this branch's is read off the branch's diff, which touches
  neither the tick nor the stores.
