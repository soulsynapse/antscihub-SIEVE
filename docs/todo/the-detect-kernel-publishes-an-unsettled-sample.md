---
title: The detect kernel publishes the one sample its own frontier excludes
status: open
opened: 2026-08-05T23:38:44-07:00
priority: normal
gated_on: nothing
reads:
  - src/sieve/filters/detect.py
  - src/sieve/detect/detector.py
  - src/sieve/core/ops/wavelet.py
---

# The detect kernel publishes the one sample its own frontier excludes

`detect_cpu` derives over the span it is handed and returns
`float(gate[-1])`. `morlet_power` zero-pads past the end of any record it is
given, so that last sample sits inside the cone of influence at the cut — it is
exactly the sample `core/ops/wavelet.py` `settled_frames` calls *provisional*,
meaning its value changes when the next frames arrive. `core/ops/detection.py`
`settled_frames` says the same of a centered mean near the cut,
`detect/detector.py` `settled_for` takes the smaller of the two, and `gate_to`
enforces it for every other caller. The kernel calls none of them.

So the one filter that most needs the frontier publishes the one value the
frontier excludes, and it publishes it as an ordinary float indistinguishable
from a settled one. That is rule 6 stated as a defect rather than as a rule,
and it is standing in the tree now — it has nothing to do with the graph
migration and does not wait on it.

**Separate from `a-kernel-that-sees-past-its-target` on purpose.** That item
lists this fix among the things it finishes, and bundling them would make a
defect wait for a protocol. The honest emission is available today: NaN is
already `detect_cpu`'s absent value for a gate that is `None`, and rule 6's
whole posture is refuse rather than approximate. A trailing kernel whose target
is inside its own COI has nothing settled to say, and saying so is correct even
though it means a hand-built detect graph mostly emits NaN until the protocol
widens. That outcome is the argument for widening it, not a reason to keep
returning a number.

The check that would fail if it regressed: a span whose target is inside the
band's cone of influence yields NaN, and one far enough from the cut yields the
same value `detect_series` gives for that index over the same frames. The
second half is the sharper of the two — it pins that the kernel and the
whole-record adapter agree *where they are both entitled to an opinion*, which
is the only region where agreement is even meaningful, and it is a piece of
`detection-disagreement-is-measured`'s answer arriving as a test.
