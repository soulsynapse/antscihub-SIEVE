---
title: A number says how it was founded, and for which machine
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [work-units-have-one-anchor]
serves: A2
reads: [src/sieve/bench/budgets.py, src/sieve/core/machine.py]
---

# A number says how it was founded, and for which machine

REWORK.md R6's provenance half. `TargetProfile` (shape in `core/` — `bench`
produces it and both front ends consume it, so its shape is agreement
vocabulary even though its values are machine-specific) and a `WallEstimate`
carrying dispersion; the `(WorkUnits, TargetProfile) -> WallEstimate`
conversion lives in `bench/`, whose only consumers sit above it.

The constraints that are the point, each a rule-6 failure if dropped:

- **Dispersion must not shrink with n.** Scaling a per-frame residual as √n
  over a 100k-frame job collapses the p95 toward the mean — a point estimate
  wearing a quantile's name, worse than the scalar it replaced because it
  looks principled. Job-level uncertainty is dominated by systematic error
  (wrong resolution, throttling, a contended node); it does not average out.
- **Every displayed wall number carries predicted-versus-measured and which
  profile produced it.** The realtime factor during tuning is measured once
  the clip has run and predicted before; one number silently either costs an
  afternoon. `FrameResult.source_cropped` is the precedent — a value that
  could be either says which.
- **A stale or unmatched fingerprint is a refusal**, and the graceful form is
  already implied by the type split: work units, labeled uncalibrated. Never
  the reference machine's constants.
- The target is explicit at the call site, recorded into the plan and any
  output artifact, declared **non-hashed** (rule 7: the machine a prediction
  was made for does not change what a result is).

The calibration is at minimum per core class — the worker-optimum finding
(2.33x across worker counts, optimum moving P- to E-cores) is the evidence,
and it makes the calibration file and `adaptive-worker-allocation` the same
object seen twice.
