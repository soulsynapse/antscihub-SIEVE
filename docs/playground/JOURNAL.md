# Playground journal: one store

Branch `v5-playground-one-store`, cut from `v5`. This file is the working memory of the effort and
is deleted before anything merges.

## Resume here

A session resuming after a restart or a compaction reads this file whole and then acts on "Next
action". It does not reread `inventory.md`, the systems review or the code to rebuild what this
file already concludes: a row of the inventory is opened only to check one fact, by section. It
verifies state with `git log --oneline v5..HEAD` and `orchestrator list`, and trusts the tree over
this file where they differ.

- Stage: 2 (the contract), not yet written. Stage 1 is done: `docs/playground/inventory.md`.
- Next action: write `docs/playground/contract.md` from "The hypothesis" below, then build the
  simulator of stage 3 (`docs/playground/sim/`) against it.
- Counters: queued runs 1 of 15; cycles 0 of 4.
- Context: `bash ~/.claude/tools/context-used.sh 300` prints what is left before the auto-compact
  window (300k by his `/autocompact` on 2026-11-21). Bring this file up to date before a step
  that reads a lot, and when under about 30k left.
- No PushNotification in this effort, by his word on 2026-11-21, though his global CLAUDE.md asks
  for one.

## What Kendrick asked for (2026-11-21)

He wants to stop thinking about the backend: the decode cache, the memo, the series, the held
file, the document's file, the monitor, what periods and other tools keep. Today a new tool means
touching several of them to be sure nothing broke. His goals, in his words:

1. Windows are reliable and fast.
2. A saved file opens where the user left off, as the user expects.
3. Walk bare and walk clip keep working as tools are added.
4. What is likely to be revisited does not cost the user much.

Hardware, both ends real: machines with few cores, little RAM, slow or small disks, where a large
enough pipeline, footage or window must be slow and never fail; and HPC for larger projects,
where SIEVE should fill what it is given.

He handed over the branch: decide forks here with the reasoning written down, cover my own blind
spots, evaluate each queued run for quality and cost, keep prompts that work, and report
player-visible decisions at the end so he can overrule them.

## Decisions made, and why

- D1. A checkpoint is bound to its key and carries a snapshot of the document it was made under.
  An upstream edit stops it being served and leaves it on disk; going back restores settings and
  results together. Why: a frozen result served under changed settings breaks O1.
