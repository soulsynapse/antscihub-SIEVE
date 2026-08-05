---
title: A position is not a count, and an index belongs to one stream
status: open
opened: 2026-08-04T22:09:46-07:00
priority: normal
gated_on: nothing structurally
reads: [src/sieve/pipeline/plan.py, src/sieve/core/types.py, src/sieve/pipeline/resolve_source.py]
after: [four-numbers-four-types]
---

# A position is not a count, and an index belongs to one stream

The fifth type the four implied and did not build. `FrameCount` separated a
lead-in from a duration; it did nothing about the other confusion in the same
expression, which is `pipeline/plan.py`:

    return max(self.span.start - self.lead_in.frames, self.source_start)

The `.frames` is where a count becomes a position by hand, and nothing checks
the direction. `span.start + span.end` typechecks and means nothing.
`decode_start - source_start` is a count wearing an `int`, and
`lead_in_shortfall` reconstructs one with a `FrameCount(...)` wrapper around a
subtraction of two positions.

The sharper half is not index-versus-count, it is **which stream's numbering**.
`source_start` exists because a crop artifact's frame 0 *is* source frame 40
(`pipeline/resolve_source.py`), so `ExecutionPlan` already holds positions from
two origins in the same `int` type and keeps them apart by naming discipline.
`Frame.index` downstream of a rate-changing node is a third space. Every one of
those is an `int` today and any two of them add.

Done looks like: a `FrameIndex` in `core/types.py` beside the four, where
`index - index` is a `FrameCount`, `index + count` is a `FrameIndex`, and
`index + index` does not typecheck. `decode_start`, `decode_range`,
`source_start` and `Frame.index` carry it.

**Answer the origin question, do not assume it.** The recommendation is *one*
`FrameIndex` with no origin marker, not a phantom-typed `FrameIndex[Source]`.
The crop-artifact case is already handled by `decode_start` clamping at
`source_start` — the discipline works and the type would only restate it — and
a phantom parameter would oblige the executor to name a coordinate space at
every call site, including the many where there is only ever one. Reopen it
when a rate-changing node's *output* is addressed by index rather than
streamed, which is `the-executor-stops-cutting-frames`' territory, not this
item's.

**`ClipRange.start` and `.end` stay `int`, and the conversion happens at the
artifact boundary** — the same shape as the three CLI sites that unwrap
`.frames` for display. They are saved-schema fields, and REWORK.md's ordering
constraint puts the saved-graph changes in one migration commit rather than
four; this item is not that commit. If retyping them turns out to be free
(a pydantic serializer that still writes a bare int), it is still the
migration's call and not this one's.

The check that would fail if it regressed: `span.start + span.end` stops
typechecking, `decode_start - source_start` is a `FrameCount` without a
wrapper, and `lead_in_shortfall` is built by subtracting two positions rather
than by re-wrapping the result of one.
