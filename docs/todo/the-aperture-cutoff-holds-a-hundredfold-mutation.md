---
title: block_signal's aperture cutoff survives a ten-thousandfold mutation
priority: normal
phase: 4
status: open
gated_on: nothing
opened: 2026-08-07
---

# block_signal's aperture cutoff survives a ten-thousandfold mutation

`DET_EPS = 1e-6` is documented in `tools/block_signal.py` as v1's cutoff and as
part of the parity semantic rather than a knob — the determinant below which
the Lucas-Kanade system is aperture-degenerate and the solve returns exactly
zero. 04.4's review mutated it and `tests/unit/test_block_signal.py` stayed
green from `1e-6` through `1e-2`, four orders of magnitude, including all four
goldens. It first fails at `1e-1`.

The two fixtures that touch the guard sit at the ends of the scale and neither
lands in the band. `test_aperture_degenerate_input_reports_exactly_zero_not_noise`
and `test_flow_agreement_is_zero_where_nothing_resolved_not_one` use stripes
whose determinant is at machine zero, so any cutoff at all zeroes them; the
textured field the goldens are cut from is well-posed everywhere, so any cutoff
below `1e-1` passes every pixel. Nothing in the file produces a pixel whose
classification depends on the constant's value.

What the gap costs is a silent rescale of what "unmeasurable" means. A wrong
cutoff does not raise and does not change a shape — it moves which pixels
`flow_speed` reports as honest zero and which pixels `flow_agreement` averages
over, and both feed a band a session was tuned against. The port carried the
right number; what is missing is the case that would catch it drifting.

The case wants a fixture with a determinant *near* the cutoff — a texture
whose contrast is scaled down until its blurred products land the determinant
in the `1e-6` decade — and an assertion that pixels straddle the guard: some
resolved, some zeroed. That is a fixture v2 never wrote, which is why it is a
coverage decision rather than part of 04.4's port, and it is the same argument
`block-signal-refuses-and-converts-with-no-case.md` makes about the other
three unreached branches of the same file.

Two mutants that also survived are equivalent rather than uncovered and want
no case: relabelling `ix`/`iy` in `_lk_flow`, and flipping the sign of `it`
there. Both flow signals are magnitudes — `hypot(u, v)` and a resultant length
— so a reflection or a global negation of the flow field leaves every emitted
number identical. Direction is computed and never emitted.
