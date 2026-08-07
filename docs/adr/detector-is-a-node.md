---
title: Crop, span, and the detector are graph nodes
adr: 3
position: "02.01"
status: settled
decided: 2026-08-06
---

Schema v1 has crop, span, and the detector as graph nodes natively — no
`Project.detector`, no `Replicate.roi`, no `Project.clip`.

Why: v2 grew a bespoke field for each thing that could not be a filter, and
each field needed bespoke carry logic in `upgrade.py`. The 2026.08.05 finding
revision licenses the fold: of the three blockers that kept detection out of
the graph, two have answers and the third was drawn too wide. The detector
lands last (Phase 4) as a *centered* windowed tool on the Phase-1 declared
lookahead — its parity target is v2's `detect/` package output, the centered
whole-record result that was tuned against, not the trailing kernel.
