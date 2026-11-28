# What each act costs against each size that can grow

2026-11-27, on v5-playground-one-store at `d774580c` with `docs/playground/sim/audit.py` as the
commit that files this has it, run as `python -X utf8 docs/playground/sim/audit.py` with
`MINIATURE_CUTTER` unset and `nested`. The plan of it is `docs/playground/JOURNAL.md`, "The audit
of what each act costs". The method is Goldsmith, Aiken and Wilkerson's empirical complexity: one
size varied with the others at the base, the steps counted, the exponent the slope of log steps
on log size. Steps are lines run in `sieve_player` and `tools`, counted by the miniature; they
are not time, and a thing flat and dear is not in them.

## How to read the tables

"At once" is the act itself, which is the window's thread; "until settled" is the worker's turns
after it and what they land in. "To be" is `EXPECTED` in the script: what the act may grow with.
A bold exponent passes it by more than a quarter with more than 2000 steps at the largest size.
The window is in cuts, three at size 1, so its rows grow with the rows of a cut. Counts move by a
few steps between runs of the same tree (32843 and 32851 of one cell); no exponent moved in the
second place.

`EXPECTED` was corrected once after the first measure and before this one: a window in cuts grows
with the rows of a cut, and an edit or a let go walks the window again. Both were errors of the
table and not of the player. It is his to correct further.

## What it found

Every cell over is by cuts, and all but two are the window's thread reading every cut held to
answer of the few the window shows:

- the marks of other code, 0.96 and 0.97: `held.marked`.
- a window moved or lengthened with cuts held, 0.46 to 0.63: `cut.served`, `timeline.lanes`,
  `cut.cut_in_time`, `window._restate`. `timeline.lanes` draws every cut and may be what it is
  to cost; the others answer of the window.
- a param edited below the cuts, at once, 0.62 and 0.74: `cut.served`, `timeline.lanes`, the
  plan made whole, `held._serving`.
- the gate's band edited, at once, 0.38 and 0.39: `held._serving`, `held._serves`, `held._has`.
- a reopen until settled, 0.28 and 0.39: `held.marked`, `cut.reading`, `cut.read`.

The two others: under `nested` a clip walk until settled is 1.48 by cuts where `period`'s is
1.06, in `document.node` and the plan, which is the plan made whole at each of the inner gate's
runs held; and the first window walked after opening reads the decoder's packet times,
`decoder._packet_times`, once a clip and by its rows, which lands on whichever act is first.

By the rows of a cut, the window and the chain no cell is over. A scrub by the window is 0.52
and 0.64 at under 250 steps, beneath the floor.

## What it did not measure

A wire made or broken, a param edited above the cut, play, the cards open, the budget of held
runs, more than two depths of cut, `pad` and the other cutters of `sim/cutters`, and time: a
profile of the same acts on real footage is not made. A reopened player is left open beside the
first for the acts after it. The run before the one filed hung at about 67 s of processor time
under `period` with nothing printed and was stopped unread; the script now ends a run that hangs
with each thread's stack.

## Cut by `period`

cut by period; base {'cuts': 100, 'rows a cut': 4, 'window': 1, 'chain': 0}

