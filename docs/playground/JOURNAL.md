# Playground journal: one store

Branch `v5-playground-one-store`, cut from `v5`. This file is the working memory of the effort and
is deleted before anything merges.

## Resume here

A session resuming after a restart or a compaction reads this file whole and then acts on "Next
action". It does not reread `inventory.md`, the systems review or the code to rebuild what this
file already concludes: a row of the inventory is opened only to check one fact, by section. It
verifies state with `git log --oneline v5..HEAD` and `orchestrator list`, and trusts the tree over
this file where they differ.

- Stage: 3 (the simulation), its first half done. Stage 1 is `docs/playground/inventory.md`,
  stage 2 is `docs/playground/contract.md`, and `docs/playground/sim/store.py` with `sim.py` are
  the contract in code: `.venv/Scripts/python.exe docs/playground/sim/sim.py 150` runs the
  torture in about ten seconds and prints a line a scheme. Read "What the simulation has shown"
  before touching either file.
- Next action, in order: (a) the three changes "What the prices say" asks of the store and the
  ask, each tried in `sim.py` and kept only if the table moves: a scrub computes the row looked
  at and not its chunk; the disk tier lets go by worth as the memory tier does; a walk holds a
  plane while memory is free and stops when it is not. (b) A 5.3K table
  (`sim.py prices 5.3K`, not yet run) and a workload of many pieces walked at once by several
  stores on one disk, which is the HPC case and the one thing about cores still unpriced.
  (c) Cheap claim checks, which he offered Haiku for on 2026-11-21 with the rule that it is
  given one claim at a time and never a section to search: an Agent with `model: haiku`, one
  claim about the tree, the file to look in, and the answer wanted as holds, does not hold or
  cannot tell, with the line. I pick the claims, the ones a later step leans on. Calibrate
  first with a claim known true and one known false. The one-minute cap on runs is lifted, by
  his word the same day; a queued run's prompt no longer carries it.
  (d) Rewrite
  `contract.md` to what the simulation settled, then stage 4's first slice.
- Run the simulation: `.venv/Scripts/python.exe docs/playground/sim/sim.py 150` (torture, a line
  a scheme) and `... sim.py prices 1080p [profile]` (the table below), a few seconds each.
- Counters: queued runs 2 of 15; cycles 2 of 4 (the contract and its torture; the prices).
- Context: `bash ~/.claude/tools/context-used.sh 300` prints what is left before the auto-compact
  window (300k by his `/autocompact` on 2026-11-21). Bring this file up to date before a step
  that reads a lot, and when under about 30k left.
- No PushNotification: he had the Finishing section taken out of his global CLAUDE.md on
  2026-11-21.

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

## What the simulation has shown

`sim.py` holds a `World` (the document, the tools' code, the footage), whose `truth` is a digest
of everything a value really depends on and whose `key` is what a `Scheme` puts in a key; a
simulated `Disk` with a clock, a crash between the two steps of a write, and several stores on
one folder; an `Ask` that is the contract's `demand`; and `run`, which plays a seeded sequence of
a user's doings (scrub, walk, edit, edit of a draw's param, edit of tool code, footage changed in
its middle, evict, delete files, reopen, crash mid-walk, a second process walking, checkpoint,
restore) and checks O1, O3, O5 and O6 after each. `shrunk` cuts a failing sequence to its least.

- The contract's scheme breaks no oracle over 150 seeds of 60 doings on the laptop profile.
- Tool code left out of the key, as today: O1 broken by scrub, edit code, a second process walks.
- The footage print of size and ends, as today: O1 broken by scrub, footage changes, walk.
- Entries written in place: O1 broken by a crash mid-walk, twice. So the oracles have teeth.
- The first run broke O5 in my own store: memory let go before the inputs were read was filled
  again by reading them. The fix is in the contract's terms a reservation: work under way takes
  its output and its live inputs out of the one budget (`Store.reserve`, `release`), and what is
  held plus what is reserved never passes it. Today's `graph.py:Ref` and the "pinned" memo
  entries are this same double count unsolved.
- Not yet exercised: the disk budget under pressure with checkpoints, priority of a scrub over a
  walk, cores, and any cost figure. O2 is covered through O1 after evict and delete; O4 is not a
  simulation's to show and is counted at stage 4 by what a slice lets a new tool leave alone.

## What the figures say (run 2, `figures.md`; machine: i9-14900KF, 32 threads, 64 GB, NVMe)

