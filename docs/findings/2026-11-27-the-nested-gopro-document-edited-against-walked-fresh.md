# The nested GoPro document, edited, against the same document walked fresh

`experiments/2026-11-27-the-nested-gopro-document-edited-against-walked-fresh.py` opens a copy of
`video-tests/GoPro clip single nested.json`, 11308 rows of `square-1.mp4`, a `period` cut by
`smooth` and a second `period` inside it cut by `smooth_in`, with no window shown and the
worker's turns taken on the script's thread. It walks the clip, sets `smooth_below`'s reach to 4,
sets `smooth_in`'s band to 12 and up, and compares what is held under the keys the nodes then
have with what a player opened on the document so edited holds after a clip walk alone.

| act | seconds | worker turns | cuts of `period`, of `inner` | results held, runs |
|---|---|---|---|---|
| clip walk | 11.9 | 26898 | 21, 458 | 961, 480 |
| param edited below the inner cuts | 1.6 | 7003 | 21, 458 | 961, 938 |
| the inner gate's band edited | 3.4 | 12519 | 21, 572 | 2101, 1529 |
| the edited document opened and clip walked | 13.1 | 23838 | 21, 572 | 1189, 594 |

Of the 1189 results the fresh player holds the edited one holds every one, and none differs. The
edited player holds 912 beside them: `reduce_below` and `smooth_below` over the cuts `inner`
made before its gate's band moved, rows 0 to 9 and 10 to 14 among them, under keys the nodes
still have, a cutting tool with no `run` being in no key below it. No cut is those rows now, so
they serve nothing; they are runs held, written with the document and counted against the limit
on the held runs. Before a clip walk both cutting nodes said their gate waits on its walk and
that they were cut provisionally over the window.

One run, one machine, no window on screen; the seconds are of that run and are not a measure.

## With the runs limited

Run again with a second pass: a player whose runs are limited to the bytes its clip walk held,
the two edits then made, once with `held.Runs.hold` told which runs serve nothing and once not.
Both keep all 1189 results of the edited document, in 1094 runs told and 1134 not. The runs of
the cuts that went are the oldest held, and the oldest went first before the rule; the rule
holds for any order what age held here. The first pass's figures were the same to the turn.

## What the checkpoint has of it

The edited document saved, its checkpoint holds 617 runs where the player holds 1529 and a
fresh player 594. Every result of the fresh player's is in it, no run in it is without a result
under a key a node has, and none is of a cut that is none. The 23 beside the fresh player's
hold the walked rows of a cut with a result under a key an edit left behind, the run made after
the edit holding the results and no walked rows.
