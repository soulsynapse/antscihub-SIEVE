---
title: A record survives the rename it is built to survive
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# A record survives the rename it is built to survive

`CropRecord.backs` says in its docstring that it matches "by geometry and
parentage rather than by name, which is what lets a record survive a rename",
and nothing asserts that. The property holds by construction today — the
comparison touches `cut_from`, `region`, `luma`, and file existence and never
a name — so this is not a bug, it is a promise carried by prose in a predicate
that is about to gain a caller in 05.1.

One case in `TestCropRecords`: write the file under one name, move it, point
the record's `path` at the new name, and assert `backs` still answers yes for
the same region and parent. It is the last of v2's nine
`test_crop_artifact.py` cases that v3 does not assert
(`findings/2026.08.07-the-crop-record-half-of-v2s-artifact-file-landed-with-schema-v1.md`);
the other eight are green or have no v3 subject.

Phase 5 rather than now because the caller that would make a regression here
visible is 05.1's materialize, and until then a broken `backs` breaks nothing.
