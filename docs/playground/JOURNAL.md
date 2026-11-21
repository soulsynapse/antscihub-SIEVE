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
- Next action, in order: (a) read `docs/playground/adversary.md` when run 5 lands (Opus, told
  to break the store and the contract where the torture does not reach) and take what holds
  into `sim.py` as ops. (b) The on-disk store, `Store` over a real folder, mine to write since
  it is the design: per-file cost and the grace below are its two hard parts; then one real
  walk against the simulation's figure for it. (c) Slices onto it: the held file, then the
  walks' results. Then STOP for him to try the player, before the memo is touched; the memo
  may stay as the memory tier under the same rules. (d) Code beside the key, once he has
  answered "A decision of his the contract ran into". (e) The whole-file footage hash.
- This journal is notes to resume from, not rules. He said so on 2026-11-21 ("sometimes you make
  documentation and then treat it as binding"), and it was true of the cycle cap and of the
  contract's line on code in the key. Where the work shows a line here is wrong, the line goes.
- Standing step, his on 2026-11-21 and mine by its results: before a slice or the contract
  leans on a claim about the tree, from this journal, the inventory or my memory, the claim goes
  to a Haiku check, one claim a pass, by the shape under "Claims checked one at a time". Six
  passes corrected two of my claims. Not for searching, not for judging a design.
- Run the simulation: `.venv/Scripts/python.exe docs/playground/sim/sim.py 150` (torture, a line
  a scheme) and `... sim.py prices 1080p [profile]` (the table below), a few seconds each.
- Counters: queued runs 5 of 25 (his figure, 2026-11-21). No cap on design cycles, by the same word: a
  cycle on the simulation is run when a slice raises a question whose answer would change it.
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

## What the simulation settled (`sim.py prices 1080p` and `5.3K`; an hour, the ants-like pipeline)

Disk rates and the laptop and HPC profiles are guesses; the desktop is the measured machine.
"lru" is one budgeted store that holds by recency and writes everything, the naive reading of
the hypothesis. The policy below is `worth=True` in `store.py`, and it is the contract's.

- An address is a key and a row to a caller. A chunk is how the disk packs rows, sized by bytes,
  and a caller never names one. A row looked at is made alone and held in memory only; a walk
  fills chunks. A scrub while building is then one seek and one row: 103 ms on the desktop,
  257 on the laptop, 526 at 5.3K. The store cannot make that less; a decoder reading ahead can.
- An entry's cost is all the time its making took, its inputs' too, handed to the store with it.
- Memory lets go by seconds saved a byte (GreedyDual-Size). In a walk a plane passing through
  is held only into free memory and never pushes anything out.
- Disk takes at once what cost ten times its write to make, which is every table and signal and
  no plane; a plane that cost at least its write is written the second time it is made, and
  only into free disk. Nothing is let go to make room for a maybe. Disk lets go by worth a
  byte for its age, never what a checkpoint names.
- What that buys at 1080p: the first walk 392 s against 1049 under lru on the desktop, 1031
  against 11386 on the laptop; the same walk again and a reopened file's walk answered in under
  20 s everywhere; a detect nudge 106 s, then 59, then 51, where lru is 52 each time. The first
  nudge is the price of not writing planes on a guess.
- What lru loses: planes fill the disk and push the tables off it. On the laptop the same walk
  again costs 1989 s and the checkpoint is refused; at 5.3K the desktop does the same (9711 s,
  checkpoint refused with 14296 of 21706 entries gone). One store with one recency order is
  worse than today's separate holders. The policy is the design, not a tuning.
- Where the policy still loses: the laptop at 5.3K, 21476 s for every nudge, since 40 GB holds
  almost none of the gray planes. Slow and never failing, which is what he asked of small
  machines; a region or a scale on the pipeline is the user's lever there, not the store's.
- The gate's pass and the detect pass both decode the kept pieces, so a walk decodes them
  twice. A fused walk that feeds both from one decode is the walk's to gain, not the store's.
- The torture holds for both policies over 150 seeds and breaks for today's three weaknesses.

## Two writers at once, and what a real disk costs (2026-11-21)

- `diskrate.py`: the store's NVMe writes 1637 MB/s through an fsync and the USB hard drive 235;
  a small file costs 1.4 ms and 3.2 ms to write and rename whatever its size. Its read figures
  came from the page cache and mean nothing. `PROFILES` has the writes and a `usb-hdd` profile.
  The per-file cost says a table's chunk should be far more rows than a plane's: ten rows a
  file is 10800 files a node an hour. Chunks sized by the node's own row, not the widest.
- The torture has a `race` op: a walk or a checkpoint while another writer lets go of loose
  entries between any two of this one's disk steps. It broke two things at once. A checkpoint
  looked for its entries and then named them, and one went in between: now the manifest lands
  first, then the look, and a refused checkpoint fills and tries again. And letting go listed
  the files and then ranked them, and one was gone: a file gone since it was listed is skipped.
  400 seeds hold for both policies after.
- What the simulation cannot show: its other writer reads the manifests at the moment it lets
  go. A real one reads them, then deletes, and a manifest can land in between. Git's prune has
  this race and answers it with a grace period, never pruning what is younger than it. Here:
  letting go is a rename into a `trash/` folder, emptied of what has lain there past a grace;
  a checkpoint that finds an entry gone takes it back out of the trash by a rename.
- Disk lets go by GreedyDual-Size now, the floor kept on the disk for every writer.

## A decision of his the contract ran into

`docs/spec/what-a-node-declares.md:263` is ticked in his name: held results outlive an edit to a
tool, are served, and are let go by hand; the node shows `!` and the user decides. The contract
put the code's digest in the key, slice 1 built that, and its run said what it broke: after a
restart, results of older code are not found at all. Its own test showed the cost he decided
against, a comment's edit changing the key. I took that half of slice 1 back out (the footage
sampling stays). Not mine to overrule, and both are wanted: an HPC job must never take another
code's result for its own, and an edit must not throw away a day's walks unasked.

