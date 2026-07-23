# Next steps

Last reviewed: `2026-07-23 16:12:57 -07:00`.

This file records unfinished work that is justified by the current checkout.
It is not authorization to continue automatically into later Isolate
milestones.

## Current priority

### Validate and accept the first intensity channel

Source:

- `docs/handoffs/5-First-channel.md`
- `docs/handoffs/5-First-channel-review.md`
- `docs/handoffs/.isolate-state-divergence.md`

Milestone 4 was accepted when the user authorized milestone 5. The first
channel now provides:

- A Qt-independent post-decoder RGB601 intensity computation with exact area
  downsampling and partial-cell-aware block means.
- Exact retained-result admission before source construction through a portable
  policy with 16 GiB CPU and 6 GiB GPU defaults; execution remains CPU-only.
- A worker-owned request-local source, cancellation, verified shutdown,
  latest-only pending work, and stale-publication rejection.
- One fixed-scale time-by-block raster with absolute-frame cursor,
  click-to-seek, and spatial hover context.
- Immediate invalidation on asset, window, downsample, or block changes without
  automatic recomputation.

Automated validation:

```text
Focused intensity, GUI, and player suites: 39 passed
Complete offscreen suite: 135 passed in 25.46s
```

Remaining:

1. Open a representative registered asset and choose a short window.
2. Compute intensity and inspect the fixed `[0,1]` time-by-block raster.
3. Play, scrub, step, and click raster columns to confirm exact cursor/seek
   synchronization without recomputation.
4. Change the window and grid, then switch assets; confirm obsolete results
   disappear immediately.
5. Start, supersede, cancel, and close during work; confirm no stale or partial
   result is presented as current.
6. Accept milestone 5 or report visible/scientific interaction changes.

Do not begin normalization or a second channel during this validation step.

## Planned foundational product surface — no current implementation authorization

### Design compute resources and execution policy

Source:

- `docs/decisions/003-compute-resources-are-a-first-class-product-capability.md`
- `docs/decisions/001-reusable-benchmarks-are-product-diagnostics.md`
- `docs/decisions/002-headless-scientific-identity-is-not-gui-lifecycle.md`

Available compute resources are a first-class product capability and the basis
for keeping SIEVE HPC-ready. Plan a dedicated **Resources** surface, likely a
top-level tab before Replicates, without coupling the underlying contracts to
Qt or to one workstation.

Concrete later work:

1. Define immutable Qt-free capability-report and execution-policy schemas.
2. Separate observed capability from selected policy, with timestamps,
   provenance, refresh behavior, and explicit staleness.
3. Inventory CPU topology and compute backends, memory, GPUs,
   drivers/backends, and media capabilities.
4. Add supported, bounded diagnostics for relevant source, result, temporary,
   and scratch-path read/write performance.
5. Let users configure memory admission, thread/process counts, device/backend,
   concurrency, and scratch placement.
6. Provide guided CPU and GPU compatibility, backend selection, parallelism,
   and setup/use workflows rather than merely listing devices.
7. Design the Resources tab placement, recommendation/override interaction,
   and clear distinction between cheap automatic inventory and explicitly run
   expensive diagnostics.
8. Make resource profiles exportable/importable for later CLI, remote, and HPC
   execution, including scheduler/container/scratch facts when those runners
   exist.
9. Define how job admission combines current availability, configured limits,
   peak-buffer estimates, retained results, storage, and backend constraints.

Milestone 5 is the first consumer: its retained-result limit should enter
through a minimal portable resource-policy seam. Do not implement the complete
Resources tab, CPU/GPU executors, scheduler integration, or general job planner
as part of that channel milestone.

## Follow-up diagnostic

One full-suite run intermittently reached
`test_delete_removes_a_missing_child_record_without_deleting_its_files` with a
derivation child record lacking `media_path`, causing the test to report a
`KeyError` instead of the underlying derivation status. The test passed
immediately in isolation and the next complete run passed all 115 tests.

If this recurs, capture the returned child status/error before indexing output
paths and decide whether the derivation fixture needs a bounded retry or a
clearer failure assertion. This is unrelated to working-grid behavior, but the
current `KeyError` masks the actionable cause.

## Deferred work — no current implementation authorization

Do not begin these merely because the working-window source and working grid
are complete:

- Add normalization or a second scientific channel.
- Generalize the concrete intensity worker/panel into a channel registry,
  graph, or cross-channel scheduler before another measured use requires it.
- Add additional media planes or a plane registry.
- Add scientific result persistence, recipes, export, CLI/HPC processing, or a
  general graph executor.

When the first real channel handoff arrives, evaluate the benchmarkable
multi-basis channel contract proposed in
`docs/ideas/processing-ideas.md`. Do not add direct grayscale delivery or a
general plane registry before a real channel and measurement justify them.

The milestone-5 review found that commit `0f4afb2` has implementation-shaped
metadata but contains documentation only. Do not use its commit subject as
evidence that intensity exists.

Milestone 5 implemented the minimal Qt-free resource policy and first intensity
channel. Manual acceptance is now the gate. Stop before normalization or a
second channel.

The oracle handoff for each later milestone must be reviewed against the
then-current checkout and recorded in
`docs/handoffs/.isolate-state-divergence.md` before implementation.
