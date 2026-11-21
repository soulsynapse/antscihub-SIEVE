# Playground journal: one store

Branch `v5-playground-one-store`, cut from `v5`. This file is the working memory of the effort and
is deleted before anything merges. A session resuming after a restart or a compaction reads this
file whole, then `git log --oneline v5..HEAD`, then `orchestrator list`, and trusts none of the
three over the tree.

## What Kendrick asked for (2026-11-21)

He wants to stop thinking about the backend: the decode cache, the memo, the series, the held
file, the document's file, the monitor, what periods and other tools keep. Today a new tool means
touching several of them to be sure nothing broke. His goals, in his words:

1. Windows are reliable and fast.
2. A saved file opens where the user left off, as the user expects.
3. Walk bare and walk clip keep working as tools are added.
4. What is likely to be revisited does not cost the user much.

Two hardware facts he holds as real, not hedges: people will run SIEVE on machines with few
cores, little RAM, slow or small disks, and a large enough pipeline, footage or window makes any
machine hardware-limited, which must make it slow and never make it fail; and SIEVE will run on
HPC for larger projects, so it should fill the resources it is given.

He handed over the branch: decide forks here with the reasoning written down, cover my own blind
spots, report player-visible decisions at the end so he can overrule them.

## Decisions made, and why

- D1. A checkpoint is bound to its key and carries a snapshot of the document it was made under.
  An upstream edit stops it being served and leaves it on disk; going back restores settings and
  results together. Why: a frozen result served under changed settings is the one case that
  breaks "what is shown equals a recompute". (He accepted.)
- D2. Saving a file promises pinned results only. Everything else is a cache that persists across
  sessions and is usually warm, never promised. (He accepted.)
- D3. The effort runs through building into `sieve_player` on this branch, stopping to report at
  each stage boundary. (He accepted.)
- D4. Budget: 15 queued runs and 4 propose-build-test cycles, then stop and write up, finished or
  not. The counters are below. (He accepted.)
- D5. Resources are one budget, not a constant a module. Memory, cores and disk are each given as
  a figure the store and the walk are held under, read from the machine by default. The same
  figure made small is the low-end machine and made large is the HPC node.
- D6. The store is safe under many writers: several processes, and on HPC several nodes on one
  filesystem. A result lands by a write to a temporary name and an atomic rename under its key.

## The invariants the work is held to (the oracles)

- O1. Served equals recomputed: under any sequence of edit, scrub, walk, evict, crash mid-write
  and reopen, what is handed out for a key equals a cold recompute of that key.
- O2. Dropping any unpinned entry changes speed and nothing else.
- O3. A pinned entry is served after a reopen, or the store says it is gone; never a wrong one.
- O4. Adding a tool changes no file of the store, the walk or the monitor.
- O5. Peak memory held stays under the budget given, at any pipeline, footage and window; a
  budget too small for one row's work is said, not crashed on.
- O6. Two processes writing the same key leave one whole entry.

## Blind spots I know of, and what covers each

- I have not read the runtime. `docs/systems-review.md` is of 2026-11-16 and by Kendrick's word
  estimated and spottily updated. Covered by stage 1, which reads the tree and not the review.
- "Six stores" is the review's guess at where the feeding is. The measure is the history: what a
  commit that added a tool or a kind of result had to touch outside `tools/`. Stage 1 counts it.
- The monitor is not a store, and he named it among what must be fed. Stage 1 says what a tool or
  a store must emit today, so the contract can emit it once on everyone's behalf.
- A proxy with no Qt and no threads cannot see the GUI thread, the GIL or the worker's ladder,
  where goal 1 lives. The slices are held to the existing suite, `smoke.py`, `bench.py` and the
  findings on GUI cost, and the proxy's cost readout is labelled as blind to them.
- One machine to measure on. Low-end profiles are emulated where the budget makes them real
  (memory, cores by affinity) and labelled as extrapolation where it does not (disk speed).
- I lean to the general design. The inventory decides what the contract needs; a referent is
  cited for a part only where the tree shows the problem it answers.

## Stages

1. Inventory. Every place that holds or keys a result or must be told of one, read off the tree;
   and the files past tool additions touched, read off the log. Lands as `docs/playground/inventory.md`.
2. The contract, as a spec in the repo's assertion style, from the inventory and the referents
   (Nuke's Op hash and DiskCache; Mokhov, Mitchell and Peyton Jones, Build Systems a la Carte;
   content-addressed stores as in Nix and Bazel for D6).
3. One proxy: a small pure-Python store behind the contract, synthetic tools with declared costs
   and sizes, the oracles run over random sequences, and the same sequences priced per hardware
   profile from figures in `docs/findings/`. One real bare walk calibrates the pricing.
4. Slices into `sieve_player`, one of the inventory's holders at a time, each a queued run whose
   criterion is the oracles and the suite; each diff read here before the next is queued.

## How the work is run

- The orchestrator queue for this tree: `uv run --project ~/Documents/Code/agent-orchestrator
  orchestrator add|list|log|cancel|wait`. A queued run is its own session on the queue panel's
  model, works in this same tree, and is told to commit and push; nothing is edited here while
  one is in flight. `orchestrator wait` run in the background is the wake-up.
- Design, reading of results and review of diffs happen in the supervising session; reading
  across many files and building go to queued runs.
- Every run or measurement is capped near a minute of wall time.

## Counters

Queued runs used: 0 of 15. Cycles used: 0 of 4.

## Log

- 2026-11-21. Branch cut, journal written. Stage 1 queued next.
