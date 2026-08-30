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
- **`gray` is the decoder's luma plane.** Settled against the oracle rather
  than against the argument: `forms.py` claimed the construction for every
  format and was never run, the session explorer took plane 0 and every
  measured number on the storage shelf came out of frames that did. `forms.py`
  keeps which source pixels at what sampling; what a pixel *is* belongs to
  whoever produced it. Refusing gray had made a crop cost more than the whole
  frame it was cut from. The video source is version 2 for it (ADR-0010).
- **Window fill and write-behind chunks.** `sieve/fill.py` and
  `sieve/chunks.py`, ported from the session explorer with its ordering, its
  complete-chunks-only rule and its two stop speeds. A fill reads through its
  own opened source, borrowed from a pool, because an open here is ADR-0004's
  whole demux pass and not a container. `av` became a SIEVE dependency for
  SIEVE's own cut and nothing else — `sieve/` names no container and demuxes
  nothing, which is the line ADR-0009 actually draws.
- **A drawn crop, and the invalidation a form change needs.** The crop is what
  makes a window holdable at all, and drawing one is what gives the
  invalidation path a caller.

- **The route table.** `sieve/serve.py`: the tiers of one open recording in
  one place, and a serve that names which one answered. The window kept the
  two things that are its own — a drag may not block, and what a route means
  for a canvas — and gave up the ordinal snapshot, the chunks and the filled
  span. `HOLD` and `GONE` are opposite instructions and were being told apart
  by re-deriving a refusal.

- **The display proxy.** `sieve/proxy.py`, which is the chunk store and the
  window fill at a coarser form over the whole extent, anchored at attention
  and redirected on landing. It needed `forms.build` to stop refusing to
  resample — a refusal that was argued where `tool-experiments/forms.py` had
  already settled the construction and the grade.

  What each of those cost is in the commit messages that landed them, which is
  the wrong shelf for it — a finding is owed here and none has been minted.
  The proxy's is the most owed: it moved a drag outside the filled window from
  the source's seek to a cut's random access, and it found two defects in the
  chunk tier that a window fill cannot reach.

## Next, in order

**1. The step contract.** `contract/nodes.py` says one contract per tool type
and a source is the first. `experiments/tool-experiments/tools.py` is the
shape: a form that is a function of the crop, the offsets a step admits, its
reach, its key. Cost class stays computed and never declared (ADR-0007). It
was gated on the loop being fast enough to feel — a step contract designed
against one that is not is the mistake tool-experiments' post-mortem records
— and that gate is now open in the substrate and not yet in the hand. What
is owed before this is a driven session rather than more code: every route
was timed by a script, and what the gate was about is the loop under a
person's cursor.

The keyframe strip was first in the storage plan's tier list and is no longer
urgent: `Output.starts` removed the reason, and the display proxy is now the
tier a filmstrip would be drawn from. It is a transport concern and folds
into the step contract rather than standing before it.

## Waiting on a decision that is not the code's

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
  trigger has arrived and has not fired: the fill asks position by position,
  and the video source's own cursor rule already turns an ascending run into
  forward decoding, so a batch read would save the seek at a chunk boundary
  and nothing else. It fires when a tier asks for positions that are *not*
  ascending — the display proxy's fill, or a step reaching across offsets.

## Untested cases, named so they are not discovered by a user

- **The undeliverable tail.** The session explorer drops a GOP from its total
  because the last one's decodability is not guaranteed. `starts` may list a
  keyframe there, and nothing has asked.
- **An extent growing while somebody watches.** `Store.positions` re-asks, so
  growth is visible to anything that looks — and nothing re-polls, so a folder
  being written into does not lengthen its own strip.
- **A landing while a chunk of the same window is still encoding.** The
  explorer priced both halves of that seam solo and the overlap not at all,
  and nothing here has driven it either. The writer's queue is the seam.

- **Three readers of one recording at once.** The window fill, the proxy
  build and the drawing thread all borrow from the same pool now, where the
  measured case was two
  (`findings/2026.08.21-software-decoders-collapse-under-contention.md` is
  the shape of what a third could cost, and it was not measured on this
  pairing).

- **A session killed rather than closed leaves its scratch behind**, and a
  whole-file proxy is a much larger thing to leave than a 300-frame window.
  Nothing sweeps a dead process's directory. `nodes.py`'s granted scratch
  space is where this belongs and it does not exist.

- **A write-behind that fails every chunk reports nothing.** `WriteBehind`
  swallows an encode exception so one bad chunk re-derives rather than
  killing the writer, which is right; a build where *every* encode fails
  looks identical to one making no progress, which is how a broken partial
  rename survived a full run. There is no logging facility to fix it with.
- **A second recording opened over a filled one.** `_close_source` stops the
  fill, closes the readers and destroys the chunks in that order; the order is
  argued and has not been driven with a fill actually running.
- **An extent growing while somebody watches.** `Store.positions` re-asks, so
  growth is visible to anything that looks — and the window now snapshots the
  listing at open to have an ordinal table at all, so a folder being written
  into does not lengthen its own strip *or* its own grid. The snapshot is the
  new half of this.

Struck from this list: a form change had no counterpart and now has one, in
`_apply_crop` — stop the fill and wait for it, drain the writer, wipe the
frames, move the chunk generation, then move the rect. It is driven.
