# The vertical slice — what is built, what is next, what is waiting

The arc `v4-vertical-slice` is on: one recording, opened by a tool, through a
substrate, onto a canvas somebody can drive. This file is the order the work is
going in and why, revised as it goes; it dies when the slice closes.

It is not the other genres and does not duplicate them. What is **settled**
is in `adr/`. What was **measured** is in `findings/`, and this file cites
those rather than restating their numbers, so a later measurement supersedes
them in one place. What is **argued but untriggered** is in
`architecture-leads.md`. What SIEVE being finished *means* is
`SIEVE-CAPABILITIES.md`, which is the oracle this plan is trying to satisfy.

## The method this arc follows

Two rules, both the tree's own, and both learned the expensive way.

**Derive a contract from more than one implementation.** `decode/ideas.md`:
a protocol written from a single backend is that backend wearing an
interface's clothes. Three source tools exist so that the contract has
something to disagree with.

**A tool that does not exist may be a workload and may never be evidence.**
`experiments/tool-experiments/README.md` records designs *argued* from
invented tools failing twice and designs *tested* against them working every
time. So a contract clause is written after something breaks without it, not
before — and no clause lands without a reader. The two clauses in the tree
with no experimental backing, `Access` and `Fingerprint`, are the two that sat
unread for months, which is the correlation this rule exists to avoid
repeating.

## Done

- **The source contract and the registry.** Tools load by path, `offers`
  narrows a source to what it serves, and `tools/` cannot import a substrate
  internal — enforced by the ADR-0009 contracts in `pyproject.toml`.
- **`sieve/store.py`.** One open recording, frames keyed by position *and*
  form, the extent asked rather than stored, and only a permanent refusal
  recorded as a hole.
- **Three sources.** A video file, a folder of stills, and a synthetic
  generator whose address is not a path. What they found the contract could
  not say is
  `findings/2026.08.29-what-two-more-sources-found-the-contract-cannot-say.md`.
- **`Refusal` and `Answer`.** A refusal names its kind — never decodable,
  wrong form, not to you now — because three sources produced three that want
  opposite handling and one return value collapsed them.
- **A read names its form.** The source crops before returning; `forms` stays
  the authority on the bytes.
- **`Output.starts`.** Where a read may begin, which is structure and not cost
  (ADR-0007). It is what stopped SIEVE discovering a cut-away GOP by paying a
  seek per frame to be refused.
- **The transport.** Play, step and scrub with no pipeline on the recording —
  the first line of `SIEVE-CAPABILITIES.md`. Ported from `mockup/mockup.py`
  into `gui/view/transport/`, mapping positions to columns by ordinal so an
  invented timebase is never drawn as if it were time.

## Next, in order

**1. Window fill and write-behind chunks.** Ports `WindowFill` and
`ChunkStore` from `experiments/storage-experiments/session-explorer.py`. This
is what stops a read blocking the thread that draws, which playback currently
does. Carry attention-first ordering (fill from the playhead's chunk and wrap
after — the same decode work in a different order is the difference between a
frozen landing and a seamless one), complete-chunks-only persistence, the
per-frame encode yield, and `stop(wait=False)` on a landing against a blocking
stop on a form change. Do **not** carry `ChunkStore.fetch`'s lock, which is
held across an open, a seek and a decode; `store.py` forbids that in as many
words and gives the reason.

**2. The display proxy and the route table.** Ports `_serve`'s selection.
`Frames` still lacks `nearest`, `covered` and a batched snapshot accessor, and
all three are needed here. Keep the two-threshold subtlety: a very near cached
frame beats the proxy, a merely near one loses to it, because a right-time
low-resolution frame beats a wrong-time sharp one.

**3. The step contract.** `contract/nodes.py` says one contract per tool type
and a source is the first. `experiments/tool-experiments/tools.py` is the
shape: a form that is a function of the crop, the offsets a step admits, its
reach, its key. Cost class stays computed and never declared (ADR-0007). Not
before 1 and 2 — a step contract designed against a loop that is not yet fast
enough to feel is the mistake tool-experiments' post-mortem records.

The keyframe strip was first in the storage plan's tier list and is no longer
urgent: `Output.starts` removed the reason. A filmstrip is now a transport
concern and folds into 1 and 2 rather than standing before them.

## Waiting on a decision that is not the code's

**What `gray` means.** `forms.py` is the authority and says BT.601 over the
decoded BGR. A decoder's luma plane is a different quantity, so the video
source refuses `gray` and lets the canonical construction run after a
full-size decode. Serving the plane directly is the difference between a
whole-frame decode and a crop, and it cannot be a tool's decision: two
producers of one form must agree in the low bits. Changing it means changing
`forms.py`'s definition, which is a decision about what a form *is*.

**How a source that is not a file gets picked.** `Source.patterns` are file
globs, so neither a folder of stills nor an address with a scheme can be
offered by the chooser or reached by the + button. Both are opened today only
by calling into the window directly. Either a source says what kind of thing
to ask for and the chooser grows modes, or the address gets typed. This is
lead-shaped and belongs in `architecture-leads.md` if it is not settled soon.

## Waiting on a trigger

- **`Fingerprint`** is declared and read by nothing, and is now the last such
  clause. Its lead's trigger is the first thing written beside a recording.
- **A batch read** — one request carrying a set of positions, sorted by
  keyframe. `ideas.md` names it as one of three things a single-backend
  protocol cannot express, and `tool-experiments` lists it untried. Its
  trigger is a fill tier, which is the next piece of work.

## Untested cases, named so they are not discovered by a user

- **The undeliverable tail.** The session explorer drops a GOP from its total
  because the last one's decodability is not guaranteed. `starts` may list a
  keyframe there, and nothing has asked.
- **An extent growing while somebody watches.** `Store.positions` re-asks, so
  growth is visible to anything that looks — and nothing re-polls, so a folder
  being written into does not lengthen its own strip.
- **A form change.** Nothing changes a crop yet, so the invalidation the
  session explorer performs on one — stop the fill, drain the encode queue,
  rebuild the store, wipe the chunks, and only then move the rect — has no
  counterpart here and will be needed by the first piece of work above.