| act | size | at once: steps smallest to largest | exponent | to be | until settled: steps | exponent | to be |
|---|---|---|---|---|---|---|---|
| window moved, none held | cuts | 7746 to 273 | -1.45 | 0 | 19222 to 57053 | **0.48** | 0 |
| clip walk | cuts | 12 to 12 | 0.00 | 0 | 552475 to 4975456 | 1.06 | 1 |
| scrub | cuts | 77 to 77 | 0.00 | 0 | 192 to 192 | 0.00 | 0 |
| window moved, cuts held | cuts | 3185 to 10535 | **0.58** | 0 | 9101 to 9463 | 0.02 | 0 |
| window lengthened, cuts held | cuts | 4509 to 11859 | **0.46** | 0 | 17714 to 17740 | 0.00 | 0 |
| marks of other code | cuts | 4493 to 32843 | **0.96** | 0 | 192 to 204 | 0.03 | 0 |
| save | cuts | 2805 to 18555 | 0.91 | 1 | 198 to 198 | 0.02 | 0 |
| reopen | cuts | 78057 to 131301 | 0.25 | 1 | 124575 to 225071 | **0.28** | 0 |
| param edited below the cuts | cuts | 14131 to 50881 | **0.62** | 0 | 236494 to 1874115 | 0.99 | 1 |
| gate's band edited | cuts | 8324 to 18824 | **0.39** | 0 | 40633 to 94602 | 0.41 | 1 |
| let go | cuts | 7221 to 7575 | 0.02 | 0 | 19562 to 19190 | -0.01 | 1 |
| window moved, none held | rows a cut | 273 to 273 | 0.00 | 1 | 40992 to 167778 | 1.02 | 1 |
| clip walk | rows a cut | 12 to 12 | 0.00 | 0 | 1177986 to 4030282 | 0.89 | 1 |
| scrub | rows a cut | 77 to 77 | 0.00 | 0 | 198 to 192 | -0.02 | 0 |
| window moved, cuts held | rows a cut | 4235 to 4235 | 0.00 | 1 | 9163 to 34930 | 0.97 | 1 |
| window lengthened, cuts held | rows a cut | 5559 to 5559 | 0.00 | 1 | 17726 to 69121 | 0.98 | 1 |
| marks of other code | rows a cut | 8543 to 8543 | 0.00 | 0 | 210 to 198 | -0.04 | 0 |
| save | rows a cut | 5055 to 5055 | 0.00 | 1 | 192 to 216 | 0.08 | 0 |
| reopen | rows a cut | 85699 to 53997 | -0.33 | 1 | 138985 to 137795 | -0.01 | 1 |
| param edited below the cuts | rows a cut | 19381 to 19507 | 0.00 | 1 | 476172 to 975258 | 0.52 | 1 |
| gate's band edited | rows a cut | 9824 to 9828 | 0.00 | 1 | 48370 to 141419 | 0.77 | 1 |
| let go | rows a cut | 7271 to 7273 | 0.00 | 0 | 19154 to 66691 | 0.90 | 1 |
| window moved, none held | window | 273 to 273 | 0.00 | 1 | 41034 to 167148 | 1.01 | 1 |
| clip walk | window | 12 to 12 | 0.00 | 0 | 1178112 to 1568175 | 0.21 | 0 |
| scrub | window | 77 to 158 | 0.52 | 0 | 198 to 194 | -0.01 | 0 |
| window moved, cuts held | window | 4235 to 8573 | 0.51 | 1 | 9163 to 35197 | 0.97 | 1 |
| window lengthened, cuts held | window | 5559 to 14073 | 0.67 | 1 | 17738 to 69701 | 0.99 | 1 |
| marks of other code | window | 8543 to 8543 | 0.00 | 0 | 204 to 198 | -0.02 | 0 |
| save | window | 5065 to 5055 | -0.00 | 0 | 198 to 222 | 0.08 | 0 |
| reopen | window | 85701 to 85713 | 0.00 | 0 | 139051 to 139083 | 0.00 | 1 |
| param edited below the cuts | window | 19381 to 25276 | 0.19 | 1 | 476202 to 782790 | 0.36 | 1 |
| gate's band edited | window | 9824 to 10310 | 0.03 | 1 | 48398 to 159572 | 0.86 | 1 |
| let go | window | 7271 to 8866 | 0.14 | 0 | 19194 to 75287 | 0.99 | 1 |
| window moved, none held | chain | 273 to 297 | 0.04 | 1 | 41058 to 58481 | 0.18 | 1 |
| clip walk | chain | 12 to 12 | 0.00 | 0 | 1178214 to 1792240 | 0.21 | 1 |
| scrub | chain | 77 to 131 | 0.27 | 1 | 192 to 192 | 0.00 | 1 |
| window moved, cuts held | chain | 4235 to 11921 | 0.53 | 1 | 9175 to 9639 | 0.02 | 1 |
| window lengthened, cuts held | chain | 5559 to 16883 | 0.57 | 1 | 17756 to 18690 | 0.03 | 1 |
| marks of other code | chain | 8543 to 48199 | 0.88 | 1 | 198 to 276 | 0.17 | 0 |
| save | chain | 5055 to 13011 | 0.48 | 1 | 204 to 216 | 0.03 | 0 |
| reopen | chain | 85721 to 263223 | 0.57 | 1 | 139103 to 240041 | 0.28 | 1 |
| param edited below the cuts | chain | 19381 to 40276 | 0.37 | 1 | 476284 to 925066 | 0.34 | 1 |
| gate's band edited | chain | 9824 to 24992 | 0.47 | 1 | 48438 to 106277 | 0.40 | 1 |
| let go | chain | 7271 to 20158 | 0.52 | 1 | 19190 to 23310 | 0.10 | 1 |

