# Held runs of many periods, the periods a band makes, and what a `period` reaches into

2026-11-20, on v5-period at `f4109a6b`, for `docs/spec/a-cut-in-time.md`'s two "Not sized" and its
"Not measured". The measurement is
`docs/findings/experiments/2026-11-20-held-runs-of-many-periods.py`, one run of 5.8 s on a machine
not left alone, over `video-tests/purb-settings.json.series` as it lay: one run, the clip's, 38100
rows from row 0, 3315072 bytes as it was held, 87 a row, of `track`, `count`, `size`, `travel` and
`smooth`. No player and no window ran. The sizing is a reading of `plan.py`, `walk.py`,
`worker.py`, `held.py`, `graph.py` and `window.py` at that commit, and nothing was built.

## The periods a band makes

No band is set in the held file, so no period has been made by a real gate. Each signal was
thresholded at three of its own quantiles, which is this session's band and not Kendrick's; the
counts say what order of periods a band makes, and not what his would.

| signal | at or over its quantile | periods | rows kept | median rows | longest | of one row |
| --- | --- | --- | --- | --- | --- | --- |
| `count` | 0.50 | 29 | 32148 | 35 | 14465 | 8 |
| `count` | 0.75 and 0.90 | 82 | 11681 | 6 | 1876 | 20 |
| `travel` | 0.50 | 5779 | 19050 | 2 | 112 | 2289 |
| `travel` | 0.75 | 4495 | 9525 | 1 | 80 | 2806 |
| `travel` | 0.90 | 1951 | 3810 | 1 | 77 | 1424 |
| `smooth` | 0.50 | 542 | 19050 | 8 | 942 | 102 |
| `smooth` | 0.75 | 334 | 9525 | 12 | 307 | 72 |
| `smooth` | 0.90 | 145 | 3810 | 18 | 208 | 28 |

The clip is 10.6 minutes. A signal no node smoothed makes thousands of periods of it, most of one
or two rows; the smoothed one makes hundreds, a fifth of them of one row. The count of periods is
set by how the gate chatters at its threshold and not by how much of the clip it keeps. A period
of one row is a walk of its own in which `motion` hands out its zero and a stepped node its first
row and nothing after, so it holds no result worth its walk. The spec says nothing of a period too
short to keep or of two a gap of a row parts; a margin is in its Not here.

## `held.Runs` and `held.File` at a run a period

The clip's run cut into N runs of equal length, one a period; ms unless said.

| N | rows each | hold all N | hold one more | `over` | `part` | `spans` | `beside` | file: write all | add one | drop one | load | MB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 381 | 1 | 0.02 | 0.03 | 0.02 | 0.11 | 0.40 | 203 | 3.1 | 8.1 | 11 | 3.2 |
| 300 | 127 | 6 | 0.04 | 0.05 | 0.04 | 0.28 | 2.53 | 207 | 2.9 | 12.4 | 17 | 3.5 |
| 1000 | 38 | 58 | 0.11 | 0.14 | 0.11 | 1.02 | 27.31 | 240 | 21.0 | 35.6 | 40 | 4.3 |
| 3000 | 12 | 502 | 0.33 | 0.42 | 0.34 | 3.12 | 229.85 | 303 | 180.7 | 199.9 | 113 | 6.7 |

To hundreds of runs nothing here is a cost: every loop is under 3 ms and a write under 13. Past a
thousand three things grow with the square of the count: holding them all, `Runs.beside`, which the
window calls for the plot's rows outside the window (`window.py`, where `more[nid]` is set), and
`File.write`'s matching of the runs it has by identity, which makes adding one run 181 ms at 3000
where it is 3 ms at 300. The file grows by about a kilobyte a run over the rows' own bytes.

What the limit is of is rows and not runs. At 87 bytes a row `window.HELD_BYTES`, 512 MB, is some
six million rows of this chain; `docs/findings/2026-11-12-what-a-walk-holds.md` has a walk of the
same document at 2599 a row with the tables counted, which is some two hundred thousand. Either
way the periods of a clip cost less than the clip's one run does, being fewer rows.

