---
title: The live column holds one spelling per dead word
status: open
priority: normal
phase: 4
gated_on: nothing
opened: 2026-08-07
---

# The live column holds one spelling per dead word

`DEAD_IDENTIFIERS` in `tests/unit/test_tool_id_spelling.py` matches a dead word
as a case-insensitive substring with no boundary, and the escape hatch is a
single live spelling per row that is stripped before the search. That was
sufficient while the only row was `filter`, whose collisions in v3 are rare. The
`clip` row added at 02.2 is a different case: `np.clip` is the ordinary way to
bound an array, and `rescale`/`normalize` (04.3) are the tools most likely to
reach for it — as would any clamp in `core/ops/`. `clipped`, `clipping`, and
`np.clip` all fire, and the exception list cannot absorb them because
`test_the_exception_list_is_empty` asserts it stays empty for a reason that is
still right.

One live slot cannot hold `np.clip` *and* `clipped`, so the first real
collision is a change to the table's shape, not a row edit — the live column
becoming a tuple of spellings, or the match gaining word boundaries with the
substring case handled per row. Decide which when the collision arrives and
there is a real line to test against; deciding now would be picking a shape for
a call nobody has written. The failure mode if it is not decided is worse than
noisy: the cheap way out under a red gate is to rename a legitimate `np.clip`
call, which makes the array math worse to read in order to keep a rename gate
green.