7 cells over what is expected by more than 0.25, the furthest first:
 - marks of other code, at once, by cuts: 0.96 where 0 is expected, 4493 to 32843 steps; held.py:marked +25900, held.py:_has +1400, held.py:good +1050, window.py:_walked_nodes +0, window.py:_show_stale +0
 - param edited below the cuts, at once, by cuts: 0.62 where 0 is expected, 14131 to 50881 steps; cut.py:served +7000, timeline.py:lanes +3500, plan.py:<genexpr> +2800, held.py:_serving +2100, generated:__init__ +2100
 - window moved, cuts held, at once, by cuts: 0.58 where 0 is expected, 3185 to 10535 steps; cut.py:served +3500, timeline.py:lanes +1750, graph.py:<genexpr> +700, cut.py:cut_in_time +700, window.py:_restate +350
 - window moved, none held, until settled, by cuts: 0.48 where 0 is expected, 19222 to 57053 steps; decoder.py:_packet_times +16012, generated:__init__ +1737, document.py:node +1647, graph.py:_compute +1128, walk.py:step +1056
 - window lengthened, cuts held, at once, by cuts: 0.46 where 0 is expected, 4509 to 11859 steps; cut.py:served +3500, timeline.py:lanes +1750, graph.py:<genexpr> +700, cut.py:cut_in_time +700, window.py:_restate +350
 - gate's band edited, at once, by cuts: 0.39 where 0 is expected, 8324 to 18824 steps; held.py:_serving +4200, held.py:_serves +1400, held.py:_has +1400, held.py:<genexpr> +1400, held.py:good +700
 - reopen, until settled, by cuts: 0.28 where 0 is expected, 124575 to 225071 steps; held.py:marked +25900, cut.py:reading +22400, cut.py:read +18200, held.py:_serving +8050, held.py:rows_of +4900

## Cut by `nested`

cut by nested; base {'cuts': 100, 'rows a cut': 4, 'window': 1, 'chain': 0}

