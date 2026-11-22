# Playground: one store

Branch `v5-playground-one-store`, cut from `v5`. Notes to resume from, not rules: where the tree
or the work shows a line here wrong, the line goes. Deleted before anything merges. State is
verified with `git log --oneline v5..HEAD`, never taken from this file.

## What Kendrick asked for

He develops tools and runs experiments to publish, and wants to stop thinking about the back end:
the decode cache, the memo, the series, the checkpoint, what periods and other tools keep. A
collaborator's weak computer runs it and a strong one too; above all no worry as tools are added.

1. Windows are reliable and fast.
2. A saved file opens where the user left off, as the user expects.
3. Walk bare and walk clip keep working as tools are added.
4. What is likely to be revisited does not cost the user much.

Results are held in several separate places, each with its own rule. His suspicion, and the
evening of the 850 periods is evidence for it: consolidating them is a simplification everything
benefits from. "One store" is a name for that and not the goal.

The branch is mine to build: forks are decided here with the reasoning said to him, specs are
historical referents and not rulings, and player-visible decisions are reported so he can
overrule them. His freeing me from a spec's decision endorses neither side of it.

## The oracles

O1 to O6 were written of a machine-wide store of results, which is gone; none is shown to hold.
O2, O3 and O6 have no subject left: there is no entry to drop, no checkpoint of the store's, no
second writer of one address. O1, O4 and O5 read on as claims about the memo and the checkpoint
that nothing checks.

- O1. What is handed out for an address equals a cold recompute of it, under any sequence of
  edit, scrub, walk, evict, crash mid-write and reopen.
- O2. Dropping any entry no checkpoint names changes speed and nothing else.
- O3. A checkpoint is served after a reopen, or the store says it is gone; never a wrong one.
- O4. Adding a tool changes no file of the store, the walk or the monitor.
- O5. Memory held stays under the budget given; a budget too small for one row's work is said.
- O6. Two processes writing the same address leave one whole entry.
- O7, from the 850 periods: what one more cut, run or node costs a turn of either thread does
  not grow with how many there are. The miniature asks it of a clip walk's steps a cut, and of a
  window moved, whose steps with 800 cuts held are not to pass 1.5 times those with 200. A window
  moved took 193630, 338240 and 980519 steps with 200, 800 and 3200 held while it asked
  `_show_held` of every cut and run, and takes 131920, 145120 and 261610 now. What still grows,
  about 22 steps a cut, is `_restate` on each window result: `graph.footage` over every read of a
  node below a cut in time, and the strip handed every cut in time (`timeline.lanes`). At 3200 a
  dataclass `__init__` the monitor's `ledger._view` runs takes some 64000 steps more; generated
  code is counted whoever calls it.

- O8, his: a bare walk and a clip walk leave the same held; bare is only the faster for having
  no window beside it.
- O9, his: nothing computed only for the window reaches a tool, a walk of the clip or the held
  file.
- O10, his: the window shows what is asked of it, every series node's line over its rows, whether
  or not a clip walk was made. The miniature asks it over a window inside a period, one over two
  whole periods and one cutting periods at both edges; before a clip walk the lines at a period
  cut off by the window's edge are to be best effort, and after one none is.
- O11, his: a full run made and the document saved, the document and its checkpoint copied
  elsewhere and opened: every run the first player held is served without walking.
- O14, his ruling: a held run made under a tool's older code is served after the tool's code
  changes, and its node is marked as of other code.
- O12 and O13 were of a frame node's small rows in the checkpoint, which he ruled out of it.

## What checks the work

- `sim/miniature.py`, the player itself over a clip made for it, says which of O7 to O11 and O14 hold.
  It writes nothing outside a temp folder. It does not see real threads, decode or disk.
- What caught real defects: an adversary told to prove a break in a scratch copy; an unanchored
  reader tracing one path; a profile of the real document
  (`docs/findings/experiments/2026-11-21-the-gui-thread-while-the-clip-lane-walks-periods.py`).
- What did not: a ledger of my own beliefs rechecked on a file's change. A belief that bites is
  one never written down.
