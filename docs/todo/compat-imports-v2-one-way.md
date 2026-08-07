---
title: compat imports v2 one way
priority: normal
phase: 3
status: open
gated_on: nothing
opened: 2026-08-06
---

# compat imports v2 one way

Pooled, not sequenced — Kendrick pulled compatibility off the overnight
path (2026-08-06); promote to a step when a real v2 project needs to come
over. The shape is already settled and does not need re-deciding then:
`compat/v2.py` is the only module spelling v2 field names
(`adr/compat-spells-v2.md`), reuses `upgrade.py`'s carry logic (derived node
ids, per-replicate pinned boxes, identity-crop baseline), refuses by field
name what it cannot carry, and v2's `tests/fixtures/project-v5.sieve.yaml`
ports as the import fixture. Its layer position is already drawn in 00.2.
