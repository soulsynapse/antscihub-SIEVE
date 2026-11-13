# What a clip walk holds, and what a node run whole costs over an hour

2026-11-12, on v5-monitor, the working tree over f410e9a1 with `count`, `reduce` and `spacing` stepping.
Experiment: `docs/findings/experiments/2026-11-12-what-a-walk-holds.py`. One run, while Kendrick baked on
the same machine: the bytes are counts and stand; the timings are inflated by an unknown amount and want
taking again on a machine left alone.

The question was whether a clip of an hour can be walked. `video-tests/purb-settings.json`, 38100 rows at
59.94 fps, its clip walked cold as saved and with every bake live, and `worker._Walk.bytes` read against
`STACK_BYTES`, 512 MB, with what each stepped node holds beside it.

| | as saved | every bake live |
| --- | --- | --- |
| the walk's bytes | 94.4 MB, 2599 a row | 87.9 MB, 2420 a row |
| the head's rows: `bake_2` stepped, or the stack | 1199 a row | 1079 a row |
| `track` | 1208 a row | 1149 a row |
| `count`, `size`, `travel`, each | 64 a row | 64 a row |
| records a row in track's tables, mean and most | 2.3, 5 | 1.3, 4 |
| of a track row, in records and behind contours | 149, 995 | 85, 999 |
| the cap reached at | row 206571, 57.4 min | row 221876, 61.7 min |

So an hour of this document, 215784 rows, is at the cap: 0.52 GB as saved, refused some minutes short, and
0.49 GB live. Nothing in purb runs whole now, and the walk still does not fit, because it holds the blobs
tables and the tracks tables for every row and both are mostly contour.

Three things in the count that are not what is held. A signal's share is a numpy scalar and `graph.nbytes`
charges it 64, "anything else that is not None", where the array it lands in holds 4: the three signals
are charged 192 bytes a row and hold 12. Whether track's contours are the blobs' own arrays, charged once
under each node and held once, was not read. And the saved document's tracks hold 2.3 records a row where
the live chain's hold 1.3 at nearly the same contour bytes, which is not explained here; the saved chain
reads `bake_2`'s file and the live one walks the frames.

The tools that cannot step, run whole over prefixes of the saved walk's own tracks and its count signal,
ms a run; a line fitted through the four and summed over an emit every 30 rows.

| tool | 4762 rows | 9525 | 19050 | 38100 | the clip's emits, s | an hour's emits, s | once over an hour, s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| smooth, mean, reach 2 | 0.6 | 0.6 | 1.0 | 2.0 | 1.4 | 35 | 0.0 |
| smooth, median, reach 60 | 29.0 | 32.6 | 60.7 | 91.9 | 71 | 1656 | 0.4 |
| tracks-filter, rows | 163 | 251 | 547 | 1850 | 972 | 38680 | 11.0 |
| tracks-filter, path | 220 | 443 | 562 | 1711 | 999 | 33815 | 9.5 |
| resolve, no column read | 400 | 875 | 1069 | 2126 | 1494 | 39577 | 10.8 |
| csv over tracks | 0.6 | 1.1 | 2.3 | 4.8 | 3.0 | 99 | 0.0 |

The saved walk itself took 17 s. tracks-filter or resolve on its chain would add some quarter of an hour
to it at this cadence, and some ten hours to an hour's walk, against some ten seconds run once at its
end. The tracks-filter runs are not a line, the last doubling costing over three times, so the hour's
figure is an order and no more. smooth is seconds to half an hour by its kernel and reach. csv whole is
under two minutes over an hour, so its step is worth little in time; stepped over tables it would be
charged the tables a third time by the count above.

Not measured: a document with more animals a row, where the tables are larger and the cap nearer; the
window walk, which holds by the same rule over a range a user sets; and the process's own memory against
what `_Walk.bytes` says.
