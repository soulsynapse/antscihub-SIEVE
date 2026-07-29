---
title: A filter never says what one element of its output means
status: open
priority: high
opened: 2026-07-28
gated_on: >
  nothing — `sieve detect --node` already mislabels today, and the CSV export
  ships the mislabelling to disk where it outlives the session
reads:
  - src/sieve/core/filter_base.py
  - src/sieve/detect/tables.py
  - src/sieve/cli/detect_cmd.py
  - docs/todo/kernel-protocol-beyond-one-frame.md
---

# A filter never says what one element of its output means

`ArraySpec` declares dtype and channel layout — enough to reject a graph that
cannot run, which is what it was built for. It says nothing about what one
*element* of an emitted frame is. `block_signal` emits one float per block of
the source; `downsample` emits one float per pixel. Both are
`ArraySpec(dtypes=("float32",))` and the graph cannot tell them apart.

Nothing needed the distinction while the only consumer was the executor, which
moves arrays and does not interpret them. `sieve detect` interprets them —
`_collect` flattens any node's output into a `(T, B)` stack and the detector
counts how many of the `B` fell inside a value band — and it has been doing so
against an undeclared assumption since it was written. The CSV export
(`docs/completed-todo/2026.07.28-detection-csv-export.md`) is what made it
visible, because it writes the assumption down: a column named
`blocks_in_band`, beside `blocks_total`.

## What is already wrong

```
sieve detect rep3.sieve.yaml --node <the downsample node> --csv out/
  -> blocks_total = 52668
```

52668 is a pixel count. No refusal, no warning; the numbers are real and the
noun is invented. `--node` is documented as the way a two-sink graph says
which series a detection is taken over, so this is a supported invocation
producing a mislabelled artifact, not a misuse.

## The three that are worse, and why this is `open` and not deferred

**A circular signal.** `flow_direction`
(`docs/todo/block-signal-free-measures.md`) is the screening's other survivor,
and `inband_count` is `lo <= m <= hi`. A band from 170° to −170° is 20° wide
through the wrap and reads as empty. The count would be wrong rather than
mislabelled, and no column would say so.

**A rate-changing node.** `docs/todo/kernel-protocol-beyond-one-frame.md`'s
decimator. The export computes `frame = start + offset`, which assumes one
emitted row per source frame. Under a decimator every `frame`, every
`time_seconds`, and every interval bound is wrong by the decimation factor —
silently, and by a ratio plausible enough to survive being looked at. This is
the expensive one.

**A `TableSpec` node.** `_collect` calls `reshape(-1)` on frame data. This one
at least fails loudly.

## The shape

An element-meaning on the emitted spec — what one value *is a value of* — and
a series node that declares nothing cannot be a series node. Two properties
follow, and both are the point:

- The column names come from the pipeline instead of from `tables.py`'s
  assumption. `blocks_in_band` when the node emits blocks; whatever the filter
  says otherwise.
- Cases 1 and 4 become refusals rather than lies, which is rule 6 at the one
  boundary where a wrong answer gets written to disk and outlives the run.

Whether it belongs on `ArraySpec` or on `FilterSpec` beside `output_rate` is
the open question, and `frame_bytes_ratio`'s docstring is the argument to
read first: it is explicit that a declaration feeding a *prediction* may go
unenforced, while `output_rate` is cross-checked because it feeds a
correctness decision. Element meaning is the second kind — it decides whether
a detection is admissible at all — so it wants `output_rate`'s treatment, not
`frame_bytes_ratio`'s.

Do not solve this by renaming the columns to something shape-neutral.
`units_in_band` is a column nobody can read, and it would make the export
honest by making it useless, which is the trade rule 6 exists to refuse.
