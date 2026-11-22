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
second writer of one address. O1, O4 and O5 read on as claims about the memo, the keeper and the
checkpoint that nothing checks.

- O1. What is handed out for an address equals a cold recompute of it, under any sequence of
  edit, scrub, walk, evict, crash mid-write and reopen.
- O2. Dropping any entry no checkpoint names changes speed and nothing else.
- O3. A checkpoint is served after a reopen, or the store says it is gone; never a wrong one.
- O4. Adding a tool changes no file of the store, the walk or the monitor.
- O5. Memory held stays under the budget given; a budget too small for one row's work is said.
- O6. Two processes writing the same address leave one whole entry.
- O7, from the 850 periods: what one more cut, run or node costs a turn of either thread does
  not grow with how many there are.

- O8, his: a bare walk and a clip walk leave the same held; bare is only the faster for having
  no window beside it.
- O9, his: nothing computed only for the window reaches a tool, a walk of the clip or the held
  file.
- O10, his: the window shows what is asked of it, every series node's line over its rows, whether
  or not a clip walk was made.
- O11, his: a colleague's laptop gets the document and its checkpoint, and what lives in the
  checkpoint is what should be beside it: copied to another folder and opened with no other
  source of rows, it serves every run held without walking, and after an edit below a frame node
  that makes small rows a clip walk runs that node zero times.
- O12, from O7: what one more cut in time costs the kept rows, in steps of `result_keeper.py` and
  in the checkpoint's bytes, does not grow with how many there are, and no chunk is written to
  the checkpoint twice.
- O13, his: what a bare walk computed of a frame node's small rows reaches the checkpoint: handed
  back with its results, held by the player's keeper, written at the save, and a player of a
  copy runs that node zero times after an edit below it.

## What checks the work

- `sim/miniature.py`, the player itself over a clip made for it, says which of O7 to O13 hold.
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
for it, the worker's turns taken on one thread, and it says which of O7 to O13 hold. A defect
found on a real document is pinned there. An alternative holder goes behind the seam the held
runs sit behind and is driven against the same checks.

1. Which of the places results are held in are apart for no reason, and can be one.
2. O10: a cutting node cut by a result on a wire makes no cut until a run of that result over
   the whole clip is held (`heldwalks.gate_result`), so the window shows nothing below it.
3. The held runs onto the store behind that seam, driven against today's. Goal 2 moves here.
4. The keeper's address follows `cut.read`, as the memo's does; then series and stepped nodes
   under it, `track` above all.

Not to be done on this machine: long walks or timing runs for their own sake. He said no stress
testing, and a restart now and then is fine.

## Where things are

- In the player, to be verified in the tree: holders sized from the machine's RAM (`budget.py`);
  the window-against-full test over the registry; display proxies; a tool's code in every node's
  key; a frame node's small rows held in memory by the session's keeper (`result_keeper.py`)
  under the node's raw key, the cut's rows and its reach, a bare walk's handed back with its
  results; a checkpoint beside the document, one append-only file of its held runs, the keeper's
  chunks and the document's form (`held.py`), the one place on disk the small rows lie, whose
  document record nothing reads yet.
- Not in the player: the memo, the decode cache, the held runs, the keeper and cut files are each
  their own holder still; no one ask. Series and stepped results are kept by nothing across a
  bare walk but the runs its results are held as.
- Findings of this branch: `docs/findings/2026-11-21-the-player-died-walking-856-periods.md`,
  `docs/findings/2026-11-21-bare-walk-crashes-on-the-full-file.md`,
  `docs/findings/window-against-full.md`.

## Known open, mine

- Five tools declare a reach without bound and no measurement stands behind it.
- The keeper decides what to keep by a value's shape, and saves no stepped state at a chunk's edge.
- A cut file served to a bare walk, and a row the keeper keeps, are named by the sampled footage
  print: footage changed only between its samples is taken for the one before.
- A kept row's address holds nothing of the player's own code or numpy's and cv2's versions, as a
  held run's key does not: an edit of the walking code or a library leaves kept rows answering.
- A crash loses every kept chunk no write has taken; a write a held run waits on takes the whole
  ones, a save and a close the rest.
- Whether the mark of other code reaches nodes under a cut in time is unread.
- The registry's types are unchecked for a set of periods as a value, a gate of two inputs, a
  matrix of time by scale.

## His to decide, none blocking

- How much of the checkpoint the kept rows may take: the window hands the keeper and the file the
  held runs' figure, `budget.py`'s "held", as their bound.
- Whether a csv written from a window's card says it is the window's.
- The encoder's version is in no cut file's key.
- A test in `tests/test_graph.py` asserting wall time failed once and is not marked `simulation`.
- `docs/spec/what-a-node-declares.md` and `docs/spec/held-results.md` say the key holds no code;
  the tree now does otherwise, and the specs are his.

## Standing words of his

- A failed check is a defect to find. The processor is a hypothesis, tested against the event
  logs, and never the assumed cause.
- He reopens the player mid-change: a change that orphans held results is said before it lands.
- A run is queued through the orchestrator, whose window he opens on this project.
