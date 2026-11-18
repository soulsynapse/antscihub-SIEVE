# What the stores let go of first

2026-11-17, on `v5-what-a-node-declares`. Three trees set side by side: `v5` at `cf063108`, the
branch at `3e0ed73c` ("before"), and the branch with the change this finding is of ("now"). The
rule `docs/findings/2026-11-17-a-clip-walk-under-a-playing-window.md` describes under "The stores
let go by an order" is the one before; this one's is below, and that finding's first line under
"Not measured" is measured here.

Every figure is one thread's replay or one timing on a machine in use, Kendrick's player open on
it for the later runs. The store limits are small, 4 to 256 MB, so the stores fill in seconds; the
player's are 4 GB.

## What was found in the rule before

The memo and the decoder's cache, once past their limit, sorted every image entry they held by
the graph's order, under their lock, and let go of a sixteenth of the limit.

- The sort is of the whole store. `2026-11-17-the-longest-put.py`, the memo full of entries of 64
  bytes, a window of 600 rows held and a walk going on past it: the longest single `Memo.put` was
  11 ms at 20,000 entries, 64 ms at 100,000 and 190 ms at 300,000, where v5's was 1.6, 2.6 and
  11.6. The display's read of the memo waits on that lock. At 4 GB a 1080p plane is about 2,000
  entries and a plane of `test.json`'s coarsegrain, 12.5 KB, about 320,000.
- A row outside the window ranked by how far it was from the nearest of the display and the walk,
  so the rows midway between the two went first. After a walk of 1,500 rows under a window at row
  0, the window moved to row 750 was computed again whole, 161 runs and 81 decodes for 80 rows,
  where v5 computed none of it.
- A lane's walk said where it was at every row and never that it had stopped, so the rows beside
  where a walk last was stayed the last to go.
- `PlayerWindow._show_held` asked `registry.code_print` of each node's tool, and each asking listed
  the tools' folder and looked at each shared file again: about 4 ms on the GUI thread at each ask
  of the window, 0.006 on v5.

## The rule now

`decoder.letting_go` is both stores'. The order answers None for an entry that goes as any does,
and a rank for one kept back: a row inside what `Graph.holds` was told, or within `graph.NEAR` of
a walk under way. A store past its limit lets go of the least lately read entry that is not kept
back, moving each kept one it meets to the new end, and nothing is ranked while one of the others
is left. Only with none left does it rank those kept back, by the order as it was among them, and
clear a sixteenth of its limit. An entry under a key no node has goes as any does, where it went
before all. A walk says it rests at its last row, where it is stopped and where it begins again,
and `Graph.rests` forgets its lane. `registry.code_print` takes a dict that one moment's calls
share, so a folder is listed and a file looked at once among them.

Outside the window a store is an LRU again, as v5's is, so a walk leaves one run of rows behind
it. Which rows that favours is Kendrick's choice, made in this session: the rows a walk last
passed over the rows just past the window.

## Measured

The longest single put, ms, and the mean, µs:

```
entries        v5            before          now
 20,000     1.6  0.76     11.2  3.50      1.6  1.48
100,000     2.6  0.78     64.4  3.73      4.4  1.48
300,000    11.6  0.85    190.4  3.99     19.2  1.60
```

Before and now the 1,200 entries of the window's rows were all held at the end; on v5 none.

`2026-11-17-the-stores-under-a-replay.py`, `test.json` (462x456, motion shown and walked): the
display's tool runs and decodes made again while a clip walk of 1,500 rows ran under it, then the
window's first lap where it was moved to.

```
                                          v5           before        now
memo 32, cache 32, window 80
  under the walk                          0 / 0        0 / 0         0 / 0
  moved to row 750                        0 / 0        161 / 81      0 / 0
  moved to row 80                         161 / 83     0 / 0         160 / 80
memo 32, cache 32, window 300, more than the cache holds
  under the walk                          43 / 22      0 / 0         0 / 0
  moved to row 750                        0 / 0        187 / 94      0 / 0
memo 4, cache 32, window 300, more than either holds
  the loop alone, a lap after the first   600 / 300    0 / 0         0 / 0
  under the walk                          657 / 323    105 / 39      81 / 32
  the walk's decodes a row                1.0          0.80          0.80
  moved to row 750, the second lap        601 / 301    80 / 38       0 / 0
```

`purb-168-178.json` (1920x1080, threshold shown, blobs walked and drawn), memo and cache 256 MB,
window 60, a walk of 590: under the walk 152 / 77 on v5 and 0 / 0 before and now; moved to row 295,
120 / 61 on all three. The memo's bytes as it counts them were its bytes as they are in every
replay on every tree, the tables of blobs among them.

The row "moved to row 80" is the cost of the choice: the rows just past the window are the oldest
a walk leaves, and go first.

With stores that discard nothing, the walk's ms a row over the 1080p clip, two runs each in turn:
v5 2.87 and 2.52, before 2.59 and 2.62, now 2.82 and 2.97. Four runs each of v5 and before earlier
in the session were 2.59 to 2.83 and 2.77 to 2.90. Not told apart.

`2026-11-17-what-a-window-ask-costs-the-gui-thread.py`, a player offscreen, `_show_held`: on
`purb-settings.json` 6.3 ms before and 1.2 now, on the Thermal hysteresis document 7.8 and 1.8,
each pair run back to back; `Graph.sync` 1.9 and 2.0, 3.2 and 2.2.

## Not measured

- Two threads: the replay is one thread's, in a fixed order.
- The stores at 4 GB, and the 3840x2160 document the first finding is of.
- A window that fits neither store beyond the one replay above. There the entries kept back are
  ranked and a sixteenth cleared as before, so the lock is held for the window's entries, not the
  store's: with a window as long as a long clip of small planes that is the 190 ms again.
- What a walk begun again costs in rows beside it let go between its resting and its first row.
- The player on the screen.
