---
title: A kernel that sees past its target
status: open
opened: 2026-08-05T23:20:19-07:00
priority: high
gated_on: nothing structurally
reads:
  - src/sieve/core/types.py
  - src/sieve/pipeline/executor.py
  - src/sieve/filters/detect.py
  - src/sieve/detect/detector.py
after: [a-kernel-that-sees-a-span]
---

# A kernel that sees past its target

`a-kernel-that-sees-a-span` settled the trailing half of the windowed protocol:
a kernel is handed a `FrameSpan` and returns the frame for `FrameSpan.target`,
and the executor sizes that span as refined `warmup_frames` plus the current
frame (`executor.py`, `window = node_warmup_frames(...) + 1`). This is the
other half. It was written down as `the-detector-node-is-centered`'s gate in
prose — "a windowed kernel that can be handed a span with frames on both sides
of its target" — and a gate that is prose is a gate with no slug and no rank.

**What is wrong now, and it is not only the migration.** `detect_cpu` derives
over the span it is handed and returns `float(gate[-1])`. `morlet_power`
zero-pads past the end of any record it is given, so that last sample sits
inside the cone of influence at the cut — it is exactly the sample
`core/ops/wavelet.py` `settled_frames` calls *provisional*, meaning its value
changes when the next frames arrive. `core/ops/detection.py` `settled_frames`
says the same of a centered mean, `detect/detector.py` `settled_for` takes the
smaller of the two, `gate_to` enforces it, and the GUI fades everything past
it. The kernel calls none of them. So the one filter that most needs the
frontier publishes the one value the frontier excludes, which is rule 6 stated
as a defect rather than as a rule.

**The quantity is already derived; nothing has to be invented.** How far
forward a centered detector must see is `SETTLE_EFOLDINGS` cone-of-influence
lengths at the *band's* lowest frequency, plus `window - window // 2 - 1` for
the centred mean — the two functions above, evaluated for a bound instead of
for a record. `warmup_frames` has exactly this shape already (spec-level bound,
params-level refinement, `node_warmup_frames` picking between them), and
`filter_base.py` anticipates this item in the `warmup_frames` docstring: "a
`WINDOWED` filter has them too, and its protocol does not exist yet."

Done looks like:

- `FrameSpan` carries a target that is not necessarily its last frame.
  `target` is `frames[-1]` today, in `core/types.py`, and every trailing kernel
  must go on meaning what it means — a filter that declares no look-ahead gets
  the span it gets today, unchanged and unmoved.
- A forward declaration beside `warmup_frames` on `FilterSpec`, with the same
  bound/refinement split and the same `node_*` picker. Which channel it sits in
  is decided by `the-spec-has-three-channels`: it changes *what a result is*,
  so it is identity.
- The executor sizes the span as lead-in + target + look-ahead and therefore
  yields frame *t* only once it has decoded *t + lookahead*. That lag is the
  price and it is the item's real content, not the protocol edit.
- `detect_cpu` gates its own output through `settled_for` rather than reaching
  for `gate[-1]`, and refuses (NaN is already its absent value) rather than
  publishing a provisional sample.

**The price, stated so it can be argued rather than discovered.** The lag is
denominated on the lowest frequency in the tuned band: at 0.5 Hz,
`SETTLE_EFOLDINGS = 2` is ~5.5 s, ~165 frames at 30 fps, out of the interactive
loop that is the whole product. A detector tuned high pays almost nothing. So
the measurement this item owes is the lag as a function of the band, against
`bench/budgets.py`'s first-frame budget — and if the answer is that a low-band
detector cannot render interactively at all, that is a finding and a design
decision (render the settled frontier and fade the rest, which is what the GUI
already does today for the same reason), not a reason to skip the protocol.

What this unblocks: `the-detector-node-is-centered`, and behind it
`detector-state-dies`, `rule-sixs-frontier-moves-into-the-contract` and
`the-band-handlers-are-one-shape-said-five-times`. `rule-sixs-frontier-moves-
into-the-contract` is the closest neighbour and may turn out to be the same
work seen from the other end — it moves `settled_for`/`gate_to` into the
execution contract, and a look-ahead declaration is what the contract would
have to hold for it to.