- A seek costs 80 to 140 ms at 1080p and 490 ms at 5.3K, against 1.1 to 2.8 ms for a row read
  in order: one seek is fifty to a hundred rows. Scrub latency is seeks, not tools.
- Work does not scale with cores inside one clip. Threads flatten at about four (7.03 ms a row
  at one worker, 2.05 at four and at eight, worse at sixteen); four decoders on chunks give
  1.3 times one; sixteen processes give 3.4 times after 0.6 s to start. So `Ask.walk`'s
  `speed = cores` is wrong: cap it near 3.5 within a clip. Filling an HPC node is done across
  pieces that share nothing (clips, regions, cuts in time, documents), a process each, which is
  what a store of many writers allows and the reason D6 matters more than I had it.
- Holding more made a walk slower: the stress document's bare walk ran 515 rows a second under a
  64 MB memo and 151 to 316 under 4 GB. A put to memory is not free, and "fill the RAM" is wrong
  for planes a walk passes through.
- A plane is cheap to make and dear to keep: about 2 ms and 2 MB a row at 1080p, so writing it
  to a 100 MB/s disk costs ten times recomputing it. A table or a signal is the reverse: a
  track step is 0.6 to 0.9 ms for 1.2 KB, a signal 4 B. Whole-clip series tools cost seconds
  (tracks-filter 1.8 s, resolve 2.1 s over 38100 rows).
- So the tiers take entries by what they save per byte, recompute time over size, not by
  recency alone: GreedyDual-Size (Cao and Irani 1997) is the referent. Planes stay in memory
  near the playhead and go to disk only when a slow producer makes them worth it (a 5.3K
  decode at 31 ms, a background composite at 32 s); tables, signals and whole results always go.
  This is a policy object in the simulation, compared against plain LRU.

Three changes this asks of `sim.py`: the speed cap; a cost to a memory put and a policy that may
decline to hold; the real figures in `pipeline()` and `PROFILES`, with a 5.3K variant.

## What the prices say (`sim.py prices 1080p`; an hour of footage, the ants-like pipeline)

The policies compared: "worth" ranks memory by seconds saved a byte, writes to disk only what
costs more to make than to write, and lets a plane pass through a walk unheld; "lru" holds by
recency and writes everything. Disk rates and the laptop and HPC profiles are guesses.

- The first walk of the tracks: 755 s against 11384 on the laptop, 374 against 1048 on the
  desktop, 395 against 3944 on the HPC profile. Writing planes is the whole difference.
- Under lru the laptop's 40 GB fills with planes, which push the tables off the disk: the same
  walk again costs 1988 s where worth costs none, and the checkpoint is refused with 1653 of
  2132 entries gone. Under worth the hour's results are 0.1 GB. This is the case for goal 4.
- Reopened, the walk is answered from disk in 0.4 to 17 s under worth.
- Where worth loses: after a nudge to detect, the walk decodes again what it let pass, 137 s
  against 52 on the desktop and 276 against 193 on HPC. Memory was free there and worth did not
  use it. Hence change three above.
- A scrub while building is 168 ms on the desktop and 317 on the laptop, nearly all of it one
  seek and a chunk of ten rows computed for one looked at. Hence change one.
- On the desktop worth still wrote 129 GB: decoded chunks reached by a seek cost more than their
  write. Right by its own rule, and they are what the disk should let go of first. Change two.
- The torture still holds for both policies and still breaks for today's three weaknesses.

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
| 2 | Measured figures from `docs/findings/`, one table, told which findings to open first | 2m 31s | about 88k, 24 turns | On brief, every row sourced, disagreements kept as two rows, empty cells said. The shape to reuse: one file out, the reader told it is the queued run, where to start reading, a line cap. |
| 1 | Stage 1 inventory, five questions over the whole tree and the log | 8m 30s | about 215k, 115 turns | Output accurate on five spot checks, dense, on brief. Too wide for one run: five questions should have been two or three runs. It took the journal's "supervising session" to be itself; later prompts say who the reader is. |

## Log

- 2026-11-21. Branch cut, journal written, stage 1 run and read. Hypothesis written above.
- 2026-11-21. Contract written; store and simulation written here, not queued, being small and
  the design itself. Torture passes for the contract and fails for today's three weaknesses.
- 2026-11-21. Figures gathered by run 2; chunks by bytes, the worth policy and priced workloads
  added to the simulation. A first pricing run passed its minute for an uncached cut; memoized.
