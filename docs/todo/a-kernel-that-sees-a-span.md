---
title: A kernel that sees a span — Mode.WINDOWED runs
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
after: [declarable-but-not-runnable]
reads: [src/sieve/backend/dispatch.py, src/sieve/core/filter_base.py, src/sieve/pipeline/executor.py]
---

# A kernel that sees a span — Mode.WINDOWED runs

The protocol widening, unblocked 2026-07-29 by the channel-versus-intervals
decision (REWORK.md ## Decided): **the detection filter emits a per-frame
channel**, so the windowed kernel signature is span-in, frame-shaped-out, and
the uniform contract holds. The refusal set in `unrunnable_reason` shrinks by
`Mode.WINDOWED` in the same commit the execution lands.

The precedent to follow is `MergingKernel`: the second signature `Kernel`'s
docstring declined to invent early, arrived with the filter class that needed
it, added without breaking the first — `_bind` dispatches on the spec, and
protocols here extend rather than lock. Detection is the arrived case
(REWORK.md R2: do not wait for a filter the current protocol makes impossible
to write); `motion_history`'s docstring names `Mode.WINDOWED` as what it
actually wants, so it is the second consumer.

Rule 6's obligations ride along and are stated where the work is: a windowed
kernel's settled frontier (what `settled_for`/`gate_to` compute in the GUI
today) belongs to the execution contract — the executor must know which
frames of a windowed output are founded — though the GUI code moves later
(`rule-sixs-frontier-moves-into-the-contract`). Warmup arithmetic for
windowed filters must go through the existing fold; a plain sum under-warms
behind a decimator while rendering a plausible frame.

`a-kernel-that-changes-the-rate` (rate_changing execution) stays a separate,
deferred item: its arithmetic is fully built and its consumer (a decimator)
does not exist yet.
