---
title: The motion history filter
status: open
opened: 2026-07-26
gated_on: >
  nothing structurally — single-upstream, streaming, rate-preserving and
  stateful, the shape background_ema already established
reads:
  - src/sieve/filters/background_ema.py
  - src/sieve/filters/temporal_baseline.py
  - src/sieve/core/detection.py
  - docs/REFINED-VISION.md
  - docs/VISION.md
---

# The motion history filter

**Gated on: nothing structurally** — single-upstream, streaming,
rate-preserving and stateful, which is the shape `background_ema` already
established, down to the buffer discipline. It was ordered last because its
thresholds wanted the units `temporal_baseline` now provides and its output
wants somewhere to be combined; the first is settled, the second is still true —
nothing yet evaluates a two-signal rule.

**What is already paid for.** `tau_seconds` has exactly `temporal_baseline`'s
shape — a warmup that is a parameter in physical units, needing `fps` to
convert — so the contract half is done and the pattern to copy is
`TemporalBaselineParams.warmup_frames`: declare the worst case over the legal
range on the spec, override the method with the configured need.

**What it is.** The vision's "exponential decay function and a blooming touch
function", which is `a[t] = λ·(K ⊛ a[t−1]) + (1−λ)·s[t]` — the semi-implicit
Euler step of `∂a/∂t = −a/τ + D∇²a + s`. `VISION.md` step 3 category C already
names MEI and MHI, and this is them: Bobick & Davis's Motion History Image is
the same operator with a linear decay law. Name it for them so a user can find
the literature.

**Four decisions, all argued in `REFINED-VISION.md` C:**

- **Decay and coupling are one node, two parameters.** Blurring the output of a
  leaky integrator is a different operator — in the recursion the coupling
  compounds through the feedback path.
- **Physical units.** `tau_seconds`, not λ; `reach_blocks`, not κ. `fps` plumbs
  in exactly as `block_signal`'s does.
- **Two coupling modes.** `diffuse` (linear, conservative, spreads the peak
  *down* and fights the threshold) and `dilate` (grayscale morphological,
  sustains support without lowering peaks). Expect `dilate` to win; ship both.
- **Group delay is declared or removed.** A causal integrator lags its event by
  order τ, and mixing it with `windowed_mean`'s `centered` mode biases reported
  onsets late by an amount nothing writes down. Either run forward-and-backward
  for zero phase (legitimate offline) or declare the delay. Not neither.

**The stability bound is the test worth writing.** With `reach` unbounded the
dilation form propagates one detection outward at one block per frame until it
fills the arena. Run a single-block impulse through a long run and assert the
support stops growing — that is what catches a beautiful demo that is wrong.

Read: `docs/REFINED-VISION.md` **C**, `docs/VISION.md` step 3 category C.
