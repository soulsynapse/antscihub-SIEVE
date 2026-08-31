# explorer-logs

Sessions `../explorer.py` wrote, scripted and hand-driven alike. Ground truth
for how the thing behaves; read the newest before trusting any recollection of
it.

**Nothing in a log says which build wrote it**, so check the fields the fixes
added rather than the timestamp. Same discipline as
`../../orchestrator-experiments/explorer-logs/README.md`, and the same reason:
a log is an artifact of a build, and the build moves.

| fix | fingerprint |
|---|---|
| the walk paces on arrival, so leg 1 records anything at all | `legs["leg1 hunt"].by_task` is non-empty |
| a landing drops unreferenced frames, so leg 5 is the cold refill its name says | `topology.drops_unreferenced_at_landing` present |
| roles stripped of the per-activation `#seq`, so bars are per role | `duration_bars` keys are `dispatch:fill` / `dispatch:gui`, never `dispatch:gui#42` |
| two tiers, so what is looked at is held at display sampling (ADR-0017) | `topology.display_divisor` present; above 1 the fill's rows are a different key from the step's |
| the step's progress recorded, so a stalled pass is visible | `step` present, with `computed` against `wanted` |

Both of the first two landed in one commit, so one fingerprint covers them.
A log missing either is not wrong about everything — its `dispatch_trace`,
its decode counts and its pool numbers are all real — but **its leg walls are
not comparable to a later log's**, because leg 1 measured an empty set and
leg 5 measured a window nothing had evicted.

## What differs from V1's logs, on purpose

`graph_holds` **is accurate here.** The derived-eviction finding documents it
reading 1 in a V1 log because `closeEvent` released the sweep before the log
was saved; this explorer saves while the window is live and releases nothing
from the graph on close. A reader comparing that field across the two folders
is comparing a measurement against an artefact — use `pool.frames` and the
per-leg `window covered` walls for both, which is what that finding already
tells a V1 reader to do.

`topology` carries what V1's did not and what this folder's results have to
name: `readers`, `recorders`, `request_depth`, `replacement`, and
`drops_unreferenced_at_landing`. A wall from one reader and a wall from two
are different facts (`docs/findings/2026.08.30-a-second-cursor-that-overlaps-
costs-a-scrub-nothing`), and so is a wall that kept its victims.

**A log with `display_divisor` above 1 is not comparable to one without it**,
and neither its walls nor its decode counts are. Two tiers change what a decode
produces and what a window weighs: `pool_held_gb` is the number ADR-0017 moves
and `pool.gb` is not, because that one also counts released rows nothing has
swept. `request_depth` moved with the same change and is load-bearing under
two tiers where it was not under one, so a comparison names both.

`--quick` and `--window-seconds` below 20 both produce logs whose scheduling
behaviour is real and whose walls and memory numbers are not; `topology.quick`
and `topology.window_is_full_size` say which, and a short run must not be read
as a full one.

Which logs each published finding used is stated in that finding's `where:`
field, in `docs/findings/`.
