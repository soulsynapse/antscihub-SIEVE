[INTENT] The replicate vision treats replicates as independent. A tab for
splitting replicates makes that separation visible, and a user can optionally
inherit settings from an already configured replicate.

The basic workflow for replicates is the user draws a box, optionally holding shift to keep it perfectly square if they want. This draws the box. The replicates are listed on the other side. Then, whenever a replicate already exists, the user can either draw a box or just click to use the existing replicate box as a stamp. They can drag the replicate box around independently etc. Clicking into the replicate loads the replicate as the primary target for the filters tab and switches to the filters tab. Right clicking in the filters tab kicks it back to the replicates tab, which shows the whole uncropped source video.

The replicates tab should allow the replicates to be cropped from the source, and then live in their own folders. For local signal analysis, this is probably fine.

[INTENT] Replicates are independent and do not share a processing frame, so
seam concerns do not arise.

Replicate ID is not stable across geometry edits however - if a user tries to drag the replicate box of a processed replicate, a warning box stating that the current results will be invalidated needs to let the user know what they're doing.

Crop to folder is done once the box is committed - dragging is done and the user hits an accept button.

Calibration is a replicate property, not a filter property or a source property.


## Written up formally

# SIEVE — Replicate Vision [INTENT]

A replicate is an independent experimental unit derived from a source
video by cropping. Each replicate has its own filter pipeline, its own
outputs, and its own folder on disk. Replicates do not share a processing
frame; each is treated as an independent source once cropped.

---

## 1. What a replicate is [INTENT]

Replicates are almost certainly independent — a source video typically
contains several separate experimental subjects, and the natural unit of
analysis is one subject at a time. A tab dedicated to splitting the
source into replicates isolates them for what they are. When configuring
a new replicate, the user can optionally inherit settings from an
already-configured one.

A source owns its replicates. They travel with it in project files,
batch runs, and HPC handoff.

## 2. Workflow [INTENT]

Two tabs cooperate.

**Replicates tab.** Shows the uncropped source video. The user:

- Draws a box to define a replicate. Holding Shift constrains it to a
  square.
- With a replicate already drawn, either draws a new box or clicks to
  stamp using an existing replicate's box as a template.
- Drags a replicate box around independently to reposition it.
- Sees the list of existing replicates on the side panel.
- Commits a replicate's geometry with an accept button. Cropping to the
  replicate's folder happens on commit — not during dragging.

Clicking into a replicate loads it as the active target for the filters
tab and switches to that tab. Right-clicking in the filters tab returns
to the replicates tab and the whole uncropped source view.

## 3. Identity and geometry [INTENT]

Replicate identity is tied to geometry. Editing a committed replicate's
box invalidates its cached results. Before applying such an edit on a
processed replicate, the UI shows a warning that current results will
be invalidated and requires confirmation.

Rationale: if a replicate moves to a location with no overlap with its
original pixels, the prior results are meaningless anyway. Rather than
carry a complicated identity-versus-geometry model, the simple rule
holds: geometry change means the replicate's outputs are stale, and the
user is told so explicitly.

Annotation persistence across geometry edits is deliberately out of
scope for v1 and may be revisited later.

## 4. Storage [INTENT]

Cropping is committed, not lazy. When the user commits a replicate's
geometry, the crop is written and the replicate lives in its own folder
under the project. Dragging before commit does not touch disk.

For local signal analysis, this is sufficient.

## 5. Calibration [INTENT]

Calibration is a replicate property rather than a filter or source
property. Physical scale, working scale, and per-experiment
metadata that filters may read live on the replicate.

## 6. Independence [INTENT]

Replicates do not share a processing frame. There are no seam concerns,
no cross-replicate pixel ownership rules, and no partial-block edge
weighting. Each replicate's edges are that replicate's problem.

Two replicates may overlap in source pixels. This is not a correctness
problem — it only means the overlapping region is processed twice, once
per replicate. The user chooses whether that duplication is worth it.

## 7. Source ownership — batch and HPC [INTENT]

The source video owns its replicates. Batch and HPC operations against
a source run the replicates spawned from that source. Each
replicate's pipeline executes independently.

The HPC handoff bundle includes the source, the full replicate list
with geometries and calibrations, and each replicate's pipeline. Crops
execute as part of the remote run, not as a pre-handoff step, so the
bundle stays self-contained and reproducible. See `HPC_HANDOFF.md`.

## 8. What replicates are not [INTENT]

- **Not a filter.** Replicates are not nodes in the pipeline DAG. They
  are the scope in which a DAG runs.
- **Not seam-aware.** Independence obviates seam handling.
- **Not a mechanism for cross-replicate aggregation.** Comparison
  across replicates, if wanted, happens in the review layer.
