# The ledger and the log hold a bounded 22 MB however long they are read, the sample queue grew without bound unread, and the monitor's poll is mostly the ledger's folding

2026-11-13, on v5-cleaning-up-monitor over 46060680, by
`docs/findings/experiments/2026-11-13-what-the-ledger-holds-over-hours.py` and
`docs/findings/experiments/2026-11-13-what-the-monitor-costs-with-a-full-history.py`. One run each
unless said.

## What is held over hours

A Ledger and a Log fed made events on a clock of their own, by tracemalloc: a lane walking windows
of 300 rows, three nodes a row, every walk under new keys, every result discarded as it is made, a
slot a row, lateness at 10 Hz and the machine at 1 Hz, a view taken and read by the log every 250 ms.

| hours | traced MB | buckets | walks | discards remembered |
|---|---|---|---|---|
| 0.17 | 9.7 | 2400 | 51 | 45885 |
| 0.34 | 14.9 | 2400 | 64 | 91791 |
| 0.51 | 17.1 | 2400 | 64 | 131072 |
| 0.68 | 22.1 | 2400 | 64 | 131072 |
| 0.84 | 22.1 | 2400 | 64 | 131072 |
| 1.10 | 22.1 | 2400 | 64 | 131072 |

It grows until the last of its limits is met, the discards remembered, and is flat from there. The
log's entries were none in this run, no store computing again, so `Log.entries`, which is never
pruned and holds one entry a class and subject ever seen, is not measured here.

With no reader and no event, the samples alone, as the player stands with a video open, nothing
walking and the monitor shut:

| hours | before: traced MB | queued | after: traced MB | queued |
|---|---|---|---|---|
| 0.25 | 1.0 | 9901 | 1.9 | 1707 |
| 0.50 | 1.9 | 19801 | 2.1 | 3413 |
| 0.75 | 2.8 | 29701 | 1.9 | 1022 |
| 1.00 | 3.7 | 39601 | 2.0 | 2728 |

Before, `Ledger.sample` queued and never folded, `event` alone folding past `BACKLOG`, so the queue
grew by some 3.7 MB an hour until an event came. After, whichever queues folds past `BACKLOG`.

## What the monitor costs with the history full

The monitor's window, offscreen at 1200 by 780, on `video-tests/purb-settings.json`, 14 nodes, over
window walks of 60 rows each begun 30 past the last; a poll's mean ms as the stream has it, six or
seven polls a row of the table.

| walks in the history | before | after, two runs |
|---|---|---|
| 16 | 7.26, 8.09 | 7.60, 7.45 |
| 32 | 9.24, 8.64 | 9.18, 8.18 |
| 48 | 12.16, 11.27 | 11.43, 10.58 |
| 64 | 12.58, 12.92 | 10.88, 11.16 |

After is `catalogue.thrash` taking `needs` only for a walk with a store past `THRASH`, `alike`
reading the walk's own rows once, and a Panel measuring its lines only when they change. A paint of
one of the window's widgets was 0.5 ms with 16 walks held and 1.1 to 1.6 with 64, some five a poll.

Under cProfile, the lane walking and the history full, a poll's cumulative time was about
four-fifths `Ledger.view`, nearly all of it `_fold` in `_span`, some thousand spans a poll: the
bookkeeping of the events queued since the last poll, done on the GUI thread inside the monitor's
slot and so named the monitor's. With the monitor shut the same folding is the emitting thread's,
past `BACKLOG`, under "monitor ledger".

## What it does not show

Nothing here is of a long session of the player itself: the process's memory was not measured, so
growth in the memo, the caches, Qt or the dump is not ruled out. The poll's figures are offscreen
and of a harness whose GUI thread does little else; the share the monitor's own panel shows in a
real session was not reproduced. The profiler's shares are inflated and are a split, not a cost.
Why a poll costs twice as much while a lane walks as standing still, beyond the folding, was not
separated: the interpreter changing hands at each Qt call is a guess.
