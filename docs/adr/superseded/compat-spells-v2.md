---
title: compat is the only module that spells v2 field names
adr: 4
status: superseded
superseded_by: v2-does-not-import
decided: 2026-08-06
---

`compat/v2.py` is the one-way importer, and no module outside `compat/` may
spell a v2 field name.

Why: containment is what keeps the importer deletable and the rename
checkable — the moment `filter_id` or `Replicate.roi` appears in a second
module, v3 has two vocabularies instead of a translation at the border. One
direction only: v3 never writes v2's format, so nothing v2-shaped constrains
schema v1's evolution.
