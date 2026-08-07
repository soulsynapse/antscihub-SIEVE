---
priority: high
phase: 5
status: done
gated_on: nothing
opened: 2026-08-07
title: Two items name the same crop artifact test file
---

# Two items name the same crop artifact test file

04.1 and 05.1 both put `tests/unit/test_crop_artifact.py` in their `done_when`,
and they mean different files. 04.1 says the writer is "read, not written" and
its subject is the pair that had never met — the crop tool's frames through
`write_ffv1` and back byte-identical, which is the guard v2's codec finding
demands and the only thing 04.1 could mean by a crop *artifact* when it lands
no record. 05.1's subject is v2's `test_crop_artifact.py`, whose cases are
`CropRecord` round-tripping through a document and the `backs` matching rule,
and it states the file holds **9 cases**.

04.1 landed five in that file. So 05.1's count now stands over a file that
already exists with a different subject, and the item's session has to decide
between three things it cannot decide from its own text: extend to 14, split
the record cases into a file of their own, or find that the record half is
already covered — which it may well be, because `test_pipeline_model.py`
carries `backs`, `with_crop`, `without_crop`, the relocation rebase, and the
duplicate-cut refusal today, and that is most of v2's file.

What this item wants is the adjudication written down before 05.1 runs, in
05.1's `done_when` and case count — which only a review may edit. It is not a
question about the pixels: 04.1's five cases pin something no other file does
and should not move on account of a name.
