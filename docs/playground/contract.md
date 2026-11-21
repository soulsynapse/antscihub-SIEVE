# The contract: one address, one store, one ask

Stage 2 of `docs/playground/JOURNAL.md`. Each line is an assertion that holds of the built thing.
`docs/playground/sim/` is this contract in code, and where the two differ the simulation is right
and this file is behind. A line marked (open) is a choice not yet settled.

## The address

- A caller addresses a result by a key and a row. The key is `plan.py`'s. A result with no rows
  has one address.
- A key holds everything the value depends on and nothing else: the tool's name, the digest of
  its code, the params its run reads, the keys of what it reads, the footage's print, and the cut
  it was made inside. Two values under one address are equal.
- The footage's print changes when the file's bytes change anywhere in it, to the odds its
  sampling gives, and costs no more than a seek's worth of time to make.
- A chunk is how the disk packs the rows of a key: consecutive rows on a grid fixed for the key,
  sized by bytes and not by a count. No caller names a chunk.
- A stepped tool's row depends on the rows before it in its cut. Its address is the same; the ask
  makes its rows in order from the cut's first row or from the end of the last chunk held.

## The store

- There is one store. It answers `get`, `put`, `covered` and `drop`, and nothing holds a result
  but through it: not the walk, the window, a tool or a card.
- It has a memory tier and a disk tier. A caller does not say which and cannot tell which
  answered, but by time.
- A `put` carries the seconds the value took to make, its inputs' making among them.
- Memory holds no more than the memory budget less what work under way has reserved. It lets go
  of what saves the fewest seconds a byte first. A row looked at is held in memory only. A plane
  a walk passes through is held only into free memory and pushes nothing out.
- Disk holds no more than the disk budget. It takes at once what cost many times its own write
  to make, which is a table or a signal and not a plane; a value that cost at least its write is
  taken the second time it is made, and only into free room. It lets go, for what it must take,
  of what saves the fewest seconds a byte for its age.
- An entry lands whole or not at all: by a write to a name no other writer uses and one rename,
  or by an append to a log whose reader stops at the first record that does not read. A file
  that is not whole is no entry.
- Dropping any entry no checkpoint names changes how long an ask takes and nothing else.
- Two stores open on one folder, in two processes or on two machines, are one store on disk.
- The store says what it does to the monitor's stream: a hit by tier, a miss, a put, a letting
  go, a refusal. No tool and no caller emits for it.

## A checkpoint

- A checkpoint is a manifest: a name, a snapshot of the document, and the addresses of the
  results the user asked to keep. It lands as an entry does, and what it names is written to
  disk whatever the policy thinks of it.
- The store never lets go of an entry a manifest names, in memory pressure or disk pressure;
  when the disk budget cannot hold what the manifests name, a new checkpoint is refused with the
  figures, and nothing already named is lost.
- A checkpoint is served only under its own keys. After an edit upstream its entries are still
  on disk and are not answered for the new keys; restoring the snapshot brings back the keys
  they answer.
- An entry a manifest names that is gone or not whole is said to be gone, by name, at open.

## The ask

- Anything that needs a result asks for it: the window, a clip walk, a bare walk, a cluster job,
  a csv write, a tool that reads another's whole result (a gate), a node served from a file. It
  is answered from the store or by computing, and the caller cannot tell which but by time.
- Computing reserves the memory its output and its live inputs take, asks for what it reads,
  puts what it made, and returns it. A missing input is made, never waited on.
- A look at one row makes that row. A walk makes chunks.
- An ask the user is looking at is answered before one that is not.
- Inside one clip, work is given the few cores it gains from. Cores past that go to pieces that
  share nothing, a process each, which the store's many writers allow. (open: how a walk is
  split into such pieces, and whether one decode can feed a gate and what it cuts.)

## The budget

- Memory, cores and disk are three figures read off the machine at start and overridable. No
  other constant in the player bounds a holder.
- A budget too small for one row's work is said with the row's need and the budget, and the
  player goes on.

## What a tool does about any of this

- Nothing. A tool declares what `registry` already reads; its code's digest and its params reach
  the key through the plan. Adding a tool, or a tool that reads another's whole result, changes
  no file of the store, the ask, the walk or the monitor.
