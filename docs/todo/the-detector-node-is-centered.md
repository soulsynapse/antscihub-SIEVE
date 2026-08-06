---
title: The detector node is centered, and the graph carries it
status: deferred
opened: 2026-08-05T22:56:16-07:00
priority: high
gated_on: >
  a windowed kernel that can be handed a span with frames on both sides of its
  target. `a-kernel-that-sees-a-span` settled the trailing shape — the executor
  sizes the span as refined warmup plus the current frame, and `FrameSpan.target`
  is its last frame — so look-ahead is a widening of that protocol and an item
  nobody has written. Until it exists, a detect node in the graph computes
  something the saved field does not mean, and there is nothing to migrate to.
reads: [src/sieve/filters/detect.py, src/sieve/pipeline/upgrade.py, src/sieve/gui/detector_worker.py]
after: [the-graph-carries-the-crop-the-span-and-the-detector]
---

# The detector node is centered, and the graph carries it

The half of the v6 migration that could not go with the other half. `Project.
detector` and `Replicate.detector_overrides` survive that commit; this is where
they leave, and `pipeline/upgrade.py`'s `carry_into_graph` stops refusing them
by name.

**Why not now, precisely.** `detect_cpu` is a `Mode.WINDOWED` kernel handed a
`FrameSpan` and asked for the gate at `span.target` — trailing and causal.
`Project.detector` means what `filters/detect.py`'s own `detect_series` adapter
does: the Morlet transform over the whole collected series, gated with
`centered=True`. `detection-is-a-filter` settles that the two must not be
substituted for one another, so a detect node synthesized from the saved field
today would emit a plausible channel of the right length computed from the
wrong window — the migration's named failure mode arriving through the one
field the GUI/CLI parity diff cannot see it in, since after the flip both front
ends would be claiming from the same new semantics. `carry_into_graph` refuses
rather than approximating, which is rule 6 and R2's posture both.

So the gate is a kernel protocol question, not a scheduling one. What unblocks
this is a windowed kernel that can be given lead-in *and* look-ahead around its
target, and that is not a parameter change: the executor walks `decode_range` in
order and hands each node the frames it has already seen, so look-ahead means
the yield lags its own decode by half a window. `a-kernel-that-sees-a-span`
settled the trailing shape; this is the first caller with a reason to widen it,
and widening it is its own item.

**The second problem, which the protocol does not solve.** `DetectParams.fps`
is a source fact and no document records it —
`2026.08.05-exact-source-frame-rate.md` settles that the rate is the container's
own rational, probed off the stream. A document-to-document upgrade can only
take it from a sibling node's params (`block_signal`, `temporal_baseline` and
`motion_history` each declare a float `fps`) or from the field's default of
30.0, and the default is silently wrong for the whole NTSC family in the
direction that moves the Morlet bank and therefore what is claimed as an event.
Reading it out of the graph is correct for every project that exists and is
correct by luck, not construction. Decide which before writing the synthesis:
either the upgrade refuses a document with no fps-bearing node, or `fps` stops
being a params field and becomes something the plan supplies from the bound
source — and the second is the larger and probably the right answer, since three
other filters carry the same duplicated fact.

Done looks like: `carry_into_graph` synthesizes a detect node, the two fields
are off the model, `DetectorState` has nothing left to mirror
(`detector-state-dies`), and an equivalence test diffs claimed intervals from a
v5 fixture through the old adapter against the same document through the graph
— the shape `tests/integration/test_upgrade_run.py` already has for pixels.
