---
title: Schema v1 is re-derived with nodes
step: "03.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py -q"
opened: 2026-08-06
---

# Schema v1 is re-derived with nodes

`core/pipeline_model.py` re-derived as schema v1: crop, span, and the
detector are graph nodes natively (`adr/detector-is-a-node.md`). Kept
verbatim in spirit: `extra=forbid`, registry-blind, no measurements in the
artifact, checkpoints and outputs on `Project` not `Node`. Re-derived is not
freehand: v2's `test_pipeline_model.py` ports wherever the claim survives
(forbid, round-trip, registry-blindness), and each dropped case names the
node that replaced the field it covered. No v2 field name is spelled here
(`adr/compat-spells-v2.md`) — schema v1 is written as if v2 never existed,
and only `compat/` ever learns otherwise.
