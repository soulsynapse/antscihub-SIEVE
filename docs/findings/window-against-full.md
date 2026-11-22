# A window's walk against the clip's, row by row, against the reach each tool declares

2026-11-21, on v5-playground-one-store at `be653b2c`, by `docs/findings/experiments/window_against_full.py`,
which runs in about a second and prints the same lines every run. The claim: a walk over rows a..b
gives, at every row whose reach summed along its chain (cut off at the clip's ends) lies inside a..b,
exactly what a walk over the whole clip gives there. Each tool sits on the shortest chain that feeds
it from 60 rows of synthetic footage (three squares drifting over seeded noise, a row's pixels a
function of its row alone), a required input past the first wired from the shortest chain to it, and
a frame tool closed by a series probe so its rows are stacked. Each walk
is `walk._Walk` on a Graph of its own, its turns taken on the script's thread; a chain below a cut in
time is walked leg by leg, the clip's over the cut whole and the window's over `walk.window_legs`.
Windows are [20,40) and [0,20). Rows compare by `tests/stepping.same`: exact for integers, tables
and object rows, NaN equal to NaN for floats, dtype for dtype; every per-row field of a result.

Every tool not listed below printed HOLDS with no differing row in either window: agreement, attach,
background, bg-subtract, blobs, box-bandpass, changeenergy, coarsegrain, combine, count, csv, decode,
detect, filter, flow, gray, hsv, inrange, mask, morphology, motion, period, reduce, region, rescale,
sample, size, spacing, speed, threshold, top-hat. The rest, as printed (summed reach in brackets,
+k from a window's first row, -k from its last):

| tool | declares | [20,40) | [0,20) | verdict |
| --- | --- | --- | --- | --- |
| smooth | (2, 2) | (2, 2): +0,+1,-1,-0 | (2, 2): -1,-0 | HOLDS |
| travel | (1, 0) | (None, 0): +0,+1 | none | HOLDS |
| transitions | (1, 0) | (None, 0): +0 | none | HOLDS |
| track | (None, 0) | (None, 0): +0..+9, -9, -4..-0 | none | HOLDS |
| kinematics | undeclared | (None, None): as track | none | HOLDS |
| tracks-filter | undeclared | (None, None): as track | none | HOLDS |
| resolve | undeclared | (None, None): +0..+9, -9..-0 | +0..+9, -9..-1 | HOLDS |
| file | undeclared | | | SKIPPED |

HOLDS 38, BREAKS 0, SKIPPED 1. No row differed past its summed reach, so there is no least case and
no read to point at. `smooth` differs at exactly the rows its (2, 2) reaches out of the window and at
none further in; touching the clip's start, its first rows match, as the cut-off says. Below a
`period` (gray, period over rows 10..50, reduce, smooth) the same smooth differs nowhere: the window's
leg reaches past the window by the chain's bounded reach (`sieve_player/walk.py:415`), where the
untimed window walk is begun over the window's rows alone (`sieve_player/worker.py:331`).

`file` is skipped: a selector hands out no rows. Four tools ran only with params the synthetic tables
or a window-less driver need: `transitions` on column `x` and `resolve` on `h` (their defaults, `nest`
and `tag_code`, are columns these tables lack); `region` given a plate and one box shape with its
clip not served; `period` fed a periods file through a `file` node, the file's params put into the
node as `PlayerWindow._pick_paths` (`sieve_player/window.py:923`) does, since the Graph loads no path.

What this could not determine. Every frame tool's HOLDS is structural: a frame row is computed from
the decoder at that row, not from the window, and a read past the declared reach raises
(`sieve_player/graph.py:273`), so these runs show only that no frame tool read past its declaration on
this footage, never that a declaration is tight or that one larger than needed is wrong. A side
declared or left unbounded allows every row, so `track`, `kinematics`, `tracks-filter` and `resolve`
in the middle window, and `resolve` touching the start, are not tested at all; whether their
differences are only renumbered ids or other values was not looked at. One parameter set a tool,
windows of 20 rows, one chain each, 60 rows; `period` was the only cut in time, and its chain had no
unbounded side, so the best-effort nodes of a leg cut short of its cut's edge were never walked.
