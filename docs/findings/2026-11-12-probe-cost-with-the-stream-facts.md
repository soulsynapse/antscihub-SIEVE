# The stream's new facts cost a cold fill nothing outside its own spread, and bench.py's dump line cannot say so

2026-11-12, on v5-monitor, the tree with the first deliverable of `docs/spec/monitor.md` built beside f96a9d77
without it, the earlier checked out as a second worktree and the two run in turn through
`docs/findings/experiments/2026-11-12-probe-cost-with-the-stream-facts.py`. The graph is `bench.py`'s, video →
gray → rescale → threshold → motion → reduce on `video-tests/rep3_intermittent_crop.MP4`, 462×456, a cold fill
of 600 rows by `walk_row` and `progress`. One consumer a process, four fills each on a fresh decoder and graph,
three rounds, before and after interleaved; the machine otherwise idle, Kendrick's player closed.

The facts in question: every event carries the reader, the demand and its node, and the lane; a progress event
carries the lane's memo hits and each store's counters; a sync carries the plan. With no consumer the walk pays
one context manager a row, the demand's, and nothing else.

## What was measured

Every fill, ms, in the order run. `list` is `[].append` as the consumer, what an emit costs with nothing done
with it; `both` is Stats and a dump, bench.py's third line.

| consumer | round | before | after |
|---|---|---|---|
| bare | 1 | 294 279 261 396 | 265 271 251 411 |
| bare | 2 | 242 236 252 403 | 271 259 264 365 |
| bare | 3 | 269 237 248 391 | 251 248 243 370 |
| list | 1 | 270 316 281 290 | 278 285 269 374 |
| list | 2 | 292 310 260 268 | 271 273 258 349 |
| list | 3 | 291 356 291 277 | 268 266 262 372 |
| dump | 1 | 281 269 357 269 | 275 336 297 294 |
| dump | 2 | 310 282 379 290 | 282 312 283 279 |
| dump | 3 | 281 267 374 290 | 291 286 306 398 |
| both | 1 | 278 274 364 274 | 303 323 295 302 |
| both | 2 | 281 278 351 282 | 314 297 303 391 |
| both | 3 | 275 323 263 268 | 279 310 274 283 |

`bench.py` itself, three runs of each tree interleaved: probe unset 0.23 to 0.28 s on both; dump attached 0.26,
0.27, 0.30 s before and 0.37, 0.37, 0.38 s after, the dump 720 KB before and 1109 KB after.

## What it says

Bare, with a list and with a dump alone, the two trees are not told apart: the fills of each overlap across
their whole range. With Stats and a dump the after fills sit 10 to 25 ms above the before ones, fill for fill,
which is inside the 40 ms the fills of one tree spread over and is in one direction in most pairs; it is not
shown to be a cost and not shown to be none.

One fill in about four takes some 100 ms more than its neighbours, in either tree and under every consumer,
the bare one included, so it is not the probe's. Which of the four it is moves with the consumer and the tree:
the fourth bare, the second or third with a consumer before, the fourth or second after. `bench.py` times its
dump line on one fill, the third of its process, and its 0.1 s is the size of the slow fill and four times
what any consumer shows here; that the third fill is the slow one after and not before is the reading, and
was not observed fill by fill inside bench.py. What the slow fill is was not taken apart; each fill allocates
and frees some 210 MB of memo, which is where to look.

The dump is half again as large, 390 KB over 600 rows, most of it the store counters on each progress event
and the five fields on each of the six events a row.

## What is not known

Whether the 10 to 25 ms under Stats and a dump is real, which wants more fills than twelve a side. What the
facts cost on Kendrick's footage in the player, which is What the trace costs' to measure with the ledger
attached. `bench.py`'s dump line is not a figure to hold a later one beside until it times more than one fill.