Three rules of `Runs` as it stands, each seen at every N, that a run a period meets:

- With the limit at half of what the N take, half are left, the earliest beginning at row 19050:
  the oldest go, which are the first periods walked, and `over` then serves the first period from
  none. Nothing says a period's walk was let go; it is walked again when asked for.
- With the clip's run held, none of the N is held: `Runs.hold` takes no run another covers under
  the same keys.
- With the N held, holding the clip's run leaves one run: it drops every run it covers.

The last two are `docs/spec/a-cut-in-time.md`'s A value is of its cut as the tree now stands
against it: a period's own walk and the clip's rows over the same range are one thing to `Runs`,
and the clip's wins both ways.

`walk.STACK_BYTES` is of one walk and a period is a shorter walk than the clip, so a period
reaches it later than the clip does and no sooner.

## What a `period` fed a file reaches into

Nothing of the player. A tool that names a path input and its loader (`registry.paths`) has the
file a `file` selector picks loaded into its node's params by `window.py:PlayerWindow._pick_paths`,
again when the file changes on disk, the rows greyed as driven; `region` and its geometry file are
this. A tool's `key_params` says which of its params its key holds, so periods held in params and
left out of the key is what `region.py:key_params` does for a shape that is not the chosen one.

## What a `period` fed a gate reaches into

No wire carries a series node's result to a frame node. `plan.py`'s `wired` knows a tool's frame
inputs and, for a selector, its one input; `_pick_paths` is the one place a wire's source becomes
a node's params. `window.py:PlayerWindow._clip_result` reads a node's result over the clip from
`Runs.from_first_row`. A gate's periods laid on the `period`'s params where that run is held, as
`_pick_paths` lays a file's, would make both feeds one thing to everything below, periods in
params; the wire's edge is then the plan's for the cycle alone. `bare.py` has no window and would
be handed the params as its job has them. Not read: whether `document.py` holds a wire of that
kind today, and what the pane draws for one.

## What a node of a cut a period reaches into

Less of `plan.py` than the spec's Facts say. A node below a `period` has one key and is below one
cutting node whatever the count of periods, so `Entry` keeps one key and `Entry.piece` one id; the
periods are the cutting node's params. What holds a value by more than key and row is elsewhere:

| where | what is of one range or of no cut today |
| --- | --- |
| `graph.py`, 834 lines | the memo, read and written at four sites by (key, row), a static node by key alone; `frames(row)` and `frames.count` of the footage; `_footage`, the one reader of `Entry.piece` |
| `walk.py`, 431 | none in `_Walk`: `begin(start, length)` walks any range and the window's is one. `step` and `run_chain` hand a tool its place in the range and the range's rows, which is a period's own when the range is the period |
| `worker.py`, 236 | the clip lane: `give_clip(rows, given)` and `clip.begin(0, count)` are of one range from row 0, at two sites in `_turn` and one outside it |
| `held.py`, 356 | `Run` holds a start and no cut; `over`, `part`, `hold`, `spans`, `beside` and `from_first_row` each read `start` and `rows` alone. A record of a cut in `Run` is a new `VERSION`, and a file of the old one loads as none |
| `window.py`, 1577 | eleven calls of those six, in `_ask_window`, `_show_held`, the hold at a walk's end, `_clip_result` and the plot's rows beside the window |
| `bare.py`, 94 | one walk, `begin(0, g.count)` |
| `plan.py`, 268 | `pieces_of` and the refusal of a read across two cutting nodes, which stand; the cycle a gate's wire adds |

So the walk of one period is the walk the window already asks for, over the period's rows, with
the graph answering a read outside them as absent. What is new is the clip lane taking a range a
period in turn where it takes one, and a value's address in the memo and in `Runs`.

Not measured: a walk of many short ranges, each begun, against one walk of the same rows, which is
where a cost a period would show; the decoder's seek to each period's first row, which
`docs/findings/2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md` bears on; and
overlapping periods, whose rows are walked once each.