- D2. Saving a file promises checkpointed results only. Everything else is a cache that persists
  across sessions, usually warm, never promised. The tree has nothing called a pinned result
  (`Document.pinned` is the plot's list), so the contract coins the checkpoint.
- D3. The effort runs through building into `sieve_player` on this branch, reporting at each
  stage boundary.
- D4. Budget: 15 queued runs and 4 propose-build-test cycles, then stop and write up.
- D5. Resources are one budget read off the machine and overridable: memory, cores, disk. Small
  is the low-end machine, large is the HPC node.
- D6. The store is safe under many writers, across processes and nodes on one filesystem: a
  result lands by a uniquely named temporary and an atomic rename under its address.
- D7. Stage 3 is a deterministic simulation, not a mathematical model: the real store code run
  against a simulated clock, disk and memory budget, driven by a seed, with synthetic tools of
  declared cost and size. Hardware profiles are parameters; policies are swappable objects
  compared over the same seeds. Why: the code that passes is the code that ships, so only the
  cost figures need calibrating, and a failure replays from its seed. `hypothesis` is not in the
  venv; a seeded driver with its own shrink of a failing sequence is enough and adds nothing.

## The invariants the work is held to (the oracles)

- O1. Served equals recomputed: under any sequence of edit, scrub, walk, evict, crash mid-write
  and reopen, what is handed out for an address equals a cold recompute of it.
- O2. Dropping any entry that is not a checkpoint changes speed and nothing else.
- O3. A checkpoint is served after a reopen, or the store says it is gone; never a wrong one.
- O4. Adding a tool changes no file of the store, the walk or the monitor.
- O5. Memory held stays under the budget given, at any pipeline, footage and window; a budget
  too small for one row's work is said, not crashed on.
- O6. Two processes writing the same address leave one whole entry.

## What stage 1 found (the inventory's conclusions)

Against the oracles, as the tree is at `b23ff2c4`:

- O1 fails twice. Tool code is in no key (`plan.py:key_of`; `registry.code_print` exists and
  only badges a card), so a held run made under other code is served after a reopen. The footage
  print is size plus the first and last MB (`decoder.py:footage_print`).
- O2 fails for two holders that are sources and not caches. A `period` cut by a gate cuts
  nothing once the held run it read is let go (`plan.py:cuts_of`, "waits on"). A region serving a
  clip is unfed once the clip is deleted (`plan.py:file_of`). In both, nothing asks for the
  missing thing to be made.
- O3 has no referent; the held file's loss is silent (`held.py:File.load`).
- O4 holds only for a frame tool of existing types (PRs #26, #27 touched nothing outside
  `tools/` and `tests/`). The period tool (#33, 81 commits) touched `window` 26 times, `walk` 14,
  `worker` 12, `held` 12, `graph` 12, `plan` 11, `heldwalks` 11.
- O5 fails. Seven separate constants, none read off the machine, about 10.5 GB by default:
  memo 4 GB, decoder caches 4 GB, four walk stacks of 512 MB, held runs 512 MB; three holders
  pass their limits unsaid. Threads of OpenCV, BLAS, FFmpeg and ffmpeg processes are uncapped.
- O6 holds for frame-times and clips, not for the held file (appended in place, one fixed
  `.part`), nor the csv, recent, views and document writers.
- `bare.py:main` walks `p.chain` and never `p.timed`: bare already does not keep up with period.
  Each bare walk leaves a `%TEMP%/sieve-bare-*` folder nothing removes.

Holders of results, each with its own key use, bound, staleness rule and writer: the memo, the
decoder cache, a decoder per served clip, four walk stacks, the held runs and their pickle file,
`window.py`'s four result dicts, the bare temp folder, cut clips, csv, periods JSON, frame-times.

## The hypothesis (what the contract will say; untested until stage 3)

The keys are right and already one (`plan.py`). Two things are missing, and the period tool's
81 commits were spent standing in for them.

1. One address and one store. A result is addressed by (key, rows), where the key already holds
   the cut it was made inside. Every holder above becomes a tier of one store under one budget:
   memory first, disk under it, the same `get`, `put`, `covered` whatever the tier. On disk a
   key's rows lie in fixed chunks of rows, a file a chunk, written whole under D6; this is Zarr's
   layout and for its reason, many writers and no index to corrupt. A walk in the player, a bare
   walk and a job on a cluster all write the same chunks, and the player finds them by address,
   which retires the held file's pickle, the bare temp folder and `window.py`'s copies. A
   checkpoint is a manifest of addresses with a document snapshot; the store never evicts what a
   manifest names. The store emits its own monitor events, so no tool or new holder does.
2. One ask. Anything that needs a result says `demand(address, priority)` and is answered from
   the store or by a walk, without knowing which. A gate-fed period, a region's clip, the csv
   writer, the window and bare become callers of the one ask, and a missing input is made rather
   than waited on, which is O2 for the two holders that fail it. This is the scheduler Build
   Systems a la Carte separates from the store and the key; SIEVE's is the window pushing walks.

Smaller parts the inventory makes plain: tool code joins the key (O1); the footage print reads
more than two slices, at a cost to be measured; one budget arbiter splits memory among tiers and
caps library threads (O5).

Order of slices, least risk to goal 1 first, to be confirmed by the simulation: the budget
arbiter over today's holders; the disk tier in place of the held file and the bare folder, with
checkpoints; the one ask for gates and clips; bare walking cuts in time through the same walk.

What could make this wrong: a stepped tool's row depends on the walk from its range's start, so
a chunk may not be independently valid (the tree keys this by `walk.py:stacked_key`; the
simulation must model it); the GUI thread's cost of asking a store on every paint; chunk size
against scrub latency on a slow disk.

## Blind spots I know of, and what covers each

- I have not read the runtime myself; I hold the inventory's reading, spot-checked on five rows.
  A slice's run reads the modules it touches, and its diff is read here.
- The simulation cannot see the GUI thread, the GIL or the worker's ladder, where goal 1 lives.
  Slices are held to the suite, `smoke.py`, `bench.py`; the cost readout is labelled blind to it.
- One machine to measure on. Memory and core limits are emulated; disk speed is extrapolated and
  labelled so.
- I lean to the general design. A part of the contract stands only where the inventory shows the
  problem it answers.

## How the work is run

- The queue for this tree: `uv run --project ~/Documents/Code/agent-orchestrator orchestrator
  add|list|log|cancel|wait`. The window's "Wait for more" is ticked, so an entry starts on
  arrival. A queued run is its own session (Opus by the panel), in this same tree, told by the
  orchestrator to commit and push in Conventional Commit form; nothing is edited here while one
  is in flight. `orchestrator wait` in the background is the wake-up.
- A queued prompt opens by saying the reader is the queued run and not the supervising session,
  names one question or one slice, names the files to read where known, and caps its output.
- After each run: read its closing words (`orchestrator log`), its diff, and its transcript's
  size, and record them under "Runs".

## Runs

| # | What | Wall | Context, turns | Verdict |
|---|---|---|---|---|
| 1 | Stage 1 inventory, five questions over the whole tree and the log | 8m 30s | about 215k, 115 turns | Output accurate on five spot checks, dense, on brief. Too wide for one run: five questions should have been two or three runs. It took the journal's "supervising session" to be itself; later prompts say who the reader is. |

## Log

- 2026-11-21. Branch cut, journal written, stage 1 run and read. Hypothesis written above.