- `contract.md` is the design as assertions. Most of it is not built; a line of it is no
  evidence about the tree.

## Next

`sim/miniature.py` is the player's own window, worker, plan, held runs and tools over a clip made
for it, the worker's turns taken on one thread, and it says which of O7 to O11 and O14 hold. A defect
found on a real document is pinned there. An alternative holder goes behind the seam the held
runs sit behind and is driven against the same checks.

1. Which of the places results are held in are apart for no reason, and can be one.
2. O10 is open for a gate inside a cut in time: a cutting node whose CUT_BY wire's node is below
   another cut in time is answered by held runs alone (`heldwalks.window_gate_result` answers
   none for a cut in time) and the window shows nothing below it until that cut is walked whole.
3. The held runs onto the store behind that seam, driven against today's. Goal 2 moves here.

Not to be done on this machine: long walks or timing runs for their own sake. He said no stress
testing, and a restart now and then is fine.

## Where things are

- In the player, to be verified in the tree: holders sized from the machine's RAM (`budget.py`);
  the window-against-full test over the registry; display proxies; a frame node's rows held by
  the graph's memo for a session and nowhere after it; the held runs and the window's own runs
  within `budget.py`'s "held", the window's held apart and never written; a bare walk walking the
  clip and its cuts in time and handing back their results; a checkpoint beside the document,
  `<document>.checkpoint`, one append-only file of its held runs and nothing else (`held.py`),
  written at a save where a run was held or the path changed. A tool's code is in no key: a run
  held under older code is served and its node marked (`held.marked`, the window's `_show_stale`).
  A cutting node whose gate no held run answers is cut provisionally of the gate's result as the
  window walked it (`plan.Provisional`, `cut.Record.provisional` and `cut_off`, `Plan.unheld`):
  those cuts are walked by the window lane alone, shown, best effort where cut off at the
  window's edge, and never held, written, baked or handed to a card; the cuts are made again as
  the window's walk hands the gate's result (the window's `_cut_again`).
- Not in the player: the memo, the decode cache, the held runs and cut files are each their own
  holder still; no one ask. Frame, series and stepped results are kept by nothing across sessions
  but the runs the series chain's results are held as.

## His rulings

- On a tool's code in the key: "Mark stale." A result made under older code is found by its key
  and marked; the code is not in the key. A trace on this branch (commit 16e54fe7, not reread
  since) found that such a result is drawn, feeds walks, cuts a `period` and is written to a csv
  whose card reads "on disk: this graph's", the `!` on its card the one mark.
- On the checkpoint: "if the user did a full run and hit save, it opens on that too." It holds the
  held runs, and not a frame node's small rows or the document's form.
- The footage print is v5's, size and the first and last `decoder.SLICE` bytes: sampling between
  them guarded a rare case and moved every key against v5.
- Findings of this branch: `docs/findings/2026-11-21-the-player-died-walking-856-periods.md`,
  `docs/findings/2026-11-21-bare-walk-crashes-on-the-full-file.md`,
  `docs/findings/window-against-full.md`.

## Known open, mine

- Five tools declare a reach without bound and no measurement stands behind it.
- A cut file served to a bare walk, and every key, are named by the footage print: footage
  changed only between its first and last `decoder.SLICE` bytes, at the same size, is taken for
  the one before.
- Whether the mark of other code reaches nodes under a cut in time is unread.
- The registry's types are unchecked for a set of periods as a value, a gate of two inputs, a
  matrix of time by scale.

## His to decide, none blocking

- Whether a csv written from a window's card says it is the window's.
- `docs/spec/a-cut-in-time.md`, the box of a `period` fed a series node's result: while no walk is
  held it "has no periods and says it waits"; the tree gives it provisional periods inside the
  window beside the waiting.
- The encoder's version is in no cut file's key.
- A test in `tests/test_graph.py` asserting wall time failed once and is not marked `simulation`.

## Standing words of his

- A failed check is a defect to find. The processor is a hypothesis, tested against the event
  logs, and never the assumed cause.
- He reopens the player mid-change: a change that orphans held results is said before it lands.
- A run is queued through the orchestrator, whose window he opens on this project.
