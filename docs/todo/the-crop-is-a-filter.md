---
title: The crop is a filter
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
after: [declarable-but-not-runnable]
reads: [src/sieve/pipeline/executor.py, src/sieve/pipeline/resolve_source.py, src/sieve/filters/downsample.py]
---

# The crop is a filter

REWORK.md R1's cheapest proof: crop is already Frame → Frame,
`Mode.STREAMING`, no protocol extension — a spec, a kernel, a markdown, in
`src/sieve/filters/crop.py`, discovered like everything else. "No crop" is a
full-frame ROI, never `None`; the identity value of a present parameter is
what keeps `X | None` out of the plan (R1's identity-is-not-exemption
clause).

**The schema does not move here** — that is the fourth ordering constraint's
territory (`the-graph-carries-the-crop-the-span-and-the-detector`). This item
lands the filter reachable end-to-end through `sieve run` on a hand-built
YAML project, with tests, while the GUI keeps writing `Replicate.roi`. Three
filters existing that the product does not yet write into saved graphs is the
`MergingKernel`/`Edge.port` precedent: acceptable exactly because each is
reachable from a front end and tested, which makes it a narrower front end
rather than dead code.

The thing to not get wrong, recorded now because it is the migration's named
risk: `resolve_source.py` already has two coordinate numberings (a crop
artifact's frame space versus the parent's). The crop filter's ROI is
denominated in its *input's* space, and the equivalence test in the flip item
is what checks nobody silently disagrees.
