# The contract: one address, one store, one ask

Stage 2 of `docs/playground/JOURNAL.md`. Each line is an assertion that holds of the built thing.
`docs/playground/sim/` is this contract in code, and where the two differ the simulation is right
and this file is behind. A line marked (open) is a choice the simulation is to settle.

## The address

- A result is addressed by a key and a chunk: the key is `plan.py`'s, the chunk is a run of
  `CHUNK` consecutive rows on a grid fixed for the key. A result with no rows has one chunk.
- A key holds everything the value depends on and nothing else: the tool's name, the digest of
  its code, the params its run reads, the keys of what it reads, the footage's print, and the cut
  it was made inside. Two values under one address are equal.
- A stepped tool's chunk depends on the chunks before it in its cut. Its address is the same; the
  ask makes its chunks in order from the cut's first row or from the last one held. (open: a
  stepped tool's state at a chunk's end is kept beside the chunk so a walk resumes there.)

## The store

- There is one store. It answers `get(address)`, `put(address, value)`, `covered(key)` and
  `drop(address)`, and nothing holds a result but through it: not the walk, the window, a tool
  or a card.
- It has a memory tier and a disk tier. A caller does not say which and cannot tell which
  answered, but by time.
- The memory tier holds no more than the memory budget, counted by the bytes of what it holds.
  A `put` that would pass the budget lets go of entries first, by the policy (open), and an
  entry larger than the whole budget goes to disk alone or is refused with a reason.
- The disk tier holds no more than the disk budget. An entry lands by a write to a name no other
  writer uses and one atomic rename to the address's name; a reader sees a whole entry or none.
  A file that is not whole is no entry.
- Dropping any entry no checkpoint names changes how long an ask takes and nothing else.
- Two stores open on one folder, in two processes or on two machines, are one store on disk.
- The store says what it does to the monitor's stream: a hit by tier, a miss, a put, a letting
  go, a refusal. No tool and no caller emits for it.

## A checkpoint

- A checkpoint is a manifest: a name, a snapshot of the document, and the addresses of the
  results the user asked to keep. It lands as an entry does.
- The store never lets go of an entry a manifest names, in memory pressure or disk pressure;
  when the disk budget cannot hold what the manifests name, a new checkpoint is refused with the
  figures, and nothing already named is lost.
- A checkpoint is served only under its own keys. After an edit upstream its entries are still
  on disk and are not answered for the new keys; restoring the snapshot brings back the keys
  they answer.
- An entry a manifest names that is gone or not whole is said to be gone, by name, at open.

## The ask

- Anything that needs a result calls `demand(address, priority)`: the window, a clip walk, a
  bare walk, a cluster job, a csv write, a tool that reads another's whole result (a gate), a
  node served from a file. It is answered from the store or by computing, and the caller cannot
  tell which but by time.
- Computing an address demands what it reads, puts what it made, and returns it. A missing input
  is made, never waited on.
- An ask the user is looking at (a scrub, the window) is answered before one that is not (a clip
  walk, a checkpoint being filled).
- Work is given cores up to the core budget; asks whose addresses do not depend on one another
  run at once. (open: how the budget is split between decoding and tools.)

## The budget

- Memory, cores and disk are three figures read off the machine at start and overridable. No
  other constant in the player bounds a holder.
- A budget too small for one row's work is said with the row's need and the budget, and the
  player goes on.

## What a tool does about any of this

- Nothing. A tool declares what `registry` already reads; its code's digest and its params reach
  the key through the plan. Adding a tool, or a tool that reads another's whole result, changes
  no file of the store, the ask, the walk or the monitor.