| act | size | at once: steps smallest to largest | exponent | to be | until settled: steps | exponent | to be |
|---|---|---|---|---|---|---|---|
| window moved, none held | cuts | 12443 to 295 | -1.62 | 0 | 50623 to 93159 | **0.27** | 0 |
| clip walk | cuts | 12 to 12 | 0.00 | 0 | 2021455 to 43449762 | **1.48** | 1 |
| scrub | cuts | 95 to 95 | 0.00 | 0 | 192 to 192 | 0.00 | 0 |
| window moved, cuts held | cuts | 5379 to 20087 | **0.63** | 0 | 9358 to 9716 | 0.02 | 0 |
| window lengthened, cuts held | cuts | 7674 to 22374 | **0.51** | 0 | 18214 to 18226 | 0.00 | 0 |
| marks of other code | cuts | 7599 to 56949 | **0.97** | 0 | 192 to 216 | 0.05 | 0 |
| save | cuts | 4453 to 31423 | 0.94 | 1 | 198 to 234 | 0.09 | 0 |
| reopen | cuts | 135256 to 278440 | 0.35 | 1 | 138557 to 309763 | **0.39** | 0 |
| param edited below the cuts | cuts | 31886 to 147736 | **0.74** | 0 | 329857 to 2561282 | 0.99 | 1 |
| gate's band edited | cuts | 13236 to 28994 | **0.38** | 0 | 60127 to 143484 | 0.42 | 1 |
| let go | cuts | 13307 to 14009 | 0.02 | 0 | 50578 to 50624 | 0.00 | 1 |
| window moved, none held | rows a cut | 295 to 295 | 0.00 | 1 | 77140 to 262506 | 0.88 | 1 |
| clip walk | rows a cut | 12 to 12 | 0.00 | 0 | 5000973 to 8793010 | 0.41 | 1 |
| scrub | rows a cut | 95 to 95 | 0.00 | 0 | 192 to 198 | 0.02 | 0 |
| window moved, cuts held | rows a cut | 7479 to 7479 | 0.00 | 1 | 9414 to 35597 | 0.96 | 1 |
| window lengthened, cuts held | rows a cut | 9774 to 9776 | 0.00 | 1 | 18232 to 70551 | 0.98 | 1 |
| marks of other code | rows a cut | 14649 to 14649 | 0.00 | 0 | 204 to 198 | -0.02 | 0 |
| save | rows a cut | 8303 to 8303 | 0.00 | 1 | 204 to 216 | 0.04 | 0 |
| reopen | rows a cut | 155760 to 101870 | -0.31 | 1 | 163055 to 160685 | -0.01 | 1 |
| param edited below the cuts | rows a cut | 48436 to 48544 | 0.00 | 1 | 648773 to 1156886 | 0.42 | 1 |
| gate's band edited | rows a cut | 15486 to 15488 | 0.00 | 1 | 72086 to 205120 | 0.75 | 1 |
| let go | rows a cut | 13407 to 13407 | 0.00 | 0 | 50627 to 142897 | 0.75 | 1 |
| window moved, none held | window | 295 to 295 | 0.00 | 1 | 77186 to 286135 | 0.95 | 1 |
| clip walk | window | 12 to 12 | 0.00 | 0 | 5001356 to 7034170 | 0.25 | 0 |
| scrub | window | 95 to 230 | 0.64 | 0 | 192 to 192 | 0.00 | 0 |
| window moved, cuts held | window | 7479 to 14852 | 0.49 | 1 | 9414 to 36177 | 0.97 | 1 |
| window lengthened, cuts held | window | 9774 to 24246 | 0.66 | 1 | 18232 to 71673 | 0.99 | 1 |
| marks of other code | window | 14649 to 14649 | 0.00 | 0 | 204 to 204 | 0.00 | 0 |
| save | window | 8343 to 8313 | -0.00 | 0 | 234 to 234 | 0.00 | 0 |
| reopen | window | 155772 to 155742 | -0.00 | 0 | 163121 to 163155 | 0.00 | 1 |
| param edited below the cuts | window | 48436 to 61135 | 0.17 | 1 | 648857 to 1241276 | 0.47 | 1 |
| gate's band edited | window | 15486 to 16231 | 0.03 | 1 | 72130 to 241649 | 0.87 | 1 |
| let go | window | 13417 to 17205 | 0.18 | 0 | 50674 to 173790 | 0.89 | 1 |
| window moved, none held | chain | 295 to 319 | 0.04 | 1 | 77232 to 116120 | 0.21 | 1 |
| clip walk | chain | 12 to 12 | 0.00 | 0 | 5001803 to 7534557 | 0.21 | 1 |
| scrub | chain | 95 to 149 | 0.23 | 1 | 192 to 206 | 0.03 | 1 |
| window moved, cuts held | chain | 7479 to 17181 | 0.42 | 1 | 9438 to 9912 | 0.02 | 1 |
| window lengthened, cuts held | chain | 9774 to 23322 | 0.44 | 1 | 18238 to 19176 | 0.03 | 1 |
| marks of other code | chain | 14649 to 59685 | 0.71 | 1 | 222 to 270 | 0.10 | 0 |
| save | chain | 8303 to 16259 | 0.34 | 1 | 222 to 240 | 0.05 | 0 |
| reopen | chain | 155772 to 353119 | 0.42 | 1 | 163137 to 273113 | 0.26 | 1 |
| param edited below the cuts | chain | 48444 to 75762 | 0.23 | 1 | 648976 to 1128669 | 0.28 | 1 |
| gate's band edited | chain | 15486 to 33974 | 0.40 | 1 | 72178 to 138270 | 0.33 | 1 |
| let go | chain | 13415 to 32283 | 0.44 | 1 | 50720 to 70722 | 0.17 | 1 |

8 cells over what is expected by more than 0.25, the furthest first:
 - marks of other code, at once, by cuts: 0.97 where 0 is expected, 7599 to 56949 steps; held.py:marked +43050, held.py:_has +3500, held.py:good +2800, window.py:_walked_nodes +0, window.py:_show_stale +0
 - param edited below the cuts, at once, by cuts: 0.74 where 0 is expected, 31886 to 147736 steps; cut.py:served +18200, plan.py:<genexpr> +10850, __init__.py:params +9450, document.py:node +6300, generated:__eq__ +5250
 - window moved, cuts held, at once, by cuts: 0.63 where 0 is expected, 5379 to 20087 steps; cut.py:served +9100, timeline.py:lanes +1750, graph.py:<genexpr> +1400, cut.py:cut_in_time +1400, window.py:_restate +700
 - window lengthened, cuts held, at once, by cuts: 0.51 where 0 is expected, 7674 to 22374 steps; cut.py:served +9100, timeline.py:lanes +1750, graph.py:<genexpr> +1400, cut.py:cut_in_time +1400, window.py:_restate +700
 - clip walk, until settled, by cuts: 1.48 where 1 is expected, 2021455 to 43449762 steps; document.py:node +4049850, plan.py:<genexpr> +3387836, cut.py:reading +1955800, held.py:_serving +1548750, generated:__init__ +1537745
 - reopen, until settled, by cuts: 0.39 where 0 is expected, 138557 to 309763 steps; held.py:marked +43050, cut.py:reading +33600, cut.py:read +26600, held.py:_serving +18900, held.py:_serves +7700
 - gate's band edited, at once, by cuts: 0.38 where 0 is expected, 13236 to 28994 steps; held.py:_serving +6300, held.py:_serves +2100, held.py:_has +2100, held.py:<genexpr> +2100, held.py:good +1050
 - window moved, none held, until settled, by cuts: 0.27 where 0 is expected, 50623 to 93159 steps; decoder.py:_packet_times +16012, document.py:node +3483, generated:__init__ +1779, graph.py:_compute +1128, walk.py:step +1056

