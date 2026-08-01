# Signatures and verified equivalence

This is the mechanism that lets the executor prefer a fast path without anyone having
proved the fast path correct, and it is the same mechanism that lets a user discover that
their six-month recording study can be answered from one frame every three minutes. It is
also the riskiest part of the design, so this document is explicit about where it holds and
where it does not.

## The problem it solves

The executor wants the cheapest cover of the intent DAG. Cheaper covers are almost never
bit-identical: box decimation is not Lanczos decimation, a separable approximation is not
the full convolution, and an ROI-aware decode is not a crop of a full decode. Formal
rewriting would demand a proof of equality that does not exist, so substitution instead
rests on *measured* equivalence: run both providers over a fixed reference set, reduce each
run through a probe, and test whether the two results differ by less than a declared margin.

## Signature

A **signature** is a provider's recorded behavior on the reference set: for each reference
item, the probe-reduced output, plus the measured wall clock and memory. It is
content-addressed on `(provider identity + version, reference set id, probe id, normalized
params)` and committed to the repo.

Signatures do two jobs. Between two providers they establish equivalence. Against a
provider's own history they are a regression baseline — rewrite an implementation and its
new signature is compared to the one in git automatically, with no separate golden-file
scaffolding to maintain. That second use is free and is why signatures are stored rather
than computed on demand.

## Probe

Equivalence is never absolute. It is always relative to a downstream use, and the probe is
that use made explicit: a function from a provider's output to a comparable quantity. A
probe may be generic (per-frame RMS difference against the reference provider, spectral
distance, mask IoU) or it may be a real discriminator (the detector the user actually
intends to run, at the threshold they actually intend to use).

"One frame per three minutes is equivalent to 30 fps" is false as a statement about the
frames and true as a statement about a specific detector's verdicts. The record says which,
and a record established under probe *P* licenses substitution only in plans whose terminal
output reaches the user through something *P* covers.

## Reference set

A fixed, versioned collection of media chosen to span the regimes the kernel is expected to
handle — motion scale, contrast, texture, noise, illumination change, occlusion density.
Curated deliberately, small enough to run in CI, and versioned so that changing it
invalidates the signatures computed against it rather than silently changing their meaning.

Reference-set curation is the load-bearing manual work in this design. An equivalence claim
is exactly as trustworthy as the coverage of the set it was verified on, and a set that
omits a regime will happily certify a fast path that fails in that regime. Adding a regime
to the set is a normal and expected response to a discovered failure, and doing so
invalidates and re-runs the affected claims.

## The statistical test

Use an **equivalence test**, not a difference test. Failing to reject a null of "no
difference" is not evidence of sameness — it is usually evidence of a small reference set.
Two acceptable forms:

- **TOST** (two one-sided tests) against a declared margin τ: reject "difference ≥ τ" from
  both sides. The verdict is `equivalent` only if both one-sided tests reject.
- **Bootstrap CI on the difference**, resampling over reference items, with the verdict
  `equivalent` when the whole interval lies within ±τ.

The bootstrap form is usually the honest one here. For deterministic providers on a fixed
set there is no sampling noise within an item; the variability that matters is *across*
reference items, i.e. across regimes. Power therefore comes from reference set breadth, not
from repeated runs of the same clip.

**τ is declared, not discovered.** It belongs to the probe, and it is a scientific claim:
"differences below this do not change the conclusion the probe supports." A τ chosen after
seeing the result is not a margin, it is a rationalization, and the record's `commit` field
exists partly so this is auditable.

**Multiple comparisons matter.** A new fast path claiming equivalence against many existing
providers is running many tests, and some will pass by chance. Control the family-wise error
rate across the claims made in a single submission.

## Sensitivity and composition

Tolerance does not compose through everything. A chain of small substitutions can produce a
large end-to-end difference wherever a system is sensitive and folds. But most of a video
kernel is not that: blurs, decimations, and integrations are contractive, and errors shrink
along them. The distinction is known when the provider is written, so it is declared:

- `contractive` — Lipschitz below 1; error shrinks. Blurs, decimations, temporal
  integration, most filtering.
- `stable` — Lipschitz near 1; error carried, not amplified. Affine transforms, colour
  conversions, most pointwise arithmetic.
- `sensitive` — a discrete decision or history dependence: thresholds, argmax, connected
  components, trackers, anything whose state at *t* depends on its state at *t−1*.

Along a span of `contractive` and `stable` providers, per-link tolerances compose and the
planner may substitute link by link. A `sensitive` provider is a **barrier**: any
substitution upstream of it must be verified end-to-end *through* it, on the plan's terminal
output. This is more expensive to verify and it is the correct cost — it is precisely the
place where cheap local reasoning would be wrong.

The honest limitation: this is a declared classification, not a proved one. A provider
mislabelled `contractive` will silently license unsound substitutions. Treat the label as a
contract with teeth — the conformance suite should include a numerical sensitivity probe
that perturbs inputs and checks that the measured Lipschitz behaviour is consistent with the
declared class. That check is cheap and catches the common mistake.

## The user-facing use

The registry is not only the planner's. A user can register their own discriminator as a
probe and ask: which of these cheaper paths is equivalent *for my question*? The answers
are frequently dramatic, because ethological questions are usually far coarser than the
footage that carries them. Frame decimation is the obvious case; spatial downsampling,
channel reduction, and coarse thresholding on change energy are others.

This is what turns SIEVE from a convenience into a hypothesis discriminator. Establishing
that a 30 fps, six-month recording can be answered at one frame per three minutes is not a
performance optimization — it is the difference between a study that can be run and one that
cannot. The tooling that produces that result is the same tooling that picks the executor's
defaults, and the same tooling that regression-tests the kernel. One mechanism, three uses.

## What this does not do

It does not prove anything. A verified claim means "no detectable difference beyond τ on
this reference set under this probe," and each of those three qualifiers is a real limit.
It does not make equivalence a congruence — that is what the sensitivity classes manage, and
they manage it by refusing to compose rather than by solving it. It does not eliminate the
need for judgment about τ. And a claim verified under one user's probe says nothing about
another user's probe, which is why records are stored per probe rather than per provider
pair.

Failure mode to watch: missing or failed equivalence records must make SIEVE *slow*, never
*wrong*. If a record is absent, the executor uses the provider the plan named. Any design
change that would let an unverified substitution through is a defect regardless of how much
faster it is.
