# The held file written whole at every run held: three seconds of the interpreter each, once a clip run is in it

2026-11-13, on v5-held over 20d1998c with the held-results work in the working tree, on an i9-14900KF,
by `docs/findings/experiments/2026-11-13-what-the-held-file-costs.py` on Kendrick's own
`speed output.json.series` of that afternoon: `square-1.mp4`, 345595 rows, chain track, size and count,
a bare walk's run over the whole clip and 21 window runs of 600 rows under keys the chain had since
moved to.

## What Kendrick saw

A bare walk read in and filed; something upstream of track adjusted, then track; every window after
it lagged. The monitor's report of 17:51:51 on one such window: 6.40 ms a row against 1.18 for the
walk before under the same plan, every tool's span slower together (detect 0.34 to 3.09 ms, threshold
0.09 to 1.13, the decode 0.28 to 0.86), the GUI 1139 ms late at worst, and SIEVE writing 9.1 MB a
second to the disk. Nothing the ledger probes had changed.

## What it was

The file was one pickle of every run (`held.save`, VERSION 3), written again whole two seconds after
any run was held. A window walked under a new key is a new run, so each window placed and each knob
moved rewrote the clip run with it, stale as it was. Track's `rows` is an object array of one small
table a row, and pickle's time is in their count, not their bytes; it holds the interpreter throughout,
so the writer's thread, which the ledger does not see, took it from the worker's tools and the GUI's
paints alike.

| | one pickle, VERSION 3 | `held.File`, VERSION 4 |
|---|---|---|
| the file | 85.2 MB | 24.0 MB |
| read at open, on the GUI thread | 2155 ms | 62 ms |
| a run's first filing, the clip run's | 2689 ms | 2107 ms, 1775 on the later run |
| a write after a 600-row run is held | 2689 ms, the whole file | 3.5 ms, the run added |
| a write after a run is let go | 2689 ms, the whole file | 19 ms, the records kept copied as bytes |

`held.File` knows where the record of each run it has read or written lies and pickles a run once: a
new run is added behind the file's, and when a run is let go, covered by a wider one or over
`window.HELD_BYTES`, the file is made again from the kept records' bytes. A record holds a row's tables
as their concatenation and the rows' lengths where every row's table has one dtype with no object field
(`held._flat`); the concatenation of 345595 tables is nearly all of the clip run's first filing, which
is the one cost left that grows with the clip, paid once a run on the writer's thread.
`tests/test_held.py` holds that a run the file has is not pickled again.

The VERSION 3 column and the first three figures of the other are of the file as the bare walk left it.
A player started on VERSION 4 at 17:57 read that file as none and wrote its own over it, so the last
two rows are of a clip run made by repeating a 600-row run of the later file to 345595 rows.

Not changed by this: a table with an object field, track's contours in `video-tests/purb-168-178.json`,
is pickled a row at a time, at its first filing and at every open. Every knob position a window's chain
is run at is held as a run of its own, under its own key, and none goes until the bound; what a long
session of them costs the window's own loops over `runs` is not measured. The writer's thread emits
nothing into the stream, so the monitor saw its cost only as every tool slower at once.
