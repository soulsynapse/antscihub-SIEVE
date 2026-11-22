# The contract: one address, one store, one ask

The design, each line an assertion that holds of the thing once built; most of it is not built,
and a line here is no evidence about the tree. `docs/playground/sim/` is this contract in code, and
where the two differ the simulation is right and this file is behind. A line marked (open) is a
choice not yet settled.

## What is exact and what is a window's

- A full walk's results and what a checkpoint names are exact. What a window shows is best
  effort, in a way the user can predict: enough to judge what the full walk will give.
- A row a walk made is exact when the rows it reads, by the reach each tool upstream declares
  summed along the chain and cut off at the ends of its extent, lay inside the walk's range and
  were themselves exact. Any other row is the window's. No tool declares more for this than
  its reach.
- An exact value has the address below. A window's value has an address that also holds the
  range it was made over, is held in memory only, and no checkpoint names it.
- A window's value never answers a full walk, a checkpoint's fill or a bare walk. An exact
  value answers a window. A window is answered again by its own values only for the same range.
- What a loop displays is a proxy when the planes it shows do not fit free memory: a small
  picture made from the exact plane as its row is made, held in memory, addressed apart from
  every value, and never handed to a tool. A tool reads decoded frames and exact planes only.
- (open: a csv written from a window's card is the window's; whether the card says so.)

## The address

- A caller addresses a result by a key and a row. The key is `plan.py`'s. A result with no rows
  has one address.
- A key holds everything the value depends on and nothing else: the tool's name, the digest of
  its code, the params its run reads, the keys of what it reads, the footage's print, and what it
  read of the cut it was made inside: an edge of the cut only where its reach met it. Two values
  under one address are equal. (open: a cut baked to a clip is
  encoded; if baking it twice gives other pixels, what was made from the first bake does not
  outlive it, and the bake is kept as long as a checkpoint names what was made from it.)
- The footage's print changes when the file's bytes change anywhere in it, to the odds its
  sampling gives, and costs no more than a seek's worth of time to make.
- A chunk is how the disk packs the rows of a key: consecutive rows on a grid sized by the bytes
  of the node's own row and not by a count. The grid is part of an entry's name, so entries of
  two grids are never taken for one another. No caller names a chunk.
- A stepped tool's row depends on the rows before it in its cut: its reach before has no bound.
  A full walk makes its rows in order from the cut's first row or from the end of the last chunk
  held, and those are exact; a window starts it at the window's first row, and those are the
  window's.

## The store

- There is one store. It answers `get`, `put`, `covered` and `drop`, and nothing holds a result
  but through it: not the walk, the window, a tool or a card.
- It has a memory tier and a disk tier. A caller does not say which and cannot tell which
  answered, but by time.
- A `put` carries the seconds the value took to make, its inputs' making among them.
- Memory holds no more than the memory budget less what work under way has reserved. It lets go
  of what saves the fewest seconds a byte first. A row looked at is held in memory only. A plane
  a walk passes through is held only into free memory and pushes nothing out.
- Disk holds no more than the disk budget, parts and manifests counted. It takes at once what
  cost many times its own write to make, whatever its kind; a value that cost at least its write
  is taken the second time it is made, and only into free room. It lets go, for what it must
  take, of what was touched longest ago, and of what a crash left behind once that is old.
- Letting go on disk, and a checkpoint's look at its entries, happen under one lock of the
  folder's, so neither falls between the other's reading and its acting. Nothing else waits on
  the lock.
- An entry lands whole or not at all: by a write to a name no other writer uses, flushed, and
  one rename. It carries its length and a checksum, and a read that finds either wrong finds no
  entry. (open: an append to a log whose reader stops at the first record that does not read,
  as `held.py` does now, for tables.)
- A file another process holds open, which Windows will not rename over or delete, is passed
  over and not an error.
- Dropping any entry no checkpoint names changes how long an ask takes and nothing else.
- Two stores open on one folder, in two processes or on two machines, are one store on disk.
- The store says what it does to the monitor's stream: a hit by tier, a miss, a put, a letting
  go, a refusal. No tool and no caller emits for it. (open: nothing checks this yet.)

## A checkpoint

- A checkpoint is a manifest: a name, a snapshot of the document, and the addresses of the
  results the user asked to keep. What it names is written to disk whatever the policy thinks
  of it. It lands as pending before its entries are filled, so filling one lets go of no other,
  and is finished after a look that finds them all.
- The store never lets go of an entry a manifest names, in memory pressure or disk pressure;
  when the disk budget cannot hold what the manifests name, a new checkpoint is refused with the
  figures before any of it is made, and nothing already named is lost.
- A checkpoint is let go by name, and its entries are then as any others.
- A checkpoint is served only under its own keys. After an edit upstream its entries are still
  on disk and are not answered for the new keys; restoring the snapshot brings back the keys
  they answer. A checkpoint made of other footage, or of other code where code is in the key,
  answers nothing, and is said to by name.
- An entry a finished manifest names that is gone or not whole is said to be gone, by the
  checkpoint's name, at open.

## The ask

- Anything that needs a result asks for it: the window, a clip walk, a bare walk, a cluster job,
  a csv write, a tool that reads another's whole result (a gate), a node served from a file. It
  is answered from the store or by computing, and the caller cannot tell which but by time.
- Computing reserves the memory its output and its live inputs take, asks for what it reads,
  puts what it made, and returns it. A missing input is made, never waited on. A value is alive
  under a reservation or in the store and nowhere else.
- A look at one row makes that row. A window makes its rows, in order, once; a loop over it
  makes nothing again. A full walk makes chunks.
- An ask the user is looking at is answered before one that is not. (open: nothing does this yet.)
- Inside one clip, work is given the few cores it gains from. Cores past that go to pieces that
  share nothing, a process each, which the store's many writers allow; a process started as one
  of N takes one Nth of the memory budget. (open: how a walk is
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
