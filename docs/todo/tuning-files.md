---
title: "Tuning files: export and import the baseline"
status: deferred
gated_on: >
  the first tuning somebody wants to apply to a second video — likely the
  parity-comparison finding, or the first multi-source experiment
reads:
  - src/sieve/core/pipeline_model.py
  - docs/REFINED-VISION.md
  - docs/completed-todo/2026.07.27-replicates-remember-their-settings.md
---

# Tuning files: export and import the baseline

**Why not now.** The thing a tuning file would carry only just started existing
as one object: since replicates remember their settings (2026.07.27), a
complete tuning is exactly `Project.pipeline` plus `Project.detector` — the
baselines every un-pinned replicate follows — and per-replicate pins are
deliberately *not* part of it, because a pin is a correction for one arena's
footage, not part of the behaviour's fingerprint. Nothing yet asks to move
that object between projects, and building the importer before the first real
cross-experiment reuse would fix the file format on a guess.

**What would make it the right time.** The first tuning somebody wants to
apply to a second video — likely the parity-comparison finding, or the first
multi-source experiment. Import is then semantically free: replacing the
baseline is the same operation every knob edit already performs, so every
replicate without pins adopts the imported tuning instantly and every pinned
deviation survives (and should be reported, not silently kept).

**The constraint to not get wrong when it lands.** A tuning file is only a
transferable fingerprint when the chain standardizes against the per-block
baseline (`REFINED-VISION.md` **A**): a threshold in k·MAD units transfers, a
threshold in raw energy units is a fact about one lighting rig, and the export
must not launder the second into looking like the first. Version it like the
project (it is a subset of one), and refuse an import whose filters are not
installed rather than importing the parts that resolve.

Read: `core/pipeline_model.py` (`DetectorSettings`, the two-write helpers),
`docs/REFINED-VISION.md` **A**,
`docs/completed-todo/2026.07.27-replicates-remember-their-settings.md`.
