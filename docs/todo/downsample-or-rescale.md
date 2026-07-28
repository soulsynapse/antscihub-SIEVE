---
title: Downsample or rescale
status: deferred
opened: 2026-07-27
gated_on: >
  the parity-comparison finding landing — rescale is v1's semantic and must
  exist unchanged until the comparison has run; after it, this item decides
  whether rescale stays a first-class step or becomes a parity fixture
reads:
  - src/sieve/filters/downsample.py
  - src/sieve/filters/rescale.py
  - docs/todo/parity-comparison-finding.md
---

# Downsample or rescale — which is the de facto shrink, and what actually differs

Raised 2026-07-27: "I'm not sure if Downsample and Rescale are meaningfully
different — I'm leaning towards downsample as the de facto because aliasing is
helpful but the main difference (for me) is that downsample has integers which
is way more friendly. What actually matters is the difference between them."

## The differences that are real, in decreasing order of consequence

They are meaningfully different, and the split was already decided once —
`rescale.py`'s module docstring records why it is a second filter and not a
params-v2 of `downsample` (disjoint parameter spaces, disjoint output
geometry, and migrating would break every existing cache key). What follows is
the *user-facing* difference, which that docstring does not state:

1. **Only `downsample` can preserve aliasing.** `rescale` always area-averages
   (`INTER_AREA` — it low-pass filters before decimating, deliberately).
   `downsample` defaults to the same averaging but has `anti_alias=False`: a
   pure stride sample, every output pixel a source pixel, aliasing and all. So
   "aliasing is helpful" is not an argument between the two filters — it is an
   argument for `downsample` *with `anti_alias` off*, a setting of a parameter
   the other filter structurally cannot offer.
2. **Integer vs float geometry.** `factor` divides and truncates — exact,
   composable (4 = 2 then 2), and the output grid is a strict subgrid of the
   source. `scale` multiplies and rounds — any target size is reachable, and
   `block_signal`'s `0 = auto` grid arithmetic is defined against `scale`.
3. **Parity.** `rescale` *is* v1's semantic (`round(src x scale)`,
   INTER_AREA, exact no-op at 1.0). The tab's spinbox speaks it, and the
   parity comparison depends on it existing bit-for-bit.

## The claim to test, because it is currently a hunch

"Aliasing is helpful" is an empirical claim about the detection chain, and it
cuts both ways. For it: stride sampling preserves per-pixel amplitude of
fine-scale motion that averaging attenuates — a leg-tip crossing one source
pixel survives sampling and is diluted 1/factor² by averaging. Against it:
aliased high spatial frequencies decorrelate between consecutive frames, which
inflates `<I_t²>` background and violates the brightness-constancy assumption
the LK solve rests on — so it may raise change_energy's noise floor and
corrupt flow_speed/coherence rather than help them.

**Hypothesis test:** on the reference footage, run the chain at matched output
size through (a) `rescale`, (b) `downsample` averaged, (c) `downsample`
strided, and compare event-window vs quiet-window separation (the detector's
own band-power statistic) per signal. Prediction worth pre-stating: (c) helps
change_energy on sub-pixel motion and *hurts* flow_speed and coherence. Result
is a finding either way, and it decides whether `anti_alias=False` is a
recommendation or a trap.

## The decision this item exists to make, after parity

If the finding says averaging is right for the tensor signals (likely), the
de facto shrink for new work is `downsample` with its default on — integers,
composability, and the storage-ratio arithmetic are the friendliness that
matters — and `rescale` remains what it is: the parity semantic the live tab
speaks. Retiring `rescale` would require migrating the tab's spinbox and the
auto-block arithmetic onto integer factors, and is only worth deciding once
the parity finding says nothing still depends on v1's exact geometry.
