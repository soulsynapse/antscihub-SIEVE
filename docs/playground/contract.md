# The contract: one address, one ask

The design, each line an assertion that holds of the thing once built; a line here is no evidence
about the tree. A line marked (open) is a choice not yet settled. The lines of one store under
every holder are gone with the store; `docs/findings/2026-11-27-one-store-was-simulated-and-taken-out.md`
holds what they were and why.

## What is exact and what is a window's

- A full walk's results and what a checkpoint names are exact. What a window shows is best
  effort, in a way the user can predict: enough to judge what the full walk will give.
- A row a walk made is exact when the rows it reads, by the reach each tool upstream declares
  summed along the chain and cut off at the ends of its extent, lay inside the walk's range and
  were themselves exact. Any other row is the window's. No tool declares more for this than
  its reach.
- A window's value is held in memory only, and no checkpoint names it. It never answers a full
  walk, a checkpoint's fill or a bare walk. An exact value answers a window.
- What a loop displays is a proxy when the planes it shows do not fit free memory: a small
  picture made from the exact plane as its row is made, held in memory, addressed apart from
  every value, and never handed to a tool. A tool reads decoded frames and exact planes only.
- (open: a csv written from a window's card is the window's; whether the card says so.)
- (open: a cutting tool declares no reach over the result that cuts it, so a cut made of a
  window's rows of that result is taken for whole where the tool reads past them.)

## The address

- A caller addresses a result by a key and a row. The key is `plan.py`'s. A result with no rows
  has one address.
- A key holds the tool's name, the params its run reads, the keys of what it reads, the footage's
  print, and what it read of the cut it was made inside: an edge of the cut only where its reach
  met it. A tool's code is in no key: a result made under other code is found and marked.
- (open: a cut baked to a clip is encoded; if baking it twice gives other pixels, what was made
  from the first bake does not outlive it.)
- A stepped tool's row depends on the rows before it in its cut: its reach before has no bound.
  A full walk makes its rows in order from the cut's first row, and those are exact; a window
  starts it at the window's first row, and those are the window's.

## The ask

- Anything that needs a result asks for it: the window, a clip walk, a bare walk, a cluster job,
  a csv write, a tool that reads another's whole result (a gate), a node served from a file. It
  is answered from what is held or by computing, and the caller cannot tell which but by time.
- A result a cutting node is cut by is asked for as any other is: held, it cuts; not held, the
  window's walk of it cuts provisionally, over the footage or inside a cut in time alike.
- (open: a held result that cuts a node is read by the plan, so letting it go changes what is
  computed and not how long it takes; whether it is held as the document's and never let go for
  a budget.)
- A look at one row makes that row. A window makes its rows, in order, once; a loop over it
  makes nothing again.
- An ask the user is looking at is answered before one that is not. (open: nothing does this yet.)

## The budget

- Memory, cores and disk are three figures read off the machine at start and overridable. No
  other constant in the player bounds a holder.
- A budget too small for one row's work is said with the row's need and the budget, and the
  player goes on.

## What a tool does about any of this

- Nothing. A tool declares what `registry` already reads; its params reach the key through the
  plan. Adding a tool, or a tool that reads another's whole result, changes no file of the ask,
  the walk or the monitor. `sim/miniature.py` asks it of cutting tools by `MINIATURE_CUTTER`.