What I will propose to him, not build unasked: the code's digest rides beside the key and not
in it. An address is a key, a code and a row; a lookup takes the entry of this code, or failing
that one of another code and says it is stale, which is his `!`; a walk that must be exact (a
bare walk, a cluster job, a checkpoint being filled) asks for this code only. O1 then reads:
two values under one key and one code are equal, and a value of another code is never served
unmarked.

## Drift from the referents (told to him 2026-11-21)

- The footage print samples; Git's index and Bazel hash the whole file once and remember it by
  path, size and time. Follow slice 1 with that, the sampled print standing in until the whole
  one is made in the background.
- Disk lets go by worth over age, which is mine; GreedyDual-Size is the referent and memory
  already uses it. The "ten times its write" is tuned to guessed disks.
- The simulation is stateful property testing, not FoundationDB's: no two stores run
  interleaved. One letting go of a file another is reading is Bazel's disk cache's known weak
  spot and is untested here.
- Keys are of inputs' keys, as Nix's, so there is no early cutoff as Shake and Bazel have.
  Left so; draw-only params cover the common case.
- Reservations are Spark's unified memory manager (execution memory may push out storage
  memory, in one pool). Read how it bounds that before the real one is built.

## Claims checked one at a time (Haiku, 2026-11-21)

The shape that worked, five of five: "Check ONE claim against code in <repo>. Read only. Claim:
<one sentence, with the file and the function>. <what to read or grep>. Answer in under N
words: HOLDS, DOES NOT HOLD or CANNOT TELL; the file:line that decides it, quoted." Each took 7
to 17 s and two to six tool calls. A planted false claim (the footage print hashes every byte)
came back DOES NOT HOLD with the lines; a known true one (`bare.py` never reads `timed`) HOLDS,
with its own limit stated. Run them in one message, in parallel.

- Holds: no key of `plan.py` carries a code digest (`plan.py:269`). But the claim as I had it
  was too strong: `registry.code_print` exists, `walk.py:453` and `:485` record it beside held
  results, and `window.py:1344` marks a card stale from it (`held.marked`, `held.py:402`). A
  sixth pass found no caller that keeps a stale held result from being served, without tracing
  the serve path; and corrected me that `store.py` names no file: `tools/_cutfile.py` and the
  decoder do, under the store's folder.
- Holds: nothing sizes a budget from the machine's RAM; `machine.py:129` reads it to report.
- Does not hold, that the held file is always written beside and renamed: `held.py:149` appends
  in place when every record is kept, and `load` (`held.py:131`) stops at the first record that
  does not read, so a torn tail loses the tail and nothing else. An append-only log with a
  tolerant reader is a sound second way to be atomic; the contract may allow it for tables.

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
| 4 | Slice 2: `budget.py`, each holder's limit shared out of half the RAM, today's constants as ceilings | 2m 01s | not read | Clean, 39 lines, three tests, said its own choices: an env override can still push the sum past the total; `walk` reads the real machine at import, so a test leaning on the default stack sees less on a machine under about 21 GB; `tests/test_graph.py` restores `STACK_BYTES` to a literal. Kept. |
| 3 | Slice 1: code digest in `key_of`, footage print sampled at 32 offsets | 2m 21s | not read | Did what was asked and found what I had not: the ticked decision above, and two docs made false (`docs/spec/held-results.md:25`, a finding's line 117). The key half taken back out by me. The prompt's "say what your change made false" line is what surfaced it; keep it in every slice. |
| 2 | Measured figures from `docs/findings/`, one table, told which findings to open first | 2m 31s | about 88k, 24 turns | On brief, every row sourced, disagreements kept as two rows, empty cells said. The shape to reuse: one file out, the reader told it is the queued run, where to start reading, a line cap. |
| 1 | Stage 1 inventory, five questions over the whole tree and the log | 8m 30s | about 215k, 115 turns | Output accurate on five spot checks, dense, on brief. Too wide for one run: five questions should have been two or three runs. It took the journal's "supervising session" to be itself; later prompts say who the reader is. |

## Log

- 2026-11-21. Branch cut, journal written, stage 1 run and read. Hypothesis written above.
- 2026-11-21. Contract written; store and simulation written here, not queued, being small and
  the design itself. Torture passes for the contract and fails for today's three weaknesses.
- 2026-11-21. Figures gathered by run 2; chunks by bytes, the worth policy and priced workloads
  added to the simulation. A first pricing run passed its minute for an uncached cut; memoized.
