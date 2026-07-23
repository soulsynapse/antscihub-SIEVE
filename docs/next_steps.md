# Next steps

Last reviewed: `2026-07-23 16:36:24 -07:00`.

This file records unfinished work that is justified by the current checkout.
It is not authorization to continue automatically into later Isolate
milestones.

## Current priority

### Validate and accept per-frame normalization

Source:

- `docs/handoffs/6-Normalization.md`
- `docs/handoffs/.isolate-state-divergence.md`

The user explicitly authorized milestone 6 after its rewrite review. This
superseded the sequencing gate without claiming that milestone 5 separately
received manual acceptance. The intensity path now provides:

- Immutable Qt-free `off` and per-frame population-z-score specifications.
- Fixed `1e-6` z-score epsilon, float64 population statistics, float32 science,
  finite complete-frame validation, and exact-zero degeneracy.
- One immutable uint8 degeneracy flag per processed frame, included in exact
  pre-source result admission.
- A scientific key separated from execution policy, batch size, and GUI token.
- Safe automatic replacement when normalization changes after a result/job
  exists, without overlapping source-owning workers.
- Fixed `[0,1]` Off and `[-3,3]` diverging z-score presentation with real-value
  hover readout and explicit units/degeneracy.

Automated validation:

```text
Focused intensity/normalization and GUI suites: 43 passed in 4.54s
Complete offscreen suite: 158 passed in 28.00s
```

Remaining:

1. Open a representative registered asset and choose a short window.
2. Compute with **Off** and confirm the accepted `[0,1]` raster behavior.
3. Select **Per-frame z-score** and confirm immediate old-result removal, one
   replacement job, z-score units, and fixed `[-3,3]` presentation.
4. Hover clipped extremes and confirm the readout retains the stored value.
5. Use a constant/near-constant lossless fixture and confirm exact-zero output
   is labelled valid degenerate data.
6. Play, step, scrub, and click raster columns; confirm the one player clock
   remains synchronized without recomputation.
7. Toggle modes rapidly, change window/grid/asset during work, cancel, and
   close; confirm no overlapping worker or stale publication.
8. Accept milestone 6 or report visible/scientific interaction changes.

Do not begin change energy or another channel during this validation step.

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

An earlier full-suite run intermittently reached
`test_delete_removes_a_missing_child_record_without_deleting_its_files` with a
derivation child record lacking `media_path`, causing the test to report a
`KeyError` instead of the underlying derivation status. The test passed
immediately in isolation and the next complete run passed all 115 tests.

During normalization validation,
`test_cancel_during_verification_does_not_publish_a_ready_child` also
intermittently failed when `write_json_atomic(...)` received Windows
`PermissionError: [WinError 5]` at `os.replace(temp, layout_path)`. It passed
immediately in isolation, and the following complete run passed all 158 tests.

If either recurs, inspect whether antivirus/indexing or concurrent layout
access is transiently holding the destination, then decide whether atomic JSON
writes need a bounded Windows sharing-violation retry. Separately, capture
returned derivation status before indexing output paths so a `KeyError` cannot
mask the actionable cause. This remains unrelated to Isolate normalization.

## Deferred work — no current implementation authorization

Do not begin these merely because the working-window source and working grid
are complete:

- Add change energy or a second scientific channel.
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

Milestone 6 implemented per-frame normalization through the existing intensity
path. Visible/manual acceptance is now the gate. Stop before change energy or a
second channel.

The oracle handoff for each later milestone must be reviewed against the
then-current checkout and recorded in
`docs/handoffs/.isolate-state-divergence.md` before implementation.
