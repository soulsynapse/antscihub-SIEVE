# The player died walking 856 periods

2026-11-21, on v5-period at `aa3f7d12`. Kendrick opened
`video-tests/GoPro-stress-test-periods-in-period-analysis.json` and the player died. What it left
is `stderr.prev.log` under the app folder, read once before a later launch could replace it. The
measurement is `docs/findings/experiments/2026-11-21-what-a-period-lanes-telling-costs.py`.
Nothing of the player was changed.

## The document

The first of the stress documents with a series node below a `period`: `reduce_4`, unsmoothed and
banded, gates `period_4`, and `motion_2`, `reduce_5` and `smooth` sit below it. With the clip's
run held the plan has one timed walk of 856 cuts, most of one or two rows, and the clip lane walks
each alone.

## What the log says

Two `Timeout (0:00:05)!` dumps, `dev/qt_trace.py`'s watchdog saying the GUI thread had not turned
its event loop for five seconds, and then `Windows fatal exception: access violation`. The fatal
line begins in the middle of a line of the second dump, after `File "<string>"`, and the dump that
follows it names no `Current thread`: every thread is listed as `Thread`. The worker's stack in
all three is `cut.Record`'s generated `__eq__` under `worker.py:_walking`, under `_Legs._ask` and
`_Legs.emit`, under `walk.report`. The GUI thread's is `canvas.mouseMoveEvent` in the first and
`_period_ready`, `_hold_run`, `_recut`, `Graph.sync`, `region.cut_file` and `_cutfile.sidecar`'s
`json.load` at the fault.

## What killed it

The watchdog's dump. `faulthandler.dump_traceback_later` writes other threads' stacks from a
thread of its own that holds no interpreter lock, while those threads run. A fault with no current
Python thread, landing mid-line in that dump's own output, is that thread's. Shown apart from the
player's hang: an offscreen `PlayerWindow` on a copy of the document with
`dump_traceback_later(0.02, repeat=True)` armed died of the same access violation at its twelfth
dump, mid-line after `File `, while still importing; the same run without the watchdog walked
periods for 45 s and did not die. That was a script that opens a window and is not in the tree. So
the player was slow and alive, and its hang report killed it.

## Why the watchdog fired

Not reproduced: no run here stalled the GUI thread for five seconds, and whether the thread was
stuck or the timer that pushes the deadline ahead was starved under a flood of events is not
known. What was measured is the work each period costs both threads, which is what the two stacks
in the log are in.

The worker: `_Legs.emit` runs at every telling of a leg's progress and asks `_walking` of every leg
left in the queue; `_walking` looks for the leg's cut with `cut in w.cuts`, an equality against
each of the walk's cuts until one matches, each a dataclass `__eq__` over the record and the
records it was made from. One telling over 856 legs is 40 ms where the legs' records are the
plan's own objects and 115 ms after a sync has made the plan's records again, equal and not the
same, and 90 ms with half the legs left: it grows with the square of the periods and is paid a
period walked. It holds the interpreter while it runs.

The window: each period's results arrive at `_period_ready`, which holds the run, and
`_hold_run` then calls `_show_held` and `_recut`. Of the GUI thread's stack sampled every 4 ms
over the 45 s offscreen run, 19% was under `_recut`, a `Graph.sync` that asks `region` for its
served file again, reading the sidecar's JSON and stamping the file, and 18% under `_show_stale`,
printing the tools' files' code. In 44 s that run held 97 periods of the 856, about two a second.

## What is open

The watchdog no longer arms `dump_traceback_later`: `qt_trace.watchdog` dumps from a thread of its
own that holds the interpreter lock, so a slow player is reported and not killed. The slowness
stands: how a leg finds its walk without an equality against every cut, whether the count of legs
left is told at every telling, and what of a sync and of the stale marks a period's run held needs
made again.

## What was done, on v5-playground-one-store

The same evening `video-tests/GoPro-stress-test-periods.json`, 850 cuts under `motion`, `reduce`
and `smooth`, hung the player again: the watchdog's dump, which no longer kills, has the worker in
the same `_Legs.emit` and the GUI thread in the unsaved-changes box of a window being closed. The
measurement is `docs/findings/experiments/2026-11-21-the-gui-thread-while-the-clip-lane-walks-periods.py`,
the player offscreen over that document with its period runs let go, the event loop turned under
cProfile for 30 s, so every figure is the profiler's and larger than a plain run's.

Before any change but the lane's telling: all 850 periods held in the 30 s, and the longest single
turn of the event loop was 18.4 s. Each `_period_ready` cost the GUI thread 39 ms: `_recut` 15 ms,
a `Graph.sync` planning 850 cuts again; `_show_stale` reading nine tool files' stamps; the hold.
The worker walks the periods faster than that, so the results queue and the loop does not turn
until they are through. On the worker, `cut.computed_in` scanned a node's every cut at each
compute, 13.8 million `made_from` calls in the run.

After: the longest turn is 93 ms and a `_period_ready` 8 ms.

- `_Legs` finds a leg's walk in a dict made once a plan, and counts the legs left once for a plan,
  a queue and a `give_periods` that have not moved, where it asked every leg at every row told.
- `cut.computed_in` looks the reader's cut and the cuts it was made from up among the node's, and
  costs those, not the node's cuts.
- `_hold_run` makes the cuts again only where a run that went or came holds a result some cutting
  node is cut by. A period's run below its gate holds none.
- A run held alone marks the cards of other code within `STALE_MS`, once for the runs held meanwhile.

What still grows with the periods, a hold: `held.Runs.hold` asks `stands_in` of every run, twice;
`heldwalks.window_periods` asks `Runs.over`, a scan of every run, twice a period the window
overlaps; the lane's count is made again after each `give_periods`. Together about 6 ms a period
at 850 under the profiler. Not measured at several thousand.
