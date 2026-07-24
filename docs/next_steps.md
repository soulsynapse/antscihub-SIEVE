# Next steps

Last reviewed: `2026-07-23 16:55:13 -07:00`.

This file records unfinished work that is justified by the current checkout.
It is not authorization to continue automatically into later Isolate
milestones.

## Current priority

### Validate and accept temporal change energy

Source:

- `docs/handoffs/7-Change-energy.md`
- `docs/handoffs/.isolate-state-divergence.md`
- `findings/2026-07-23-change-energy-overlay-performance.md`

The user explicitly authorized milestone 7 after its current-checkout review.
This superseded the handoff's sequencing gate without claiming that milestones
5 or 6 separately received manual acceptance. The selected-channel path now
provides:

- Exactly Intensity or Change energy through one active worker, one newest
  pending request, one retained result, and one publication token.
- One bounded predecessor context frame and explicit later-frame temporal
  alignment, with frame zero invalid rather than fabricated zero.
- Fixed float32 current-minus-previous square, sigma-2 17-tap reflect-101
  Gaussian integration, and accepted owned-pixel block reduction.
- Immutable temporal-valid, previous/current normalization-degenerate evidence
  and exact `4*T*R*C + 3*T` pre-source retained-result admission.
- Area-weighted time-by-value density with fixed scientific mappings and
  absolute cursor/seek behavior.
- One shared selected-channel overlay gated to the absolute frame actually
  decoded into the player, with independent grid/channel visibility.

Automated validation:

```text
Focused milestone-5/6/7 and player suites: 74 passed in 9.63s
Complete offscreen suite: 170 passed in 30.33s
```

Remaining:

1. Open a representative registered asset, choose a short mid-asset window,
   compute Intensity, and verify the new value-density panel plus exact
   current-frame spatial overlay.
2. Select Change energy and confirm one replacement job, hidden predecessor
   context, later-frame `(t-1,t)` alignment, and no retained Intensity result.
3. Move the window to frame zero and confirm frame zero is absent/invalid while
   valid exact-zero pairs remain visibly distinct.
4. Toggle grid and channel overlay independently; hover density bins and player
   blocks to verify their different aggregate/spatial readouts.
5. Seek, scrub, step, and play rapidly; confirm an old overlay never paints over
   a newly decoded frame and no navigation triggers scientific computation.
6. Compare Off and per-frame z-score units/mappings and verify previous/current
   degenerate pair evidence on constant/nonconstant lossless fixtures.
7. Resize and play on the native Windows window. Confirm partial-edge alignment
   and assess whether the measured approximately `6 ms` per-new-frame overlay
   preparation causes any visible playback regression.
8. Toggle channel and normalization rapidly, change window/grid/asset during
   work, cancel, and close; confirm one source owner and no stale publication.
9. Accept milestones 5–7 as visible integrated behavior or report concrete
   scientific/presentation changes.

Do not begin static value filtering, Morlet processing, or detection during
this validation step.

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

- Add static value filtering, value bands, Morlet processing, detection, or a
  third scientific channel.
- Generalize the concrete selected-channel worker/panel into a channel registry,
  graph, or cross-channel scheduler before another measured use requires it.
- Add additional media planes or a plane registry.
- Add scientific result persistence, recipes, export, CLI/HPC processing, or a
  general graph executor.

When a later multi-basis channel handoff arrives, evaluate the benchmarkable
contract proposed in `docs/ideas/processing-ideas.md`. Do not add direct
grayscale delivery or a general plane registry before a measured channel use
justifies them.

The milestone-5 review found that commit `0f4afb2` has implementation-shaped
metadata but contains documentation only. Do not use its commit subject as
evidence that intensity exists.

Milestone 7 implemented temporal change energy through the selected-channel
path. Visible/manual acceptance of the integrated milestone-5/6/7 behavior is
now the gate. Stop before static filtering or milestone 8.

The oracle handoff for each later milestone must be reviewed against the
then-current checkout and recorded in
`docs/handoffs/.isolate-state-divergence.md` before implementation.
