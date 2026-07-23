# Next steps

Last reviewed: `2026-07-23 15:53:49 -07:00`.

This file records unfinished work that is justified by the current checkout.
It is not authorization to continue automatically into later Isolate
milestones.

## Current priority

### Validate and accept the implemented working grid

Source:

- `docs/handoffs/4-Working-grid.md`
- `docs/handoffs/4-Working-grid-review.md`
- `docs/handoffs/.isolate-state-divergence.md`

Implementation now provides:

- A Qt-free immutable working-grid contract with deterministic dimension
  resolution, tagged auto/explicit block intent, compact block ownership,
  partial-edge bounds and area weights, and boundary projection.
- Isolate-local downsample and block controls whose plain settings value is
  retained across asset switches and reset only on application restart.
- A resolved source/working/block/grid/edge readout.
- A toggleable presentation-only player overlay mapped through the existing
  letterboxed `image_rect()`.
- Dense-grid suppression that preserves the true geometry and outside boundary
  without generating thousands of internal lines.
- Spatial controls on one-frame assets without coupling them to `can_loop`.
- No working-window decode, display-decoder request, worker, persistence, cache,
  channel, result, or coverage artifact on geometry changes.

Automated validation:

```text
Focused grid/player suites: 39 passed in 2.37s
Complete offscreen suite: 115 passed in 23.71s
```

Remaining:

1. Open a representative registered parent and child or two replicate assets.
2. Confirm the controls/readout placement is readable at the normal window
   size.
3. Toggle the grid and verify alignment while resizing and scrubbing.
4. Change downsample and block intent, then switch assets and confirm the
   requested intent remains while dimensions and edge cells re-resolve.
5. Confirm a dense grid shows its bounded presentation indication without
   affecting playback.
6. Accept milestone 4 or report visible interaction changes.

Do not begin a channel during this validation step.

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

- Implement the first scientific channel. Its oracle handoff and review have
  now been reconciled with the current checkout in
  `docs/handoffs/5-First-channel.md`,
  `docs/handoffs/5-First-channel-review.md`, and the divergence ledger. The
  corrected path is queued behind visible milestone-4 acceptance.
- Add a GUI computation worker, latest-only publication, or cross-thread queue.
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

Before milestone-5 implementation, confirm milestone-4 visible acceptance.
Define the minimal Qt-free resource-policy input and select its initial
in-memory result-budget value/default under decision 003. Then implement only
the corrected first-channel increment, including pre-source result-memory
admission, source-outcome composition, and a worker-owned source lifecycle.
Stop before normalization or a second channel.

The oracle handoff for each later milestone must be reviewed against the
then-current checkout and recorded in
`docs/handoffs/.isolate-state-divergence.md` before implementation.
