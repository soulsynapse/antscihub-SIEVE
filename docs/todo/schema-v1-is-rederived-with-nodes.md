---
title: Schema v1 is re-derived with nodes
step: "02.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_replicates.py -q"
opened: 2026-08-06
---

# Schema v1 is re-derived with nodes

`core/pipeline_model.py` re-derived as schema v1: crop, span, and the
detector are graph nodes natively (`adr/detector-is-a-node.md`). Kept
verbatim in spirit: `extra=forbid`, registry-blind, no measurements in the
artifact, checkpoints and outputs on `Project` not `Node`. No v2 field name
is spelled anywhere (`adr/v2-does-not-import.md`) — schema v1 is written as
if v2 never existed.

The replicate is part of this module rather than beside it: v2 split
`core/replicates.py` out because the model was already 1,273 lines, and
`adr/core-membership-is-closed.md` admits `pipeline_model.py` and not a
second child, so keeping the split would buy an ADR revision for nothing.

Under PLAN.md's re-derivation clause: v2's `test_pipeline_model.py` holds
**25 cases in 8 classes** and `test_replicates.py` **14 cases**, and this
item's table has 39 rows. `tests/property/test_replicates.py` is not in the
criterion — its three cases need `hypothesis`, which no v3 component has
asked for, and adding a dependency is a decision this item does not carry.

What the fields must still be able to say, because Phase 5 builds on them:
`checkpoints` (node ids whose output is written), `outputs` (the sink
records), and the crop record with its `backs` matching — associated with the
box it was cut from by geometry and parentage, never by name, so a rename
survives and a box that moved correctly stops matching. All three live on
`Project` because none of them may reach a cache key: turning a checkpoint
off for a cluster run must not change what a result is.
