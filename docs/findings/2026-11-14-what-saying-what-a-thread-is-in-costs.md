# Keeping each thread's open spans where a sampler reads them is not told apart from the probe before it, on a machine in use

2026-11-14, on v5-cleaning-up-monitor over ce86e5a3 with the working tree's `Emitter.still_out`, by
`docs/findings/experiments/2026-11-14-what-saying-what-a-thread-is-in-costs.py`. The walk is the Worker's
window walk of `video-tests/purb-settings.json`, 600 rows from row 0, its bake live, cold on a fresh Graph
and Decoder each time, a Ledger with its Log and the machine's sampler attached as the player attaches
them. It is the observation of the fork of `docs/spec/monitor.md`'s A walk is judged while it is under
way, whether saying what a thread is in costs the walk. Kendrick was using the machine throughout and said
it chugged under these runs; the walks sit well above those of
`docs/findings/2026-11-12-what-the-trace-costs.md`, on the same document and rows.

What is in question adds no event. A span of `Emitter.probe` leaves its node, its start and its starting
CPU clock in the list the probe already kept of the spans open on its thread, and the list is reachable
by the thread's name; the machine's sampler reads it once a second, with the thread's CPU by
`machine.thread_cpu`, into a "still_out" sample. `before` is `Emitter.probe` and `Emitter.turn` read out
of ce86e5a3 and put on the tree's Emitter, the sampler sampling the machine alone; `after` is the tree's.

## What was measured

Every walk, ms, in the order run: the two walked in turn, walk by walk, ten times round, three processes.

| | round 1 | round 2 | round 3 |
|---|---|---|---|
| before | 1925 1726 2379 3114 2118 1808 2267 1807 1633 1544 | 1571 1459 1436 1967 1588 1643 1610 1564 2000 1791 | 1585 2234 2080 2442 2070 2033 2152 2052 2233 2236 |
| after | 1750 1961 2375 2252 2162 2241 2315 2362 1530 1535 | 1475 1545 1438 1656 1693 1619 1626 1939 2104 1541 | 1555 2085 2110 2155 2113 2094 2026 2760 2135 2217 |

The thirty of each in order of size:

| | least | lower quartile | median | upper quartile | most |
|---|---|---|---|---|---|
| before | 1436 | 1610 | 1946 | 2152 | 3114 |
| after | 1438 | 1619 | 2056 | 2162 | 2760 |

Of the thirty pairs walked one after the other, `after` was the slower in fifteen. The sampler took 54
"still_out" samples over the `after` walks and found a thread in a span in 46.

## What it says

The two are not told apart: the least and both quartiles are within ten ms, the pairs split evenly, and
the medians' 110 ms is a seventh of the 700 ms the middle half of either spreads over. By the fork's
criterion the rate with it sits inside the spread of the rate without, so it is built as the box says.

## What it does not show

That it costs nothing. The spread is the machine's, in use, and a cost of a few percent would sit inside
it unseen; the criterion asks little, as the trace-cost finding says of its own. What a sample costs the
thread it reads was not timed apart: it is one list copied and one `GetThreadTimes` a second. A walk
longer than 600 rows, the player itself, and a machine left alone were not run.
