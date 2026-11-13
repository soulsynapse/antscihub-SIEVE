# The monitor's poll took a fifth of the GUI thread's wall with a full history, and a twentieth once a walk its lane has left is judged once

2026-11-12, on v5-monitor over c0ec2e20 with the working tree of `docs/spec/stream-seams.md`'s deliverables
through The catalogue's parts, by `docs/findings/experiments/2026-11-12-what-the-poll-costs.py 128 300`. It is
the observation of the Fork under The poll judges a walk once, and the same run again after what the Fork
then has built.

The monitor's window was opened offscreen on one Graph and Ledger of `video-tests/purb-settings.json`, 14
nodes, its bake live, and the Worker walked 128 windows of 300 rows, each begun 150 rows past the last, so
every walk is half cold and the history fills at the sixty-fourth. The poll is the window's own, every
250 ms, and is in the stream as a "slot" named "monitor": the ledger's view taken, the log's read of it, and
the panels' values made. Its painting is a "paint" and is not in these figures. One run each; the walks
took about half a second apiece, so a row of the table is some four to six seconds.

## Before: every finished walk judged at every poll

| walks | in the history | a poll, mean ms | longest ms | share of the wall |
|---|---|---|---|---|
| 1 to 8 | 8 | 9.01 | 13.99 | 3.78% |
| 9 to 16 | 16 | 12.18 | 16.08 | 4.81% |
| 17 to 24 | 24 | 14.18 | 18.84 | 5.57% |
| 25 to 32 | 32 | 17.13 | 21.67 | 6.92% |
| 33 to 40 | 40 | 21.31 | 27.10 | 8.46% |
| 41 to 48 | 48 | 26.01 | 31.66 | 10.46% |
| 49 to 56 | 56 | 36.96 | 55.78 | 14.98% |
| 57 to 64 | 64 | 46.39 | 54.35 | 18.26% |
| 65 to 128, eight rows | 64 | 44.32 to 53.33 | 52.02 to 65.96 | 17.70% to 21.38% |

The poll's cost grows faster than the walks held, as `thrash` reading `needs` for each walk and `needs`
reading every walk would have it, and stops growing where the history is full. From the forty-first walk
its share is over `catalogue.WAITS`, the share at which `waits` names a span of the GUI thread's, and the log
at the end held `waits` of "slot monitor": the monitor named itself.

## After: a walk its lane has begun another after is judged once

`Log.read` hands each detector the finished walks it has not judged for the last time, and a walk that is no
longer its lane's last is judged in the first read that finds it so and not again.

| walks | in the history | a poll, mean ms | longest ms | share of the wall |
|---|---|---|---|---|
| 1 to 8 | 8 | 8.29 | 10.53 | 3.38% |
| 9 to 16 | 16 | 10.96 | 21.65 | 4.57% |
| 17 to 64, six rows | 24 to 64 | 9.51 to 11.68 | 14.30 to 23.56 | 3.87% to 4.77% |
| 65 to 128, eight rows | 64 | 11.36 to 12.38 | 15.78 to 23.42 | 4.36% to 5.00% |

The share is under `WAITS` at every length of the history and no longer follows it past the first sixteen
walks. What is left of a poll still rises a little with the walks held, three or four ms from eight walks to
sixty-four: the panels' values, `store_name`, `rows` and `_pixels`, read every walk, and the view is taken.

## Each again, three times

The tables above are one run each. Later the same day both were run three times more, a run of one and a
run of the other in turn, each in its own process: the tree as it is, and the tree with `Log._settled`
emptied before every read, which judges every finished walk at every poll as before. Over the walks with
the history full, 65 to 128, eight rows a run:

| | run | a poll, mean ms | longest ms | share of the wall |
|---|---|---|---|---|
| every walk at every poll | 1 | 49.49 to 57.88 | 57.99 to 70.01 | 19.54% to 23.19% |
| every walk at every poll | 2 | 34.18 to 51.65 | 36.72 to 59.91 | 13.63% to 21.04% |
| every walk at every poll | 3 | 40.04 to 45.31 | 47.40 to 59.80 | 15.96% to 17.91% |
| judged once | 1 | 13.88 to 15.95 | 18.76 to 29.27 | 5.63% to 6.43% |
| judged once | 2 | 14.66 to 16.89 | 20.18 to 26.30 | 5.97% to 6.87% |
| judged once | 3 | 10.87 to 12.61 | 15.06 to 21.72 | 4.33% to 5.13% |

With the first run of each, four runs a side: every walk judged at every poll is 13.6% to 23.2% of the
wall with the history full and over `WAITS` in every row; judged once it is 4.3% to 6.9% and under `WAITS`
in every row of every run, at every length of the history. A twentieth is the low end of it. In the second
run of the first side the poll fell from some 50 ms to some 35 for five rows and came back, the walks of
those rows being the faster too, which was not looked into.

## What it does not show

The runs were offscreen, so nothing is said of the paints. The logs of the runs judged once held `waits`
of "slot monitor" and of "paint monitor": in this harness the monitor's are the only spans the GUI thread
has, so any wait of a tool's that falls beside a span of that thread falls beside one of them, whatever
their share. `grows` of blobs was in the log of three of the four runs that judged every walk at every poll
and of none of the four that judged once, and one of the first held four `unread` besides. Two logs, one
of each sort, handed the same hand-built history a walk at a time, turning over, hold the same entries at
every read, so the difference is not in the judging; that it is the longer poll changing what a walk costs
is a guess and was not tested.