## The cells after three of them were taken away

Run again with `7071e32c`, `102533a8` and the commit that holds this section, which are the
restating of cuts at a window's walk, the marks of other code, and what is held of a node asked
of every run. The tables above are the tree before them. By cuts, under `period` and `nested`:
a window moved with cuts held 0.00 and 0.00, lengthened 0.00 and 0.00, the marks of other code
0.00 and 0.00, the gate's band edited at once 0.09 and under the floor of a quarter in both, a
reopen until settled 0.24 and 0.33.

What is still over: a param edited below the cuts, at once, 0.51 and 0.68, and under `nested` a
clip walk until settled 1.47, both the plan made whole (`plan.<genexpr>`, `plan._within`,
`document.node`, and `timeline.lanes` laid again of cuts the plan made again); the first walk's
`decoder._packet_times`, 0.48 and 0.27; under `nested` a reopen until settled, 0.33, one pass
over every cut held; and under `nested` a clip walk by the window, 0.25, at the line. No cell
by the rows of a cut or the chain is over, and none that was under is over now.

The first form of the third fix took every run with a result of a node where the runs near
the rows were fewer, and the audit said so before it was committed: a window moved with cuts
held went to 0.70 and a param edited until settled to 1.65.

## The cells after the plan keeps the cuts it made

Run again with the commit that holds this section over `218bb4a4`: the graph keeps what each
cutting node last made and `plan` hands back the same tuple of cuts where it is asked the same
of the same cuts and results. A param edited below the cuts, at once, by cuts: 0.14 under
`period`, where it was 0.51, and 0.45 under `nested`, where it was 0.68. Under `period` one
cell is over, the first walk's `decoder._packet_times`, 0.48. Under `nested` five are: that
param edited, in `plan.<genexpr>`, `document.node` and `window._cut_result`, the plan asking
`cut_result` of every outer cut at each sync; a clip walk until settled by cuts, 1.40, of the
same; a reopen until settled, 0.33; a clip walk by the window, 0.27; and the decoder's, 0.27.

## The cells after a run held syncs only where a cut could move

Run again with the commit that holds this section. A node cut by a result on a wire is cut by
the held results where every cut it reads has one and else by what the window walked alone, so
a run held of one outer cut moves no cut until the last, and the window syncs then and not
before. Under `nested`, a clip walk until settled by cuts: 1.01 where it was 1.40, 7972255 steps
at 400 cuts where it took 34387578, and the miniature holds O7 under `nested`, which it failed.
Still over under `nested`: a param edited at once by cuts, 0.48, the plan asking `cut_result` of
every outer cut and the window now asked what it walked of each; a reopen until settled, 0.33; a
clip walk by the window, 0.32; the decoder's packet times, 0.27. Under `period` the one cell
over is the decoder's, 0.48.

## What the cell still over under nested is in milliseconds

`sim/adversary.py T` under `nested`, the tree of the section above: one param edited below the
cuts, on the window's own thread with no worker turn taken, the least of five, 8.2 ms with 100
cuts held, 25.3 with 400 and 64.1 with 1600. Under the profile at 1600, `plan` is 87 ms of 122
and `window._cut_result` 73 of them over 1601 calls, `held._near` 43. The audit's exponent says
the cost grows with the cuts and this says by how much: sixteen times the cuts, eight times the
milliseconds. Answering it of fewer asks would take a held answer kept from one sync to the
next and let go wherever a run or the window's walk moves, which is not built.
