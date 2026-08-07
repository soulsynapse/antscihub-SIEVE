---
title: cut_to_ready is the one pre-pipeline ceiling nothing can measure
status: open
phase: 6
priority: normal
gated_on: nothing
opened: 2026-08-07
---

# cut_to_ready is the one pre-pipeline ceiling nothing can measure

06.3 put a clock on three of the four pre-pipeline budgets and stopped at this
one. `cut_to_ready` is 200 ms from confirming a cut to the session being ready
to work on it, and there is no headless gesture that corresponds to it:
confirming a cut writes a crop artifact, `pipeline/materialize.py` is the thing
that writes it, and the command that drives that from a terminal is still
`todo/the-materialize-command-derives-what-v2-was-handed.md`. Measuring it
through `materialize` directly would be a benchmark inventing its own definition
of the gesture, which is the failure `budgets.TIMED` exists to make visible
rather than to paper over.

Two things have to be decided together, and that is why this is one item rather
than a line in the benchmark. First, what a cut *is* when nothing has a window:
v2's 200 ms anchor is "a click with a state change, not a render", so the
interval plausibly ends when the session can render over the new source rather
than when the file is closed — and an FFV1 encode of a real clip is not a
200 ms operation, which would make the ceiling one about the *handoff* and not
about the write. Second, whether the interval belongs to the crop path at all:
VISION's pre-pipeline regime runs to "replicates cut and a stretch selected",
and selecting a stretch is `PreviewSession.set_window`, which is free.

Whichever it is, the answer lands as a `within_budget("cut_to_ready", ...)`
call site in `tests/bench/`, the key joins `budgets.TIMED`, and this item's
sentence in that set's comment is deleted rather than left true.
`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md` holds the reading
the other three took.
