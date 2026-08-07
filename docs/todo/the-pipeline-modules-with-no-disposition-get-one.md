---
title: The pipeline modules with no disposition get one
priority: high
phase: 2
status: open
gated_on: nothing
opened: 2026-08-07
---

# The pipeline modules with no disposition get one

PLAN.md's port disposition rules on six of v2's fourteen `pipeline/`
modules. These have no verdict in either direction, and four of them are
reached by `sieve run`:

| Module | Who reaches it in v2 |
|---|---|
| `cache.py` | `run_cmd`, `preview_cmd` — `FrameStore`, `MemoryFrameStore`, `NullFrameStore` |
| `resolve_source.py` | `run_cmd`, `preview_cmd`, `cli/common.py` |
| `source_home.py` | `run_cmd`, `preview_cmd` |
| `lowering.py` | `cli/common.py`, and `decode/` is the thing lowered into |
| `series_collector.py` | what turns a run into the series a graph is drawn from |
| `crop_binding.py` | the crop-as-contract handoff Phase 7 generalizes |

Also unruled: `core/replicates.py`, `bench/sweep.py`,
`bench/retention_trace.py`.

A verdict per module, in PLAN.md's disposition where the others live. The
one that matters most is `series_collector.py`: VISION's loop is a graph
refilling faster than the video plays, and nothing in the plan currently says
where the series comes from — 02.5 gets away with it because one tool's
output is one array, and Phase 6 will not.

`crop_binding.py` and `replicates.py` are entangled with decisions already
made (`adr/core-membership-is-closed.md`, Phase 7's handoff services) and are
each a paragraph, not a table row.
