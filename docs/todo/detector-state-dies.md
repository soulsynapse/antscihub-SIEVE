---
title: DetectorState dies, and nothing replaces it
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [the-graph-carries-the-crop-the-span-and-the-detector, one-definition-of-edge-legality, presentation-is-a-channel-not-a-switch]
reads: [src/sieve/gui/chain_model.py, src/sieve/gui/filter_tab.py, src/sieve/gui/commands.py]
---

# DetectorState dies, and nothing replaces it

Demolition, second tranche — the GUI's hand-rolled stand-ins for facilities a
node now has. These are deleted, not extracted; that is the point of the
supersede half of the GUI triage (they only ever existed because the detector
was not a node):

- `DetectorState` — the second, mutable spelling of the detector's settings,
  field list hand-typed twice, with its `to_settings`/`from_settings`
  converters. `solo_block` is view state and stays, in the view-state bucket,
  not in whatever replaces the container.
- `reuse_band_power` — the one-boolean hand-rolled cache standing in for what
  `cache_key.py` does generically. The cheap/expensive-drag *shape* (a drag
  must not re-run an FFT) survives as cache behaviour of the detection
  filter's stages, which is where it always belonged.
- `ChainKind` and `grade` — replaced by `Dag.validate()` diagnostics
  (`one-definition-of-edge-legality`).
- `EditDetector` — detector edits become node-param edits through the
  existing `EditTuningParams` path; the drag-merge undo mechanics are the
  part to keep, and they already live in `commands.py`.

After this lands, `chain_model.py` is containers and view state,
`detector_worker.py` is a QThread wrapper around a pipeline call, and
`filter_tab.py`'s jobs 2/3/5/6 have shrunk to signal wiring —
`filter-tab-is-eleven-jobs` becomes mostly bookkeeping.
